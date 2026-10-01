import os, sys, json, time, re, threading, subprocess, requests
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GROQ_FILE = os.path.join(BASE_DIR, "groq-api-harvester", "keys", "groq_keys.txt")
OPENROUTER_FILE = os.path.join(BASE_DIR, "openrouter-api-harvester", "keys", "openrouter_keys.txt")
GROK_FILE = os.path.join(BASE_DIR, "grok-token-harvester", "grok_accounts.json")

# Farming task tracker
farm_state = {
    "running": False,
    "provider": None,
    "count": 0,
    "log": ""
}

def read_groq_keys():
    keys = []
    if os.path.exists(GROQ_FILE):
        with open(GROQ_FILE, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "|" in line:
                    email, key = line.split("|", 1)
                else:
                    email, key = f"groq_key_{idx+1}", line
                keys.append({"id": f"groq_{idx}", "email": email.strip(), "key": key.strip()})
    return keys

def save_groq_keys(keys):
    os.makedirs(os.path.dirname(GROQ_FILE), exist_ok=True)
    with open(GROQ_FILE, "w", encoding="utf-8") as f:
        for k in keys:
            f.write(f"{k['email']}|{k['key']}\n")

def read_openrouter_keys():
    keys = []
    if os.path.exists(OPENROUTER_FILE):
        with open(OPENROUTER_FILE, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "|" in line:
                    email, key = line.split("|", 1)
                else:
                    email, key = f"openrouter_key_{idx+1}", line
                keys.append({"id": f"or_{idx}", "email": email.strip(), "key": key.strip()})
    return keys

def save_openrouter_keys(keys):
    os.makedirs(os.path.dirname(OPENROUTER_FILE), exist_ok=True)
    with open(OPENROUTER_FILE, "w", encoding="utf-8") as f:
        for k in keys:
            f.write(f"{k['email']}|{k['key']}\n")

def read_grok_accounts():
    if os.path.exists(GROK_FILE):
        try:
            with open(GROK_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for idx, acc in enumerate(data):
                        acc["id"] = f"grok_{idx}"
                    return data
        except Exception:
            return []
    return []

def save_grok_accounts(accounts):
    clean_accs = []
    for a in accounts:
        clean = {k: v for k, v in a.items() if k not in ["id", "status", "latency", "details"]}
        clean_accs.append(clean)
    os.makedirs(os.path.dirname(GROK_FILE), exist_ok=True)
    with open(GROK_FILE, "w", encoding="utf-8") as f:
        json.dump(clean_accs, f, indent=2)

def test_single_groq(key):
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    payload = {
        "model": "qwen/qwen3.8-27b",
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 5
    }
    t0 = time.time()
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=10)
        elapsed = time.time() - t0
        if r.status_code == 200:
            return {"active": True, "latency": round(elapsed, 2), "error": None}
        return {"active": False, "latency": round(elapsed, 2), "error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"active": False, "latency": None, "error": str(e)[:50]}

def test_single_openrouter(key):
    headers = {
        "Authorization": f"Bearer {key}",
        "HTTP-Referer": "https://localhost",
        "X-Title": "Dashboard Validator",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "openrouter/free",
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 5
    }
    t0 = time.time()
    try:
        r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=12)
        elapsed = time.time() - t0
        if r.status_code == 200:
            routed = r.json().get("model", "free")
            return {"active": True, "latency": round(elapsed, 2), "routed": routed, "error": None}
        return {"active": False, "latency": round(elapsed, 2), "error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"active": False, "latency": None, "error": str(e)[:50]}

def test_single_grok(access_token):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "User-Agent": "grok-pager/1.0.44 grok-shell/1.0.44 (linux; x86_64)",
        "x-xai-token-auth": "xai-grok-cli",
        "x-grok-client-version": "1.0.44"
    }
    t0 = time.time()
    try:
        r = requests.get("https://cli-chat-proxy.grok.com/v1/user", headers=headers, timeout=10)
        elapsed = time.time() - t0
        if r.status_code == 200:
            data = r.json()
            return {
                "active": True,
                "latency": round(elapsed, 2),
                "name": f"{data.get('firstName', '')} {data.get('lastName', '')}".strip(),
                "grokCode": data.get("hasGrokCodeAccess", False),
                "error": None
            }
        return {"active": False, "latency": round(elapsed, 2), "error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"active": False, "latency": None, "error": str(e)[:50]}

def run_farm_task(provider, count):
    global farm_state
    farm_state["running"] = True
    farm_state["provider"] = provider
    farm_state["count"] = count
    farm_state["log"] = f"Started harvest for {provider} (count={count})...\n"

    try:
        if provider == "groq":
            cwd = os.path.join(BASE_DIR, "groq-api-harvester")
            script = "register_groq.py"
        elif provider == "openrouter":
            cwd = os.path.join(BASE_DIR, "openrouter-api-harvester")
            script = "register_openrouter.py"
        elif provider == "grok":
            cwd = os.path.join(BASE_DIR, "grok-token-harvester")
            script = "register_grok_tokens.py"
        else:
            return

        cmd = [sys.executable, "-u", script, "--count", str(count)]
        proc = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        for line in proc.stdout:
            farm_state["log"] += line
        proc.wait()
        farm_state["log"] += f"\n[Completed with code {proc.returncode}]"
    except Exception as e:
        farm_state["log"] += f"\nError: {e}"
    finally:
        farm_state["running"] = False

HTML_PAGE = """<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI Harvester Suite - Management Dashboard</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          fontFamily: {
            sans: ['Inter', 'sans-serif'],
            mono: ['JetBrains Mono', 'monospace'],
          }
        }
      }
    }
  </script>
  <style>
    body {
      background-color: #0B0F19;
      color: #E2E8F0;
    }
    .glass-card {
      background: rgba(15, 23, 42, 0.7);
      backdrop-filter: blur(12px);
      border: 1px solid rgba(51, 65, 85, 0.6);
    }
    .glass-card:hover {
      border-color: rgba(100, 116, 139, 0.7);
    }
  </style>
</head>
<body class="min-h-screen font-sans flex flex-col antialiased selection:bg-indigo-500 selection:text-white">

  <!-- Header -->
  <header class="border-b border-slate-800 bg-slate-900/60 backdrop-blur sticky top-0 z-40">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="w-9 h-9 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
          <i class="fa-solid fa-server text-base"></i>
        </div>
        <div>
          <h1 class="text-base font-semibold tracking-tight text-white flex items-center gap-2">
            AI Harvester Suite
            <span class="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">9Router Bridge</span>
          </h1>
          <p class="text-xs text-slate-400">Manage, validate and export credentials to 9Router</p>
        </div>
      </div>
      
      <div class="flex items-center gap-2.5">
        <button onclick="refreshAllData()" id="refreshBtn" class="px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 transition flex items-center gap-2">
          <i class="fa-solid fa-rotate text-xs"></i>
          <span>Reload</span>
        </button>
        <button onclick="testAllKeys()" id="testAllBtn" class="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-medium text-white transition flex items-center gap-2 shadow-sm">
          <i class="fa-solid fa-vial-circle-check text-xs"></i>
          <span>Check All</span>
        </button>
      </div>
    </div>
  </header>

  <!-- Farming Status Banner (shows when farming is in progress) -->
  <div id="farmBanner" class="hidden border-b border-amber-500/30 bg-amber-500/10 px-4 py-2.5">
    <div class="max-w-7xl mx-auto flex items-center justify-between text-xs text-amber-300">
      <div class="flex items-center gap-2.5">
        <i class="fa-solid fa-circle-notch fa-spin text-amber-400"></i>
        <span id="farmBannerText">Harvesting in progress...</span>
      </div>
      <button onclick="openLogModal()" class="underline hover:text-white transition">View Live Log</button>
    </div>
  </div>

  <!-- Main Content -->
  <main class="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">

    <!-- Overview Statistics -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <div class="glass-card rounded-xl p-4 flex items-center justify-between">
        <div>
          <span class="text-xs font-medium uppercase tracking-wider text-slate-400">Groq API Keys</span>
          <div class="text-2xl font-bold text-white mt-1" id="groqCount">0</div>
        </div>
        <div class="w-10 h-10 rounded-lg bg-orange-500/10 border border-orange-500/20 flex items-center justify-center text-orange-400">
          <i class="fa-solid fa-bolt text-lg"></i>
        </div>
      </div>

      <div class="glass-card rounded-xl p-4 flex items-center justify-between">
        <div>
          <span class="text-xs font-medium uppercase tracking-wider text-slate-400">OpenRouter Keys</span>
          <div class="text-2xl font-bold text-white mt-1" id="openrouterCount">0</div>
        </div>
        <div class="w-10 h-10 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
          <i class="fa-solid fa-network-wired text-lg"></i>
        </div>
      </div>

      <div class="glass-card rounded-xl p-4 flex items-center justify-between">
        <div>
          <span class="text-xs font-medium uppercase tracking-wider text-slate-400">Grok CLI Accounts</span>
          <div class="text-2xl font-bold text-white mt-1" id="grokCount">0</div>
        </div>
        <div class="w-10 h-10 rounded-lg bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
          <i class="fa-solid fa-terminal text-lg"></i>
        </div>
      </div>
    </div>

    <!-- Providers Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">

      <!-- 1. GROQ CARD -->
      <section class="glass-card rounded-xl overflow-hidden flex flex-col">
        <div class="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/40">
          <div class="flex items-center gap-2.5">
            <i class="fa-solid fa-bolt text-orange-400"></i>
            <h2 class="text-sm font-semibold text-white">Groq API</h2>
          </div>
          <div class="flex items-center gap-1.5">
            <button onclick="copyAllGroq()" title="Copy all for 9Router" class="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs border border-slate-700 transition flex items-center gap-1">
              <i class="fa-solid fa-copy text-[11px]"></i>
              <span>All</span>
            </button>
            <button onclick="triggerFarm('groq', 1)" title="Farm 1 account" class="px-2 py-1 rounded bg-orange-600/20 hover:bg-orange-600/30 text-orange-300 text-xs border border-orange-500/30 transition flex items-center gap-1">
              <i class="fa-solid fa-plus text-[11px]"></i>
              <span>Farm</span>
            </button>
          </div>
        </div>
        
        <div class="p-4 flex-1 space-y-3" id="groqList">
          <div class="text-center py-8 text-xs text-slate-500">Loading keys...</div>
        </div>
      </section>

      <!-- 2. OPENROUTER CARD -->
      <section class="glass-card rounded-xl overflow-hidden flex flex-col">
        <div class="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/40">
          <div class="flex items-center gap-2.5">
            <i class="fa-solid fa-network-wired text-indigo-400"></i>
            <h2 class="text-sm font-semibold text-white">OpenRouter</h2>
          </div>
          <div class="flex items-center gap-1.5">
            <button onclick="copyAllOpenRouter()" title="Copy all for 9Router" class="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs border border-slate-700 transition flex items-center gap-1">
              <i class="fa-solid fa-copy text-[11px]"></i>
              <span>All</span>
            </button>
            <button onclick="triggerFarm('openrouter', 1)" title="Farm 1 account" class="px-2 py-1 rounded bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 text-xs border border-indigo-500/30 transition flex items-center gap-1">
              <i class="fa-solid fa-plus text-[11px]"></i>
              <span>Farm</span>
            </button>
          </div>
        </div>
        
        <div class="p-4 flex-1 space-y-3" id="openrouterList">
          <div class="text-center py-8 text-xs text-slate-500">Loading keys...</div>
        </div>
      </section>

      <!-- 3. GROK CLI CARD -->
      <section class="glass-card rounded-xl overflow-hidden flex flex-col">
        <div class="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/40">
          <div class="flex items-center gap-2.5">
            <i class="fa-solid fa-terminal text-sky-400"></i>
            <h2 class="text-sm font-semibold text-white">Grok CLI (OAuth)</h2>
          </div>
          <div class="flex items-center gap-1.5">
            <button onclick="copyAllGrok()" title="Copy JSON for 9Router Batch Import" class="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs border border-slate-700 transition flex items-center gap-1">
              <i class="fa-solid fa-file-export text-[11px]"></i>
              <span>Batch JSON</span>
            </button>
            <button onclick="triggerFarm('grok', 1)" title="Farm 1 account" class="px-2 py-1 rounded bg-sky-600/20 hover:bg-sky-600/30 text-sky-300 text-xs border border-sky-500/30 transition flex items-center gap-1">
              <i class="fa-solid fa-plus text-[11px]"></i>
              <span>Farm</span>
            </button>
          </div>
        </div>
        
        <div class="p-4 flex-1 space-y-3" id="grokList">
          <div class="text-center py-8 text-xs text-slate-500">Loading accounts...</div>
        </div>
      </section>

    </div>
  </main>

  <!-- Log Modal -->
  <div id="logModal" class="hidden fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
    <div class="glass-card rounded-xl max-w-2xl w-full flex flex-col overflow-hidden shadow-2xl border border-slate-700">
      <div class="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/70">
        <div class="flex items-center gap-2 text-sm font-semibold text-white">
          <i class="fa-solid fa-terminal text-slate-400"></i>
          <span>Live Harvest Log</span>
        </div>
        <button onclick="closeLogModal()" class="text-slate-400 hover:text-white p-1">
          <i class="fa-solid fa-xmark text-sm"></i>
        </button>
      </div>
      <div class="p-4 bg-black/60 font-mono text-xs text-emerald-400 h-80 overflow-y-auto whitespace-pre-wrap leading-relaxed" id="logContent">
        Connecting...
      </div>
    </div>
  </div>

  <!-- Toast Notification -->
  <div id="toast" class="fixed bottom-5 right-5 z-50 transform translate-y-12 opacity-0 transition duration-200 pointer-events-none px-4 py-2.5 rounded-lg bg-slate-800 border border-slate-700 text-xs font-medium text-white shadow-xl flex items-center gap-2">
    <i class="fa-solid fa-circle-check text-emerald-400" id="toastIcon"></i>
    <span id="toastMsg">Action completed</span>
  </div>

  <script>
    let appData = { groq: [], openrouter: [], grok: [] };

    function showToast(msg, isSuccess = true) {
      const toast = document.getElementById('toast');
      const toastMsg = document.getElementById('toastMsg');
      const toastIcon = document.getElementById('toastIcon');
      toastMsg.innerText = msg;
      toastIcon.className = isSuccess ? 'fa-solid fa-circle-check text-emerald-400' : 'fa-solid fa-circle-xmark text-rose-400';
      toast.classList.remove('translate-y-12', 'opacity-0');
      setTimeout(() => {
        toast.classList.add('translate-y-12', 'opacity-0');
      }, 2400);
    }

    async function copyToClipboard(text, btnElement, label = 'Copied') {
      try {
        await navigator.clipboard.writeText(text);
        if (btnElement) {
          const originalHTML = btnElement.innerHTML;
          btnElement.innerHTML = `<i class="fa-solid fa-check text-emerald-400"></i> ${label}`;
          setTimeout(() => { btnElement.innerHTML = originalHTML; }, 1800);
        }
        showToast('Copied to clipboard!');
      } catch (err) {
        showToast('Copy failed', false);
      }
    }

    async function refreshAllData() {
      try {
        const res = await fetch('/api/data');
        appData = await res.json();
        renderGroq();
        renderOpenRouter();
        renderGrok();
        document.getElementById('groqCount').innerText = appData.groq.length;
        document.getElementById('openrouterCount').innerText = appData.openrouter.length;
        document.getElementById('grokCount').innerText = appData.grok.length;
      } catch (err) {
        showToast('Failed to load data', false);
      }
    }

    function renderGroq() {
      const el = document.getElementById('groqList');
      if (appData.groq.length === 0) {
        el.innerHTML = '<div class="text-center py-8 text-xs text-slate-500">No Groq keys found</div>';
        return;
      }
      el.innerHTML = appData.groq.map(k => `
        <div class="rounded-lg border border-slate-800 bg-slate-900/50 p-3 space-y-2 text-xs">
          <div class="flex items-center justify-between">
            <span class="font-medium text-slate-200 truncate max-w-[180px]" title="${k.email}">${k.email}</span>
            <div id="status_${k.id}" class="text-[11px] text-slate-400 font-mono">
              ${k.latency ? `<span class="text-emerald-400"><i class="fa-solid fa-bolt text-[10px]"></i> ${k.latency}s</span>` : 'Unchecked'}
            </div>
          </div>
          <div class="font-mono text-[11px] text-slate-400 truncate bg-slate-950/60 px-2 py-1 rounded border border-slate-800/80">
            ${k.key.substring(0, 14)}...${k.key.substring(k.key.length - 6)}
          </div>
          <div class="flex items-center justify-between pt-1 border-t border-slate-800/50">
            <button onclick="testKey('groq', '${k.id}', '${k.key}')" class="text-slate-400 hover:text-white transition flex items-center gap-1 text-[11px]">
              <i class="fa-solid fa-arrows-rotate"></i> Test
            </button>
            <div class="flex items-center gap-2">
              <button onclick="copyToClipboard('${k.email}|${k.key}', this)" class="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition text-[11px] flex items-center gap-1 border border-slate-700">
                <i class="fa-solid fa-copy"></i> Copy
              </button>
              <button onclick="deleteKey('groq', '${k.id}')" title="Delete key" class="text-rose-400 hover:text-rose-300 p-1 transition">
                <i class="fa-solid fa-trash-can"></i>
              </button>
            </div>
          </div>
        </div>
      `).join('');
    }

    function renderOpenRouter() {
      const el = document.getElementById('openrouterList');
      if (appData.openrouter.length === 0) {
        el.innerHTML = '<div class="text-center py-8 text-xs text-slate-500">No OpenRouter keys found</div>';
        return;
      }
      el.innerHTML = appData.openrouter.map(k => `
        <div class="rounded-lg border border-slate-800 bg-slate-900/50 p-3 space-y-2 text-xs">
          <div class="flex items-center justify-between">
            <span class="font-medium text-slate-200 truncate max-w-[180px]" title="${k.email}">${k.email}</span>
            <div id="status_${k.id}" class="text-[11px] text-slate-400 font-mono">
              ${k.latency ? `<span class="text-emerald-400"><i class="fa-solid fa-bolt text-[10px]"></i> ${k.latency}s</span>` : 'Unchecked'}
            </div>
          </div>
          <div class="font-mono text-[11px] text-slate-400 truncate bg-slate-950/60 px-2 py-1 rounded border border-slate-800/80">
            ${k.key.substring(0, 14)}...${k.key.substring(k.key.length - 6)}
          </div>
          <div class="flex items-center justify-between pt-1 border-t border-slate-800/50">
            <button onclick="testKey('openrouter', '${k.id}', '${k.key}')" class="text-slate-400 hover:text-white transition flex items-center gap-1 text-[11px]">
              <i class="fa-solid fa-arrows-rotate"></i> Test
            </button>
            <div class="flex items-center gap-2">
              <button onclick="copyToClipboard('${k.email}|${k.key}', this)" class="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition text-[11px] flex items-center gap-1 border border-slate-700">
                <i class="fa-solid fa-copy"></i> Copy
              </button>
              <button onclick="deleteKey('openrouter', '${k.id}')" title="Delete key" class="text-rose-400 hover:text-rose-300 p-1 transition">
                <i class="fa-solid fa-trash-can"></i>
              </button>
            </div>
          </div>
        </div>
      `).join('');
    }

    function renderGrok() {
      const el = document.getElementById('grokList');
      if (appData.grok.length === 0) {
        el.innerHTML = '<div class="text-center py-8 text-xs text-slate-500">No Grok accounts found</div>';
        return;
      }
      el.innerHTML = appData.grok.map(a => `
        <div class="rounded-lg border border-slate-800 bg-slate-900/50 p-3 space-y-2 text-xs">
          <div class="flex items-center justify-between">
            <span class="font-medium text-slate-200 truncate max-w-[180px]" title="${a.email}">${a.email}</span>
            <div id="status_${a.id}" class="text-[11px] text-slate-400 font-mono">
              ${a.latency ? `<span class="text-emerald-400"><i class="fa-solid fa-bolt text-[10px]"></i> ${a.latency}s</span>` : 'Unchecked'}
            </div>
          </div>
          <div class="font-mono text-[11px] text-slate-400 truncate bg-slate-950/60 px-2 py-1 rounded border border-slate-800/80">
            Access: ${a.access_token.substring(0, 12)}...
          </div>
          <div class="flex items-center justify-between pt-1 border-t border-slate-800/50">
            <button onclick="testKey('grok', '${a.id}', '${a.access_token}')" class="text-slate-400 hover:text-white transition flex items-center gap-1 text-[11px]">
              <i class="fa-solid fa-arrows-rotate"></i> Test
            </button>
            <div class="flex items-center gap-2">
              <button onclick='copySingleGrok(${JSON.stringify(a)}, this)' class="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition text-[11px] flex items-center gap-1 border border-slate-700">
                <i class="fa-solid fa-copy"></i> JSON
              </button>
              <button onclick="deleteKey('grok', '${a.id}')" title="Delete account" class="text-rose-400 hover:text-rose-300 p-1 transition">
                <i class="fa-solid fa-trash-can"></i>
              </button>
            </div>
          </div>
        </div>
      `).join('');
    }

    async function testKey(provider, id, secret) {
      const stEl = document.getElementById(`status_${id}`);
      if (stEl) stEl.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin text-indigo-400"></i> Testing...';
      
      const res = await fetch('/api/test-single', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider, secret })
      });
      const data = await res.json();
      
      if (stEl) {
        if (data.active) {
          stEl.innerHTML = `<span class="text-emerald-400"><i class="fa-solid fa-circle-check text-[10px]"></i> ${data.latency}s</span>`;
        } else {
          stEl.innerHTML = `<span class="text-rose-400" title="${data.error}"><i class="fa-solid fa-circle-xmark text-[10px]"></i> Failed</span>`;
        }
      }
    }

    async function testAllKeys() {
      showToast('Testing all keys...');
      for (const k of appData.groq) { testKey('groq', k.id, k.key); }
      for (const k of appData.openrouter) { testKey('openrouter', k.id, k.key); }
      for (const a of appData.grok) { testKey('grok', a.id, a.access_token); }
    }

    async function deleteKey(provider, id) {
      if (!confirm('Are you sure you want to delete this credential?')) return;
      const res = await fetch('/api/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider, id })
      });
      if (res.ok) {
        showToast('Credential removed');
        refreshAllData();
      }
    }

    function copyAllGroq() {
      if (appData.groq.length === 0) return showToast('No Groq keys to copy', false);
      const text = appData.groq.map(k => `${k.email}|${k.key}`).join('\\n');
      copyToClipboard(text, null, 'Copied All');
    }

    function copyAllOpenRouter() {
      if (appData.openrouter.length === 0) return showToast('No OpenRouter keys to copy', false);
      const text = appData.openrouter.map(k => `${k.email}|${k.key}`).join('\\n');
      copyToClipboard(text, null, 'Copied All');
    }

    function copySingleGrok(accountObj, btn) {
      const clean = {
        access_token: accountObj.access_token,
        refresh_token: accountObj.refresh_token,
        id_token: accountObj.id_token,
        email: accountObj.email
      };
      copyToClipboard(JSON.stringify([clean], null, 2), btn);
    }

    function copyAllGrok() {
      if (appData.grok.length === 0) return showToast('No Grok accounts to copy', false);
      const cleanList = appData.grok.map(a => ({
        access_token: a.access_token,
        refresh_token: a.refresh_token,
        id_token: a.id_token,
        email: a.email
      }));
      copyToClipboard(JSON.stringify(cleanList, null, 2), null);
    }

    async function triggerFarm(provider, count) {
      const res = await fetch('/api/farm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider, count })
      });
      const data = await res.json();
      if (data.status === 'started') {
        showToast(`Harvest started for ${provider}`);
        checkFarmState();
      } else {
        showToast(data.message || 'Busy', false);
      }
    }

    let pollInterval = null;
    async function checkFarmState() {
      const res = await fetch('/api/farm-status');
      const state = await res.json();
      const banner = document.getElementById('farmBanner');
      const text = document.getElementById('farmBannerText');
      const logBox = document.getElementById('logContent');

      if (state.running) {
        banner.classList.remove('hidden');
        text.innerText = `Harvesting ${state.provider} in progress...`;
        logBox.innerText = state.log;
        logBox.scrollTop = logBox.scrollHeight;
        if (!pollInterval) {
          pollInterval = setInterval(checkFarmState, 2500);
        }
      } else {
        banner.classList.add('hidden');
        if (pollInterval) {
          clearInterval(pollInterval);
          pollInterval = null;
          refreshAllData();
          showToast('Harvest completed!');
        }
      }
    }

    function openLogModal() {
      document.getElementById('logModal').classList.remove('hidden');
    }

    function closeLogModal() {
      document.getElementById('logModal').classList.add('hidden');
    }

    // Initial Load
    refreshAllData();
    setInterval(checkFarmState, 4000);
  </script>
</body>
</html>
"""

class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
        elif path == "/api/data":
            data = {
                "groq": read_groq_keys(),
                "openrouter": read_openrouter_keys(),
                "grok": read_grok_accounts()
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))
        elif path == "/api/farm-status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(farm_state).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        try:
            payload = json.loads(body)
        except Exception:
            payload = {}

        if path == "/api/test-single":
            provider = payload.get("provider")
            secret = payload.get("secret")
            if provider == "groq":
                res = test_single_groq(secret)
            elif provider == "openrouter":
                res = test_single_openrouter(secret)
            elif provider == "grok":
                res = test_single_grok(secret)
            else:
                res = {"active": False, "error": "Unknown provider"}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(res).encode("utf-8"))

        elif path == "/api/delete":
            provider = payload.get("provider")
            item_id = payload.get("id")
            if provider == "groq":
                keys = [k for k in read_groq_keys() if k["id"] != item_id]
                save_groq_keys(keys)
            elif provider == "openrouter":
                keys = [k for k in read_openrouter_keys() if k["id"] != item_id]
                save_openrouter_keys(keys)
            elif provider == "grok":
                accs = [a for a in read_grok_accounts() if a.get("id") != item_id]
                save_grok_accounts(accs)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode("utf-8"))

        elif path == "/api/farm":
            global farm_state
            if farm_state["running"]:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "busy", "message": "Another harvest is already running"}).encode("utf-8"))
            else:
                provider = payload.get("provider", "groq")
                count = int(payload.get("count", 1))
                threading.Thread(target=run_farm_task, args=(provider, count), daemon=True).start()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "started"}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

def main():
    port = 5050
    server = ThreadingHTTPServer(("0.0.0.0", port), DashboardHandler)
    print("=" * 65)
    print("   AI HARVESTER SUITE - WEB DASHBOARD")
    print(f"   Local URL   : http://localhost:{port}")
    print(f"   Network URL : http://0.0.0.0:{port}")
    print("=" * 65)
    print("Dashboard server running. Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down dashboard server...")
        server.server_close()

if __name__ == "__main__":
    main()
