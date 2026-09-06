"""
CashGuard.AI - Tools Package

Contains specialized tools for the Strands Agents SDK:
1. monitor_financial_feeds: Loads and returns invoices, bank feeds, and client emails.
2. match_invoices_to_bank_feed: Reconciles invoices against the bank feed, separating silent routine matches from escalations.
"""

from .monitor import monitor_financial_feeds
from .matcher import match_invoices_to_bank_feed

__all__ = ["monitor_financial_feeds", "match_invoices_to_bank_feed"]
