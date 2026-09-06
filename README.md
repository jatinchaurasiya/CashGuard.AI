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
├── .env.example       # Template for your private API keys (never commit real keys!)
├── .gitignore          # Tells Git which temporary/secret files to ignore
├── config.py           # Central configuration: defines the LLM model in one single place
├── requirements.txt    # List of Python packages required to run the project
├── main.py             # Entry point: initializes the Strands Agent and runs a reconciliation demo
├── README.md           # Project documentation and guide (this file)
└── LICENSE             # MIT Open Source License
```

---

## 🚀 Quickstart Guide (Step-by-Step)

Follow these simple steps to run the agent on your computer:

### 1. Prerequisites
- **Python 3.10 or newer** installed on your system.
- An **OpenRouter API Key** (you can generate one for free at [openrouter.ai/keys](https://openrouter.ai/keys)).

### 2. Create and Activate a Virtual Environment
A virtual environment keeps your project dependencies clean and separate from other projects.

```bash
# Create the virtual environment named 'venv'
python3 -m venv venv

# Activate it (on Linux/macOS):
source venv/bin/activate

# (If you are on Windows, activate using: venv\Scripts\activate)
```

### 3. Install Dependencies
Install the Strands Agents SDK and other helper libraries:

```bash
pip install -r requirements.txt
```

### 4. Configure Your API Key
Copy the `.env.example` file to create your own `.env` file:

```bash
cp .env.example .env
```

Open the newly created `.env` file in your text editor and paste your OpenRouter API key:
```env
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxx
```

### 5. Run the Agent!
Run the main script:

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
