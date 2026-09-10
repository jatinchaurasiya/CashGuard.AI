"""
CashGuard.AI - Test Suite for OpenRouter Reasoning Layer & Draft Message Tool

Verifies the 3-step reasoning workflow:
1. Plain-language WhatsApp alert generation for freelancer.
2. Natural language user instruction interpretation.
3. Structured action drafting via `draft_message` tool without sending.
"""

import unittest
from tools.drafter import draft_message, get_staged_drafts, clear_staged_drafts
from tools.prioritizer import prioritize_cash_impact
from reasoning import CashGuardReasoningEngine


class TestReasoningLayer(unittest.TestCase):

    def setUp(self):
        clear_staged_drafts()
        self.engine = CashGuardReasoningEngine.create()

    def test_draft_message_tool_contract(self):
        """Verifies that draft_message enforces non-sending safety contract."""
        res = draft_message(
            invoice_id="INV-TEST-001",
            client_name="Test Client",
            content="Hello world test",
            recipient_type="freelancer",
            channel="whatsapp",
            message_type="alert",
        )

        self.assertEqual(res["status"], "success")
        draft = res["draft"]
        self.assertFalse(draft["sent"], "Drafted message must NEVER be marked as sent")
        self.assertEqual(draft["status"], "draft_created")
        self.assertTrue(draft["staged"])
        self.assertIn("NOT been sent", draft["disclaimer"])

    def test_step1_whatsapp_alert_generation(self):
        """Step 1: Test plain-language WhatsApp-style alert for freelancer."""
        exception = {
            "invoice_id": "INV-2026-009",
            "client_name": "Pulse Dynamics",
            "amount": 3100.0,
            "difference": 25.0,
            "status": "PARTIAL",
            "days_overdue": 0,
            "explanation": "Deposit of $3,075.00 received against invoiced $3,100.00. Underpayment of $25.00.",
        }

        res = self.engine.write_whatsapp_alert(exception)
        draft = res["draft"]

        self.assertEqual(draft["recipient_type"], "freelancer")
        self.assertEqual(draft["channel"], "whatsapp")
        self.assertIn("Pulse Dynamics", draft["content"])
        self.assertIn("25", draft["content"])
        self.assertTrue(draft["content"].endswith("?") or "what" in draft["content"].lower(), "Alert must ask freelancer for direction")

    def test_step2_and_3_interpret_reply_and_draft_action_fee_waiver(self):
        """Steps 2 & 3: Interprets 'let it go' and drafts fee waiver email without sending."""
        exception = {
            "invoice_id": "INV-2026-009",
            "client_name": "Pulse Dynamics",
            "amount": 3100.0,
            "difference": 25.0,
            "status": "PARTIAL",
        }
        user_reply = "Let it go, $25 is fine to write off as a wire fee. Mark it settled."

        res = self.engine.interpret_reply_and_draft_action(exception, user_reply)
        draft = res["draft"]

        self.assertEqual(draft["recipient_type"], "client")
        self.assertEqual(draft["channel"], "email")
        self.assertFalse(draft["sent"])
        self.assertIsNotNone(draft["subject"])
        self.assertIn("settled", draft["content"].lower())
        self.assertIn("Priya", draft["content"])

    def test_step2_and_3_interpret_reply_duplicate_refund_refusal(self):
        """Steps 2 & 3: Interprets refund caution instruction and drafts polite trace request."""
        exception = {
            "invoice_id": "INV-2026-007",
            "client_name": "UrbanBite Food Truck",
            "amount": 750.0,
            "status": "DUPLICATE_CLAIM",
            "explanation": "Chef Mateo claims two transfers sent; bank feed shows only 1.",
        }
        user_reply = "Do not refund! Tell Chef Mateo we only received one payment and ask for their bank trace numbers."

        res = self.engine.interpret_reply_and_draft_action(exception, user_reply)
        draft = res["draft"]

        self.assertEqual(draft["recipient_type"], "client")
        self.assertEqual(draft["channel"], "email")
        self.assertFalse(draft["sent"])
        self.assertIn("Chef Mateo", draft["content"])
        self.assertIn("trace", draft["content"].lower())

    def test_full_prioritized_pipeline(self):
        """Verifies end-to-end execution: prioritize -> alert -> user reply -> draft action."""
        # 1. Prioritize live exceptions
        priorities = prioritize_cash_impact(as_of_date_str="2026-09-06")
        ranked = priorities["ranked_exceptions"]
        self.assertGreaterEqual(len(ranked), 4)

        # 2. Process top priority (Nexa Health Labs - $49,500 score)
        top_exception = ranked[0]
        self.assertEqual(top_exception["invoice_id"], "INV-2026-004")

        # Step 1: Alert
        alert_res = self.engine.write_whatsapp_alert(top_exception)
        alert_draft = alert_res["draft"]
        self.assertEqual(alert_draft["recipient_type"], "freelancer")
        self.assertEqual(alert_draft["channel"], "whatsapp")

        # Step 2 & 3: User replies
        user_instruction = "Acknowledge the milestone payment and confirm the remaining $1,500 will be approved after UAT."
        action_res = self.engine.interpret_reply_and_draft_action(top_exception, user_instruction)
        action_draft = action_res["draft"]

        self.assertEqual(action_draft["recipient_type"], "client")
        self.assertEqual(action_draft["channel"], "email")
        self.assertFalse(action_draft["sent"])
        self.assertIn("1,500", action_draft["content"])

        # Check total staged drafts
        staged = get_staged_drafts()
        self.assertEqual(len(staged), 2)
        for d in staged:
            self.assertFalse(d["sent"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
