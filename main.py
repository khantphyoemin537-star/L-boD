import asyncio
from telethon import TelegramClient, events
from datetime import datetime

# --- Configuration ---
API_ID = 38225985
API_HASH = '0b6330bc916f9e29d6bf302be079e9d6'
OWNER_ID = 7693106830
AI_BOT_ID = 8091345445  # @chatgpt_ai_ime_bot

client = TelegramClient('bod_user_session', API_ID, API_HASH)

# --- Data Storage (In-memory) ---
# တစ်ရက်စာ usage ကို သိမ်းဖို့ (Restart ချရင် reset ဖြစ်ပါမယ်)
authorized_users = {OWNER_ID} # Owner ကို အမြဲ ခွင့်ပြုထားမယ်
usage_tracker = {} # {user_id: {'count': 0, 'last_date': 'YYYY-MM-DD'}}

# --- Helper Functions ---
def get_today():
    return datetime.now().strftime('%Y-%m-%d')

def check_usage(user_id):
    today = get_today()
    if user_id not in usage_tracker or usage_tracker[user_id]['last_date'] != today:
        usage_tracker[user_id] = {'count': 0, 'last_date': today}
    return usage_tracker[user_id]['count']

# --- Handlers ---

# ၁။ ဖြေခွင့်ပေးခြင်း (Reply ထောက်ပြီး "ဖြေခွင့်ပေးတယ်" ဟု ရိုက်ပါ)
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
    today = get_today()
    
    # ခွင့်ပြုချက်ရှိမရှိ စစ်မယ်
    if user_id not in authorized_users:
        return # ခွင့်ပြုချက်မရှိရင် ဘာမှမလုပ်ဘူး

    # Usage Limit စစ်မယ် (တစ်ရက် ၃ ကြိမ်)
    count = check_usage(user_id)
    if count >= 3:
        await event.reply("စိတ်မရှိပါနဲ့... တစ်ရက်ကို ၃ ကြိမ်ပဲ မေးမြန်းခွင့် ရှိပါတယ်ဗျ။")
        return

    question = event.pattern_match.group(1)
    sender = await event.get_sender()
    mention = f"[{sender.first_name}](tg://user?id={user_id})"

    # AI Bot ဆီကို မေးခွန်း ပို့မယ်
    try:
        async with client.conversation(AI_BOT_ID) as conv:
            await conv.send_message(question)
            # Bot ဆီက အဖြေကို စောင့်မယ်
            response = await conv.get_response()
            ai_text = response.text
            
            # Usage count တိုးမယ်
            usage_tracker[user_id]['count'] += 1
            remains = 3 - usage_tracker[user_id]['count']

            # မူလ Group/Chat ထဲမှာ ပြန်ဖြေမယ်
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

print("🦇 BoD AI UserBot is Running...")
client.start()
client.run_until_disconnected()
