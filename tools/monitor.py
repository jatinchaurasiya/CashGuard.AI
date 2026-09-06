"""
CashGuard.AI - Monitor Tool for Strands Agents SDK

This tool loads and returns the current state of:
1. Invoices (`invoices.json`)
2. Bank feed (`bank_feed.csv`)
3. Client communications/emails (`client_emails.json`)

It allows the CashGuard agent to inspect and monitor all incoming and outgoing financial
activities of the freelancer in real time.
"""

import csv
import json
import logging
from pathlib import Path
from typing import Any
from strands import tool

logger = logging.getLogger("CashGuard.Tools.Monitor")

# Determine default data directory relative to project root
DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@tool(
    name="monitor_financial_feeds",
    description=(
        "Loads and returns the current financial feeds for the freelancer: "
        "issued invoices (invoices.json), bank statement feed (bank_feed.csv), "
        "and client emails/messages (client_emails.json). "
        "Use this tool whenever you need to check the freelancer's current cash flow, "
        "verify bank transactions, or reconcile pending/overdue invoices."
    ),
)
def monitor_financial_feeds(
    feed_type: str = "all",
    data_dir_path: str | None = None,
) -> dict[str, Any]:
    """
    Loads and returns the current state of freelancer financial feeds.

    Args:
        feed_type: Filter for which feed to retrieve.
                   Options: 'all' (default), 'invoices', 'bank_feed', 'client_emails'.
        data_dir_path: Optional custom path to data directory. Defaults to the project 'data/' folder.

    Returns:
        A dictionary containing:
        - status: 'success' or 'error'
        - feed_summary: counts of loaded items
        - invoices: list of invoice records (if requested)
        - bank_transactions: list of parsed bank transaction records (if requested)
        - client_emails: list of client email records (if requested)
    """
    data_dir = Path(data_dir_path) if data_dir_path else DEFAULT_DATA_DIR

    invoices_path = data_dir / "invoices.json"
    bank_feed_path = data_dir / "bank_feed.csv"
    emails_path = data_dir / "client_emails.json"

    result: dict[str, Any] = {
        "status": "success",
        "data_directory": str(data_dir),
        "feed_summary": {},
    }

    selected_type = (feed_type or "all").lower().strip()

    # 1. Load Invoices
    if selected_type in ("all", "invoices"):
        if not invoices_path.exists():
            result["invoices_error"] = f"Invoices file not found at {invoices_path}"
            logger.warning(f"Invoices file not found at {invoices_path}")
            result["invoices"] = []
        else:
            try:
                with open(invoices_path, "r", encoding="utf-8") as f:
                    invoices = json.load(f)
                result["invoices"] = invoices
                result["feed_summary"]["invoices_count"] = len(invoices)
                # Quick financial metric
                total_invoiced = sum(inv.get("amount", 0.0) for inv in invoices)
                result["feed_summary"]["total_invoiced_amount"] = round(total_invoiced, 2)
            except Exception as e:
                result["invoices_error"] = f"Error reading invoices: {e}"
                result["invoices"] = []

    # 2. Load Bank Feed (CSV)
    if selected_type in ("all", "bank_feed", "bank"):
        if not bank_feed_path.exists():
            result["bank_feed_error"] = f"Bank feed file not found at {bank_feed_path}"
            logger.warning(f"Bank feed file not found at {bank_feed_path}")
            result["bank_transactions"] = []
        else:
            try:
                transactions = []
                total_credits = 0.0
                total_debits = 0.0
                with open(bank_feed_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Clean and format numeric amounts
                        try:
                            amount_val = float(row.get("amount", 0.0))
                            if amount_val > 0:
                                total_credits += amount_val
                            else:
                                total_debits += abs(amount_val)
                        except (ValueError, TypeError):
                            amount_val = row.get("amount")

                        transactions.append(
                            {
                                "transaction_id": row.get("transaction_id", "").strip(),
                                "date": row.get("date", "").strip(),
                                "description": row.get("description", "").strip(),
                                "amount": amount_val,
                                "type": row.get("type", "").strip(),
                                "balance": row.get("balance", "").strip(),
                            }
                        )

                result["bank_transactions"] = transactions
                result["feed_summary"]["bank_transactions_count"] = len(transactions)
                result["feed_summary"]["total_bank_deposits_credits"] = round(total_credits, 2)
                result["feed_summary"]["total_bank_expenses_debits"] = round(total_debits, 2)
            except Exception as e:
                result["bank_feed_error"] = f"Error reading bank feed: {e}"
                result["bank_transactions"] = []

    # 3. Load Client Emails
    if selected_type in ("all", "client_emails", "emails"):
        if not emails_path.exists():
            result["emails_error"] = f"Client emails file not found at {emails_path}"
            logger.warning(f"Client emails file not found at {emails_path}")
            result["client_emails"] = []
        else:
            try:
                with open(emails_path, "r", encoding="utf-8") as f:
                    emails = json.load(f)
                result["client_emails"] = emails
                result["feed_summary"]["client_emails_count"] = len(emails)
            except Exception as e:
                result["emails_error"] = f"Error reading client emails: {e}"
                result["client_emails"] = []

    logger.info(
        f"[MonitorTool] Loaded feeds successfully: "
        f"{result.get('feed_summary', {})}"
    )
    return result
