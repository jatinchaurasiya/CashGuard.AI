"""
CashGuard.AI — Streamlit Web Interface for AWS Hackathon Demo
Alternative lightweight demo UI for judges and public deployment.

Runs on port 8501 by default:
    streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0
"""

import os
import sys
import time
from datetime import datetime
import streamlit as st

from config import check_api_key_status, get_model_id
from tools.monitor import monitor_financial_feeds
from tools.matcher import match_invoices_to_bank_feed
from tools.prioritizer import prioritize_cash_impact
from tools.drafter import get_staged_drafts, clear_staged_drafts, update_staged_draft
from tools.approval_gate import human_approval_gate
from reasoning import CashGuardReasoningEngine
from audit_logger import audit_logger

# Page Configuration
st.set_page_config(
    page_title="CashGuard.AI — Autonomous Invoice Guardian",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling for Simulated WhatsApp & Professional Polish
st.markdown("""
<style>
  .whatsapp-bubble-agent {
    background-color: #005c4b;
    color: #e9edef;
    padding: 12px 16px;
    border-radius: 12px;
    border-top-left-radius: 2px;
    margin-bottom: 12px;
    max-width: 85%;
    box-shadow: 0 1px 3px rgba(0,0,0,0.2);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }
  .whatsapp-bubble-user {
    background-color: #202c33;
    color: #e9edef;
    padding: 12px 16px;
    border-radius: 12px;
    border-top-right-radius: 2px;
    margin-bottom: 12px;
    margin-left: auto;
    max-width: 85%;
    box-shadow: 0 1px 3px rgba(0,0,0,0.2);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }
  .staged-card {
    background: #111b21;
    border: 1.5px solid #00a884;
    border-radius: 12px;
    padding: 16px;
    margin: 14px 0;
  }
  .metric-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 14px;
    text-align: center;
  }
</style>
""", unsafe_allow_html=True)

# Session State Initialization
if "scan_completed" not in st.session_state:
    st.session_state.scan_completed = False
if "exceptions" not in st.session_state:
    st.session_state.exceptions = []
if "summary" not in st.session_state:
    st.session_state.summary = {}
if "selected_exception_idx" not in st.session_state:
    st.session_state.selected_exception_idx = 0
if "chat_history" not in st.session_state:
    st.session_state.chat_history = {}  # invoice_id -> list of messages
if "active_draft" not in st.session_state:
    st.session_state.active_draft = None

# Sidebar: AWS Hackathon & Telemetry
with st.sidebar:
    st.image("architecture-diagram.png", use_container_width=True)
    st.title("🛡️ CashGuard.AI")
    st.caption("AWS Agents for Humans Hackathon • Professional Track")

    # API Status Check
    status = check_api_key_status()
    if status["is_live"]:
        st.success("🟢 **OpenRouter Live LLM Active**")
        st.caption(f"Model: `{status['model_id']}` • Security: Encrypted Server-Side")
    else:
        st.info("ℹ️ **Fallback Simulation Active**")
        st.caption("Deterministic tools active • Protected Server-Side")

    st.divider()

    st.subheader("Responsible AI Pillars")
    st.markdown("""
    - 🔒 **100% Read-Only Ingestion**: Bank & invoice feeds are never mutated.
    - 🛑 **Human-Approval Gate**: No email or action is dispatched without human sign-off.
    - 📋 **Immutable Audit Log**: Every decision is cryptographically logged.
    """)

    st.divider()
    st.caption("Demo Persona: Priya Sharma (Solo Freelance Designer)")


# Main View: Header & Action Suite
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.title("Autonomous Invoice & Cash-Flow Guardian")
    st.write(
        "Silently reconciles routine payments in the background and surfaces high-stakes "
        "exceptions via simulated WhatsApp with human-gated approval."
    )

with col_h2:
    st.write("")
    if st.button("⚡ Run Demo Scan", type="primary", use_container_width=True):
        with st.spinner("Ingesting feeds, running matching algorithms, and prioritizing cash-impact..."):
            feeds = monitor_financial_feeds(feed_type="all")
            match_res = match_invoices_to_bank_feed(
                invoices=feeds.get("invoices", []),
                bank_transactions=feeds.get("bank_transactions", []),
                client_emails=feeds.get("client_emails", []),
                as_of_date_str="2026-09-06",
            )
            priorities = prioritize_cash_impact(
                exceptions=match_res.get("escalations", []),
                as_of_date_str="2026-09-06",
            )
            st.session_state.exceptions = priorities.get("ranked_exceptions", [])
            st.session_state.summary = match_res.get("summary", {})
            st.session_state.scan_completed = True
            st.session_state.selected_exception_idx = 0
            st.rerun()

# Telemetry Banner if Scan Run
if st.session_state.scan_completed:
    s = st.session_state.summary
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Silent Resolutions", f"{s.get('silent_resolutions_count', 0)} / {s.get('total_invoices_analyzed', 0)}", "0 user interruptions")
    m2.metric("Flagged Exceptions", f"{len(st.session_state.exceptions)}", "Require human eye")
    m3.metric("Cash Value at Risk", f"${sum(e.get('amount_at_risk', 0) for e in st.session_state.exceptions):,.2f}", "Prioritized by stakes")
    m4.metric("Engine Health", "100% Operational", "Deterministic + LLM")

st.divider()

# Main Interaction Tabs
tab_triage, tab_audit, tab_arch = st.tabs(["💬 WhatsApp Triage Studio", "📋 Responsible AI Audit Trail", "📐 System Architecture"])

with tab_triage:
    if not st.session_state.scan_completed:
        st.info("👋 Click **⚡ Run Demo Scan** above to ingest invoices, bank feeds, and client messages.")
    else:
        col_list, col_chat = st.columns([1, 2])

        # Left Column: Prioritized Exceptions Queue
        with col_list:
            st.subheader("⚠️ Priority Exception Queue")
            for i, exc in enumerate(st.session_state.exceptions):
                client = exc.get("client_name", "Unknown")
                inv_id = exc.get("invoice_id", "")
                score = exc.get("impact_score", 0)
                risk = exc.get("amount_at_risk", 0)
                days = exc.get("days_overdue", 0)
                status_label = exc.get("status", "")

                selected = (i == st.session_state.selected_exception_idx)
                btn_label = f"#{i+1} {client} (${risk:,.0f} • {days}d late)"
                
                if st.button(
                    btn_label,
                    key=f"exc_btn_{i}",
                    use_container_width=True,
                    type="primary" if selected else "secondary",
                ):
                    st.session_state.selected_exception_idx = i
                    st.rerun()

        # Right Column: Simulated WhatsApp Conversation & Staged Action
        with col_chat:
            cur_exc = st.session_state.exceptions[st.session_state.selected_exception_idx]
            inv_id = cur_exc.get("invoice_id", "")
            client = cur_exc.get("client_name", "")
            risk = cur_exc.get("amount_at_risk", 0)
            days = cur_exc.get("days_overdue", 0)
            issue = cur_exc.get("discrepancy_reason", "")

            st.markdown(f"### 📱 WhatsApp: {client} — {inv_id}")
            st.caption(f"Status: **{cur_exc.get('status')}** • Cash at Risk: **${risk:,.2f}** • Overdue: **{days} days**")

            # Initialize chat history for this invoice if not exists
            if inv_id not in st.session_state.chat_history:
                # Trigger Reasoning Engine to start conversation
                engine = CashGuardReasoningEngine.create()
                with st.spinner("CashGuard Agent analyzing case and drafting WhatsApp alert..."):
                    start_res = engine.start_exception_conversation(cur_exc)
                    initial_msg = start_res.get("initial_message", f"Exception on {inv_id} for ${risk:,.2f}.")
                    st.session_state.chat_history[inv_id] = [
                        {"role": "agent", "content": initial_msg, "time": datetime.now().strftime("%H:%M")}
                    ]
                    # Check staged drafts
                    drafts = get_staged_drafts()
                    active = next((d for d in reversed(drafts) if d.get("invoice_id") == inv_id), None)
                    st.session_state.active_draft = active

            # Render Chat Messages
            chat_container = st.container()
            with chat_container:
                for msg in st.session_state.chat_history[inv_id]:
                    if msg["role"] == "agent":
                        st.markdown(f"""
                        <div class="whatsapp-bubble-agent">
                          <div style="font-size: 11px; opacity: 0.8; margin-bottom: 4px;">🤖 CashGuard Agent • {msg['time']}</div>
                          <div>{msg['content']}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="whatsapp-bubble-user">
                          <div style="font-size: 11px; opacity: 0.8; margin-bottom: 4px;">👩‍🎨 Priya Sharma • {msg['time']}</div>
                          <div>{msg['content']}</div>
                        </div>
                        """, unsafe_allow_html=True)

            # Interactive Staged Action Card (Human Approval Gate)
            drafts = get_staged_drafts()
            active_draft = next((d for d in reversed(drafts) if d.get("invoice_id") == inv_id), None)

            if active_draft:
                st.markdown("---")
                st.markdown("#### 📝 Staged Outbound Action (Pending Human Authorization)")
                st.info("🔒 **Safety Contract Enforced:** `contract: { sent: false }`. Draft will NEVER be sent without explicit human sign-off.")

                edited_subject = st.text_input("Subject / Headline", value=active_draft.get("subject", ""), key=f"subj_{inv_id}")
                edited_content = st.text_area("Message Body (Editable inline before dispatch)", value=active_draft.get("content", ""), height=120, key=f"body_{inv_id}")

                c_app, c_rej = st.columns(2)
                with c_app:
                    if st.button("✓ Approve & Dispatch Follow-Up", type="primary", use_container_width=True, key=f"app_{inv_id}"):
                        gate_res = human_approval_gate(
                            draft_id=active_draft["draft_id"],
                            confirmed=True,
                            approved_by="Priya Sharma",
                            human_notes=f"Authorized via Streamlit UI with subject: {edited_subject}",
                        )
                        st.success(f"🚀 {gate_res['message']} (Logged to immutable audit trail)")
                        st.session_state.chat_history[inv_id].append({
                            "role": "agent",
                            "content": f"✅ Follow-up approved and dispatched to {active_draft.get('recipient_name', client)}. Case recorded in audit log.",
                            "time": datetime.now().strftime("%H:%M")
                        })
                        time.sleep(1)
                        st.rerun()

                with c_rej:
                    if st.button("✕ Reject / Hold", use_container_width=True, key=f"rej_{inv_id}"):
                        gate_res = human_approval_gate(
                            draft_id=active_draft["draft_id"],
                            confirmed=False,
                            approved_by="Priya Sharma",
                            human_notes="Rejected via Streamlit UI",
                        )
                        st.warning("🛑 Outbound action rejected. No message was sent.")
                        st.session_state.chat_history[inv_id].append({
                            "role": "agent",
                            "content": "🛑 Staged action dismissed. No outbound message was dispatched.",
                            "time": datetime.now().strftime("%H:%M")
                        })
                        time.sleep(1)
                        st.rerun()

            # User Reply Input
            st.markdown("---")
            user_input = st.chat_input("Reply to CashGuard Agent in plain language (e.g., 'Draft a firm reminder' or 'What did their email say?')...")
            if user_input:
                st.session_state.chat_history[inv_id].append({
                    "role": "user",
                    "content": user_input,
                    "time": datetime.now().strftime("%H:%M")
                })
                engine = CashGuardReasoningEngine.create()
                with st.spinner("CashGuard Agent reasoning..."):
                    reply_res = engine.handle_user_reply(
                        user_message=user_input,
                        conversation_history=st.session_state.chat_history[inv_id],
                        current_exception=cur_exc,
                    )
                    st.session_state.chat_history[inv_id].append({
                        "role": "agent",
                        "content": reply_res.get("agent_reply", "Understood. I have updated the draft."),
                        "time": datetime.now().strftime("%H:%M")
                    })
                st.rerun()

with tab_audit:
    st.subheader("📋 Append-Only Cryptographic Audit Trail")
    st.caption("Tracks all routine silent matches, exception escalations, LLM tool calls, and human approvals.")
    
    entries = audit_logger.get_recent_entries(limit=50)
    if entries:
        st.dataframe(entries, use_container_width=True)
    else:
        st.info("No audit events recorded yet. Run a demo scan to populate.")

with tab_arch:
    st.subheader("📐 System Architecture Diagram")
    st.image("architecture-diagram.png", use_container_width=True)
    st.markdown("""
    - **Strands Agent Core**: Orchestrates Monitor, Matcher, and Prioritizer tools.
    - **OpenRouter LLM Gateway**: Dynamically routes to `openrouter/free` meta-models with structured tool calling.
    - **Human-in-the-Loop Gate**: Enforces explicit human sign-off before any outbound communication.
    """)
