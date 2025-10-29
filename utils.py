import json
import os
import random
import string
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
    return {"total": 0, "processed": 0, "live": 0, "insufficient": 0, "hit": 0, "current_file": ""}

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

def add_user(user_id, username=""):
    if is_banned(user_id):
        return False
    
    users = load_users()
    user_id_str = str(user_id)
    
    if user_id_str not in users:
        users[user_id_str] = {
            'id': user_id_str,
            'username': username,
            'joined': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'access_count': 0,
            'hits_found': 0
        }
        save_users(users)
    return True

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
