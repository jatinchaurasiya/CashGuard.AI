"""
CashGuard.AI - Deterministic Invoice & Bank Feed Matching Tool

This tool matches bank transactions against invoices using clear, testable arithmetic,
date proximity, and reference text analysis.

Classification for each invoice:
- MATCHED: High-confidence exact match (resolved silently, no escalation).
- PARTIAL: Payment found, but amount is less than invoiced (or has fee deduction).
- UNMATCHED: Invoice is past due and no matching payment has been seen.
- DUPLICATE_CLAIM: Client email claims payment was sent/duplicated, but matching bank
                   transaction is missing or only 1 transfer exists instead of 2.
- PENDING: Invoice is not yet due and awaiting standard payment terms (silent).

Routine matches are resolved silently so the LLM agent saves its reasoning for
genuinely ambiguous cases.
"""

from datetime import datetime, date
import re
import logging
from typing import Any
from strands import tool

from .monitor import monitor_financial_feeds
from audit_logger import audit_logger

logger = logging.getLogger("CashGuard.Tools.Matcher")

DEFAULT_AS_OF_DATE = "2026-09-06"


def _parse_date(date_str: str) -> date | None:
    """Safely parse an ISO date string (YYYY-MM-DD)."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def _clean_text(text: str) -> str:
    """Removes punctuation and normalizes text for clean substring matching."""
    return re.sub(r"[^a-zA-Z0-9]", "", text.lower()) if text else ""


def _has_invoice_id_match(invoice_id: str, description: str) -> bool:
    """
    Checks if an invoice ID appears in the transaction description.
    Handles variations like 'INV-2026-001', 'INV2026001', 'INV-001', '#001'.
    """
    if not invoice_id or not description:
        return False

    clean_id = _clean_text(invoice_id)
    clean_desc = _clean_text(description)

    if clean_id and clean_id in clean_desc:
        return True

    # Check numeric sequence at the end of invoice id (e.g. '001', '004')
    parts = [p for p in re.findall(r"[0-9]+", invoice_id) if len(p) >= 3 and p not in {"2024", "2025", "2026", "2027"}]
    for num in parts:
        pattern = rf"(?:inv|invoice|ref)?\s*#?\s*{num}\b"
        if re.search(pattern, description, re.IGNORECASE):
            return True

    return False


def _has_client_name_match(client_name: str, description: str) -> bool:
    """
    Checks if meaningful words from client name appear in description.
    Excludes generic stop-words and 4-digit years.
    """
    if not client_name or not description:
        return False

    stop_words = {
        "inc", "corp", "corporation", "llc", "ltd", "co", "company",
        "studio", "studios", "labs", "lab", "academy", "food", "truck",
        "energy", "coffee", "organics", "apparel", "dynamics", "saas",
        "2024", "2025", "2026", "2027"
    }

    words = re.findall(r"[a-zA-Z0-9]+", client_name.lower())
    significant_tokens = [w for w in words if len(w) >= 4 and w not in stop_words and not w.isdigit()]

    desc_lower = description.lower()
    return any(token in desc_lower for token in significant_tokens)


def _check_duplicate_claim_in_emails(invoice_id: str, client_name: str, emails: list[dict[str, Any]]) -> dict[str, Any] | None:
    """
    Checks if client emails make a claim of payment or duplicate payment for this invoice.
    """
    for em in emails:
        related_id = em.get("related_invoice_id", "")
        company = em.get("client_company", "")
        body = em.get("body", "").lower()
        subject = em.get("subject", "").lower()
        full_text = f"{subject} {body}"

        # Match by related ID or client company name
        is_related = False
        if related_id and _clean_text(related_id) == _clean_text(invoice_id):
            is_related = True
        elif company and _has_client_name_match(client_name, company):
            is_related = True

        if not is_related:
            continue

        # If email is explicitly a delay or future payment notice, do not treat as an active payment claim
        is_delay = any(w in full_text for w in ["delay", "extension", "will remit", "will pay", "queued up for payment", "queued up", "no rush"])
        if is_delay:
            continue

        # Check for duplicate claim vs standard payment claim
        is_dup = any(w in full_text for w in ["duplicate", "twice", "two separate transfers", "second transfer", "refund the second", "refund"])
        is_claim = any(w in full_text for w in [
            "already paid", "remitted", "wired", "sent payment", "processed payment", 
            "sent via zelle", "i paid", "we paid", "have paid", "payment made", 
            "payment sent", "transferred funds", "payment was sent", "we have transferred"
        ])

        if is_dup:
            return {
                "type": "duplicate_payment_claim",
                "email_id": em.get("email_id"),
                "sender": em.get("sender_name"),
                "subject": em.get("subject"),
                "body": em.get("body"),
            }
        elif is_claim:
            return {
                "type": "payment_sent_claim",
                "email_id": em.get("email_id"),
                "sender": em.get("sender_name"),
                "subject": em.get("subject"),
                "body": em.get("body"),
            }

    return None


@tool(
    name="match_invoices_to_bank_feed",
    description=(
        "Reconciles invoices against the bank feed using deterministic arithmetic, "
        "date proximity, and reference matching. Classifies each invoice into: "
        "MATCHED (resolve silently), PARTIAL (underpayment/fee difference), "
        "UNMATCHED (overdue with no payment), DUPLICATE_CLAIM (client claims payment "
        "or duplicate transfer but bank records do not match), or PENDING. "
        "Separates silent routine matches from actionable escalations requiring agent review."
    ),
)
def match_invoices_to_bank_feed(
    invoices: list[dict[str, Any]] | None = None,
    bank_transactions: list[dict[str, Any]] | None = None,
    client_emails: list[dict[str, Any]] | None = None,
    as_of_date_str: str | None = None,
) -> dict[str, Any]:
    """
    Executes deterministic matching logic between invoices and bank transactions.

    Args:
        invoices: Optional list of invoices. If None, loaded automatically.
        bank_transactions: Optional list of bank transactions. If None, loaded automatically.
        client_emails: Optional list of client emails. If None, loaded automatically.
        as_of_date_str: Current reference date (YYYY-MM-DD). Defaults to '2026-09-06'.

    Returns:
        Structured reconciliation dictionary with silent_matches, escalations, and summary.
    """
    # 1. Load data if not explicitly provided
    if invoices is None or bank_transactions is None or client_emails is None:
        feed_data = monitor_financial_feeds()
        invoices = invoices if invoices is not None else feed_data.get("invoices", [])
        bank_transactions = bank_transactions if bank_transactions is not None else feed_data.get("bank_transactions", [])
        client_emails = client_emails if client_emails is not None else feed_data.get("client_emails", [])

    as_of = _parse_date(as_of_date_str) or _parse_date(DEFAULT_AS_OF_DATE) or date.today()

    # 2. Filter for incoming credits (deposits)
    credits: list[dict[str, Any]] = []
    for tx in bank_transactions:
        try:
            amt = float(tx.get("amount", 0.0))
            if amt > 0 and tx.get("type", "").upper() != "DEBIT":
                credits.append({**tx, "amount_float": amt})
        except (ValueError, TypeError):
            continue

    silent_matches: list[dict[str, Any]] = []
    escalations: list[dict[str, Any]] = []
    all_results: list[dict[str, Any]] = []

    used_transaction_ids: set[str] = set()

    # 3. Process each invoice
    for inv in invoices:
        invoice_id = str(inv.get("invoice_id", "")).strip()
        client_name = str(inv.get("client_name", "")).strip()
        inv_amount = float(inv.get("amount", 0.0))
        issue_d = _parse_date(inv.get("issue_date", ""))
        due_d = _parse_date(inv.get("due_date", ""))
        is_overdue = due_d is not None and due_d < as_of

        # Check client email claims
        email_claim = _check_duplicate_claim_in_emails(invoice_id, client_name, client_emails)

        # Find candidate matching deposits in bank credits
        candidate_deposits: list[dict[str, Any]] = []
        for tx in credits:
            desc = tx.get("description", "")
            id_match = _has_invoice_id_match(invoice_id, desc)
            client_match = _has_client_name_match(client_name, desc)

            # Either text references the invoice/client, or exact amount matches within close date
            if id_match or client_match:
                candidate_deposits.append(tx)
            else:
                # Fallback matching by date proximity and amount closeness
                tx_d = _parse_date(tx.get("date", ""))
                is_close_date = tx_d and issue_d and abs((tx_d - issue_d).days) <= 14
                if is_close_date:
                    # Exact amount match
                    if abs(tx["amount_float"] - inv_amount) < 0.01:
                        candidate_deposits.append(tx)
                    # Close amount match (e.g. wire fee <= $50 or within 20% tolerance)
                    elif (0 < inv_amount - tx["amount_float"] <= 50.0) or (0.80 * inv_amount <= tx["amount_float"] < inv_amount):
                        candidate_deposits.append(tx)

        # Select best candidate
        best_exact = None
        best_partial = None

        for tx in candidate_deposits:
            tx_id = tx.get("transaction_id", "")
            tx_amt = tx["amount_float"]

            if tx_id in used_transaction_ids:
                continue

            if abs(tx_amt - inv_amount) < 0.01:
                if best_exact is None:
                    best_exact = tx
            elif tx_amt < inv_amount:
                # Select partial payment closest in value to invoice amount
                if best_partial is None or abs(tx_amt - inv_amount) < abs(best_partial["amount_float"] - inv_amount):
                    best_partial = tx

        # ==============================================================================
        # Classification
        # ==============================================================================

        # CASE A: Client claims a DUPLICATE transfer or claims paid when funds are missing
        if email_claim and email_claim["type"] == "duplicate_payment_claim":
            matched_tx = best_exact or (candidate_deposits[0] if candidate_deposits else None)
            matched_id = matched_tx.get("transaction_id") if matched_tx else None
            
            # Count actual deposits found for this invoice/client
            actual_count = len(candidate_deposits)
            days_overdue = max(0, (as_of - due_d).days) if due_d else 0
            record = {
                "invoice_id": invoice_id,
                "client_name": client_name,
                "amount": inv_amount,
                "status": "DUPLICATE_CLAIM",
                "resolution": "escalate",
                "due_date": str(due_d) if due_d else None,
                "days_overdue": days_overdue,
                "matched_transaction_id": matched_id,
                "email_id": email_claim["email_id"],
                "explanation": (
                    f"Client email ({email_claim['sender']}) claims a duplicate transfer of ${inv_amount:,.2f} "
                    f"was sent, but the bank feed shows only {actual_count} deposit(s). "
                    f"DO NOT issue a refund without bank confirmation."
                ),
            }
            if matched_id:
                used_transaction_ids.add(matched_id)
            escalations.append(record)
            all_results.append(record)
            audit_logger.log_event(
                event_type="EXCEPTION_ESCALATION",
                action_taken=f"Escalated duplicate claim for {invoice_id} ({client_name})",
                reasoning_summary=record["explanation"],
                invoice_id=invoice_id,
                client_name=client_name,
                principle="Harm Prevention / Block Accidental Refund",
                metadata={"status": "DUPLICATE_CLAIM", "amount": inv_amount},
            )
            continue

        # CASE B: High confidence exact match (MATCHED - Resolve Silently)
        if best_exact is not None:
            tx_id = best_exact["transaction_id"]
            used_transaction_ids.add(tx_id)
            record = {
                "invoice_id": invoice_id,
                "client_name": client_name,
                "amount": inv_amount,
                "status": "MATCHED",
                "resolution": "silent",
                "matched_transaction_id": tx_id,
                "deposit_date": best_exact.get("date"),
                "deposit_amount": best_exact["amount_float"],
                "explanation": f"Full payment of ${inv_amount:,.2f} confirmed ({tx_id} on {best_exact.get('date')}).",
            }
            silent_matches.append(record)
            all_results.append(record)
            audit_logger.log_event(
                event_type="SILENT_RESOLUTION",
                action_taken=f"Resolved invoice {invoice_id} ({client_name}) silently as MATCHED",
                reasoning_summary=record["explanation"] + " Routine match requires no human interruption.",
                invoice_id=invoice_id,
                client_name=client_name,
                principle="Noise Reduction & Accuracy",
                metadata={"status": "MATCHED", "amount": inv_amount, "matched_transaction_id": tx_id},
            )
            continue

        # CASE C: Partial payment or fee discrepancy (PARTIAL - Escalate for LLM judgment)
        if best_partial is not None:
            tx_id = best_partial["transaction_id"]
            deposit_amt = best_partial["amount_float"]
            diff = round(inv_amount - deposit_amt, 2)
            used_transaction_ids.add(tx_id)
            days_overdue = max(0, (as_of - due_d).days) if due_d else 0

            record = {
                "invoice_id": invoice_id,
                "client_name": client_name,
                "amount": inv_amount,
                "status": "PARTIAL",
                "resolution": "escalate",
                "due_date": str(due_d) if due_d else None,
                "days_overdue": days_overdue,
                "matched_transaction_id": tx_id,
                "deposit_date": best_partial.get("date"),
                "amount_received": deposit_amt,
                "difference": diff,
                "explanation": (
                    f"Deposit of ${deposit_amt:,.2f} received against invoiced ${inv_amount:,.2f} "
                    f"({tx_id}). Underpayment/variance of ${diff:,.2f}."
                ),
            }
            escalations.append(record)
            all_results.append(record)
            audit_logger.log_event(
                event_type="EXCEPTION_ESCALATION",
                action_taken=f"Escalated partial payment on {invoice_id} ({client_name})",
                reasoning_summary=record["explanation"],
                invoice_id=invoice_id,
                client_name=client_name,
                principle="Cash Flow Protection",
                metadata={"status": "PARTIAL", "invoiced": inv_amount, "received": deposit_amt, "variance": diff},
            )
            continue

        # CASE D0: Client email claims paid, but no matching bank transaction exists (DUPLICATE_CLAIM - Escalate)
        if email_claim and email_claim["type"] == "payment_sent_claim":
            record = {
                "invoice_id": invoice_id,
                "client_name": client_name,
                "amount": inv_amount,
                "status": "DUPLICATE_CLAIM",
                "resolution": "escalate",
                "due_date": str(due_d),
                "matched_transaction_id": None,
                "email_id": email_claim["email_id"],
                "explanation": (
                    f"Client email ({email_claim['sender']}) claims payment of ${inv_amount:,.2f} "
                    f"was sent ('{email_claim.get('subject')}'), but no matching bank transaction exists in the feed."
                ),
            }
            escalations.append(record)
            all_results.append(record)
            audit_logger.log_event(
                event_type="EXCEPTION_ESCALATION",
                action_taken=f"Escalated unverified payment claim for {invoice_id} ({client_name})",
                reasoning_summary=record["explanation"],
                invoice_id=invoice_id,
                client_name=client_name,
                principle="Financial Verification",
                metadata={"status": "DUPLICATE_CLAIM", "amount": inv_amount},
            )
            continue

        # CASE D: Overdue with no matching payment (UNMATCHED - Escalate)
        if is_overdue:
            days_overdue = (as_of - due_d).days if due_d else 0
            explanation = f"Invoice is {days_overdue} days overdue (due {due_d}) with no matching bank payment."
            if email_claim:
                explanation += f" Note: Client previously sent email '{email_claim.get('subject')}'."

            record = {
                "invoice_id": invoice_id,
                "client_name": client_name,
                "amount": inv_amount,
                "status": "UNMATCHED",
                "resolution": "escalate",
                "due_date": str(due_d),
                "days_overdue": days_overdue,
                "matched_transaction_id": None,
                "explanation": explanation,
            }
            escalations.append(record)
            all_results.append(record)
            audit_logger.log_event(
                event_type="EXCEPTION_ESCALATION",
                action_taken=f"Escalated overdue invoice {invoice_id} ({client_name})",
                reasoning_summary=record["explanation"],
                invoice_id=invoice_id,
                client_name=client_name,
                principle="Timely Cash Collection",
                metadata={"status": "UNMATCHED", "amount": inv_amount, "days_overdue": days_overdue},
            )
            continue

        # CASE E: Not yet due (PENDING - Silent)
        record = {
            "invoice_id": invoice_id,
            "client_name": client_name,
            "amount": inv_amount,
            "status": "PENDING",
            "resolution": "silent",
            "due_date": str(due_d),
            "matched_transaction_id": None,
            "explanation": f"Invoice not yet due (due {due_d}). Within standard terms.",
        }
        silent_matches.append(record)
        all_results.append(record)
        audit_logger.log_event(
            event_type="SILENT_RESOLUTION",
            action_taken=f"Resolved invoice {invoice_id} ({client_name}) silently as PENDING",
            reasoning_summary=record["explanation"] + " Within normal terms; avoiding unnecessary alerts.",
            invoice_id=invoice_id,
            client_name=client_name,
            principle="Noise Reduction",
            metadata={"status": "PENDING", "amount": inv_amount, "due_date": str(due_d)},
        )

    # 4. Identify any unmatched incoming bank deposits
    unmatched_bank_deposits = [
        tx for tx in credits if tx["transaction_id"] not in used_transaction_ids
    ]

    summary = {
        "as_of_date": str(as_of),
        "total_invoices_analyzed": len(invoices),
        "silent_resolutions_count": len(silent_matches),
        "escalations_required_count": len(escalations),
        "breakdown": {
            "MATCHED": sum(1 for r in all_results if r["status"] == "MATCHED"),
            "PARTIAL": sum(1 for r in all_results if r["status"] == "PARTIAL"),
            "UNMATCHED": sum(1 for r in all_results if r["status"] == "UNMATCHED"),
            "DUPLICATE_CLAIM": sum(1 for r in all_results if r["status"] == "DUPLICATE_CLAIM"),
            "PENDING": sum(1 for r in all_results if r["status"] == "PENDING"),
        },
        "unmatched_bank_deposits_count": len(unmatched_bank_deposits),
    }

    logger.info(
        f"[MatcherTool] Reconciliation complete. Silent: {summary['silent_resolutions_count']}, "
        f"Escalations: {summary['escalations_required_count']}"
    )

    return {
        "status": "success",
        "summary": summary,
        "escalations": escalations,
        "silent_matches": silent_matches,
        "unmatched_bank_deposits": [
            {
                "transaction_id": tx["transaction_id"],
                "date": tx.get("date"),
                "description": tx.get("description"),
                "amount": tx["amount_float"],
            }
            for tx in unmatched_bank_deposits
        ],
        "all_results": all_results,
    }
