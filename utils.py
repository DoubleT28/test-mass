import json
import os
import random
import string

# Import config properly
try:
    from config import BOT_TOKEN, ADMIN_ID, UPLOAD_DIR, DATA_DIR, USER_AGENTS
except ImportError:
    # Fallback values if config not found
    BOT_TOKEN = "8077915640:AAE0ntUcx_EwMR2IJi7XaxeuB6rs4606_i0"
    ADMIN_ID = "841100316"
    UPLOAD_DIR = "uploads"
    DATA_DIR = "data"
    USER_AGENTS = ["Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"]

def load_config():
    """Load configuration"""
    try:
        return {
            'proxy_host': '',
            'proxy_port': '', 
            'proxy_username': '',
            'proxy_password': ''
        }
    except:
        return {}

def save_config(config):
    """Save configuration"""
    pass

def load_users():
    """Load users from JSON file"""
    try:
        with open('data/users.json', 'r') as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    """Save users to JSON file"""
    os.makedirs('data', exist_ok=True)
    with open('data/users.json', 'w') as f:
        json.dump(users, f, indent=2)

def load_banned():
    """Load banned users list"""
    try:
        with open('data/banned.json', 'r') as f:
            return json.load(f)
    except:
        return []

def save_banned(banned_list):
    """Save banned users list"""
    os.makedirs('data', exist_ok=True)
    with open('data/banned.json', 'w') as f:
        json.dump(banned_list, f, indent=2)

def load_session():
    """Load current session data"""
    try:
        with open('data/session.json', 'r') as f:
            return json.load(f)
    except:
        return {
            'total': 0,
            'processed': 0,
            'live': 0,
            'insufficient': 0,
            'hit': 0,
            'ccn': 0,
            'current_file': ''
        }

def save_session(session):
    """Save session data"""
    os.makedirs('data', exist_ok=True)
    with open('data/session.json', 'w') as f:
        json.dump(session, f, indent=2)

def generate_identifier(type):
    """Generate random identifier"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=16))

def get_bin_info(cc_no):
    """Get BIN information for card"""
    # Simple BIN lookup - you can enhance this later
    bin_data = {
        '4': {'bank': 'Visa', 'brand': 'Visa', 'type': 'Credit', 'country': 'International'},
        '5': {'bank': 'MasterCard', 'brand': 'MasterCard', 'type': 'Credit', 'country': 'International'}, 
        '3': {'bank': 'American Express', 'brand': 'Amex', 'type': 'Credit', 'country': 'International'},
        '6': {'bank': 'Discover', 'brand': 'Discover', 'type': 'Credit', 'country': 'International'}
    }
    
    first_digit = cc_no[0] if cc_no else '4'
    return bin_data.get(first_digit, {
        'bank': 'Unknown Bank',
        'brand': 'Unknown Brand', 
        'type': 'Unknown Type',
        'country': 'Unknown Country'
    })

def can_use_bot(user_id):
    """Check if user can use the bot"""
    banned = load_banned()
    return str(user_id) not in banned

def is_admin(user_id):
    """Check if user is admin"""
    return str(user_id) == ADMIN_ID

def add_user(user_id, username="", is_premium=False):
    """Add new user"""
    users = load_users()
    users[str(user_id)] = {
        'id': str(user_id),
        'username': username,
        'is_premium': is_premium,
        'is_active': True,
        'joined': '2024-01-01',
        'hits_found': 0
    }
    save_users(users)
    return True

def get_user_role(user_id):
    """Get user role display"""
    if is_admin(user_id):
        return "👑 Alpha Admin"
    users = load_users()
    user = users.get(str(user_id), {})
    if user.get('is_premium'):
        return "⭐ Premium User"
    return "👤 Basic User"

def ban_user(user_id):
    """Ban user from using bot"""
    banned = load_banned()
    if str(user_id) not in banned:
        banned.append(str(user_id))
        save_banned(banned)
        
        users = load_users()
        if str(user_id) in users:
            del users[str(user_id)]
            save_users(users)
        return True
    return False

def unban_user(user_id):
    """Unban user"""
    banned = load_banned()
    if str(user_id) in banned:
        banned.remove(str(user_id))
        save_banned(banned)
        return True
    return False

def set_premium(user_id, premium_status):
    """Set premium status for user"""
    users = load_users()
    if str(user_id) in users:
        users[str(user_id)]['is_premium'] = premium_status
        save_users(users)
        return True
    return False

def remove_user(user_id):
    """Remove user"""
    users = load_users()
    if str(user_id) in users:
        del users[str(user_id)]
        save_users(users)
        return True
    return False

def random_user_info():
    """Generate random user info"""
    first_names = ["James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas", "Charles"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
    domains = ["gmail.com", "outlook.com", "hotmail.com", "yahoo.com"]
    
    first_name = random.choice(first_names)
    last_name = random.choice(last_names)
    email = f"{first_name.lower()}.{last_name.lower()}{random.randint(100,999)}@{random.choice(domains)}"
    
    return [True, first_name, email]
