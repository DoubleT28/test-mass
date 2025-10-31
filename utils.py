import json
import os
import random
import string

def load_config():
    try:
        from config import *
        return {
            'proxy_host': '',
            'proxy_port': '', 
            'proxy_username': '',
            'proxy_password': ''
        }
    except:
        return {}

def save_config(config):
    pass

def load_users():
    try:
        with open('data/users.json', 'r') as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    os.makedirs('data', exist_ok=True)
    with open('data/users.json', 'w') as f:
        json.dump(users, f)

def load_banned():
    try:
        with open('data/banned.json', 'r') as f:
            return json.load(f)
    except:
        return []

def save_banned(banned_list):
    os.makedirs('data', exist_ok=True)
    with open('data/banned.json', 'w') as f:
        json.dump(banned_list, f)

def load_session():
    try:
        with open('data/session.json', 'r') as f:
            return json.load(f)
    except:
        return {}

def save_session(session):
    os.makedirs('data', exist_ok=True)
    with open('data/session.json', 'w') as f:
        json.dump(session, f)

def generate_identifier(type):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=16))

def get_bin_info(cc_no):
    return {
        'bank': 'Unknown Bank',
        'brand': 'Unknown Brand', 
        'type': 'Unknown Type',
        'country': 'Unknown Country'
    }

def can_use_bot(user_id):
    banned = load_banned()
    return str(user_id) not in banned

def is_admin(user_id):
    return str(user_id) == ADMIN_ID

def add_user(user_id, username="", is_premium=False):
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
    if is_admin(user_id):
        return "👑 Alpha Admin"
    users = load_users()
    user = users.get(str(user_id), {})
    if user.get('is_premium'):
        return "⭐ Premium User"
    return "👤 Basic User"

def ban_user(user_id):
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
    banned = load_banned()
    if str(user_id) in banned:
        banned.remove(str(user_id))
        save_banned(banned)
        return True
    return False

def set_premium(user_id, premium_status):
    users = load_users()
    if str(user_id) in users:
        users[str(user_id)]['is_premium'] = premium_status
        save_users(users)
        return True
    return False

def remove_user(user_id):
    users = load_users()
    if str(user_id) in users:
        del users[str(user_id)]
        save_users(users)
        return True
    return False
