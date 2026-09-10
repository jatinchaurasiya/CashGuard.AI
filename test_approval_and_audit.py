"""
CashGuard.AI - Test Suite for Human-Approval Gate & Responsible AI Audit Logger

Verifies:
1. Human-approval gate: NO drafted message can be sent without explicit confirmation.
2. Rejection handling: Staged draft is safely cancelled and blocked.
3. Audit logger: Every check (including silent resolutions) is written to append-only
   JSONL and formatted Markdown tables with reasoning summaries.
"""

import unittest
from pathlib import Path

from tools.drafter import draft_message, clear_staged_drafts
from tools.approval_gate import human_approval_gate
from tools.matcher import match_invoices_to_bank_feed
from audit_logger import audit_logger, JSONL_LOG_PATH, MD_LOG_PATH


class TestApprovalAndAudit(unittest.TestCase):

    def setUp(self):
        clear_staged_drafts()
        audit_logger.clear()

    def test_human_approval_gate_rejects_and_blocks(self):
        """When a human rejects a draft, it must NOT be sent and marked cancelled."""
        res = draft_message(
            invoice_id="INV-TEST-001",
            client_name="Acme Corp",
            content="Payment reminder body",
            recipient_type="client",
            channel="email",
            subject="Invoice #INV-TEST-001 Reminder",
        )
        draft_id = res["draft"]["draft_id"]

        # Human clicks REJECT / NO
        gate_res = human_approval_gate(
            draft_id=draft_id,
            confirmed=False,
            approved_by="Priya",
            human_notes="Client verbally told me they paid today; hold reminder.",
        )

        self.assertEqual(gate_res["status"], "blocked")
        self.assertFalse(gate_res["sent"])
        self.assertFalse(gate_res["approved"])

        # Check audit log
        entries = audit_logger.get_recent_entries()
        reject_events = [e for e in entries if e["event_type"] == "HUMAN_APPROVAL_REJECTED"]
        self.assertEqual(len(reject_events), 1)
        self.assertIn("rejected", reject_events[0]["reasoning_summary"])
        self.assertEqual(reject_events[0]["principle"], "Human-in-the-Loop Oversight")

    def test_human_approval_gate_explicit_authorization(self):
        """When a human explicitly approves, the draft is dispatched and logged."""
        res = draft_message(
            invoice_id="INV-TEST-002",
            client_name="Beta Labs",
            content="Milestone follow-up body",
            recipient_type="client",
            channel="email",
            subject="Milestone 2 Follow-up",
        )
        draft_id = res["draft"]["draft_id"]

        # Human clicks APPROVE / YES
        gate_res = human_approval_gate(
            draft_id=draft_id,
            confirmed=True,
            approved_by="Priya",
            human_notes="Approved with no modifications.",
        )

        self.assertEqual(gate_res["status"], "success")
        self.assertTrue(gate_res["sent"])
        self.assertTrue(gate_res["approved"])
        self.assertEqual(gate_res["approved_by"], "Priya")

        # Check audit log
        entries = audit_logger.get_recent_entries()
        dispatch_events = [e for e in entries if e["event_type"] == "ACTION_DISPATCHED"]
        self.assertEqual(len(dispatch_events), 1)
        self.assertIn("Explicit human confirmation", dispatch_events[0]["reasoning_summary"])

    def test_audit_log_captures_silent_resolutions(self):
        """
        CRITICAL RESPONSIBLE-AI REQUIREMENT:
        Every check, including 'resolved silently' cases, gets written to the audit log
        with timestamps and reasoning summaries as demo evidence for judges.
        """
        # Run matching on demo dataset
        res = match_invoices_to_bank_feed(as_of_date_str="2026-09-06")

        entries = audit_logger.get_recent_entries(limit=100)
        self.assertGreater(len(entries), 0)

        silent_events = [e for e in entries if e["event_type"] == "SILENT_RESOLUTION"]
        escalation_events = [e for e in entries if e["event_type"] == "EXCEPTION_ESCALATION"]

        # 8 silent resolutions: 5 MATCHED + 3 PENDING
        self.assertEqual(len(silent_events), 8)

        # 4 escalations: Nexa, BrightPath, UrbanBite, Pulse
        self.assertEqual(len(escalation_events), 4)

        # Verify silent resolution reasoning
        for s in silent_events:
            self.assertTrue(len(s["reasoning_summary"]) > 10)
            self.assertIn(s["principle"], ["Noise Reduction & Accuracy", "Noise Reduction"])

        # Verify escalation reasoning
        urbanbite_esc = [e for e in escalation_events if e["invoice_id"] == "INV-2026-007"][0]
        self.assertIn("DO NOT issue a refund", urbanbite_esc["reasoning_summary"])
        self.assertEqual(urbanbite_esc["principle"], "Harm Prevention / Block Accidental Refund")

        # Verify files exist on disk and have content
        self.assertTrue(JSONL_LOG_PATH.exists())
        self.assertTrue(MD_LOG_PATH.exists())

        with open(MD_LOG_PATH, "r", encoding="utf-8") as f:
            md_content = f.read()
            self.assertIn("SILENT_RESOLUTION", md_content)
            self.assertIn("EXCEPTION_ESCALATION", md_content)
            self.assertIn("Apex Fitness Co", md_content)


if __name__ == "__main__":
    unittest.main(verbosity=2)
