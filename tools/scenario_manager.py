"""
CashGuard.AI - Scenario Manager & Financial Feed Data Engine

Enables dynamic interactive data exploration, custom data injection,
and instant switching between hackathon demonstration scenarios:
1. 'default': Priya Sharma benchmark dataset (4 prioritized exceptions, 5 silent matches).
2. 'silent_clean_slate': All invoices matched by bank deposits (demonstrating autonomous silent background reconciliation with zero human interruption).
3. 'high_risk_disputes': High-stakes fraud prevention and duplicate transfer claims.
"""

import csv
import json
import logging
import shutil
from pathlib import Path
from typing import Any

logger = logging.getLogger("CashGuard.ScenarioManager")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SEEDS_DIR = DATA_DIR / "seeds"

INVOICES_PATH = DATA_DIR / "invoices.json"
BANK_FEED_PATH = DATA_DIR / "bank_feed.csv"
CLIENT_EMAILS_PATH = DATA_DIR / "client_emails.json"


def ensure_seeds_exist():
    """Ensure seed datasets exist as pristine restore points."""
    SEEDS_DIR.mkdir(parents=True, exist_ok=True)
    for filename in ["invoices.json", "bank_feed.csv", "client_emails.json"]:
        dest = SEEDS_DIR / filename
        src = DATA_DIR / filename
        if not dest.exists() and src.exists():
            shutil.copy(src, dest)


def get_all_feeds() -> dict[str, Any]:
    """Returns raw structured content of all three financial feeds."""
    ensure_seeds_exist()

    invoices = []
    if INVOICES_PATH.exists():
        with open(INVOICES_PATH, "r", encoding="utf-8") as f:
            invoices = json.load(f)

    bank_transactions = []
    if BANK_FEED_PATH.exists():
        with open(BANK_FEED_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            bank_transactions = list(reader)

    client_emails = []
    if CLIENT_EMAILS_PATH.exists():
        with open(CLIENT_EMAILS_PATH, "r", encoding="utf-8") as f:
            client_emails = json.load(f)

    return {
        "invoices": invoices,
        "bank_transactions": bank_transactions,
        "client_emails": client_emails,
        "counts": {
            "invoices": len(invoices),
            "bank_transactions": len(bank_transactions),
            "client_emails": len(client_emails),
        },
    }


def add_custom_invoice(invoice_data: dict[str, Any]) -> dict[str, Any]:
    """Appends a user-defined custom invoice to invoices.json."""
    feeds = get_all_feeds()
    invoices = feeds["invoices"]

    # Assign invoice ID if not supplied
    inv_id = invoice_data.get("invoice_id")
    if not inv_id:
        inv_id = f"INV-CUSTOM-{len(invoices) + 1:03d}"
        invoice_data["invoice_id"] = inv_id

    invoice_data.setdefault("status", "UNPAID")
    invoice_data["amount"] = float(invoice_data.get("amount", 1000.0))
    invoice_data.setdefault("client_name", "New Client Corp")
    invoice_data.setdefault("issue_date", "2026-08-15")
    invoice_data.setdefault("due_date", "2026-08-30")
    invoice_data.setdefault("description", "Custom freelance deliverable")

    invoices.append(invoice_data)

    with open(INVOICES_PATH, "w", encoding="utf-8") as f:
        json.dump(invoices, f, indent=2)

    logger.info(f"[ScenarioManager] Added custom invoice {inv_id} for {invoice_data['client_name']}")
    return {"status": "success", "invoice": invoice_data, "total_invoices": len(invoices)}


def add_custom_bank_transaction(tx_data: dict[str, Any]) -> dict[str, Any]:
    """Appends a user-defined custom bank transaction to bank_feed.csv."""
    ensure_seeds_exist()

    tx_id = tx_data.get("transaction_id") or f"TXN-CUSTOM-{tx_data.get('date', '20260906')}"
    tx_type = tx_data.get("type", "CREDIT").upper()
    amount = float(tx_data.get("amount", 1000.0))
    date = tx_data.get("date", "2026-09-04")
    description = tx_data.get("description", "Direct Deposit")
    reference = tx_data.get("reference", "")

    row = {
        "transaction_id": tx_id,
        "date": date,
        "type": tx_type,
        "amount": f"{amount:.2f}",
        "description": description,
        "reference": reference,
        "balance_after": "18500.00",
    }

    # Append to CSV
    fieldnames = ["transaction_id", "date", "type", "amount", "description", "reference", "balance_after"]
    with open(BANK_FEED_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writerow(row)

    logger.info(f"[ScenarioManager] Added bank transaction {tx_id} (${amount:.2f})")
    return {"status": "success", "transaction": row}


def add_custom_client_email(email_data: dict[str, Any]) -> dict[str, Any]:
    """Appends a custom client email to client_emails.json."""
    feeds = get_all_feeds()
    emails = feeds["client_emails"]

    email_id = email_data.get("email_id") or f"EML-CUSTOM-{len(emails) + 1:03d}"
    email_data["email_id"] = email_id
    email_data.setdefault("sender", "Client Rep <client@example.com>")
    email_data.setdefault("date", "2026-09-05T10:00:00Z")
    email_data.setdefault("subject", "Payment update")
    email_data.setdefault("body", "We have processed the payment. Please let us know.")

    emails.append(email_data)

    with open(CLIENT_EMAILS_PATH, "w", encoding="utf-8") as f:
        json.dump(emails, f, indent=2)

    logger.info(f"[ScenarioManager] Added client email {email_id} from {email_data['sender']}")
    return {"status": "success", "email": email_data, "total_emails": len(emails)}


def switch_scenario(scenario_id: str) -> dict[str, Any]:
    """
    Switches active datasets to showcase specific agent capabilities:
    - 'default': Original benchmark dataset (Priya Sharma).
    - 'silent_clean_slate': Perfect cash-flow scenario where all 12 invoices are
      matched by bank deposits. The agent resolves all 12 silently in the background!
    - 'high_risk_disputes': Highlights duplicate refund scams and unverified wire claims.
    """
    ensure_seeds_exist()

    if scenario_id == "silent_clean_slate":
        # Load seed invoices
        with open(SEEDS_DIR / "invoices.json", "r", encoding="utf-8") as f:
            invoices = json.load(f)

        # Generate exact matching deposits for EVERY invoice
        synthetic_txs = []
        for idx, inv in enumerate(invoices):
            synthetic_txs.append({
                "transaction_id": f"TXN-CLEAN-{idx + 1:03d}",
                "date": inv.get("due_date", "2026-09-01"),
                "type": "CREDIT",
                "amount": f"{float(inv['amount']):.2f}",
                "description": f"Direct Deposit {inv['client_name']}",
                "reference": f"{inv['invoice_id']} Payment in Full",
                "balance_after": f"{20000 + (idx * 1500):.2f}",
            })

        with open(INVOICES_PATH, "w", encoding="utf-8") as f:
            json.dump(invoices, f, indent=2)

        fieldnames = ["transaction_id", "date", "type", "amount", "description", "reference", "balance_after"]
        with open(BANK_FEED_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(synthetic_txs)

        # Clear disruptive emails for clean slate
        with open(CLIENT_EMAILS_PATH, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)

        logger.info("[ScenarioManager] Activated 'silent_clean_slate' scenario.")
        return {
            "status": "success",
            "scenario": "silent_clean_slate",
            "name": "Clean Slate (Autonomous Silent Reconciler)",
            "description": "All 12 invoices matched by exact bank deposits. Demonstrates the core hackathon theme: the agent works 100% in the background, resolving all routine items silently without disturbing the user!",
        }

    elif scenario_id == "high_risk_disputes":
        # Restore default first
        reset_to_default()
        # Add high-stakes dispute claim
        add_custom_client_email({
            "email_id": "EML-FRAUD-999",
            "sender": "CFO Marcus Vance <finance@acmepremium.com>",
            "date": "2026-09-06T09:15:00Z",
            "subject": "URGENT: Accidental Double Wire of $5,000 for INV-2026-001 - Request Immediate Wire Refund",
            "body": "Hi Priya, Our accounts payable department accidentally sent two separate wires of $3,200.00 each for Invoice #INV-2026-001 instead of one. Please immediately refund $3,200.00 to our Chase account ending in 4491.",
            "inferred_intent": "refund_claim",
            "related_invoice": "INV-2026-001",
        })
        logger.info("[ScenarioManager] Activated 'high_risk_disputes' scenario.")
        return {
            "status": "success",
            "scenario": "high_risk_disputes",
            "name": "High-Stakes Wire Fraud & Duplicate Claims",
            "description": "Client demands an immediate $3,200 wire refund claiming a duplicate transfer. The agent cross-checks bank records, verifies only 1 deposit arrived, prevents accidental fund leakage, and stages a protective clarification note.",
        }

    else:
        # Default scenario
        reset_to_default()
        logger.info("[ScenarioManager] Restored 'default' benchmark scenario.")
        return {
            "status": "success",
            "scenario": "default",
            "name": "Priya Sharma (Benchmark Freelancer)",
            "description": "Realistic real-world workload: 12 invoices, $25,550 total invoiced, 5 silent routine matches, 4 prioritized exceptions ($6,775 at risk).",
        }


def reset_to_default() -> dict[str, Any]:
    """Restores all data feeds to their pristine seed state."""
    ensure_seeds_exist()
    for filename in ["invoices.json", "bank_feed.csv", "client_emails.json"]:
        src = SEEDS_DIR / filename
        dest = DATA_DIR / filename
        if src.exists():
            shutil.copy(src, dest)
    logger.info("[ScenarioManager] All financial feeds reset to default seeds.")
    return {"status": "success", "message": "Datasets successfully reset to default benchmark."}
