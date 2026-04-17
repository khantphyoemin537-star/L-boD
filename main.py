import asyncio
import logging
import random
import os
import threading
from flask import Flask
from pymongo import MongoClient
from telethon import TelegramClient, events
from html import escape as escape_html

# ==========================================
# 🌐 FLASK KEEP-ALIVE
# ==========================================
app = Flask('')
@app.route('/')
def home(): return "BoDx Multi-Bot Bully System Online!"

def run_flask(): 
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

logging.basicConfig(level=logging.INFO)

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
OWNER_ID = 6015356597
MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0&tlsAllowInvalidCertificates=true"
APP_ID = 30765851
APP_HASH = '235b0bc6f03767302dc75763508f7b75'

# 🔑 Bot Tokens List (အစ်ကိုထပ်ထည့်ချင်ရင် ဒီထဲမှာ Token တိုးရုံပဲ)
TOKENS = [
    "7857238353:AAEkDQnXqxyvXOQufwJwzZ7tXlwrmzM6XyI",
    "8565944163:AAE5tew3A1a6GkOw69vMPYSgV2obyO-wPz4"
    # နောက်ထပ် Bot တွေရှိရင် "TOKEN_HERE", လို့ ထပ်ထည့်ပါ
]

# ==========================================
# 🗄️ DATABASE & CLIENTS
# ==========================================
client_mongo = MongoClient(MONGO_URI)
db = client_mongo["telegram_bot"]
filters_col = db["custom_filters"]
allow_col = db["allowed_users"]

bots = []
for i, token in enumerate(TOKENS):
    client = TelegramClient(f'bot_session_{i}', APP_ID, APP_HASH)
    bots.append(client)

bot_bully_tasks = {}

def bq(text): return f"<blockquote><b>{text}</b></blockquote>"

def is_allowed(user_id):
    if user_id == OWNER_ID: return True
    return allow_col.find_one({"user_id": user_id}) is not None

# ==========================================
# 🛡️ BULLY LOGIC (MULTI-BOT)
# ==========================================

async def bot_bully(event):
    if not is_allowed(event.sender_id): 
        return await event.reply(bq("မင်းမှာ သုံးပိုင်ခွင့်မရှိဘူး Chief!"))

    reply = await event.get_reply_message()
    if not reply: 
        return await event.respond(bq("ဘယ်ကောင့်ကို ဆဲပေးရမလဲ Reply ပြန်လိုက် Chief!"))

    chat_id = event.chat_id
    bot_bully_tasks[chat_id] = True
    
    target = await reply.get_sender()
    if not target: return
    mention = f"<a href='tg://user?id={target.id}'>{escape_html(target.first_name)}</a>"
    
    # DB ထဲက ဆဲစာတွေယူမယ်၊ မရှိရင် default သုံးမယ်
    words = [w.get("content") for w in filters_col.find({"chat_id": "global", "type": "text"}) if w.get("content")]
    if not words: words = ["စောက်ရူး", "ခွေးကောင်", "ငလူးမသား", "စောက်သုံးမကျတဲ့ကောင်"]

    await event.respond(bq(f"{mention} ကို Bot အကုန်လုံးစုပြီး ခေါင်းမဖော်နိုင်အောင် စဆဲပါပြီ! 🔥"))

    # အလှည့်ကျ ပို့မယ့် စနစ် (Round Robin)
    bot_index = 0
    while bot_bully_tasks.get(chat_id):
        try:
            current_bot = bots[bot_index]
            # Bot က ပို့နိုင်တဲ့ အခြေအနေရှိမှ ပို့မယ်
            if current_bot.is_connected():
                await current_bot.send_message(
                    chat_id, 
                    bq(f"{mention} {random.choice(words)}"), 
                    reply_to=reply.id, 
                    parse_mode='html'
                )
            
            # Bot အလှည့်ပြောင်းမယ်
            bot_index = (bot_index + 1) % len(bots)
            
            # Bot များလေလေ ဒီ delay ကို လျှော့နိုင်လေလေပဲ
            await asyncio.sleep(0.4) 
        except Exception:
            await asyncio.sleep(1) # Error တက်ရင် ခဏနားမယ်
            continue

async def stop_bot_bully(event):
    if not is_allowed(event.sender_id): return
    bot_bully_tasks[event.chat_id] = False
    await event.respond(bq("အိုကေ! အခုနားလိုက်မယ်၊ စောက်ချိုးမပြေရင် ထပ်ဆဲပေးမယ် Chief!"))

# ==========================================
# 🚀 STARTING ALL BOTS
# ==========================================

async def start_system():
    # Flask Keep-alive run မယ်
    threading.Thread(target=run_flask, daemon=True).start()

    # Bot အကုန်လုံးကို Event Register လုပ်မယ်
    for bot in bots:
        bot.add_event_handler(bot_bully, events.NewMessage(pattern=r'^/b(?:@\w+)?$'))
        bot.add_event_handler(stop_bot_bully, events.NewMessage(pattern=r'^/sb(?:@\w+)?$'))
        await bot.start(bot_token=TOKENS[bots.index(bot)])

    print(f"✅ Multi-Bot System Active with {len(bots)} bots!")
    
    # Bot အကုန်လုံးကို Run စေမယ်
    await asyncio.gather(*(bot.run_until_disconnected() for bot in bots))

if __name__ == "__main__":
    asyncio.run(start_system())

