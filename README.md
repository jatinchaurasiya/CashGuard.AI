# CashGuard.AI 🛡️
### Invoice Exception & Cash-Flow Guardian for Solo Freelancers

> **Built for the AWS "Agents for Humans" Hackathon — Professional Agents Track**

---

## 💡 What is CashGuard.AI?

Freelancers and solo professionals spend hours every month manually cross-referencing:
1. **Issued Invoices** (What clients owe)
2. **Bank Feeds** (What was actually deposited)
3. **Client Emails & Messages** (Promises, disputes, and delayed milestone notices)

When an invoice is paid partially, paid late, or delayed due to an email thread buried in the inbox, freelancers often don't notice until their cash flow is already hurt.

**CashGuard.AI** is an autonomous AI agent that reconciles these three sources, automatically detects exceptions (underpayments, overdue bills, missing receipts, or broken promises), and drafts professional follow-up actions to keep cash flow safe.

---

## 🛠️ Architecture & Tech Stack

- **Orchestration**: Built with the **Strands Agents SDK** (an open-source, model-driven agent framework created by AWS).
- **Model Intelligence**: Powered by **OpenRouter**, allowing flexible, cost-effective switching across any top-tier LLM.
- **Language**: Python 3.10+

---

## 📂 Project Structure

```text
cashguard.ai/
├── .env.example         # Template for your private API keys (never commit real keys!)
├── .gitignore           # Tells Git which temporary/secret files to ignore
├── config.py            # Central configuration: defines active model, fallback chain & backoff
├── llm.py               # Resilient OpenRouter provider (fallbacks, 429 retries & logging)
├── tools/               # Strands Agent Tools
│   ├── monitor.py       # Monitor Tool: loads and monitors financial feeds
│   ├── matcher.py       # Matching Tool: deterministic reconciliation & silence/escalate logic
│   ├── prioritizer.py   # Cash-Impact Prioritizer: ranks exceptions by (amount) x (days overdue)
│   ├── drafter.py       # Draft Message Tool: structured tool-calling for WhatsApp alerts & emails (never sends)
│   └── approval_gate.py # Human-Approval Gate: enforces explicit user confirmation before any dispatch
├── audit_logger.py      # Responsible AI Audit Logger: immutable append-only trail (JSONL & Markdown)
├── reasoning.py         # OpenRouter-backed reasoning layer: WhatsApp alerts, reply interpretation & action drafting
├── test_connection.py   # Quick test script to verify LLM connection & check served model
├── test_monitor_tool.py # Test script to verify monitor tool file parsing
├── test_matcher_tool.py # Test script to verify deterministic arithmetic & classification
├── test_matcher_unit.py # Fast unit test suite verifying the 4 matching outcomes
├── test_prioritizer_tool.py # Test script verifying cash-impact ranking calculations
├── test_reasoning_layer.py  # Test suite verifying WhatsApp alerts, natural language interpretation & draft tool contract
├── test_approval_and_audit.py # Test suite verifying human approval gate & responsible AI audit logging
├── requirements.txt     # List of Python packages required to run the project
├── main.py              # Entry point: runs CashGuard reconciliation on sample data
├── data/                # Realistic synthetic demo datasets for Priya (graphic designer)
│   ├── invoices.json
│   ├── bank_feed.csv
│   ├── client_emails.json
│   ├── audit_log.jsonl  # Append-only machine-readable audit trail
│   └── audit_log.md     # Human-readable Responsible AI table for judges/demo
├── README.md            # Project documentation and guide (this file)
└── LICENSE              # MIT Open Source License
```

---

## 🚀 Quickstart Guide (Step-by-Step)

Follow these simple steps to run the agent on your computer:

### 1. Prerequisites
- **Python 3.10 or newer** installed on your system.
- An **OpenRouter API Key** (you can generate one for free at [openrouter.ai/keys](https://openrouter.ai/keys)).

### 2. Create and Activate a Virtual Environment
```bash
# Create the virtual environment
python3 -m venv venv

# Activate it (on Linux/macOS):
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Your API Key
Copy the `.env.example` file to create your own `.env` file:
```bash
cp .env.example .env
```
Open `.env` and paste your key:
```env
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxx
```

### 5. Verify Connection with the Test Script
Confirm that your connection works, test rate-limit resilience, and see which model responds:
```bash
python test_connection.py
```

### 6. Run the Full Reconciliation Agent!
Run the main CashGuard agent on the realistic demo datasets:
```bash
python main.py
```

The script will simulate a real-world freelance scenario (an overdue invoice, a partial bank deposit, and an accounting email explaining milestone payment terms) and output the AI agent's reconciliation analysis and drafted follow-up.

---

## ⚙️ Changing the LLM Model

The LLM model ID is defined in **only one place** in [`config.py`](config.py):

```python
DEFAULT_MODEL_ID: str = "openrouter/free"
```

To switch models, you can:
- **Option A**: Edit `DEFAULT_MODEL_ID` in `config.py` (e.g., change to `"anthropic/claude-3.5-sonnet"` or `"openai/gpt-4o-mini"`).
- **Option B**: Set the `MODEL_ID` environment variable in your `.env` file:
  ```env
  MODEL_ID=meta-llama/llama-3.3-70b-instruct
  ```

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details. (Meets hackathon open source licensing requirements).
