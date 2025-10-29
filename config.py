import os
import json
from dotenv import load_dotenv

load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
ADMIN_ID = os.getenv('ADMIN_ID', 'YOUR_ADMIN_ID_HERE')

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
