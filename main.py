import os
import re
import random
import string
import asyncio
from datetime import datetime
from telethon import TelegramClient, events, Button
from pymongo import MongoClient

# ==========================================
# ⚙️ CONFIGURATIONS
# ==========================================
API_ID = 1234567  # သင့်ရဲ့ API_ID
API_HASH = "your_api_hash" # သင့်ရဲ့ API_HASH
BOT_TOKEN = "8738081667:AAGr7HkSxO6nC_QhPJJElKR2VKABTEDfNEo"
OWNER_ID = 6015356597
LOG_CHAT_ID = -1003933136412

MONGO_URI = "Mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0&tlsAllowInvalidCertificates=true"
db_client = MongoClient(MONGO_URI)
db = db_client["Brotherhood_of_Dexter_DB"]

actress_col = db["actresses"] 
users_col = db["users"] 
spawn_col = db["spawns"] 
trade_col = db["trades"] # Trade စနစ်အတွက် collection အသစ်

bot = TelegramClient('catcher_bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# ==========================================
# 🛠 HELPERS
# ==========================================
def generate_unique_id(prefix="JAV"):
    chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"{prefix}-{chars}"

def get_random_rarity():
    ranks = ["Common", "Rare", "Epic", "Legendary", "Mythic"]
    weights = [50, 30, 12, 6, 2]
    return random.choices(ranks, weights=weights)[0]

# ==========================================
# 🩸 1. WAIFU / SPAWN SYSTEM (Copyable Catch Link ပါဝင်သည်)
# ==========================================
@bot.on(events.NewMessage(pattern=r'^/waifu'))
async def spawn_waifu(event):
    if event.is_private: return
    
    # လက်ရှိ Group မှာ ပေါ်နေတာ ရှိမရှိ စစ်ဆေးခြင်း
    existing = spawn_col.find_one({"chat_id": event.chat_id, "active": True})
    if existing:
        return await event.reply(f"⚠️ `{existing['display_name']}` က ပေါ်နေတုန်းပဲရှိပါသေးတယ်။\nCopy catch: `/catch {existing['display_name']}`")

    all_actresses = list(actress_col.find())
    if not all_actresses: return
    
    target = random.choice(all_actresses)
    spawn_col.update_one(
        {"chat_id": event.chat_id},
        {"$set": {"base_id": target["base_id"], "name": target["name"], "display_name": target["display_name"], "active": True}},
        upsert=True
    )

    caption = (f"🩸 **A new actress has appeared!**\n\n"
               f"Copy to catch:\n`/catch {target['display_name']}`")
    
    await bot.send_file(event.chat_id, file=target['file_id'], caption=caption)

# ==========================================
# 🖤 2. CATCH SYSTEM (ပထမဆုံးလူသာ ဖမ်းနိုင်သော စနစ်)
# ==========================================
@bot.on(events.NewMessage(pattern=r'^/catch (.*)'))
async def catch_character(event):
    if event.is_private: return
    
    chat_id = event.chat_id
    user_id = event.sender_id
    guess_name = event.pattern_match.group(1).strip().lower()

    # Active ဖြစ်နေသော spawn ကို ရှာပြီး တစ်ခါတည်း update လုပ်ခြင်း (Race Condition ကာကွယ်ရန်)
    spawn_data = spawn_col.find_one_and_update(
        {"chat_id": chat_id, "active": True},
        {"$set": {"active": False}}
    )
    
    if not spawn_data:
        return await event.reply("❌ နောက်ကျသွားပါပြီ! သူ ထွက်သွားပါပြီ သို့မဟုတ် တစ်ယောက်ယောက် ဖမ်းသွားပါပြီ။")

    if guess_name == spawn_data["name"]:
        target_actress = actress_col.find_one({"base_id": spawn_data["base_id"]})
        card_id = generate_unique_id("CARD")
        
        users_col.insert_one({
            "user_id": user_id, "card_id": card_id, "base_id": target_actress["base_id"],
            "display_name": target_actress["display_name"], "rarity": target_actress["rarity"],
            "file_id": target_actress["file_id"], "caught_date": datetime.now()
        })
        
        user_mention = f"[(User)](tg://user?id={user_id})"
        await event.reply(f"🏆 ဂုဏ်ယူပါတယ် {user_mention}!\n**{target_actress['display_name']}** ({target_actress['rarity']}) ကို ဖမ်းမိသွားပါပြီ။\n🔖 Card ID: `{card_id}`")
    else:
        # နာမည်မှားသွားရင် ပြန်ဖွင့်ပေးခြင်း
        spawn_col.update_one({"chat_id": chat_id}, {"$set": {"active": True}})
        await event.reply("❌ နာမည်မှားနေပါတယ်။ Copy ကူးပြီး ပြန်ကြိုးစားပါ။")

# ==========================================
# 🎁 3. GIFT SYSTEM (ကဒ် လက်ဆောင်ပေးခြင်း)
# ==========================================
@bot.on(events.NewMessage(pattern=r'^/gift (.*)'))
async def gift_card(event):
    if not event.is_reply:
        return await event.reply("⚠️ ကဒ်ပေးလိုတဲ့သူကို Reply ထောက်ပြီး သုံးပါ။\nUsage: `/gift [CardID]`")
    
    card_id = event.pattern_match.group(1).strip()
    sender_id = event.sender_id
    receiver_id = (await event.get_reply_message()).sender_id
    
    # ကဒ်ပိုင်ရှင် ဟုတ်မဟုတ် စစ်ဆေးခြင်း
    card = users_col.find_one({"user_id": sender_id, "card_id": card_id})
    if not card:
        return await event.reply("❌ ဒီ Card ID က မင်းဆီမှာ မရှိပါဘူး။")

    # ပိုင်ရှင်ပြောင်းခြင်း
    users_col.update_one({"card_id": card_id}, {"$set": {"user_id": receiver_id}})
    await event.reply(f"🎁 **{card['display_name']}** ကို အောင်မြင်စွာ လက်ဆောင်ပေးလိုက်ပါပြီ!")

# ==========================================
# 🤝 4. TRADE SYSTEM (ကဒ်လဲလှယ်ခြင်း)
# ==========================================
@bot.on(events.NewMessage(pattern=r'^/trade (.*)'))
async def trade_request(event):
    if not event.is_reply:
        return await event.reply("⚠️ Trade ချင်တဲ့သူကို Reply ထောက်ပါ။\nUsage: `/trade [CardID]`")
    
    my_card_id = event.pattern_match.group(1).strip()
    sender_id = event.sender_id
    partner_id = (await event.get_reply_message()).sender_id
    
    card = users_col.find_one({"user_id": sender_id, "card_id": my_card_id})
    if not card: return await event.reply("❌ မင်းဆီမှာ ဒီကဒ်မရှိပါဘူး။")

    buttons = [
        [Button.inline("🤝 Accept Trade", data=f"tr_acc_{sender_id}_{my_card_id}"),
         Button.inline("❌ Decline", data="tr_dec")]
    ]
    await event.reply(f"🤝 Trade Request!\n\n**{card['display_name']}** နဲ့ လဲလှယ်ချင်ပါသလား?", buttons=buttons)

@bot.on(events.CallbackQuery(pattern=re.compile(b"tr_acc_(\d+)_(.*)")))
async def accept_trade(event):
    sender_id = int(event.data_match.group(1).decode())
    my_card_id = event.data_match.group(2).decode()
    partner_id = event.sender_id
    
    # ဤနေရာတွင် Partner ထံမှ မည်သည့်ကဒ်နှင့် လဲမည်ကို ထပ်မံတောင်းခံရမည် (ရိုးရှင်းစေရန် Partner ၏ နောက်ဆုံးရကဒ်နှင့် လဲလိုက်မည်)
    partner_card = users_col.find_one({"user_id": partner_id})
    if not partner_card: return await event.answer("မင်းမှာ လဲစရာ ကဒ်မရှိသေးဘူး။", alert=True)

    # ကဒ်ချင်းလဲခြင်း
    users_col.update_one({"card_id": my_card_id}, {"$set": {"user_id": partner_id}})
    users_col.update_one({"card_id": partner_card['card_id']}, {"$set": {"user_id": sender_id}})
    
    await event.edit(f"✅ Trade အောင်မြင်သွားပါပြီ!\n{my_card_id} 🔄 {partner_card['card_id']}")

# ==========================================
# 👑 5. PUBLIC HAREM VIEW (အားလုံးကြည့်နိုင်သော Harem)
# ==========================================
@bot.on(events.NewMessage(pattern=r'^/harem'))
async def view_harem(event):
    # Reply ထောက်ထားရင် အဲ့ဒီလူရဲ့ harem ပြမယ်၊ မထောက်ထားရင် ကိုယ့်ဟာကိုယ်ပြမယ်
    user_id = (await event.get_reply_message()).sender_id if event.is_reply else event.sender_id
    user_data = await bot.get_entity(user_id)
    
    user_cards = list(users_col.find({"user_id": user_id}))
    if not user_cards:
        return await event.reply(f"🦇 {user_data.first_name} ရဲ့ Harem ထဲမှာ ဘယ်သူမှ မရှိသေးပါဘူး။")

    first_card = user_cards[0]
    caption = (f"🖤 **{user_data.first_name}'s Harem** (1/{len(user_cards)})\n\n"
               f"🎬 Name: **{first_card['display_name']}**\n"
               f"💎 Rarity: {first_card['rarity']}\n"
               f"🔖 Card ID: `{first_card['card_id']}`")
    
    # မည်သူမဆို နှိပ်ကြည့်နိုင်ရန် user_id ကို data ထဲမှာ ထည့်ထားသည်
    buttons = [[Button.inline("⬅️ Prev", data=f"h_{user_id}_p_0"), 
                Button.inline("Next ➡️", data=f"h_{user_id}_n_0")]]
    
    await bot.send_file(event.chat_id, file=first_card['file_id'], caption=caption, buttons=buttons)

@bot.on(events.CallbackQuery(pattern=re.compile(b"h_(\d+)_(n|p)_(\d+)")))
async def navigate_harem(event):
    target_user_id = int(event.data_match.group(1).decode())
    action = event.data_match.group(2).decode()
    current_idx = int(event.data_match.group(3).decode())
    
    user_cards = list(users_col.find({"user_id": target_user_id}))
    new_idx = (current_idx + 1) % len(user_cards) if action == "n" else (current_idx - 1) % len(user_cards)
    
    target_card = user_cards[new_idx]
    user_data = await bot.get_entity(target_user_id)
    caption = (f"🖤 **{user_data.first_name}'s Harem** ({new_idx + 1}/{len(user_cards)})\n\n"
               f"🎬 Name: **{target_card['display_name']}**\n"
               f"💎 Rarity: {target_card['rarity']}\n"
               f"🔖 Card ID: `{target_card['card_id']}`")
    
    buttons = [[Button.inline("⬅️ Prev", data=f"h_{target_user_id}_p_{new_idx}"), 
                Button.inline("Next ➡️", data=f"h_{target_user_id}_n_{new_idx}")]]
    
    await event.edit(caption, file=target_card['file_id'], buttons=buttons)

print("🦇 Besites Catcher System စတင်လည်ပတ်ပါပြီ...")
bot.run_until_disconnected()
