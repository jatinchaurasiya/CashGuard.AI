"""
CashGuard.AI - Comprehensive Unit Tests for Matching Tool
Tests the 4 required classification outcomes:
- MATCHED (high confidence — resolve silently)
- PARTIAL (payment amount is close but not exact)
- UNMATCHED (overdue, no payment seen)
- DUPLICATE_CLAIM (client email says paid, but no matching bank transaction exists)
"""

import unittest
from tools.matcher import match_invoices_to_bank_feed


class TestMatchingToolLogic(unittest.TestCase):

    def test_matched_silently(self):
        """High confidence exact match: resolves silently without disturbing freelancer."""
        invoices = [
            {
                "invoice_id": "INV-101",
                "client_name": "Acme Corp",
                "amount": 1000.0,
                "issue_date": "2026-09-01",
                "due_date": "2026-09-15",
            }
        ]
        bank_tx = [
            {
                "transaction_id": "TX-001",
                "date": "2026-09-03",
                "description": "ACH DEPOSIT - ACME CORP INV-101",
                "amount": 1000.0,
                "type": "CREDIT",
            }
        ]
        emails = []

        result = match_invoices_to_bank_feed(
            invoices=invoices,
            bank_transactions=bank_tx,
            client_emails=emails,
            as_of_date_str="2026-09-06",
        )

        self.assertEqual(len(result["silent_matches"]), 1)
        self.assertEqual(len(result["escalations"]), 0)
        match = result["silent_matches"][0]
        self.assertEqual(match["status"], "MATCHED")
        self.assertEqual(match["resolution"], "silent")
        self.assertEqual(match["matched_transaction_id"], "TX-001")

    def test_partial_payment_escalated(self):
        """Payment amount is close but not exact (e.g. wire fee or partial milestone): escalated for LLM judgment."""
        invoices = [
            {
                "invoice_id": "INV-102",
                "client_name": "Beta Labs",
                "amount": 2500.0,
                "issue_date": "2026-08-20",
                "due_date": "2026-09-03",
            }
        ]
        bank_tx = [
            {
                "transaction_id": "TX-002",
                "date": "2026-09-01",
                "description": "INCOMING WIRE - BETA LABS INV-102",
                "amount": 2475.0,  # $25 wire fee deduction
                "type": "CREDIT",
            }
        ]
        emails = []

        result = match_invoices_to_bank_feed(
            invoices=invoices,
            bank_transactions=bank_tx,
            client_emails=emails,
            as_of_date_str="2026-09-06",
        )

        self.assertEqual(len(result["silent_matches"]), 0)
        self.assertEqual(len(result["escalations"]), 1)
        esc = result["escalations"][0]
        self.assertEqual(esc["status"], "PARTIAL")
        self.assertEqual(esc["resolution"], "escalate")
        self.assertEqual(esc["amount_received"], 2475.0)
        self.assertEqual(esc["difference"], 25.0)

    def test_unmatched_overdue_escalated(self):
        """Invoice is overdue and no payment has been seen: escalated for follow-up."""
        invoices = [
            {
                "invoice_id": "INV-103",
                "client_name": "Gamma Studio",
                "amount": 1800.0,
                "issue_date": "2026-08-01",
                "due_date": "2026-08-20",  # Overdue by 17 days as of Sept 6
            }
        ]
        bank_tx = []
        emails = []

        result = match_invoices_to_bank_feed(
            invoices=invoices,
            bank_transactions=bank_tx,
            client_emails=emails,
            as_of_date_str="2026-09-06",
        )

        self.assertEqual(len(result["silent_matches"]), 0)
        self.assertEqual(len(result["escalations"]), 1)
        esc = result["escalations"][0]
        self.assertEqual(esc["status"], "UNMATCHED")
        self.assertEqual(esc["resolution"], "escalate")
        self.assertEqual(esc["days_overdue"], 17)
        self.assertIsNone(esc["matched_transaction_id"])

    def test_duplicate_claim_email_says_paid_no_bank_tx(self):
        """Client email claims payment was sent, but no matching bank transaction exists in feed."""
        invoices = [
            {
                "invoice_id": "INV-104",
                "client_name": "Delta Agency",
                "amount": 3200.0,
                "issue_date": "2026-08-25",
                "due_date": "2026-09-10",
            }
        ]
        bank_tx = []
        emails = [
            {
                "email_id": "EML-501",
                "client_company": "Delta Agency",
                "sender_name": "Sarah Connor",
                "related_invoice_id": "INV-104",
                "subject": "Payment sent for INV-104",
                "body": "Hi Priya, we already wired the payment of $3,200 yesterday.",
            }
        ]

        result = match_invoices_to_bank_feed(
            invoices=invoices,
            bank_transactions=bank_tx,
            client_emails=emails,
            as_of_date_str="2026-09-06",
        )

        self.assertEqual(len(result["silent_matches"]), 0)
        self.assertEqual(len(result["escalations"]), 1)
        esc = result["escalations"][0]
        self.assertEqual(esc["status"], "DUPLICATE_CLAIM")
        self.assertEqual(esc["resolution"], "escalate")
        self.assertIsNone(esc["matched_transaction_id"])
        self.assertEqual(esc["email_id"], "EML-501")

    def test_duplicate_claim_refund_request_only_one_transfer(self):
        """Client claims duplicate payment and asks for refund, but bank shows only 1 deposit."""
        invoices = [
            {
                "invoice_id": "INV-105",
                "client_name": "Omega Cafe",
                "amount": 500.0,
                "issue_date": "2026-08-28",
                "due_date": "2026-09-10",
            }
        ]
        bank_tx = [
            {
                "transaction_id": "TX-501",
                "date": "2026-09-02",
                "description": "TRANSFER OMEGA CAFE INV-105",
                "amount": 500.0,
                "type": "CREDIT",
            }
        ]
        emails = [
            {
                "email_id": "EML-502",
                "client_company": "Omega Cafe",
                "sender_name": "Bob Vance",
                "related_invoice_id": "INV-105",
                "subject": "Accidental duplicate transfer",
                "body": "We sent two separate transfers of $500 by accident. Please check and refund the second transfer!",
            }
        ]

        result = match_invoices_to_bank_feed(
            invoices=invoices,
            bank_transactions=bank_tx,
            client_emails=emails,
            as_of_date_str="2026-09-06",
        )

        self.assertEqual(len(result["silent_matches"]), 0)
        self.assertEqual(len(result["escalations"]), 1)
        esc = result["escalations"][0]
        self.assertEqual(esc["status"], "DUPLICATE_CLAIM")
        self.assertEqual(esc["resolution"], "escalate")
        self.assertIn("DO NOT issue a refund", esc["explanation"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
