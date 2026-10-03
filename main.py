#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WeGive Recon Tool - يستخرج كل حاجة من الموقع
- Form fields
- API endpoints
- Hidden tokens
- iframe URLs
- JS variables
- Network requests
"""

import os
os.environ['DISPLAY'] = ':99'

import re
import json
import time
from playwright.sync_api import sync_playwright

# ═══════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════

BD_USER = "brd-customer-hl_24c8058e-zone-scraping_browser1"
BD_PASS = "eyr0v46j28pi"
BD_HOST = "brd.superproxy.io"
BD_PORT = "9222"

TARGET_URL = "https://donate.timtebowfoundation.org/tim-tebow-foundation-inc/"

# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

def connect_browser(p):
    cdp_url = f"wss://{BD_USER}:{BD_PASS}@{BD_HOST}:{BD_PORT}"
    print("🌐 Connecting to BrightData...", flush=True)
    browser = p.chromium.connect_over_cdp(cdp_url, timeout=120000)
    print("✅ Connected", flush=True)
    return browser


def extract_forms(page):
    """استخراج كل الفورم من الصفحة"""
    forms_data = page.evaluate("""() => {
        const forms = [];
        document.querySelectorAll('form').forEach((form, idx) => {
            const inputs = [];
            form.querySelectorAll('input, select, textarea, button').forEach(el => {
                inputs.push({
                    tag: el.tagName.toLowerCase(),
                    type: el.type || '',
                    name: el.name || '',
                    id: el.id || '',
                    placeholder: el.placeholder || '',
                    value: el.value || '',
                    required: el.required || false,
                    disabled: el.disabled || false,
                    className: el.className || ''
                });
            });
            forms.push({
                index: idx,
                id: form.id || '',
                className: form.className || '',
                action: form.action || '',
                method: form.method || '',
                inputs: inputs
            });
        });
        return forms;
    }""")
    return forms_data


def extract_iframes(page):
    """استخراج كل iframes"""
    iframes = page.evaluate("""() => {
        const result = [];
        document.querySelectorAll('iframe').forEach((iframe, idx) => {
            result.push({
                index: idx,
                id: iframe.id || '',
                name: iframe.name || '',
                src: iframe.src || '',
                className: iframe.className || '',
                title: iframe.title || ''
            });
        });
        return result;
    }""")
    return iframes


def extract_scripts(page):
    """استخراج معلومات السكريبتات المهمة"""
    scripts_data = page.evaluate("""() => {
        const scripts = [];
        document.querySelectorAll('script').forEach((script, idx) => {
            scripts.push({
                index: idx,
                src: script.src || '',
                type: script.type || '',
                inline: script.src ? false : true,
                content_length: script.textContent ? script.textContent.length : 0
            });
        });
        return scripts;
    }""")
    return scripts_data


def extract_js_variables(page):
    """استخراج متغيرات JS المهمة من window"""
    js_vars = page.evaluate("""() => {
        const important = {};
        const keywords = [
            'stripe', 'stripeKey', 'publishableKey', 'pk_live', 'pk_test',
            'organization', 'org_id', 'form_id', 'formId', 'csrf', 'nonce',
            'recaptcha', 'siteKey', 'publicKey', 'clientKey',
            'api', 'baseUrl', 'endpoint', 'token', 'session',
            'wegive', 'config', 'settings', 'give', 'donate'
        ];
        
        for (const key in window) {
            try {
                const lowerKey = key.toLowerCase();
                for (const kw of keywords) {
                    if (lowerKey.includes(kw.toLowerCase())) {
                        const val = window[key];
                        if (typeof val === 'string' || typeof val === 'number') {
                            important[key] = val;
                        } else if (typeof val === 'object' && val !== null) {
                            try {
                                important[key] = JSON.stringify(val).substring(0, 500);
                            } catch(e) {
                                important[key] = '[object]';
                            }
                        }
                        break;
                    }
                }
            } catch(e) {}
        }
        return important;
    }""")
    return js_vars


def extract_meta_and_links(page):
    """استخراج meta tags و links"""
    data = page.evaluate("""() => {
        const meta = [];
        document.querySelectorAll('meta').forEach(m => {
            meta.push({
                name: m.name || '',
                property: m.property || '',
                content: m.content || ''
            });
        });
        
        const links = [];
        document.querySelectorAll('link[rel="stylesheet"], link[rel="preload"], link[rel="preconnect"], link[rel="dns-prefetch"]').forEach(l => {
            links.push({
                rel: l.rel || '',
                href: l.href || '',
                as: l.as || ''
            });
        });
        
        return { meta: meta, links: links };
    }""")
    return data


def extract_global_config(page):
    """استخراج إعدادات التطبيق من window أو __INITIAL_STATE__"""
    config = page.evaluate("""() => {
        const results = {};
        
        // Vue apps
        if (window.__INITIAL_STATE__) results.__INITIAL_STATE__ = window.__INITIAL_STATE__;
        if (window.__VUE__) results.__VUE__ = 'exists';
        if (window.__NUXT__) results.__NUXT__ = window.__NUXT__;
        if (window.__NEXT_DATA__) results.__NEXT_DATA__ = window.__NEXT_DATA__;
        
        // App config
        if (window.APP_CONFIG) results.APP_CONFIG = window.APP_CONFIG;
        if (window.__APP__) results.__APP__ = 'exists';
        if (window.__ENV__) results.__ENV__ = window.__ENV__;
        
        // Stripe
        if (window.Stripe) results.Stripe = 'exists';
        if (window.stripe) results.stripe = 'exists';
        
        // reCAPTCHA
        if (window.grecaptcha) results.grecaptcha = 'exists';
        if (window.grecaptchaEnterprise) results.grecaptchaEnterprise = 'exists';
        
        // متغيرات مشتركة
        const commonKeys = ['config', 'settings', 'wegive', 'wegiveConfig', 'giveConfig'];
        for (const k of commonKeys) {
            if (window[k]) {
                try {
                    results[k] = JSON.stringify(window[k]).substring(0, 2000);
                } catch(e) {
                    results[k] = '[object]';
                }
            }
        }
        
        return results;
    }""")
    return config


def main():
    print("=" * 70, flush=True)
    print("  WeGive Recon Tool - Extracting Everything", flush=True)
    print("=" * 70, flush=True)
    print(f"🎯 Target: {TARGET_URL}", flush=True)
    print("=" * 70, flush=True)
    
    # تخزين كل الـ network requests
    all_requests = []
    all_responses = []
    
    try:
        with sync_playwright() as p:
            browser = connect_browser(p)
            
            context = browser.new_context(
                viewport={"width": 1366, "height": 900},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            )
            
            page = context.new_page()
            
            # تسجيل كل الـ requests
            def on_request(req):
                try:
                    all_requests.append({
                        'url': req.url,
                        'method': req.method,
                        'headers': dict(req.headers),
                        'post_data': req.post_data if req.post_data else None,
                        'resource_type': req.resource_type
                    })
                except:
                    pass
            
            def on_response(resp):
                try:
                    # حفظ الردود المهمة بس
                    url = resp.url
                    if any(x in url for x in ['api.wegive.com', 'api.stripe.com', 'stripe.com/v1', 'donate.timtebow']):
                        body = None
                        try:
                            body = resp.text()[:5000]
                        except:
                            pass
                        
                        all_responses.append({
                            'url': url,
                            'status': resp.status,
                            'method': resp.request.method,
                            'body': body
                        })
                except:
                    pass
            
            page.on('request', on_request)
            page.on('response', on_response)
            
            print("\n📄 Loading page...", flush=True)
            try:
                page.goto(TARGET_URL, timeout=90000, wait_until="networkidle")
            except Exception as e:
                print(f"⚠️ Nav warning: {str(e)[:100]}", flush=True)
            
            print("⏳ Waiting for page to load completely...", flush=True)
            time.sleep(5)
            
            # 1. Forms
            print("\n" + "=" * 70, flush=True)
            print("📋 FORMS", flush=True)
            print("=" * 70, flush=True)
            forms = extract_forms(page)
            print(json.dumps(forms, indent=2, ensure_ascii=False), flush=True)
            
            # 2. iframes
            print("\n" + "=" * 70, flush=True)
            print("🖼️ IFRAMES", flush=True)
            print("=" * 70, flush=True)
            iframes = extract_iframes(page)
            print(json.dumps(iframes, indent=2, ensure_ascii=False), flush=True)
            
            # 3. Scripts
            print("\n" + "=" * 70, flush=True)
            print("📜 SCRIPTS", flush=True)
            print("=" * 70, flush=True)
            scripts = extract_scripts(page)
            # فلترة: عرض السكريبتات اللي فيها كلمات مهمة فقط
            important_scripts = [
                s for s in scripts
                if s['src'] and any(x in s['src'].lower() for x in ['stripe', 'wegive', 'give', 'payment', 'recaptcha'])
            ]
            print(json.dumps(important_scripts, indent=2, ensure_ascii=False), flush=True)
            
            # 4. JS Variables
            print("\n" + "=" * 70, flush=True)
            print("🔧 JS VARIABLES", flush=True)
            print("=" * 70, flush=True)
            js_vars = extract_js_variables(page)
            print(json.dumps(js_vars, indent=2, ensure_ascii=False), flush=True)
            
            # 5. Global Config
            print("\n" + "=" * 70, flush=True)
            print("⚙️ GLOBAL CONFIG", flush=True)
            print("=" * 70, flush=True)
            config = extract_global_config(page)
            print(json.dumps(config, indent=2, ensure_ascii=False)[:5000], flush=True)
            
            # 6. Meta & Links
            print("\n" + "=" * 70, flush=True)
            print("🔗 META & LINKS", flush=True)
            print("=" * 70, flush=True)
            meta_links = extract_meta_and_links(page)
            print(json.dumps(meta_links, indent=2, ensure_ascii=False)[:3000], flush=True)
            
            # 7. محاولة التفاعل - اضغط على Next لو موجود
            print("\n" + "=" * 70, flush=True)
            print("🖱️ INTERACTING WITH PAGE", flush=True)
            print("=" * 70, flush=True)
            
            # جرب تحدد الفورم
            selectors_to_try = [
                '#amount',
                'input[type="number"]',
                'input[name*="amount"]',
                'input[placeholder*="0"]',
                'input[placeholder*="Amount"]',
            ]
            
            for sel in selectors_to_try:
                try:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        print(f"✅ Found amount field: {sel}", flush=True)
                        el.fill("5")
                        time.sleep(1)
                        break
                except:
                    pass
            
            # جرب تضغط Next
            next_buttons = [
                'button:has-text("Next")',
                'button:has-text("Continue")',
                'button:has-text("التالي")',
                '.wg-btn',
                'button[type="submit"]'
            ]
            
            clicked = False
            for sel in next_buttons:
                try:
                    btns = page.query_selector_all(sel)
                    for btn in btns:
                        if btn.is_visible():
                            text = btn.inner_text()
                            if 'next' in text.lower() or 'continue' in text.lower() or 'التالي' in text:
                                print(f"✅ Clicking: {text}", flush=True)
                                btn.click()
                                clicked = True
                                time.sleep(3)
                                break
                    if clicked:
                        break
                except:
                    pass
            
            if clicked:
                print("⏳ After clicking Next, waiting 3s...", flush=True)
                time.sleep(3)
                
                # استخراج الفورم الجديد
                print("\n" + "=" * 70, flush=True)
                print("📋 NEW FORMS AFTER NEXT", flush=True)
                print("=" * 70, flush=True)
                forms2 = extract_forms(page)
                print(json.dumps(forms2, indent=2, ensure_ascii=False), flush=True)
                
                # iframes جديدة
                print("\n" + "=" * 70, flush=True)
                print("🖼️ NEW IFRAMES AFTER NEXT", flush=True)
                print("=" * 70, flush=True)
                iframes2 = extract_iframes(page)
                print(json.dumps(iframes2, indent=2, ensure_ascii=False), flush=True)
            
            # 8. عرض كل الـ API calls المهمة
            print("\n" + "=" * 70, flush=True)
            print("🌐 API REQUESTS (filtered)", flush=True)
            print("=" * 70, flush=True)
            
            filtered_reqs = [
                r for r in all_requests
                if any(x in r['url'] for x in ['api.wegive.com', 'api.stripe.com', 'stripe.com/v1', 'donate.timtebow'])
                and 'analytics' not in r['url']
                and 'hubspot' not in r['url']
                and 'facebook' not in r['url']
                and 'tiktok' not in r['url']
                and 'doubleclick' not in r['url']
                and 'google' not in r['url'].lower()
            ]
            
            for req in filtered_reqs:
                print(f"\n→ {req['method']} {req['url']}", flush=True)
                if req['post_data']:
                    print(f"  POST DATA: {req['post_data'][:500]}", flush=True)
            
            # 9. حفظ كل حاجة في ملفات
            print("\n" + "=" * 70, flush=True)
            print("💾 SAVING TO FILES", flush=True)
            print("=" * 70, flush=True)
            
            with open('recon_forms.json', 'w', encoding='utf-8') as f:
                json.dump(forms, f, indent=2, ensure_ascii=False)
            
            with open('recon_iframes.json', 'w', encoding='utf-8') as f:
                json.dump(iframes, f, indent=2, ensure_ascii=False)
            
            with open('recon_scripts.json', 'w', encoding='utf-8') as f:
                json.dump(scripts, f, indent=2, ensure_ascii=False)
            
            with open('recon_js_vars.json', 'w', encoding='utf-8') as f:
                json.dump(js_vars, f, indent=2, ensure_ascii=False)
            
            with open('recon_config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            with open('recon_requests.json', 'w', encoding='utf-8') as f:
                json.dump(filtered_reqs, f, indent=2, ensure_ascii=False)
            
            with open('recon_responses.json', 'w', encoding='utf-8') as f:
                json.dump(all_responses, f, indent=2, ensure_ascii=False)
            
            print("✅ Saved files:", flush=True)
            print("   - recon_forms.json", flush=True)
            print("   - recon_iframes.json", flush=True)
            print("   - recon_scripts.json", flush=True)
            print("   - recon_js_vars.json", flush=True)
            print("   - recon_config.json", flush=True)
            print("   - recon_requests.json", flush=True)
            print("   - recon_responses.json", flush=True)
            
            # 10. حفظ HTML كامل
            html = page.content()
            with open('recon_page.html', 'w', encoding='utf-8') as f:
                f.write(html)
            print("   - recon_page.html", flush=True)
            
            # 11. screenshot
            try:
                page.screenshot(path='recon_page.png', full_page=True)
                print("   - recon_page.png", flush=True)
            except:
                pass
            
            print("\n" + "=" * 70, flush=True)
            print("✅ RECON COMPLETE!", flush=True)
            print("=" * 70, flush=True)
            
            input("\n[Press Enter to close browser...]", flush=True)
            
            try:
                context.close()
                browser.close()
            except:
                pass
    
    except Exception as e:
        print(f"\n❌ Error: {str(e)[:200]}", flush=True)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Stopped", flush=True)
    except Exception as e:
        print(f"\n❌ Fatal: {str(e)[:200]}", flush=True)
