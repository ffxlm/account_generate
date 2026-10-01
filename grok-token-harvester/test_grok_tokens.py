import os, sys, json, requests, time

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

ACCOUNTS_FILE = os.path.join(os.path.dirname(__file__), "grok_accounts.json")

def test_tokens():
    if not os.path.exists(ACCOUNTS_FILE):
        print(f"[!] File not found: {ACCOUNTS_FILE}")
        return

    with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
        try:
            accounts = json.load(f)
        except Exception as e:
            print(f"[!] Error parsing JSON: {e}")
            return

    if not accounts:
        print("[!] No accounts found in grok_accounts.json")
        return

    print("=" * 65)
    print("   GROK CLI / 9ROUTER TOKEN VALIDATOR")
    print(f"   Found {len(accounts)} account(s) to test")
    print("=" * 65)

    valid_count = 0
    for idx, acc in enumerate(accounts, 1):
        email_addr = acc.get("email", f"Account-{idx}")
        access_tok = acc.get("access_token", "")
        refresh_tok = acc.get("refresh_token", "")

        print(f"\n[{idx}/{len(accounts)}] Testing: {email_addr}")
        masked_tok = f"{access_tok[:15]}...{access_tok[-6:]}" if len(access_tok) > 25 else access_tok
        print(f"      Access Token: {masked_tok}")

        headers = {
            "Authorization": f"Bearer {access_tok}",
            "Accept": "application/json",
            "User-Agent": "grok-pager/1.0.44 grok-shell/1.0.44 (linux; x86_64)",
            "x-xai-token-auth": "xai-grok-cli",
            "x-grok-client-version": "1.0.44"
        }

        t0 = time.time()
        try:
            r = requests.get("https://cli-chat-proxy.grok.com/v1/user", headers=headers, timeout=15)
            elapsed = time.time() - t0
            if r.status_code == 200:
                u_data = r.json()
                has_code = u_data.get("hasGrokCodeAccess", False)
                name = f"{u_data.get('firstName', '')} {u_data.get('lastName', '')}".strip()
                print(f"      [OK] Valid | Latency: {elapsed:.2f}s | Name: {name} | GrokCode: {has_code}")
                valid_count += 1
            else:
                print(f"      [FAIL] Status: {r.status_code} | Error: {r.text[:150]}")
        except Exception as e:
            print(f"      [ERROR] Network error: {e}")

    print("\n" + "=" * 65)
    print(f"   SUMMARY: {valid_count}/{len(accounts)} Token(s) are ACTIVE and VALID!")
    print("=" * 65)

if __name__ == "__main__":
    test_tokens()
