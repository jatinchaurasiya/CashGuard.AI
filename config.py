"""
CashGuard.AI - Configuration Module

This file holds all the core settings for the project in one place.
You can change settings here without having to edit any of the agent logic code.
"""

import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# ==============================================================================
# LLM MODEL CONFIGURATION
# ==============================================================================
# This is the single central place where the model ID is defined.
# If you want to switch to a different model (e.g., anthropic/claude-3.5-sonnet,
# openai/gpt-4o-mini, meta-llama/llama-3.3-70b-instruct, etc.), just change this string!
# It defaults to "openrouter/free" as requested.
DEFAULT_MODEL_ID: str = "openrouter/free"

# Allow overriding via environment variable MODEL_ID, otherwise use DEFAULT_MODEL_ID
MODEL_ID: str = os.getenv("MODEL_ID", DEFAULT_MODEL_ID)

# OpenRouter API settings
OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")


def get_model_id() -> str:
    """Returns the configured model ID."""
    return MODEL_ID


def get_openrouter_model():
    """
    Creates and returns an OpenAIModel instance configured to talk to OpenRouter
    using the Strands Agents SDK.
    """
    api_key = OPENROUTER_API_KEY
    if not api_key:
        raise ValueError(
            "OPENROUTER_API_KEY is not set. Please create a .env file based on .env.example "
            "and add your OpenRouter API key."
        )

    try:
        from strands.models.openai import OpenAIModel
    except ImportError:
        raise ImportError(
            "The 'strands-agents' package is not installed. "
            "Please run: pip install -r requirements.txt"
        )

    return OpenAIModel(
        model_id=MODEL_ID,
        client_args={
            "api_key": api_key,
            "base_url": OPENROUTER_BASE_URL,
        },
    )

