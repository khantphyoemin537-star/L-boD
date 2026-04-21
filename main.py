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

bots = [TelegramClient(f'session_bot_{i}', APP_ID, APP_HASH) for i in range(len(TOKENS))]
main_bot = bots[0]

bot_compliment_tasks = {}
learning_status = {} # စကားမှတ်ခြင်း (On/Off)
talking_status = {}  # ဝင်ပြောခြင်း (On/Off)
message_counts = {}  # Chat အလိုက် Message အရေအတွက် မှတ်ရန်
bot_ids = []
bot_names = [] # Bot တွေရဲ့ နာမည်တွေ သိမ်းရန်

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
    if not is_allowed(event.sender_id): return
    input_str = event.pattern_match.group(1).split(None, 1)
    keyword = input_str[0].lower()
    reply = await event.get_reply_message()

    if reply:
        # Sticker, Photo, Video တွေကို စစ်မယ်
        if reply.media:
            m_type = "sticker" if reply.sticker else "photo" if reply.photo else "video" if reply.video else "media"
            # Media object ကို MongoDB မှာ သိမ်းလို့ရအောင် တိုက်ရိုက်ထည့်မယ်
            # အကယ်၍ error တက်ရင် message reference ကို သုံးရပါမယ်
            try:
                db["custom_filters"].update_one(
                    {"keyword": keyword}, 
                    {"$set": {"content": reply.media, "type": m_type, "chat_id": "global"}}, 
                    upsert=True
                )
                await event.reply(f"အိုကေ! '{keyword}' ကို {m_type} Filter အဖြစ် မှတ်လိုက်ပြီ ✅")
            except Exception as e:
                await event.reply(f"Error: MongoDB က ဒီ Media ကို သိမ်းမရနေဘူး၊စာသားပဲ စမ်းကြည့်ပါ။")
    elif len(input_str) > 1:
        db["custom_filters"].update_one(
            {"keyword": keyword}, 
            {"$set": {"content": input_str[1], "type": "text", "chat_id": "global"}}, 
            upsert=True
        )
        await event.reply(f"အိုကေ! '{keyword}' ဆိုရင် ပြန်ဖြေဖို့ မှတ်လိုက်ပြီ ✅")


# ==========================================
# 🎛️ [2] LEARNING & TALKING SETTINGS
# ==========================================
@main_bot.on(events.NewMessage(pattern=r'^မှတ်\s+(.*)'))
async def register_talker(event):
    if event.sender_id != OWNER_ID: return
    reply = await event.get_reply_message()
    if not reply: return await event.respond(bq("User တစ်ယောက်ကို Reply ထောက်ပြီးမှ 'မှတ် [nickname]' လို့ သုံးပါ Chief!"))
    nickname = event.pattern_match.group(1).strip()
    talker_col.update_one({"user_id": reply.sender_id}, {"$set": {"nickname": nickname}}, upsert=True)
    await event.reply(bq(f"ဒီ User ရဲ့စကားတွေကို '{nickname}' နာမည်နဲ့ မှတ်သားဖို့ စာရင်းသွင်းလိုက်ပါပြီ။"), parse_mode='html')

# --- Learning Control ---
@main_bot.on(events.NewMessage(pattern=r'^/fon$'))
async def turn_on_learning(event):
    if not await is_admin(main_bot, event.chat_id, event.sender_id): return
    learning_status[event.chat_id] = True
    await event.reply(bq("Database အတွင်းသို့ စကားများမှတ်သားခြင်း စနစ် ဖွင့်ပါပြီ။"), parse_mode='html')

@main_bot.on(events.NewMessage(pattern=r'^/foff$'))
async def turn_off_learning(event):
    if not await is_admin(main_bot, event.chat_id, event.sender_id): return
    learning_status[event.chat_id] = False
    await event.reply(bq("စကားများမှတ်သားခြင်း စနစ် ပိတ်ပါပြီ။"), parse_mode='html')

# --- Talking Control ---
@main_bot.on(events.NewMessage(pattern=r'^/fonn$'))
async def turn_on_talking(event):
    if not await is_admin(main_bot, event.chat_id, event.sender_id): return
    talking_status[event.chat_id] = True
    message_counts[event.chat_id] = 0 # reset counter
    await event.reply(bq("ဟုတ် ငါတို့လည်းပျင်းလို့ စကားဝင်ပြောမယ်ကွာ "), parse_mode='html')

@main_bot.on(events.NewMessage(pattern=r'^/fonnoff$'))
async def turn_off_talking(event):
    if not await is_admin(main_bot, event.chat_id, event.sender_id): return
    talking_status[event.chat_id] = False
    await event.reply(bq("ငါတို့စကားပြောတော့ဘူး နားပြီ "), parse_mode='html')

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
    await event.respond(bq("ဆဲလို့ဝပြီအိပ်အုံးမယ်အစ်ကို"), parse_mode='html')

# ==========================================
# 🎯 [4] GENERAL WATCHER (Learning, Defense, Auto-Talk)
# ==========================================
@main_bot.on(events.NewMessage())
async def general_watcher(event):
    if event.is_private or not event.text: return
    if event.sender_id in bot_ids: return # Bot အချင်းချင်း ရှောင်ရန်

    text = event.text.strip()
    if text.startswith(('/', '.', 'မှတ်')): return

    chat_id = event.chat_id

    # --- A. Bot Reply Defense (၁ ကောင်တည်းကနေ ၄ ကောင်ကိုယ်စား ပြန်ဖြေမည်) ---
    reply = await event.get_reply_message()
    if reply and reply.sender_id in bot_ids:
        # Bot နာမည်အားလုံးကို ပေါင်းပြီး string ထုတ်မယ်
        names_str = ", ".join(bot_names)
        defense_msg = f"ဟာငါက botဆိုပေမယ့် စကားဝင်ပြောချင်လို့သာပြောနေတာ မင်းတို့ငါ့ကို စာထောက်နေလည်းငါဘာမှမသိဘူး၊ Morgan ပြောဆိုလို့ {names_str} တို့က ပြောနေကြ တာပါဗျာ"
        sender_bot = random.choice(bots) # တစ်ကောင်ကို random ရွေးပြီး ပို့ခိုင်းမယ်
        try:
            await sender_bot.send_message(chat_id, defense_msg, reply_to=event.id)
        except: pass
        return 

        # --- Custom Filter System (စာသားရော Media ပါ အလုပ်လုပ်မည့်အပိုင်း) ---
    all_filters = db["custom_filters"].find()
    for f in all_filters:
        if f["keyword"] in text.lower():
            try:
                # Type ကို ကြည့်ပြီး ခွဲပို့မယ်
                if f.get("type") == "text":
                    await event.reply(f["content"])
                else:
                    # Sticker, Photo, Video တွေဆိုရင် file= နဲ့ ပို့ရပါတယ်
                    await event.reply(file=f["content"])
            except Exception as e:
                print(f"Filter Send Error: {e}")
            break

    

    # --- C. Message Learning ( /fon ထားမှ မှတ်မည် ) ---
    if learning_status.get(chat_id, False):
        talker = talker_col.find_one({"user_id": event.sender_id})
        if talker and len(text) > 1:
            talk_col.insert_one({"text": text, "nickname": talker["nickname"]})

    # --- D. Auto-Talk per 10 Messages ( /fonn ထားမှ ပြောမည် ) ---
    if talking_status.get(chat_id, False):
        message_counts[chat_id] = message_counts.get(chat_id, 0) + 1
        
        # ၁၀ ကြောင်းပြည့်ရင် ဝင်ပြောမယ်
                if message_counts[chat_id] >= 10:
            message_counts[chat_id] = 0 # Count ပြန်စမယ်
            saved_talks = list(talk_col.find())
            if saved_talks:
                chosen = random.choice(saved_talks)
                
                # ပုံနာမည်နဲ့ formatting အားလုံးကို ဖြုတ်ပြီး text တစ်ခုတည်းကိုပဲ ယူမယ်
                msg_to_send = chosen['text']
                
                talk_bot = random.choice(bots) 
                try:
                    # parse_mode မလိုတော့တဲ့အတွက် ဖြုတ်ထားပါတယ်
                    await talk_bot.send_message(chat_id, msg_to_send)
                except: pass

# ==========================================
# 🚀 START SYSTEM
# ==========================================
async def start_system():
    threading.Thread(target=run_flask, daemon=True).start()

    print("Starting bots and fetching IDs & Names...")
    for i, bot in enumerate(bots):
        await bot.start(bot_token=TOKENS[i])
        me = await bot.get_me()
        bot_ids.append(me.id)
        bot_names.append(me.first_name) # Bot နာမည်တွေကိုပါ သိမ်းထားမယ် (Defense နေရာမှာ သုံးဖို့)

    print("✅ BoDx Sovereign System Online (10 Messages Trigger Configured)!")
    await asyncio.gather(*(bot.run_until_disconnected() for bot in bots))

if __name__ == "__main__":
    asyncio.run(start_system())

