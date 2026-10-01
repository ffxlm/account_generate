import sys, os, urllib.request, urllib.error, json, time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KEYS_FILE = os.path.join(BASE_DIR, "keys", "groq_keys.txt")

if not os.path.exists(KEYS_FILE):
    print(f"[!] Keys file not found at: {KEYS_FILE}")
    sys.exit(1)

with open(KEYS_FILE, "r", encoding="utf-8") as f:
    lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

print(f"\n{'='*60}")
print(f"[*] Testing {len(lines)} Groq API Key(s) in {KEYS_FILE}")
print(f"{'='*60}\n")

valid_count = 0
for i, line in enumerate(lines, 1):
    if "|" in line:
        parts = line.split("|", 1)
    elif ":" in line:
        parts = line.split(":", 1)
    else:
        parts = [line]

    if len(parts) == 2:
        email, key = parts
    else:
        email, key = "unknown", line

    print(f"[{i}/{len(lines)}] Testing: {email}")
    print(f"       Key: {key[:10]}...{key[-6:]}")

    start_t = time.time()
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    data = {
        "model": "qwen/qwen3.8-27b",
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 5
    }

    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            dur = time.time() - start_t
            res = json.loads(resp.read().decode("utf-8"))
            valid_count += 1
            print(f"       Status: ✅ ACTIVE (Latency: {dur:.2f}s)\n")
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        print(f"       Status: ❌ FAILED (HTTP {e.code}: {err[:80]})\n")
    except Exception as e:
        print(f"       Status: ❌ ERROR ({e})\n")

print(f"{'='*60}")
print(f"[*] Summary: {valid_count}/{len(lines)} Keys are ACTIVE and ready to use in 9Router!")
print(f"{'='*60}\n")
