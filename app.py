"""
CashGuard.AI - WhatsApp Web Simulated Chat Interface

A lightweight, pixel-perfect simulated WhatsApp Web interface for the demo video:
- Left sidebar: Prioritized exception cases with live Cash-Impact score badges.
- Main chat window:
  - Agent sends plain-language WhatsApp exception alerts.
  - Freelancer replies in plain text (with typing indicator).
  - Agent responds with formatted client draft actions.
  - Human-Approval Gate card: "Approve & Dispatch" or "Reject" before anything is sent.
- Live Responsible-AI Audit Trail modal for judges.

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
from reasoning import CashGuardReasoningEngine
from audit_logger import audit_logger, MD_LOG_PATH, JSONL_LOG_PATH

engine = CashGuardReasoningEngine.create()

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>WhatsApp Web — CashGuard AI 🛡️</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --wa-dark-bg: #0c1317;
      --wa-panel-bg: #111b21;
      --wa-header-bg: #202c33;
      --wa-message-in: #202c33;
      --wa-message-out: #005c4b;
      --wa-green: #00a884;
      --wa-green-hover: #06cf9c;
      --wa-text-primary: #e9edef;
      --wa-text-secondary: #8696a0;
      --wa-border: #222e35;
      --wa-hover: #182229;
      --wa-active: #2a3942;
      --wa-tick-blue: #53bdeb;
      --wa-red: #ea4335;
      --wa-card-bg: #182229;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      font-family: 'Segoe UI', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background-color: var(--wa-dark-bg);
      color: var(--wa-text-primary);
      height: 100vh;
      overflow: hidden;
      display: flex;
      justify-content: center;
      align-items: center;
    }

    .app-container {
      width: 100vw;
      height: 100vh;
      display: flex;
      background: var(--wa-panel-bg);
      box-shadow: 0 4px 20px rgba(0,0,0,0.6);
      position: relative;
    }

    /* Top banner */
    .hackathon-banner {
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 32px;
      background: linear-gradient(90deg, #1f2937, #065f46);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 16px;
      font-size: 12px;
      color: #34d399;
      font-weight: 600;
      z-index: 100;
      border-bottom: 1px solid rgba(255,255,255,0.1);
    }
    .hackathon-banner a {
      color: #a7f3d0;
      text-decoration: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .hackathon-banner a:hover { text-decoration: underline; }

    /* Left Sidebar */
    .sidebar {
      width: 380px;
      background: var(--wa-panel-bg);
      border-right: 1px solid var(--wa-border);
      display: flex;
      flex-direction: column;
      height: calc(100vh - 32px);
      margin-top: 32px;
    }

    .sidebar-header {
      height: 60px;
      background: var(--wa-header-bg);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 16px;
      border-bottom: 1px solid var(--wa-border);
    }

    .user-profile {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .avatar {
      width: 40px;
      height: 40px;
      border-radius: 50%;
      background: #025144;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
      border: 2px solid var(--wa-green);
    }

    .user-info h3 {
      font-size: 15px;
      font-weight: 600;
      color: var(--wa-text-primary);
    }
    .user-info p {
      font-size: 12px;
      color: var(--wa-text-secondary);
    }

    .header-icons {
      display: flex;
      gap: 14px;
      color: var(--wa-text-secondary);
      font-size: 18px;
      cursor: pointer;
    }

    .sidebar-search {
      padding: 8px 12px;
      background: var(--wa-panel-bg);
      border-bottom: 1px solid var(--wa-border);
    }

    .search-box {
      background: var(--wa-header-bg);
      border-radius: 8px;
      padding: 6px 12px;
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 13px;
      color: var(--wa-text-secondary);
    }

    .chat-list {
      flex: 1;
      overflow-y: auto;
    }

    .chat-section-title {
      padding: 10px 16px 4px;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--wa-green);
      font-weight: 700;
    }

    .chat-item {
      display: flex;
      align-items: center;
      padding: 12px 16px;
      cursor: pointer;
      border-bottom: 1px solid rgba(255,255,255,0.03);
      transition: background 0.15s;
      position: relative;
    }
    .chat-item:hover { background: var(--wa-hover); }
    .chat-item.active { background: var(--wa-active); }

    .chat-avatar {
      width: 46px;
      height: 46px;
      border-radius: 50%;
      background: #1f2c34;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 22px;
      margin-right: 14px;
      flex-shrink: 0;
    }

    .chat-details {
      flex: 1;
      min-width: 0;
    }

    .chat-top-row {
      display: flex;
      justify-content: space-between;
      margin-bottom: 4px;
    }

    .chat-title {
      font-size: 15px;
      font-weight: 600;
      color: var(--wa-text-primary);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .chat-time {
      font-size: 11px;
      color: var(--wa-text-secondary);
    }

    .chat-bottom-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 13px;
      color: var(--wa-text-secondary);
    }

    .chat-preview {
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 220px;
    }

    .badge-score {
      padding: 2px 7px;
      border-radius: 10px;
      font-size: 10px;
      font-weight: 700;
      color: #fff;
    }
    .badge-critical { background: #dc2626; }
    .badge-high { background: #d97706; }
    .badge-medium { background: #2563eb; }
    .badge-low { background: #4b5563; }

    /* Main Chat Window */
    .chat-window {
      flex: 1;
      display: flex;
      flex-direction: column;
      height: calc(100vh - 32px);
      margin-top: 32px;
      background: #0b141a;
      position: relative;
    }

    /* Subtle WhatsApp doodle background effect */
    .chat-window::before {
      content: "";
      position: absolute;
      top: 0; left: 0; right: 0; bottom: 0;
      opacity: 0.04;
      background-image: radial-gradient(#00a884 1px, transparent 1px);
      background-size: 20px 20px;
      pointer-events: none;
    }

    .chat-header {
      height: 60px;
      background: var(--wa-header-bg);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 16px;
      border-bottom: 1px solid var(--wa-border);
      z-index: 10;
    }

    .chat-header-info {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .chat-header-avatar {
      width: 40px;
      height: 40px;
      border-radius: 50%;
      background: #005c4b;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
    }

    .chat-header-title {
      font-size: 16px;
      font-weight: 600;
    }
    .chat-header-status {
      font-size: 12px;
      color: var(--wa-green);
    }

    .chat-header-actions {
      display: flex;
      gap: 12px;
      align-items: center;
    }

    .btn-audit {
      background: rgba(0, 168, 132, 0.15);
      border: 1px solid var(--wa-green);
      color: #34d399;
      font-size: 12px;
      font-weight: 600;
      padding: 6px 12px;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.2s;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .btn-audit:hover {
      background: var(--wa-green);
      color: #0c1317;
    }

    /* Message Area */
    .messages-container {
      flex: 1;
      overflow-y: auto;
      padding: 20px 60px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      z-index: 5;
    }

    .enc-notice {
      align-self: center;
      background: #182229;
      color: #ffd279;
      padding: 6px 14px;
      border-radius: 8px;
      font-size: 11.5px;
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 6px;
      border: 1px solid rgba(255, 210, 121, 0.15);
    }

    .msg-row {
      display: flex;
      width: 100%;
    }
    .msg-row.in { justify-content: flex-start; }
    .msg-row.out { justify-content: flex-end; }

    .msg-bubble {
      max-width: 68%;
      padding: 10px 14px;
      border-radius: 8px;
      font-size: 14.5px;
      line-height: 1.45;
      position: relative;
      box-shadow: 0 1px 2px rgba(0,0,0,0.3);
    }

    .msg-row.in .msg-bubble {
      background: var(--wa-message-in);
      color: var(--wa-text-primary);
      border-top-left-radius: 0;
    }

    .msg-row.out .msg-bubble {
      background: var(--wa-message-out);
      color: var(--wa-text-primary);
      border-top-right-radius: 0;
    }

    .msg-meta {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 4px;
      font-size: 11px;
      color: var(--wa-text-secondary);
      margin-top: 4px;
    }
    .msg-ticks {
      color: var(--wa-tick-blue);
      font-size: 13px;
    }

    /* Draft & Human Approval Card */
    .approval-card {
      margin-top: 10px;
      background: #111b21;
      border: 1px solid var(--wa-border);
      border-radius: 8px;
      padding: 12px;
    }
    .approval-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid var(--wa-border);
      padding-bottom: 8px;
      margin-bottom: 8px;
    }
    .approval-badge {
      background: rgba(234, 179, 8, 0.15);
      border: 1px solid #eab308;
      color: #fde047;
      font-size: 11px;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 4px;
    }
    .approval-subject {
      font-size: 13px;
      font-weight: 600;
      color: #93c5fd;
      margin-bottom: 6px;
    }
    .approval-body {
      background: #0b141a;
      padding: 10px;
      border-radius: 6px;
      font-size: 13px;
      color: var(--wa-text-primary);
      white-space: pre-wrap;
      max-height: 180px;
      overflow-y: auto;
      border: 1px solid rgba(255,255,255,0.05);
      font-family: monospace;
    }
    .approval-actions {
      display: flex;
      gap: 10px;
      margin-top: 12px;
    }
    .btn-approve {
      flex: 1;
      background: var(--wa-green);
      color: #0c1317;
      border: none;
      padding: 9px;
      border-radius: 6px;
      font-weight: 700;
      font-size: 13px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      transition: background 0.2s;
    }
    .btn-approve:hover { background: var(--wa-green-hover); }
    .btn-reject {
      flex: 1;
      background: rgba(239, 68, 68, 0.15);
      color: #f87171;
      border: 1px solid #ef4444;
      padding: 9px;
      border-radius: 6px;
      font-weight: 700;
      font-size: 13px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      transition: background 0.2s;
    }
    .btn-reject:hover { background: #ef4444; color: #fff; }

    .dispatched-tag {
      margin-top: 8px;
      padding: 6px 10px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .tag-success { background: rgba(0, 168, 132, 0.2); color: #34d399; border: 1px solid #059669; }
    .tag-blocked { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid #dc2626; }

    /* Quick Suggestion Chips */
    .suggestions-container {
      padding: 8px 60px 0;
      display: flex;
      gap: 8px;
      overflow-x: auto;
      z-index: 5;
    }
    .chip {
      background: #182229;
      border: 1px solid rgba(255,255,255,0.1);
      color: #34d399;
      padding: 6px 12px;
      border-radius: 16px;
      font-size: 12px;
      font-weight: 500;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.2s;
    }
    .chip:hover {
      background: rgba(0, 168, 132, 0.2);
      border-color: var(--wa-green);
    }

    /* Input Footer */
    .chat-footer {
      height: 64px;
      background: var(--wa-header-bg);
      display: flex;
      align-items: center;
      padding: 0 16px;
      gap: 12px;
      z-index: 10;
    }

    .footer-icon {
      font-size: 22px;
      color: var(--wa-text-secondary);
      cursor: pointer;
    }

    .input-box {
      flex: 1;
      height: 42px;
      background: #2a3942;
      border-radius: 8px;
      border: none;
      padding: 0 16px;
      color: var(--wa-text-primary);
      font-size: 14.5px;
      outline: none;
    }
    .input-box::placeholder { color: var(--wa-text-secondary); }

    .btn-send {
      width: 42px;
      height: 42px;
      border-radius: 50%;
      background: var(--wa-green);
      border: none;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #0c1317;
      font-size: 18px;
      cursor: pointer;
      transition: background 0.2s;
    }
    .btn-send:hover { background: var(--wa-green-hover); }

    /* Typing indicator */
    .typing-row {
      display: none;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      color: var(--wa-green);
      margin-left: 60px;
      margin-bottom: 8px;
    }
    .dot {
      width: 6px; height: 6px;
      background: var(--wa-green);
      border-radius: 50%;
      animation: blink 1.2s infinite ease-in-out;
    }
    .dot:nth-child(2) { animation-delay: 0.2s; }
    .dot:nth-child(3) { animation-delay: 0.4s; }
    @keyframes blink { 0%, 100% { opacity: 0.2; } 50% { opacity: 1; } }

    /* Modal */
    .modal-overlay {
      display: none;
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0,0,0,0.8);
      z-index: 200;
      justify-content: center;
      align-items: center;
    }
    .modal-content {
      width: 85vw;
      max-width: 900px;
      max-height: 80vh;
      background: var(--wa-panel-bg);
      border: 1px solid var(--wa-border);
      border-radius: 12px;
      display: flex;
      flex-direction: column;
      box-shadow: 0 10px 40px rgba(0,0,0,0.8);
    }
    .modal-header {
      padding: 16px 20px;
      border-bottom: 1px solid var(--wa-border);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .modal-header h3 { font-size: 18px; color: #34d399; font-weight: 700; }
    .modal-close { font-size: 20px; color: var(--wa-text-secondary); cursor: pointer; }
    .modal-body {
      padding: 20px;
      overflow-y: auto;
      font-size: 13px;
      color: var(--wa-text-primary);
    }
    .audit-table {
      width: 100%;
      border-collapse: collapse;
    }
    .audit-table th, .audit-table td {
      border: 1px solid var(--wa-border);
      padding: 8px 10px;
      text-align: left;
      font-size: 12px;
    }
    .audit-table th { background: #1f2c34; color: #34d399; font-weight: 600; }
    .audit-table tr:nth-child(even) { background: rgba(255,255,255,0.02); }
  </style>
</head>
<body>

  <div class="app-container">
    <!-- Hackathon Banner -->
    <div class="hackathon-banner">
      <span>🛡️ CashGuard.AI • AWS Agents for Humans Hackathon Demo</span>
      <a onclick="openAuditModal()">📜 View Responsible AI Audit Log</a>
    </div>

    <!-- Sidebar -->
    <div class="sidebar">
      <div class="sidebar-header">
        <div class="user-profile">
          <div class="avatar">👩‍🎨</div>
          <div class="user-info">
            <h3>Priya Sharma</h3>
            <p>Brand & Graphic Designer</p>
          </div>
        </div>
        <div class="header-icons">
          <span>⚙️</span>
        </div>
      </div>

      <div class="sidebar-search">
        <div class="search-box">
          <span>🔍</span>
          <span>Prioritized Cash-Impact Exceptions</span>
        </div>
      </div>

      <div class="chat-list" id="chatList">
        <div class="chat-section-title">Prioritized Exceptions Queue</div>
        <!-- Loaded via JavaScript -->
      </div>
    </div>

    <!-- Main Chat Window -->
    <div class="chat-window">
      <div class="chat-header">
        <div class="chat-header-info">
          <div class="chat-header-avatar">🛡️</div>
          <div>
            <div class="chat-header-title">CashGuard AI 🛡️</div>
            <div class="chat-header-status">online • cash-flow guardian active</div>
          </div>
        </div>
        <div class="chat-header-actions">
          <button class="btn-audit" onclick="openAuditModal()">
            <span>📜</span> Responsible AI Audit Trail
          </button>
        </div>
      </div>

      <div class="messages-container" id="messagesContainer">
        <div class="enc-notice">
          <span>🔒</span> End-to-end simulated: All actions strictly require your approval before sending.
        </div>
      </div>

      <div class="typing-row" id="typingIndicator">
        <span>CashGuard AI is thinking</span>
        <div class="dot"></div>
        <div class="dot"></div>
        <div class="dot"></div>
      </div>

      <div class="suggestions-container" id="suggestionsContainer">
        <!-- Loaded dynamically based on active exception -->
      </div>

      <div class="chat-footer">
        <span class="footer-icon">😊</span>
        <span class="footer-icon">📎</span>
        <input
          type="text"
          class="input-box"
          id="userInput"
          placeholder="Type your instruction to CashGuard (e.g. 'let it go', 'send reminder', 'refuse refund')..."
          onkeypress="handleKeyPress(event)"
        >
        <button class="btn-send" onclick="sendMessage()">➤</button>
      </div>
    </div>
  </div>

  <!-- Audit Modal -->
  <div class="modal-overlay" id="auditModal" onclick="closeModalOnOutsideClick(event)">
    <div class="modal-content">
      <div class="modal-header">
        <h3>🛡️ Responsible AI Audit Trail (Append-Only Log)</h3>
        <span class="modal-close" onclick="closeAuditModal()">✕</span>
      </div>
      <div class="modal-body">
        <p style="margin-bottom: 12px; color: var(--wa-text-secondary);">
          Evidence of responsible AI design: All decisions, silent resolutions, and human authorizations are permanently tracked.
        </p>
        <table class="audit-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Event</th>
              <th>Invoice</th>
              <th>Client</th>
              <th>Action Taken</th>
              <th>Principle</th>
              <th>Reasoning</th>
            </tr>
          </thead>
          <tbody id="auditTableBody">
            <!-- Loaded dynamically -->
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <script>
    let exceptions = [];
    let currentExceptionIndex = 0;
    let currentDraftId = null;

    const SUGGESTIONS = {
      "INV-2026-004": [
        "Acknowledge milestone 1 and confirm balance upon Sept 18 UAT",
        "Ask Dr. Elena for milestone 2 approval timeline"
      ],
      "INV-2026-005": [
        "Send polite reminder asking if board meeting signed off",
        "Ask Arthur when autumn disbursements will be released"
      ],
      "INV-2026-007": [
        "Do not refund! Ask for Chase wire trace numbers",
        "Tell Chef Mateo we only received one payment"
      ],
      "INV-2026-009": [
        "Let it go, $25 is fine to write off as wire fee. Mark settled",
        "Ask them to reimburse the $25 wire fee"
      ]
    };

    async function init() {
      try {
        const res = await fetch("/api/exceptions");
        const data = await res.json();
        exceptions = data.ranked_exceptions || [];
        renderSidebar();
        if (exceptions.length > 0) {
          selectException(0);
        }
      } catch (err) {
        console.error("Error loading exceptions:", err);
      }
    }

    function renderSidebar() {
      const container = document.getElementById("chatList");
      container.innerHTML = `<div class="chat-section-title">Prioritized Exceptions Queue (${exceptions.length})</div>`;

      exceptions.forEach((item, idx) => {
        const tierClass = `badge-${item.priority_tier.toLowerCase()}`;
        const itemEl = document.createElement("div");
        itemEl.className = `chat-item ${idx === currentExceptionIndex ? "active" : ""}`;
        itemEl.onclick = () => selectException(idx);
        itemEl.innerHTML = `
          <div class="chat-avatar">${item.status === 'DUPLICATE_CLAIM' ? '⚠️' : '📄'}</div>
          <div class="chat-details">
            <div class="chat-top-row">
              <span class="chat-title">${item.client_name}</span>
              <span class="badge-score ${tierClass}">$${item.impact_score.toLocaleString()}</span>
            </div>
            <div class="chat-bottom-row">
              <span class="chat-preview">${item.invoice_id} • ${item.status}</span>
              <span class="chat-time">${item.days_overdue}d overdue</span>
            </div>
          </div>
        `;
        container.appendChild(itemEl);
      });
    }

    async function selectException(index) {
      currentExceptionIndex = index;
      renderSidebar();
      const item = exceptions[index];
      const container = document.getElementById("messagesContainer");
      container.innerHTML = `
        <div class="enc-notice">
          <span>🔒</span> Case #${item.rank} [${item.priority_tier}] • Impact Score: $${item.impact_score.toLocaleString()} • Strictly Human-in-the-Loop
        </div>
      `;

      renderSuggestions(item.invoice_id);

      // Fetch initial WhatsApp alert from CashGuard
      showTyping(true);
      try {
        const res = await fetch("/api/chat/start", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ exception: item })
        });
        const data = await res.json();
        showTyping(false);
        addMessage(data.draft.content, "in");
      } catch (e) {
        showTyping(false);
        addMessage("Hey Priya! Exception flagged for " + item.client_name + " (" + item.invoice_id + "). How would you like to handle this?", "in");
      }
    }

    function renderSuggestions(invoiceId) {
      const container = document.getElementById("suggestionsContainer");
      container.innerHTML = "";
      const list = SUGGESTIONS[invoiceId] || ["Send a polite reminder", "Hold on this for now"];
      list.forEach(text => {
        const chip = document.createElement("div");
        chip.className = "chip";
        chip.innerText = "💡 " + text;
        chip.onclick = () => {
          document.getElementById("userInput").value = text;
          sendMessage();
        };
        container.appendChild(chip);
      });
    }

    function addMessage(text, direction, approvalData = null) {
      const container = document.getElementById("messagesContainer");
      const row = document.createElement("div");
      row.className = `msg-row ${direction}`;

      const now = new Date();
      const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

      let innerHtml = `
        <div class="msg-bubble">
          <div>${escapeHtml(text)}</div>
      `;

      if (approvalData) {
        currentDraftId = approvalData.draft_id;
        innerHtml += `
          <div class="approval-card" id="card-${approvalData.draft_id}">
            <div class="approval-header">
              <span class="approval-badge">🛑 HUMAN-APPROVAL GATE</span>
              <span style="font-size: 11px; color: var(--wa-text-secondary);">${approvalData.draft_id}</span>
            </div>
            <div class="approval-subject">✉️ Subject: ${escapeHtml(approvalData.subject || 'Client Communication')}</div>
            <div class="approval-body">${escapeHtml(approvalData.content)}</div>
            <div class="approval-actions" id="actions-${approvalData.draft_id}">
              <button class="btn-approve" onclick="submitApproval('${approvalData.draft_id}', true)">
                ✅ Approve & Dispatch Email
              </button>
              <button class="btn-reject" onclick="submitApproval('${approvalData.draft_id}', false)">
                ❌ Reject / Cancel
              </button>
            </div>
          </div>
        `;
      }

      innerHtml += `
          <div class="msg-meta">
            <span>${timeStr}</span>
            <span class="msg-ticks">✓✓</span>
          </div>
        </div>
      `;

      row.innerHTML = innerHtml;
      container.appendChild(row);
      container.scrollTop = container.scrollHeight;
    }

    async function sendMessage() {
      const input = document.getElementById("userInput");
      const text = input.value.trim();
      if (!text) return;

      input.value = "";
      addMessage(text, "out");

      const item = exceptions[currentExceptionIndex];
      showTyping(true);

      try {
        const res = await fetch("/api/chat/reply", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            exception: item,
            user_reply: text
          })
        });
        const data = await res.json();
        showTyping(false);

        const draft = data.draft;
        const msgText = "I've drafted the next client action according to your instruction: \\"" + (draft.action_intent || text) + "\\". Please review and approve before sending:";
        addMessage(msgText, "in", draft);
      } catch (err) {
        showTyping(false);
        addMessage("Sorry, I encountered an error preparing the draft. Please try again.", "in");
      }
    }

    async function submitApproval(draftId, approved) {
      const actionsEl = document.getElementById(`actions-${draftId}`);
      if (actionsEl) {
        actionsEl.innerHTML = `<span style="font-size: 12px; color: var(--wa-text-secondary);">Processing authorization...</span>`;
      }

      try {
        const res = await fetch("/api/chat/approve", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            draft_id: draftId,
            confirmed: approved,
            approved_by: "Priya (Freelancer)"
          })
        });
        const data = await res.json();

        if (actionsEl) {
          if (approved) {
            actionsEl.innerHTML = `
              <div class="dispatched-tag tag-success">
                <span>✅</span> Dispatched to client via Email (Authorized by Priya). Logged to Audit Trail!
              </div>
            `;
          } else {
            actionsEl.innerHTML = `
              <div class="dispatched-tag tag-blocked">
                <span>❌</span> Dispatch Halted & Cancelled by Priya. Logged to Audit Trail!
              </div>
            `;
          }
        }
      } catch (err) {
        if (actionsEl) {
          actionsEl.innerHTML = `<span style="color: #ef4444;">Error recording decision.</span>`;
        }
      }
    }

    function showTyping(show) {
      const el = document.getElementById("typingIndicator");
      el.style.display = show ? "flex" : "none";
      const container = document.getElementById("messagesContainer");
      container.scrollTop = container.scrollHeight;
    }

    function handleKeyPress(e) {
      if (e.key === "Enter") {
        sendMessage();
      }
    }

    async function openAuditModal() {
      const modal = document.getElementById("auditModal");
      modal.style.display = "flex";
      try {
        const res = await fetch("/api/audit-log");
        const data = await res.json();
        const tbody = document.getElementById("auditTableBody");
        tbody.innerHTML = "";

        data.entries.forEach(e => {
          const tr = document.createElement("tr");
          tr.innerHTML = `
            <td><code>${e.timestamp.slice(11, 19)}</code></td>
            <td><strong>${e.event_type}</strong></td>
            <td><code>${e.invoice_id}</code></td>
            <td>${e.client_name}</td>
            <td>${escapeHtml(e.action_taken)}</td>
            <td><em>${e.principle}</em></td>
            <td>${escapeHtml(e.reasoning_summary)}</td>
          `;
          tbody.appendChild(tr);
        });
      } catch (err) {
        console.error("Error loading audit log:", err);
      }
    }

    function closeAuditModal() {
      document.getElementById("auditModal").style.display = "none";
    }

    function closeModalOnOutsideClick(e) {
      if (e.target.id === "auditModal") {
        closeAuditModal();
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

    window.onload = init;
  </script>
</body>
</html>
"""


async def get_index(request: Request) -> HTMLResponse:
    return HTMLResponse(HTML_TEMPLATE)


async def get_exceptions(request: Request) -> JSONResponse:
    priorities = prioritize_cash_impact(as_of_date_str="2026-09-06")
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
    approved_by = body.get("approved_by", "Priya")
    gate_res = human_approval_gate(
        draft_id=draft_id,
        confirmed=confirmed,
        approved_by=approved_by,
        human_notes=f"Authorized via WhatsApp Web UI by {approved_by}",
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
    print(" 💬 CashGuard.AI — WhatsApp Web Simulation Running")
    print(" 👉 Open in your browser: http://localhost:8000")
    print("=" * 70 + "\n")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
