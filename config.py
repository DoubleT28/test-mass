import os
import json
from dotenv import load_dotenv

load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN', '8077915640:AAE0ntUcx_EwMR2IJi7XaxeuB6rs4606_i0E')
ADMIN_ID = os.getenv('ADMIN_ID', '841100316')

# File paths
CONFIG_FILE = 'data/config.json'
SESSION_FILE = 'data/session.json'
USERS_FILE = 'data/users.json'
BANNED_FILE = 'data/banned.json'
UPLOAD_DIR = 'uploads'

# Ensure directories exist
os.makedirs('data', exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# User Agents
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0'
]
