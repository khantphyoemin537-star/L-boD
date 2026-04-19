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
    "8565944163:AAE5tew3A1a6GkOw69vMPYSgV2obyO-wPz4",
    "8704927120:AAFUIrQhFaly9yRkEhsD4Yu5FiIEfj1F7Oo",
    "7716597590:AAF4uR9g-cOBLssQcPfqe2ROIxnr3dd-PDQ"
]

# ==========================================
# 🗄️ DATABASE SETUP
# ==========================================
client_mongo = MongoClient(MONGO_URI)
db = client_mongo["telegram_bot"]
filters_col = db["filters"] 
allow_col = db["allowed_users"]
custom_filters_col = db["custom_filters"]

# Bot များကို List အဖြစ် တည်ဆောက်ခြင်း
bots = [TelegramClient(f'session_bot_{i}', APP_ID, APP_HASH) for i in range(len(TOKENS))]

# Main Bot (ပထမဆုံး Bot) ကို Command တွေ ဖမ်းဖို့ သတ်မှတ်မယ် (၄ ကောင်လုံး ပြိုင်မလုပ်အောင်လို့ပါ)
main_bot = bots[0]

bot_compliment_tasks = {}
chat_auto_reply_status = {} # Auto Reply ကို ဖွင့်/ပိတ် မှတ်ထားရန်

def bq(text): 
    return f"<blockquote><b>{escape_html(str(text))}</b></blockquote>"

def is_allowed(user_id):
    if user_id == OWNER_ID: return True
    return allow_col.find_one({"user_id": user_id}) is not None

async def is_admin(client, chat_id, user_id):
    if user_id == OWNER_ID: return True
    try:
        participant = await client.get_permissions(chat_id, user_id)
        return participant.is_admin or participant.is_creator
    except:
        return False

# ==========================================
# 🛡️ [1] ADD FILTER (/f)
# ==========================================
@main_bot.on(events.NewMessage(pattern=r'^[/.]f\s+(.*)'))
async def add_filter(event):
    if not await is_admin(main_bot, event.chat_id, event.sender_id): 
        return

    input_str = event.pattern_match.group(1).split(None, 1)
    keyword = input_str[0].lower()
    reply = await event.get_reply_message()

    if reply:
        media = reply.media if (reply.sticker or reply.photo or reply.video) else reply.text
        m_type = "sticker" if reply.sticker else "photo" if reply.photo else "video" if reply.video else "text"

        if media:
            custom_filters_col.update_one(
                {"keyword": keyword},
                {"$set": {"content": media, "type": m_type, "chat_id": "global"}}, 
                upsert=True
            )
            await event.reply(bq(f"အိုကေ! '{keyword}' ကို Filter မှတ်လိုက်ပြီ ✅"), parse_mode='html')
    
    elif len(input_str) > 1:
        custom_filters_col.update_one(
            {"keyword": keyword},
            {"$set": {"content": input_str[1], "type": "text", "chat_id": "global"}}, 
            upsert=True
        )
        await event.reply(bq(f"အိုကေ! '{keyword}' ဆိုရင် ပြန်ဖြေဖို့ မှတ်လိုက်ပြီ ✅"), parse_mode='html')

# ==========================================
# 🎛️ [2] FILTER ON/OFF (Admin Only)
# ==========================================
@main_bot.on(events.NewMessage(pattern=r'^/fon$'))
async def turn_on_filter(event):
    if not await is_admin(main_bot, event.chat_id, event.sender_id): return
    chat_auto_reply_status[event.chat_id] = True
    await event.reply(bq("ဟုတ် ငါတို့လည်းပျင်းလို့ စကားဝင်ပြောမယ်ကွာ"), parse_mode='html')

@main_bot.on(events.NewMessage(pattern=r'^/foff$'))
async def turn_off_filter(event):
    if not await is_admin(main_bot, event.chat_id, event.sender_id): return
    chat_auto_reply_status[event.chat_id] = False
    await event.reply(bq("ငါတို့စကားပြောတော့ဘူး နားပြီ"), parse_mode='html')

# ==========================================
# 🛡️ [3] MULTI-BOT COMPLIMENT LOOP
# ==========================================
@main_bot.on(events.NewMessage(pattern=r'^ချီးမွမ်း(?:@\w+)?$'))
async def bot_polite_tag(event):
    if not is_allowed(event.sender_id): return
    reply = await event.get_reply_message()
    if not reply: return await event.respond(bq("Reply ပြန်လိုက်ပါ"))

    try: await event.delete() 
    except: pass

    chat_id = event.chat_id
    t = await reply.get_sender()
    if not t or t.id == OWNER_ID: return

    bot_compliment_tasks[chat_id] = True
    mention = f"<a href='tg://user?id={t.id}'>{escape_html(t.first_name)}</a>"
    words = [w.get("text") for w in filters_col.find() if w.get("text")]
    if not words: words = ["ချစ်တယ်"] # Fallback

    bot_index = 0
    while bot_compliment_tasks.get(chat_id):
        try: 
            # Bot ၄ ကောင် တစ်ကောင်ပြီးတစ်ကောင် မြန်မြန်ပို့မယ်
            current_bot = bots[bot_index % len(bots)]
            if current_bot.is_connected():
                await current_bot.send_message(
                    chat_id, 
                    f"{mention} {bq(random.choice(words))}", 
                    reply_to=reply.id, 
                    parse_mode='html'
                )
            bot_index += 1
            await asyncio.sleep(0.5) # Flood မမိအောင် စက္ကန့်ဝက်ခြားသည်
        except Exception:
            break

@main_bot.on(events.NewMessage(pattern=r'^ခဏနား(?:@\w+)?$'))
async def stop_bot_polite_tag(event):
    if not is_allowed(event.sender_id): return
    try: await event.delete()
    except: pass
    bot_compliment_tasks[event.chat_id] = False
    await event.respond(bq("အိုကေ နားလိုက်ပြီ Chief!"), parse_mode='html')

# ==========================================
# 🎯 [4] NO-REPLY FILTER WATCHER
# ==========================================
@main_bot.on(events.NewMessage())
async def group_filter_watcher(event):
    if event.is_private or not event.text: return
    
    # /fon နဲ့ ဖွင့်ထားမှသာ အလုပ်လုပ်မည်
    if not chat_auto_reply_status.get(event.chat_id, False): return

    user_msg = event.text.lower().strip()
    all_filters = custom_filters_col.find() 
    
    for item in all_filters:
        keyword = item["keyword"].lower().strip()
        is_match = (user_msg == keyword) or (f" {keyword} " in f" {user_msg} ") or user_msg.startswith(f"{keyword} ") or user_msg.endswith(f" {keyword}")

        if is_match:
            content = item["content"]
            m_type = item["type"]
            try:
                # Random Bot တစ်ကောင်က Reply "မပြန်ဘဲ" တိုက်ရိုက်ဝင်ပို့မယ်
                sender_bot = random.choice(bots)
                if m_type == "text":
                    await sender_bot.send_message(event.chat_id, content) # No reply_to
                else:
                    await sender_bot.send_message(event.chat_id, file=content) # No reply_to
                break
            except Exception:
                pass

# ==========================================
# 🚀 START SYSTEM
# ==========================================
async def start_system():
    threading.Thread(target=run_flask, daemon=True).start()

    # Bot ၄ ကောင်လုံးကို Start မယ်
    for i, bot in enumerate(bots):
        await bot.start(bot_token=TOKENS[i])

    print("✅ BoDx Multi-Bot Stealth System Online with 4 Tokens!")
    await asyncio.gather(*(bot.run_until_disconnected() for bot in bots))

if __name__ == "__main__":
    asyncio.run(start_system())
