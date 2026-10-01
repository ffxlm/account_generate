import sys, os, time, imaplib, email, re, random, string, argparse
from DrissionPage import ChromiumPage, ChromiumOptions
from dotenv import load_dotenv

# Ensure UTF-8 output on Windows
sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

# Base directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KEYS_FILE = os.path.join(BASE_DIR, "keys", "groq_keys.txt")

# Load environment configuration
load_dotenv(os.path.join(BASE_DIR, ".env"))

gmail_user = os.getenv("GMAIL_BASE_EMAIL")
gmail_pass = os.getenv("GMAIL_APP_PASSWORD")
domain = os.getenv("CUSTOM_DOMAIN", "thirx.com")

if not gmail_user or not gmail_pass:
    print("[!] Error: GMAIL_BASE_EMAIL or GMAIL_APP_PASSWORD missing in .env")
    sys.exit(1)

def get_random_email():
    rnd = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"groq_{rnd}@{domain}"

def create_groq_account(index=1, total=1):
    target_email = get_random_email()
    print(f"\n{'='*55}", flush=True)
    print(f"[{index}/{total}] Starting Groq Account Registration: {target_email}", flush=True)
    print(f"{'='*55}", flush=True)

    port = random.randint(9300, 9600)
    udata = os.path.join(os.environ.get("TEMP", r"C:\Users\film\AppData\Local\Temp"), f"groq_reg_{port}")
    
    co = ChromiumOptions()
    co.set_local_port(port)
    co.set_user_data_path(udata)
    co.set_argument('--window-position=-2400,-2400')
    co.set_argument('--window-size=1280,900')
    page = ChromiumPage(co)

    try:
        # 1. Login page
        print("[1] Opening Groq login page...", flush=True)
        page.get("https://console.groq.com/login")
        time.sleep(3)

        email_input = page.ele('#email-input')
        if not email_input:
            print("[!] Email input not found on login page!", flush=True)
            return None

        email_input.input(target_email)
        time.sleep(0.5)
        submit_btn = page.ele('css:button[type="submit"]') or page.ele('text:Continue with email')
        submit_btn.click()
        print(f"[2] Submitted {target_email}, waiting for magic link via IMAP...", flush=True)

        # 2. Wait for email in IMAP
        magic_link = None
        start_wait = time.time()
        for attempt in range(16):
            time.sleep(3)
            try:
                mail = imaplib.IMAP4_SSL("imap.gmail.com")
                mail.login(gmail_user, gmail_pass)
                mail.select("inbox")
                status, msgs = mail.search(None, 'ALL')
                for mid in reversed(msgs[0].split()[-6:]):
                    s, data = mail.fetch(mid, '(RFC822)')
                    msg = email.message_from_bytes(data[0][1])
                    if target_email in msg.get("To", ""):
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() in ["text/plain", "text/html"]:
                                    body += part.get_payload(decode=True).decode('utf-8', errors='replace')
                        else:
                            body = msg.get_payload(decode=True).decode('utf-8', errors='replace')
                        links = re.findall(r'https://stytch\.com/v1/magic_links/redirect[^\s<>"\'\)]+', body)
                        if links:
                            magic_link = links[0]
                            print(f"[3] Found Magic Link in {time.time() - start_wait:.1f}s!", flush=True)
                            break
                mail.logout()
                if magic_link:
                    break
            except Exception as e:
                print(f"  [IMAP Attempt {attempt+1}]: {e}", flush=True)

        if not magic_link:
            print("[!] Timed out waiting for magic link email!", flush=True)
            return None

        # 3. Open magic link and wait for authentication redirect
        print("[4] Opening Magic Link in browser...", flush=True)
        page.get(magic_link)

        authenticated = False
        print("Waiting for authentication redirect...", flush=True)
        for s in range(35):
            time.sleep(1)
            cur_url = page.url
            if "console.groq.com" in cur_url and "/authenticate" not in cur_url and "/login" not in cur_url:
                authenticated = True
                print(f"[5] Successfully authenticated! URL: {cur_url}", flush=True)
                break

        time.sleep(2)

        # 4. Navigate to API Keys page
        print("[6] Navigating to https://console.groq.com/keys ...", flush=True)
        page.get("https://console.groq.com/keys")
        time.sleep(4)

        # 5. Open Create API Key modal
        create_btn = page.ele('text:Create API Key') or page.ele('css:button[aria-label*="Create" i]') or page.ele('css:button[aria-label*="Key" i]')
        if not create_btn:
            print("[!] 'Create API Key' button not found!", flush=True)
            return None

        create_btn.click()
        time.sleep(1.5)

        # 6. Fill Key Name
        page.run_js('''
            var modal = document.querySelector('[role="dialog"]') || document.body;
            var inp = modal.querySelector('input');
            if (inp) {
                inp.focus();
                var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                setter.call(inp, "GroqBot");
                inp.dispatchEvent(new Event('input', { bubbles: true }));
                inp.dispatchEvent(new Event('change', { bubbles: true }));
            }
        ''')
        print("[7] Filled key display name: GroqBot", flush=True)

        # 7. Wait for Turnstile verification and Submit button
        print("[8] Waiting for Turnstile verification & Submit button...", flush=True)
        submit_btn = None
        for w in range(25):
            time.sleep(1)
            btn = page.run_js('''
                var modal = document.querySelector('[role="dialog"]') || document.body;
                for (var b of modal.querySelectorAll('button')) {
                    if ((b.innerText || '').trim().toLowerCase() === 'submit') {
                        b.click();
                        return true;
                    }
                }
                return false;
            ''')
            if btn:
                print(f"[{w+1}s] Found and clicked Submit button via JS!", flush=True)
                submit_btn = True
                break

        if not submit_btn:
            print("[!] Timed out waiting for Submit button!", flush=True)
            return None

        # 8. Extract generated key
        print("[9] Extracting generated API key...", flush=True)
        api_key = None
        for k in range(12):
            time.sleep(1)
            api_key = page.run_js('''
                for (var el of document.querySelectorAll('input, code, span, div, p')) {
                    var txt = (el.value || el.innerText || '').trim();
                    var m = txt.match(/gsk_[a-zA-Z0-9_]{30,}/);
                    if (m) return m[0];
                }
                var bodyMatch = document.body.innerText.match(/gsk_[a-zA-Z0-9_]{30,}/);
                return bodyMatch ? bodyMatch[0] : null;
            ''')
            if api_key:
                break

        if api_key:
            print(f"\n🎉 SUCCESS! Generated API Key for {target_email}:", flush=True)
            print(f"    Key: {api_key}", flush=True)
            os.makedirs(os.path.dirname(KEYS_FILE), exist_ok=True)
            with open(KEYS_FILE, "a", encoding="utf-8") as f:
                f.write(f"{target_email}|{api_key}\n")
            print(f"[+] Saved to {KEYS_FILE}!\n", flush=True)
            return api_key
        else:
            print("[!] Could not find gsk_ key in modal!", flush=True)
            return None

    except Exception as e:
        print(f"[!] Error during registration: {e}", flush=True)
        return None
    finally:
        try:
            page.quit()
        except Exception:
            pass

def main():
    parser = argparse.ArgumentParser(description="Automated Groq Cloud Account & API Key Harvester")
    parser.add_argument("--count", type=int, default=1, help="Number of accounts/keys to generate (default: 1)")
    parser.add_argument("--delay", type=int, default=5, help="Delay in seconds between registrations (default: 5)")
    args = parser.parse_args()

    print(f"[*] Starting Groq Key Harvester. Target: {args.count} account(s)")
    success_count = 0
    for i in range(1, args.count + 1):
        key = create_groq_account(index=i, total=args.count)
        if key:
            success_count += 1
        if i < args.count:
            print(f"Waiting {args.delay}s before next account...", flush=True)
            time.sleep(args.delay)

    print(f"\n{'='*55}")
    print(f"[*] Batch Complete! Successfully harvested {success_count}/{args.count} keys.")
    print(f"[*] Keys file: {KEYS_FILE}")
    print(f"{'='*55}\n")

if __name__ == "__main__":
    main()
