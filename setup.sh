#!/bin/bash

echo "🚀 Setting up Ara Araass Checker on Ubuntu..."

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and required packages
sudo apt install -y python3 python3-pip python3-venv curl

# Create virtual environment
python3 -m venv botenv
source botenv/bin/activate

# Install Python packages
pip install -r requirements.txt

# Create .env file if not exists
if [ ! -f .env ]; then
    cat > .env << EOL
BOT_TOKEN=YOUR_BOT_TOKEN_HERE
ADMIN_ID=YOUR_ADMIN_ID_HERE
EOL
    echo "⚠️ Please edit .env file with your bot token and admin ID"
fi

echo "✅ Setup complete!"
echo "📝 Edit .env file with your credentials"
echo "🚀 Start bot with: source botenv/bin/activate && python bot.py"
