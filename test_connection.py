"""
CashGuard.AI - OpenRouter Connection & Fallback Test Script

Run this script to verify:
1. Your OpenRouter API key is recognized from .env.
2. The connection to OpenRouter (base_url: https://openrouter.ai/api/v1) is alive.
3. The fallback chain and exponential backoff are configured.
4. Which model actually served your test request.

Usage:
    python test_connection.py
"""

import sys
import time
from config import (
    OPENROUTER_BASE_URL,
    OPENROUTER_API_KEY,
    get_model_id,
    get_fallback_models,
    get_openrouter_model,
    RETRY_DELAYS,
)


def run_test():
    print("=" * 72)
    print(" 🛡️  CashGuard.AI — OpenRouter Connection & Resiliency Test")
    print("=" * 72)

    # 1. Display configuration
    primary_model = get_model_id()
    fallbacks = get_fallback_models()

    print(f"\n[1] Configuration Check:")
    print(f"    • API Base URL:       {OPENROUTER_BASE_URL}")
    print(f"    • Primary Model:      {primary_model}")
    print(f"    • Fallback Chain:     {fallbacks}")
    print(f"    • Backoff Delays:     {RETRY_DELAYS} seconds")

    # 2. Check API Key
    if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "your_openrouter_api_key_here":
        print("\n[!] Error: OPENROUTER_API_KEY is not set in your .env file.")
        print("\nHow to fix:")
        print("1. Open (or create) the `.env` file in the project folder.")
        print("2. Add your key from OpenRouter (https://openrouter.ai/keys):")
        print("   OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxx")
        print("3. Run this script again: python test_connection.py\n")
        sys.exit(1)

    masked_key = OPENROUTER_API_KEY[:8] + "..." + OPENROUTER_API_KEY[-4:] if len(OPENROUTER_API_KEY) > 12 else "***"
    print(f"    • OpenRouter API Key: {masked_key} (Found)")

    # 3. Initialize Model and Strands Agent
    print("\n[2] Initializing Strands Agent with OpenRouter fallback model...")
    try:
        model = get_openrouter_model()
    except Exception as err:
        print(f"[!] Initialization Error: {err}")
        sys.exit(1)

    from strands import Agent

    agent = Agent(
        model=model,
        system_prompt=(
            "You are CashGuard.AI, an intelligent cash-flow and invoice exception guardian for freelancers. "
            "Keep your responses concise, professional, and friendly."
        ),
    )

    # 4. Test Prompt
    test_prompt = (
        "Hello! Confirm in 2 short sentences that your LLM connection is working, "
        "and state how you help freelancers protect their cash flow."
    )

    print(f"\n[3] Sending test request to OpenRouter...")
    print(f"    • Prompt: \"{test_prompt}\"")
    print(f"    • Awaiting response...\n")

    start_time = time.time()
    try:
        response = agent(test_prompt)
        elapsed = time.time() - start_time

        # Retrieve the model that actually served the request
        served_model = getattr(model, "last_served_model", primary_model)

        print("-" * 72)
        print(" ✅ CONNECTION SUCCESSFUL!")
        print("-" * 72)
        print(f"• Model that served request: {served_model}")
        print(f"• Round-trip response time:  {elapsed:.2f} seconds")
        text_response = getattr(response, "text", None) or getattr(response, "content", None) or str(response)
        print(f"\"{text_response.strip()}\"")
        print("-" * 72)

        if served_model == primary_model:
            print("\nResult: Primary model responded directly without needing fallbacks.")
        else:
            print(f"\nResult: Fallback mechanism kicked in and was successfully handled by '{served_model}'.")

        print("Your OpenRouter and Strands Agents setup is ready for the hackathon!\n")

    except Exception as exc:
        elapsed = time.time() - start_time
        print("-" * 72)
        print(" ❌ CONNECTION FAILED")
        print("-" * 72)
        print(f"Error after {elapsed:.2f} seconds: {exc}")
        print("\nTroubleshooting tips:")
        print("• Check your internet connection.")
        print("• Verify that your OpenRouter API key has credits or is active at openrouter.ai/activity.")
        print("• Free tier models may occasionally be busy; retry in a few seconds.\n")
        sys.exit(1)


if __name__ == "__main__":
    run_test()
