"""
CashGuard.AI - Invoice Exception & Cash-Flow Guardian
AWS 'Agents for Humans' Hackathon (Professional Agents Track)

This is the main entry point for the agent. It initializes the Strands Agent
using the OpenRouter model specified in config.py and runs a sample invoice reconciliation.
"""

import sys
from config import get_openrouter_model, get_model_id

# System prompt defining the agent's persona and objective
# System prompt defining the agent's persona and objective
CASHGUARD_SYSTEM_PROMPT = """
You are CashGuard, an intelligent AI Cash-Flow Guardian built for solo freelancers.
Your mission is to protect the freelancer's cash flow by reconciling their issued invoices
against bank transactions and client email communications.

Your Workflow & Tool-Calling Protocol:
1. Reconcile & Prioritize:
   - Use `match_invoices_to_bank_feed` to find discrepancies.
   - Maintain silence on routine matches (`MATCHED` and `PENDING`).
   - Use `prioritize_cash_impact` to rank actionable exceptions (`PARTIAL`, `UNMATCHED`, `DUPLICATE_CLAIM`) by (amount) x (days overdue).

2. WhatsApp-Style Alerts for Freelancer:
   - For each prioritized exception, use the `draft_message` tool with:
     recipient_type="freelancer", channel="whatsapp", message_type="alert"
   - Write a short, plain-language message describing the situation and asking what they would like to do.
     Example: "Client X's payment is $50 short of Invoice #12 — could be a bank fee or a partial payment. What would you like to do?"

3. Interpret User Reply & Stage Next Action:
   - When the freelancer replies with a natural-language instruction (e.g. "send a reminder", "let it go", "ask for the missing $50", "refuse refund until Chase clears it"):
     - Accurately interpret their intent.
     - Call `draft_message` with:
       recipient_type="client", channel="email", action_intent=<user_instruction>
     - Draft the professional action text (e.g. reminder email, fee waiver note, polite clarification question, refund refusal warning).
     - NEVER send the message; strictly stage it as a draft for the freelancer's review.

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

    # 2. Initialize the Strands Agent with the Monitor, Matching, Prioritizer, and Drafter Tools
    from strands import Agent
    from tools import (
        monitor_financial_feeds,
        match_invoices_to_bank_feed,
        prioritize_cash_impact,
        draft_message,
        get_staged_drafts,
    )
    from reasoning import CashGuardReasoningEngine

    guardian_agent = Agent(
        model=model,
        tools=[
            monitor_financial_feeds,
            match_invoices_to_bank_feed,
            prioritize_cash_impact,
            draft_message,
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
        print(f"\n[!] Note on agent full prompt run: {e}")

    # 4. Demonstrate the 3-Step WhatsApp Alert & Tool-Called Action Drafting Loop
    demonstrate_reasoning_flow()


def demonstrate_reasoning_flow():
    """
    Demonstrates the 3-step OpenRouter-backed reasoning flow on prioritized exceptions:
    1. Plain-language WhatsApp alert for freelancer.
    2. Freelancer natural language response.
    3. Structured client action drafting via draft_message tool (staged, not sent).
    """
    from tools.prioritizer import prioritize_cash_impact
    from tools.drafter import get_staged_drafts, clear_staged_drafts
    from reasoning import CashGuardReasoningEngine

    print("\n" + "=" * 70)
    print(" 💬 CASHGUARD REASONING LAYER — WHATSAPP ALERTS & ACTION DRAFTS")
    print("=" * 70)

    clear_staged_drafts()
    engine = CashGuardReasoningEngine.create()
    priorities = prioritize_cash_impact(as_of_date_str="2026-09-06")
    ranked = priorities.get("ranked_exceptions", [])

    sample_replies = {
        "INV-2026-004": "Acknowledge the milestone payment and confirm the remaining $1,500 will be approved after UAT.",
        "INV-2026-005": "Send a polite follow-up reminder asking if the finance committee approved the disbursement.",
        "INV-2026-007": "Do not refund! Tell Chef Mateo we only received one transfer and ask for their Chase trace numbers.",
        "INV-2026-009": "Let it go, $25 is fine to write off as an intermediary wire fee. Mark the invoice settled.",
    }

    for item in ranked:
        inv_id = item["invoice_id"]
        client = item["client_name"]
        print(f"\n[Rank #{item['rank']} | {item['priority_tier']}] Invoice {inv_id} — {client}")
        print(f"Impact Score: ${item['impact_score']:,.2f} | Status: {item['status']}")

        # Step 1: Plain-language WhatsApp alert
        alert_res = engine.write_whatsapp_alert(item)
        alert = alert_res.get("draft", {})
        print(f"\n📱 WhatsApp Alert to Priya (Staged Draft {alert.get('draft_id')}):")
        print(f"   \"{alert.get('content')}\"")

        # Step 2: Freelancer natural-language instruction
        user_reply = sample_replies.get(inv_id, "Send a polite reminder.")
        print(f"\n👤 Priya's Reply via WhatsApp:")
        print(f"   \"{user_reply}\"")

        # Step 3: Interpreted instruction & staged draft action
        action_res = engine.interpret_reply_and_draft_action(item, user_reply)
        action = action_res.get("draft", {})
        print(f"\n✉️  Drafted Action to Client (Staged Draft {action.get('draft_id')} | Sent: {action.get('sent')}):")
        print(f"   Action Intent: {action.get('action_intent')}")
        print(f"   Subject:       {action.get('subject')}")
        print(f"   Body:\n" + "\n".join("      " + line for line in action.get('content', '').splitlines()))
        print("-" * 70)

    staged = get_staged_drafts()
    print(f"\n[+] Total Staged Drafts in Memory: {len(staged)} (All marked sent: False)")
    print("=" * 70)


if __name__ == "__main__":
    run_sample_guardian()
