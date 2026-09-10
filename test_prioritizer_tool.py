"""
CashGuard.AI - Test Script for Cash-Impact Prioritizer Tool
Tests ranking of invoice exceptions by: (amount) x (days overdue), highest first.
"""

import unittest
from tools.prioritizer import (
    prioritize_cash_impact,
    calculate_cash_impact_score,
)


class TestPrioritizerTool(unittest.TestCase):

    def test_score_calculation(self):
        """Tests core arithmetic: score = (amount) x (days overdue)."""
        # Normal overdue
        self.assertEqual(calculate_cash_impact_score(1000.0, 10), 10000.0)
        self.assertEqual(calculate_cash_impact_score(4500.0, 11), 49500.0)
        self.assertEqual(calculate_cash_impact_score(1600.0, 8), 12800.0)
        self.assertEqual(calculate_cash_impact_score(750.0, 3), 2250.0)

        # Zero or negative overdue (not yet due)
        self.assertEqual(calculate_cash_impact_score(3100.0, 0), 0.0)
        self.assertEqual(calculate_cash_impact_score(2500.0, -5), 0.0)

    def test_ranking_synthetic_exceptions(self):
        """Verifies that exceptions are ordered strictly by impact score descending."""
        cases = [
            {
                "invoice_id": "INV-LOW",
                "client_name": "Low Impact Co",
                "amount": 500.0,
                "days_overdue": 2,  # 500 x 2 = 1,000
                "status": "UNMATCHED",
            },
            {
                "invoice_id": "INV-CRITICAL",
                "client_name": "Critical Giant LLC",
                "amount": 10000.0,
                "days_overdue": 15,  # 10,000 x 15 = 150,000
                "status": "PARTIAL",
            },
            {
                "invoice_id": "INV-MEDIUM",
                "client_name": "Medium Firm",
                "amount": 2000.0,
                "days_overdue": 5,  # 2,000 x 5 = 10,000
                "status": "DUPLICATE_CLAIM",
            },
            {
                "invoice_id": "INV-FUTURE",
                "client_name": "Not Overdue Inc",
                "amount": 4000.0,
                "days_overdue": 0,  # 4,000 x 0 = 0
                "status": "PARTIAL",
            },
        ]

        result = prioritize_cash_impact(exceptions=cases)
        ranked = result["ranked_exceptions"]

        self.assertEqual(len(ranked), 4)

        # Verify ranks
        self.assertEqual(ranked[0]["invoice_id"], "INV-CRITICAL")
        self.assertEqual(ranked[0]["rank"], 1)
        self.assertEqual(ranked[0]["impact_score"], 150000.0)

        self.assertEqual(ranked[1]["invoice_id"], "INV-MEDIUM")
        self.assertEqual(ranked[1]["rank"], 2)
        self.assertEqual(ranked[1]["impact_score"], 10000.0)

        self.assertEqual(ranked[2]["invoice_id"], "INV-LOW")
        self.assertEqual(ranked[2]["rank"], 3)
        self.assertEqual(ranked[2]["impact_score"], 1000.0)

        self.assertEqual(ranked[3]["invoice_id"], "INV-FUTURE")
        self.assertEqual(ranked[3]["rank"], 4)
        self.assertEqual(ranked[3]["impact_score"], 0.0)

    def test_tie_breaking_by_amount(self):
        """When two exceptions have the same score (e.g. 0 score), the larger amount ranks higher."""
        cases = [
            {"invoice_id": "INV-A", "client_name": "Client A", "amount": 1200.0, "days_overdue": 0, "status": "PARTIAL"},
            {"invoice_id": "INV-B", "client_name": "Client B", "amount": 5000.0, "days_overdue": 0, "status": "PARTIAL"},
        ]

        result = prioritize_cash_impact(exceptions=cases)
        ranked = result["ranked_exceptions"]

        self.assertEqual(ranked[0]["invoice_id"], "INV-B")  # $5,000 > $1,200
        self.assertEqual(ranked[1]["invoice_id"], "INV-A")

    def test_live_dataset_prioritization(self):
        """Verifies the prioritizer against the realistic demo dataset."""
        result = prioritize_cash_impact(as_of_date_str="2026-09-06")
        summary = result["summary"]
        ranked = result["ranked_exceptions"]

        print("\n" + "=" * 76)
        print(" 📊 CashGuard.AI — Cash-Impact Prioritizer Test (Live Dataset)")
        print("=" * 76)
        print(f"Total Exceptions Ranked: {summary['total_exceptions_ranked']}")
        print(f"Highest Impact Invoice:  {summary['highest_impact_invoice_id']} ({summary['highest_impact_client']})")
        print(f"Highest Impact Score:    ${summary['highest_impact_score']:,.2f}")
        print("-" * 76)

        for item in ranked:
            print(
                f"Rank #{item['rank']} [{item['priority_tier']}] "
                f"Invoice {item['invoice_id']} ({item['client_name']})\n"
                f"  • Status:       {item['status']}\n"
                f"  • Amount:       ${item['amount']:,.2f}\n"
                f"  • Days Overdue: {item['days_overdue']} days\n"
                f"  • IMPACT SCORE: ${item['impact_score']:,.2f}  [ = ${item['amount']:,.2f} x {item['days_overdue']}d ]\n"
            )

        # Assertions on hackathon demo data
        self.assertEqual(len(ranked), 4)

        # Rank 1: Nexa Health Labs ($4,500 x 11d = 49,500)
        self.assertEqual(ranked[0]["invoice_id"], "INV-2026-004")
        self.assertEqual(ranked[0]["client_name"], "Nexa Health Labs")
        self.assertEqual(ranked[0]["status"], "PARTIAL")
        self.assertEqual(ranked[0]["impact_score"], 49500.0)

        # Rank 2: BrightPath Academy ($1,600 x 8d = 12,800)
        self.assertEqual(ranked[1]["invoice_id"], "INV-2026-005")
        self.assertEqual(ranked[1]["client_name"], "BrightPath Academy")
        self.assertEqual(ranked[1]["status"], "UNMATCHED")
        self.assertEqual(ranked[1]["impact_score"], 12800.0)

        # Rank 3: UrbanBite Food Truck ($750 x 3d = 2,250)
        self.assertEqual(ranked[2]["invoice_id"], "INV-2026-007")
        self.assertEqual(ranked[2]["client_name"], "UrbanBite Food Truck")
        self.assertEqual(ranked[2]["status"], "DUPLICATE_CLAIM")
        self.assertEqual(ranked[2]["impact_score"], 2250.0)

        # Rank 4: Pulse Dynamics ($3,100 x 0d = 0.0, due in future)
        self.assertEqual(ranked[3]["invoice_id"], "INV-2026-009")
        self.assertEqual(ranked[3]["client_name"], "Pulse Dynamics")
        self.assertEqual(ranked[3]["status"], "PARTIAL")
        self.assertEqual(ranked[3]["impact_score"], 0.0)

        print("=" * 76)
        print("✅ All Prioritizer tests and assertions passed successfully!")
        print("=" * 76)


if __name__ == "__main__":
    unittest.main(verbosity=2)
