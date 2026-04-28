import asyncio
import os
import threading
from flask import Flask
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from datetime import datetime

# --- Flask Keep-Alive Setup ---
app = Flask('')

@app.route('/')
def home():
    return "BoD AI Proxy System is Active!"

def run_flask():
    # Render ကပေးတဲ့ PORT ကို ယူသုံးပါမယ်
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# --- Configuration ---
API_ID = 38225985
API_HASH = '0b6330bc916f9e29d6bf302be079e9d6'
OWNER_ID = 7693106830
AI_BOT_ID = 8091345445 

SESSION_STRING = "1BVtsOIMBu5q47Yk7lvLZHBNZcEzXRXMU-B_4nKjlxNp4LXfBN1qFvlArW56vX58522EwtnOdFfWZsKV-cn4Xx3Byrrv1FsbOog8rcZ6m8u8ZdrGzPwYsNfTblkzbJASQCHCHZnHnA_yD4XHOX4A51FDlVvPJJTyzPW2uCHw-1bu_NXVTGR7sHJdR4LJnKMu7zLkLl300WG4fGXeRby1rCLNtm9USnh8sWv4C3vIyH0wbC6GRteuSzkjJBBpIy-NIDj-0IVeVQtyt-lhXMTlcgPmPkT9xmvYBrQ8xvoF-vigttRnVXmn6uC0Mi8NbKY1ufUMYol0NDYtNI9mECSagfAowTId2aSs="

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# --- Data Storage ---
authorized_users = {OWNER_ID} 
usage_tracker = {} 

def get_today():
    return datetime.now().strftime('%Y-%m-%d')

def check_usage(user_id):
    today = get_today()
    if user_id not in usage_tracker or usage_tracker[user_id]['last_date'] != today:
        usage_tracker[user_id] = {'count': 0, 'last_date': today}
    return usage_tracker[user_id]['count']

# --- Handlers ---

@client.on(events.NewMessage(pattern=r'^ဖြေခွင့်ပေးတယ်$'))
async def grant_permission(event):
    if event.sender_id != OWNER_ID: return
    reply = await event.get_reply_message()
    if reply:
        authorized_users.add(reply.sender_id)
        mention = f"<a href='tg://user?id={reply.sender_id}'>ဒီလူသား</a>"
        await event.respond(f"သခင်လေးရဲ့ အမိန့်အရ {mention} ကို 'ဖြေ' cmd သုံးခွင့် ပေးလိုက်ပါပြီ။", parse_mode='html')

@client.on(events.NewMessage(pattern=r'^ဖြေ\s+(.*)'))
async def ai_proxy(event):
    user_id = event.sender_id
    if user_id not in authorized_users: return 

    count = check_usage(user_id)
    if count >= 3:
        await event.reply("စိတ်မရှိပါနဲ့... တစ်ရက်ကို ၃ ကြိမ်ပဲ မေးမြန်းခွင့် ရှိပါတယ်ဗျ။")
        return

    question = event.pattern_match.group(1)
    sender = await event.get_sender()
    first_name = sender.first_name if sender.first_name else "User"
    mention = f"[{first_name}](tg://user?id={user_id})"

    try:
        async with client.conversation(AI_BOT_ID) as conv:
            await conv.send_message(question)
            response = await conv.get_response()
            ai_text = response.text
            
            usage_tracker[user_id]['count'] += 1
            remains = 3 - usage_tracker[user_id]['count']

            final_msg = (
                f"ဟိတ် {mention}\nအဖြေကဒီမှာ\n\n"
                f"{ai_text}\n\n"
                f"__Created by Khant ThuRain__\n"
                f"*(ကျန်ရှိသောအကြိမ်ရေ - {remains})*"
            )
            await event.respond(final_msg)
    except Exception as e:
        await event.reply("AI Bot က အဖြေပြန်မပေးပါဘူးဗျ။")

# --- Start System ---
if __name__ == "__main__":
    # Flask ကို Thread တစ်ခုနဲ့ သီးသန့် Run ပါမယ်
    threading.Thread(target=run_flask, daemon=True).start()
    
    print("🦇 BoD AI UserBot with Flask is Running...")
    client.start()
    client.run_until_disconnected()
