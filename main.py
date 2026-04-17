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
def home(): return "BoDx Sovereign System Active!"

def run_flask(): 
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

logging.basicConfig(level=logging.ERROR)

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
OWNER_ID = 6015356597
MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0&tlsAllowInvalidCertificates=true"
APP_ID = 30765851
APP_HASH = '235b0bc6f03767302dc75763508f7b75'

TOKENS = [
    "7857238353:AAEkDQnXqxyvXOQufwJwzZ7tXlwrmzM6XyI",
    "8565944163:AAE5tew3A1a6GkOw69vMPYSgV2obyO-wPz4"
]

# ==========================================
# 🗄️ DATABASE SETUP
# ==========================================
client_mongo = MongoClient(MONGO_URI)
db = client_mongo["telegram_bot"]
filters_col = db["filters"] 
allow_col = db["allowed_users"]

bots = []
for i, token in enumerate(TOKENS):
    client = TelegramClient(f'session_bot_{i}', APP_ID, APP_HASH)
    bots.append(client)

bot_bully_tasks = {}

def bq(text): 
    safe_text = escape_html(str(text))
    return f"<blockquote><b>{safe_text}</b></blockquote>"

def is_allowed(user_id):
    if user_id == OWNER_ID: return True
    return allow_col.find_one({"user_id": user_id}) is not None

# ==========================================
# 🛡️ [5] /b Bully - Fixed Multi-Bot Logic
# ==========================================

async def bot_bully(event):
    # Permission Check
    if not is_allowed(event.sender_id): 
        return await event.reply(bq("မင်းမှာ ဒီ Command ကို သုံးပိုင်ခွင့်မရှိဘူး။သုံးခွင့်နဲ့အသုံးပြုနည်းများအတွက် @Besties_with_BoD ကိုလာ "), parse_mode='html')
    
    # Reply Check
    reply = await event.get_reply_message()
    if not reply: 
        return await event.respond(bq("ဘယ်ကောင့်ကို ခေါင်းမဖော်နိုင်အောင် ဆဲပေးရမလဲ၊Replyပြန်လိုက် "), parse_mode='html')

    # Command ကို ဖျက်တယ်
    try: await event.delete() 
    except: pass

    chat_id = event.chat_id
    t = await reply.get_sender()
    if not t: return

    target_id = t.id
    # Creator Protection
    if target_id == OWNER_ID:
        await event.respond(bq("ဟိတ်ကောင် Creatorကို ပြန်ပြီးဆဲဆိုခွင့် မပေးထားဘူး🔥"), parse_mode='html')
        return

    bot_bully_tasks[chat_id] = True
    mention = f"<a href='tg://user?id={target_id}'>{escape_html(t.first_name)}</a>"
    
    # DB က စာလုံးတွေကို ယူတယ် (text field)
    words = [w.get("text") for w in filters_col.find() if w.get("text")]
    if not words: 
        return await event.respond(bq("DB (filters collection) ထဲမှာ စာလုံးမရှိသေးဘူး Chief!"))

    await event.respond(bq(f"{mention} ကို ခေါင်းမဖော်နိုင်အောင် စဆဲပါပြီ။"), parse_mode='html')

    send_count = 0
    bot_index = 0 # Bot အလှည့်ကျသုံးဖို့

    while bot_bully_tasks.get(chat_id):
        try: 
            # လက်ရှိအလှည့်ကျတဲ့ Bot နဲ့ ပို့မယ်
            current_bot = bots[bot_index]
            if current_bot.is_connected():
                await current_bot.send_message(
                    chat_id, 
                    f"{mention} {bq(random.choice(words))}", 
                    reply_to=reply.id, 
                    parse_mode='html'
                )
            
            # Bot အလှည့်ပြောင်းမယ် (Bot 1 ပြီးရင် Bot 2)
            bot_index = (bot_index + 1) % len(bots)
            
            send_count += 1
            if send_count >= 8: 
                await asyncio.sleep(1)
                send_count = 0 
            else: 
                # Bot ၂ ကောင်ခွဲပို့တာမို့ delay ကို နည်းနည်းလျှော့ထားပေးပါတယ်
                await asyncio.sleep(0.4) 
        except Exception:
            # Error တက်ရင် (ဥပမာ Flood မိရင်) အဲ့ဒီ chat အတွက် bully ရပ်မယ်
            bot_bully_tasks[chat_id] = False
            break

# ==========================================
# 🛡️ [6] /sb Stop Bully
# ==========================================

async def stop_bot_bully(event):
    if not is_allowed(event.sender_id): return
    try: await event.delete() # Command ကို ဖျက်တယ်
    except: pass
    bot_bully_tasks[event.chat_id] = False
    await event.respond(bq("အခုနားဆိုလို့နားလိုက်မယ်၊စောက်ချိုးမပြေရင်ထပ်ဆဲပေးမယ်"), parse_mode='html')

# ==========================================
# 🚀 START SYSTEM
# ==========================================

async def start_system():
    threading.Thread(target=run_flask, daemon=True).start()

    for i, bot in enumerate(bots):
        bot.add_event_handler(bot_bully, events.NewMessage(pattern=r'^/b(?:@\w+)?$'))
        bot.add_event_handler(stop_bot_bully, events.NewMessage(pattern=r'^/sb(?:@\w+)?$'))
        await bot.start(bot_token=TOKENS[i])

    print("✅ BoDx Multi-Bot Stealth System Online!")
    await asyncio.gather(*(bot.run_until_disconnected() for bot in bots))

if __name__ == "__main__":
    asyncio.run(start_system())

