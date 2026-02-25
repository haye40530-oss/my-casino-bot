import telebot
from telebot import types
import re
import threading
import time
from datetime import datetime, timedelta

# --- KONFIGURATSIYA ---
TOKEN = '8609558089:AAExgvs1_XR5jlj9RGC55zZStvc7nV_Z6hE'
ADMIN_ID = 8299021738 
ADMIN_KARTA = "9860 6067 5582 9722"
bot = telebot.TeleBot(TOKEN)

# Foydalanuvchilar lug'ati
users = {}

def get_user(uid):
    if uid not in users:
        users[uid] = {
            'reg': False, 'name': '', 'phone': '', 'age': 0,
            'balance': 0, 'loan': 0, 'loan_time': None, 
            'deposit': 0, 'notified': False, 'referrals': 0, 'game_count': 0
        }
    return users[uid]

# --- ASOSIY MENYU ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎰 777 O'yini", "💰 Balans")
    markup.row("💳 Depozit qilish", "💸 Qarz olish")
    markup.row("🏦 Qarzni to'lash", "👥 Do'stlar")
    markup.row("ℹ️ Ma'lumot")
    return markup

# --- 1. RO'YXATDAN O'TISH (YOSH SO'ROVI BILAN) ---
@bot.message_handler(commands=['start'])
def start(message):
    user = get_user(message.chat.id)
    if not user['reg']:
        msg = bot.send_message(message.chat.id, "👋 Salom! To'liq ismingizni yozing:")
        bot.register_next_step_handler(msg, reg_name)
    else:
        bot.send_message(message.chat.id, "Asosiy menyu:", reply_markup=main_menu())

def reg_name(message):
    user = get_user(message.chat.id)
    user['name'] = message.text
    msg = bot.send_message(message.chat.id, "Yoshingizni kiriting:")
    bot.register_next_step_handler(msg, reg_age)

def reg_age(message):
    user = get_user(message.chat.id)
    age = re.sub(r'\D', '', message.text)
    if age and 10 < int(age) < 100:
        user['age'] = int(age)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(types.KeyboardButton("📱 Raqam yuborish", request_contact=True))
        msg = bot.send_message(message.chat.id, "Telefon raqamingizni yuboring:", reply_markup=markup)
        bot.register_next_step_handler(msg, reg_phone)
    else:
        msg = bot.send_message(message.chat.id, "⚠️ Yoshingizni to'g'ri (raqamda) kiriting:")
        bot.register_next_step_handler(msg, reg_age)

def reg_phone(message):
    user = get_user(message.chat.id)
    if message.contact:
        user['phone'] = message.contact.phone_number
        user['reg'] = True
        bot.send_message(message.chat.id, "✅ Ro'yxatdan o'tdingiz!", reply_markup=main_menu())
        bot.send_message(ADMIN_ID, f"🆕 Yangi user: {user['name']}\n🎂 Yosh: {user['age']}\n📞 {user['phone']}")
    else:
        msg = bot.send_message(message.chat.id, "Iltimos, tugmani bosing!")
        bot.register_next_step_handler(msg, reg_phone)

# --- 2. DEPOZIT QILISH (TASDIQLASH BILAN) ---
@bot.message_handler(func=lambda m: m.text == "💳 Depozit qilish")
def dep_start(message):
    bot.send_message(message.chat.id, f"💳 Karta: `{ADMIN_KARTA}`\nTo'lovdan so'ng summani yozing:", parse_mode="Markdown")
    bot.register_next_step_handler(message, dep_process)

def dep_process(message):
    if message.text in ["🎰 777 O'yini", "💰 Balans", "💳 Depozit qilish", "💸 Qarz olish"]:
        bot.send_message(message.chat.id, "Bekor qilindi.", reply_markup=main_menu())
        return
    try:
        amt = int(re.sub(r'\D', '', message.text))
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ TASDIQLASH", callback_data=f"dep_ok_{message.chat.id}_{amt}"),
                   types.InlineKeyboardButton("❌ RAD ETISH", callback_data=f"dep_no_{message.chat.id}"))
        bot.send_message(ADMIN_ID, f"💳 Depozit: {message.chat.id}\n💰 Summa: {amt:,} UZS", reply_markup=markup)
        bot.send_message(message.chat.id, "⌛️ Tasdiqlash kutilmoqda...")
    except:
        msg = bot.send_message(message.chat.id, "⚠️ Summani raqamda yozing:")
        bot.register_next_step_handler(msg, dep_process)

# --- 3. QARZ OLISH (QAT'IY CHEKLOV) ---
@bot.message_handler(func=lambda m: m.text == "💸 Qarz olish")
def loan_start(message):
    user = get_user(message.chat.id)
    if user['loan'] > 0:
        bot.send_message(message.chat.id, "⚠️ Sizda to'lanmagan qarz bor! Yangi qarz olish taqiqlanadi.")
        return
    msg = bot.send_message(message.chat.id, "💰 Qancha qarz olasiz? (100,000 - 1,000,000):")
    bot.register_next_step_handler(msg, loan_final)

def loan_final(message):
    try:
        amt = int(re.sub(r'\D', '', message.text))
        if 100000 <= amt <= 1000000:
            user = get_user(message.chat.id)
            user['loan'] = amt
            user['balance'] += amt
            user['loan_time'] = datetime.now()
            bot.send_message(message.chat.id, f"✅ {amt:,} UZS berildi. 12 soatda qaytaring!")
        else:
            bot.send_message(message.chat.id, "❌ Limit: 100k-1mln.")
    except:
        bot.send_message(message.chat.id, "⚠️ Raqam yozing.")

# --- 4. MA'LUMOT (ADMIN VA USER UCHUN) ---
@bot.message_handler(func=lambda m: m.text == "ℹ️ Ma'lumot")
def info_btn(message):
    if message.chat.id == ADMIN_ID:
        text = "👥 **BARCHA USERLAR:**\n\n"
        for uid, u in users.items():
            if u['reg']:
                text += f"👤 {u['name']} | 🎂 {u['age']} | 📞 {u['phone']}\n💰 Balans: {u['balance']:,} | 💸 Qarz: {u['loan']:,}\n\n"
        bot.send_message(ADMIN_ID, text if len(users) > 0 else "Bo'sh.")
    else:
        u = get_user(message.chat.id)
        text = f"👤 Ism: {u['name']}\n🎂 Yosh: {u['age']}\n💰 Balans: {u['balance']:,}\n💸 Qarz: {u['loan']:,}"
        bot.send_message(message.chat.id, text)

# --- 5. CALLBACKLAR (TASDIQLASH) ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("dep_"))
def dep_callback(call):
    data = call.data.split("_")
    uid = int(data[2])
    if data[1] == "ok":
        amt = int(data[3])
        users[uid]['balance'] += amt
        users[uid]['deposit'] += amt
        bot.send_message(uid, f"✅ Depozit tasdiqlandi! +{amt:,} UZS")
        bot.edit_message_text("✅ Tasdiqlandi", call.message.chat.id, call.message.message_id)
    else:
        bot.send_message(uid, "❌ Depozit rad etildi.")
        bot.edit_message_text("❌ Rad etildi", call.message.chat.id, call.message.message_id)

bot.polling(none_stop=True)

    
    
        
       

    
            
        
        
    
  
