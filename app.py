"""
CashGuard.AI - Intelligent Financial Guardian
Ultra-Premium Web Application implementing the Clay Design System (DESIGN.md)

- Canvas: Warm cream-tinted canvas (#fffaf0) with hairline borders (#e5e5e5)
- Typography: Plain Black display voice (Inter 500/600 with negative letter-spacing)
- Saturated Feature Cards: Lavender, Peach, Teal, Pink, Ochre, and Mint
- 3-Column Executive Workspace:
  1. Exception Hub & Cash-Impact Prioritizer Queue
  2. Conversational Agent Action Studio with Human-Approval Gate
  3. Responsible AI Live Observability Drawer & Audit Trail

Run locally:
    python app.py
Open:
    http://localhost:8000
"""

import json
from pathlib import Path
from typing import Any

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

from tools.prioritizer import prioritize_cash_impact
from tools.approval_gate import human_approval_gate
from tools.drafter import get_staged_drafts
from tools.monitor import monitor_financial_feeds
from tools.matcher import match_invoices_to_bank_feed
from reasoning import CashGuardReasoningEngine
from audit_logger import audit_logger, MD_LOG_PATH, JSONL_LOG_PATH

engine = CashGuardReasoningEngine.create()

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CashGuard.AI — Invoice Exception & Cash-Flow Guardian</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    /* ==========================================================================
       CLAY DESIGN SYSTEM TOKENS (from DESIGN.md)
       ========================================================================== */
    :root {
      /* Colors: Canvas & Surfaces */
      --clay-canvas: #fffaf0;
      --clay-surface-soft: #faf5e8;
      --clay-surface-card: #f5f0e0;
      --clay-surface-strong: #ebe6d6;
      --clay-surface-white: #ffffff;
      --clay-surface-dark: #0a1a1a;
      --clay-surface-dark-elevated: #1a2a2a;

      /* Colors: Ink & Text */
      --clay-primary: #0a0a0a;
      --clay-primary-active: #1f1f1f;
      --clay-primary-disabled: #e5e5e5;
      --clay-ink: #0a0a0a;
      --clay-body: #3a3a3a;
      --clay-body-strong: #1a1a1a;
      --clay-muted: #6a6a6a;
      --clay-muted-soft: #9a9a9a;
      --clay-on-primary: #ffffff;
      --clay-on-dark: #ffffff;
      --clay-on-dark-soft: #a0a0a0;

      /* Colors: Hairlines & Borders */
      --clay-hairline: #e5e5e5;
      --clay-hairline-soft: #f0ede1;
      --clay-hairline-strong: #d5d0c0;

      /* Colors: Saturated 6-Color Brand Palette */
      --clay-brand-pink: #ff4d8b;
      --clay-brand-teal: #1a3a3a;
      --clay-brand-lavender: #b8a4ed;
      --clay-brand-peach: #ffb084;
      --clay-brand-ochre: #e8b94a;
      --clay-brand-mint: #a4d4c5;
      --clay-brand-coral: #ff6b5a;

      /* Colors: Semantic */
      --clay-success: #22c55e;
      --clay-warning: #f59e0b;
      --clay-error: #ef4444;

      /* Border Radius Scale */
      --rounded-xs: 6px;
      --rounded-sm: 8px;
      --rounded-md: 12px;
      --rounded-lg: 16px;
      --rounded-xl: 24px;
      --rounded-pill: 9999px;

      /* Shadows (Minimal, crisp Clay aesthetic) */
      --shadow-subtle: 0 1px 3px rgba(10, 10, 10, 0.04), 0 4px 12px rgba(10, 10, 10, 0.02);
      --shadow-card: 0 2px 8px rgba(10, 10, 10, 0.05), 0 12px 28px -6px rgba(10, 10, 10, 0.05);
      --shadow-pop: 0 16px 40px -10px rgba(10, 10, 10, 0.12);
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
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
       TOP NAVIGATION BAR (64px, Cream Canvas, Hairline Border)
       ========================================================================== */
    .clay-top-nav {
      height: 64px;
      background-color: var(--clay-canvas);
      border-bottom: 1px solid var(--clay-hairline);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 28px;
      z-index: 50;
      flex-shrink: 0;
    }

    .nav-brand-group {
      display: flex;
      align-items: center;
      gap: 16px;
    }

    .brand-logo-badge {
      display: flex;
      align-items: center;
      gap: 10px;
      text-decoration: none;
      color: var(--clay-ink);
    }

    .brand-shield-icon {
      width: 36px;
      height: 36px;
      background: var(--clay-primary);
      color: #ffffff;
      border-radius: var(--rounded-md);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 18px;
      box-shadow: var(--shadow-subtle);
    }

    .brand-text-block {
      display: flex;
      flex-direction: column;
    }

    .brand-title {
      font-size: 17px;
      font-weight: 600;
      letter-spacing: -0.5px;
      line-height: 1.15;
    }

    .brand-subtitle {
      font-size: 11px;
      color: var(--clay-muted);
      font-weight: 500;
      letter-spacing: 0.3px;
      text-transform: uppercase;
    }

    .agent-status-pill {
      background: var(--clay-surface-card);
      border: 1px solid var(--clay-hairline-strong);
      padding: 4px 10px;
      border-radius: var(--rounded-pill);
      font-size: 12px;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 6px;
      color: var(--clay-body-strong);
    }

    .status-pulse-dot {
      width: 7px;
      height: 7px;
      background: var(--clay-success);
      border-radius: 50%;
      box-shadow: 0 0 0 2px rgba(34, 197, 94, 0.25);
    }

    /* Live Telemetry Pills Center Cluster */
    .nav-telemetry-group {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .telemetry-pill {
      display: flex;
      align-items: center;
      gap: 7px;
      padding: 6px 14px;
      border-radius: var(--rounded-pill);
      font-size: 13px;
      font-weight: 500;
      border: 1px solid transparent;
      transition: transform 0.15s ease;
    }

    .telemetry-pill:hover {
      transform: translateY(-1px);
    }

    .pill-risk {
      background: var(--clay-brand-peach);
      color: var(--clay-ink);
      border-color: rgba(0, 0, 0, 0.06);
    }

    .pill-silent {
      background: var(--clay-brand-mint);
      color: var(--clay-ink);
      border-color: rgba(0, 0, 0, 0.06);
    }

    .pill-safety {
      background: var(--clay-brand-lavender);
      color: var(--clay-ink);
      border-color: rgba(0, 0, 0, 0.06);
    }

    .pill-count {
      font-weight: 700;
    }

    /* Right Nav Actions */
    .nav-user-actions {
      display: flex;
      align-items: center;
      gap: 14px;
    }

    .user-profile-badge {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 5px 12px 5px 6px;
      background: var(--clay-surface-soft);
      border: 1px solid var(--clay-hairline);
      border-radius: var(--rounded-pill);
    }

    .user-avatar-circle {
      width: 28px;
      height: 28px;
      border-radius: 50%;
      background: var(--clay-brand-ochre);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 14px;
    }

    .user-meta-name {
      font-size: 13px;
      font-weight: 600;
      color: var(--clay-ink);
    }

    .user-meta-role {
      font-size: 11px;
      color: var(--clay-muted);
    }

    .btn-clay-secondary {
      background-color: var(--clay-canvas);
      color: var(--clay-ink);
      border: 1px solid var(--clay-hairline);
      font-size: 13px;
      font-weight: 600;
      padding: 8px 16px;
      border-radius: var(--rounded-md);
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 7px;
      transition: all 0.15s ease;
    }

    .btn-clay-secondary:hover {
      background-color: var(--clay-surface-card);
      border-color: var(--clay-ink);
    }

    .btn-clay-secondary.active {
      background-color: var(--clay-primary);
      color: var(--clay-on-primary);
      border-color: var(--clay-primary);
    }

    /* ==========================================================================
       MAIN 3-COLUMN WORKSPACE
       ========================================================================== */
    .clay-workspace {
      flex: 1;
      display: flex;
      overflow: hidden;
      background-color: var(--clay-canvas);
    }

    /* ==========================================================================
       COLUMN 1: PRIORITIZED EXCEPTION HUB (360px)
       ========================================================================== */
    .exception-hub-col {
      width: 360px;
      border-right: 1px solid var(--clay-hairline);
      display: flex;
      flex-direction: column;
      background: var(--clay-canvas);
      flex-shrink: 0;
    }

    .hub-header {
      padding: 20px 24px 14px;
      border-bottom: 1px solid var(--clay-hairline);
    }

    .hub-header-top {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      margin-bottom: 6px;
    }

    .hub-title {
      font-size: 20px;
      font-weight: 600;
      letter-spacing: -0.5px;
      color: var(--clay-ink);
    }

    .hub-badge {
      background: var(--clay-surface-card);
      color: var(--clay-body-strong);
      padding: 3px 8px;
      border-radius: var(--rounded-pill);
      font-size: 11px;
      font-weight: 600;
    }

    .hub-subline {
      font-size: 12px;
      color: var(--clay-muted);
      line-height: 1.4;
    }

    /* Category Filter Tabs (Clay category-tab) */
    .hub-filter-tabs {
      display: flex;
      gap: 6px;
      padding: 12px 24px;
      border-bottom: 1px solid var(--clay-hairline-soft);
      overflow-x: auto;
      scrollbar-width: none;
      -ms-overflow-style: none;
    }
    .hub-filter-tabs::-webkit-scrollbar {
      display: none;
    }

    .category-tab {
      background: transparent;
      border: 1px solid transparent;
      color: var(--clay-muted);
      font-size: 12px;
      font-weight: 500;
      padding: 5px 12px;
      border-radius: var(--rounded-pill);
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.15s ease;
    }

    .category-tab:hover {
      color: var(--clay-ink);
      background: var(--clay-surface-soft);
    }

    .category-tab.active {
      background: var(--clay-surface-card);
      color: var(--clay-ink);
      font-weight: 600;
      border-color: var(--clay-hairline);
    }

    /* Exception List Stream */
    .exception-list {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .exception-card {
      background: var(--clay-surface-white);
      border: 1px solid var(--clay-hairline);
      border-radius: var(--rounded-lg);
      padding: 16px;
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
      top: 14px;
      bottom: 14px;
      width: 4px;
      background: var(--clay-primary);
      border-radius: 0 var(--rounded-xs) var(--rounded-xs) 0;
    }

    .card-top-meta {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 6px;
    }

    .client-title {
      font-size: 15px;
      font-weight: 600;
      color: var(--clay-ink);
      letter-spacing: -0.2px;
    }

    .score-badge {
      font-size: 11px;
      font-weight: 700;
      padding: 3px 9px;
      border-radius: var(--rounded-pill);
      letter-spacing: -0.2px;
    }

    .score-critical {
      background: var(--clay-brand-pink);
      color: #ffffff;
    }

    .score-high {
      background: var(--clay-brand-peach);
      color: var(--clay-ink);
    }

    .score-medium {
      background: var(--clay-brand-ochre);
      color: var(--clay-ink);
    }

    .score-low {
      background: var(--clay-brand-mint);
      color: var(--clay-ink);
    }

    .card-subline {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 12px;
      color: var(--clay-muted);
      margin-bottom: 10px;
    }

    .invoice-id-tag {
      font-weight: 600;
      color: var(--clay-body-strong);
      font-family: monospace;
    }

    .card-footer-tags {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 12px;
    }

    .status-chip {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 2px 8px;
      border-radius: var(--rounded-sm);
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.2px;
    }

    .chip-partial {
      background: rgba(232, 185, 74, 0.25);
      color: #8c6307;
    }

    .chip-unmatched {
      background: rgba(255, 77, 139, 0.18);
      color: #b90e4f;
    }

    .chip-duplicate {
      background: rgba(184, 164, 237, 0.35);
      color: #432b85;
    }

    .overdue-tag {
      font-weight: 600;
      color: var(--clay-muted);
    }

    .overdue-tag.alert-urgent {
      color: var(--clay-error);
    }

    /* ==========================================================================
       COLUMN 2: CONVERSATIONAL ACTION STUDIO (FLEX 1)
       ========================================================================== */
    .action-studio-col {
      flex: 1;
      display: flex;
      flex-direction: column;
      background: var(--clay-canvas);
      position: relative;
      overflow: hidden;
    }

    /* Active Case Header Band */
    .studio-case-header {
      height: 64px;
      background: var(--clay-surface-white);
      border-bottom: 1px solid var(--clay-hairline);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 32px;
      flex-shrink: 0;
    }

    .case-header-left {
      display: flex;
      align-items: center;
      gap: 14px;
    }

    .case-avatar-box {
      width: 38px;
      height: 38px;
      background: var(--clay-surface-card);
      border: 1px solid var(--clay-hairline);
      border-radius: var(--rounded-md);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 18px;
    }

    .case-title-block h2 {
      font-size: 16px;
      font-weight: 600;
      letter-spacing: -0.3px;
      color: var(--clay-ink);
    }

    .case-title-block p {
      font-size: 12px;
      color: var(--clay-muted);
    }

    .case-header-badges {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .safety-shield-pill {
      background: var(--clay-surface-soft);
      border: 1px solid var(--clay-hairline-strong);
      padding: 4px 12px;
      border-radius: var(--rounded-pill);
      font-size: 12px;
      font-weight: 600;
      color: var(--clay-body-strong);
      display: flex;
      align-items: center;
      gap: 6px;
    }

    /* Message Workspace Container */
    .studio-messages-stream {
      flex: 1;
      overflow-y: auto;
      padding: 32px;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }

    .case-context-banner {
      background: var(--clay-surface-soft);
      border: 1px solid var(--clay-hairline);
      border-radius: var(--rounded-lg);
      padding: 16px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .context-metric-grid {
      display: flex;
      gap: 24px;
    }

    .context-metric-item {
      display: flex;
      flex-direction: column;
    }

    .metric-label {
      font-size: 11px;
      color: var(--clay-muted);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      font-weight: 600;
    }

    .metric-val {
      font-size: 16px;
      font-weight: 700;
      color: var(--clay-ink);
    }

    /* Message Bubbles */
    .msg-row {
      display: flex;
      width: 100%;
    }

    .msg-row.in {
      justify-content: flex-start;
    }

    .msg-row.out {
      justify-content: flex-end;
    }

    .msg-bubble-agent {
      max-width: 780px;
      background: var(--clay-surface-white);
      border: 1px solid var(--clay-hairline);
      border-radius: var(--rounded-xl);
      padding: 22px 26px;
      box-shadow: var(--shadow-subtle);
      position: relative;
    }

    .agent-header-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 12px;
    }

    .agent-identity {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .agent-avatar-small {
      width: 24px;
      height: 24px;
      background: var(--clay-primary);
      color: #ffffff;
      border-radius: var(--rounded-xs);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 12px;
    }

    .agent-name {
      font-size: 13px;
      font-weight: 600;
      color: var(--clay-ink);
    }

    .agent-meta-time {
      font-size: 11px;
      color: var(--clay-muted);
    }

    .msg-body-text {
      font-size: 15px;
      line-height: 1.6;
      color: var(--clay-body-strong);
      white-space: pre-wrap;
    }

    /* User Message Bubble */
    .msg-bubble-user {
      max-width: 600px;
      background: var(--clay-primary);
      color: #ffffff;
      border-radius: var(--rounded-xl);
      padding: 16px 22px;
      box-shadow: var(--shadow-subtle);
    }

    .msg-bubble-user .msg-body-text {
      color: #ffffff;
    }

    .msg-bubble-user .user-meta-time {
      display: flex;
      justify-content: flex-end;
      gap: 4px;
      font-size: 11px;
      color: rgba(255, 255, 255, 0.6);
      margin-top: 6px;
    }

    /* ==========================================================================
       CLAY FEATURE CARD: STAGED ACTION & HUMAN-APPROVAL GATE
       ========================================================================== */
    .clay-feature-card {
      margin-top: 18px;
      background: var(--clay-surface-card);
      border: 1px solid var(--clay-hairline-strong);
      border-radius: var(--rounded-xl);
      padding: 24px;
      box-shadow: var(--shadow-subtle);
    }

    .feature-card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 14px;
    }

    .card-badge-pill {
      background: var(--clay-brand-lavender);
      color: var(--clay-ink);
      font-size: 11px;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: var(--rounded-pill);
      letter-spacing: 0.5px;
      text-transform: uppercase;
    }

    .draft-id-code {
      font-family: monospace;
      font-size: 12px;
      color: var(--clay-muted);
      font-weight: 600;
    }

    .draft-subject-title {
      font-size: 14px;
      font-weight: 600;
      color: var(--clay-ink);
      margin-bottom: 10px;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .draft-body-scrollbox {
      background: var(--clay-surface-white);
      border: 1px solid var(--clay-hairline);
      border-radius: var(--rounded-md);
      padding: 16px;
      font-size: 13.5px;
      line-height: 1.55;
      color: var(--clay-body);
      max-height: 220px;
      overflow-y: auto;
      white-space: pre-wrap;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace;
    }

    .approval-gate-bar {
      margin-top: 18px;
      padding-top: 16px;
      border-top: 1px solid var(--clay-hairline);
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .gate-notice {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 12px;
      font-weight: 600;
      color: var(--clay-body-strong);
    }

    .gate-actions-row {
      display: flex;
      gap: 12px;
    }

    .btn-clay-primary {
      flex: 1;
      height: 44px;
      background: var(--clay-primary);
      color: var(--clay-on-primary);
      border: none;
      border-radius: var(--rounded-md);
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      transition: all 0.15s ease;
      box-shadow: var(--shadow-subtle);
    }

    .btn-clay-primary:hover {
      background: var(--clay-primary-active);
      transform: translateY(-1px);
    }

    .btn-clay-danger {
      flex: 1;
      height: 44px;
      background: var(--clay-surface-white);
      color: var(--clay-error);
      border: 1px solid rgba(239, 68, 68, 0.3);
      border-radius: var(--rounded-md);
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      transition: all 0.15s ease;
    }

    .btn-clay-danger:hover {
      background: #fef2f2;
      border-color: var(--clay-error);
    }

    /* Dispatched State Pill */
    .dispatched-status-card {
      margin-top: 14px;
      padding: 12px 16px;
      border-radius: var(--rounded-md);
      font-size: 13px;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .status-card-approved {
      background: var(--clay-brand-mint);
      color: var(--clay-ink);
      border: 1px solid rgba(0, 0, 0, 0.08);
    }

    .status-card-rejected {
      background: #fee2e2;
      color: #991b1b;
      border: 1px solid #f87171;
    }

    /* Quick Suggestion Chips (Clay category tabs) */
    .suggestions-strip {
      padding: 10px 32px 0;
      display: flex;
      gap: 8px;
      overflow-x: auto;
      flex-shrink: 0;
      scrollbar-width: none;
      -ms-overflow-style: none;
    }
    .suggestions-strip::-webkit-scrollbar {
      display: none;
    }

    .chip-pill {
      background: var(--clay-surface-card);
      border: 1px solid var(--clay-hairline-strong);
      color: var(--clay-ink);
      padding: 7px 14px;
      border-radius: var(--rounded-pill);
      font-size: 12.5px;
      font-weight: 500;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.15s ease;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .chip-pill:hover {
      background: var(--clay-brand-ochre);
      border-color: var(--clay-ink);
      transform: translateY(-1px);
    }

    /* Input Console */
    .studio-input-bar {
      padding: 16px 32px 24px;
      display: flex;
      align-items: center;
      gap: 12px;
      flex-shrink: 0;
    }

    .clay-input-box {
      flex: 1;
      height: 48px;
      background: var(--clay-surface-white);
      border: 1px solid var(--clay-hairline-strong);
      border-radius: var(--rounded-md);
      padding: 0 18px;
      font-size: 14.5px;
      color: var(--clay-ink);
      outline: none;
      transition: all 0.15s ease;
      box-shadow: var(--shadow-subtle);
    }

    .clay-input-box:focus {
      border-color: var(--clay-ink);
      box-shadow: 0 0 0 1px var(--clay-ink);
    }

    .btn-send-square {
      width: 48px;
      height: 48px;
      background: var(--clay-primary);
      color: #ffffff;
      border: none;
      border-radius: var(--rounded-md);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 18px;
      cursor: pointer;
      transition: all 0.15s ease;
      box-shadow: var(--shadow-subtle);
    }

    .btn-send-square:hover {
      background: var(--clay-primary-active);
      transform: translateY(-1px);
    }

    /* Typing Animation */
    .typing-pill {
      display: none;
      align-items: center;
      gap: 8px;
      font-size: 12px;
      color: var(--clay-muted);
      font-weight: 500;
      margin-bottom: 8px;
      padding-left: 32px;
    }

    .dot {
      width: 6px;
      height: 6px;
      background: var(--clay-primary);
      border-radius: 50%;
      animation: clayPulse 1.2s infinite ease-in-out;
    }
    .dot:nth-child(2) { animation-delay: 0.2s; }
    .dot:nth-child(3) { animation-delay: 0.4s; }

    @keyframes clayPulse {
      0%, 100% { opacity: 0.2; transform: scale(0.8); }
      50% { opacity: 1; transform: scale(1.1); }
    }

    /* ==========================================================================
       COLUMN 3: RESPONSIBLE AI OBSERVABILITY DRAWER (380px)
       ========================================================================== */
    .audit-drawer-col {
      width: 380px;
      border-left: 1px solid var(--clay-hairline);
      background: var(--clay-surface-soft);
      display: flex;
      flex-direction: column;
      flex-shrink: 0;
      transition: transform 0.2s ease;
    }

    .drawer-header {
      padding: 20px 24px;
      border-bottom: 1px solid var(--clay-hairline);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .drawer-title-group h3 {
      font-size: 16px;
      font-weight: 600;
      color: var(--clay-ink);
      letter-spacing: -0.3px;
    }

    .drawer-title-group p {
      font-size: 12px;
      color: var(--clay-muted);
    }

    .kpi-grid-2x2 {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      padding: 16px 20px;
      border-bottom: 1px solid var(--clay-hairline);
    }

    .kpi-card {
      border-radius: var(--rounded-md);
      padding: 14px;
      border: 1px solid rgba(0, 0, 0, 0.05);
      display: flex;
      flex-direction: column;
    }

    .kpi-mint {
      background: var(--clay-brand-mint);
      color: var(--clay-ink);
    }

    .kpi-peach {
      background: var(--clay-brand-peach);
      color: var(--clay-ink);
    }

    .kpi-lavender {
      background: var(--clay-brand-lavender);
      color: var(--clay-ink);
    }

    .kpi-ochre {
      background: var(--clay-brand-ochre);
      color: var(--clay-ink);
    }

    .kpi-title {
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.4px;
      opacity: 0.85;
    }

    .kpi-number {
      font-size: 19px;
      font-weight: 700;
      margin-top: 4px;
      letter-spacing: -0.5px;
    }

    .audit-stream-wrapper {
      flex: 1;
      overflow-y: auto;
      padding: 16px 20px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .audit-entry-card {
      background: var(--clay-surface-white);
      border: 1px solid var(--clay-hairline);
      border-radius: var(--rounded-md);
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 6px;
      font-size: 12px;
      box-shadow: var(--shadow-subtle);
    }

    .audit-entry-top {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .audit-time-stamp {
      font-family: monospace;
      font-size: 11px;
      color: var(--clay-muted);
    }

    .audit-event-pill {
      font-size: 10px;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: var(--rounded-pill);
    }

    .pill-silent-res {
      background: rgba(34, 197, 94, 0.15);
      color: #15803d;
    }

    .pill-escalation {
      background: rgba(239, 68, 68, 0.15);
      color: #b91c1c;
    }

    .pill-draft {
      background: rgba(184, 164, 237, 0.35);
      color: #5b21b6;
    }

    .pill-approval {
      background: rgba(232, 185, 74, 0.3);
      color: #854d0e;
    }

    .audit-action-text {
      font-weight: 600;
      color: var(--clay-ink);
      line-height: 1.35;
    }

    .audit-principle-tag {
      font-size: 11px;
      color: var(--clay-muted);
      display: flex;
      align-items: center;
      gap: 4px;
    }

    .audit-reasoning-desc {
      color: var(--clay-body);
      font-size: 11.5px;
      line-height: 1.4;
      background: var(--clay-surface-soft);
      padding: 6px 8px;
      border-radius: var(--rounded-xs);
    }

    /* Responsiveness */
    @media (max-width: 1200px) {
      .audit-drawer-col {
        position: absolute;
        right: 0;
        top: 64px;
        bottom: 0;
        z-index: 40;
        box-shadow: var(--shadow-pop);
        transform: translateX(100%);
      }
      .audit-drawer-col.open {
        transform: translateX(0);
      }
    }

    @media (max-width: 860px) {
      .exception-hub-col {
        width: 280px;
      }
      .nav-telemetry-group {
        display: none;
      }
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
          <span class="brand-subtitle">Invoice Guardian</span>
        </div>
      </a>
      <div class="agent-status-pill">
        <div class="status-pulse-dot"></div>
        <span>Autonomous Agent Active</span>
      </div>
    </div>

    <!-- Live Telemetry Group -->
    <div class="nav-telemetry-group">
      <div class="telemetry-pill pill-risk" title="Total invoice value currently in exception status">
        <span>⚠️</span>
        <span class="pill-count" id="telemetryRiskVal">$6,775</span>
        <span>At Risk</span>
      </div>
      <div class="telemetry-pill pill-silent" title="Routine invoices matched silently without disturbing you">
        <span>✅</span>
        <span class="pill-count" id="telemetrySilentCount">5</span>
        <span>Silently Resolved</span>
      </div>
      <div class="telemetry-pill pill-safety" title="Strict human approval enforced before any outbound message">
        <span>🛑</span>
        <span>Human-Approval Gate Active</span>
      </div>
    </div>

    <!-- User & Drawer Actions -->
    <div class="nav-user-actions">
      <div class="user-profile-badge">
        <div class="user-avatar-circle">👩‍🎨</div>
        <div>
          <div class="user-meta-name">Priya Sharma</div>
          <div class="user-meta-role">Brand & UI Designer</div>
        </div>
      </div>
      <button class="btn-clay-secondary" id="btnToggleDrawer" onclick="toggleAuditDrawer()">
        <span>📜</span>
        <span>Audit Trail</span>
      </button>
    </div>
  </header>

  <!-- ========================================================================
       3-COLUMN WORKSPACE
       ======================================================================== -->
  <main class="clay-workspace">

    <!-- COLUMN 1: EXCEPTION HUB -->
    <aside class="exception-hub-col">
      <div class="hub-header">
        <div class="hub-header-top">
          <h1 class="hub-title">Exception Hub</h1>
          <span class="hub-badge" id="exceptionsCountBadge">4 Exceptions</span>
        </div>
        <p class="hub-subline">Ranked by <code>(Amount) × (Days Overdue)</code> to surface highest financial stakes first.</p>
      </div>

      <!-- Filter Tabs -->
      <div class="hub-filter-tabs">
        <button class="category-tab active" onclick="filterExceptions('ALL', this)">All (4)</button>
        <button class="category-tab" onclick="filterExceptions('CRITICAL', this)">Critical (2)</button>
        <button class="category-tab" onclick="filterExceptions('PARTIAL', this)">Underpaid</button>
        <button class="category-tab" onclick="filterExceptions('UNMATCHED', this)">Overdue</button>
      </div>

      <!-- Exception Cards Queue -->
      <div class="exception-list" id="exceptionQueue">
        <!-- Rendered dynamically -->
      </div>
    </aside>

    <!-- COLUMN 2: CONVERSATIONAL ACTION STUDIO -->
    <section class="action-studio-col">
      <!-- Active Case Header -->
      <div class="studio-case-header">
        <div class="case-header-left">
          <div class="case-avatar-box" id="activeCaseIcon">📄</div>
          <div class="case-title-block">
            <h2 id="activeCaseTitle">Loading exception case...</h2>
            <p id="activeCaseSubtitle">Synchronizing financial telemetry</p>
          </div>
        </div>
        <div class="case-header-badges">
          <div class="safety-shield-pill">
            <span>🔒</span>
            <span>Read-Only & Human-Gated</span>
          </div>
        </div>
      </div>

      <!-- Messages Stream -->
      <div class="studio-messages-stream" id="messagesStream">
        <!-- Banner and chat entries inserted dynamically -->
      </div>

      <!-- Typing Indicator -->
      <div class="typing-pill" id="typingIndicator">
        <span>CashGuard reasoning engine is analyzing options</span>
        <div class="dot"></div>
        <div class="dot"></div>
        <div class="dot"></div>
      </div>

      <!-- Quick Action Suggestion Chips -->
      <div class="suggestions-strip" id="suggestionsStrip">
        <!-- Rendered per active exception -->
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

    <!-- COLUMN 3: RESPONSIBLE AI OBSERVABILITY DRAWER -->
    <aside class="audit-drawer-col" id="auditDrawer">
      <div class="drawer-header">
        <div class="drawer-title-group">
          <h3>Responsible AI Trail</h3>
          <p>Append-only transparent governance</p>
        </div>
        <button class="btn-clay-secondary" onclick="loadAuditFeed()" title="Refresh audit feed">
          ↻ Sync
        </button>
      </div>

      <!-- 2x2 Saturated KPI Grid -->
      <div class="kpi-grid-2x2">
        <div class="kpi-card kpi-mint">
          <span class="kpi-title">Total Invoiced</span>
          <span class="kpi-number">$25,550</span>
        </div>
        <div class="kpi-card kpi-peach">
          <span class="kpi-title">Cash At Risk</span>
          <span class="kpi-number" id="kpiAtRisk">$6,775</span>
        </div>
        <div class="kpi-card kpi-lavender">
          <span class="kpi-title">Silent Matches</span>
          <span class="kpi-number">5 Items</span>
        </div>
        <div class="kpi-card kpi-ochre">
          <span class="kpi-title">Human Sign-off</span>
          <span class="kpi-number">100% Gated</span>
        </div>
      </div>

      <!-- Stream of Audit Events -->
      <div class="audit-stream-wrapper" id="auditStream">
        <!-- Rendered dynamically -->
      </div>
    </aside>

  </main>

  <script>
    let allExceptions = [];
    let displayedExceptions = [];
    let currentExceptionIndex = 0;
    let activeFilter = 'ALL';

    const CONTEXT_SUGGESTIONS = {
      "INV-2026-004": [
        "Acknowledge milestone 1 deposit and confirm balance upon Sept 18 UAT",
        "Ask Dr. Elena for milestone 2 approval timeline",
        "Offer to deliver staging preview to expedite final $1,500"
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
      try {
        const res = await fetch("/api/exceptions");
        const data = await res.json();
        allExceptions = data.ranked_exceptions || [];
        displayedExceptions = [...allExceptions];
        renderSidebarQueue();
        loadAuditFeed();

        if (allExceptions.length > 0) {
          selectCase(0);
        }
      } catch (err) {
        console.error("Initialization error:", err);
      }
    }

    function renderSidebarQueue() {
      const container = document.getElementById("exceptionQueue");
      container.innerHTML = "";

      displayedExceptions.forEach((item, idx) => {
        const isSelected = allExceptions[currentExceptionIndex] && allExceptions[currentExceptionIndex].invoice_id === item.invoice_id;
        const card = document.createElement("div");
        card.className = `exception-card ${isSelected ? "active" : ""}`;
        card.onclick = () => {
          const globalIdx = allExceptions.findIndex(e => e.invoice_id === item.invoice_id);
          selectCase(globalIdx);
        };

        let scoreBadgeClass = "score-low";
        if (item.impact_score > 20000) scoreBadgeClass = "score-critical";
        else if (item.impact_score > 5000) scoreBadgeClass = "score-high";
        else if (item.impact_score > 0) scoreBadgeClass = "score-medium";

        let chipClass = "chip-partial";
        if (item.status === 'UNMATCHED') chipClass = "chip-unmatched";
        if (item.status === 'DUPLICATE_CLAIM') chipClass = "chip-duplicate";

        const invoiced = Number(item.invoiced_amount || item.amount || 0);
        const received = Number(item.bank_amount_seen || item.amount_received || 0);
        const variance = Number(item.variance || item.difference || (invoiced - received));
        const score = Number(item.impact_score || 0);

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
      if (btn) {
        btn.classList.add("active");
      }

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
      document.getElementById("activeCaseSubtitle").innerText = `Case #${item.rank} [${item.priority_tier}] • Impact Score: $${score.toLocaleString()} • Strictly Human-in-the-Loop`;
      document.getElementById("activeCaseIcon").innerText = item.status === 'DUPLICATE_CLAIM' ? '⚠️' : '📄';

      // Setup Case Banner and Clear Message Stream
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

      // Fetch initial agent alert
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
        appendAgentMessage(`Exception detected for ${item.client_name} (${item.invoice_id}). Total at risk: $${item.variance.toLocaleString()}. How would you like me to proceed?`);
      }
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
        cardHtml = `
          <div class="clay-feature-card" id="card-${stagedDraft.draft_id}">
            <div class="feature-card-header">
              <span class="card-badge-pill">Staged Client Action • Sent: False</span>
              <span class="draft-id-code">${stagedDraft.draft_id}</span>
            </div>
            <div class="draft-subject-title">
              <span>✉️</span>
              <span><strong>Subject:</strong> ${escapeHtml(stagedDraft.subject || 'Client Communication')}</span>
            </div>
            <div class="draft-body-scrollbox">${escapeHtml(stagedDraft.content)}</div>
            
            <div class="approval-gate-bar" id="gate-${stagedDraft.draft_id}">
              <div class="gate-notice">
                <span>🛑</span>
                <span>Strict Human-Approval Gate: Confirming will simulate client dispatch and commit to audit log.</span>
              </div>
              <div class="gate-actions-row">
                <button class="btn-clay-primary" onclick="confirmApproval('${stagedDraft.draft_id}', true)">
                  <span>✅</span> Approve & Dispatch Email
                </button>
                <button class="btn-clay-danger" onclick="confirmApproval('${stagedDraft.draft_id}', false)">
                  <span>❌</span> Reject / Revise Draft
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
      if (gateContainer) {
        gateContainer.innerHTML = `<span style="font-size: 13px; color: var(--clay-muted);">Verifying authorization and recording to audit trail...</span>`;
      }

      try {
        const res = await fetch("/api/chat/approve", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            draft_id: draftId,
            confirmed: isApproved,
            approved_by: "Priya Sharma (Freelancer)"
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
        entries.slice(0, 30).forEach(e => {
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

    function toggleAuditDrawer() {
      const drawer = document.getElementById("auditDrawer");
      drawer.classList.toggle("open");
      const btn = document.getElementById("btnToggleDrawer");
      btn.classList.toggle("active");
    }

    function showTyping(show) {
      const el = document.getElementById("typingIndicator");
      el.style.display = show ? "flex" : "none";
      const stream = document.getElementById("messagesStream");
      stream.scrollTop = stream.scrollHeight;
    }

    function handleKeyPress(e) {
      if (e.key === "Enter") {
        sendInstruction();
      }
    }

    function escapeHtml(str) {
      if (!str) return "";
      return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
    }

    window.onload = initApp;
  </script>
</body>
</html>
"""


async def get_index(request: Request) -> HTMLResponse:
    return HTMLResponse(HTML_TEMPLATE)


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
    gate_res = human_approval_gate(
        draft_id=draft_id,
        confirmed=confirmed,
        approved_by=approved_by,
        human_notes=f"Authorized via CashGuard Clay UI by {approved_by}",
    )
    return JSONResponse(gate_res)


async def get_audit_log(request: Request) -> JSONResponse:
    entries = audit_logger.get_recent_entries(limit=100)
    return JSONResponse({"entries": list(reversed(entries))})


routes = [
    Route("/", endpoint=get_index, methods=["GET"]),
    Route("/api/exceptions", endpoint=get_exceptions, methods=["GET"]),
    Route("/api/chat/start", endpoint=post_chat_start, methods=["POST"]),
    Route("/api/chat/reply", endpoint=post_chat_reply, methods=["POST"]),
    Route("/api/chat/approve", endpoint=post_chat_approve, methods=["POST"]),
    Route("/api/audit-log", endpoint=get_audit_log, methods=["GET"]),
]

app = Starlette(routes=routes)


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print(" 🛡️ CashGuard.AI — Clay Design System Application Running")
    print(" 👉 Open in your browser: http://localhost:8000")
    print("=" * 70 + "\n")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
