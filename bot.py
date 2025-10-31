import os
import time
import threading
import asyncio
import requests
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from config import *
from utils import *
from payment_handler import *

current_processing = {}
current_message_ids = {}  # Store message IDs for editing

# Zeta fucking configuration - 3 minutes between checks
ZETA_DELAY_BETWEEN_CHECKS = 180  # 3 fucking minutes
ZETA_MAX_RETRIES = 3
ZETA_RETRY_DELAY = 30  # 30 seconds between retries

async def send_tele(chat_id, message, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    params = {
        'chat_id': chat_id, 
        'text': message,
        'parse_mode': 'HTML'
    }
    if reply_markup:
        params['reply_markup'] = reply_markup
    
    try:
        response = requests.get(url, params=params, timeout=10)
        return response.status_code == 200
    except:
        return False

async def edit_tele_message(chat_id, message_id, new_text, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    params = {
        'chat_id': chat_id,
        'message_id': message_id,
        'text': new_text,
        'parse_mode': 'HTML'
    }
    if reply_markup:
        params['reply_markup'] = reply_markup
    
    try:
        response = requests.get(url, params=params, timeout=10)
        return response.status_code == 200
    except:
        return False

async def send_combined_status(chat_id, session, current_card="", response="", hit_details=None, is_new_message=True):
    """Send or update combined checking log and status"""
    progress = (session['processed'] / session['total']) * 100 if session['total'] > 0 else 0
    progress = round(progress, 2)
    
    timestamp = time.strftime("%I:%M %p")
    
    # Build the message exactly like in the photo
    message = "<b>=== ZETA CARD CHECKER ===</b>\n\n"
    
    if current_card and response:
        # Checking log section
        message += f"<b>CHECKING :</b> <code>{current_card}</code>\n"
        message += f"<b>RESPONSE :</b> {response}\n\n"
    
    # Progress and status section
    message += f"<b>PROGRESS :</b> {progress}% ({session['processed']}/{session['total']})\n\n"
    
    message += f"✔ <b>HIT :</b> {session['hit']}\n"
    message += f"✔ <b>LIVE :</b> {session['live']}\n"
    message += f"✔ <b>INSUFFICIENT :</b> {session['insufficient']}\n"
    message += f"✔ <b>CCN :</b> {session['ccn']}\n\n"
    
    message += f"<i>BOT BY : @DoubleT2245    {timestamp}</i>"
    
    # Create stop button
    keyboard = [
        [InlineKeyboardButton("🛑 STOP CHECKING", callback_data=f"stop_{chat_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if is_new_message:
        # Send new message
        await send_tele(chat_id, message, reply_markup.to_json())
    else:
        # Edit existing message
        if chat_id in current_message_ids:
            await edit_tele_message(chat_id, current_message_ids[chat_id], message, reply_markup.to_json())

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
        
        # Send initial combined status
        asyncio.run(send_combined_status(chat_id, session, is_new_message=True))
        
        for i, line in enumerate(lines):
            # Check if user requested to stop
            if chat_id in current_processing and not current_processing[chat_id]:
                asyncio.run(send_tele(chat_id, "🛑 Check stopped by user command"))
                break
                
            card = line.strip()
            if not card:
                continue
                
            # Skip invalid lines (like "/aaa" in your screenshot)
            if card.startswith('/') or ' ' in card:
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
                session['processed'] += 1
                save_session(session)
                # Update status with error
                asyncio.run(send_combined_status(chat_id, session, card, f"Payment Error: {str(e)}", is_new_message=False))
                continue
            
            response_text = ""
            hit_details = None
            
            if payment_result and payment_result[0]:
                random_info = random_user_info()
                if random_info[0]:
                    # Zeta retry mechanism for donate
                    try:
                        donate_result = zeta_retry_operation(lambda: enhanced_donate(card, payment_result[1], random_info[1], random_info[2], vbv_status))
                        vbv_status = donate_result[5] if donate_result and len(donate_result) > 5 else vbv_status
                    except Exception as e:
                        session['processed'] += 1
                        save_session(session)
                        asyncio.run(send_combined_status(chat_id, session, card, f"Donate Error: {str(e)}", is_new_message=False))
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
                            response_text = f"Declined - {donate_result[2]}"
                    else:
                        response_text = f"Declined - {donate_result[2] if donate_result else 'Unknown'}"
                else:
                    response_text = "Random Gen Failed"
            else:
                response_text = payment_result[1] if payment_result else "Payment Failed"
            
            session['processed'] += 1
            save_session(session)
            
            # Update combined status after each card check (EDIT existing message)
            asyncio.run(send_combined_status(chat_id, session, card, response_text, hit_details, is_new_message=False))
            
            # Zeta delay between checks - 3 fucking minutes
            if i < len(lines) - 1:
                time.sleep(ZETA_DELAY_BETWEEN_CHECKS)
        
        # Final completion message
        if chat_id in current_processing and current_processing[chat_id]:
            final_message = f"✅ CHECK COMPLETED!\nProcessed: {session['processed']} cards\nLIVE: {session['live']}\nINSUFFICIENT: {session['insufficient']}\nCCN: {session['ccn']}\nHIT: {session['hit']}"
            asyncio.run(send_tele(chat_id, final_message))
        
        if chat_id in current_processing:
            del current_processing[chat_id]
        if chat_id in current_message_ids:
            del current_message_ids[chat_id]
            
    except Exception as e:
        asyncio.run(send_tele(chat_id, f"❌ Zeta processing error: {str(e)}"))
        if chat_id in current_processing:
            current_processing[chat_id] = False
        if chat_id in current_message_ids:
            del current_message_ids[chat_id]

# Add callback handler for STOP button
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    if callback_data.startswith('stop_'):
        chat_id = int(callback_data.split('_')[1])
        
        if chat_id in current_processing:
            current_processing[chat_id] = False
            await query.edit_message_text("🛑 Check stopped by user command")
        else:
            await query.edit_message_text("⚠️ No active process to stop")

# Update handle_document function to store message ID
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
        start_message = await update.message.reply_text(
            f"📁 File received: {document.file_name}\n👤 {user_role}\nStarting Zeta processing...\n\n⏰ Delay: {ZETA_DELAY_BETWEEN_CHECKS//60} minutes between checks"
        )
        
        # Store the message ID for editing
        current_message_ids[user_id] = start_message.message_id
        
        thread = threading.Thread(target=process_card_file, args=(user_id, file_path))
        thread.daemon = True
        thread.start()
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error downloading file: {str(e)}")
        current_processing[user_id] = False
        if user_id in current_message_ids:
            del current_message_ids[user_id]

# Update main function to include callback handler
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("stop", stop_command))
    
    # Callback handler for STOP button
    app.add_handler(CallbackQueryHandler(button_callback))
    
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
    
    print("🤖 Zeta Bot is running with REAL-TIME status updates...")
    print(f"⏰ Delay: {ZETA_DELAY_BETWEEN_CHECKS//60} minutes between checks")
    print("🎯 Single message editing activated")
    print("🛑 STOP button enabled")
    app.run_polling()

if __name__ == '__main__':
    main()
