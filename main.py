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
talk_col = db["random_talk"]
talker_col = db["talker"]

# Bot များကို List အဖြစ် တည်ဆောက်ခြင်း
bots = [TelegramClient(f'session_bot_{i}', APP_ID, APP_HASH) for i in range(len(TOKENS))]
main_bot = bots[0]

bot_compliment_tasks = {}
learning_status = {} # မှတ်နေတာကို ဖွင့်/ပိတ် မှတ်ထားရန်
bot_ids = [] # Bot 4 ကောင်ရဲ့ ID တွေသိမ်းရန် (Reply Defense အတွက်)

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
    if not await is_admin(main_bot, event.chat_id, event.sender_id): return

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
# 🎛️ [2] LEARNING ON/OFF & REGISTER
# ==========================================
@main_bot.on(events.NewMessage(pattern=r'^မှတ်\s+(.*)'))
async def register_talker(event):
    if event.sender_id != OWNER_ID: return
    reply = await event.get_reply_message()
    if not reply: return await event.respond(bq("User တစ်ယောက်ကို Reply ထောက်ပြီးမှ 'မှတ် [nickname]' လို့ သုံးပါ Chief!"))
    
    nickname = event.pattern_match.group(1).strip()
    talker_col.update_one({"user_id": reply.sender_id}, {"$set": {"nickname": nickname}}, upsert=True)
    await event.reply(bq(f"ဒီ User ရဲ့စကားတွေကို '{nickname}' နာမည်နဲ့ မှတ်သားဖို့ စာရင်းသွင်းလိုက်ပါပြီ။"), parse_mode='html')

@main_bot.on(events.NewMessage(pattern=r'^/fon$'))
async def turn_on_learning(event):
    if not await is_admin(main_bot, event.chat_id, event.sender_id): return
    learning_status[event.chat_id] = True
    await event.reply(bq("ဟုတ် ငါတို့လည်းပျင်းလို့ စကားဝင်ပြောမယ်ကွာ (စကားမှတ်ခြင်း ဖွင့်ပါပြီ၊ ၃၀ စက္ကန့်ခြား တစ်ခါပြောပါမည်)"), parse_mode='html')

@main_bot.on(events.NewMessage(pattern=r'^/foff$'))
async def turn_off_learning(event):
    if not await is_admin(main_bot, event.chat_id, event.sender_id): return
    learning_status[event.chat_id] = False
    await event.reply(bq("ငါတို့စကားပြောတော့ဘူး နားပြီ (စကားမှတ်ခြင်း ပိတ်ပါပြီ)"), parse_mode='html')

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

    chat_id = event.event.chat_id
    t = await reply.get_sender()
    if not t or t.id == OWNER_ID: return

    bot_compliment_tasks[chat_id] = True
    mention = f"<a href='tg://user?id={t.id}'>{escape_html(t.first_name)}</a>"
    words = [w.get("text") for w in filters_col.find() if w.get("text")]
    if not words: words = ["ချစ်တယ်"] 

    bot_index = 0
    while bot_compliment_tasks.get(chat_id):
        try: 
            current_bot = bots[bot_index % len(bots)]
            if current_bot.is_connected():
                await current_bot.send_message(chat_id, f"{mention} {bq(random.choice(words))}", reply_to=reply.id, parse_mode='html')
            bot_index += 1
            await asyncio.sleep(0.5) 
        except: break

@main_bot.on(events.NewMessage(pattern=r'^ခဏနား(?:@\w+)?$'))
async def stop_bot_polite_tag(event):
    if not is_allowed(event.sender_id): return
    try: await event.delete()
    except: pass
    bot_compliment_tasks[event.chat_id] = False
    await event.respond(bq("အိုကေ နားလိုက်ပြီ Chief!"), parse_mode='html')

# ==========================================
# 🎯 [4] GENERAL WATCHER (Learning, Defense, Filters)
# ==========================================
@main_bot.on(events.NewMessage())
async def general_watcher(event):
    if event.is_private or not event.text: return
    if event.sender_id in bot_ids: return # Bot အချင်းချင်း ရှောင်ရန်

    text = event.text.strip()
    if text.startswith(('/', '.', 'မှတ်')): return

    # --- A. Bot Reply Defense ---
    reply = await event.get_reply_message()
    if reply and reply.sender_id in bot_ids:
        defense_msg = "ဟာငါက botဆိုပေမယ့် စကားဝင်ပြောချင်လို့သာပြောနေတာ မင်းတို့ငါ့ကို စာထောက်နေလည်းငါဘာမှမသိဘူး၊Morgan ပြောဆိုလို့ ပြောနေကြ တာပါဗျာ"
        for b in bots:
            try:
                await b.send_message(event.chat_id, defense_msg, reply_to=event.id)
                await asyncio.sleep(0.3)
            except: pass
        return # Defense အလုပ်လုပ်သွားရင် ကျန်တာဆက်မလုပ်တော့ပါ

    # --- B. Custom Filter Auto-Reply ---
    all_filters = custom_filters_col.find() 
    for item in all_filters:
        keyword = item["keyword"].lower().strip()
        user_msg_lower = text.lower()
        is_match = (user_msg_lower == keyword) or (f" {keyword} " in f" {user_msg_lower} ") or user_msg_lower.startswith(f"{keyword} ") or user_msg_lower.endswith(f" {keyword}")

        if is_match:
            try:
                sender_bot = random.choice(bots)
                if item["type"] == "text":
                    await sender_bot.send_message(event.chat_id, item["content"]) 
                else:
                    await sender_bot.send_message(event.chat_id, file=item["content"]) 
            except: pass
            break

    # --- C. Message Learning ---
    if learning_status.get(event.chat_id, False):
        talker = talker_col.find_one({"user_id": event.sender_id})
        if talker and len(text) > 1: # စာအရမ်းတိုရင် မမှတ်ပါ
            talk_col.insert_one({"text": text, "nickname": talker["nickname"]})

# ==========================================
# 🔄 [TIMER] 30 SEC RANDOM TALK LOOP
# ==========================================
async def random_talk_timer():
    await asyncio.sleep(20) # Bot တွေတက်လာအောင် ခဏစောင့်
    while True:
        # Group တိုင်းမှာ ဝင်ပြောဖို့ loop ပတ်မယ် (learning status ဖွင့်ထားတဲ့ chat တွေမှာပဲ ပြောမယ်)
        for chat_id, active in learning_status.items():
            if active:
                try:
                    saved_talks = list(talk_col.find())
                    if saved_talks:
                        chosen = random.choice(saved_talks)
                        # Nickname အပိုင်းကို blockquote လုပ်လိုက်တာပါ
                        msg_to_send = f"{chosen['text']}\n\n<blockquote><b>ပုံ/{escape_html(chosen['nickname'])}</b></blockquote>"
                        talk_bot = random.choice(bots)
                        await talk_bot.send_message(chat_id, msg_to_send, parse_mode='html')
                except: pass
        await asyncio.sleep(30) # ၃၀ စက္ကန့် တိတိခြားမယ်

# ==========================================
# 🚀 START SYSTEM
# ==========================================
async def start_system():
    threading.Thread(target=run_flask, daemon=True).start()

    print("Starting bots and fetching IDs...")
    for i, bot in enumerate(bots):
        await bot.start(bot_token=TOKENS[i])
        me = await bot.get_me()
        bot_ids.append(me.id)

    print("✅ BoDx AI Learning & Multi-Bot System Online!")
    
    # Timer ကို ဒီနေရာကနေ စတင် Run ပေးမှာပါ
    asyncio.create_task(random_talk_timer())
    
    await asyncio.gather(*(bot.run_until_disconnected() for bot in bots))

if __name__ == "__main__":
    asyncio.run(start_system())
