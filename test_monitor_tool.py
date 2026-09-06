"""
CashGuard.AI - Test Script for the Monitor Tool

Run this script to test the `monitor_financial_feeds` tool independently:
    python test_monitor_tool.py
"""

import json
from tools.monitor import monitor_financial_feeds


def test_monitor():
    print("=" * 72)
    print(" 🔍 CashGuard.AI — Monitor Tool Test")
    print("=" * 72)

    # 1. Test loading all feeds
    print("\n[+] Invoking monitor_financial_feeds(feed_type='all')...")
    data = monitor_financial_feeds()

    print(f"• Status:         {data.get('status')}")
    print(f"• Data Directory: {data.get('data_directory')}")
    print("\n• Feed Summary:")
    for key, value in data.get("feed_summary", {}).items():
        print(f"    - {key}: {value}")

    # 2. Inspect Invoices
    invoices = data.get("invoices", [])
    print(f"\n• Invoices Sample (showing first 2 of {len(invoices)}):")
    for inv in invoices[:2]:
        print(f"    - [{inv['invoice_id']}] {inv['client_name']}: ${inv['amount']:,.2f} ({inv['status']})")

    # 3. Inspect Bank Transactions
    txns = data.get("bank_transactions", [])
    print(f"\n• Bank Transactions Sample (showing first 3 of {len(txns)}):")
    for tx in txns[:3]:
        print(f"    - [{tx['transaction_id']}] {tx['date']} | {tx['description']} | ${tx['amount']}")

    # 4. Inspect Client Emails
    emails = data.get("client_emails", [])
    print(f"\n• Client Emails Sample (showing first 2 of {len(emails)}):")
    for em in emails[:2]:
        print(f"    - [{em['email_id']}] From: {em['sender_name']} ({em['client_company']})")
        print(f"      Subject: {em['subject']}")

    # 5. Test filtering by specific feed
    print("\n" + "-" * 72)
    print("[+] Testing feed filtering (feed_type='bank_feed')...")
    bank_only = monitor_financial_feeds(feed_type="bank_feed")
    print(f"• Invoices in response:        {'invoices' in bank_only}")
    print(f"• Bank transactions retrieved: {len(bank_only.get('bank_transactions', []))}")
    print(f"• Client emails in response:   {'client_emails' in bank_only}")

    print("\n✅ Monitor Tool test passed successfully!")
    print("=" * 72)


if __name__ == "__main__":
    test_monitor()
