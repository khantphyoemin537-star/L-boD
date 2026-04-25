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
# ⚙️ RENDER KEEP ALIVE (Flask Setup)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Besites Catcher Bot is Running"

def run():
    app.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ==========================================
# ⚙️ CONFIGURATIONS
# ==========================================
API_ID = 37675502
API_HASH = "45955dc059f23ca5bfa3dcaff9c0f032"
BOT_TOKEN = "8738081667:AAGr7HkSxO6nC_QhPJJElKR2VKABTEDfNEo"
OWNER_ID = 6015356597
LOG_CHAT_ID = -1003933136412

MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0&tlsAllowInvalidCertificates=true"
db_client = MongoClient(MONGO_URI)
db = db_client["Brotherhood_of_Dexter_DB"]

# Collections
actress_col = db["actresses"] 
users_col = db["users"] 
spawn_col = db["spawns"] 

bot = TelegramClient('catcher_bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# ==========================================
# 🛠 HELPERS
# ==========================================
def generate_id(prefix, length=6):
    chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
    return f"{prefix}-{chars}"

def get_random_rarity():
    ranks = ["Common", "Rare", "Epic", "Legendary", "Mythic"]
    weights = [55, 25, 12, 6, 2]
    return random.choices(ranks, weights=weights)[0]

# ==========================================
# 🩸 1. DATABASE ADDING (Owner Only - Log Group)
# ==========================================
@bot.on(events.NewMessage(chats=LOG_CHAT_ID))
async def add_to_db(event):
    if event.sender_id != OWNER_ID or not event.photo:
        return
    
    try:
        text = event.text or ""
        data = text.split('|')
        name = data[0].strip()
        
        # Rarity: Manual or Auto
        rarity = data[1].strip() if len(data) > 1 else get_random_rarity()
        
        base_id = generate_id("BASE")
        
        actress_col.insert_one({
            "base_id": base_id,
            "name": name.lower(),
            "display_name": name,
            "rarity": rarity,
            "file_id": event.message.media,
            "timestamp": datetime.now()
        })
        
        await event.reply(f"✅ **Added to DB**\n🎬 Name: `{name}`\n💎 Rarity: `{rarity}`\n🔖 Base ID: `{base_id}`")
    except Exception as e:
        await event.reply(f"❌ Error: {e}")

# ==========================================
# 🍷 2. SPAWN SYSTEM (/waifu)
# ==========================================
@bot.on(events.NewMessage(pattern=r'^/waifu'))
async def spawn_waifu(event):
    if event.is_private: return
    
    # Check if someone is already spawned
    existing = spawn_col.find_one({"chat_id": event.chat_id, "active": True})
    if existing:
        return await event.reply(f"⚠️ `{existing['display_name']}` ပေါ်နေပါသေးတယ်။\nCatch: `/catch {existing['display_name']}`")

    all_data = list(actress_col.find())
    if not all_data: return await event.reply("Database ထဲမှာ ဘာမှမရှိသေးပါဘူး။")
    
    target = random.choice(all_data)
    spawn_col.update_one(
        {"chat_id": event.chat_id},
        {"$set": {"base_id": target["base_id"], "name": target["name"], "display_name": target["display_name"], "active": True}},
        upsert=True
    )

    caption = (f"🩸 **A new actress has appeared!**\n\n"
               f"Copy to catch:\n`/catch {target['display_name']}`")
    await bot.send_file(event.chat_id, file=target['file_id'], caption=caption)

# ==========================================
# 🖤 3. CATCH SYSTEM (Atomic - First Win)
# ==========================================
@bot.on(events.NewMessage(pattern=r'^/catch (.*)'))
async def catch_waifu(event):
    if event.is_private: return
    
    guess = event.pattern_match.group(1).strip().lower()
    
    # Race condition ကာကွယ်ရန် find_one_and_update သုံးသည်
    spawn_data = spawn_col.find_one_and_update(
        {"chat_id": event.chat_id, "active": True},
        {"$set": {"active": False}}
    )
    
    if not spawn_data:
        return await event.reply("❌ နောက်ကျသွားပါပြီ! တစ်ယောက်ယောက် ဖမ်းသွားပါပြီ။")

    if guess == spawn_data["name"]:
        target = actress_col.find_one({"base_id": spawn_data["base_id"]})
        card_id = generate_id("CARD")
        
        users_col.insert_one({
            "user_id": event.sender_id,
            "card_id": card_id,
            "base_id": target["base_id"],
            "display_name": target["display_name"],
            "rarity": target["rarity"],
            "file_id": target["file_id"],
            "caught_at": datetime.now()
        })
        
        await event.reply(f"🏆 ဂုဏ်ယူပါတယ်!\n**{target['display_name']}** ({target['rarity']}) ကို ဖမ်းမိသွားပါပြီ။\n🔖 ID: `{card_id}`")
    else:
        # နာမည်မှားရင် ပြန်ဖွင့်ပေးသည်
        spawn_col.update_one({"chat_id": event.chat_id}, {"$set": {"active": True}})
        await event.reply("❌ နာမည်မှားနေပါတယ်။ ပြန်ကြိုးစားကြည့်ပါ။")

# ==========================================
# 👑 4. HAREM SYSTEM (Public Pagination)
# ==========================================
@bot.on(events.NewMessage(pattern=r'^/harem'))
async def view_harem(event):
    user_id = (await event.get_reply_message()).sender_id if event.is_reply else event.sender_id
    user_info = await bot.get_entity(user_id)
    
    cards = list(users_col.find({"user_id": user_id}))
    if not cards:
        return await event.reply(f"🦇 {user_info.first_name} မှာ စုဆောင်းထားတာ မရှိသေးဘူး။")

    card = cards[0]
    caption = (f"🖤 **{user_info.first_name}'s Harem** (1/{len(cards)})\n\n"
               f"🎬 Name: **{card['display_name']}**\n"
               f"💎 Rarity: {card['rarity']}\n"
               f"🔖 Card ID: `{card['card_id']}`")
    
    buttons = [[Button.inline("⬅️ Prev", data=f"h_{user_id}_p_0"), 
                Button.inline("Next ➡️", data=f"h_{user_id}_n_0")]]
    await bot.send_file(event.chat_id, file=card['file_id'], caption=caption, buttons=buttons)

@bot.on(events.CallbackQuery(pattern=re.compile(rb"h_(\d+)_(n|p)_(\d+)")))
async def harem_nav(event):
    target_id = int(event.data_match.group(1).decode())
    action = event.data_match.group(2).decode()
    idx = int(event.data_match.group(3).decode())
    
    cards = list(users_col.find({"user_id": target_id}))
    new_idx = (idx + 1) % len(cards) if action == "n" else (idx - 1) % len(cards)
    
    card = cards[new_idx]
    user_info = await bot.get_entity(target_id)
    caption = (f"🖤 **{user_info.first_name}'s Harem** ({new_idx + 1}/{len(cards)})\n\n"
               f"🎬 Name: **{card['display_name']}**\n"
               f"💎 Rarity: {card['rarity']}\n"
               f"🔖 Card ID: `{card['card_id']}`")
    
    buttons = [[Button.inline("⬅️ Prev", data=f"h_{target_id}_p_{new_idx}"), 
                Button.inline("Next ➡️", data=f"h_{target_id}_n_{new_idx}")]]
    await event.edit(caption, file=card['file_id'], buttons=buttons)

# ==========================================
# 🎁 5. GIFT & TRADE
# ==========================================
@bot.on(events.NewMessage(pattern=r'^/gift (.*)'))
async def gift_waifu(event):
    if not event.is_reply: return await event.reply("Reply ထောက်ပြီးသုံးပါ။")
    
    card_id = event.pattern_match.group(1).strip()
    receiver_id = (await event.get_reply_message()).sender_id
    
    res = users_col.update_one({"user_id": event.sender_id, "card_id": card_id}, {"$set": {"user_id": receiver_id}})
    if res.modified_count > 0:
        await event.reply(f"🎁 Card `{card_id}` ကို လက်ဆောင်ပေးလိုက်ပါပြီ!")
    else:
        await event.reply("❌ မင်းဆီမှာ ဒီ Card ID မရှိပါဘူး။")

@bot.on(events.NewMessage(pattern=r'^/trade (.*)'))
async def trade_req(event):
    if not event.is_reply: return await event.reply("လဲမယ့်သူကို Reply ထောက်ပါ။")
    card_id = event.pattern_match.group(1).strip()
    
    # ရိုးရှင်းသော Trade: ကိုယ့်ကဒ်ကို ပြပြီး တစ်ဖက်လူက Accept လုပ်လျှင် ၎င်း၏ နောက်ဆုံးရကဒ်နှင့်လဲမည်
    buttons = [[Button.inline("🤝 Accept Trade", data=f"t_a_{event.sender_id}_{card_id}"),
                Button.inline("❌ Decline", data=b"t_d")]]
    await event.reply(f"🤝 **Trade Request!**\nCard `{card_id}` နဲ့ လဲလှယ်ချင်ပါသလား?", buttons=buttons)

@bot.on(events.CallbackQuery(pattern=re.compile(rb"t_a_(\d+)_(.*)")))
async def trade_confirm(event):
    sender_id = int(event.data_match.group(1).decode())
    s_card_id = event.data_match.group(2).decode()
    p_id = event.sender_id
    
    p_card = users_col.find_one({"user_id": p_id})
    if not p_card: return await event.answer("လဲစရာကဒ် မရှိသေးပါ။", alert=True)

    users_col.update_one({"card_id": s_card_id}, {"$set": {"user_id": p_id}})
    users_col.update_one({"card_id": p_card['card_id']}, {"$set": {"user_id": sender_id}})
    await event.edit(f"✅ Trade Success!\n`{s_card_id}` 🔄 `{p_card['card_id']}`")

# ==========================================
# 🚀 LAUNCH
# ==========================================
if __name__ == "__main__":
    keep_alive()
    print("🦇 Besites Catcher System is Online!")
    bot.run_until_disconnected()
