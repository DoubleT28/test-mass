import os

# Bot Configuration
BOT_TOKEN = "8077915640:AAE0ntUcx_EwMR2IJi7XaxeuB6rs4606_i0"
ADMIN_ID = "841100316"

# File paths  
UPLOAD_DIR = "uploads"
DATA_DIR = "data"

# Create directories if they don't exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# User agents for requests
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
]
