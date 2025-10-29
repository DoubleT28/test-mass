import json
import os
import random
import string
import requests
from datetime import datetime
from config import *

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {"proxy_host": "", "proxy_port": "", "proxy_username": "", "proxy_password": ""}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

def load_session():
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, 'r') as f:
            return json.load(f)
    return {"total": 0, "processed": 0, "live": 0, "insufficient": 0, "hit": 0, "ccn": 0, "current_file": ""}

def save_session(session):
    with open(SESSION_FILE, 'w') as f:
        json.dump(session, f)

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)

def load_banned():
    if os.path.exists(BANNED_FILE):
        with open(BANNED_FILE, 'r') as f:
            return json.load(f)
    return []

def save_banned(banned):
    with open(BANNED_FILE, 'w') as f:
        json.dump(banned, f)

def is_admin(user_id):
    return str(user_id) == ADMIN_ID

def is_banned(user_id):
    banned = load_banned()
    return str(user_id) in banned

def can_use_bot(user_id):
    """Check if user can use the bot (admin, premium, or in users list)"""
    if is_admin(user_id):
        return True
    
    if is_banned(user_id):
        return False
    
    users = load_users()
    user_id_str = str(user_id)
    
    # Check if user exists and is premium or active
    if user_id_str in users:
        user_data = users[user_id_str]
        return user_data.get('is_premium', False) or user_data.get('is_active', True)
    
    return False  # User not in database, cannot use bot

def add_user(user_id, username="", is_premium=False):
    if is_banned(user_id):
        return False
    
    users = load_users()
    user_id_str = str(user_id)
    
    users[user_id_str] = {
        'id': user_id_str,
        'username': username,
        'joined': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'access_count': 0,
        'hits_found': 0,
        'is_premium': is_premium,
        'is_active': True
    }
    save_users(users)
    return True

def remove_user(user_id):
    users = load_users()
    user_id_str = str(user_id)
    
    if user_id_str in users:
        del users[user_id_str]
        save_users(users)
        return True
    return False

def set_premium(user_id, premium_status=True):
    users = load_users()
    user_id_str = str(user_id)
    
    if user_id_str in users:
        users[user_id_str]['is_premium'] = premium_status
        save_users(users)
        return True
    return False

def ban_user(user_id):
    banned = load_banned()
    user_id_str = str(user_id)
    
    if user_id_str not in banned:
        banned.append(user_id_str)
        save_banned(banned)
        remove_user(user_id)
        return True
    return False

def unban_user(user_id):
    banned = load_banned()
    user_id_str = str(user_id)
    
    if user_id_str in banned:
        banned.remove(user_id_str)
        save_banned(banned)
        return True
    return False

def generate_identifier(identifier_type):
    hex_chars = string.hexdigits.lower()[:16]
    
    if identifier_type == 'guid':
        return ''.join(random.choice(hex_chars) for _ in range(8)) + '-' + \
               ''.join(random.choice(hex_chars) for _ in range(4)) + '-' + \
               ''.join(random.choice(hex_chars) for _ in range(4)) + '-' + \
               ''.join(random.choice(hex_chars) for _ in range(4)) + '-' + \
               ''.join(random.choice(hex_chars) for _ in range(12))
    else:  # muid or sid
        return ''.join(random.choice(hex_chars) for _ in range(8)) + '-' + \
               ''.join(random.choice(hex_chars) for _ in range(4)) + '-' + \
               ''.join(random.choice(hex_chars) for _ in range(4)) + '-' + \
               ''.join(random.choice(hex_chars) for _ in range(12))

def get_user_role(user_id):
    if is_admin(user_id):
        return "👑 Owner"
    
    users = load_users()
    user_data = users.get(str(user_id), {})
    
    if user_data.get('is_premium', False):
        return "⭐ Premium"
    
    if user_data.get('is_active', False):
        return "👤 User"
    
    return "❌ No Access"

def get_bin_info_from_api(card_number):
    """Get BIN information from online APIs"""
    bin_code = card_number[:6]
    
    # Multiple BIN lookup APIs
    bin_apis = [
        f"https://lookup.binlist.net/{bin_code}",
        f"https://bin-ip-checker.p.rapidapi.com/?bin={bin_code}",
        f"https://api.bincodes.com/bin/?format=json&api_key=free&bin={bin_code}",
        f"https://binlist.io/lookup/{bin_code}/",
    ]
    
    for api_url in bin_apis:
        try:
            response = requests.get(api_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                # Parse different API response formats
                if 'bank' in data:
                    # binlist.net format
                    return {
                        'type': data.get('type', 'Unknown'),
                        'brand': data.get('brand', 'Unknown'),
                        'bank': data.get('bank', {}).get('name', 'UNKNOWN BANK'),
                        'country': data.get('country', {}).get('name', 'UNKNOWN'),
                        'currency': data.get('country', {}).get('currency', 'USD')
                    }
                elif 'data' in data:
                    # Some APIs wrap in data object
                    bank_data = data['data']
                    return {
                        'type': bank_data.get('type', 'Unknown'),
                        'brand': bank_data.get('brand', 'Unknown'),
                        'bank': bank_data.get('bank', 'UNKNOWN BANK'),
                        'country': bank_data.get('country', 'UNKNOWN'),
                        'currency': bank_data.get('currency', 'USD')
                    }
        except:
            continue
    
    # Fallback to local database if APIs fail
    return get_bin_info_local(card_number)

def get_bin_info_local(card_number):
    """Enhanced local BIN database"""
    bin_code = card_number[:6]
    
    bin_db = {
        # US Banks
        '552342': {'type': 'Credit', 'brand': 'Mastercard', 'bank': 'CAPITAL ONE, NATIONAL ASSOCIATION', 'country': 'UNITED STATES', 'currency': 'USD'},
        '411111': {'type': 'Credit', 'brand': 'Visa', 'bank': 'CHASE BANK USA, N.A.', 'country': 'UNITED STATES', 'currency': 'USD'},
        '511111': {'type': 'Credit', 'brand': 'Mastercard', 'bank': 'BANK OF AMERICA', 'country': 'UNITED STATES', 'currency': 'USD'},
        '453211': {'type': 'Credit', 'brand': 'Visa', 'bank': 'CITIBANK N.A.', 'country': 'UNITED STATES', 'currency': 'USD'},
        '542418': {'type': 'Credit', 'brand': 'Mastercard', 'bank': 'WELLS FARGO BANK', 'country': 'UNITED STATES', 'currency': 'USD'},
        '371449': {'type': 'Credit', 'brand': 'American Express', 'bank': 'AMERICAN EXPRESS', 'country': 'UNITED STATES', 'currency': 'USD'},
        '601100': {'type': 'Credit', 'brand': 'Discover', 'bank': 'DISCOVER BANK', 'country': 'UNITED STATES', 'currency': 'USD'},
        '476676': {'type': 'Debit', 'brand': 'Visa', 'bank': 'HSBC AMANAH MALAYSIA BERHAD', 'country': 'MALAYSIA', 'currency': 'MYR'},
        '483316': {'type': 'Debit', 'brand': 'Visa', 'bank': 'UNKNOWN BANK', 'country': 'UNITED STATES', 'currency': 'USD'},
        '465946': {'type': 'Credit', 'brand': 'Visa', 'bank': 'BARCLAYS BANK', 'country': 'UNITED KINGDOM', 'currency': 'GBP'},
        '549099': {'type': 'Credit', 'brand': 'Mastercard', 'bank': 'HSBC UK', 'country': 'UNITED KINGDOM', 'currency': 'GBP'},
        '453957': {'type': 'Credit', 'brand': 'Visa', 'bank': 'ROYAL BANK OF CANADA', 'country': 'CANADA', 'currency': 'CAD'},
        '557365': {'type': 'Credit', 'brand': 'Mastercard', 'bank': 'SCOTIABANK', 'country': 'CANADA', 'currency': 'CAD'},
        '456472': {'type': 'Credit', 'brand': 'Visa', 'bank': 'COMMONWEALTH BANK OF AUSTRALIA', 'country': 'AUSTRALIA', 'currency': 'AUD'},
        '552218': {'type': 'Credit', 'brand': 'Mastercard', 'bank': 'WESTPAC BANKING CORPORATION', 'country': 'AUSTRALIA', 'currency': 'AUD'},
        '491748': {'type': 'Credit', 'brand': 'Visa', 'bank': 'DEUTSCHE BANK', 'country': 'GERMANY', 'currency': 'EUR'},
        '550474': {'type': 'Credit', 'brand': 'Mastercard', 'bank': 'BNP PARIBAS', 'country': 'FRANCE', 'currency': 'EUR'},
    }
    
    default_info = {'type': 'Unknown', 'brand': 'Unknown', 'bank': 'UNKNOWN BANK', 'country': 'UNKNOWN', 'currency': 'USD'}
    return bin_db.get(bin_code, default_info)

def get_bin_info(card_number):
    """Main BIN info function - tries API first, then local database"""
    try:
        # Try online API first
        api_info = get_bin_info_from_api(card_number)
        if api_info['bank'] != 'UNKNOWN BANK':
            return api_info
    except:
        pass
    
    # Fallback to local database
    return get_bin_info_local(card_number)
