# AI Account & API Key Harvesters Suite 🚀

Automated multi-provider API key and token harvester toolkit for **9Router**, **Claude Code**, and AI coding assistants.

Built for fast, headless account creation using Cloudflare Catch-All email domains and Gmail IMAP automation.

---

## 📦 Projects Overview

| Provider | Folder | Output Format | Purpose / Capabilities |
| :--- | :--- | :--- | :--- |
| **Groq** | [`groq-api-harvester`](./groq-api-harvester/) | `email\|apiKey` | Ultra-fast inference (Llama 3.3 70B, Qwen 3 32B) |
| **OpenRouter** | [`openrouter-api-harvester`](./openrouter-api-harvester/) | `email\|apiKey` | Access to 20+ free models (`openrouter/free`, `cohere/north-mini-code:free`) |
| **Grok CLI** | [`grok-token-harvester`](./grok-token-harvester/) | JSON (`access_token`, `refresh_token`, etc.) | Direct Grok Code access via OAuth2 Device Code with Auto-Refresh |

---

## ⚙️ Quick Start

### 1. Requirements
- Python 3.10+
- Chrome / Chromium installed
- Gmail with App Password & Cloudflare Catch-All routing enabled

### 2. Setup Configuration
Copy `.env.example` to `.env` in the project folder you wish to run:
```bash
cp .env.example .env
```
Fill in your credentials:
```ini
GMAIL_BASE_EMAIL="your_email@gmail.com"
GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
CUSTOM_DOMAIN="yourdomain.com"
```

---

## 🚀 Running the Harvesters

### Groq API Key Harvester
```powershell
cd groq-api-harvester
pip install -r requirements.txt
python register_groq.py --count 2
python test_keys.py
```

### OpenRouter API Key Harvester
```powershell
cd openrouter-api-harvester
pip install -r requirements.txt
python register_openrouter.py --count 2
python test_keys.py
```

### Grok CLI Token Harvester (for 9Router Batch Import)
```powershell
cd grok-token-harvester
pip install -r requirements.txt
python register_grok_tokens.py --count 2
python test_grok_tokens.py
```

---

## 🔒 Security Notice
- Never commit `.env` or files containing harvested keys/tokens to any public or private repository.
- A strict `.gitignore` is provided to safeguard all secrets, keys, and tokens.
