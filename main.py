import os
import re
import random
import string
import asyncio
from datetime import datetime
from telethon import TelegramClient, events, Button
from pymongo import MongoClient
from flask import Flask
from threading import Thread

# ==========================================
# ⚙️ RENDER KEEP ALIVE
# ==========================================
app = Flask(__name__)
@app.route('/')
def home(): return "Bot is Running"

def run(): app.run(host='0.0.0.0', port=10000)
def keep_alive(): Thread(target=run).start()

# ==========================================
# ⚙️ CONFIGURATIONS
# ==========================================
API_ID = 37675502
API_HASH = "45955dc059f23ca5bfa3dcaff9c0f032"
BOT_TOKEN = "87r7HkSxO6nC_QhPJJElKR2VKABTEDfNEo"
OWNER_ID = 6015356597
LOG_CHAT_ID = -1003933136412

MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0&tlsAllowInvalidCertificates=true"
db_client = MongoClient(MONGO_URI)
db = db_client["Brotherhood_of_Dexter_DB"]

actress_col = db["actresses"] 
users_col = db["users"] 
spawn_col = db["spawns"] 

bot = TelegramClient('catcher_bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
msg_counters = {}

def generate_id(prefix, length=6):
    chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
    return f"{prefix}-{chars}"

def get_random_rarity():
    ranks = ["Common", "Rare", "Epic", "Legendary", "Mythic"]
    weights = [55, 25, 12, 6, 2]
    return random.choices(ranks, weights=weights)[0]

# ==========================================
# 🩸 1. DATABASE ADDING
# ==========================================
@bot.on(events.NewMessage(chats=LOG_CHAT_ID, pattern=r'^/fuck (.*)'))
async def add_to_db(event):
    if event.sender_id != OWNER_ID or not event.is_reply: return
    reply_msg = await event.get_reply_message()
    if not reply_msg.photo: return
    try:
        data = event.pattern_match.group(1).split('|')
        name = data[0].strip()
        rarity = data[1].strip() if len(data) > 1 else get_random_rarity()
        base_id = generate_id("BASE")
        actress_col.insert_one({
            "base_id": base_id, "name": name.lower(), "display_name": name,
            "rarity": rarity, "message_id": reply_msg.id, "chat_id": event.chat_id
        })
        await event.reply(f"✅ Saved: `{name}` | `{rarity}`")
    except Exception as e: await event.reply(f"❌ Error: {e}")

# ==========================================
# 🍷 2. AUTO & MANUAL SPAWN
# ==========================================
async def spawn_logic(chat_id):
    existing = spawn_col.find_one({"chat_id": chat_id, "active": True})
    if existing: return
    all_data = list(actress_col.find())
    if not all_data: return
    target = random.choice(all_data)
    spawn_col.update_one({"chat_id": chat_id}, {"$set": {
        "base_id": target["base_id"], "name": target["name"], 
        "display_name": target["display_name"], "active": True
    }}, upsert=True)
    caption = f"🩸 **A new actress appeared!**\n\n`/catch {target['display_name']}`"
    await bot.send_file(chat_id, file=target['message_id'], caption=caption)

@bot.on(events.NewMessage(pattern=r'^/waifu'))
async def manual_spawn(event):
    if not event.is_private: await spawn_logic(event.chat_id)

@bot.on(events.NewMessage)
async def auto_spawn(event):
    if event.is_private or event.text.startswith('/'): return
    chat_id = event.chat_id
    msg_counters[chat_id] = msg_counters.get(chat_id, 0) + 1
    if msg_counters[chat_id] >= 10:
        await spawn_logic(chat_id)
        msg_counters[chat_id] = 0

# ==========================================
# 🖤 3. CATCH & 👑 4. HAREM
# ==========================================
@bot.on(events.NewMessage(pattern=r'^/catch (.*)'))
async def catch_waifu(event):
    guess = event.pattern_match.group(1).strip().lower()
    spawn_data = spawn_col.find_one_and_update({"chat_id": event.chat_id, "active": True}, {"$set": {"active": False}})
    if not spawn_data: return await event.reply("❌ Too late!")
    if guess == spawn_data["name"]:
        target = actress_col.find_one({"base_id": spawn_data["base_id"]})
        card_id = generate_id("CARD")
        users_col.insert_one({
            "user_id": event.sender_id, "card_id": card_id, "display_name": target["display_name"],
            "rarity": target["rarity"], "message_id": target["message_id"]
        })
        await event.reply(f"🏆 Caught **{target['display_name']}**!")
    else:
        spawn_col.update_one({"chat_id": event.chat_id}, {"$set": {"active": True}})

@bot.on(events.NewMessage(pattern=r'^/harem'))
async def view_harem(event):
    user_id = (await event.get_reply_message()).sender_id if event.is_reply else event.sender_id
    cards = list(users_col.find({"user_id": user_id}))
    if not cards: return await event.reply("🦇 Empty Harem.")
    card = cards[0]
    caption = f"🖤 **Harem** (1/{len(cards)})\n\n🎬 **{card['display_name']}**\n💎 {card['rarity']}\n🔖 `{card['card_id']}`"
    buttons = [[Button.inline("⬅️ Prev", data=f"h_{user_id}_p_0"), Button.inline("Next ➡️", data=f"h_{user_id}_n_0")]]
    await bot.send_file(event.chat_id, file=card['message_id'], caption=caption, buttons=buttons)
# ==========================================
# 🎁 5. GIFT SYSTEM
# ==========================================
@bot.on(events.NewMessage(pattern=r'^/gift (.*)'))
async def gift_waifu(event):
    # Reply ထောက်ထားခြင်း ရှိမရှိ စစ်မယ်
    if not event.is_reply:
        return await event.reply("⚠️ လက်ဆောင်ပေးချင်တဲ့သူကို Reply ထောက်ပြီး `/gift Card_ID` လို့ ရိုက်ပါဗျ။")
    
    card_id = event.pattern_match.group(1).strip().upper()
    sender_id = event.sender_id
    
    # Reply ထောက်ထားတဲ့သူရဲ့ ID ကို ယူမယ်
    reply_msg = await event.get_reply_message()
    receiver_id = reply_msg.sender_id

    # ကိုယ့် ID ကိုယ် ပြန်ပေးတာမျိုး မဖြစ်အောင် ကာကွယ်မယ်
    if sender_id == receiver_id:
        return await event.reply("❌ ကိုယ့်ဟာကိုယ် ပြန်ပေးလို့ မရဘူးဟ။")

    # Card ပိုင်ရှင် ဟုတ်မဟုတ် စစ်ပြီး User ID ကို Update လုပ်မယ်
    result = users_col.update_one(
        {"user_id": sender_id, "card_id": card_id},
        {"$set": {"user_id": receiver_id}}
    )

    if result.modified_count > 0:
        # လက်ခံရရှိသူရဲ့ နာမည်ကို ယူမယ်
        try:
            receiver = await bot.get_entity(receiver_id)
            receiver_name = receiver.first_name
        except:
            receiver_name = "သူ့"
            
        await event.reply(f"🎁 ဂုဏ်ယူပါတယ်! Card ID `{card_id}` ကို **{receiver_name}** ဆီသို့ အောင်မြင်စွာ လက်ဆောင်ပေးလိုက်ပါပြီ။")
    else:
        await event.reply(f"❌ မင်းဆီမှာ Card ID `{card_id}` မရှိပါဘူး။ ID မှန်မမှန် ပြန်စစ်ကြည့်ပါဦး။")

@bot.on(events.CallbackQuery(pattern=re.compile(rb"h_(\d+)_(n|p)_(\d+)")))
async def harem_nav(event):
    uid, act, idx = int(event.data_match.group(1)), event.data_match.group(2).decode(), int(event.data_match.group(3))
    cards = list(users_col.find({"user_id": uid}))
    new_idx = (idx + 1) % len(cards) if act == "n" else (idx - 1) % len(cards)
    card = cards[new_idx]
    caption = f"🖤 **Harem** ({new_idx+1}/{len(cards)})\n\n🎬 **{card['display_name']}**\n💎 {card['rarity']}\n🔖 `{card['card_id']}`"
    await event.edit(caption, file=card['message_id'], buttons=[[Button.inline("⬅️ Prev", data=f"h_{uid}_p_{new_idx}"), Button.inline("Next ➡️", data=f"h_{uid}_n_{new_idx}")]])

if __name__ == "__main__":
    keep_alive()
    print("🦇 Online!")
    bot.run_until_disconnected()

