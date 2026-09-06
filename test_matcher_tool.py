"""
CashGuard.AI - Test Script for the Matching Tool

Run this script to verify deterministic arithmetic and classification:
    python test_matcher_tool.py
"""

from tools.matcher import match_invoices_to_bank_feed


def test_matcher():
    print("=" * 72)
    print(" 🎯 CashGuard.AI — Invoice & Bank Matching Tool Test")
    print("=" * 72)

    res = match_invoices_to_bank_feed()
    summary = res["summary"]

    print(f"\n[+] Reconciliation Summary (As of {summary['as_of_date']}):")
    print(f"    • Total Invoices:        {summary['total_invoices_analyzed']}")
    print(f"    • Silent Resolutions:    {summary['silent_resolutions_count']} (No agent alert needed)")
    print(f"    • Escalations Required:  {summary['escalations_required_count']} (Requires agent judgment)")
    print(f"    • Category Breakdown:    {summary['breakdown']}")
    print(f"    • Unmatched Deposits:    {summary['unmatched_bank_deposits_count']}")

    print("\n" + "=" * 72)
    print(" 🚨 ESCALATIONS (Flagged for AI Agent Review & Follow-up)")
    print("=" * 72)
    for esc in res["escalations"]:
        print(f"\n• [{esc['status']}] Invoice {esc['invoice_id']} — {esc['client_name']}")
        print(f"  Invoiced Amount: ${esc['amount']:,.2f}")
        if "amount_received" in esc:
            print(f"  Amount Received: ${esc['amount_received']:,.2f} (Variance: -${esc['difference']:,.2f})")
        if "days_overdue" in esc:
            print(f"  Overdue By:      {esc['days_overdue']} days")
        print(f"  Details:         {esc['explanation']}")

    print("\n" + "=" * 72)
    print(" 🤫 SILENT RESOLUTIONS (Routine Matches & Future Pending)")
    print("=" * 72)
    for s in res["silent_matches"]:
        print(f"• [{s['status']}] {s['invoice_id']} ({s['client_name']}): ${s['amount']:,.2f} — {s['explanation']}")

    if res["unmatched_bank_deposits"]:
        print("\n" + "=" * 72)
        print(" ❓ UNMATCHED BANK DEPOSITS (Credits with no matching invoice)")
        print("=" * 72)
        for dep in res["unmatched_bank_deposits"]:
            print(f"• [{dep['transaction_id']}] {dep['date']} | ${dep['amount']:,.2f} | {dep['description']}")

    # Validation assertions
    assert summary["breakdown"]["MATCHED"] == 5, f"Expected 5 MATCHED, got {summary['breakdown']['MATCHED']}"
    assert summary["breakdown"]["PARTIAL"] == 2, f"Expected 2 PARTIAL, got {summary['breakdown']['PARTIAL']}"
    assert summary["breakdown"]["UNMATCHED"] == 1, f"Expected 1 UNMATCHED, got {summary['breakdown']['UNMATCHED']}"
    assert summary["breakdown"]["DUPLICATE_CLAIM"] == 1, f"Expected 1 DUPLICATE_CLAIM, got {summary['breakdown']['DUPLICATE_CLAIM']}"

    print("\n" + "=" * 72)
    print("✅ All deterministic matching assertions passed successfully!")
    print("=" * 72)


if __name__ == "__main__":
    test_matcher()
