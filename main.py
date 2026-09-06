"""
CashGuard.AI - Invoice Exception & Cash-Flow Guardian
AWS 'Agents for Humans' Hackathon (Professional Agents Track)

This is the main entry point for the agent. It initializes the Strands Agent
using the OpenRouter model specified in config.py and runs a sample invoice reconciliation.
"""

import sys
from config import get_openrouter_model, get_model_id

# System prompt defining the agent's persona and objective
CASHGUARD_SYSTEM_PROMPT = """
You are CashGuard, an intelligent AI Cash-Flow Guardian built for solo freelancers.
Your mission is to protect the freelancer's cash flow by reconciling their issued invoices
against bank transactions and client email communications.

Your responsibilities:
1. Identify Invoice Exceptions:
   - Invoices that are past due without payment.
   - Partial payments (e.g., invoiced $2,500, but only $2,000 received).
   - Unmatched bank deposits (money received without a clear invoice).
   - Invoices where the client emailed an explanation, promise date, or dispute.

2. Provide Clear, Actionable Recommendations:
   - Status summary (Paid in Full, Pending, Discrepancy, Overdue).
   - Recommended next step (e.g., send polite reminder, reconcile partial payment, follow up on promise date).
   - A friendly, ready-to-send draft email or message for the client if action is needed.

Always communicate with clarity, empathy, and professional precision.
"""


def run_sample_guardian():
    """Runs a demonstration reconciliation using the CashGuard agent."""
    print("=" * 70)
    print(" CashGuard.AI - Invoice Exception & Cash-Flow Guardian")
    print(f" Powered by Strands Agents SDK & OpenRouter (Model: {get_model_id()})")
    print("=" * 70)

    # 1. Initialize the OpenRouter model from config.py
    try:
        model = get_openrouter_model()
    except ValueError as err:
        print(f"\n[!] Configuration Error: {err}")
        print("\nQuick Setup Guide:")
        print("1. Copy `.env.example` to `.env`:")
        print("   cp .env.example .env")
        print("2. Open `.env` and paste your OpenRouter API key.")
        print("3. Run this script again: python main.py\n")
        sys.exit(1)

    # 2. Initialize the Strands Agent
    from strands import Agent

    guardian_agent = Agent(
        model=model,
        system_prompt=CASHGUARD_SYSTEM_PROMPT,
    )

    # 3. Load synthetic datasets from the data/ directory
    import json
    from pathlib import Path

    data_dir = Path(__file__).parent / "data"
    invoices_file = data_dir / "invoices.json"
    bank_feed_file = data_dir / "bank_feed.csv"
    emails_file = data_dir / "client_emails.json"

    if invoices_file.exists() and bank_feed_file.exists() and emails_file.exists():
        with open(invoices_file, "r") as f:
            invoices_data = json.load(f)
        with open(bank_feed_file, "r") as f:
            bank_feed_data = f.read()
        with open(emails_file, "r") as f:
            emails_data = json.load(f)

        print(f"\n[+] Loaded {len(invoices_data)} invoices from data/invoices.json")
        print(f"[+] Loaded bank feed transactions from data/bank_feed.csv")
        print(f"[+] Loaded {len(emails_data)} client emails from data/client_emails.json")

        scenario = f"""
Freelancer: Priya (Freelance Brand & Graphic Designer)
Today's Date: September 6, 2026

Please reconcile the following freelancer data across Invoices, Bank Feed, and Client Emails:

=== 1. ISSUED INVOICES ===
{json.dumps(invoices_data, indent=2)}

=== 2. BANK TRANSACTIONS (CSV) ===
{bank_feed_data}

=== 3. CLIENT COMMUNICATIONS & EMAILS ===
{json.dumps(emails_data, indent=2)}

---
YOUR INSTRUCTIONS:
1. Reconcile each invoice with the bank feed and client emails.
2. Flag all exceptions:
   - Identify which invoice was only partially paid and explain why based on emails.
   - Identify the overdue invoice with no matching deposit and explain the client's extension request.
   - Investigate the client claiming a duplicate payment and determine if the bank feed actually shows two payments or only one.
   - Flag any fee discrepancies (e.g. wire fee deduction) or unmatched deposits.
   - Ignore unrelated personal/business expenses (rent, groceries, SaaS subscriptions).
3. Provide an executive cash-flow health summary (total outstanding, expected incoming).
4. Draft ready-to-send email responses for Priya to send to clients with exceptions.
"""
    else:
        # Fallback minimal scenario if data files are missing
        scenario = "Please provide an overview of your capabilities as CashGuard AI."

    print("\n[+] Analyzing freelancer data (Invoices, Bank Feed, Emails)...")
    print("[+] Querying Strands Agent...\n")

    try:
        response = guardian_agent(scenario)
        print("-" * 70)
        print(" GUARDIAN RECONCILIATION REPORT")
        print("-" * 70)
        print(response)
        print("-" * 70)
    except Exception as e:
        print(f"\n[!] Error during agent execution: {e}")
        print("Please check your internet connection and verify that your OpenRouter API key is valid.")


if __name__ == "__main__":
    run_sample_guardian()
