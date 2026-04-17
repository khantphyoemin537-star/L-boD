import io
import asyncio
import logging
import random
import os
import threading
import re
from datetime import datetime
import pytz
from flask import Flask
from pymongo import MongoClient
from telethon import TelegramClient, events, types
from telethon.tl.types import ChatAdminRights, ChannelParticipantsAdmins
from html import escape as escape_html
from PIL import Image, ImageDraw, ImageFont, ImageOps

# ==========================================
# 🌐 DNS FIX FOR MONGODB
# ==========================================
try:
    import dns.resolver
    dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
    dns.resolver.default_resolver.nameservers = ['8.8.8.8', '1.1.1.1']
except: pass

# ==========================================
# 🌐 FLASK KEEP-ALIVE
# ==========================================
app = Flask('')
@app.route('/')
def home(): return "BoDx Sovereign System Active!"

def run_flask(): 
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
OWNER_ID = 6015356597
MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0&tlsAllowInvalidCertificates=true"
APP_ID = 30765851
APP_HASH = '235b0bc6f03767302dc75763508f7b75'

BOT_TOKEN_1 = "8565944163:AAE5tew3A1a6GkOw69vMPYSgV2obyO-wPz4"
BOT_TOKEN_2 = "7857238353:AAEkDQnXqxyvXOQufwJwzZ7tXlwrmzM6XyI"

SPECIFIC_GROUP = -1003580630981 # Log group / Target Image Group
TZ = pytz.timezone('Asia/Yangon')

# ==========================================
# 🗄️ DATABASE SETUP
# ==========================================
client_mongo = MongoClient(MONGO_URI)
db = client_mongo["telegram_bot"]
filters_col = db["custom_filters"]
allow_col = db["allowed_users"]
groups_col = db["active_groups"]

# 🤖 CLIENTS INITIALIZATION
bot1 = TelegramClient('bot1_session', APP_ID, APP_HASH)
bot2 = TelegramClient('bot2_session', APP_ID, APP_HASH)

# ==========================================
# 🛠️ HELPERS
# ==========================================
bot_bully_tasks = {}
sticker_spam_data = {}

def bq(text): return f"<blockquote><b>{text}</b></blockquote>"
def owner_tag(): return f"<a href='tg://user?id={OWNER_ID}'>⚚𝘽𝙤𝘿𝙭𝗪𝘆𝗮𝗮𝗾𝗾 𝗭𝘅𝘆𝗳𝗮𝗻𝘇𝘁</a>"

def is_allowed(user_id):
    if user_id == OWNER_ID: return True
    return allow_col.find_one({"user_id": user_id}) is not None

async def check_admin(client, chat_id, user_id):
    if user_id == OWNER_ID: return True
    try:
        permissions = await client.get_permissions(chat_id, user_id)
        return permissions.is_admin
    except: return False

# ==========================================
# 🛡️ EVENT HANDLERS (SHARED BY BOTH BOTS)
# ==========================================

# 1. Welcome & Goodbye (Text Only Version)
async def welcome_goodbye(event):
    client = event.client
    chat = await event.get_chat()
    bot_me = await client.get_me()
    bot_mention = f"<a href='tg://user?id={bot_me.id}'>{escape_html(bot_me.first_name)}</a>"
    safe_title = escape_html(chat.title)

    if event.user_added or event.user_joined:
        # Bot ကိုယ်တိုင် Group ထဲ အထည့်ခံရရင်
        if bot_me.id in event.user_ids:
            groups_col.update_one({"chat_id": chat.id}, {"$set": {"title": chat.title}}, upsert=True)
            msg1 = f"ဟိတ် OWNER နဲ့ Admins တို့ မင်းတို့ရဲ့ ဒီ {safe_title} ထဲကို ထည့်သုံးပေးလို့ ကျေးဇူးတင်ပါတယ်! အသုံးလိုကောင်းလိုနိုင်တဲ့ command များယူထားမယ်ဆိုရင် {bot_mention} ရဲ့ Creator {owner_tag()} ရဲ့ Dm (သို့မဟုတ်) @Besties_with_BoD ကိုလာရောက်ပါ!!!"
            await client.send_message(chat.id, bq(msg1), parse_mode='html')
            
            try: members = getattr(chat, 'participants_count', 'Unknown')
            except: members = "Unknown"
            
            msg2 = f"မင်္ဂလာပါ {safe_title}က သူငယ်ချင်းတို့ မင်းတို့ရဲ့\n{bot_mention}ကို အောက်ပါ Group က ထည့်သုံးထားပါသေးတယ်\n\nGroup Name - {safe_title}\nGroup ID - <code>{chat.id}</code>\nMembers အရေအတွက် - {members}\nBot Creator - {owner_tag()}"
            await client.send_message(SPECIFIC_GROUP, bq(msg2), parse_mode='html')
        
        # User အသစ်ဝင်လာရင် (ပုံမပါဘဲ စာပဲပို့မယ်)
        else:
            for uid in event.user_ids:
                if uid != bot_me.id:
                    try:
                        u = await client.get_entity(uid)
                        u_mention = f"<a href='tg://user?id={u.id}'>{escape_html(u.first_name)}</a>"
                        caption_msg = f"ဟိတ် {u_mention} ... {safe_title} ကနေ ကြိုဆိုလိုက်ပါတယ်!!🤍စကားဝင်ပြော၊သီချင်းနားထောင်၊ရည်းစားရှာ အပေါင်းအသင်းရှာ ကြိုက်တာလုပ်!"
                        await client.send_message(event.chat_id, bq(caption_msg), parse_mode='html')
                    except Exception as e: 
                        print(f"Welcome Message Error: {e}")

    # User ထွက်သွားရင်
    elif event.user_left or event.user_kicked:
        try:
            u = await client.get_entity(event.user_id)
            u_mention = f"<a href='tg://user?id={u.id}'>{escape_html(u.first_name)}</a>"
            await client.send_message(event.chat_id, bq(f"ထွက်သွားလိုက်ပါသေးတယ် {u_mention}!!"), parse_mode='html')
        except: pass

# 2. Add Global Filter
async def add_filter(event):
    client = event.client
    if not await check_admin(client, event.chat_id, event.sender_id): return

    input_str = event.pattern_match.group(1).split(None, 1)
    keyword = input_str[0].lower()
    reply = await event.get_reply_message()

    if reply:
        media = None
        m_type = None
        if reply.sticker:
            media = reply.media
            m_type = "sticker"
        elif reply.photo:
            media = reply.media
            m_type = "photo"
        elif reply.video:
            media = reply.media
            m_type = "video"
        elif reply.text:
            media = reply.text
            m_type = "text"

        if media:
            filters_col.update_one(
                {"keyword": keyword},
                {"$set": {"content": media, "type": m_type, "chat_id": "global"}}, 
                upsert=True
            )
            await event.reply(bq(f"အိုကေ! '{keyword}' အတွက် {m_type} filter ကို Group အားလုံးအတွက် မှတ်လိုက်ပြီ ✅"), parse_mode='html')
    
    elif len(input_str) > 1:
        filters_col.update_one(
            {"keyword": keyword},
            {"$set": {"content": input_str[1], "type": "text", "chat_id": "global"}}, 
            upsert=True
        )
        await event.reply(bq(f"အိုကေ! '{keyword}' ဆိုရင် '{input_str[1]}' လို့ Group အားလုံးမှာ ပြန်ပေးမယ်။ ✅"), parse_mode='html')

# 3. ID / GID Finders
async def get_user_id(event):
    reply = await event.get_reply_message()
    if reply:
        target_id = reply.sender_id
        user = await reply.get_sender()
        name = escape_html(user.first_name) if user else "User"
        msg = f"👤 <b>Name:</b> {name}\n🆔 <b>User ID:</b> <code>{target_id}</code>"
    else:
        target_id = event.sender_id
        msg = f"🆔 <b>Your ID:</b> <code>{target_id}</code>"
    await event.respond(bq(msg), parse_mode='html')

async def get_group_id(event):
    if event.is_private: return await event.respond(bq("ဒါက Private Chat မို့လို့ Group ID မရှိပါဘူး!"), parse_mode='html')
    chat_id = event.chat_id
    chat_title = escape_html(event.chat.title)
    msg = f"📍 <b>Group:</b> {chat_title}\n🌐 <b>Chat ID:</b> <code>{chat_id}</code>"
    await event.respond(bq(msg), parse_mode='html')

# 4. Admin Management Commands
async def tag_admins(event):
    client = event.client
    if not await check_admin(client, event.chat_id, event.sender_id): return
    text = event.pattern_match.group(1) or "Admins ခေါ်နေပါတယ်!"
    try:
        admins = await client.get_participants(event.chat_id, filter=ChannelParticipantsAdmins)
        msg = f"📣 <b>{escape_html(text)}</b>\n\n"
        for a in admins:
            if not a.bot: msg += f"• <a href='tg://user?id={a.id}'>{escape_html(a.first_name)}</a>\n"
        await event.respond(bq(msg), parse_mode='html')
    except Exception as e: await event.respond(bq(f"Error: {e}"), parse_mode='html')

async def promote_admin(event):
    client = event.client
    if not await check_admin(client, event.chat_id, event.sender_id): return
    reply = await event.get_reply_message()
    if not reply: return await event.respond(bq("Admin ပေးချင်တဲ့သူကို Reply ထောက်ပါ။"), parse_mode='html')
    
    promoter = await event.get_sender()
    target = await reply.get_sender()
    p_mention = f"<a href='tg://user?id={promoter.id}'>{escape_html(promoter.first_name)}</a>"
    t_mention = f"<a href='tg://user?id={target.id}'>{escape_html(target.first_name)}</a>"
    
    rights = ChatAdminRights(
        post_messages=True, add_admins=False, change_info=False,
        ban_users=False, anonymous=False, delete_messages=True,
        invite_users=True, pin_messages=True, edit_messages=True, manage_call=True
    )
    try:
        await client.edit_admin(event.chat_id, target.id, admin_rights=rights, rank="Admin")
        msg = f"{p_mention} က {t_mention} သူ့ကို ADMIN ပေးထားလိုက်ပါပြီ။\n\n<b>သူ/သူမ၏ Admin Rights-</b>\n✅ Delete Messages\n✅ Pin Messages\n✅ Invite Users\n✅ Manage Video Chats\n✅ Edit Messages\n❌ Ban Users\n❌ Change Group Info\n❌ Remain Anonymous"
        await event.respond(bq(msg), parse_mode='html')
    except Exception as e: await event.respond(bq(f"Error: {e}"), parse_mode='html')

async def demote_admin(event):
    client = event.client
    if not await check_admin(client, event.chat_id, event.sender_id): return
    reply = await event.get_reply_message()
    if not reply: return await event.respond(bq("ရာထူးဖြုတ်ချင်တဲ့သူကို Reply ထောက်ပါ။"), parse_mode='html')
    
    empty_rights = ChatAdminRights(
        post_messages=False, add_admins=False, change_info=False, ban_users=False,
        anonymous=False, delete_messages=False, invite_users=False, pin_messages=False,
        edit_messages=False, manage_call=False
    )
    try:
        await client.edit_admin(event.chat_id, reply.sender_id, admin_rights=empty_rights, rank="")
        target = await reply.get_sender()
        await event.respond(bq(f"<a href='tg://user?id={target.id}'>{escape_html(target.first_name)}</a> ကို Admin အဖြစ်မှ ဖယ်ရှားလိုက်ပါပြီ။"), parse_mode='html')
    except Exception as e: await event.respond(bq(f"Error: {e}"), parse_mode='html')

async def mute_user(event):
    client = event.client
    if not await check_admin(client, event.chat_id, event.sender_id): return
    reply = await event.get_reply_message()
    if reply:
        try:
            await client.edit_permissions(event.chat_id, reply.sender_id, send_messages=False)
            await event.respond(bq(f"<a href='tg://user?id={reply.sender_id}'>{escape_html(reply.sender.first_name)}</a> ကို Mute လိုက်ပါပြီ!"), parse_mode='html')
        except Exception as e: await event.respond(bq(f"Error: {e}"), parse_mode='html')

async def unmute_user(event):
    client = event.client
    if not await check_admin(client, event.chat_id, event.sender_id): return
    reply = await event.get_reply_message()
    if reply:
        try:
            await client.edit_permissions(event.chat_id, reply.sender_id, send_messages=True)
            await event.respond(bq(f"<a href='tg://user?id={reply.sender_id}'>{escape_html(reply.sender.first_name)}</a> စာပြန်ပို့!Unmute လုပ်ပြီးပြီ!"), parse_mode='html')
        except Exception as e: await event.respond(bq(f"Error: {e}"), parse_mode='html')

# 5. Allow System
async def add_allow(event):
    if event.sender_id != OWNER_ID: return
    reply = await event.get_reply_message()
    if reply:
        allow_col.update_one({"user_id": reply.sender_id}, {"$set": {"name": reply.sender.first_name}}, upsert=True)
        await event.reply(bq(f"{escape_html(reply.sender.first_name)} ကို Allow List ထည့်ပြီးပါပြီ! ✅"), parse_mode='html')
    else: await event.reply(bq("Allow ပေးချင်တဲ့သူကို Reply ထောက်ပြီးမှ Command ရိုက်"), parse_mode='html')

async def remove_allow(event):
    if event.sender_id != OWNER_ID: return
    target_id = int(event.pattern_match.group(1))
    res = allow_col.delete_one({"user_id": target_id})
    if res.deleted_count > 0:
        await event.respond(bq(f"User ID <code>{target_id}</code> ကို ပါမစ်မပေးတော့ဘူး"), parse_mode='html')
    else:
        await event.respond(bq("ဒီ User ID ကို List ထဲမှာ မတွေ့ပါ။"), parse_mode='html')

async def allow_list(event):
    if event.sender_id != OWNER_ID: return
    users = list(allow_col.find())
    if users:
        msg = "<b>✅ Allowed Users List:</b>\n\n"
        for u in users: msg += f"• <a href='tg://user?id={u.get('user_id')}'>{escape_html(u.get('name', 'Unknown'))}</a> (<code>{u.get('user_id')}</code>)\n"
    else: msg = "Allow List မှာ မရှိသေးပါ။"
    await event.reply(bq(msg), parse_mode='html')

# 6. Bully System
async def bot_bully(event):
    client = event.client
    if not is_allowed(event.sender_id): 
        return await event.reply(bq("မင်းမှာ ဒီ Command ကို သုံးပိုင်ခွင့်မရှိဘူး။သုံးခွင့်နဲ့အသုံးပြုနည်းများအတွက် @Besties_with_BoD ကိုလာ"), parse_mode='html')
    
    reply = await event.get_reply_message()
    if not reply: 
        return await event.respond(bq("ဘယ်ကောင့်ကို ခေါင်းမဖော်နိုင်အောင် ဆဲပေးရမလဲ၊Replyပြန်လိုက်"), parse_mode='html')

    try: await event.delete()
    except: pass

    chat_id = event.chat_id
    t = await reply.get_sender()
    if not t: return

    target_id = t.id
    if target_id == OWNER_ID:
        await event.respond(bq("ဟိတ်ကောင် Creatorကို ပြန်ပြီးဆဲဆိုခွင့် မပေးထားဘူး🔥"), parse_mode='html')
        return

    bot_bully_tasks[chat_id] = True
    mention = f"<a href='tg://user?id={target_id}'>{escape_html(t.first_name)}</a>"
    sender = await event.get_sender()
    s_mention = f"<a href='tg://user?id={sender.id}'>{escape_html(sender.first_name)}</a>"
    
    words = [w.get("content") for w in filters_col.find({"chat_id": "global", "type": "text"}) if w.get("content")]
    if not words: words = ["ခွေးကောင်", "စောက်ရူး", "ငလူးမသား"] # Fallback if DB is empty
    
    await event.respond(bq(f"ဟိတ် {s_mention} !! /b သို့မဟုတ် /sb command ကို အသုံးပြုလိုက်ပါသေးတယ်! စာအစားထိုးပေးထားပါတယ်ဗျ။\n{mention} ကို ခေါင်းမဖော်နိုင်အောင် စဆဲပါပြီ။"), parse_mode='html')

    send_count = 0
    while bot_bully_tasks.get(chat_id):
        try: 
            await client.send_message(chat_id, bq(f"{mention} {random.choice(words)}"), reply_to=reply.id, parse_mode='html')
            send_count += 1
            if send_count >= 8: 
                await asyncio.sleep(1)
                send_count = 0 
            else: await asyncio.sleep(0.6) 
        except Exception:
            bot_bully_tasks[chat_id] = False
            break

async def stop_bot_bully(event):
    if not is_allowed(event.sender_id): return
    try: await event.delete()
    except: pass
    
    sender = await event.get_sender()
    s_mention = f"<a href='tg://user?id={sender.id}'>{escape_html(sender.first_name)}</a>"
    
    bot_bully_tasks[event.chat_id] = False
    await event.respond(bq(f"ဟိတ် {s_mention} !! /sb command ကို အသုံးပြုလိုက်ပါသေးတယ်!\nအခုနားဆိုလို့နားလိုက်မယ်၊စောက်ချိုးမပြေရင်ထပ်ဆဲပေးမယ်"), parse_mode='html')

# 7. VC Service
async def vc_service_listener(event):
    client = event.client
    if event.is_private: return
    if event.action_message:
        if isinstance(event.action_message.action, types.MessageActionGroupCallStarted):
            try: await event.action_message.delete()
            except: pass
            await client.send_message(event.chat_id, bq("ဟုတ် သီချင်းနားထောင်တာ (or) စကားပြောဖို့အတွက် Voice Chat စလိုက်ပါသေးတယ် 🎧"), parse_mode='html')
        elif isinstance(event.action_message.action, types.MessageActionGroupCallEnded):
            try: await event.action_message.delete()
            except: pass
            await client.send_message(event.chat_id, bq("Voice Chat ပြီးဆုံးသွားပါပြီ!! 💔"), parse_mode='html')

# 8. Protection & Spam Check
async def protection_logic(event):
    client = event.client
    if event.is_private: return
    me = await client.get_me()
    if not event.text or event.sender_id == OWNER_ID or event.sender_id == me.id: return

    sender = await event.get_sender()
    text = event.text.strip()
    chat_id = event.chat_id
    sender_id = event.sender_id

    # Harem & Waifu Filter
    if re.search(r'/harem(@\w+)?', text) or re.search(r'/waifu(@\w+)?', text):
        try:
            full_name = escape_html(f"{sender.first_name} {sender.last_name or ''}".strip())
            mention = f"<a href='tg://user?id={sender_id}'>{full_name}</a>"
            cmd_type = "harem" if "harem" in text.lower() else "waifu"
            await event.delete()
            msg_template = "<b>{type} လုပ်သူ-</b> {mention}\nChat သန့်ရှင်းအောင် ဖျက်လိုက်ပါပြီ။"
            warn_msg = await event.respond(bq(msg_template.format(type=cmd_type, mention=mention)), parse_mode='html')
            for i in range(9, -1, -1):
                await asyncio.sleep(1)
                if i == 0:
                    await warn_msg.delete()
                    break
                await warn_msg.edit(bq(msg_template.format(type=cmd_type, mention=mention) + f"\n\n{i} စက္ကန့်အတွင်း ပျောက်ကွယ်သွားပါမယ်။"), parse_mode='html')
            return 
        except: pass

    # Bio Filter
    bio_keywords = ["Bio", "bio", "ဘိုင်အို", "ဘိုင်-အို", "ဘိုင်-O"]
    if any(key in text for key in bio_keywords):
        if not await check_admin(client, chat_id, sender_id):
            try:
                await event.delete()
                await event.respond(bq("Bruhh bruhh bioမှာဘာဖြစ်တာလဲ မသိချင်ဘူး ဖျက်လိုက်ပြီ။"), parse_mode='html')
                return 
            except: pass

    # Link Filter
    urls = re.findall(r'(https?://\S+|www\.\S+)', text)
    if urls:
        if event.forward:
            if await check_admin(client, chat_id, sender_id):
                text_lower = text.lower()
                if any(k in text_lower for k in ["movie", "episode", "season", "ဇာတ်ကား", "ကားသစ်"]):
                    await event.reply(bq("ဘာကားလဲဟ! သူငယ်ချင်းတွေပါ ခေါ်ကြည့်လို့ရတယ်နော်။ 😎🍿"), parse_mode='html')
                elif any(k in text_lower for k in ["mp3", "music", "song", "lyrics", "audio", "သီချင်း"]):
                    await event.reply(bq("သီချင်းကောင်းလေးပဲ! ကျန်တဲ့သူတွေလည်း သူပို့တာ နားထောင်ကြည့်ကြဦး။ 🔥🎧"), parse_mode='html')
            return 

        if await check_admin(client, chat_id, sender_id):
            full_name = escape_html(f"{sender.first_name} {sender.last_name or ''}".strip())
            mention = f"<a href='tg://user?id={sender_id}'>{full_name}</a>"
            all_links = "\n".join(urls)
            try:
                await event.delete()
                await event.respond(bq(f"Link ပို့လိုက်တဲ့ Admin ချောချောလေး - {mention}\nသူပို့လိုက်တဲ့ Link- {all_links}"), parse_mode='html')
            except: pass
        else:
            try:
                full_name = escape_html(f"{sender.first_name} {sender.last_name or ''}".strip())
                member_mention = f"<a href='tg://user?id={sender_id}'>{full_name}</a>"
                await event.delete()
                steps = ["ဟိတ်..", f"ဟိတ်.. {member_mention} ဘာ link မှမပို့နဲ့ မရဘူး၊", f"ဟိတ်.. {member_mention} မင်း link ကို ငါဖျက်လိုက်ပြီ🫵"]
                warn_msg = await event.respond(bq(steps[0]), parse_mode='html')
                for step in steps[1:]:
                    await asyncio.sleep(1)
                    try: await warn_msg.edit(bq(step), parse_mode='html')
                    except: break
            except: pass

# 9. Group Specific Rules (Catcher Bot logic)
async def group_specific_rules(event):
    client = event.client
    if event.is_private: return
    me = await client.get_me()
    if not event.text or event.sender_id == OWNER_ID or event.sender_id == me.id: return

    text = event.text.strip().lower()
    chat_id = event.chat_id
    sender = await event.get_sender()
    sender_id = event.sender_id
    
    if chat_id == SPECIFIC_GROUP:
        chat_title = escape_html(event.chat.title)
        keywords = ["ဂေ့", "ဂစ်", "ကတ်ဂေ့", "ကဒ်ဂေ့"]
        if re.search(r'^[/,.](harem|gift|check)', text) or any(k in text for k in keywords):
            full_name = escape_html(f"{sender.first_name} {sender.last_name or ''}".strip())
            user_mention = f"<a href='tg://user?id={sender_id}'>{full_name}</a>"
            msg = f"ဟိတ်... {user_mention} !! <b>{chat_title}</b> ထဲမှာ Character Catcher Bot ကို ကဒ်ကောက်ဖို့ပဲ ရတော့မယ်။ကျန်တဲ့ Giftပေးတာ,Haremတာ,Checkတာတွေအတွက် သီးသန့် Group Chat တစ်ခု ဖွင့်ပေးထားပါတယ်၊အဲ့ထဲမှာ စိတ်ကြိုက် ကဒ်ဂေ့၊ဟာရမ်း၊ချက်ခ်လုပ်ကြပါ သူငယ်ချင်းတို့🤍 သီးသန့် Group Mention Link - https://t.me/catchbot_gift_harem_check_only"
            try: await event.reply(bq(msg), parse_mode='html', link_preview=False)
            except: pass


async def broadcast(event):
    client = event.client
    if event.sender_id != OWNER_ID: return
    text = event.pattern_match.group(1)
    if not text: return await event.respond(bq("ပို့မယ့်စာသား ထည့်ပါဦး​ဗျ"))
    success = 0
    for g in list(groups_col.find()):
        try:
            await client.send_message(g['chat_id'], bq(text), parse_mode='html')
            success += 643
        except: pass
    await event.respond(bq(f"ငါ မင်းပို့ခိုင်းတဲ့ Message တွေကို သေချာပို့ပေးလိုက်ပြီ! 📢\nပို့ဆောင်ပြီးစီးသော Group အရေအတွက်: {success}"), parse_mode='html')

async def show_commands(event):
    features = (
        "🤖 <b>BoDx Sovereign Bot Features:</b>\n"
        "• <b>Welcome Image:</b> အဖွဲ့ဝင်သစ်တွေကို Profile ပါတဲ့ ပုံနဲ့ ကြိုဆိုခြင်း\n"
        "• <b>Anti-Spam:</b> Sticker 2 ခု 1 စက္ကန့်အတွင်း ပို့ရင် သတိပေးခြင်း\n"
        "• <b>Filters:</b> Link, Bio, Harem/Waifu Command တွေ သန့်ရှင်းရေးလုပ်ခြင်း\n"
        "• <b>VC Monitor:</b> Voice Chat စတာနဲ့ ပြီးတာကို အသိပေးခြင်း\n\n"
    )
    admin_cmds = (
        "🛠 <b>Admin Commands:</b>\n"
        "• <code>/adm [text]</code> - Admin အကုန်လုံးကို Tag ခေါ်ပြီး စာပို့ခြင်း\n"
        "• <code>/padm</code> - Admin Rights (Change info, Ban etc.. မပါ) ပေးခြင်း\n"
        "• <code>/dadm</code> - Admin ရာထူးမှ ဖြုတ်ချခြင်း\n"
        "• <code>/mute</code> / <code>/unmute</code> - စာပို့ခွင့် ပိတ်/ဖွင့်ခြင်း\n"
        "• <code>/f [word] [reply]</code> - Global Filter မှတ်ခြင်း\n"
        "• <code>/play [name]</code> - သီချင်းဖွင့်ကြောင်း အလှပြစာသားပို့ခြင်း\n"
        "• <code>/id</code> / <code>/gid</code> - User သို့မဟုတ် Group ရဲ့ ID ကို ကြည့်ခြင်း\n\n"
    )
    allowed_only = (
        "🌟 <b>Allowed Users Only:</b>\n"
        "• <code>/b</code> - တစ်ဖက်လူကို ခေါင်းမဖော်နိုင်အောင် ဆဲခိုင်းခြင်း (Bully)\n"
        "• <code>/sb</code> - Bully လုပ်နေတာကို ရပ်ခိုင်းခြင်း\n"
        "• <code>/addallow</code> - Allow List ထဲသို့ ထည့်ခြင်း\n"
        "• <code>/removeallow [id]</code> - Allow List မှ ပယ်ဖျက်ခြင်း\n"
        "• <code>/allowlist</code> - Allow ရထားသူများ စာရင်းကြည့်ခြင်း\n"
    )
    await event.respond(bq(features + admin_cmds + allowed_only), parse_mode='html')

# 11. Global Filter Watcher
async def group_filter_watcher(event):
    client = event.client
    if event.is_private or not event.text: return
    me = await client.get_me()
    if event.sender_id == me.id: return

    user_msg = event.text.lower().strip()
    all_filters = filters_col.find()
    
    for item in all_filters:
        keyword = item["keyword"].lower().strip()
        is_match = False
        if user_msg == keyword: is_match = True
        elif f" {keyword} " in f" {user_msg} ": is_match = True
        elif user_msg.startswith(f"{keyword} "): is_match = True
        elif user_msg.endswith(f" {keyword}"): is_match = True

        if is_match:
            content = item["content"]
            m_type = item["type"]
            try:
                if m_type == "text": await event.reply(content)
                else: await event.reply(file=content)
                break
            except Exception as e: print(f"Filter Response Error: {e}")

# ==========================================
# 🔌 REGISTER HANDLERS TO BOTH BOTS
# ==========================================
def register_handlers(bot):
    bot.add_event_handler(welcome_goodbye, events.ChatAction())
    bot.add_event_handler(vc_service_listener, events.ChatAction())
    
    bot.add_event_handler(add_filter, events.NewMessage(pattern=r'^[/.]f\s+(.*)'))
    bot.add_event_handler(get_user_id, events.NewMessage(pattern=r'^[/.]id'))
    bot.add_event_handler(get_group_id, events.NewMessage(pattern=r'^[/.]gid'))
    bot.add_event_handler(tag_admins, events.NewMessage(pattern=r'^/adm(?:\s+(.*))?'))
    bot.add_event_handler(promote_admin, events.NewMessage(pattern=r'^/padm(?:@\w+)?$'))
    bot.add_event_handler(demote_admin, events.NewMessage(pattern=r'^/dadm(?:@\w+)?$'))
    bot.add_event_handler(mute_user, events.NewMessage(pattern=r'^/mute(?:@\w+)?$'))
    bot.add_event_handler(unmute_user, events.NewMessage(pattern=r'^/unmute(?:@\w+)?$'))
    bot.add_event_handler(add_allow, events.NewMessage(pattern=r'^/addallow(?:@\w+)?$'))
    bot.add_event_handler(remove_allow, events.NewMessage(pattern=r'^/removeallow(?:@\w+)?\s+(\d+)'))
    bot.add_event_handler(allow_list, events.NewMessage(pattern=r'^/allowlist(?:@\w+)?$'))
    bot.add_event_handler(bot_bully, events.NewMessage(pattern=r'^/b(?:@\w+)?$'))
    bot.add_event_handler(stop_bot_bully, events.NewMessage(pattern=r'^/sb(?:@\w+)?$'))
    bot.add_event_handler(play_response, events.NewMessage(pattern=r'^/play(?:\s+(.*))?'))
    bot.add_event_handler(broadcast, events.NewMessage(pattern=r'^/send(?:@\w+)?\s+(.*)'))
    bot.add_event_handler(show_commands, events.NewMessage(pattern=r'^[/.]show'))

    bot.add_event_handler(protection_logic, events.NewMessage())
    bot.add_event_handler(sticker_spam_filter, events.NewMessage())
    bot.add_event_handler(group_specific_rules, events.NewMessage())
    bot.add_event_handler(group_filter_watcher, events.NewMessage())

register_handlers(bot1)
register_handlers(bot2)

# ==========================================
# 🚀 EXECUTION
# ==========================================
async def main():
    threading.Thread(target=run_flask, daemon=True).start()
    
    await bot1.start(bot_token=BOT_TOKEN_1)
    await bot2.start(bot_token=BOT_TOKEN_2)
    print("✅ Dexter Morgan's Dual-Bot System Online!")
    
    await asyncio.gather(
        bot1.run_until_disconnected(),
        bot2.run_until_disconnected()
    )

if __name__ == "__main__":
    asyncio.run(main())
