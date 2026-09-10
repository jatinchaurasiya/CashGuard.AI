"""
CashGuard.AI - Cash-Impact Prioritizer Tool for Strands Agents SDK

Ranks invoice exception cases (PARTIAL, UNMATCHED, DUPLICATE_CLAIM) by
Cash Impact Score = (amount) x (days overdue), highest first.

This ranking determines the order in which exceptions are surfaced to the freelancer,
ensuring that urgent, high-dollar cash leaks are addressed immediately.
"""

from datetime import datetime, date
import logging
from typing import Any
from strands import tool

from .matcher import match_invoices_to_bank_feed

logger = logging.getLogger("CashGuard.Tools.Prioritizer")

DEFAULT_AS_OF_DATE = "2026-09-06"


def _parse_date(date_str: str) -> date | None:
    """Safely parse an ISO date string (YYYY-MM-DD)."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return None


def calculate_cash_impact_score(
    amount: float,
    days_overdue: int,
) -> float:
    """
    Computes Cash Impact Score = (amount) x (days overdue).
    A non-overdue invoice (days_overdue <= 0) has a base score of 0.0.
    """
    effective_days = max(0, int(days_overdue))
    return round(float(amount) * effective_days, 2)


def assign_priority_tier(score: float, days_overdue: int, status: str) -> str:
    """
    Assigns a human-readable priority tier based on impact score and urgency:
    - CRITICAL: Score >= $10,000 (large sum significantly overdue)
    - HIGH:     Score >= $2,000 (substantial cash flow risk or urgent claim)
    - MEDIUM:   Score > $0 (mild delay or moderate balance)
    - LOW:      Score == 0 (early notice, not yet past due)
    """
    # Duplicate refund claims are urgent regardless of due date to prevent accidental payouts
    if status == "DUPLICATE_CLAIM" and score < 2000:
        return "HIGH"

    if score >= 10000.0:
        return "CRITICAL"
    elif score >= 2000.0:
        return "HIGH"
    elif score > 0.0:
        return "MEDIUM"
    return "LOW"


@tool(
    name="prioritize_cash_impact",
    description=(
        "Ranks exception cases (PARTIAL, UNMATCHED, DUPLICATE_CLAIM) from the "
        "Matching Tool by Cash Impact Score: (amount) x (days overdue), highest first. "
        "Determines the exact priority order for surfacing exceptions to the freelancer."
    ),
)
def prioritize_cash_impact(
    exceptions: list[dict[str, Any]] | None = None,
    as_of_date_str: str | None = None,
) -> dict[str, Any]:
    """
    Prioritizes invoice exceptions by cash impact.

    Args:
        exceptions: Optional list of exception records from the matching tool.
                    If None, automatically retrieves escalations from match_invoices_to_bank_feed().
        as_of_date_str: Optional reference date string (YYYY-MM-DD). Defaults to '2026-09-06'.

    Returns:
        Structured dictionary containing ranked exceptions, impact scores, and summary stats.
    """
    as_of = _parse_date(as_of_date_str) or _parse_date(DEFAULT_AS_OF_DATE) or date.today()

    # 1. Fetch exceptions from matching tool if not provided
    if exceptions is None:
        logger.info("[Prioritizer] No exceptions list provided. Fetching from match_invoices_to_bank_feed()...")
        match_results = match_invoices_to_bank_feed(as_of_date_str=str(as_of))
        exceptions = match_results.get("escalations", [])

    # Filter to only actionable exception statuses
    actionable_statuses = {"PARTIAL", "UNMATCHED", "DUPLICATE_CLAIM"}
    filtered_cases = [
        item for item in exceptions
        if item.get("status") in actionable_statuses
    ]

    scored_exceptions: list[dict[str, Any]] = []

    # 2. Calculate impact scores
    for item in filtered_cases:
        amount = float(item.get("amount", 0.0))
        status = str(item.get("status", "UNKNOWN"))
        invoice_id = str(item.get("invoice_id", ""))
        client_name = str(item.get("client_name", ""))
        due_date_str = item.get("due_date")

        # Resolve days overdue from item or compute from due_date
        if "days_overdue" in item and item["days_overdue"] is not None:
            days_overdue = max(0, int(item["days_overdue"]))
        elif due_date_str:
            due_d = _parse_date(due_date_str)
            days_overdue = max(0, (as_of - due_d).days) if due_d else 0
        else:
            days_overdue = 0

        # Cash impact score = (amount) x (days overdue)
        impact_score = calculate_cash_impact_score(amount, days_overdue)
        tier = assign_priority_tier(impact_score, days_overdue, status)

        scored_item = {
            **item,
            "amount": amount,
            "days_overdue": days_overdue,
            "impact_score": impact_score,
            "priority_tier": tier,
        }
        scored_exceptions.append(scored_item)

    # 3. Sort by: (-impact_score, -amount, -days_overdue)
    # Highest impact score first. Tie-breakers: higher dollar amount, higher days overdue.
    ranked_exceptions = sorted(
        scored_exceptions,
        key=lambda x: (
            -x["impact_score"],
            -x["amount"],
            -x["days_overdue"],
        ),
    )

    # 4. Attach 1-based rank numbers
    for idx, item in enumerate(ranked_exceptions, start=1):
        item["rank"] = idx

    logger.info(f"[Prioritizer] Successfully ranked {len(ranked_exceptions)} exceptions by cash impact.")

    summary = {
        "as_of_date": str(as_of),
        "total_exceptions_ranked": len(ranked_exceptions),
        "highest_impact_invoice_id": ranked_exceptions[0]["invoice_id"] if ranked_exceptions else None,
        "highest_impact_client": ranked_exceptions[0]["client_name"] if ranked_exceptions else None,
        "highest_impact_score": ranked_exceptions[0]["impact_score"] if ranked_exceptions else 0.0,
        "tier_counts": {
            "CRITICAL": sum(1 for e in ranked_exceptions if e["priority_tier"] == "CRITICAL"),
            "HIGH": sum(1 for e in ranked_exceptions if e["priority_tier"] == "HIGH"),
            "MEDIUM": sum(1 for e in ranked_exceptions if e["priority_tier"] == "MEDIUM"),
            "LOW": sum(1 for e in ranked_exceptions if e["priority_tier"] == "LOW"),
        },
    }

    return {
        "status": "success",
        "summary": summary,
        "ranked_exceptions": ranked_exceptions,
    }
