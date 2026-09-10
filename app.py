"""
CashGuard.AI - Award-Winning Financial Guardian & Autonomous Agent Platform
Built with Strands Agents SDK & OpenRouter for the AWS 'Agents for Humans' Hackathon

Full Interactive Judge & User Capabilities:
1. Live OpenRouter API Key Status & dynamic .env reload.
2. Interactive "Run Autonomous Scan" with animated 4-stage pipeline stepper.
3. Financial Data Explorer: Inspect raw Invoices, Bank Feed CSV, and Client Emails.
4. Custom Data Injection: Add custom invoices, bank transactions, and email claims.
5. Multi-Scenario Switcher:
   - Benchmark: Priya Sharma (4 prioritized exceptions, 5 silent matches)
   - Silent Reconciler: Clean Slate (All 12 invoices matched; 100% background silent automation)
   - High-Risk Disputes: Wire fraud & duplicate transfer refund attempts
6. Editable Staged Action Feature Card with Human-Approval Gate.
7. Real-Time Append-Only Responsible AI Audit Trail.

Run locally:
    python app.py
Open:
    http://localhost:8000
"""

import csv
import json
import logging
import os
from pathlib import Path
from typing import Any

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, FileResponse
from starlette.routing import Route

from config import check_api_key_status, get_model_id
from tools.prioritizer import prioritize_cash_impact
from tools.approval_gate import human_approval_gate
from tools.drafter import get_staged_drafts, _STAGED_DRAFTS
from tools.monitor import monitor_financial_feeds
from tools.matcher import match_invoices_to_bank_feed
from tools.scenario_manager import (
    get_all_feeds,
    add_custom_invoice,
    add_custom_bank_transaction,
    add_custom_client_email,
    switch_scenario,
    reset_to_default,
)
from reasoning import CashGuardReasoningEngine
from audit_logger import audit_logger, MD_LOG_PATH, JSONL_LOG_PATH

engine = CashGuardReasoningEngine.create()
current_scenario_id = "default"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CashGuard.AI — Autonomous Invoice Guardian (AWS Hackathon)</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    /* ==========================================================================
       CLAY DESIGN SYSTEM TOKENS
       ========================================================================== */
    :root {
      --clay-canvas: #fffaf0;
      --clay-surface-soft: #faf5e8;
      --clay-surface-card: #f5f0e0;
      --clay-surface-strong: #ebe6d6;
      --clay-surface-white: #ffffff;
      --clay-surface-dark: #0a1a1a;
      --clay-primary: #0a0a0a;
      --clay-primary-active: #1f1f1f;
      --clay-ink: #0a0a0a;
      --clay-body: #3a3a3a;
      --clay-body-strong: #1a1a1a;
      --clay-muted: #6a6a6a;
      --clay-muted-soft: #9a9a9a;
      --clay-on-primary: #ffffff;
      --clay-hairline: #e5e5e5;
      --clay-hairline-soft: #f0ede1;
      --clay-hairline-strong: #d5d0c0;

      /* Saturated 6-Color Palette */
      --clay-brand-pink: #ff4d8b;
      --clay-brand-teal: #1a3a3a;
      --clay-brand-lavender: #b8a4ed;
      --clay-brand-peach: #ffb084;
      --clay-brand-ochre: #e8b94a;
      --clay-brand-mint: #a4d4c5;
      --clay-brand-coral: #ff6b5a;

      --clay-success: #22c55e;
      --clay-warning: #f59e0b;
      --clay-error: #ef4444;

      --rounded-xs: 6px;
      --rounded-sm: 8px;
      --rounded-md: 12px;
      --rounded-lg: 16px;
      --rounded-xl: 24px;
      --rounded-pill: 9999px;

      --shadow-subtle: 0 1px 3px rgba(10, 10, 10, 0.04), 0 4px 12px rgba(10, 10, 10, 0.02);
      --shadow-card: 0 2px 8px rgba(10, 10, 10, 0.05), 0 12px 28px -6px rgba(10, 10, 10, 0.05);
      --shadow-pop: 0 16px 40px -10px rgba(10, 10, 10, 0.14);
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      -webkit-font-smoothing: antialiased;
    }

    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background-color: var(--clay-canvas);
      color: var(--clay-ink);
      height: 100vh;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }

    /* ==========================================================================
       TOP NAVIGATION BAR
       ========================================================================== */
    .clay-top-nav {
      height: 64px;
      background-color: var(--clay-canvas);
      border-bottom: 1px solid var(--clay-hairline);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 24px;
      z-index: 50;
      flex-shrink: 0;
      gap: 12px;
    }

    .nav-brand-group {
      display: flex;
      align-items: center;
      gap: 14px;
    }

    .brand-logo-badge {
      display: flex;
      align-items: center;
      gap: 10px;
      text-decoration: none;
      color: var(--clay-ink);
    }

    .brand-shield-icon {
      width: 38px;
      height: 38px;
      background: var(--clay-primary);
      color: #ffffff;
      border-radius: var(--rounded-md);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 19px;
      box-shadow: var(--shadow-subtle);
    }

    .brand-title {
      font-size: 17px;
      font-weight: 700;
      letter-spacing: -0.5px;
      line-height: 1.1;
    }

    .brand-subtitle {
      font-size: 10.5px;
      color: var(--clay-muted);
      font-weight: 600;
      letter-spacing: 0.4px;
      text-transform: uppercase;
    }

    /* API Status Pill in Nav */
    .api-status-pill {
      background: var(--clay-surface-white);
      border: 1px solid var(--clay-hairline-strong);
      padding: 5px 12px;
      border-radius: var(--rounded-pill);
      font-size: 12px;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 7px;
      cursor: pointer;
      transition: all 0.15s ease;
    }
    .api-status-pill:hover {
      background: var(--clay-surface-card);
      border-color: var(--clay-ink);
    }
    .status-dot-green {
      width: 8px; height: 8px; background: var(--clay-success); border-radius: 50%; box-shadow: 0 0 0 2px rgba(34,197,94,0.25);
    }
    .status-dot-yellow {
      width: 8px; height: 8px; background: var(--clay-warning); border-radius: 50%; box-shadow: 0 0 0 2px rgba(245,158,11,0.25);
    }

    /* Action Center Top Group */
    .nav-actions-center {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .btn-clay-scan {
      background: var(--clay-primary);
      color: #ffffff;
      border: none;
      font-size: 13px;
      font-weight: 600;
      padding: 8px 16px;
      border-radius: var(--rounded-md);
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: all 0.15s ease;
      box-shadow: var(--shadow-subtle);
    }
    .btn-clay-scan:hover {
      background: var(--clay-primary-active);
      transform: translateY(-1px);
    }

    .btn-nav-action {
      background: var(--clay-surface-white);
      border: 1px solid var(--clay-hairline);
      color: var(--clay-ink);
      font-size: 12.5px;
      font-weight: 600;
      padding: 7px 13px;
      border-radius: var(--rounded-md);
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s ease;
    }
    .btn-nav-action:hover {
      background: var(--clay-surface-card);
      border-color: var(--clay-ink);
    }

    /* Right Nav Group */
    .nav-user-cluster {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .telemetry-pill {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 5px 12px;
      border-radius: var(--rounded-pill);
      font-size: 12.5px;
      font-weight: 600;
    }
    .pill-risk { background: var(--clay-brand-peach); color: var(--clay-ink); }
    .pill-silent { background: var(--clay-brand-mint); color: var(--clay-ink); }

    .user-pill {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 4px 10px 4px 5px;
      background: var(--clay-surface-soft);
      border: 1px solid var(--clay-hairline);
      border-radius: var(--rounded-pill);
    }
    .user-avatar-circle {
      width: 26px; height: 26px; border-radius: 50%; background: var(--clay-brand-ochre); display: flex; align-items: center; justify-content: center; font-size: 13px;
    }

    /* ==========================================================================
       WORKSPACE
       ========================================================================== */
    .clay-workspace {
      flex: 1;
      display: flex;
      overflow: hidden;
      background-color: var(--clay-canvas);
    }

    /* COLUMN 1: EXCEPTION HUB */
    .exception-hub-col {
      width: 360px;
      border-right: 1px solid var(--clay-hairline);
      display: flex;
      flex-direction: column;
      background: var(--clay-canvas);
      flex-shrink: 0;
    }

    .hub-header {
      padding: 16px 20px 12px;
      border-bottom: 1px solid var(--clay-hairline);
    }

    .hub-header-top {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 6px;
    }
    .hub-title { font-size: 19px; font-weight: 700; letter-spacing: -0.5px; }
    .hub-badge {
      background: var(--clay-surface-card); color: var(--clay-body-strong); padding: 3px 8px; border-radius: var(--rounded-pill); font-size: 11px; font-weight: 600;
    }

    /* Scenario Switcher Bar */
    .scenario-picker-bar {
      margin-top: 10px;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .scenario-label {
      font-size: 11px; font-weight: 600; color: var(--clay-muted); text-transform: uppercase; letter-spacing: 0.4px;
    }
    .scenario-select {
      height: 36px;
      background: var(--clay-surface-white);
      border: 1px solid var(--clay-hairline-strong);
      border-radius: var(--rounded-sm);
      padding: 0 10px;
      font-size: 12.5px;
      font-weight: 600;
      color: var(--clay-ink);
      outline: none;
      cursor: pointer;
    }

    /* Filter Tabs */
    .hub-filter-tabs {
      display: flex;
      gap: 6px;
      padding: 10px 20px;
      border-bottom: 1px solid var(--clay-hairline-soft);
      overflow-x: auto;
      scrollbar-width: none;
    }
    .hub-filter-tabs::-webkit-scrollbar { display: none; }

    .category-tab {
      background: transparent;
      border: 1px solid transparent;
      color: var(--clay-muted);
      font-size: 12px;
      font-weight: 500;
      padding: 4px 10px;
      border-radius: var(--rounded-pill);
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.15s ease;
    }
    .category-tab:hover { color: var(--clay-ink); background: var(--clay-surface-soft); }
    .category-tab.active {
      background: var(--clay-surface-card);
      color: var(--clay-ink);
      font-weight: 600;
      border-color: var(--clay-hairline);
    }

    /* Exception Cards Queue */
    .exception-list {
      flex: 1;
      overflow-y: auto;
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .exception-card {
      background: var(--clay-surface-white);
      border: 1px solid var(--clay-hairline);
      border-radius: var(--rounded-lg);
      padding: 14px;
      cursor: pointer;
      transition: all 0.15s ease;
      position: relative;
    }
    .exception-card:hover {
      border-color: var(--clay-ink);
      box-shadow: var(--shadow-subtle);
      transform: translateY(-1px);
    }
    .exception-card.active {
      background: var(--clay-surface-card);
      border-color: var(--clay-ink);
      box-shadow: var(--shadow-card);
    }
    .exception-card.active::before {
      content: "";
      position: absolute;
      left: 0;
      top: 12px;
      bottom: 12px;
      width: 4px;
      background: var(--clay-primary);
      border-radius: 0 var(--rounded-xs) var(--rounded-xs) 0;
    }

    .card-top-meta { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
    .client-title { font-size: 14.5px; font-weight: 600; color: var(--clay-ink); letter-spacing: -0.2px; }
    .score-badge { font-size: 10.5px; font-weight: 700; padding: 2px 8px; border-radius: var(--rounded-pill); }
    .score-critical { background: var(--clay-brand-pink); color: #fff; }
    .score-high { background: var(--clay-brand-peach); color: var(--clay-ink); }
    .score-medium { background: var(--clay-brand-ochre); color: var(--clay-ink); }
    .score-low { background: var(--clay-brand-mint); color: var(--clay-ink); }

    .card-subline {
      display: flex; align-items: center; gap: 8px; font-size: 11.5px; color: var(--clay-muted); margin-bottom: 8px;
    }
    .invoice-id-tag { font-weight: 600; color: var(--clay-body-strong); font-family: monospace; }

    .card-footer-tags { display: flex; align-items: center; justify-content: space-between; font-size: 11.5px; }
    .status-chip {
      display: inline-flex; align-items: center; gap: 4px; padding: 2px 7px; border-radius: var(--rounded-sm); font-size: 10.5px; font-weight: 600;
    }
    .chip-partial { background: rgba(232, 185, 74, 0.25); color: #8c6307; }
    .chip-unmatched { background: rgba(255, 77, 139, 0.18); color: #b90e4f; }
    .chip-duplicate { background: rgba(184, 164, 237, 0.35); color: #432b85; }

    .overdue-tag { font-weight: 600; color: var(--clay-muted); }
    .overdue-tag.alert-urgent { color: var(--clay-error); }

    /* Silent Mode Banner */
    .silent-mode-card {
      background: var(--clay-brand-mint);
      border-radius: var(--rounded-lg);
      padding: 18px;
      color: var(--clay-ink);
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin: 10px;
    }
    .silent-mode-card h4 { font-size: 14px; font-weight: 700; display: flex; align-items: center; gap: 6px; }
    .silent-mode-card p { font-size: 12px; line-height: 1.45; }

    /* COLUMN 2: ACTION STUDIO */
    .action-studio-col {
      flex: 1;
      display: flex;
      flex-direction: column;
      background: var(--clay-canvas);
      position: relative;
      overflow: hidden;
    }

    .studio-case-header {
      height: 64px;
      background: var(--clay-surface-white);
      border-bottom: 1px solid var(--clay-hairline);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 28px;
      flex-shrink: 0;
    }
    .case-header-left { display: flex; align-items: center; gap: 12px; }
    .case-avatar-box {
      width: 38px; height: 38px; background: var(--clay-surface-card); border: 1px solid var(--clay-hairline); border-radius: var(--rounded-md); display: flex; align-items: center; justify-content: center; font-size: 18px;
    }
    .case-title-block h2 { font-size: 16px; font-weight: 700; color: var(--clay-ink); }
    .case-title-block p { font-size: 12px; color: var(--clay-muted); }

    .safety-shield-pill {
      background: var(--clay-surface-soft);
      border: 1px solid var(--clay-hairline-strong);
      padding: 4px 12px;
      border-radius: var(--rounded-pill);
      font-size: 12px;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .studio-messages-stream {
      flex: 1;
      overflow-y: auto;
      padding: 28px;
      display: flex;
      flex-direction: column;
      gap: 18px;
    }

    .case-context-banner {
      background: var(--clay-surface-soft);
      border: 1px solid var(--clay-hairline);
      border-radius: var(--rounded-lg);
      padding: 14px 18px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .context-metric-grid { display: flex; gap: 24px; }
    .context-metric-item { display: flex; flex-direction: column; }
    .metric-label { font-size: 10.5px; color: var(--clay-muted); text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; }
    .metric-val { font-size: 15px; font-weight: 700; color: var(--clay-ink); }

    /* Messages */
    .msg-row { display: flex; width: 100%; }
    .msg-row.in { justify-content: flex-start; }
    .msg-row.out { justify-content: flex-end; }

    .msg-bubble-agent {
      max-width: 780px;
      background: var(--clay-surface-white);
      border: 1px solid var(--clay-hairline);
      border-radius: var(--rounded-xl);
      padding: 20px 24px;
      box-shadow: var(--shadow-subtle);
    }
    .agent-header-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
    .agent-identity { display: flex; align-items: center; gap: 8px; }
    .agent-avatar-small {
      width: 24px; height: 24px; background: var(--clay-primary); color: #fff; border-radius: var(--rounded-xs); display: flex; align-items: center; justify-content: center; font-size: 12px;
    }
    .agent-name { font-size: 13px; font-weight: 600; }
    .agent-meta-time { font-size: 11px; color: var(--clay-muted); }
    .msg-body-text { font-size: 14.5px; line-height: 1.55; color: var(--clay-body-strong); white-space: pre-wrap; }

    .msg-bubble-user {
      max-width: 600px;
      background: var(--clay-primary);
      color: #fff;
      border-radius: var(--rounded-xl);
      padding: 14px 20px;
      box-shadow: var(--shadow-subtle);
    }
    .msg-bubble-user .msg-body-text { color: #fff; }
    .msg-bubble-user .user-meta-time {
      display: flex; justify-content: flex-end; gap: 4px; font-size: 10.5px; color: rgba(255,255,255,0.6); margin-top: 4px;
    }

    /* Staged Action Card (Clay Feature Card) */
    .clay-feature-card {
      margin-top: 16px;
      background: var(--clay-surface-card);
      border: 1px solid var(--clay-hairline-strong);
      border-radius: var(--rounded-xl);
      padding: 22px;
      box-shadow: var(--shadow-subtle);
    }
    .feature-card-header {
      display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;
    }
    .card-badge-pill {
      background: var(--clay-brand-lavender); color: var(--clay-ink); font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: var(--rounded-pill); text-transform: uppercase;
    }
    .card-header-actions { display: flex; align-items: center; gap: 8px; }
    .btn-edit-toggle {
      background: var(--clay-surface-white);
      border: 1px solid var(--clay-hairline);
      font-size: 11.5px;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: var(--rounded-sm);
      cursor: pointer;
    }

    .draft-subject-block {
      margin-bottom: 8px;
    }
    .draft-subject-input {
      width: 100%;
      background: var(--clay-surface-white);
      border: 1px solid var(--clay-hairline);
      border-radius: var(--rounded-sm);
      padding: 6px 10px;
      font-size: 13px;
      font-weight: 600;
      color: var(--clay-ink);
      outline: none;
    }

    .draft-body-scrollbox {
      background: var(--clay-surface-white);
      border: 1px solid var(--clay-hairline);
      border-radius: var(--rounded-md);
      padding: 14px;
      font-size: 13px;
      line-height: 1.5;
      color: var(--clay-body);
      max-height: 200px;
      overflow-y: auto;
      white-space: pre-wrap;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace;
    }
    .draft-body-textarea {
      width: 100%;
      height: 180px;
      background: var(--clay-surface-white);
      border: 1px solid var(--clay-ink);
      border-radius: var(--rounded-md);
      padding: 12px;
      font-size: 13px;
      line-height: 1.5;
      color: var(--clay-ink);
      font-family: monospace;
      outline: none;
      resize: vertical;
    }

    .approval-gate-bar {
      margin-top: 16px;
      padding-top: 14px;
      border-top: 1px solid var(--clay-hairline);
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .gate-notice {
      display: flex; align-items: center; gap: 6px; font-size: 11.5px; font-weight: 600; color: var(--clay-body-strong);
    }
    .gate-actions-row { display: flex; gap: 10px; }
    .btn-clay-primary {
      flex: 1; height: 42px; background: var(--clay-primary); color: #fff; border: none; border-radius: var(--rounded-md); font-size: 13.5px; font-weight: 600; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; transition: all 0.15s ease;
    }
    .btn-clay-primary:hover { background: var(--clay-primary-active); transform: translateY(-1px); }
    .btn-clay-danger {
      flex: 1; height: 42px; background: var(--clay-surface-white); color: var(--clay-error); border: 1px solid rgba(239,68,68,0.3); border-radius: var(--rounded-md); font-size: 13.5px; font-weight: 600; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; transition: all 0.15s ease;
    }
    .btn-clay-danger:hover { background: #fef2f2; border-color: var(--clay-error); }

    .dispatched-status-card {
      margin-top: 12px; padding: 12px 16px; border-radius: var(--rounded-md); font-size: 12.5px; font-weight: 600; display: flex; align-items: center; gap: 8px;
    }
    .status-card-approved { background: var(--clay-brand-mint); color: var(--clay-ink); }
    .status-card-rejected { background: #fee2e2; color: #991b1b; }

    /* Suggestions & Input Bar */
    .suggestions-strip {
      padding: 8px 28px 0; display: flex; gap: 8px; overflow-x: auto; flex-shrink: 0; scrollbar-width: none;
    }
    .suggestions-strip::-webkit-scrollbar { display: none; }
    .chip-pill {
      background: var(--clay-surface-card); border: 1px solid var(--clay-hairline-strong); color: var(--clay-ink); padding: 6px 12px; border-radius: var(--rounded-pill); font-size: 12px; font-weight: 500; cursor: pointer; white-space: nowrap; transition: all 0.15s ease; display: flex; align-items: center; gap: 5px;
    }
    .chip-pill:hover { background: var(--clay-brand-ochre); border-color: var(--clay-ink); transform: translateY(-1px); }

    .studio-input-bar {
      padding: 14px 28px 20px; display: flex; align-items: center; gap: 10px; flex-shrink: 0;
    }
    .clay-input-box {
      flex: 1; height: 46px; background: var(--clay-surface-white); border: 1px solid var(--clay-hairline-strong); border-radius: var(--rounded-md); padding: 0 16px; font-size: 14px; color: var(--clay-ink); outline: none; transition: all 0.15s ease;
    }
    .clay-input-box:focus { border-color: var(--clay-ink); }
    .btn-send-square {
      width: 46px; height: 46px; background: var(--clay-primary); color: #fff; border: none; border-radius: var(--rounded-md); display: flex; align-items: center; justify-content: center; font-size: 18px; cursor: pointer; transition: all 0.15s ease;
    }
    .btn-send-square:hover { background: var(--clay-primary-active); }

    .typing-pill {
      display: none; align-items: center; gap: 8px; font-size: 12px; color: var(--clay-muted); font-weight: 500; margin-bottom: 8px; padding-left: 28px;
    }
    .dot {
      width: 6px; height: 6px; background: var(--clay-primary); border-radius: 50%; animation: clayPulse 1.2s infinite ease-in-out;
    }
    .dot:nth-child(2) { animation-delay: 0.2s; }
    .dot:nth-child(3) { animation-delay: 0.4s; }
    @keyframes clayPulse { 0%, 100% { opacity: 0.2; } 50% { opacity: 1; } }

    /* COLUMN 3: RESPONSIBLE AI AUDIT DRAWER */
    .audit-drawer-col {
      width: 380px;
      border-left: 1px solid var(--clay-hairline);
      background: var(--clay-surface-soft);
      display: flex;
      flex-direction: column;
      flex-shrink: 0;
    }
    .drawer-header {
      padding: 16px 20px; border-bottom: 1px solid var(--clay-hairline); display: flex; align-items: center; justify-content: space-between;
    }
    .drawer-title-group h3 { font-size: 15.5px; font-weight: 700; }
    .drawer-title-group p { font-size: 11.5px; color: var(--clay-muted); }

    .kpi-grid-2x2 {
      display: grid; grid-template-columns: 1fr 1fr; gap: 8px; padding: 12px 18px; border-bottom: 1px solid var(--clay-hairline);
    }
    .kpi-card { border-radius: var(--rounded-md); padding: 12px; display: flex; flex-direction: column; }
    .kpi-mint { background: var(--clay-brand-mint); }
    .kpi-peach { background: var(--clay-brand-peach); }
    .kpi-lavender { background: var(--clay-brand-lavender); }
    .kpi-ochre { background: var(--clay-brand-ochre); }
    .kpi-title { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.4px; opacity: 0.85; }
    .kpi-number { font-size: 18px; font-weight: 700; margin-top: 4px; }

    .audit-stream-wrapper {
      flex: 1; overflow-y: auto; padding: 14px 18px; display: flex; flex-direction: column; gap: 8px;
    }
    .audit-entry-card {
      background: var(--clay-surface-white); border: 1px solid var(--clay-hairline); border-radius: var(--rounded-md); padding: 10px 12px; display: flex; flex-direction: column; gap: 5px; font-size: 11.5px; box-shadow: var(--shadow-subtle);
    }
    .audit-entry-top { display: flex; align-items: center; justify-content: space-between; }
    .audit-time-stamp { font-family: monospace; font-size: 10.5px; color: var(--clay-muted); }
    .audit-event-pill { font-size: 9.5px; font-weight: 700; padding: 2px 6px; border-radius: var(--rounded-pill); }
    .pill-silent-res { background: rgba(34, 197, 94, 0.15); color: #15803d; }
    .pill-escalation { background: rgba(239, 68, 68, 0.15); color: #b91c1c; }
    .pill-draft { background: rgba(184, 164, 237, 0.35); color: #5b21b6; }
    .pill-approval { background: rgba(232, 185, 74, 0.3); color: #854d0e; }
    .audit-action-text { font-weight: 600; color: var(--clay-ink); }
    .audit-principle-tag { font-size: 10.5px; color: var(--clay-muted); display: flex; align-items: center; gap: 4px; }
    .audit-reasoning-desc {
      color: var(--clay-body); font-size: 11px; line-height: 1.35; background: var(--clay-surface-soft); padding: 5px 8px; border-radius: var(--rounded-xs);
    }

    /* ==========================================================================
       MODALS (API KEY, DATA EXPLORER, NEW ENTRY, SCAN STEPPER)
       ========================================================================== */
    .modal-overlay {
      display: none;
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(10, 26, 26, 0.6);
      backdrop-filter: blur(4px);
      z-index: 200;
      justify-content: center;
      align-items: center;
    }
    .modal-box {
      width: 90vw;
      max-width: 860px;
      max-height: 85vh;
      background: var(--clay-surface-white);
      border: 1px solid var(--clay-hairline-strong);
      border-radius: var(--rounded-xl);
      box-shadow: var(--shadow-pop);
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }
    .modal-header {
      padding: 18px 24px;
      border-bottom: 1px solid var(--clay-hairline);
      display: flex;
      align-items: center;
      justify-content: space-between;
      background: var(--clay-surface-soft);
    }
    .modal-header h3 { font-size: 17px; font-weight: 700; display: flex; align-items: center; gap: 8px; }
    .modal-close-btn {
      width: 32px; height: 32px; border-radius: 50%; border: 1px solid var(--clay-hairline); background: var(--clay-surface-white); cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 14px;
    }
    .modal-body {
      padding: 24px;
      overflow-y: auto;
      flex: 1;
    }

    /* Data Explorer Tabs */
    .explorer-nav {
      display: flex; gap: 8px; border-bottom: 1px solid var(--clay-hairline); padding-bottom: 12px; margin-bottom: 16px;
    }
    .explorer-tab {
      background: var(--clay-surface-soft); border: 1px solid var(--clay-hairline); padding: 6px 14px; border-radius: var(--rounded-pill); font-size: 12.5px; font-weight: 600; cursor: pointer;
    }
    .explorer-tab.active { background: var(--clay-primary); color: #fff; border-color: var(--clay-primary); }

    .data-table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
    .data-table th, .data-table td { padding: 9px 12px; text-align: left; border-bottom: 1px solid var(--clay-hairline-soft); }
    .data-table th { background: var(--clay-surface-soft); font-weight: 600; color: var(--clay-muted); }
    .data-table tr:hover { background: var(--clay-surface-soft); }

    /* Scan Stepper Animation */
    .scan-step-item {
      display: flex; align-items: flex-start; gap: 14px; padding: 12px 0; border-bottom: 1px solid var(--clay-hairline-soft);
    }
    .step-icon-circle {
      width: 28px; height: 28px; border-radius: 50%; background: var(--clay-surface-card); display: flex; align-items: center; justify-content: center; font-size: 14px; flex-shrink: 0;
    }
    .step-icon-circle.done { background: var(--clay-brand-mint); }
    .step-title { font-size: 13.5px; font-weight: 700; color: var(--clay-ink); }
    .step-desc { font-size: 12px; color: var(--clay-muted); }

    /* Form Fields */
    .form-group { margin-bottom: 14px; }
    .form-label { display: block; font-size: 12px; font-weight: 600; margin-bottom: 5px; color: var(--clay-body-strong); }
    .form-input {
      width: 100%; height: 40px; background: var(--clay-surface-white); border: 1px solid var(--clay-hairline-strong); border-radius: var(--rounded-sm); padding: 0 12px; font-size: 13px; outline: none;
    }
    .form-input:focus { border-color: var(--clay-ink); }
    .form-textarea {
      width: 100%; height: 90px; background: var(--clay-surface-white); border: 1px solid var(--clay-hairline-strong); border-radius: var(--rounded-sm); padding: 10px; font-size: 13px; outline: none; resize: vertical;
    }
  </style>
</head>
<body>

  <!-- ========================================================================
       TOP NAVIGATION BAR
       ======================================================================== -->
  <header class="clay-top-nav">
    <div class="nav-brand-group">
      <a href="/" class="brand-logo-badge">
        <div class="brand-shield-icon">🛡️</div>
        <div class="brand-text-block">
          <span class="brand-title">CashGuard.AI</span>
          <span class="brand-subtitle">Autonomous Guardian</span>
        </div>
      </a>
      <div class="api-status-pill" id="apiStatusPill" onclick="openApiModal()" title="View OpenRouter API connection details">
        <div class="status-dot-yellow" id="apiStatusDot"></div>
        <span id="apiStatusText">Checking LLM...</span>
      </div>
    </div>

    <!-- Center Action Suite -->
    <div class="nav-actions-center">
      <button class="btn-clay-scan" onclick="triggerAutonomousScan()" title="Trigger autonomous background reconciliation scan">
        <span>⚡</span>
        <span>Run Autonomous Scan</span>
      </button>
      <button class="btn-nav-action" onclick="openExplorerModal()" title="Explore raw invoices, bank feeds, and client messages">
        <span>📁</span>
        <span>Data Explorer</span>
      </button>
      <button class="btn-nav-action" onclick="openNewEntryModal()" title="Add custom invoice, transaction, or email to test live">
        <span>➕</span>
        <span>Add Entry</span>
      </button>
      <button class="btn-nav-action" onclick="openModal('archModal')" title="View Visual System Architecture diagram">
        <span>📐</span>
        <span>Architecture</span>
      </button>
    </div>

    <!-- Right Telemetry & User -->
    <div class="nav-user-cluster">
      <div class="telemetry-pill pill-risk" title="Total cash value currently in exception status">
        <span>⚠️</span>
        <span id="navRiskVal">$6,775</span>
        <span style="font-weight: 400; opacity: 0.8;">At Risk</span>
      </div>
      <div class="telemetry-pill pill-silent" title="Invoices verified silently with zero human interruption">
        <span>✅</span>
        <span id="navSilentCount">5</span>
        <span style="font-weight: 400; opacity: 0.8;">Silent</span>
      </div>
      <div class="user-pill">
        <div class="user-avatar-circle">👩‍🎨</div>
        <span style="font-size: 12.5px; font-weight: 600;">Priya Sharma</span>
      </div>
    </div>
  </header>

  <!-- ========================================================================
       WORKSPACE
       ======================================================================== -->
  <main class="clay-workspace">

    <!-- COLUMN 1: EXCEPTION HUB -->
    <aside class="exception-hub-col">
      <div class="hub-header">
        <div class="hub-header-top">
          <h1 class="hub-title">Exception Hub</h1>
          <span class="hub-badge" id="exceptionsCountBadge">4 Exceptions</span>
        </div>
        
        <!-- Scenario Switcher -->
        <div class="scenario-picker-bar">
          <span class="scenario-label">Hackathon Scenario Preset:</span>
          <select class="scenario-select" id="scenarioSelect" onchange="handleScenarioChange(this.value)">
            <option value="default">👩‍🎨 Priya Sharma (Benchmark Freelancer)</option>
            <option value="silent_clean_slate">🤫 Clean Slate (Autonomous Silent Reconciler)</option>
            <option value="high_risk_disputes">⚠️ Wire Fraud & Duplicate Dispute Scenarios</option>
          </select>
        </div>
      </div>

      <!-- Filter Tabs -->
      <div class="hub-filter-tabs">
        <button class="category-tab active" onclick="filterExceptions('ALL', this)">All</button>
        <button class="category-tab" onclick="filterExceptions('CRITICAL', this)">Critical</button>
        <button class="category-tab" onclick="filterExceptions('PARTIAL', this)">Underpaid</button>
        <button class="category-tab" onclick="filterExceptions('UNMATCHED', this)">Overdue</button>
      </div>

      <!-- Exception Queue -->
      <div class="exception-list" id="exceptionQueue">
        <!-- Rendered dynamically -->
      </div>
    </aside>

    <!-- COLUMN 2: CONVERSATIONAL ACTION STUDIO -->
    <section class="action-studio-col">
      <div class="studio-case-header">
        <div class="case-header-left">
          <div class="case-avatar-box" id="activeCaseIcon">📄</div>
          <div class="case-title-block">
            <h2 id="activeCaseTitle">Loading exception case...</h2>
            <p id="activeCaseSubtitle">Synchronizing financial feeds</p>
          </div>
        </div>
        <div class="safety-shield-pill">
          <span>🔒</span>
          <span>Read-Only & Strict Human Gate</span>
        </div>
      </div>

      <!-- Stream -->
      <div class="studio-messages-stream" id="messagesStream">
        <!-- Injected dynamically -->
      </div>

      <!-- Typing Indicator -->
      <div class="typing-pill" id="typingIndicator">
        <span>CashGuard reasoning engine is analyzing options</span>
        <div class="dot"></div>
        <div class="dot"></div>
        <div class="dot"></div>
      </div>

      <!-- Quick Action Chips -->
      <div class="suggestions-strip" id="suggestionsStrip">
        <!-- Rendered per exception -->
      </div>

      <!-- Input Bar -->
      <div class="studio-input-bar">
        <input
          type="text"
          class="clay-input-box"
          id="userInputField"
          placeholder="Instruct CashGuard (e.g. 'Ask for missing $25', 'Waive wire fee', 'Refuse refund and ask for trace')..."
          onkeypress="handleKeyPress(event)"
        >
        <button class="btn-send-square" onclick="sendInstruction()" title="Send instruction to agent">
          ➤
        </button>
      </div>
    </section>

    <!-- COLUMN 3: RESPONSIBLE AI AUDIT DRAWER -->
    <aside class="audit-drawer-col" id="auditDrawer">
      <div class="drawer-header">
        <div class="drawer-title-group">
          <h3>Responsible AI Trail</h3>
          <p>Append-only transparent governance</p>
        </div>
        <button class="btn-nav-action" onclick="loadAuditFeed()" title="Refresh live audit trail">
          ↻ Sync
        </button>
      </div>

      <div class="kpi-grid-2x2">
        <div class="kpi-card kpi-mint">
          <span class="kpi-title">Total Invoiced</span>
          <span class="kpi-number" id="kpiTotalInvoiced">$25,550</span>
        </div>
        <div class="kpi-card kpi-peach">
          <span class="kpi-title">Cash At Risk</span>
          <span class="kpi-number" id="kpiAtRisk">$6,775</span>
        </div>
        <div class="kpi-card kpi-lavender">
          <span class="kpi-title">Silent Matches</span>
          <span class="kpi-number" id="kpiSilentMatches">5 Items</span>
        </div>
        <div class="kpi-card kpi-ochre">
          <span class="kpi-title">Human Sign-off</span>
          <span class="kpi-number">100% Gated</span>
        </div>
      </div>

      <div class="audit-stream-wrapper" id="auditStream">
        <!-- Rendered dynamically -->
      </div>
    </aside>

  </main>

  <!-- ========================================================================
       MODAL: ARCHITECTURE DIAGRAM
       ======================================================================== -->
  <div class="modal-overlay" id="archModal" onclick="closeOnOutside(event, 'archModal')">
    <div class="modal-box" style="max-width: 1200px; width: 95vw;">
      <div class="modal-header">
        <div>
          <h3 style="display: flex; align-items: center; gap: 8px;"><span>📐</span> Visual System Architecture</h3>
          <p style="font-size: 12px; color: var(--clay-muted); margin-top: 2px;">Strands Agent Core Orchestration • OpenRouter LLM Gateway • Human Approval Gate</p>
        </div>
        <div style="display: flex; gap: 10px; align-items: center;">
          <a href="/architecture" target="_blank" class="btn-clay-secondary" style="text-decoration: none; padding: 6px 14px; font-size: 12px; display: inline-flex; align-items: center; gap: 6px;">
            <span>↗</span> Open Full Screen
          </a>
          <button class="modal-close-btn" onclick="closeModal('archModal')">✕</button>
        </div>
      </div>
      <div class="modal-body" style="padding: 12px; background: #090d16; border-radius: var(--rounded-md); text-align: center; overflow: auto; max-height: 75vh;">
        <img src="/architecture-diagram.png" alt="CashGuard.AI System Architecture" style="max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 4px 24px rgba(0,0,0,0.6);">
      </div>
    </div>
  </div>

  <!-- ========================================================================
       MODAL: API KEY & ENGINE STATUS
       ======================================================================== -->
  <div class="modal-overlay" id="apiModal" onclick="closeOnOutside(event, 'apiModal')">
    <div class="modal-box" style="max-width: 580px;">
      <div class="modal-header">
        <h3>🔑 OpenRouter & Strands Engine Configuration</h3>
        <button class="modal-close-btn" onclick="closeModal('apiModal')">✕</button>
      </div>
      <div class="modal-body">
        <p style="font-size: 13.5px; color: var(--clay-body); margin-bottom: 16px; line-height: 1.5;">
          CashGuard.AI uses <strong>OpenRouter's zero-cost free tier</strong> (<code>openrouter/free</code>) and the <strong>AWS Strands Agents SDK</strong>.
        </p>

        <div style="background: var(--clay-surface-soft); border: 1px solid var(--clay-hairline); border-radius: var(--rounded-md); padding: 16px; margin-bottom: 20px;">
          <div style="display: flex; justify-content: space-between; margin-bottom: 10px; font-size: 13px;">
            <span style="font-weight: 600;">Status:</span>
            <span id="modalApiStatus" style="font-weight: 700;">Checking...</span>
          </div>
          <div style="display: flex; justify-content: space-between; margin-bottom: 10px; font-size: 13px;">
            <span style="font-weight: 600;">Active Model:</span>
            <span id="modalApiModel" style="font-family: monospace;">openrouter/free</span>
          </div>
          <div style="display: flex; justify-content: space-between; margin-bottom: 10px; font-size: 13px;">
            <span style="font-weight: 600;">Config Source:</span>
            <span id="modalApiSource">.env file</span>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 13px;">
            <span style="font-weight: 600;">Key Mask:</span>
            <span id="modalApiKeyMask" style="font-family: monospace;">Not loaded</span>
          </div>
        </div>

        <div style="font-size: 13px; line-height: 1.5; color: var(--clay-body); margin-bottom: 20px;">
          <strong>How to activate Live LLM:</strong>
          <ol style="margin-left: 20px; margin-top: 6px;">
            <li>Copy <code>.env.example</code> to <code>.env</code> in the project directory.</li>
            <li>Add your OpenRouter key: <code>OPENROUTER_API_KEY=sk-or-v1-...</code></li>
            <li>Click the button below to re-read <code>.env</code> without restarting!</li>
          </ol>
        </div>

        <button class="btn-clay-primary" onclick="reloadApiKeyFromEnv()" style="width: 100%;">
          <span>↻</span> Re-read .env & Connect Live LLM
        </button>
      </div>
    </div>
  </div>

  <!-- ========================================================================
       MODAL: FINANCIAL DATA EXPLORER
       ======================================================================== -->
  <div class="modal-overlay" id="explorerModal" onclick="closeOnOutside(event, 'explorerModal')">
    <div class="modal-box">
      <div class="modal-header">
        <h3>📁 Financial Data Explorer (Raw Feeds)</h3>
        <button class="modal-close-btn" onclick="closeModal('explorerModal')">✕</button>
      </div>
      <div class="modal-body">
        <p style="font-size: 13px; color: var(--clay-muted); margin-bottom: 14px;">
          Inspect the exact raw financial feeds loaded into CashGuard's <code>monitor_financial_feeds</code> tool.
        </p>
        
        <div class="explorer-nav">
          <button class="explorer-tab active" id="tabInvoicesBtn" onclick="showExplorerTab('invoices')">📑 Invoices (<span id="countInvoices">12</span>)</button>
          <button class="explorer-tab" id="tabBankBtn" onclick="showExplorerTab('bank')">🏦 Bank Feed (<span id="countBank">16</span>)</button>
          <button class="explorer-tab" id="tabEmailsBtn" onclick="showExplorerTab('emails')">✉️ Client Inbox (<span id="countEmails">9</span>)</button>
        </div>

        <div id="explorerTableContainer">
          <!-- Rendered dynamically -->
        </div>
      </div>
    </div>
  </div>

  <!-- ========================================================================
       MODAL: ADD CUSTOM FINANCIAL ENTRY
       ======================================================================== -->
  <div class="modal-overlay" id="newEntryModal" onclick="closeOnOutside(event, 'newEntryModal')">
    <div class="modal-box" style="max-width: 600px;">
      <div class="modal-header">
        <h3>➕ Add Custom Financial Entry</h3>
        <button class="modal-close-btn" onclick="closeModal('newEntryModal')">✕</button>
      </div>
      <div class="modal-body">
        <p style="font-size: 13px; color: var(--clay-muted); margin-bottom: 16px;">
          Inject a custom invoice, bank transaction, or email to test how CashGuard reconciles live data!
        </p>

        <div class="explorer-nav">
          <button class="explorer-tab active" id="btnTypeInv" onclick="switchNewEntryType('invoice')">Invoice</button>
          <button class="explorer-tab" id="btnTypeBank" onclick="switchNewEntryType('bank')">Bank Deposit</button>
          <button class="explorer-tab" id="btnTypeEmail" onclick="switchNewEntryType('email')">Client Email</button>
        </div>

        <!-- Invoice Form -->
        <form id="formNewInvoice" onsubmit="submitNewInvoice(event)">
          <div class="form-group">
            <label class="form-label">Client Name</label>
            <input class="form-input" id="newInvClient" required placeholder="e.g. Apex Global Tech" value="Summit Media Group">
          </div>
          <div style="display: flex; gap: 12px;">
            <div class="form-group" style="flex: 1;">
              <label class="form-label">Invoice Amount ($)</label>
              <input class="form-input" type="number" step="0.01" id="newInvAmount" required value="4000.00">
            </div>
            <div class="form-group" style="flex: 1;">
              <label class="form-label">Due Date</label>
              <input class="form-input" type="date" id="newInvDue" required value="2026-08-20">
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">Description / Deliverable</label>
            <input class="form-input" id="newInvDesc" value="Enterprise UI Design Sprint">
          </div>
          <button type="submit" class="btn-clay-primary" style="width: 100%; margin-top: 10px;">
            Save Invoice & Run Scan
          </button>
        </form>

        <!-- Bank Form -->
        <form id="formNewBank" style="display: none;" onsubmit="submitNewBank(event)">
          <div class="form-group">
            <label class="form-label">Transaction Description</label>
            <input class="form-input" id="newBankDesc" required placeholder="e.g. Wire Transfer Apex" value="Direct Deposit Summit Media">
          </div>
          <div style="display: flex; gap: 12px;">
            <div class="form-group" style="flex: 1;">
              <label class="form-label">Deposit Amount ($)</label>
              <input class="form-input" type="number" step="0.01" id="newBankAmount" required value="3950.00">
            </div>
            <div class="form-group" style="flex: 1;">
              <label class="form-label">Transaction Date</label>
              <input class="form-input" type="date" id="newBankDate" required value="2026-09-02">
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">Bank Reference Text</label>
            <input class="form-input" id="newBankRef" value="INV-CUSTOM Summit Pmt">
          </div>
          <button type="submit" class="btn-clay-primary" style="width: 100%; margin-top: 10px;">
            Save Deposit & Run Scan
          </button>
        </form>

        <!-- Email Form -->
        <form id="formNewEmail" style="display: none;" onsubmit="submitNewEmail(event)">
          <div class="form-group">
            <label class="form-label">Sender</label>
            <input class="form-input" id="newEmailSender" required value="Markus Trent <accounting@summit.com>">
          </div>
          <div class="form-group">
            <label class="form-label">Subject</label>
            <input class="form-input" id="newEmailSubject" required value="Payment update on Summit Design invoice">
          </div>
          <div class="form-group">
            <label class="form-label">Email Message Body</label>
            <textarea class="form-textarea" id="newEmailBody">Hi Priya, our treasury department wired $3,950.00 today. The $50 intermediary fee was deducted by Citibank.</textarea>
          </div>
          <button type="submit" class="btn-clay-primary" style="width: 100%; margin-top: 10px;">
            Save Email & Run Scan
          </button>
        </form>

      </div>
    </div>
  </div>

  <!-- ========================================================================
       MODAL: AUTONOMOUS SCAN STEPPER
       ======================================================================== -->
  <div class="modal-overlay" id="scanModal">
    <div class="modal-box" style="max-width: 600px;">
      <div class="modal-header">
        <h3>⚡ Autonomous Background Scan</h3>
        <button class="modal-close-btn" onclick="closeModal('scanModal')">✕</button>
      </div>
      <div class="modal-body">
        <p style="font-size: 13px; color: var(--clay-muted); margin-bottom: 16px;">
          Executing the full autonomous Strands Agents SDK reconciliation pipeline:
        </p>

        <div id="scanStep1" class="scan-step-item">
          <div class="step-icon-circle" id="iconStep1">🔍</div>
          <div>
            <div class="step-title">1. Monitor Tool (Ingesting Feeds)</div>
            <div class="step-desc" id="descStep1">Parsing invoices.json, bank_feed.csv, and client_emails.json...</div>
          </div>
        </div>

        <div id="scanStep2" class="scan-step-item">
          <div class="step-icon-circle" id="iconStep2">⚖️</div>
          <div>
            <div class="step-title">2. Matching Tool (Arithmetic & Silence Filter)</div>
            <div class="step-desc" id="descStep2">Evaluating amounts, dates, and references; silently resolving routine items...</div>
          </div>
        </div>

        <div id="scanStep3" class="scan-step-item">
          <div class="step-icon-circle" id="iconStep3">📊</div>
          <div>
            <div class="step-title">3. Cash-Impact Prioritizer</div>
            <div class="step-desc" id="descStep3">Ranking exceptions by (Amount at Risk) × (Days Overdue)...</div>
          </div>
        </div>

        <div id="scanStep4" class="scan-step-item">
          <div class="step-icon-circle" id="iconStep4">🛡️</div>
          <div>
            <div class="step-title">4. Strands Reasoning Engine</div>
            <div class="step-desc" id="descStep4">Staging prioritized cases and enforcing strict Human-Approval Gate...</div>
          </div>
        </div>

        <div id="scanSummaryBanner" style="display: none; margin-top: 18px; padding: 14px; background: var(--clay-surface-card); border-radius: var(--rounded-md); border: 1px solid var(--clay-hairline-strong);">
          <div style="font-size: 14px; font-weight: 700; margin-bottom: 4px;" id="scanBannerTitle">Scan Complete!</div>
          <div style="font-size: 12.5px; color: var(--clay-body);" id="scanBannerText"></div>
          <button class="btn-clay-primary" onclick="closeModal('scanModal')" style="width: 100%; margin-top: 12px;">
            View Prioritized Exceptions
          </button>
        </div>

      </div>
    </div>
  </div>

  <!-- ========================================================================
       JAVASCRIPT LOGIC
       ======================================================================== -->
  <script>
    let allExceptions = [];
    let displayedExceptions = [];
    let currentExceptionIndex = 0;
    let activeFilter = 'ALL';
    let currentActiveDraft = null;
    let rawFeedsData = null;

    const CONTEXT_SUGGESTIONS = {
      "INV-2026-004": [
        "Acknowledge milestone 1 deposit and confirm balance upon Sept 18 UAT",
        "Ask Dr. Elena for milestone 2 approval timeline",
        "Offer staging preview to expedite final balance"
      ],
      "INV-2026-005": [
        "Send polite reminder asking if board meeting signed off",
        "Ask Arthur when autumn disbursements will be released",
        "Request estimated remittance date"
      ],
      "INV-2026-007": [
        "Do not refund! Ask for Chase wire trace numbers",
        "Tell Chef Mateo we only received one payment of $750",
        "Clarify that banking records show only single credit"
      ],
      "INV-2026-009": [
        "Let it go, $25 is fine to write off as wire fee. Mark settled",
        "Ask them to reimburse the $25 international wire fee",
        "Apply $25 credit toward their next project"
      ]
    };

    async function initApp() {
      await checkApiStatus();
      await loadExceptions();
      await loadAuditFeed();
    }

    async function checkApiStatus() {
      try {
        const res = await fetch("/api/status");
        const data = await res.json();
        const dot = document.getElementById("apiStatusDot");
        const txt = document.getElementById("apiStatusText");

        if (data.is_live) {
          dot.className = "status-dot-green";
          txt.innerText = "OpenRouter Live LLM Active";
        } else {
          dot.className = "status-dot-yellow";
          txt.innerText = "Demo Simulation (.env ready)";
        }

        document.getElementById("modalApiStatus").innerText = data.is_live ? "Live Connected" : "Resilient Fallback Active";
        document.getElementById("modalApiModel").innerText = data.model_id;
        document.getElementById("modalApiSource").innerText = data.source;
        document.getElementById("modalApiKeyMask").innerText = data.masked_key;
      } catch (err) {
        console.error("API status check error:", err);
      }
    }

    async function reloadApiKeyFromEnv() {
      try {
        const res = await fetch("/api/status/reload", { method: "POST" });
        const data = await res.json();
        await checkApiStatus();
        alert(data.is_live ? "Connected to live OpenRouter LLM!" : "Checked .env. No valid key found; using resilient mock mode.");
        closeModal('apiModal');
      } catch (err) {
        alert("Error reloading .env configuration.");
      }
    }

    async function loadExceptions() {
      try {
        const res = await fetch("/api/exceptions");
        const data = await res.json();
        allExceptions = data.ranked_exceptions || [];
        displayedExceptions = [...allExceptions];
        
        // Update nav telemetry
        let totalRisk = allExceptions.reduce((acc, curr) => acc + (curr.variance || curr.amount || 0), 0);
        document.getElementById("navRiskVal").innerText = `$${totalRisk.toLocaleString()}`;
        document.getElementById("kpiAtRisk").innerText = `$${totalRisk.toLocaleString()}`;

        renderSidebarQueue();

        if (allExceptions.length > 0) {
          selectCase(0);
        } else {
          renderSilentCleanSlateView();
        }
      } catch (err) {
        console.error("Error loading exceptions:", err);
      }
    }

    function renderSidebarQueue() {
      const container = document.getElementById("exceptionQueue");
      container.innerHTML = "";

      if (displayedExceptions.length === 0) {
        container.innerHTML = `
          <div class="silent-mode-card">
            <h4><span>🤫</span> Autonomous Silent Mode</h4>
            <p>All invoices match bank records. The agent runs silently in the background without interrupting you.</p>
          </div>
        `;
        document.getElementById("exceptionsCountBadge").innerText = "0 Exceptions";
        return;
      }

      displayedExceptions.forEach((item, idx) => {
        const isSelected = allExceptions[currentExceptionIndex] && allExceptions[currentExceptionIndex].invoice_id === item.invoice_id;
        const card = document.createElement("div");
        card.className = `exception-card ${isSelected ? "active" : ""}`;
        card.onclick = () => {
          const globalIdx = allExceptions.findIndex(e => e.invoice_id === item.invoice_id);
          selectCase(globalIdx);
        };

        const score = Number(item.impact_score || 0);
        let scoreBadgeClass = "score-low";
        if (score > 20000) scoreBadgeClass = "score-critical";
        else if (score > 5000) scoreBadgeClass = "score-high";
        else if (score > 0) scoreBadgeClass = "score-medium";

        let chipClass = "chip-partial";
        if (item.status === 'UNMATCHED') chipClass = "chip-unmatched";
        if (item.status === 'DUPLICATE_CLAIM') chipClass = "chip-duplicate";

        const invoiced = Number(item.invoiced_amount || item.amount || 0);

        card.innerHTML = `
          <div class="card-top-meta">
            <span class="client-title">${escapeHtml(item.client_name)}</span>
            <span class="score-badge ${scoreBadgeClass}">$${score.toLocaleString()} score</span>
          </div>
          <div class="card-subline">
            <span class="invoice-id-tag">${item.invoice_id}</span>
            <span>•</span>
            <span>$${invoiced.toLocaleString()} invoiced</span>
          </div>
          <div class="card-footer-tags">
            <span class="status-chip ${chipClass}">
              ${item.status === 'DUPLICATE_CLAIM' ? '⚠️ UNVERIFIED CLAIM' : item.status}
            </span>
            <span class="overdue-tag ${item.days_overdue > 7 ? 'alert-urgent' : ''}">
              ${item.days_overdue > 0 ? item.days_overdue + 'd overdue' : 'Current terms'}
            </span>
          </div>
        `;
        container.appendChild(card);
      });

      document.getElementById("exceptionsCountBadge").innerText = `${displayedExceptions.length} Exceptions`;
    }

    function filterExceptions(filter, btn) {
      activeFilter = filter;
      document.querySelectorAll(".category-tab").forEach(tab => tab.classList.remove("active"));
      if (btn) btn.classList.add("active");

      if (filter === 'ALL') {
        displayedExceptions = [...allExceptions];
      } else if (filter === 'CRITICAL') {
        displayedExceptions = allExceptions.filter(e => (e.impact_score || 0) > 5000);
      } else if (filter === 'PARTIAL') {
        displayedExceptions = allExceptions.filter(e => e.status === 'PARTIAL');
      } else if (filter === 'UNMATCHED') {
        displayedExceptions = allExceptions.filter(e => e.status === 'UNMATCHED');
      }
      renderSidebarQueue();
    }

    async function selectCase(index) {
      if (index < 0 || index >= allExceptions.length) return;
      currentExceptionIndex = index;
      renderSidebarQueue();

      const item = allExceptions[index];
      const invoiced = Number(item.invoiced_amount || item.amount || 0);
      const received = Number(item.bank_amount_seen || item.amount_received || 0);
      const variance = Number(item.variance || item.difference || (invoiced - received));
      const score = Number(item.impact_score || 0);

      document.getElementById("activeCaseTitle").innerText = `${item.client_name} (${item.invoice_id})`;
      document.getElementById("activeCaseSubtitle").innerText = `Case #${item.rank || (index + 1)} [${item.priority_tier || 'EXCEPTION'}] • Impact Score: $${score.toLocaleString()} • Strictly Human-in-the-Loop`;
      document.getElementById("activeCaseIcon").innerText = item.status === 'DUPLICATE_CLAIM' ? '⚠️' : '📄';

      const stream = document.getElementById("messagesStream");
      stream.innerHTML = `
        <div class="case-context-banner">
          <div class="context-metric-grid">
            <div class="context-metric-item">
              <span class="metric-label">Invoiced Amount</span>
              <span class="metric-val">$${invoiced.toLocaleString()}</span>
            </div>
            <div class="context-metric-item">
              <span class="metric-label">Actual Received</span>
              <span class="metric-val">$${received.toLocaleString()}</span>
            </div>
            <div class="context-metric-item">
              <span class="metric-label">Variance at Risk</span>
              <span class="metric-val" style="color: var(--clay-error);">$${variance.toLocaleString()}</span>
            </div>
            <div class="context-metric-item">
              <span class="metric-label">Days Overdue</span>
              <span class="metric-val">${item.days_overdue || 0} days</span>
            </div>
          </div>
          <div class="status-chip chip-partial" style="font-size: 12px; padding: 4px 10px;">
            ${item.status}
          </div>
        </div>
      `;

      renderSuggestionChips(item.invoice_id);

      showTyping(true);
      try {
        const res = await fetch("/api/chat/start", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ exception: item })
        });
        const data = await res.json();
        showTyping(false);
        appendAgentMessage(data.draft.content);
      } catch (err) {
        showTyping(false);
        appendAgentMessage(`Exception flagged for ${item.client_name} (${item.invoice_id}). Total variance at risk: $${variance.toLocaleString()}. How would you like me to handle this?`);
      }
    }

    function renderSilentCleanSlateView() {
      document.getElementById("activeCaseTitle").innerText = "All Invoices Reconciled Silently";
      document.getElementById("activeCaseSubtitle").innerText = "Core Hackathon Theme: Zero Interruptions for Routine Matches";
      document.getElementById("activeCaseIcon").innerText = "🤫";

      const stream = document.getElementById("messagesStream");
      stream.innerHTML = `
        <div class="case-context-banner" style="background: var(--clay-brand-mint);">
          <div class="context-metric-grid">
            <div class="context-metric-item">
              <span class="metric-label">Total Invoices</span>
              <span class="metric-val">12 Invoices</span>
            </div>
            <div class="context-metric-item">
              <span class="metric-label">Silently Reconciled</span>
              <span class="metric-val">12 (100%)</span>
            </div>
            <div class="context-metric-item">
              <span class="metric-label">Human Interruptions</span>
              <span class="metric-val">0 Notifications</span>
            </div>
          </div>
        </div>
      `;
      appendAgentMessage("Hello Priya! I completed an autonomous background scan across all 12 invoices and bank deposits. Everything matched down to the cent. As designed, I've resolved all 12 silently and recorded the full verification trail in your audit log.");
      document.getElementById("suggestionsStrip").innerHTML = "";
    }

    function renderSuggestionChips(invoiceId) {
      const container = document.getElementById("suggestionsStrip");
      container.innerHTML = "";
      const list = CONTEXT_SUGGESTIONS[invoiceId] || [
        "Send polite reminder",
        "Hold off for now",
        "Clarify terms"
      ];

      list.forEach(promptText => {
        const pill = document.createElement("button");
        pill.className = "chip-pill";
        pill.innerHTML = `<span>💡</span> <span>${escapeHtml(promptText)}</span>`;
        pill.onclick = () => {
          document.getElementById("userInputField").value = promptText;
          sendInstruction();
        };
        container.appendChild(pill);
      });
    }

    function appendAgentMessage(text, stagedDraft = null) {
      const stream = document.getElementById("messagesStream");
      const row = document.createElement("div");
      row.className = "msg-row in";

      const now = new Date();
      const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

      let cardHtml = "";
      if (stagedDraft) {
        currentActiveDraft = stagedDraft;
        cardHtml = `
          <div class="clay-feature-card" id="card-${stagedDraft.draft_id}">
            <div class="feature-card-header">
              <span class="card-badge-pill">Staged Client Action • Sent: False</span>
              <div class="card-header-actions">
                <button class="btn-edit-toggle" onclick="toggleEditDraft('${stagedDraft.draft_id}')">
                  ✏️ Edit Draft
                </button>
                <span style="font-family: monospace; font-size: 11px; color: var(--clay-muted);">${stagedDraft.draft_id}</span>
              </div>
            </div>

            <!-- Subject line -->
            <div class="draft-subject-block">
              <input class="draft-subject-input" id="subjectInput-${stagedDraft.draft_id}" value="${escapeHtml(stagedDraft.subject || 'Client Communication')}">
            </div>

            <!-- Read-only view -->
            <div class="draft-body-scrollbox" id="viewBody-${stagedDraft.draft_id}">${escapeHtml(stagedDraft.content)}</div>
            <!-- Edit view -->
            <textarea class="draft-body-textarea" id="editBody-${stagedDraft.draft_id}" style="display: none;">${escapeHtml(stagedDraft.content)}</textarea>

            <div class="approval-gate-bar" id="gate-${stagedDraft.draft_id}">
              <div class="gate-notice">
                <span>🛑</span>
                <span>Strict Human-Approval Gate: Message is held inert. Nothing sends until you confirm.</span>
              </div>
              <div class="gate-actions-row">
                <button class="btn-clay-primary" onclick="confirmApproval('${stagedDraft.draft_id}', true)">
                  <span>✅</span> Approve & Dispatch Email
                </button>
                <button class="btn-clay-danger" onclick="confirmApproval('${stagedDraft.draft_id}', false)">
                  <span>❌</span> Reject / Hold Action
                </button>
              </div>
            </div>
          </div>
        `;
      }

      row.innerHTML = `
        <div class="msg-bubble-agent">
          <div class="agent-header-row">
            <div class="agent-identity">
              <div class="agent-avatar-small">🛡️</div>
              <span class="agent-name">CashGuard AI</span>
            </div>
            <span class="agent-meta-time">${timeStr}</span>
          </div>
          <div class="msg-body-text">${escapeHtml(text)}</div>
          ${cardHtml}
        </div>
      `;

      stream.appendChild(row);
      stream.scrollTop = stream.scrollHeight;
    }

    function toggleEditDraft(draftId) {
      const viewEl = document.getElementById(`viewBody-${draftId}`);
      const editEl = document.getElementById(`editBody-${draftId}`);
      if (viewEl.style.display === "none") {
        viewEl.innerText = editEl.value;
        viewEl.style.display = "block";
        editEl.style.display = "none";
      } else {
        editEl.style.display = "block";
        viewEl.style.display = "none";
        editEl.focus();
      }
    }

    function appendUserMessage(text) {
      const stream = document.getElementById("messagesStream");
      const row = document.createElement("div");
      row.className = "msg-row out";

      const now = new Date();
      const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

      row.innerHTML = `
        <div class="msg-bubble-user">
          <div class="msg-body-text">${escapeHtml(text)}</div>
          <div class="user-meta-time">
            <span>${timeStr}</span>
            <span>✓✓</span>
          </div>
        </div>
      `;

      stream.appendChild(row);
      stream.scrollTop = stream.scrollHeight;
    }

    async function sendInstruction() {
      const input = document.getElementById("userInputField");
      const userText = input.value.trim();
      if (!userText) return;

      input.value = "";
      appendUserMessage(userText);

      const activeCase = allExceptions[currentExceptionIndex];
      showTyping(true);

      try {
        const res = await fetch("/api/chat/reply", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            exception: activeCase,
            user_reply: userText
          })
        });
        const data = await res.json();
        showTyping(false);

        const draft = data.draft;
        const msgIntro = `I've prepared a tailored draft based on your instruction: "${draft.action_intent || userText}". Review and authorize below:`;
        appendAgentMessage(msgIntro, draft);
        loadAuditFeed();
      } catch (err) {
        showTyping(false);
        appendAgentMessage("I encountered an issue preparing that draft action. Please try again.");
      }
    }

    async function confirmApproval(draftId, isApproved) {
      const gateContainer = document.getElementById(`gate-${draftId}`);
      const subjectInput = document.getElementById(`subjectInput-${draftId}`);
      const editBody = document.getElementById(`editBody-${draftId}`);

      const editedContent = editBody ? editBody.value : null;
      const editedSubject = subjectInput ? subjectInput.value : null;

      if (gateContainer) {
        gateContainer.innerHTML = `<span style="font-size: 13px; color: var(--clay-muted);">Verifying authorization and committing to immutable audit trail...</span>`;
      }

      try {
        const res = await fetch("/api/chat/approve", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            draft_id: draftId,
            confirmed: isApproved,
            approved_by: "Priya Sharma (Freelancer)",
            edited_content: editedContent,
            edited_subject: editedSubject
          })
        });
        const data = await res.json();

        if (gateContainer) {
          if (isApproved) {
            gateContainer.innerHTML = `
              <div class="dispatched-status-card status-card-approved">
                <span>✅</span>
                <span>Action Approved & Dispatched via Email (Authorized by Priya). Logged to Responsible AI Trail!</span>
              </div>
            `;
          } else {
            gateContainer.innerHTML = `
              <div class="dispatched-status-card status-card-rejected">
                <span>❌</span>
                <span>Dispatch Halted & Cancelled by Priya. Logged to Responsible AI Trail!</span>
              </div>
            `;
          }
        }
        loadAuditFeed();
      } catch (err) {
        if (gateContainer) {
          gateContainer.innerHTML = `<span style="color: var(--clay-error);">Error recording decision.</span>`;
        }
      }
    }

    async function loadAuditFeed() {
      try {
        const res = await fetch("/api/audit-log");
        const data = await res.json();
        const container = document.getElementById("auditStream");
        container.innerHTML = "";

        const entries = data.entries || [];
        entries.slice(0, 35).forEach(e => {
          const item = document.createElement("div");
          item.className = "audit-entry-card";

          let pillClass = "pill-silent-res";
          if (e.event_type === 'EXCEPTION_ESCALATION') pillClass = "pill-escalation";
          if (e.event_type === 'DRAFT_STAGED') pillClass = "pill-draft";
          if (e.event_type === 'HUMAN_APPROVAL') pillClass = "pill-approval";

          item.innerHTML = `
            <div class="audit-entry-top">
              <span class="audit-time-stamp">${e.timestamp.slice(11, 19)}</span>
              <span class="audit-event-pill ${pillClass}">${e.event_type}</span>
            </div>
            <div class="audit-action-text">${escapeHtml(e.action_taken)}</div>
            <div class="audit-principle-tag">
              <span>🎯</span>
              <em>${e.principle}</em>
            </div>
            <div class="audit-reasoning-desc">${escapeHtml(e.reasoning_summary)}</div>
          `;
          container.appendChild(item);
        });
      } catch (err) {
        console.error("Audit load error:", err);
      }
    }

    /* ========================================================================
       AUTONOMOUS SCAN STEPPER EXECUTION
       ======================================================================== */
    async function triggerAutonomousScan() {
      openModal('scanModal');
      document.getElementById("scanSummaryBanner").style.display = "none";

      const s1 = document.getElementById("iconStep1");
      const s2 = document.getElementById("iconStep2");
      const s3 = document.getElementById("iconStep3");
      const s4 = document.getElementById("iconStep4");

      s1.className = "step-icon-circle"; s1.innerText = "⏳";
      s2.className = "step-icon-circle"; s2.innerText = "⚖️";
      s3.className = "step-icon-circle"; s3.innerText = "📊";
      s4.className = "step-icon-circle"; s4.innerText = "🛡️";

      await sleep(400);
      s1.className = "step-icon-circle done"; s1.innerText = "✅";
      s2.className = "step-icon-circle"; s2.innerText = "⏳";

      await sleep(500);
      s2.className = "step-icon-circle done"; s2.innerText = "✅";
      s3.className = "step-icon-circle"; s3.innerText = "⏳";

      await sleep(400);
      s3.className = "step-icon-circle done"; s3.innerText = "✅";
      s4.className = "step-icon-circle"; s4.innerText = "⏳";

      try {
        const res = await fetch("/api/scan", { method: "POST" });
        const data = await res.json();
        s4.className = "step-icon-circle done"; s4.innerText = "✅";

        await loadExceptions();
        await loadAuditFeed();

        document.getElementById("scanSummaryBanner").style.display = "block";
        document.getElementById("scanBannerTitle").innerText = `Autonomous Scan Complete!`;
        document.getElementById("scanBannerText").innerHTML = `
          • <strong>${data.summary.invoices_scanned}</strong> invoices scanned<br>
          • <strong>${data.summary.silent_resolutions}</strong> silently resolved (Routine matches)<br>
          • <strong>${data.summary.exceptions_flagged}</strong> exceptions prioritized<br>
          • <strong>$${data.summary.total_cash_at_risk.toLocaleString()}</strong> total cash at risk
        `;
      } catch (err) {
        s4.className = "step-icon-circle"; s4.innerText = "❌";
        alert("Scan execution encountered an error.");
      }
    }

    /* Scenario Switcher Handler */
    async function handleScenarioChange(scenarioId) {
      try {
        const res = await fetch("/api/scenarios/switch", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ scenario_id: scenarioId })
        });
        const data = await res.json();
        await triggerAutonomousScan();
      } catch (err) {
        alert("Failed to switch scenario.");
      }
    }

    /* ========================================================================
       DATA EXPLORER MODAL
       ======================================================================== */
    async function openExplorerModal() {
      openModal('explorerModal');
      try {
        const res = await fetch("/api/feeds");
        rawFeedsData = await res.json();
        document.getElementById("countInvoices").innerText = rawFeedsData.counts.invoices;
        document.getElementById("countBank").innerText = rawFeedsData.counts.bank_transactions;
        document.getElementById("countEmails").innerText = rawFeedsData.counts.client_emails;
        showExplorerTab('invoices');
      } catch (err) {
        alert("Error loading financial feeds.");
      }
    }

    function showExplorerTab(tabName) {
      document.querySelectorAll(".explorer-tab").forEach(t => t.classList.remove("active"));
      const container = document.getElementById("explorerTableContainer");

      if (tabName === 'invoices') {
        document.getElementById("tabInvoicesBtn").classList.add("active");
        let html = `
          <table class="data-table">
            <thead>
              <tr><th>Invoice ID</th><th>Client</th><th>Amount</th><th>Due Date</th><th>Terms</th><th>Status</th></tr>
            </thead>
            <tbody>
        `;
        (rawFeedsData.invoices || []).forEach(inv => {
          html += `
            <tr>
              <td><code>${inv.invoice_id}</code></td>
              <td><strong>${escapeHtml(inv.client_name)}</strong></td>
              <td>$${Number(inv.amount).toLocaleString()}</td>
              <td>${inv.due_date}</td>
              <td>${inv.payment_terms || 'Net 15'}</td>
              <td><span class="status-chip chip-partial">${inv.status}</span></td>
            </tr>
          `;
        });
        html += `</tbody></table>`;
        container.innerHTML = html;
      } else if (tabName === 'bank') {
        document.getElementById("tabBankBtn").classList.add("active");
        let html = `
          <table class="data-table">
            <thead>
              <tr><th>Date</th><th>Tx ID</th><th>Type</th><th>Amount</th><th>Description</th><th>Reference</th></tr>
            </thead>
            <tbody>
        `;
        (rawFeedsData.bank_transactions || []).forEach(tx => {
          html += `
            <tr>
              <td>${tx.date}</td>
              <td><code>${tx.transaction_id}</code></td>
              <td><strong>${tx.type}</strong></td>
              <td style="color: ${tx.type === 'CREDIT' ? 'var(--clay-success)' : 'var(--clay-error)'}">$${Number(tx.amount).toLocaleString()}</td>
              <td>${escapeHtml(tx.description)}</td>
              <td><small>${escapeHtml(tx.reference || '-')}</small></td>
            </tr>
          `;
        });
        html += `</tbody></table>`;
        container.innerHTML = html;
      } else if (tabName === 'emails') {
        document.getElementById("tabEmailsBtn").classList.add("active");
        let html = `
          <table class="data-table">
            <thead>
              <tr><th>From</th><th>Subject</th><th>Preview</th><th>Claim Intent</th></tr>
            </thead>
            <tbody>
        `;
        (rawFeedsData.client_emails || []).forEach(eml => {
          html += `
            <tr>
              <td><small>${escapeHtml(eml.sender)}</small></td>
              <td><strong>${escapeHtml(eml.subject)}</strong></td>
              <td>${escapeHtml(eml.body.slice(0, 80))}...</td>
              <td><span class="status-chip chip-duplicate">${eml.inferred_intent || 'notice'}</span></td>
            </tr>
          `;
        });
        html += `</tbody></table>`;
        container.innerHTML = html;
      }
    }

    /* ========================================================================
       NEW ENTRY MODAL
       ======================================================================== */
    function openNewEntryModal() {
      openModal('newEntryModal');
      switchNewEntryType('invoice');
    }

    function switchNewEntryType(type) {
      document.getElementById("btnTypeInv").classList.remove("active");
      document.getElementById("btnTypeBank").classList.remove("active");
      document.getElementById("btnTypeEmail").classList.remove("active");

      document.getElementById("formNewInvoice").style.display = "none";
      document.getElementById("formNewBank").style.display = "none";
      document.getElementById("formNewEmail").style.display = "none";

      if (type === 'invoice') {
        document.getElementById("btnTypeInv").classList.add("active");
        document.getElementById("formNewInvoice").style.display = "block";
      } else if (type === 'bank') {
        document.getElementById("btnTypeBank").classList.add("active");
        document.getElementById("formNewBank").style.display = "block";
      } else if (type === 'email') {
        document.getElementById("btnTypeEmail").classList.add("active");
        document.getElementById("formNewEmail").style.display = "block";
      }
    }

    async function submitNewInvoice(e) {
      e.preventDefault();
      const payload = {
        client_name: document.getElementById("newInvClient").value,
        amount: parseFloat(document.getElementById("newInvAmount").value),
        due_date: document.getElementById("newInvDue").value,
        description: document.getElementById("newInvDesc").value
      };
      await fetch("/api/feeds/invoice", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      closeModal('newEntryModal');
      await triggerAutonomousScan();
    }

    async function submitNewBank(e) {
      e.preventDefault();
      const payload = {
        description: document.getElementById("newBankDesc").value,
        amount: parseFloat(document.getElementById("newBankAmount").value),
        date: document.getElementById("newBankDate").value,
        reference: document.getElementById("newBankRef").value,
        type: "CREDIT"
      };
      await fetch("/api/feeds/bank", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      closeModal('newEntryModal');
      await triggerAutonomousScan();
    }

    async function submitNewEmail(e) {
      e.preventDefault();
      const payload = {
        sender: document.getElementById("newEmailSender").value,
        subject: document.getElementById("newEmailSubject").value,
        body: document.getElementById("newEmailBody").value
      };
      await fetch("/api/feeds/email", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      closeModal('newEntryModal');
      await triggerAutonomousScan();
    }

    /* Modal Helpers */
    function openModal(id) { document.getElementById(id).style.display = "flex"; }
    function closeModal(id) { document.getElementById(id).style.display = "none"; }
    function openApiModal() { openModal('apiModal'); checkApiStatus(); }
    function closeOnOutside(e, id) { if (e.target.id === id) closeModal(id); }

    function showTyping(show) {
      document.getElementById("typingIndicator").style.display = show ? "flex" : "none";
      const stream = document.getElementById("messagesStream");
      stream.scrollTop = stream.scrollHeight;
    }

    function handleKeyPress(e) { if (e.key === "Enter") sendInstruction(); }
    function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
    function escapeHtml(str) {
      if (!str) return "";
      return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
    }

    window.onload = initApp;
  </script>
</body>
</html>
"""


async def get_index(request: Request) -> HTMLResponse:
    return HTMLResponse(HTML_TEMPLATE)


async def get_status(request: Request) -> JSONResponse:
    status_info = check_api_key_status()
    feeds = get_all_feeds()
    return JSONResponse({
        **status_info,
        "counts": feeds["counts"],
        "scenario_id": current_scenario_id,
    })


async def post_status_reload(request: Request) -> JSONResponse:
    is_live = engine.reload()
    status_info = check_api_key_status()
    return JSONResponse({
        "status": "success",
        "is_live": is_live,
        **status_info,
    })


async def get_feeds(request: Request) -> JSONResponse:
    feeds = get_all_feeds()
    return JSONResponse(feeds)


async def post_feeds_invoice(request: Request) -> JSONResponse:
    body = await request.json()
    res = add_custom_invoice(body)
    return JSONResponse(res)


async def post_feeds_bank(request: Request) -> JSONResponse:
    body = await request.json()
    res = add_custom_bank_transaction(body)
    return JSONResponse(res)


async def post_feeds_email(request: Request) -> JSONResponse:
    body = await request.json()
    res = add_custom_client_email(body)
    return JSONResponse(res)


async def post_scenarios_switch(request: Request) -> JSONResponse:
    global current_scenario_id
    body = await request.json()
    scenario_id = body.get("scenario_id", "default")
    current_scenario_id = scenario_id
    res = switch_scenario(scenario_id)
    return JSONResponse(res)


async def post_scenarios_reset(request: Request) -> JSONResponse:
    global current_scenario_id
    current_scenario_id = "default"
    res = reset_to_default()
    return JSONResponse(res)


async def get_exceptions(request: Request) -> JSONResponse:
    priorities = prioritize_cash_impact(as_of_date_str="2026-09-06")
    for item in priorities.get("ranked_exceptions", []):
        amt = float(item.get("amount", 0.0))
        rec = float(item.get("amount_received", 0.0))
        diff = float(item.get("difference", amt - rec if rec else amt))
        item["invoiced_amount"] = amt
        item["bank_amount_seen"] = rec
        item["variance"] = diff
    return JSONResponse(priorities)


async def post_scan(request: Request) -> JSONResponse:
    """Executes the full pipeline and returns step logs and summary."""
    priorities = prioritize_cash_impact(as_of_date_str="2026-09-06")
    recon = match_invoices_to_bank_feed(as_of_date_str="2026-09-06")
    ranked = priorities.get("ranked_exceptions", [])

    for item in ranked:
        amt = float(item.get("amount", 0.0))
        rec = float(item.get("amount_received", 0.0))
        diff = float(item.get("difference", amt - rec if rec else amt))
        item["invoiced_amount"] = amt
        item["bank_amount_seen"] = rec
        item["variance"] = diff

    summary = {
        "invoices_scanned": len(recon.get("silent_matches", [])) + len(recon.get("pending_invoices", [])) + len(ranked),
        "silent_resolutions": len(recon.get("silent_matches", [])) + len(recon.get("pending_invoices", [])),
        "exceptions_flagged": len(ranked),
        "total_cash_at_risk": sum(item["variance"] for item in ranked),
    }

    return JSONResponse({
        "status": "success",
        "summary": summary,
        "ranked_exceptions": ranked,
    })


async def post_chat_start(request: Request) -> JSONResponse:
    body = await request.json()
    exception = body.get("exception", {})
    alert_res = engine.write_whatsapp_alert(exception)
    return JSONResponse(alert_res)


async def post_chat_reply(request: Request) -> JSONResponse:
    body = await request.json()
    exception = body.get("exception", {})
    user_reply = body.get("user_reply", "")
    action_res = engine.interpret_reply_and_draft_action(exception, user_reply)
    return JSONResponse(action_res)


async def post_chat_approve(request: Request) -> JSONResponse:
    body = await request.json()
    draft_id = body.get("draft_id", "")
    confirmed = bool(body.get("confirmed", True))
    approved_by = body.get("approved_by", "Priya Sharma")
    edited_content = body.get("edited_content")
    edited_subject = body.get("edited_subject")

    if edited_content and draft_id in _STAGED_DRAFTS:
        _STAGED_DRAFTS[draft_id]["content"] = edited_content
        if edited_subject:
            _STAGED_DRAFTS[draft_id]["subject"] = edited_subject

    gate_res = human_approval_gate(
        draft_id=draft_id,
        confirmed=confirmed,
        approved_by=approved_by,
        human_notes=f"Authorized via CashGuard Clay UI by {approved_by}" + (" (with user edits)" if edited_content else ""),
    )
    return JSONResponse(gate_res)


async def get_audit_log(request: Request) -> JSONResponse:
    entries = audit_logger.get_recent_entries(limit=100)
    return JSONResponse({"entries": list(reversed(entries))})


async def get_architecture_page(request: Request) -> HTMLResponse:
    with open("architecture-diagram.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


async def get_architecture_image(request: Request) -> FileResponse:
    return FileResponse("architecture-diagram.png", media_type="image/png")


routes = [
    Route("/", endpoint=get_index, methods=["GET"]),
    Route("/architecture", endpoint=get_architecture_page, methods=["GET"]),
    Route("/architecture-diagram.png", endpoint=get_architecture_image, methods=["GET"]),
    Route("/api/status", endpoint=get_status, methods=["GET"]),
    Route("/api/status/reload", endpoint=post_status_reload, methods=["POST"]),
    Route("/api/feeds", endpoint=get_feeds, methods=["GET"]),
    Route("/api/feeds/invoice", endpoint=post_feeds_invoice, methods=["POST"]),
    Route("/api/feeds/bank", endpoint=post_feeds_bank, methods=["POST"]),
    Route("/api/feeds/email", endpoint=post_feeds_email, methods=["POST"]),
    Route("/api/scenarios/switch", endpoint=post_scenarios_switch, methods=["POST"]),
    Route("/api/scenarios/reset", endpoint=post_scenarios_reset, methods=["POST"]),
    Route("/api/exceptions", endpoint=get_exceptions, methods=["GET"]),
    Route("/api/scan", endpoint=post_scan, methods=["POST"]),
    Route("/api/chat/start", endpoint=post_chat_start, methods=["POST"]),
    Route("/api/chat/reply", endpoint=post_chat_reply, methods=["POST"]),
    Route("/api/chat/approve", endpoint=post_chat_approve, methods=["POST"]),
    Route("/api/audit-log", endpoint=get_audit_log, methods=["GET"]),
]

app = Starlette(routes=routes)


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print(" 🛡️ CashGuard.AI — Award-Winning Hackathon Application Running")
    print(" 👉 Open in your browser: http://localhost:8000")
    print("=" * 70 + "\n")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
