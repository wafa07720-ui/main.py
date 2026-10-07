#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Braintree Debug via Telegram — Server Edition (v2)
Dev: Debug Tool
"""

import os
import time
import json
import asyncio
import requests
import traceback
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
BOT_TOKEN = "8647240736:AAEGXuwmtZkUvAfbURX2BcyyuoWD-TekP_0"
CHAT_ID = 6843321125

# BrightData
BD_HOST = "brd.superproxy.io"
BD_PORT = "9222"
BD_USER = "brd-customer-hl_24c8058e-zone-scraping_browser1"
BD_PASS = "eyr0v46j28pi"

# Target
BT_BASE_URL = "https://www.flue-warehouse.co.uk"
BT_PRODUCT_URL = f"{BT_BASE_URL}/twinwallflue/dinakdwtwinwallchimneysystems/125mm5inchdinakflue/chimneynoticeplate"
BT_CHECKOUT_URL = f"{BT_BASE_URL}/checkout"


# ═══════════════════════════════════════════════════
# Telegram Helper
# ═══════════════════════════════════════════════════
def tg_send(text, parse_mode="HTML"):
    """Send message to Telegram (auto-split if > 4000 chars)"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    chunks = []
    if len(text) <= 3500:
        chunks = [text]
    else:
        current = ""
        for line in text.split("\n"):
            if len(current) + len(line) + 1 > 3400:
                chunks.append(current)
                current = line
            else:
                current += "\n" + line if current else line
        if current:
            chunks.append(current)

    for chunk in chunks:
        try:
            requests.post(url, data={
                "chat_id": CHAT_ID,
                "text": f"<pre>{chunk}</pre>",
                "parse_mode": parse_mode
            }, timeout=30)
            time.sleep(0.4)
        except Exception as e:
            print(f"TG send error: {e}")


# ═══════════════════════════════════════════════════
# Main Debug Function
# ═══════════════════════════════════════════════════
def run_debug():
    output = []

    def log(msg):
        print(msg, flush=True)
        output.append(str(msg))

    def p(title):
        log("")
        log("=" * 60)
        log(f"  {title}")
        log("=" * 60)

    p(f"🔍 BRAINTREE DEBUG @ {datetime.now().strftime('%H:%M:%S')}")

    cdp_url = f"wss://{BD_USER}:{BD_PASS}@{BD_HOST}:{BD_PORT}"

    # ═══ STEP 1: BrightData connect ═══
    tg_send("🔄 [1/12] Connecting to BrightData...")
    try:
        pw = sync_playwright().start()
        log(f"🌐 Connecting to BrightData...")
        browser = pw.chromium.connect_over_cdp(cdp_url, timeout=120000)
        log(f"✅ Connected")
        tg_send("✅ [1/12] Connected to BrightData")
    except Exception as e:
        log(f"❌ Connection failed: {e}")
        tg_send(f"❌ [1/12] Connection failed:\n{str(e)[:200]}")
        tg_send("OUTPUT:\n" + "\n".join(output))
        return

    context = browser.new_context(
        viewport={"width": 1366, "height": 900},
        user_agent=("Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36"),
        locale="en-GB",
    )
    page = context.new_page()
    page.set_default_timeout(60000)

    # ═══ STEP 2: Product Page ═══
    tg_send("🔄 [2/12] Opening product page...")
    p("1️⃣ PRODUCT PAGE")
    try:
        page.goto(BT_PRODUCT_URL, wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)
        log(f"✅ URL: {page.url}")
        log(f"✅ Title: {page.title()}")
        tg_send(f"✅ [2/12] Product loaded: {page.title()[:60]}")
    except Exception as e:
        log(f"❌ Failed: {e}")
        tg_send(f"❌ [2/12] Product failed:\n{str(e)[:200]}")
        tg_send("OUTPUT:\n" + "\n".join(output))
        return

    # ═══ STEP 3: Add to Cart ═══
    tg_send("🔄 [3/12] Finding add-to-cart button...")
    p("2️⃣ ADD TO CART SELECTORS")
    add_sel = None
    for sel in [
        "button.single_add_to_cart_button",
        "button[name='add-to-cart']",
        "button[type='submit'].single_add_to_cart_button",
        ".single_add_to_cart_button",
    ]:
        try:
            el = page.locator(sel).first
            if el.count() > 0:
                log(f"✅ FOUND: {sel}")
                try:
                    log(f"   HTML: {el.evaluate('e=>e.outerHTML')[:250]}")
                except:
                    pass
                if not add_sel:
                    add_sel = sel
        except:
            continue

    if not add_sel:
        log("❌ No add to cart button found")
        tg_send("❌ [3/12] No add-to-cart button found")
    else:
        tg_send(f"✅ [3/12] Found: {add_sel}")

    # ═══ STEP 4: Click Add to Cart ═══
    tg_send("🔄 [4/12] Clicking add to cart...")
    p("3️⃣ CLICK ADD TO CART")
    if add_sel:
        try:
            page.click(add_sel, timeout=10000)
            time.sleep(4)
            log(f"✅ Clicked. URL: {page.url}")
            tg_send(f"✅ [4/12] Clicked. URL: {page.url[:60]}")
        except Exception as e:
            log(f"⚠️ Click failed: {e}")
            tg_send(f"⚠️ [4/12] Click failed:\n{str(e)[:200]}")

    # ═══ STEP 5: Checkout ═══
    tg_send("🔄 [5/12] Opening checkout page...")
    p("4️⃣ CHECKOUT PAGE")
    try:
        page.goto(BT_CHECKOUT_URL, wait_until="domcontentloaded", timeout=60000)
        time.sleep(5)
        log(f"✅ URL: {page.url}")
        log(f"✅ Title: {page.title()}")
        tg_send(f"✅ [5/12] Checkout loaded: {page.title()[:60]}")
    except Exception as e:
        log(f"❌ Failed: {e}")
        tg_send(f"❌ [5/12] Checkout failed:\n{str(e)[:200]}")
        tg_send("OUTPUT:\n" + "\n".join(output))
        return

    # ═══ STEP 6: Billing Fields ═══
    tg_send("🔄 [6/12] Scanning billing fields...")
    p("5️⃣ BILLING FIELDS")
    billing_found = []
    for bid in ["#billing_first_name", "#billing_last_name", "#billing_email",
                "#billing_phone", "#billing_address_1", "#billing_city",
                "#billing_state", "#billing_postcode", "#billing_country"]:
        try:
            if page.locator(bid).first.count() > 0:
                log(f"✅ {bid}")
                billing_found.append(bid)
        except:
            pass
    tg_send(f"✅ [6/12] Found {len(billing_found)} billing fields")

    # ═══ STEP 7: All Frames ═══
    tg_send("🔄 [7/12] Scanning iframes...")
    p("6️⃣ ALL IFRAMES")
    frame_count = 0
    for i, frame in enumerate(page.frames):
        try:
            furl = (frame.url or "")[:130]
            fname = frame.name or ""
            log(f"[{i}] name='{fname}'")
            if furl:
                log(f"    url='{furl}'")
            frame_count += 1
            try:
                inputs = frame.locator("input").all()
                for inp in inputs[:15]:
                    try:
                        iid = inp.get_attribute("id") or ""
                        iname = inp.get_attribute("name") or ""
                        if iid or iname:
                            log(f"    → input: id='{iid}' name='{iname}'")
                    except:
                        continue
            except:
                pass
        except:
            continue
    tg_send(f"✅ [7/12] Found {frame_count} frames")

    # ═══ STEP 8: Turnstile ═══
    tg_send("🔄 [8/12] Checking Cloudflare Turnstile...")
    p("7️⃣ CLOUDFLARE TURNSTILE")
    try:
        info = page.evaluate("""() => {
            const out = {};
            const ts = document.querySelector('[name=cf-turnstile-response]');
            out.cf_turnstile_exists = !!ts;
            out.cf_turnstile_len = ts ? (ts.value||'').length : 0;
            const tsDiv = document.querySelector('.cf-turnstile, [data-sitekey]');
            out.turnstile_div = !!tsDiv;
            if (tsDiv) {
                out.sitekey = (tsDiv.getAttribute('data-sitekey') || '').slice(0, 60);
            }
            return out;
        }""")
        log(json.dumps(info, indent=2))
        tg_send(f"✅ [8/12] Turnstile info:\n<code>{json.dumps(info, indent=2)}</code>")
    except Exception as e:
        log(f"⚠️ {e}")
        tg_send(f"⚠️ [8/12] Turnstile error:\n{str(e)[:200]}")

    # ═══ STEP 9: Place Order ═══
    tg_send("🔄 [9/12] Finding place order button...")
    p("8️⃣ PLACE ORDER BUTTON")
    po_found = False
    for sel in ["#place_order",
                "button[name='woocommerce_checkout_place_order']",
                "input[name='woocommerce_checkout_place_order']"]:
        try:
            el = page.locator(sel).first
            if el.count() > 0:
                log(f"✅ FOUND: {sel}")
                try:
                    log(f"   HTML: {el.evaluate('e=>e.outerHTML')[:250]}")
                except:
                    pass
                po_found = True
        except:
            continue
    tg_send(f"✅ [9/12] Place order button: {'Found' if po_found else 'Not found'}")

    # ═══ STEP 10: Payment Methods ═══
    tg_send("🔄 [10/12] Scanning payment methods...")
    p("9️⃣ PAYMENT METHODS")
    try:
        pm = page.evaluate("""() => {
            const items = document.querySelectorAll('.wc_payment_method, li[class*="payment_method"]');
            return Array.from(items).map(el => ({
                cls: el.className,
                txt: el.innerText.slice(0, 60),
                radio: el.querySelector('input[type=radio]')?.id || null
            }));
        }""")
        for item in pm:
            log(f"  • {item['cls']}")
            log(f"    txt: {item['txt']}")
            log(f"    radio: {item['radio']}")
        tg_send(f"✅ [10/12] Found {len(pm)} payment methods")
    except Exception as e:
        log(f"⚠️ {e}")
        tg_send(f"⚠️ [10/12] Payment methods error:\n{str(e)[:200]}")

    # ═══ STEP 11: Braintree Scripts ═══
    tg_send("🔄 [11/12] Scanning Braintree scripts...")
    p("🔟 BRAINTREE SCRIPTS")
    try:
        scripts = page.evaluate("""() => {
            const out = [];
            document.querySelectorAll('script').forEach(s => {
                const txt = s.textContent || '';
                const src = s.src || '';
                if (txt.toLowerCase().includes('braintree') ||
                    src.toLowerCase().includes('braintree') ||
                    txt.toLowerCase().includes('wc_braintree')) {
                    out.push({
                        src: src.slice(0, 120),
                        text: txt.slice(0, 250)
                    });
                }
            });
            return out;
        }""")
        for s in scripts[:5]:
            if s['src']:
                log(f"SRC: {s['src']}")
            if s['text']:
                log(f"TXT: {s['text']}")
            log("")
        tg_send(f"✅ [11/12] Found {len(scripts)} braintree scripts")
    except Exception as e:
        log(f"⚠️ {e}")
        tg_send(f"⚠️ [11/12] Scripts error:\n{str(e)[:200]}")

    # ═══ STEP 12: Braintree Token ═══
    tg_send("🔄 [12/12] Extracting Braintree token...")
    p("1️⃣1️⃣ BRAINTREE TOKEN")
    try:
        tok = page.evaluate("""() => {
            if (window.wc_braintree_client_token) {
                const t = window.wc_braintree_client_token;
                return Array.isArray(t) ? t[0] : t;
            }
            return null;
        }""")
        if tok:
            log(f"✅ Token length: {len(tok)}")
            log(f"   First 100: {tok[:100]}")
            tg_send(f"✅ [12/12] Token length: {len(tok)}")
        else:
            log("❌ No token")
            tg_send("❌ [12/12] No token found")
    except Exception as e:
        log(f"⚠️ {e}")
        tg_send(f"⚠️ [12/12] Token error:\n{str(e)[:200]}")

    # ═══ BONUS: HTML Snippets ═══
    p("1️⃣2️⃣ BRAINTREE HTML SNIPPETS")
    try:
        html = page.content()
        for kw in ["braintree-hosted-field", "credit-card-number", "wc-braintree"]:
            idx = html.lower().find(kw)
            if idx > 0:
                log(f"--- {kw} ---")
                log(html[max(0, idx - 80):idx + 300])
                log("")
    except Exception as e:
        log(f"⚠️ {e}")

    # ═══ DONE ═══
    p("✅ DEBUG DONE")

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

    # ─── Send final output ───
    tg_send("🎯 FINAL OUTPUT:\n\n" + "\n".join(output))
    print("✅ Output sent to Telegram")


# ═══════════════════════════════════════════════════
# ENTRY
# ═══════════════════════════════════════════════════
if __name__ == "__main__":
    try:
        tg_send("⏳ Starting Braintree debug v2... Please wait")
        run_debug()
    except Exception as e:
        err = f"❌ FATAL Error: {e}\n\n{traceback.format_exc()}"
        print(err, flush=True)
        tg_send(err[:3500])
