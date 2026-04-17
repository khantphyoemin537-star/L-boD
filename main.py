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
# 🛡️ STEALTH MULTI-BOT BULLY (/b)
# ==========================================

async def bot_bully(event):
    if not is_allowed(event.sender_id): return
    
    reply = await event.get_reply_message()
    if not reply: return 

    chat_id = event.chat_id
    bot_bully_tasks[chat_id] = True
    target = await reply.get_sender()
    mention = f"<a href='tg://user?id={target.id}'>{escape_html(target.first_name)}</a>"
    
    # DB ကနေ ဆဲစာဆွဲထုတ်
    all_data = list(filters_col.find({"type": "text"}))
    words = [w.get("content") for w in all_data if w.get("content")]
    
    if not words: 
        words = ["စောက်ရူး", "ခွေးကောင်", "ငလူးမသား"]

    # --- Notification Message ကို ဖြုတ်လိုက်သည် (Stealth Mode) ---

    bot_index = 0
    while bot_bully_tasks.get(chat_id):
        try:
            current_bot = bots[bot_index]
            if current_bot.is_connected():
                await current_bot.send_message(
                    chat_id, 
                    f"{mention} {bq(random.choice(words))}", 
                    reply_to=reply.id, 
                    parse_mode='html'
                )
            
            bot_index = (bot_index + 1) % len(bots)
            await asyncio.sleep(0.2) 
            
        except Exception as e:
            if "FloodWaitError" in str(e):
                bot_index = (bot_index + 1) % len(bots)
                await asyncio.sleep(1)
            else:
                await asyncio.sleep(0.5)
            continue

async def stop_bully(event):
    if not is_allowed(event.sender_id): return
    bot_bully_tasks[event.chat_id] = False
    await event.respond(bq("ရပ်လိုက်ပါပြီ Chief!"))

# ==========================================
# 🚀 START
# ==========================================
async def start_system():
    threading.Thread(target=run_flask, daemon=True).start()

    for i, bot in enumerate(bots):
        bot.add_event_handler(bot_bully, events.NewMessage(pattern=r'^/b(?:@\w+)?$'))
        bot.add_event_handler(stop_bully, events.NewMessage(pattern=r'^/sb(?:@\w+)?$'))
        await bot.start(bot_token=TOKENS[i])

    print("✅ Stealth Bully System Active!")
    await asyncio.gather(*(bot.run_until_disconnected() for bot in bots))

if __name__ == "__main__":
    asyncio.run(start_system())
