# AI Account and API Key Harvesters Suite

Automated multi-provider API key and token harvester toolkit for 9Router, Claude Code, and AI coding assistants.

Built for fast, headless account creation using Cloudflare Catch-All email domains and Gmail IMAP automation.

---

## Projects Overview

| Provider | Folder | Output Format | Purpose / Capabilities |
| :--- | :--- | :--- | :--- |
| **Groq** | [`groq-api-harvester`](./groq-api-harvester/) | `email\|apiKey` | High-speed inference (Llama 3.3 70B, Qwen 3 32B) |
| **OpenRouter** | [`openrouter-api-harvester`](./openrouter-api-harvester/) | `email\|apiKey` | Access to 20+ free models (`openrouter/free`, `cohere/north-mini-code:free`) |
| **Grok CLI** | [`grok-token-harvester`](./grok-token-harvester/) | JSON (`access_token`, `refresh_token`, etc.) | Direct Grok Code access via OAuth2 Device Code with Auto-Refresh |

---

## Web Management Dashboard

A modern, responsive, local web dashboard is included to manage all keys, test latencies, remove revoked keys, and export credentials to 9Router.

### Features
- **Centralized View**: Monitor Groq, OpenRouter, and Grok CLI credentials in one place.
- **One-Click 9Router Export**: Instant clipboard copy formatted for 9Router (`name|key` or Batch JSON).
- **Live Health Check**: Real-time latency verification against provider endpoints.
- **Revoked Key Cleanup**: Remove invalid or rate-limited credentials with one click.
- **In-App Harvesting**: Trigger background account generation and view live streaming logs.
- **Zero Heavy Dependencies**: Built with Python native threading, styled with Tailwind CSS and FontAwesome icons (no emojis).

### Running the Dashboard
```powershell
python dashboard.py
```
Open your browser at:
`http://localhost:5050`

---

## Quick Start

### 1. Requirements
- Python 3.10+
- Google Chrome / Chromium installed
- Gmail with App Password & Cloudflare Catch-All routing enabled

### 2. Setup Configuration
Copy `.env.example` to `.env` in the root folder or specific project folders:
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

## Running Harvesters via CLI

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

## VPS Deployment Guide (Ubuntu / Debian)

### 1. Install System Dependencies and Google Chrome
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git wget curl

wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt install -y ./google-chrome-stable_current_amd64.deb
rm google-chrome-stable_current_amd64.deb
```

### 2. Clone Repository and Install Python Packages
```bash
git clone https://github.com/ffxlm/account_generate.git
cd account_generate

python3 -m venv venv
source venv/bin/activate
pip install DrissionPage requests python-dotenv
```

### 3. Setup Environment Variables
```bash
cp .env.example .env
cp .env.example groq-api-harvester/.env
cp .env.example openrouter-api-harvester/.env
cp .env.example grok-token-harvester/.env
nano .env
```

### 4. Open Port 5050 and Run Dashboard 24/7
```bash
sudo ufw allow 5050

# Run in background via nohup:
nohup python3 dashboard.py > dashboard.log 2>&1 &

# Or run via PM2 (Process Manager):
sudo apt install -y npm
sudo npm install -g pm2
pm2 start dashboard.py --name "ai-dashboard" --interpreter python3
pm2 startup
pm2 save
```
Access the dashboard at `http://<your-vps-ip>:5050`.

---

## Security Notice
- Never commit `.env` or files containing harvested keys/tokens to any public or private repository.
- A strict `.gitignore` is provided to safeguard all secrets, keys, and tokens.
