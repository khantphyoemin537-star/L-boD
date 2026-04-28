import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from datetime import datetime

# --- Configuration ---
API_ID = 38225985
API_HASH = '0b6330bc916f9e29d6bf302be079e9d6'
OWNER_ID = 7693106830
AI_BOT_ID = 8091345445  # @chatgpt_ai_ime_bot

# သခင်လေး ပေးထားတဲ့ Session String
SESSION_STRING = "1BVtsOIMBu2-y9NUI6nGmsWMnRXqYji54DT2OulJwBfV1BwZt8gJcumGqGN6019QzXdNF2lQ1Y-AH-IoSUKUYgcQImS_uQCZwIIDTgQDPyJt-K1-TECl-FtngHpDALvP5v7wZHACXB2MT0e3RsXxp7WUwG-2aeZ47EcqGbWNxIJAMZX0ai_V1KWlxGEy6Zruq5xCTX_33cuATupNCu1jkRn6D43ogdZqOzRp6Vu_PLjHXUdeeloSqX4XL7UkF-LqGyME1xcacPq8IX8SdYjxiPcARvN2ubwwH4PpfZQcf37gUwGq4fP8a8G2Ensn6yjKjqnXSXyEjN2mNVpQ7VYLpww7FURgDCAk="

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# --- Data Storage (In-memory) ---
authorized_users = {OWNER_ID} 
usage_tracker = {} 

# --- Helper Functions ---
def get_today():
    return datetime.now().strftime('%Y-%m-%d')

def check_usage(user_id):
    today = get_today()
    if user_id not in usage_tracker or usage_tracker[user_id]['last_date'] != today:
        usage_tracker[user_id] = {'count': 0, 'last_date': today}
    return usage_tracker[user_id]['count']

# --- Handlers ---

# ၁။ ဖြေခွင့်ပေးခြင်း
@client.on(events.NewMessage(pattern=r'^ဖြေခွင့်ပေးတယ်$'))
async def grant_permission(event):
    if event.sender_id != OWNER_ID: return
    reply = await event.get_reply_message()
    if reply:
        authorized_users.add(reply.sender_id)
        mention = f"<a href='tg://user?id={reply.sender_id}'>ဒီလူသား</a>"
        await event.respond(f"သခင်လေးရဲ့ အမိန့်အရ {mention} ကို 'ဖြေ' cmd သုံးခွင့် ပေးလိုက်ပါပြီ။", parse_mode='html')

# ၂။ AI ဖြေဆိုခြင်း စနစ်
@client.on(events.NewMessage(pattern=r'^ဖြေ\s+(.*)'))
async def ai_proxy(event):
    user_id = event.sender_id
    
    # ခွင့်ပြုချက်ရှိမရှိ စစ်မယ်
    if user_id not in authorized_users:
        return 

    # Usage Limit စစ်မယ် (တစ်ရက် ၃ ကြိမ်)
    count = check_usage(user_id)
    if count >= 3:
        await event.reply("စိတ်မရှိပါနဲ့... တစ်ရက်ကို ၃ ကြိမ်ပဲ မေးမြန်းခွင့် ရှိပါတယ်ဗျ။")
        return

    question = event.pattern_match.group(1)
    sender = await event.get_sender()
    first_name = sender.first_name if sender.first_name else "User"
    mention = f"[{first_name}](tg://user?id={user_id})"

    # AI Bot ဆီကို မေးခွန်း ပို့မယ်
    try:
        async with client.conversation(AI_BOT_ID) as conv:
            await conv.send_message(question)
            response = await conv.get_response()
            ai_text = response.text
            
            # Usage count တိုးမယ်
            usage_tracker[user_id]['count'] += 1
            remains = 3 - usage_tracker[user_id]['count']

            # မူလနေရာမှာ ပြန်ဖြေမယ်
            final_msg = (
                f"ဟိတ် {mention}\n"
                f"အဖြေကဒီမှာ\n\n"
                f"{ai_text}\n\n"
                f"__Created by Khant ThuRain__\n"
                f"*(တစ်ရက် ၃ ကြိမ်ပဲ မေးမြန်းခွင့်ရှိပါတယ် - {remains} ကြိမ် ကျန်သေးတယ်)*"
            )
            await event.respond(final_msg)
            
    except Exception as e:
        await event.reply("AI Bot ဆီက အဖြေယူရာမှာ အဆင်မပြေဖြစ်သွားပါတယ်။")

print("🦇 BoD AI UserBot is Running with StringSession...")
client.start()
client.run_until_disconnected()
