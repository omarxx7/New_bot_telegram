import time
import re
import os
import json
from collections import defaultdict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

import yt_dlp

import os
BOT_TOKEN = os.environ.get("BOT_TOKEN", "التوكن_هنا")
OWNER_ID = 6413050201
CREATER_USERNAME = "@Y_U_OMVR"
USER_COOLDOWN = 8

ADMINS_FILE = "admins.json"
BANNED_FILE = "banned.json"
CHANNELS_FILE = "channels.json"
WELCOME_FILE = "welcome.json"

def load_data(file, default):
    if os.path.exists(file):
        with open(file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default

def save_data(file, data):
    with open(file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

ADMINS = set(load_data(ADMINS_FILE, [7868892935]))
banned_users = set(load_data(BANNED_FILE, []))
FORCE_CHANNELS = load_data(CHANNELS_FILE, ["@Athr_Tayyeb", "@SVD_OMVR"])
WELCOME_MSG = load_data(WELCOME_FILE, {"text": "🎬 أهلاً بيك في بوت التحميل الخرافي! 🔥\n\nيسطا البوت ده هيحملك من يوتيوب بأي جودة تحبها 🚀\nمن 144p لحد 8K 💎\n\n📹 ابعت أي لينك يوتيوب\n🔍 أو اكتب /search وابحث براحتك\n🎵 حمّل فيديو أو صوت بس\n\n👨‍💻 المطور والمالك: @Y_U_OMVR\n⚡️ استمتع بالتحميل السريع!"})

known_users = set()
BAD_WORDS = ["sex", "porn", "xnxx", "xxx", "اباحي", "جنس", "سكس", "نيك", "عاهرة"]
last_message_time = defaultdict(int)
bot_active = True

def is_owner(uid):
    return uid == OWNER_ID

def is_admin(uid):
    return uid == OWNER_ID or uid in ADMINS

def anti_spam(uid):
    now = time.time()
    if now - last_message_time[uid] < USER_COOLDOWN:
        return False
    last_message_time[uid] = now
    return True

def is_youtube_link(text):
    return bool(re.search(r"(youtube\.com|youtu\.be)", text))

def contains_bad_words(text):
    return any(w in text.lower() for w in BAD_WORDS)

async def check_subscription(bot, user_id):
    if is_admin(user_id):
        return True
    for ch in FORCE_CHANNELS:
        try:
            member = await bot.get_chat_member(ch, user_id)
            if member.status in ("left", "kicked"):
                return False
        except:
            return False
    return True

async def force_subscribe_msg(update: Update):
    buttons = []
    for ch in FORCE_CHANNELS:
        buttons.append([InlineKeyboardButton(f"📢 {ch}", url=f"https://t.me/{ch[1:]}")])
    buttons.append([InlineKeyboardButton("✅ تحققت من الاشتراك", callback_data="check_sub")])
    await update.message.reply_text("🔒 عشان تستخدم البوت لازم تشترك في القنوات دي:\n\n" + "\n".join([f"• {ch}" for ch in FORCE_CHANNELS]) + "\n\n⚠️ بعد الاشتراك اضغط على الزر تحت 👇", reply_markup=InlineKeyboardMarkup(buttons))

def main_keyboard():
    return ReplyKeyboardMarkup([["🚀 ابدأ التحميل", "🔍 بحث"], ["🛠 لوحة التحكم"]], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"📨 رسالة /start من: {update.effective_user.id}")
    user = update.effective_user
    if user.id in banned_users:
        await update.message.reply_text("⛔️ أنت محظور من استخدام البوت!")
        return
    if not bot_active and not is_admin(user.id):
        await update.message.reply_text("⚠️ البوت متوقف حالياً للصيانة\nارجع بعدين يسطا 🔧")
        return
    if user.id not in known_users:
        known_users.add(user.id)
        username = f"@{user.username}" if user.username else "لا يوجد"
        await context.bot.send_message(OWNER_ID, f"🆕 مستخدم جديد انضم للبوت!\n\n👤 الاسم: {user.full_name}\n🔖 اليوزر: {username}\n🆔 ID: `{user.id}`\n📊 إجمالي المستخدمين: {len(known_users)}", parse_mode='Markdown')
    if not await check_subscription(context.bot, user.id):
        await force_subscribe_msg(update)
        return
    context.user_data.clear()
    await update.message.reply_text(WELCOME_MSG["text"], reply_markup=main_keyboard())

async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔️ هذا الأمر للمشرفين فقط!")
        return
    buttons = [[InlineKeyboardButton("👥 عدد المستخدمين", callback_data="panel_users_count"), InlineKeyboardButton("🚫 المحظورين", callback_data="panel_banned_list")], [InlineKeyboardButton("⛔️ حظر مستخدم", callback_data="panel_ban_user"), InlineKeyboardButton("✅ فك الحظر", callback_data="panel_unban_user")], [InlineKeyboardButton("🛡 عدد المشرفين", callback_data="panel_admins_list")]]
    if is_owner(user_id):
        buttons += [[InlineKeyboardButton("➕ إضافة مشرف", callback_data="panel_add_admin"), InlineKeyboardButton("➖ عزل مشرف", callback_data="panel_remove_admin")], [InlineKeyboardButton("📢 إضافة قناة شرط", callback_data="panel_add_channel"), InlineKeyboardButton("🗑 إزالة قناة", callback_data="panel_remove_channel")], [InlineKeyboardButton("✏️ تعديل رسالة الترحيب", callback_data="panel_edit_welcome"), InlineKeyboardButton("📣 نشر رسالة", callback_data="panel_broadcast")], [InlineKeyboardButton("🔴 إيقاف البوت", callback_data="panel_stop_bot") if bot_active else InlineKeyboardButton("🟢 تشغيل البوت", callback_data="panel_start_bot")]]
    role = "👑 المالك" if is_owner(user_id) else "🛡 مشرف"
    await update.message.reply_text(f"🎛 لوحة التحكم\n\n{role}: {update.effective_user.first_name}", reply_markup=InlineKeyboardMarkup(buttons))

async def panel_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    if not is_admin(user_id):
        await q.message.reply_text("⛔️ غير مصرح لك!")
        return
    if q.data == "panel_users_count":
        await q.message.reply_text(f"📊 إحصائيات المستخدمين\n\n👥 إجمالي المستخدمين: {len(known_users)}\n🛡 عدد المشرفين: {len(ADMINS)}\n🚫 المحظورين: {len(banned_users)}")
    elif q.data == "panel_banned_list":
        if not banned_users:
            await q.message.reply_text("✅ لا يوجد مستخدمين محظورين")
        else:
            text = "🚫 قائمة المحظورين:\n\n"
            for user_id_banned in banned_users:
                try:
                    user = await context.bot.get_chat(user_id_banned)
                    username = f"@{user.username}" if user.username else "لا يوجد"
                    text += f"👤 {user.full_name}\n🔖 {username}\n🆔 `{user_id_banned}`\n\n"
                except:
                    text += f"🆔 `{user_id_banned}`\n\n"
            await q.message.reply_text(text, parse_mode='Markdown')
    elif q.data == "panel_ban_user":
        context.user_data["waiting_for"] = "ban_user"
        await q.message.reply_text("✏️ ابعت اليوزر أو الـ ID للمستخدم اللي عايز تحظره\n\nمثال: @username أو 123456789")
    elif q.data == "panel_unban_user":
        context.user_data["waiting_for"] = "unban_user"
        await q.message.reply_text("✏️ ابعت اليوزر أو الـ ID للمستخدم اللي عايز تفك حظره")
    elif q.data == "panel_admins_list":
        text = f"🛡 قائمة المشرفين ({len(ADMINS)}):\n\n"
        for admin_id in ADMINS:
            try:
                user = await context.bot.get_chat(admin_id)
                username = f"@{user.username}" if user.username else "لا يوجد"
                text += f"👤 {user.full_name}\n🔖 {username}\n🆔 `{admin_id}`\n\n"
            except:
                text += f"🆔 `{admin_id}`\n\n"
        try:
            owner = await context.bot.get_chat(OWNER_ID)
            owner_username = f"@{owner.username}" if owner.username else "لا يوجد"
            text += f"👑 المالك:\n👤 {owner.full_name}\n🔖 {owner_username}\n🆔 `{OWNER_ID}`"
        except:
            text += f"👑 المالك: `{OWNER_ID}`"
        await q.message.reply_text(text, parse_mode='Markdown')
    elif q.data == "panel_add_admin":
        if not is_owner(user_id):
            await q.message.reply_text("⛔️ هذا الأمر للمالك فقط!")
            return
        context.user_data["waiting_for"] = "add_admin"
        await q.message.reply_text("✏️ ابعت اليوزر أو الـ ID للشخص اللي عايز تضيفه مشرف")
    elif q.data == "panel_remove_admin":
        if not is_owner(user_id):
            await q.message.reply_text("⛔️ هذا الأمر للمالك فقط!")
            return
        context.user_data["waiting_for"] = "remove_admin"
        await q.message.reply_text("✏️ ابعت اليوزر أو الـ ID للمشرف اللي عايز تعزله")
    elif q.data == "panel_add_channel":
        if not is_owner(user_id):
            await q.message.reply_text("⛔️ هذا الأمر للمالك فقط!")
            return
        context.user_data["waiting_for"] = "add_channel"
        await q.message.reply_text("✏️ ابعت يوزر القناة (مثال: @ChannelName)")
    elif q.data == "panel_remove_channel":
        if not is_owner(user_id):
            await q.message.reply_text("⛔️ هذا الأمر للمالك فقط!")
            return
        if len(FORCE_CHANNELS) == 0:
            await q.message.reply_text("⚠️ لا توجد قنوات لإزالتها")
            return
        buttons = []
        for ch in FORCE_CHANNELS:
            buttons.append([InlineKeyboardButton(f"🗑 {ch}", callback_data=f"remove_ch_{ch}")])
        await q.message.reply_text("اختر القناة اللي عايز تشيلها:", reply_markup=InlineKeyboardMarkup(buttons))
    elif q.data == "panel_edit_welcome":
        if not is_owner(user_id):
            await q.message.reply_text("⛔️ هذا الأمر للمالك فقط!")
            return
        context.user_data["waiting_for"] = "edit_welcome"
        await q.message.reply_text(f"✏️ ابعت رسالة الترحيب الجديدة\n\n💡 يمكنك استخدام: {{CREATER_USERNAME}} للإشارة ليوزرك\n\nالرسالة الحالية:\n{WELCOME_MSG['text']}")
    elif q.data == "panel_broadcast":
        if not is_owner(user_id):
            await q.message.reply_text("⛔️ هذا الأمر للمالك فقط!")
            return
        context.user_data["waiting_for"] = "broadcast"
        await q.message.reply_text("✏️ ابعت الرسالة اللي عايز تنشرها لكل المستخدمين")
    elif q.data == "panel_stop_bot":
        if not is_owner(user_id):
            await q.message.reply_text("⛔️ هذا الأمر للمالك فقط!")
            return
        global bot_active
        bot_active = False
        await q.message.reply_text("🔴 تم إيقاف البوت للمستخدمين العاديين\n\n✅ المشرفين والمالك يقدروا يستخدموه عادي")
    elif q.data == "panel_start_bot":
        if not is_owner(user_id):
            await q.message.reply_text("⛔️ هذا الأمر للمالك فقط!")
            return
        bot_active = True
        await q.message.reply_text("🟢 تم تشغيل البوت بنجاح!")

async def remove_channel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not is_owner(q.from_user.id):
        return
    channel = q.data.replace("remove_ch_", "")
    if channel in FORCE_CHANNELS:
        FORCE_CHANNELS.remove(channel)
        save_data(CHANNELS_FILE, FORCE_CHANNELS)
        await q.message.reply_text(f"✅ تم حذف القناة {channel} من قائمة الاشتراك الإجباري")

async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if await check_subscription(context.bot, q.from_user.id):
        await q.message.delete()
        await context.bot.send_message(q.from_user.id, WELCOME_MSG["text"], reply_markup=main_keyboard())
    else:
        await q.answer("⚠️ لسه مشتركتش في كل القنوات!", show_alert=True)

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in banned_users:
        return
    if not bot_active and not is_admin(user_id):
        await update.message.reply_text("⚠️ البوت متوقف حالياً للصيانة")
        return
    if not await check_subscription(context.bot, user_id):
        await force_subscribe_msg(update)
        return
    context.user_data["waiting_for"] = "search_query"
    await update.message.reply_text("🔍 ابعت كلمة البحث اللي عايز تدور عليها")

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"📨 رسالة نصية من: {update.effective_user.id} - النص: {update.message.text[:50]}")
    user = update.effective_user
    text = update.message.text.strip()
    if text == "🚀 ابدأ التحميل":
        await start(update, context)
        return
    if text == "🔍 بحث":
        await search(update, context)
        return
    if text == "🛠 لوحة التحكم":
        await panel(update, context)
        return
    if user.id in banned_users:
        return
    if not bot_active and not is_admin(user.id):
        return
    if contains_bad_words(text):
        try:
            await update.message.delete()
        except:
            pass
        await update.message.reply_text("⛔️ ممنوع الكلام ده هنا!")
        return
    if not anti_spam(user.id) and not is_admin(user.id):
        return
    waiting_for = context.user_data.get("waiting_for")
    if waiting_for == "ban_user":
        try:
            if text.startswith("@"):
                chat = await context.bot.get_chat(text)
                ban_id = chat.id
            else:
                ban_id = int(text)
            if ban_id == OWNER_ID:
                await update.message.reply_text("❌ ما ينفعش تحظر المالك!")
                return
            banned_users.add(ban_id)
            save_data(BANNED_FILE, list(banned_users))
            context.user_data.clear()
            await update.message.reply_text(f"✅ تم حظر المستخدم `{ban_id}` بنجاح", parse_mode='Markdown')
        except:
            await update.message.reply_text("❌ حصل خطأ! تأكد من الـ ID أو اليوزر")
        return
    elif waiting_for == "unban_user":
        try:
            if text.startswith("@"):
                chat = await context.bot.get_chat(text)
                unban_id = chat.id
            else:
                unban_id = int(text)
            if unban_id in banned_users:
                banned_users.remove(unban_id)
                save_data(BANNED_FILE, list(banned_users))
                context.user_data.clear()
                await update.message.reply_text(f"✅ تم فك حظر المستخدم `{unban_id}`", parse_mode='Markdown')
            else:
                await update.message.reply_text("⚠️ المستخدم ده مش محظور أصلاً")
        except:
            await update.message.reply_text("❌ حصل خطأ!")
        return
    elif waiting_for == "add_admin" and is_owner(user.id):
        try:
            if text.startswith("@"):
                chat = await context.bot.get_chat(text)
                admin_id = chat.id
            else:
                admin_id = int(text)
            ADMINS.add(admin_id)
            save_data(ADMINS_FILE, list(ADMINS))
            context.user_data.clear()
            await update.message.reply_text(f"✅ تم إضافة `{admin_id}` كمشرف", parse_mode='Markdown')
        except:
            await update.message.reply_text("❌ حصل خطأ!")
        return
    elif waiting_for == "remove_admin" and is_owner(user.id):
        try:
            if text.startswith("@"):
                chat = await context.bot.get_chat(text)
                admin_id = chat.id
            else:
                admin_id = int(text)
            if admin_id in ADMINS:
                ADMINS.discard(admin_id)
                save_data(ADMINS_FILE, list(ADMINS))
                context.user_data.clear()
                await update.message.reply_text(f"✅ تم عزل المشرف `{admin_id}`", parse_mode='Markdown')
            else:
                await update.message.reply_text("⚠️ هذا الشخص ليس مشرفاً")
        except:
            await update.message.reply_text("❌ حصل خطأ!")
        return
    elif waiting_for == "add_channel" and is_owner(user.id):
        if not text.startswith("@"):
            await update.message.reply_text("❌ اليوزر لازم يبدأ بـ @")
            return
        if text in FORCE_CHANNELS:
            await update.message.reply_text("⚠️ القناة دي موجودة فعلاً")
            return
        FORCE_CHANNELS.append(text)
        save_data(CHANNELS_FILE, FORCE_CHANNELS)
        context.user_data.clear()
        await update.message.reply_text(f"✅ تم إضافة القناة {text} للاشتراك الإجباري")
        return
    elif waiting_for == "edit_welcome" and is_owner(user.id):
        WELCOME_MSG["text"] = text.replace("{CREATER_USERNAME}", CREATER_USERNAME)
        save_data(WELCOME_FILE, WELCOME_MSG)
        context.user_data.clear()
        await update.message.reply_text("✅ تم تحديث رسالة الترحيب!\n\nالرسالة الجديدة:\n" + WELCOME_MSG["text"])
        return
    elif waiting_for == "broadcast" and is_owner(user.id):
        context.user_data.clear()
        success = 0
        failed = 0
        status_msg = await update.message.reply_text("📤 جاري إرسال الرسالة...")
        for uid in known_users:
            try:
                await context.bot.send_message(uid, f"📢 رسالة من المطور:\n\n{text}")
                success += 1
            except:
                failed += 1
        await status_msg.edit_text(f"✅ تم إرسال الرسالة\n\n✔️ نجح: {success}\n❌ فشل: {failed}")
        return
    elif waiting_for == "search_query":
        context.user_data.clear()
        if not await check_subscription(context.bot, user.id):
            await force_subscribe_msg(update)
            return
        await update.message.reply_text("🔍 جاري البحث...")
        try:
            with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
                results = ydl.extract_info(f"ytsearch10:{text}", download=False)["entries"]
            if not results:
                await update.message.reply_text("❌ مفيش نتائج!")
                return
            buttons = []
            for i, v in enumerate(results[:10]):
                if v:
                    context.user_data[f"vid_{i}"] = v["webpage_url"]
                    title = v.get("title", "بدون عنوان")[:50]
                    buttons.append([InlineKeyboardButton(f"🎬 {title}", callback_data=f"vid_{i}")])
            await update.message.reply_text("🔍 نتائج البحث:", reply_markup=InlineKeyboardMarkup(buttons))
        except:
            await update.message.reply_text("❌ حصل خطأ في البحث")
        return
    if is_youtube_link(text):
        if not await check_subscription(context.bot, user.id):
            await force_subscribe_msg(update)
            return
        context.user_data.clear()
        context.user_data["link"] = text
        await show_format(update.message)
        return

async def search_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not await check_subscription(context.bot, q.from_user.id):
        await q.message.reply_text("⚠️ لازم تشترك في القنوات الأول!")
        return
    context.user_data["link"] = context.user_data.get(q.data)
    if context.user_data["link"]:
        await show_format(q.message)

async def show_format(msg):
    kb = [[InlineKeyboardButton("🎬 فيديو", callback_data="format_video"), InlineKeyboardButton("🎧 صوت", callback_data="format_audio")]]
    await msg.reply_text("📦 اختر الصيغة:", reply_markup=InlineKeyboardMarkup(kb))
async def format_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    
    if not await check_subscription(context.bot, user_id):
        await q.message.reply_text("⚠️ لازم تشترك في القنوات الأول!")
        return
    
    
    
    else:
        keyboard = [
            [InlineKeyboardButton("144p", callback_data="q_144")],
            [InlineKeyboardButton("240p", callback_data="q_240")],
            [InlineKeyboardButton("360p", callback_data="q_360")],
            [InlineKeyboardButton("480p", callback_data="q_480")],
            [InlineKeyboardButton("720p HD", callback_data="q_720")],
            [InlineKeyboardButton("1080p FHD", callback_data="q_1080")],
            [InlineKeyboardButton("2K QHD", callback_data="q_1440")],
            [if q.data == "format_audio":
    await q.message.edit_text("🎵 تم اختيار الصوت... جاري التحميل ⏬")
    
    url = context.user_data.get("link")
    if not url:
        await q.message.reply_text("❌ مفيش لينك للتحميل!")
        return
    
    try:
        await q.message.edit_text("⏬ جاري تحميل الصوت...")
        
        # إعدادات لتحميل أفضل صيغة صوتية (بدون تحويل)
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            # تجنب استخدام postprocessors التي تحتاج ffmpeg
            # استخدم extract_audio إذا كان الملف أصلاً بصيغة صوتية
            'extract_audio': True,
            'audio_format': 'mp3',
            'keepvideo': False,
        }
        
        if not os.path.exists('downloads'):
            os.makedirs('downloads')
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            
            # تغيير الامتداد إذا كان لا يزال بصيغة فيديو
            if file_path.endswith(('.webm', '.m4a', '.opus')):
                new_path = file_path.rsplit('.', 1)[0] + '.mp3'
                os.rename(file_path, new_path)
                file_path = new_path
            
            await q.message.edit_text("📤 جاري إرسال الصوت...")
            
            # إرسال الملف كما هو (حتى لو كان m4a أو opus)
            with open(file_path, 'rb') as audio_file:
                await context.bot.send_audio(
                    chat_id=user_id,
                    audio=audio_file,
                    caption=f"🎵 {info.get('title', 'تم التحميل')}\n\n📁 المطور: {CREATER_USERNAME}"
                )
            
            try:
                os.remove(file_path)
            except:
                pass
            
            await q.message.edit_text("✅ تم تحميل الصوت بنجاح!")
            
    except Exception as e:
        print(f"Error downloading audio: {e}")
        await q.message.edit_text(f"❌ حصل خطأ في تحميل الصوت:\n{str(e)}")InlineKeyboardButton("4K UHD", callback_data="q_2160")],
            [InlineKeyboardButton("8K 🔥", callback_data="q_4320")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await q.message.edit_text("🎯 اختر الجودة المناسبة:", reply_markup=reply_markup)

async def quality_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    
    if not await check_subscription(context.bot, user_id):
        await q.message.reply_text("⚠️ لازم تشترك في القنوات الأول!")
        return
    
    quality = q.data.replace("q_", "")
    url = context.user_data.get("link")
    
    if not url:
        await q.message.edit_text("❌ مفيش لينك للتحميل!")
        return
    
    try:
        await q.message.edit_text(f"⏬ جاري تحميل الفيديو بجودة {quality}p...")
        
        quality_map = {
            '144': 'best[height<=144]',
            '240': 'best[height<=240]',
            '360': 'best[height<=360]',
            '480': 'best[height<=480]',
            '720': 'best[height<=720]',
            '1080': 'best[height<=1080]',
            '1440': 'best[height<=1440]',
            '2160': 'best[height<=2160]',
            '4320': 'best[height<=4320]'
        }
        
        format_string = quality_map.get(quality, 'best')
        
        ydl_opts = {
            'format': format_string,
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
        }
        
        if not os.path.exists('downloads'):
            os.makedirs('downloads')
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            
            await q.message.edit_text("📤 جاري إرسال الفيديو...")
            
            file_size = os.path.getsize(file_path)
            if file_size > 50 * 1024 * 1024:
                await q.message.edit_text("❌ حجم الفيديو كبير جداً (أكثر من 50MB) ولا يمكن إرساله على تليجرام.")
            else:
                with open(file_path, 'rb') as video_file:
                    await context.bot.send_video(
                        chat_id=user_id,
                        video=video_file,
                        caption=f"🎬 {info.get('title', 'تم التحميل')}\n\n📁 المطور: {CREATER_USERNAME}"
                    )
            
            try:
                os.remove(file_path)
            except:
                pass
            
            await q.message.edit_text("✅ تم تحميل الفيديو بنجاح!")
            
    except Exception as e:
        print(f"Error downloading video: {e}")
        await q.message.edit_text(f"❌ حصل خطأ في تحميل الفيديو:\n{str(e)}")

def main():
    print("🚀 بدء تشغيل البوت...")
    print(f"🔑 التوكن: {'موجود' if BOT_TOKEN else 'ناقص'}")
    
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("panel", panel))
    application.add_handler(CommandHandler("search", search))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    
    application.add_handler(CallbackQueryHandler(panel_callbacks, pattern="^panel_"))
    application.add_handler(CallbackQueryHandler(remove_channel_callback, pattern="^remove_ch_"))
    application.add_handler(CallbackQueryHandler(check_subscription_callback, pattern="^check_sub$"))
    application.add_handler(CallbackQueryHandler(search_select, pattern="^vid_"))
    application.add_handler(CallbackQueryHandler(format_choice, pattern="^format_"))
    application.add_handler(CallbackQueryHandler(quality_choice, pattern="^q_"))
    
    print("✅ تم تحميل جميع handlers")
    print("🤖 البوت شغال...")
    
    application.run_polling()

if __name__ == "__main__":
    main()
