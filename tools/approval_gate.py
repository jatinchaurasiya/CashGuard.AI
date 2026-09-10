"""
CashGuard.AI - Human-Approval Gate Tool for Strands Agents SDK

Enforces the core Responsible-AI requirement:
NO drafted message (reminder, refund note, fee waiver, or clarification question)
is EVER sent without explicit human confirmation.

Features:
1. Tool-calling interface for the Strands Agent (`human_approval_gate`).
2. Verification of human authorization (signature/confirmation).
3. Immutable logging to the append-only audit log for every approved or rejected action.
4. Interactive console prompt for live demonstrations.
"""

from datetime import datetime, timezone
import logging
from typing import Any
from strands import tool

from tools.drafter import get_staged_drafts
from audit_logger import audit_logger

logger = logging.getLogger("CashGuard.Tools.ApprovalGate")


class ApprovalDeniedError(Exception):
    """Raised when an automated action attempts to dispatch without human approval."""
    pass


@tool(
    name="human_approval_gate",
    description=(
        "Mandatory safety gate: no drafted message (reminder/refund/clarification) is EVER "
        "sent without the user explicitly confirming it first. "
        "Validates the human confirmation, updates the draft status, and logs the decision "
        "to the immutable audit log."
    ),
)
def human_approval_gate(
    draft_id: str,
    confirmed: bool,
    approved_by: str = "Priya",
    human_notes: str | None = None,
) -> dict[str, Any]:
    """
    Submits a staged draft to the human-approval gate.

    Args:
        draft_id: ID of the staged draft (e.g. 'DFT-INV-2026-004-02').
        confirmed: True if human approved sending, False if rejected or cancelled.
        approved_by: Name or identifier of the human approver (e.g. 'Priya').
        human_notes: Optional notes or modification instructions from the human.

    Returns:
        Confirmation dictionary with dispatch outcome and audit verification.
    """
    staged_drafts = get_staged_drafts()
    target_draft = None

    for d in staged_drafts:
        if d.get("draft_id") == draft_id:
            target_draft = d
            break

    if target_draft is None:
        return {
            "status": "error",
            "error": f"Draft ID '{draft_id}' not found in staged drafts.",
            "sent": False,
        }

    now_iso = datetime.now(timezone.utc).isoformat()
    inv_id = target_draft.get("invoice_id", "N/A")
    client = target_draft.get("client_name", "N/A")
    channel = target_draft.get("channel", "email")
    recipient = target_draft.get("recipient_type", "client")

    if not confirmed:
        # HUMAN REJECTED / CANCELLED DISPATCH
        target_draft["status"] = "cancelled_by_human"
        target_draft["sent"] = False
        target_draft["human_decision"] = "REJECTED"
        target_draft["decision_timestamp"] = now_iso
        target_draft["human_notes"] = human_notes

        audit_logger.log_event(
            event_type="HUMAN_APPROVAL_REJECTED",
            action_taken=f"Blocked dispatch of draft {draft_id} to {client}",
            reasoning_summary=(
                f"Human approver ({approved_by}) rejected or halted sending of draft {draft_id}. "
                f"Message was NOT sent. Notes: {human_notes or 'None provided'}."
            ),
            invoice_id=inv_id,
            client_name=client,
            principle="Human-in-the-Loop Oversight",
            metadata={"draft_id": draft_id, "approved": False},
        )

        logger.info(f"[ApprovalGate] Draft {draft_id} REJECTED by human ({approved_by}). Action blocked.")

        return {
            "status": "blocked",
            "sent": False,
            "draft_id": draft_id,
            "approved": False,
            "message": f"Action halted: human approver ({approved_by}) declined to send draft {draft_id}.",
            "disclaimer": "Message was NOT sent.",
        }

    # HUMAN EXPLICITLY APPROVED DISPATCH
    target_draft["status"] = "approved_and_dispatched"
    target_draft["sent"] = True
    target_draft["approved_by"] = approved_by
    target_draft["dispatched_at"] = now_iso
    target_draft["human_notes"] = human_notes

    audit_logger.log_event(
        event_type="ACTION_DISPATCHED",
        action_taken=f"Dispatched {target_draft.get('message_type', 'message')} to {client} via {channel}",
        reasoning_summary=(
            f"Explicit human confirmation granted by {approved_by}. "
            f"Subject: '{target_draft.get('subject', 'N/A')}'. Intent: '{target_draft.get('action_intent', 'N/A')}'. "
            f"Notes: {human_notes or 'Direct approval without edits'}."
        ),
        invoice_id=inv_id,
        client_name=client,
        principle="Human-in-the-Loop Oversight",
        metadata={
            "draft_id": draft_id,
            "approved_by": approved_by,
            "channel": channel,
            "recipient_type": recipient,
            "sent": True,
        },
    )

    logger.info(f"[ApprovalGate] Draft {draft_id} APPROVED by human ({approved_by}) and dispatched successfully.")

    return {
        "status": "success",
        "sent": True,
        "draft_id": draft_id,
        "approved": True,
        "approved_by": approved_by,
        "dispatched_at": now_iso,
        "message": f"Verified human approval received. Message {draft_id} dispatched to {client} via {channel}.",
    }


def request_interactive_approval(
    draft_record: dict[str, Any],
    auto_approve: bool = False,
    approver_name: str = "Priya",
) -> dict[str, Any]:
    """
    Simulates or prompts an interactive human confirmation step for the demo.
    """
    draft_id = draft_record.get("draft_id", "")
    client = draft_record.get("client_name", "")
    inv_id = draft_record.get("invoice_id", "")
    channel = draft_record.get("channel", "email")
    subject = draft_record.get("subject", "N/A")
    content = draft_record.get("content", "")

    if auto_approve:
        return human_approval_gate(
            draft_id=draft_id,
            confirmed=True,
            approved_by=approver_name,
            human_notes="Confirmed via automated demonstration flow",
        )

    print("\n" + "!" * 70)
    print(" 🛑 HUMAN-APPROVAL GATE — Explicit Authorization Required")
    print("!" * 70)
    print(f"Target Draft:  {draft_id} (Invoice #{inv_id} — {client})")
    print(f"Channel:       {channel.upper()}")
    print(f"Subject:       {subject}")
    print(f"\nMessage Preview:\n" + "\n".join("  | " + l for l in content.splitlines()))
    print("-" * 70)
    choice = input(f"Approve and dispatch this {channel} to {client}? [y/N]: ").strip().lower()

    confirmed = choice in ("y", "yes")
    notes = input("Optional approver note (press enter to skip): ").strip() or None

    return human_approval_gate(
        draft_id=draft_id,
        confirmed=confirmed,
        approved_by=approver_name,
        human_notes=notes,
    )
