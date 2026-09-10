"""
CashGuard.AI - Central Configuration & LLM Connection Settings

This file holds all the core settings for the project in one place.
You can change settings here without having to edit any agent logic code.
"""

import os
import logging
from typing import Any

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ==============================================================================
# LOGGING SETUP
# ==============================================================================
def setup_logging(level=logging.INFO):
    """Configures clean, informative logging for CashGuard."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    # Ensure our custom LLM logger is set to INFO
    logging.getLogger("CashGuard.LLM").setLevel(level)


# Call setup immediately with default INFO
setup_logging()

# ==============================================================================
# 1. PRIMARY LLM MODEL CONFIGURATION
# ==============================================================================
# This is the single central place where the model ID is defined.
# It defaults to "openrouter/free" (OpenRouter's meta-router that auto-selects
# an available free, tool-calling-capable model).
DEFAULT_MODEL_ID: str = "openrouter/free"

# Allow overriding via environment variable MODEL_ID, otherwise use DEFAULT_MODEL_ID
MODEL_ID: str = os.getenv("MODEL_ID", DEFAULT_MODEL_ID)

# ==============================================================================
# 2. FALLBACK CHAIN (FOR RATE LIMITS / 429s OR ERRORS)
# ==============================================================================
# If the primary model hits a 429 (rate limited) or errors out after backoff retries,
# CashGuard automatically tries the next model in this chain.
# You can customize or add any free (:free) or paid models here anytime.
DEFAULT_FALLBACK_MODELS: list[str] = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemini-2.0-flash-exp:free",
    "mistralai/mistral-small-24b-instruct-2501:free",
    "qwen/qwen-2.5-72b-instruct:free",
]

# Read from env if provided as comma-separated string, otherwise use defaults
_env_fallbacks = os.getenv("FALLBACK_MODELS")
if _env_fallbacks:
    FALLBACK_MODELS: list[str] = [m.strip() for m in _env_fallbacks.split(",") if m.strip()]
else:
    FALLBACK_MODELS: list[str] = DEFAULT_FALLBACK_MODELS

# ==============================================================================
# 3. EXPONENTIAL BACKOFF RETRY DELAYS (SECONDS)
# ==============================================================================
# OpenRouter free tier has a 20 requests/minute account-wide rate limit.
# Before falling back to the next model, wait 2s, then 4s, then 8s to avoid hammering.
RETRY_DELAYS: list[float] = [2.0, 4.0, 8.0]

# ==============================================================================
# 4. OPENROUTER API SETTINGS
# ==============================================================================
OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")


def get_model_id() -> str:
    """Returns the primary configured model ID."""
    return MODEL_ID


def get_fallback_models() -> list[str]:
    """Returns the configured list of fallback models."""
    return list(FALLBACK_MODELS)


def get_openrouter_model():
    """
    Creates and returns a resilient OpenRouterFallbackModel instance
    configured with fallback chain, exponential backoff, and logging
    for the Strands Agents SDK.
    Prioritizes OS environment variables, then falls back to .env if present.
    """
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key or api_key == "your_openrouter_api_key_here":
        try:
            from dotenv import load_dotenv
            load_dotenv()
            api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        except ImportError:
            pass

    if not api_key or api_key == "your_openrouter_api_key_here":
        raise ValueError(
            "OPENROUTER_API_KEY is not set. Please set the OPENROUTER_API_KEY environment variable "
            "or create a .env file based on .env.example."
        )

    try:
        from llm import OpenRouterFallbackModel
    except ImportError as e:
        raise ImportError(f"Failed to load OpenRouterFallbackModel from llm.py: {e}")

    return OpenRouterFallbackModel(
        model_id=os.getenv("MODEL_ID", MODEL_ID),
        fallback_models=FALLBACK_MODELS,
        retry_delays=RETRY_DELAYS,
        api_key=api_key,
        base_url=OPENROUTER_BASE_URL,
    )


def check_api_key_status() -> dict[str, Any]:
    """Inspects OS environment variables and .env file for OpenRouter key."""
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    source = "EC2 / OS Environment Variable" if (key and key != "your_openrouter_api_key_here") else "None"

    if not key or key == "your_openrouter_api_key_here":
        try:
            from dotenv import load_dotenv
            load_dotenv()
            key = os.getenv("OPENROUTER_API_KEY", "").strip()
            if key and key != "your_openrouter_api_key_here":
                source = ".env file"
        except ImportError:
            pass

    has_env_file = os.path.exists(".env")
    is_live = bool(key and key != "your_openrouter_api_key_here" and len(key) > 10)

    return {
        "is_live": is_live,
        "masked_key": (key[:9] + "••••••••" + key[-4:]) if is_live else "Not configured",
        "model_id": os.getenv("MODEL_ID", MODEL_ID),
        "source": source if is_live else ("None (Unset)" if not has_env_file else ".env file (placeholder)"),
        "has_env_file": has_env_file,
    }
