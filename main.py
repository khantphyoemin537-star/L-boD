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
# 🩸 1. DATABASE ADDING (Reply Method)
# ==========================================
@bot.on(events.NewMessage(chats=LOG_CHAT_ID, pattern=r'^/fuck (.*)'))
async def add_to_db_reply(event):
    # Owner စစ်ဆေးခြင်း
    if event.sender_id != OWNER_ID:
        return

    # Reply ထောက်ထားခြင်း ရှိမရှိ စစ်ဆေးခြင်း
    if not event.is_reply:
        return await event.reply("⚠️ သိမ်းချင်တဲ့ ပုံကို Reply ထောက်ပြီး `/fuck Name | Rarity` လို့ ရိုက်ပါဗျ။")

    reply_msg = await event.get_reply_message()
    
    # Reply ထောက်ထားတဲ့ message မှာ ပုံပါမပါ စစ်ဆေးခြင်း
    if not reply_msg.photo:
        return await event.reply("❌ ပုံကိုပဲ Reply ထောက်ပေးပါဟ။")

    try:
        # စာသားခွဲထုတ်ခြင်း (ဥပမာ- Eimi Fukada | Mythic)
        input_text = event.pattern_match.group(1).strip()
        data = input_text.split('|')
        name = data[0].strip()
        
        # Rarity မပါရင် Auto ရွေးခိုင်းမယ်
        rarity = data[1].strip() if len(data) > 1 else get_random_rarity()
        base_id = generate_id("BASE")
        
        # DATABASE ထဲသိမ်းမယ် (Object မဟုတ်ဘဲ ID တွေကိုပဲ သိမ်းတာ)
        actress_col.insert_one({
            "base_id": base_id,
            "name": name.lower(),
            "display_name": name,
            "rarity": rarity,
            "message_id": reply_msg.id, # ပုံရဲ့ ID ကိုပဲသိမ်းတယ်
            "chat_id": event.chat_id,    # ဘယ် Chat ကလဲဆိုတာ သိမ်းတယ်
            "timestamp": datetime.now()
        })
        
        await event.reply(f"✅ **Saved Successfully!**\n🎬 Name: `{name}`\n💎 Rarity: `{rarity}`\n🔖 ID: `{base_id}`\n\n(အခုဆိုရင် Error လုံးဝမတက်တော့ပါဘူးဗျာ)")
        
    except Exception as e:
        await event.reply(f"❌ Error: `{str(e)}`")
# ==========================================
# 🍷 2. SPAWN SYSTEM (/waifu)
# ==========================================
@bot.on(events.NewMessage(pattern=r'^/waifu'))
async def spawn_waifu(event):
    if event.is_private: return
    
    # လက်ရှိ Chat မှာ ပေါ်နေတာ ရှိမရှိ အရင်စစ်မယ်
    existing = spawn_col.find_one({"chat_id": event.chat_id, "active": True})
    if existing:
        return await event.reply(f"⚠️ `{existing['display_name']}` ပေါ်နေပါသေးတယ်။\nCatch: `/catch {existing['display_name']}`")

    # DB ထဲက ကျပန်း တစ်ယောက်ကို ယူမယ်
    all_data = list(actress_col.find())
    if not all_data: 
        return await event.reply("Database ထဲမှာ ဘာမှမရှိသေးပါဘူး။ အရင် /fuck နဲ့ သိမ်းပေးပါ။")
    
    target = random.choice(all_data)
    
    # Spawn မှတ်တမ်းသွင်းမယ်
    spawn_col.update_one(
        {"chat_id": event.chat_id},
        {"$set": {
            "base_id": target["base_id"], 
            "name": target["name"], 
            "display_name": target["display_name"], 
            "active": True
        }},
        upsert=True
    )

    caption = (f"🩸 **A new actress has appeared!**\n\n"
               f"Copy to catch:\n`/catch {target['display_name']}`")
    
    # သိမ်းထားတဲ့ message_id ကို သုံးပြီး Log Chat ဆီကနေ ပုံကို ဆွဲပြမယ်
    await bot.send_file(
        event.chat_id, 
        file=target['message_id'], 
        caption=caption, 
        reply_to=event.id
    )
# ==========================================
# 🖤 3. CATCH SYSTEM (Harem ထဲသို့ သိမ်းဆည်းခြင်း)
# ==========================================
@bot.on(events.NewMessage(pattern=r'^/catch (.*)'))
async def catch_waifu(event):
    if event.is_private: return
    
    guess = event.pattern_match.group(1).strip().lower()
    
    # Active ဖြစ်နေတဲ့ spawn ကို ပိတ်မယ်
    spawn_data = spawn_col.find_one_and_update(
        {"chat_id": event.chat_id, "active": True},
        {"$set": {"active": False}}
    )
    
    if not spawn_data:
        return await event.reply("❌ နောက်ကျသွားပါပြီ! သူ ထွက်သွားပါပြီ။")

    if guess == spawn_data["name"]:
        target = actress_col.find_one({"base_id": spawn_data["base_id"]})
        card_id = generate_id("CARD")
        
        # ဒေတာသွင်းတဲ့နေရာမှာ 'users' collection ထဲ သေချာသွင်းပါ
        users_col.insert_one({
            "user_id": event.sender_id,
            "card_id": card_id,
            "base_id": target["base_id"],
            "display_name": target["display_name"],
            "rarity": target["rarity"],
            "message_id": target["message_id"], # /fuck နဲ့သိမ်းထားတဲ့ message_id
            "caught_at": datetime.now()
        })
        
        await event.reply(f"🏆 ဂုဏ်ယူပါတယ်!\n**{target['display_name']}** ကို ဖမ်းမိသွားပါပြီ။\nအခု `/harem` ရိုက်ပြီး ပြန်ကြည့်လို့ရပါပြီ။")
    else:
        spawn_col.update_one({"chat_id": event.chat_id}, {"$set": {"active": True}})
        await event.reply("❌ နာမည်မှားနေပါတယ်။")

# ==========================================
# 👑 4. HAREM SYSTEM (စစ်ဆေးပြီးသား Version)
# ==========================================
@bot.on(events.NewMessage(pattern=r'^/harem'))
async def view_harem(event):
    # Reply ထောက်ထားရင် အဲ့ဒီလူဟာကိုပြမယ်
    user_id = (await event.get_reply_message()).sender_id if event.is_reply else event.sender_id
    
    # MongoDB မှာ ဒီ user_id နဲ့ data ရှိမရှိ ရှာမယ်
    cards = list(users_col.find({"user_id": user_id}))
    
    if not cards:
        return await event.reply("🦇 မင်းရဲ့ Harem ထဲမှာ ဘယ်သူမှ မရှိသေးပါဘူး။ အရင်ဖမ်းပါဦး။")

    card = cards[0]
    caption = (f"🖤 **Harem Collection** (1/{len(cards)})\n\n"
               f"🎬 Name: **{card['display_name']}**\n"
               f"💎 Rarity: {card['rarity']}\n"
               f"🔖 Card ID: `{card['card_id']}`")
    
    buttons = [[Button.inline("⬅️ Prev", data=f"h_{user_id}_p_0"), 
                Button.inline("Next ➡️", data=f"h_{user_id}_n_0")]]
    
    # ပုံကို message_id သုံးပြီး ပြန်ပို့မယ်
    await bot.send_file(event.chat_id, file=card['message_id'], caption=caption, buttons=buttons)

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
# Group အလိုက် message counter ကို သိမ်းဖို့ dictionary
msg_counters = {}

@bot.on(events.NewMessage)
async def auto_spawn_handler(event):
    if event.is_private: return
    chat_id = event.chat_id

    # စာရိုက်တဲ့သူက Bot ဆိုရင် count မလုပ်ဘူး
    if event.sender_id == (await bot.get_me()).id:
        return

    # Counter မရှိသေးရင် တည်ဆောက်မယ်
    if chat_id not in msg_counters:
        msg_counters[chat_id] = 0
    
    # စာတစ်ကြောင်းတိုးတိုင်း counter တိုးမယ်
    msg_counters[chat_id] += 1

    # စာ ၁၀ ကြောင်းပြည့်မပြည့် စစ်မယ်
    if msg_counters[chat_id] >= 10:
        # Spawn လုပ်ဖို့ ရှိမရှိ စစ်ဆေးခြင်း
        existing = spawn_col.find_one({"chat_id": chat_id, "active": True})
        if not existing:
            # Database ထဲက ကျပန်း တစ်ယောက် ယူမယ်
            all_data = list(actress_col.find())
            if all_data:
                target = random.choice(all_data)
                
                # Spawn မှတ်တမ်းသွင်းမယ်
                spawn_col.update_one(
                    {"chat_id": chat_id},
                    {"$set": {
                        "base_id": target["base_id"], 
                        "name": target["name"], 
                        "display_name": target["display_name"], 
                        "active": True
                    }},
                    upsert=True
                )

                caption = (f"🩸 **A new actress has appeared!**\n\n"
                           f"Copy to catch:\n`/catch {target['display_name']}`")
                
                # ပုံပို့မယ်
                await bot.send_file(chat_id, file=target['message_id'], caption=caption)
                
                # Counter ကို ပြန် reset ချမယ်
                msg_counters[chat_id] = 0

# ==========================================
# 🚀 LAUNCH
# ==========================================
if __name__ == "__main__":
    keep_alive()
    print("🦇 Besites Catcher System is Online!")
    bot.run_until_disconnected()
