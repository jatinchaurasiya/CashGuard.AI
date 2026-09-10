"""
CashGuard.AI - Reasoning Layer for Strands Agent SDK & OpenRouter

Orchestrates the 3-step reasoning loop for each prioritized exception:
1. Generates a short, plain-language WhatsApp-style message describing the exception
   to the freelancer (e.g. "Client X's payment is $50 short of Invoice #12 — could be
   a bank fee or a partial payment. What would you like to do?").
2. Interprets the freelancer's natural language reply (e.g. "send a reminder",
   "let it go", "ask for the missing $50", "refuse refund until bank confirms").
3. Calls the structured `draft_message` tool to stage the next action (reminder email,
   fee waiver note, clarification question, refund refusal) as text — NEVER sending it.
"""

import json
import logging
from typing import Any

from config import get_openrouter_model, get_model_id, OPENROUTER_API_KEY
from tools.drafter import draft_message, get_staged_drafts, clear_staged_drafts

logger = logging.getLogger("CashGuard.Reasoning")

REASONING_SYSTEM_PROMPT = """
You are CashGuard's Reasoning Engine, acting on behalf of solo freelancer Priya.
Your role is to handle invoice exceptions through structured tool calling.

You have access to the `draft_message` tool with the following parameters:
- invoice_id: str
- client_name: str
- content: str (the text body)
- recipient_type: 'freelancer' (for WhatsApp alerts to Priya) or 'client' (for drafted actions)
- channel: 'whatsapp' or 'email'
- message_type: 'alert', 'client_reminder', 'refund_note', 'clarification', 'fee_waiver'
- subject: str (subject line if channel='email')
- action_intent: str (interpreted instruction from the freelancer)

RULES:
1. When alerting the freelancer (recipient_type='freelancer', channel='whatsapp'):
   - Keep it short, conversational, and direct.
   - Summarize the dollar amount, invoice number, and key context.
   - End with a clear question asking what they want to do.
   - Example: "Hey Priya, Pulse Dynamics sent $3,075 for Invoice #INV-2026-009 ($3,100). Looks like a $25 wire fee was deducted. Should we write off the $25 fee or ask them to cover it?"

2. When interpreting the freelancer's reply and drafting a client action (recipient_type='client', channel='email'):
   - Accurately translate their natural language instruction (e.g. 'let it go', 'remind them', 'ask for the missing $50', 'do not refund').
   - Draft a polite, professional, ready-to-send email.
   - CRITICAL: Never claim the email was sent. Always stage it as a draft.
"""


def _generate_fallback_alert(exception: dict[str, Any]) -> dict[str, Any]:
    """Deterministic template fallback for WhatsApp alert if LLM is offline."""
    inv_id = exception.get("invoice_id", "")
    client = exception.get("client_name", "")
    amt = float(exception.get("amount", 0.0))
    status = exception.get("status", "")
    diff = float(exception.get("difference", 0.0))
    days = int(exception.get("days_overdue", 0))

    if status == "PARTIAL":
        if diff <= 50.0:
            text = (
                f"Hey Priya! {client}'s payment for Invoice #{inv_id} came in at ${amt - diff:,.2f}, "
                f"which is ${diff:,.2f} short of the ${amt:,.2f} total. This looks like an intermediary bank wire fee. "
                f"Would you like to write off the ${diff:,.2f} fee and mark it settled, or ask them for the remainder?"
            )
        else:
            text = (
                f"Hey Priya! {client} deposited a partial payment of ${amt - diff:,.2f} for Invoice #{inv_id} "
                f"(balance remaining: ${diff:,.2f}). Their email mentions Milestone 2 approval wraps up soon. "
                f"What would you like to do — send a reminder for the milestone balance or wait until the approval date?"
            )
    elif status == "UNMATCHED":
        text = (
            f"Hey Priya! Invoice #{inv_id} for {client} (${amt:,.2f}) is now {days} days overdue with no payment in the bank feed. "
            f"Their director previously mentioned an autumn board meeting sign-off. "
            f"Should I draft a polite follow-up reminder to check on the disbursement?"
        )
    elif status == "DUPLICATE_CLAIM":
        text = (
            f"⚠️ Heads up Priya! {client} sent an urgent email claiming they accidentally made two transfers of ${amt:,.2f} for Invoice #{inv_id} "
            f"and asked for an immediate ${amt:,.2f} refund. However, your bank statement shows ONLY ONE deposit! "
            f"I strongly recommend NOT refunding. Should I draft a response asking them to check their Chase trace reference?"
        )
    else:
        text = (
            f"Hey Priya! Discrepancy noted on Invoice #{inv_id} for {client} (${amt:,.2f}). "
            f"How would you like to proceed?"
        )

    return draft_message(
        invoice_id=inv_id,
        client_name=client,
        content=text,
        recipient_type="freelancer",
        channel="whatsapp",
        message_type="alert",
    )


def _generate_fallback_draft(exception: dict[str, Any], user_reply: str) -> dict[str, Any]:
    """Deterministic template fallback for client draft if LLM is offline."""
    inv_id = exception.get("invoice_id", "")
    client = exception.get("client_name", "")
    amt = float(exception.get("amount", 0.0))
    diff = float(exception.get("difference", 0.0))
    reply_lower = user_reply.lower()
    status = exception.get("status", "")

    contact_name = exception.get("sender_name")
    if not contact_name:
        if "UrbanBite" in client:
            contact_name = "Chef Mateo"
        elif "Nexa" in client:
            contact_name = "Dr. Elena"
        elif "BrightPath" in client:
            contact_name = "Arthur"

    greeting = f"Hi {contact_name}" if contact_name else f"Hi {client} team"

    if "let it go" in reply_lower or "write off" in reply_lower or "waive" in reply_lower:
        subject = f"Payment Received & Settled - Invoice #{inv_id}"
        content = (
            f"{greeting},\n\n"
            f"Confirming safe receipt of your wire transfer of ${amt - diff:,.2f} for Invoice #{inv_id}. "
            f"We noted the $25 intermediary wire transfer fee deduction and have marked the invoice fully settled on our end.\n\n"
            f"Thank you for your partnership!\n\nBest regards,\nPriya"
        )
        msg_type = "fee_waiver"
        intent = "write off fee and mark settled"
    elif status == "DUPLICATE_CLAIM" or "refund" in reply_lower or "duplicate" in reply_lower or "trace" in reply_lower or "do not refund" in reply_lower:
        subject = f"RE: Inquiry Regarding Invoice #{inv_id} Transfer"
        content = (
            f"{greeting},\n\n"
            f"Thank you for reaching out. I reviewed my business checking statement this morning, and currently only one transfer "
            f"of ${amt:,.2f} for Invoice #{inv_id} has settled on my end.\n\n"
            f"Could you please ask your accounts team for the bank wire/transfer trace numbers for both transactions? "
            f"Once my bank verifies a second credit, I will promptly process any excess funds.\n\n"
            f"Best regards,\nPriya"
        )
        msg_type = "refund_note"
        intent = "refuse refund until second transfer is confirmed with bank trace"
    elif status == "PARTIAL" or "milestone" in reply_lower or "balance" in reply_lower or "uat" in reply_lower:
        subject = f"Invoice #{inv_id} - Milestone 1 Acknowledgment & Phase 2 Timeline"
        content = (
            f"Hi {client} team,\n\n"
            f"Thank you for releasing the initial milestone payment of ${amt - diff:,.2f} for Invoice #{inv_id}. "
            f"Confirming that the remaining balance of ${diff:,.2f} is scheduled for approval following user acceptance testing on Sept 18th.\n\n"
            f"Please let me know if your team needs any additional assets ahead of UAT sign-off.\n\n"
            f"Warm regards,\nPriya"
        )
        msg_type = "clarification"
        intent = "acknowledge partial payment and confirm milestone timeline"
    else:
        subject = f"Friendly Follow-up: Invoice #{inv_id}"
        content = (
            f"Dear {client} team,\n\n"
            f"I hope you are having a wonderful week. Following up regarding Invoice #{inv_id} (${amt:,.2f}) for the project deliverables. "
            f"Could you kindly confirm if the payment has been processed or scheduled?\n\n"
            f"Please let me know if you need any additional information or another copy of the invoice.\n\n"
            f"Thank you,\nPriya"
        )
        msg_type = "client_reminder"
        intent = "send polite follow-up on overdue payment"

    return draft_message(
        invoice_id=inv_id,
        client_name=client,
        content=content,
        recipient_type="client",
        channel="email",
        message_type=msg_type,
        subject=subject,
        action_intent=intent,
    )


class CashGuardReasoningEngine:
    """
    Reasoning layer connecting OpenRouter model intelligence with Strands tool-calling
    to triage invoice exceptions and draft client actions.
    """

    def __init__(self, agent: Any = None):
        self.agent = agent

    @classmethod
    def create(cls) -> "CashGuardReasoningEngine":
        """Factory method to initialize with Strands agent if credentials exist."""
        agent = None
        if OPENROUTER_API_KEY and OPENROUTER_API_KEY != "your_openrouter_api_key_here":
            try:
                from strands import Agent
                model = get_openrouter_model()
                agent = Agent(
                    model=model,
                    tools=[draft_message],
                    system_prompt=REASONING_SYSTEM_PROMPT,
                )
                logger.info("[ReasoningEngine] Strands Agent initialized with OpenRouter model.")
            except Exception as e:
                logger.warning(f"[ReasoningEngine] Could not initialize live agent ({e}); fallback active.")
        return cls(agent=agent)

    def write_whatsapp_alert(self, exception: dict[str, Any]) -> dict[str, Any]:
        """
        Step 1: Writes a short, plain-language WhatsApp-style alert for the freelancer
        describing the exception and asking for instruction.
        """
        inv_id = exception.get("invoice_id", "")
        client = exception.get("client_name", "")
        amount = exception.get("amount", 0.0)
        status = exception.get("status", "")
        explanation = exception.get("explanation", "")
        days_overdue = exception.get("days_overdue", 0)

        prompt = f"""
Freelancer: Priya
Invoice ID: {inv_id}
Client: {client}
Status: {status}
Amount: ${amount:,.2f}
Days Overdue: {days_overdue}
Context & Details: {explanation}

TASK:
Call the `draft_message` tool to create a short, plain-language WhatsApp-style message
alerting Priya to this exception. Summarize the dollar amount and key context concisely,
and ask what she would like to do.
Set recipient_type='freelancer', channel='whatsapp', and message_type='alert'.
"""
        if self.agent is not None:
            try:
                self.agent(prompt)
                # Retrieve the newly created draft from staged storage
                drafts = get_staged_drafts()
                for d in reversed(drafts):
                    if d["invoice_id"] == inv_id and d["recipient_type"] == "freelancer":
                        return {"status": "success", "draft": d}
            except Exception as err:
                logger.warning(f"[ReasoningEngine] Agent tool call failed ({err}), falling back to deterministic template.")

        # Fallback deterministic alert if agent is offline or tool was not called
        return _generate_fallback_alert(exception)

    def interpret_reply_and_draft_action(
        self,
        exception: dict[str, Any],
        user_reply: str,
    ) -> dict[str, Any]:
        """
        Steps 2 & 3: Interprets the freelancer's natural language reply as an instruction,
        then calls the `draft_message` tool to draft the next client action (email/note).
        Does NOT send anything.
        """
        inv_id = exception.get("invoice_id", "")
        client = exception.get("client_name", "")
        amount = exception.get("amount", 0.0)
        explanation = exception.get("explanation", "")

        prompt = f"""
Invoice ID: {inv_id}
Client: {client}
Amount: ${amount:,.2f}
Background: {explanation}

The freelancer Priya replied with the following natural language instruction:
"{user_reply}"

TASK:
1. Interpret Priya's instruction (e.g. 'send reminder', 'let it go', 'ask for missing $50', 'refuse refund until verified').
2. Call the `draft_message` tool to draft the next client action:
   - recipient_type='client'
   - channel='email'
   - subject: appropriate email subject line
   - content: complete, polite, professional email body ready for Priya's review
   - action_intent: concise summary of the interpreted instruction
CRITICAL: Do NOT send the message. Only stage it with `draft_message`.
"""
        if self.agent is not None:
            try:
                self.agent(prompt)
                drafts = get_staged_drafts()
                for d in reversed(drafts):
                    if d["invoice_id"] == inv_id and d["recipient_type"] == "client":
                        return {"status": "success", "draft": d}
            except Exception as err:
                logger.warning(f"[ReasoningEngine] Agent action call failed ({err}), falling back to deterministic template.")

        # Fallback deterministic draft
        return _generate_fallback_draft(exception, user_reply)
