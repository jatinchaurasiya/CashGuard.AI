"""
CashGuard.AI - Simulated WhatsApp Chat Interface (CLI)

Interactive terminal chat where:
1. The agent sends exception flags as WhatsApp chat messages.
2. The user can reply in plain text.
3. The agent interprets the instruction, drafts the next action, and asks for explicit approval before dispatching.
"""

import sys
import time
from tools.prioritizer import prioritize_cash_impact
from tools.approval_gate import human_approval_gate
from reasoning import CashGuardReasoningEngine
from audit_logger import MD_LOG_PATH

# Terminal colors for authentic WhatsApp aesthetic
GREEN = "\033[92m"
TEAL = "\033[96m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def print_whatsapp_header():
    print("\n" + "=" * 76)
    print(f" {GREEN}{BOLD}💬 WhatsApp Web — CashGuard AI Assistant 🛡️{RESET}")
    print(f" {DIM}Online • End-to-end Encrypted • Protecting Freelancer Cash Flow{RESET}")
    print("=" * 76)


def run_interactive_chat():
    print_whatsapp_header()

    engine = CashGuardReasoningEngine.create()
    print(f"\n{DIM}[+] Analyzing feeds and prioritizing exceptions...{RESET}")
    priorities = prioritize_cash_impact(as_of_date_str="2026-09-06")
    ranked = priorities.get("ranked_exceptions", [])

    if not ranked:
        print("No exceptions detected! Cash flow is healthy.")
        return

    print(f"{GREEN}[✓] Found {len(ranked)} prioritized exceptions requiring your input.{RESET}\n")

    for item in ranked:
        inv_id = item["invoice_id"]
        client = item["client_name"]
        score = item["impact_score"]
        tier = item["priority_tier"]

        print("-" * 76)
        print(f"{BOLD}[Case #{item['rank']}] {client} (Invoice #{inv_id}){RESET}")
        print(f"Tier: {YELLOW}{tier}{RESET} | Status: {item['status']} | Cash Impact Score: ${score:,.2f}")
        print("-" * 76)

        # Step 1: Agent sends WhatsApp alert
        time.sleep(0.5)
        alert_res = engine.write_whatsapp_alert(item)
        alert = alert_res.get("draft", {})
        alert_text = alert.get("content", "")

        print(f"\n{GREEN}{BOLD}CashGuard AI 🛡️ [WhatsApp]{RESET} {DIM}(Just now){RESET}:")
        print(f"  ┌{'─' * 70}┐")
        for line in alert_text.splitlines():
            print(f"  │ {line:<68} │")
        print(f"  └{'─' * 70}┘")

        # Step 2: User replies in plain text
        print(f"\n{TEAL}{BOLD}Priya (You) 👤 [WhatsApp]{RESET}:")
        try:
            user_reply = input("  > Type your reply (or press Enter for default): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting chat session.")
            sys.exit(0)

        if not user_reply:
            default_replies = {
                "INV-2026-004": "Acknowledge the milestone payment and confirm the remaining $1,500 will be approved after UAT.",
                "INV-2026-005": "Send a polite follow-up reminder asking if the finance committee approved the disbursement.",
                "INV-2026-007": "Do not refund! Tell Chef Mateo we only received one transfer and ask for their Chase trace numbers.",
                "INV-2026-009": "Let it go, $25 is fine to write off as an intermediary wire fee. Mark the invoice settled.",
            }
            user_reply = default_replies.get(inv_id, "Please follow up politely.")
            print(f"  {DIM}(Using response: \"{user_reply}\"){RESET}")

        # Step 3: Agent interprets and drafts action (NEVER sends yet)
        print(f"\n{DIM}[*] CashGuard AI is typing... interpreting your instruction...{RESET}")
        time.sleep(0.5)
        action_res = engine.interpret_reply_and_draft_action(item, user_reply)
        action = action_res.get("draft", {})
        draft_id = action.get("draft_id", "DFT-001")

        print(f"\n{GREEN}{BOLD}CashGuard AI 🛡️ [WhatsApp]{RESET}:")
        print(f"  I've prepared the following draft based on your instruction:")
        print(f"  ┌{'─' * 70}┐")
        print(f"  │ {BOLD}Draft ID:{RESET} {draft_id:<60} │")
        print(f"  │ {BOLD}Intent:{RESET}   {action.get('action_intent', 'N/A'):<60} │")
        print(f"  │ {BOLD}Subject:{RESET}  {action.get('subject', 'N/A'):<60} │")
        print(f"  ├{'─' * 70}┤")
        for line in action.get("content", "").splitlines():
            print(f"  │ {line:<68} │")
        print(f"  └{'─' * 70}┘")
        print(f"  {YELLOW}⚠️  STATUS: DRAFT STAGED — NOT SENT. Requires your explicit confirmation.{RESET}")

        # Step 4: Human-Approval Gate
        print(f"\n{BOLD}🛑 Human-Approval Gate:{RESET}")
        try:
            confirm = input(f"  Approve and dispatch this email to {client}? [Y/n]: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting chat session.")
            sys.exit(0)

        is_confirmed = confirm not in ("n", "no")
        notes = "Confirmed by Priya via WhatsApp CLI" if is_confirmed else "Rejected by Priya via WhatsApp CLI"

        gate_res = human_approval_gate(
            draft_id=draft_id,
            confirmed=is_confirmed,
            approved_by="Priya",
            human_notes=notes,
        )

        if is_confirmed:
            print(f"\n  {GREEN}✅ DISPATCH CONFIRMED!{RESET} Email to {client} marked sent. [✓✓ Blue Ticks]")
            print(f"  {DIM}Audit event appended to {MD_LOG_PATH}{RESET}\n")
        else:
            print(f"\n  {RED}❌ DISPATCH CANCELLED!{RESET} Action halted. Message was NOT sent.")
            print(f"  {DIM}Audit rejection appended to {MD_LOG_PATH}{RESET}\n")

    print("=" * 76)
    print(f" {GREEN}{BOLD}🎉 All exceptions reviewed! Permanent audit trail updated in {MD_LOG_PATH}{RESET}")
    print("=" * 76 + "\n")


if __name__ == "__main__":
    run_interactive_chat()
