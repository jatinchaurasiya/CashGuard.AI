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

    # 2. Initialize the Strands Agent with the Monitor, Matching, and Prioritizer Tools
    from strands import Agent
    from tools import (
        monitor_financial_feeds,
        match_invoices_to_bank_feed,
        prioritize_cash_impact,
    )

    guardian_agent = Agent(
        model=model,
        tools=[
            monitor_financial_feeds,
            match_invoices_to_bank_feed,
            prioritize_cash_impact,
        ],
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
1. Use your matching tool (`match_invoices_to_bank_feed`) to perform deterministic arithmetic and date matching.
2. Use your prioritization tool (`prioritize_cash_impact`) to rank all exceptions by Cash Impact Score: (amount) x (days overdue), surfacing highest impact first.
3. Maintain SILENCE on routine matches (MATCHED and PENDING) — do not overwhelm the freelancer with invoices that are already settled or within normal terms.
4. ESCALATE only the true judgment calls in the exact ranked order determined by the prioritizer:
   - [Rank #1 - CRITICAL]: Nexa Health Labs (milestone payment terms and balance).
   - [Rank #2 - CRITICAL]: BrightPath Academy (overdue board sign-off follow-up).
   - [Rank #3 - HIGH]: UrbanBite Chef Mateo duplicate payment claim (warn Priya NOT to refund!).
   - [Rank #4 - LOW]: Pulse Dynamics ($25 wire fee deduction analysis).
   - [UNMATCHED DEPOSIT]: Note the $350 mystery deposit from Stripe.
5. Provide an executive cash-flow health summary and draft ready-to-send email responses for Priya for each escalated case in ranked order.
"""
    else:
        # Fallback minimal scenario if data files are missing
        scenario = "Please provide an overview of your capabilities as CashGuard AI."

    print("\n[+] Analyzing freelancer data (Invoices, Bank Feed, Emails)...")
    print("[+] Querying Strands Agent...\n")

    try:
        response = guardian_agent(scenario)
        served_model = getattr(model, "last_served_model", get_model_id())
        print("-" * 70)
        print(f" GUARDIAN RECONCILIATION REPORT (Served by: {served_model})")
        print("-" * 70)
        print(response)
        print("-" * 70)
    except Exception as e:
        print(f"\n[!] Error during agent execution: {e}")
        print("Please check your internet connection and verify that your OpenRouter API key is valid.")


if __name__ == "__main__":
    run_sample_guardian()
