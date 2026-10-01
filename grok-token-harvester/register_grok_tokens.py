import os, sys, time, random, string, re, imaplib, email, argparse, json, requests
from DrissionPage import ChromiumPage, ChromiumOptions
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, ".env"))

CUSTOM_DOMAIN = os.getenv("CUSTOM_DOMAIN", "thirx.com").strip()
GMAIL_USER = os.getenv("GMAIL_BASE_EMAIL")
GMAIL_PASS = os.getenv("GMAIL_APP_PASSWORD")
PROXY = (os.getenv("GROK_PROXY") or "").strip()
ACCOUNTS_JSON = os.path.join(SCRIPT_DIR, "grok_accounts.json")

# xAI / Grok CLI OAuth2 Constants
CLIENT_ID = "b1a00492-073a-47ea-816f-4c329264a828"
SCOPE = "openid profile email offline_access grok-cli:access api:access conversations:read conversations:write"
DEVICE_CODE_URL = "https://auth.x.ai/oauth2/device/code"
TOKEN_URL = "https://auth.x.ai/oauth2/token"
USER_AGENT = "grok-pager/1.0.44 grok-shell/1.0.44 (linux; x86_64)"

def rand_str(length=8):
    return "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length))

def rand_name():
    firsts = ["Alex", "Jordan", "Taylor", "Morgan", "Sam", "Chris", "Pat", "Riley", "Casey", "Jamie"]
    lasts = ["Smith", "Taylor", "Brown", "Wilson", "Davies", "Evans", "Thomas", "Roberts", "Johnson", "Walker"]
    return random.choice(firsts), random.choice(lasts)

def get_latest_uids():
    """Get the highest UID currently in INBOX and Spam as a baseline."""
    uids_map = {}
    try:
        m = imaplib.IMAP4_SSL("imap.gmail.com")
        m.login(GMAIL_USER, GMAIL_PASS)
        for folder in ["INBOX", "[Gmail]/Spam"]:
            m.select(folder)
            _, d = m.uid('search', None, 'ALL')
            all_u = [int(x) for x in d[0].split()] if d and d[0] else []
            uids_map[folder] = max(all_u) if all_u else 0
        m.logout()
    except Exception as e:
        print(f"  [Baseline UID Error] {e}", flush=True)
    return uids_map

def fetch_otp(target_email, baseline_uids=None, timeout=90):
    """Wait for a NEW email addressed to target_email."""
    deadline = time.time() + timeout
    print(f"  Waiting up to {timeout}s for OTP to {target_email}...", flush=True)

    while time.time() < deadline:
        time.sleep(3)
        try:
            m = imaplib.IMAP4_SSL("imap.gmail.com")
            m.login(GMAIL_USER, GMAIL_PASS)

            for folder in ["INBOX", "[Gmail]/Spam"]:
                m.select(folder)
                base = (baseline_uids or {}).get(folder, 0)
                search_criterion = f'UID {base+1}:*' if base > 0 else 'ALL'

                _, d = m.uid('search', None, search_criterion)
                candidate_uids = [int(x) for x in d[0].split()] if d and d[0] else []
                new_uids = [u for u in candidate_uids if u > base]

                for u in reversed(new_uids):
                    _, md = m.uid('fetch', str(u).encode(), "(RFC822)")
                    msg = email.message_from_bytes(md[0][1])
                    to_addr = str(msg.get("To", "")).lower()
                    subj = str(msg.get("Subject", ""))

                    if target_email.lower() in to_addr or target_email.lower() in str(msg):
                        m_code = re.search(r"([A-Z0-9]{3})-?([A-Z0-9]{3})", subj)
                        if m_code:
                            code = m_code.group(1) + m_code.group(2)
                            print(f"  [+] Found new email UID {u} in {folder} -> OTP: {m_code.group(1)}-{m_code.group(2)}", flush=True)
                            m.logout()
                            return code
            m.logout()
        except Exception as e:
            pass

    return None

def authorize_device_code(page, target_email):
    """Requests device code and authorizes it using the currently logged-in browser session."""
    print("[*] Starting Grok CLI OAuth2 Device Authorization...", flush=True)
    req_data = {
        'client_id': CLIENT_ID,
        'scope': SCOPE,
        'referrer': 'grok-build'
    }
    req_headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'User-Agent': USER_AGENT
    }

    try:
        r = requests.post(DEVICE_CODE_URL, data=req_data, headers=req_headers, timeout=15)
        if r.status_code != 200:
            print(f"[!] Device code request failed: {r.status_code} {r.text}", flush=True)
            return None

        dev_res = r.json()
        device_code = dev_res.get('device_code')
        user_code = dev_res.get('user_code')
        verify_url = dev_res.get('verification_uri_complete')
        print(f"  [+] Device Code requested (User Code: {user_code})", flush=True)

        # Navigate to verify URL in browser
        page.get(verify_url)
        time.sleep(3)

        # Click Continue on device sign-in screen
        btn = page.ele('xpath://button[contains(text(), "Continue")]', timeout=8)
        if btn:
            try:
                btn.click(by_js=True)
            except Exception:
                pass
            time.sleep(3)

        # Click Allow / Authorize on consent screen
        allow_btn = page.ele('xpath://button[contains(text(), "Allow") or contains(text(), "Authorize") or contains(text(), "Confirm")]', timeout=6)
        if allow_btn:
            try:
                allow_btn.click(by_js=True)
            except Exception:
                pass
            time.sleep(2)

        # Poll token endpoint
        token_data = {
            'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
            'device_code': device_code,
            'client_id': CLIENT_ID
        }

        print("  [*] Polling for OAuth tokens from auth.x.ai...", flush=True)
        for poll in range(12):
            t_res = requests.post(TOKEN_URL, data=token_data, headers=req_headers, timeout=15)
            if t_res.status_code == 200:
                t_json = t_res.json()
                print("  [+] Received OAuth Tokens successfully!", flush=True)
                return {
                    "access_token": t_json.get("access_token"),
                    "refresh_token": t_json.get("refresh_token"),
                    "id_token": t_json.get("id_token"),
                    "email": target_email
                }
            time.sleep(3)

        print("[!] Polling for OAuth token timed out.", flush=True)
        return None

    except Exception as e:
        print(f"[!] Error in device code authorization: {e}", flush=True)
        return None

def register_and_harvest(index=1, total=1, headless=True):
    tag = f"grok_{rand_str(8)}"
    reg_email = f"{tag}@{CUSTOM_DOMAIN}"
    password = f"P@ssw0rd{rand_str(6)}!"
    first_name, last_name = rand_name()

    print(f"\n[{index}/{total}] ==========================================")
    print(f"[*] Starting Grok Registration & Token Harvest:")
    print(f"    Email: {reg_email}")
    print(f"    Name:  {first_name} {last_name}")
    print(f"==========================================")

    baseline_uids = get_latest_uids()

    co = ChromiumOptions()
    co.set_argument("--disable-blink-features=AutomationControlled")
    co.set_argument("--incognito")
    if headless:
        co.set_argument('--window-position=-2400,-2400')
        co.set_argument('--window-size=1280,900')
    if PROXY:
        proxy_addr = PROXY.replace("http://", "").replace("https://", "")
        co.set_argument(f"--proxy-server={proxy_addr}")

    page = None
    try:
        page = ChromiumPage(co)

        # 1. Open Sign-up page
        print("[1/5] Opening https://accounts.x.ai/sign-up?redirect=grok-com ...", flush=True)
        page.get("https://accounts.x.ai/sign-up?redirect=grok-com")
        time.sleep(3)

        # 2. Click email registration
        print("[2/5] Selecting email registration...", flush=True)
        page.run_js('''
            for (var b of document.querySelectorAll('button, [role="button"]')) {
                if ((b.innerText || '').toLowerCase().includes('email') || (b.innerText || '').includes('อีเมล')) {
                    b.click();
                    break;
                }
            }
        ''')
        time.sleep(2)

        # 3. Input email and submit
        email_inp = page.ele('tag:input@type=email', timeout=6) or page.ele('tag:input', timeout=6)
        if not email_inp:
            print("[!] Email input not found!", flush=True)
            return None

        email_inp.input(reg_email)
        time.sleep(1)

        page.run_js('''
            for (var b of document.querySelectorAll('button')) {
                if ((b.innerText || '').trim().toLowerCase() === 'continue' || b.type === 'submit') {
                    b.click(); break;
                }
            }
        ''')
        print("[3/5] Submitted email, waiting for OTP from Gmail...", flush=True)

        code = fetch_otp(reg_email, baseline_uids=baseline_uids, timeout=90)
        if not code:
            print("[!] OTP timed out!", flush=True)
            return None

        # 4. Input OTP code
        print("[4/5] Entering OTP code into form...", flush=True)
        otp_input = page.ele('css:input[data-input-otp="true"]', timeout=6) or page.ele('css:input[name="code"]', timeout=6)
        if otp_input:
            otp_input.click()
            time.sleep(0.5)
            otp_input.input(code)

        time.sleep(2)
        page.run_js('''
            for (var b of document.querySelectorAll('button')) {
                var t = (b.innerText || '').toLowerCase();
                if (t.includes('confirm') || t.includes('continue') || b.type === 'submit') {
                    b.click();
                    break;
                }
            }
        ''')
        time.sleep(4)

        # 5. Fill Profile Details (givenName, familyName, password)
        print("[5/5] Completing profile details...", flush=True)
        gn = page.ele('#givenName', timeout=6)
        fn = page.ele('#familyName', timeout=6)
        pw = page.ele('#password', timeout=6)

        if gn: gn.input(first_name)
        time.sleep(0.3)
        if fn: fn.input(last_name)
        time.sleep(0.3)
        if pw: pw.input(password)
        time.sleep(0.5)

        submit_btn = page.ele('css:button[type="submit"]')
        if submit_btn:
            submit_btn.click(by_js=True)
        else:
            page.run_js('''
                for (var b of document.querySelectorAll('button')) {
                    var t = (b.innerText || '').toLowerCase();
                    if (t.includes('complete') || t.includes('sign up') || b.type === 'submit') {
                        b.click();
                        break;
                    }
                }
            ''')

        # Wait for logged in state
        time.sleep(5)
        print("[+] Account registered successfully! Now generating 9Router tokens...", flush=True)

        # 6. Authorize Device Code & Extract Tokens
        tokens = authorize_device_code(page, reg_email)
        if tokens:
            # Append to grok_accounts.json
            existing_data = []
            if os.path.exists(ACCOUNTS_JSON):
                try:
                    with open(ACCOUNTS_JSON, "r", encoding="utf-8") as f:
                        loaded = json.load(f)
                        if isinstance(loaded, list):
                            existing_data = loaded
                except Exception:
                    pass

            existing_data.append(tokens)
            with open(ACCOUNTS_JSON, "w", encoding="utf-8") as f:
                json.dump(existing_data, f, indent=2)

            print(f"[🎉] Successfully added {reg_email} to {ACCOUNTS_JSON}")
            return tokens
        else:
            print("[!] Failed to obtain tokens for account.", flush=True)
            return None

    except Exception as e:
        print(f"[!] Exception during registration: {e}", flush=True)
        return None
    finally:
        if page:
            try:
                page.quit()
            except Exception:
                pass

def main():
    parser = argparse.ArgumentParser(description="Grok CLI / 9Router Automated Token Harvester")
    parser.add_argument("--count", type=int, default=1, help="Number of accounts to harvest (default: 1)")
    parser.add_argument("--headless", action="store_true", default=True, help="Run browser in background")
    args = parser.parse_args()

    if not GMAIL_USER or not GMAIL_PASS:
        print("[!] GMAIL_BASE_EMAIL and GMAIL_APP_PASSWORD must be configured in .env")
        sys.exit(1)

    print("=" * 65)
    print("   GROK CLI / 9ROUTER AUTOMATED TOKEN HARVESTER 🚀")
    print(f"   Target Domain  : {CUSTOM_DOMAIN}")
    print(f"   Target Count   : {args.count}")
    print(f"   Output JSON    : {ACCOUNTS_JSON}")
    print("=" * 65)

    harvested = []
    for i in range(1, args.count + 1):
        res = register_and_harvest(i, args.count, headless=args.headless)
        if res:
            harvested.append(res)
        if i < args.count:
            print("[*] Cooling down 4s before next account...", flush=True)
            time.sleep(4)

    print("\n" + "=" * 65)
    print(f"   HARVEST COMPLETED: {len(harvested)}/{args.count} Accounts Harvested!")
    print("=" * 65)
    for acc in harvested:
        print(f" - {acc['email']} | Access: {acc['access_token'][:15]}... | Refresh: {acc['refresh_token'][:15]}...")

    print(f"\n[+] File ready for 1-click import into 9Router:")
    print(f"    {ACCOUNTS_JSON}")

if __name__ == "__main__":
    main()
