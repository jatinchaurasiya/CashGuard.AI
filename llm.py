"""
CashGuard.AI - Resilient OpenRouter LLM Provider for Strands Agents SDK

Features:
1. OpenAI-compatible connection to OpenRouter (base_url: https://openrouter.ai/api/v1).
2. Fallback chain: if a model gets rate limited (HTTP 429) or errors out,
   it automatically switches to the next model in the configured fallback list.
3. Exponential backoff: waits (e.g. 2s, 4s, 8s) before each retry to respect
   OpenRouter's free-tier rate limits (20 requests/minute).
4. Detailed logging: logs which model actually served each request so you can
   easily see if a fallback occurred.
"""

import asyncio
import logging
import threading
from collections.abc import AsyncGenerator, AsyncIterable
from typing import Any, cast

import openai
from pydantic import BaseModel
from strands.models._openai_errors import classify_openai_error
from strands.models.openai import OpenAIModel
from strands.types.content import Messages, SystemContentBlock
from strands.types.streaming import StreamEvent
from strands.types.tools import ToolChoice, ToolSpec

# Configure logger
logger = logging.getLogger("CashGuard.LLM")


class OpenRouterFallbackModel(OpenAIModel):
    """
    An OpenAIModel subclass for OpenRouter that provides:
    - Automatic fallback across a list of models on HTTP 429 or API errors.
    - Exponential backoff between retries.
    - Tracking and logging of which model actually served each request.
    """

    def __init__(
        self,
        model_id: str,
        fallback_models: list[str] | None = None,
        retry_delays: list[float] | None = None,
        api_key: str = "",
        base_url: str = "https://openrouter.ai/api/v1",
        **kwargs: Any,
    ):
        # Configure client args with OpenRouter recommended headers
        client_args = kwargs.pop("client_args", {}) or {}
        client_args.setdefault("api_key", api_key)
        client_args.setdefault("base_url", base_url)
        
        default_headers = client_args.setdefault("default_headers", {})
        default_headers.setdefault("HTTP-Referer", "https://github.com/jatinchaurasiya/CashGuard.AI")
        default_headers.setdefault("X-Title", "CashGuard.AI (Invoice Exception Guardian)")

        super().__init__(model_id=model_id, client_args=client_args, **kwargs)

        # Build fallback model chain (primary model first, followed by fallbacks without duplicates)
        raw_chain = [model_id] + (fallback_models or [])
        seen = set()
        self.model_chain: list[str] = [m for m in raw_chain if m and not (m in seen or seen.add(m))]

        # Backoff delays in seconds (defaults to [2.0, 4.0, 8.0])
        self.retry_delays: list[float] = retry_delays if retry_delays is not None else [2.0, 4.0, 8.0]

        # Tracks which model served the most recent request
        self.last_served_model: str | None = None
        self.execution_history: list[dict[str, Any]] = []

    def _is_rate_limit_or_retryable(self, error: BaseException) -> bool:
        """Determines whether an error is a 429 rate limit or a temporary server error."""
        status_code = getattr(error, "status_code", None)
        err_str = str(error).lower()

        if status_code in (429, 500, 502, 503, 504):
            return True

        if classify_openai_error(error) == "throttling":
            return True

        retryable_keywords = ["rate limit", "too many requests", "429", "overloaded", "temporarily unavailable"]
        return any(kw in err_str for kw in retryable_keywords)

    async def stream(
        self,
        messages: Messages,
        tool_specs: list[ToolSpec] | None = None,
        system_prompt: str | None = None,
        *,
        tool_choice: ToolChoice | None = None,
        system_prompt_content: list[SystemContentBlock] | None = None,
        invocation_state: dict[str, Any] | None = None,
        cancel_signal: threading.Event | None = None,
        **kwargs: Any,
    ) -> AsyncIterable[StreamEvent]:
        """
        Streams response with automatic retry, exponential backoff, and model fallback.
        """
        last_error: Exception | None = None
        models_tried: list[str] = []

        for model_idx, candidate_model in enumerate(self.model_chain):
            models_tried.append(candidate_model)
            self.config["model_id"] = candidate_model

            # Try candidate model with exponential backoff
            for attempt in range(len(self.retry_delays) + 1):
                try:
                    logger.debug(
                        f"[CashGuard.LLM] Attempting model '{candidate_model}' (attempt {attempt + 1}/{len(self.retry_delays) + 1})..."
                    )

                    request = self.format_request(
                        messages,
                        tool_specs,
                        system_prompt,
                        tool_choice,
                        system_prompt_content=system_prompt_content,
                    )
                    request["model"] = candidate_model

                    async with self._get_client() as client:
                        response = await client.chat.completions.create(**request)

                        # Handle non-streaming response format if stream is False
                        if not request.get("stream", True):
                            self.last_served_model = candidate_model
                            self._log_success(candidate_model, model_idx)
                            for chunk in self._format_non_streaming_response(response):
                                yield chunk
                            return

                        # For streaming, check the first event to confirm active connection
                        response_iter = response.__aiter__()
                        try:
                            first_event = await response_iter.__anext__()
                        except StopAsyncIteration:
                            first_event = None

                        # Connection succeeded!
                        self.last_served_model = candidate_model
                        self._log_success(candidate_model, model_idx)

                        # Stream chunks to caller
                        yield self.format_chunk({"chunk_type": "message_start"})
                        tool_calls: dict[int, list[Any]] = {}
                        data_type = None
                        finish_reason = None
                        event = None

                        async def _iter_events():
                            if first_event is not None:
                                yield first_event
                            async for evt in response_iter:
                                yield evt

                        async for event in _iter_events():
                            if not getattr(event, "choices", None):
                                continue
                            choice = event.choices[0]

                            reasoning_content = getattr(choice.delta, "reasoning_content", None)
                            if not isinstance(reasoning_content, str) or not reasoning_content:
                                reasoning_content = getattr(choice.delta, "reasoning", None)

                            if isinstance(reasoning_content, str) and reasoning_content:
                                chunks, data_type = self._stream_switch_content("reasoning_content", data_type)
                                for chunk in chunks:
                                    yield chunk
                                yield self.format_chunk(
                                    {
                                        "chunk_type": "content_delta",
                                        "data_type": data_type,
                                        "data": reasoning_content,
                                    }
                                )

                            if choice.delta.content:
                                chunks, data_type = self._stream_switch_content("text", data_type)
                                for chunk in chunks:
                                    yield chunk
                                yield self.format_chunk(
                                    {
                                        "chunk_type": "content_delta",
                                        "data_type": data_type,
                                        "data": choice.delta.content,
                                    }
                                )

                            for tool_call in choice.delta.tool_calls or []:
                                tool_calls.setdefault(tool_call.index, []).append(tool_call)

                            if choice.finish_reason:
                                finish_reason = choice.finish_reason
                                if data_type:
                                    yield self.format_chunk(
                                        {"chunk_type": "content_stop", "data_type": data_type}
                                    )
                                break

                        for tool_deltas in tool_calls.values():
                            yield self.format_chunk(
                                {"chunk_type": "content_start", "data_type": "tool", "data": tool_deltas[0]}
                            )
                            for tool_delta in tool_deltas:
                                yield self.format_chunk(
                                    {"chunk_type": "content_delta", "data_type": "tool", "data": tool_delta}
                                )
                            yield self.format_chunk({"chunk_type": "content_stop", "data_type": "tool"})

                        yield self.format_chunk(
                            {"chunk_type": "message_stop", "data": finish_reason or "end_turn"}
                        )

                        # Drain remainder for usage metadata
                        async for event in response_iter:
                            _ = event

                        if event and hasattr(event, "usage") and event.usage:
                            yield self.format_chunk({"chunk_type": "metadata", "data": event.usage})

                        return  # Successfully finished streaming

                except Exception as exc:
                    last_error = exc
                    if self._is_rate_limit_or_retryable(exc) and attempt < len(self.retry_delays):
                        delay = self.retry_delays[attempt]
                        logger.warning(
                            f"⚠️ [CashGuard.LLM] Model '{candidate_model}' rate-limited/throttled. "
                            f"Waiting {delay:.1f}s (exponential backoff retry {attempt + 1}/{len(self.retry_delays)})..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        next_model = (
                            self.model_chain[model_idx + 1]
                            if model_idx + 1 < len(self.model_chain)
                            else None
                        )
                        if next_model:
                            logger.warning(
                                f"🔄 [CashGuard.LLM] Model '{candidate_model}' failed ({exc}). "
                                f"Falling back to next model: '{next_model}'..."
                            )
                        break

        # If all candidate models failed:
        error_msg = (
            f"All models in fallback chain failed: {models_tried}. "
            f"Last error encountered: {last_error}"
        )
        logger.error(f"❌ [CashGuard.LLM] {error_msg}")
        raise RuntimeError(error_msg) from last_error

    def _log_success(self, model: str, index: int):
        """Logs the model that actually served the request."""
        if index == 0:
            logger.info(f"✨ [CashGuard.LLM] Request successfully served by primary model: '{model}'")
        else:
            logger.warning(
                f"✨ [CashGuard.LLM] Request served by FALLBACK model: '{model}' (fallback #{index})"
            )
        self.execution_history.append({"model": model, "fallback_index": index})
