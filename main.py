import telebot
from telebot import types
import re
import threading
import time
from datetime import datetime, timedelta

# --- KONFIGURATSIYA ---
TOKEN = '8609558089:AAExgvs1_XR5jlj9RGC55zZStvc7nV_Z6hE'
ADMIN_ID = 8299021738  # Sizning yangi ID raqamingiz
ADMIN_USER = "@Vebiy_001" # Sizning usernameingiz
ADMIN_KARTA = "9860 6067 5582 9722"
bot = telebot.TeleBot(TOKEN)

users = {}

def get_user(uid):
    if uid not in users:
        users[uid] = {
            'reg': False, 'name': '', 'phone': '', 'age': 0,
            'balance': 0, 'loan': 0, 'loan_time': None, 
            'deposit': 0, 'last_scare': None, 'referrals': 0
        }
    return users[uid]

# --- 1. BALANS VA PENYA HISOBLASH ---
def get_balance_info(uid):
    user = get_user(uid)
    penya = 0
    total_to_pay = user['loan']
    
    if user['loan'] > 0 and user['loan_time']:
        passed = datetime.now() - user['loan_time']
        hours = int(passed.total_seconds() // 3600)
        
        if hours > 12:
            # 12 soatdan keyin har 1 soat uchun 5% penya
            penya_hours = hours - 12
            penya = int(user['loan'] * 0.05 * penya_hours)
            total_to_pay += penya
            
    return user['balance'], user['loan'], penya, total_to_pay

# --- 2. QO'RQITISH TIZIMI (HAR 2 SOATDA) ---
def scare_system():
    while True:
        now = datetime.now()
        for uid, u in users.items():
            if u['loan'] > 0 and u['loan_time']:
                passed = now - u['loan_time']
                if passed > timedelta(hours=12):
                    if not u['last_scare'] or (now - u['last_scare']) > timedelta(hours=2):
                        try:
                            msg = ("🛑 **DIQQAT: MUDDAT O'TDI!**\n\n"
                                   "Sizning qarzni qaytarish vaqtingiz tugagan! ⚠️\n"
                                   "Hozirda har soatda **5% penya** qo'shilmoqda.\n\n"
                                   "Agar qarzni darhol to'lamasangiz, profilingiz bloklanadi va ma'lumotlaringiz adminga topshiriladi!")
                            bot.send_message(uid, msg, parse_mode="Markdown")
                            u['last_scare'] = now
                        except: pass
        time.sleep(60)

threading.Thread(target=scare_system, daemon=True).start()

# --- 3. MENYULAR ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎰 777 O'yini", "💰 Balans")
    markup.row("💳 Depozit qilish", "💸 Qarz olish")
    markup.row("🏦 Qarzni to'lash", "ℹ️ Ma'lumot")
    return markup

# --- 4. ASOSIY FUNKSIYALAR ---
@bot.message_handler(func=lambda m: m.text == "💰 Balans")
def bal_view(message):
    b, l, p, total = get_balance_info(message.chat.id)
    text = (f"💰 **Sizning hisobingiz:**\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💵 Naqd balans: {b:,} UZS\n"
            f"💸 Asosiy qarz: {l:,} UZS\n"
            f"⚠️ To'plangan penya: {p:,} UZS\n"
            f"🚀 Jami to'lanishi kerak: **{total:,} UZS**")
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🏦 Qarzni to'lash")
def pay_loan(message):
    b, l, p, total = get_balance_info(message.chat.id)
    if l == 0:
        bot.send_message(message.chat.id, "✅ Sizning qarzingiz yo'q!")
        return
    
    if b >= total:
        user = get_user(message.chat.id)
        user['balance'] -= total
        user['loan'] = 0
        user['loan_time'] = None
        bot.send_message(message.chat.id, f"✅ Qarz to'liq yopildi! Balansdan {total:,} UZS ayirildi.")
    else:
        bot.send_message(message.chat.id, f"❌ Balansda mablag' yetarli emas!\nTo'lash uchun: {total:,} UZS kerak.\nBalansingiz: {b:,} UZS.\n\nIltimos, depozit orqali balansni to'ldiring.")

@bot.message_handler(func=lambda m: m.text == "💸 Qarz olish")
def loan_start(message):
    user = get_user(message.chat.id)
    if user['loan'] > 0:
        bot.send_message(message.chat.id, "⚠️ Sizda to'lanmagan qarz bor! Avvalgisini to'lamasdan yangi qarz olish taqiqlanadi.")
        return
    
    text = ("📜 **QARZ SHARTLARI:**\n"
            "- 12 soatgacha: 0%\n"
            "- 12 soatdan keyin: Har soatda +5%\n"
            "- To'lanmasa: Har 2 soatda ogohlantirish.\n\n"
            "Summani kiriting (100k - 1mln):")
    msg = bot.send_message(message.chat.id, text, parse_mode="Markdown")
    bot.register_next_step_handler(msg, loan_process)

def loan_process(message):
    try:
        amt = int(re.sub(r'\D', '', message.text))
        if 100000 <= amt <= 1000000:
            user = get_user(message.chat.id)
            user['loan'] = amt
            user['balance'] += amt
            user['loan_time'] = datetime.now()
            bot.send_message(message.chat.id, f"✅ {amt:,} UZS qarz berildi. 12 soat ichida qaytaring!")
        else: bot.send_message(message.chat.id, "❌ Limit 100,000 - 1,000,000 UZS.")
    except: bot.send_message(message.chat.id, "⚠️ Faqat raqam yozing!")

# --- 5. ADMIN VA MA'LUMOT ---
@bot.message_handler(func=lambda m: m.text == "ℹ️ Ma'lumot")
def info_btn(message):
    user = get_user(message.chat.id)
    if message.chat.id == ADMIN_ID:
        text = f"💎 **ADMIN PANEL**\nFoydalanuvchilar: {len(users)}\nAdmin: {ADMIN_USER}\n\n/statistika - Jami ma'lumot\n/qarzdorlar - Qarzdorlar ro'yxati"
        bot.send_message(ADMIN_ID, text)
    else:
        text = f"👤 Ism: {user['name']}\n🎂 Yosh: {user['age']}\n📞 Tel: {user['phone']}\n💰 Balans: {user['balance']:,}"
        bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['statistika'])
def admin_stat(message):
    if message.chat.id == ADMIN_ID:
        total_loans = sum(u['loan'] for u in users.values())
        bot.send_message(ADMIN_ID, f"📊 Jami foydalanuvchilar: {len(users)}\n💸 Jami qarzlar: {total_loans:,} UZS")

# --- RO'YXATDAN O'TISH ---
@bot.message_handler(commands=['start'])
def welcome(message):
    user = get_user(message.chat.id)
    if not user['reg']:
        msg = bot.send_message(message.chat.id, "👋 Salom! Ismingizni yozing:")
        bot.register_next_step_handler(msg, reg_name)
    else: bot.send_message(message.chat.id, "Asosiy menyu:", reply_markup=main_menu())

def reg_name(message):
    user = get_user(message.chat.id)
    user['name'] = message.text
    msg = bot.send_message(message.chat.id, "Yoshingizni yozing:")
    bot.register_next_step_handler(msg, reg_age)

def reg_age(message):
    user = get_user(message.chat.id)
    user['age'] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("📲 Raqam yuborish", request_contact=True))
    msg = bot.send_message(message.chat.id, "Raqamingizni yuboring:", reply_markup=markup)
    bot.register_next_step_handler(msg, reg_phone)

def reg_phone(message):
    user = get_user(message.chat.id)
    if message.contact:
        user['phone'] = message.contact.phone_number
        user['reg'] = True
        bot.send_message(message.chat.id, "✅ Ro'yxatdan o'tdingiz!", reply_markup=main_menu())
    else: bot.register_next_step_handler(bot.send_message(message.chat.id, "Tugmani bosing!"), reg_phone)

bot.polling(none_stop=True)

    
    
            
        
        
    
  
