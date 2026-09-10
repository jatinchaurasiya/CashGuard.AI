"""
CashGuard.AI - Draft Message Tool for Strands Agents SDK

Provides structured tool-calling for the agent's reasoning layer:
1. Plain-language WhatsApp-style alerts for the freelancer describing exceptions and asking for direction.
2. Drafted client actions (reminders, refund explanations, fee waivers, clarification requests)
   based on natural language user instructions.

CRITICAL GUARANTEE:
This tool creates, formats, and stages drafts as text. It NEVER sends messages automatically.
All drafts remain in 'draft_created' state until explicitly dispatched by the user.
"""

import logging
from typing import Any
from strands import tool

logger = logging.getLogger("CashGuard.Tools.Drafter")

# In-memory staging repository for drafted messages
_STAGED_DRAFTS: list[dict[str, Any]] = []


def get_staged_drafts() -> list[dict[str, Any]]:
    """Returns a copy of all staged drafts in the current session."""
    return list(_STAGED_DRAFTS)


def clear_staged_drafts() -> None:
    """Clears all staged drafts (used primarily in test suites)."""
    _STAGED_DRAFTS.clear()


@tool(
    name="draft_message",
    description=(
        "Drafts a structured message for an invoice exception. "
        "Use this tool to: "
        "1) Create a short, plain-language WhatsApp-style alert for the freelancer describing "
        "   an exception and asking for instruction (recipient_type='freelancer', channel='whatsapp'). "
        "2) Once the user provides instruction, draft the next action (reminder email, refund refusal, "
        "   clarification request) to the client (recipient_type='client', channel='email'). "
        "NOTE: This tool strictly formats and stages the draft. It DOES NOT send anything."
    ),
)
def draft_message(
    invoice_id: str,
    client_name: str,
    content: str,
    recipient_type: str = "freelancer",
    channel: str = "whatsapp",
    message_type: str = "alert",
    subject: str | None = None,
    action_intent: str | None = None,
) -> dict[str, Any]:
    """
    Creates and stages a structured message draft without sending.

    Args:
        invoice_id: The ID of the related invoice (e.g. 'INV-2026-004').
        client_name: Name of the client company or individual.
        content: The text of the WhatsApp message or email body.
        recipient_type: 'freelancer' (for WhatsApp alerts to Priya) or 'client' (for drafted actions).
        channel: 'whatsapp' or 'email'.
        message_type: 'alert', 'client_reminder', 'refund_note', 'clarification', 'fee_waiver', etc.
        subject: Email subject line (required or recommended if channel='email').
        action_intent: The interpreted natural language instruction from the user.

    Returns:
        Structured dictionary confirming draft creation, containing draft_id, content, and 'sent': False.
    """
    draft_index = len(_STAGED_DRAFTS) + 1
    draft_id = f"DFT-{invoice_id.replace(' ', '-')}-{draft_index:02d}"

    draft_record = {
        "draft_id": draft_id,
        "invoice_id": str(invoice_id).strip(),
        "client_name": str(client_name).strip(),
        "recipient_type": recipient_type.lower(),
        "channel": channel.lower(),
        "message_type": message_type.lower(),
        "subject": subject.strip() if subject else None,
        "content": content.strip(),
        "action_intent": action_intent.strip() if action_intent else None,
        "status": "draft_created",
        "sent": False,  # Explicit safety flag: NEVER send automatically
        "staged": True,
        "disclaimer": "STAGED DRAFT ONLY. This message has NOT been sent to the client.",
    }

    _STAGED_DRAFTS.append(draft_record)

    from audit_logger import audit_logger

    audit_logger.log_event(
        event_type="DRAFT_STAGED",
        action_taken=f"Created {recipient_type} {channel} draft {draft_id}",
        reasoning_summary=(
            f"Staged {message_type} draft for {invoice_id} ({client_name}). "
            f"Action intent: '{action_intent or 'Alert to freelancer'}'. "
            f"Safety enforcement: Message staged as text only; NEVER sent automatically."
        ),
        invoice_id=invoice_id,
        client_name=client_name,
        principle="Human-in-the-Loop Oversight & Safety",
        metadata={"draft_id": draft_id, "sent": False, "channel": channel},
    )

    logger.info(
        f"[DraftTool] Staged {draft_record['recipient_type']} draft {draft_id} via {draft_record['channel']} "
        f"for {invoice_id} ({client_name}). [Sent: False]"
    )

    return {
        "status": "success",
        "message": f"Draft {draft_id} successfully created and staged. Message was NOT sent.",
        "draft": draft_record,
    }
