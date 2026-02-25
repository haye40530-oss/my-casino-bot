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

users = {}

def get_user(uid):
    if uid not in users:
        users[uid] = {
            'reg': False, 'name': '', 'phone': '', 'age': '', 
            'balance': 0, 'loan': 0, 'loan_time': None, 
            'deposit': 0, 'notified': False, 'referrals': 0
        }
    return users[uid]

# --- ASOSIY MENYU ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎰 777 O'yini", "💰 Balans")
    markup.row("💳 Depozit qilish", "💸 Qarz olish")
    markup.row("🏦 Qarzni to'lash", "👥 Do'stlar")
    markup.row("ℹ️ Ma'lumot") # Yangi menyu
    return markup

# --- 1. RO'YXATDAN O'TISH (YOSH BILAN) ---
@bot.message_handler(commands=['start'])
def start(message):
    user = get_user(message.chat.id)
    if not user['reg']:
        msg = bot.send_message(message.chat.id, "👋 Xush kelibsiz! To'liq ismingizni yozing:")
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
    if age and 10 <= int(age) <= 100:
        user['age'] = age
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(types.KeyboardButton("📱 Raqam yuborish", request_contact=True))
        msg = bot.send_message(message.chat.id, "Telefon raqamingizni yuboring:", reply_markup=markup)
        bot.register_next_step_handler(msg, reg_phone)
    else:
        msg = bot.send_message(message.chat.id, "Iltimos, yoshingizni to'g'ri raqamlarda yozing:")
        bot.register_next_step_handler(msg, reg_age)

def reg_phone(message):
    user = get_user(message.chat.id)
    if message.contact:
        user['phone'] = message.contact.phone_number
        user['reg'] = True
        bot.send_message(message.chat.id, "✅ Ro'yxatdan o'tdingiz!", reply_markup=main_menu())
        bot.send_message(ADMIN_ID, f"🆕 Yangi foydalanuvchi:\n👤 {user['name']}\n🎂 Yosh: {user['age']}\n📞 {user['phone']}")
    else:
        msg = bot.send_message(message.chat.id, "Tugmani bosing!")
        bot.register_next_step_handler(msg, reg_phone)

# --- 2. QARZ OLISH (QAT'IY CHEKLOV) ---
@bot.message_handler(func=lambda m: m.text == "💸 Qarz olish")
def loan_start(message):
    user = get_user(message.chat.id)
    # 1-Qoida: Qarz to'lanmaguncha yangi qarz olish man etiladi
    if user['loan'] > 0:
        bot.send_message(message.chat.id, "⚠️ **DIQQAT!** Sizda yopilmagan qarz bor. Avvalgi qarzni to'lamagunizcha yangi qarz olish qat'iyan man etiladi!")
        return
    
    msg = bot.send_message(message.chat.id, "💰 Qancha qarz olasiz? (100,000 - 1,000,000):")
    bot.register_next_step_handler(msg, loan_process)

def loan_process(message):
    if message.text in ["🎰 777 O'yini", "💰 Balans", "ℹ️ Ma'lumot"]: # Tugma bosilsa bekor qilish
        bot.send_message(message.chat.id, "Bekor qilindi.", reply_markup=main_menu())
        return
    try:
        amt = int(re.sub(r'\D', '', message.text))
        if 100000 <= amt <= 1000000:
            user = get_user(message.chat.id)
            user['loan'] = amt
            user['balance'] += amt
            user['loan_time'] = datetime.now()
            user['notified'] = False
            bot.send_message(message.chat.id, f"✅ {amt:,} UZS qarz berildi!")
        else:
            msg = bot.send_message(message.chat.id, "❌ Limit: 100k-1mln. Qayta yozing:")
            bot.register_next_step_handler(msg, loan_process)
    except:
        msg = bot.send_message(message.chat.id, "⚠️ Faqat raqam yozing!")
        bot.register_next_step_handler(msg, loan_process)

# --- 3. MA'LUMOT MENYUSI (USER VA ADMIN UCHUN) ---
@bot.message_handler(func=lambda m: m.text == "ℹ️ Ma'lumot")
def info_menu(message):
    user = get_user(message.chat.id)
    
    # AGAR ADMIN BOSSA: Hamma foydalanuvchilar ro'yxati
    if message.chat.id == ADMIN_ID:
        full_info = "👥 **BARCHA FOYDALANUVCHILAR:**\n\n"
        for uid, u in users.items():
            if u['reg']:
                full_info += f"👤 Ism: {u['name']}\n🎂 Yosh: {u['age']}\n📞 Tel: {u['phone']}\n💰 Balans: {u['balance']:,}\n💸 Qarz: {u['loan']:,}\n\n"
        bot.send_message(ADMIN_ID, full_info if len(users) > 0 else "Hali hech kim yo'q.")
    
    # AGAR FOYDALANUVCHI BOSSA: Faqat o'zining ma'lumotlari
    else:
        my_info = (f"👤 **SIZNING MA'LUMOTLARINGIZ:**\n"
                   f"━━━━━━━━━━━━━━━\n"
                   f"🆔 ID: `{message.chat.id}`\n"
                   f"👨 Ism: {user['name']}\n"
                   f"🎂 Yosh: {user['age']}\n"
                   f"📞 Tel: {user['phone']}\n"
                   f"💰 Balans: {user['balance']:,} UZS\n"
                   f"💸 Qarz: {user['loan']:,} UZS\n"
                   f"👥 Takliflar: {user['referrals']} ta")
        bot.send_message(message.chat.id, my_info, parse_mode="Markdown")

# --- QARZNI AVTOMAT TEKSHIRISH (12 soatdan keyin xabar) ---
def check_loans():
    while True:
        now = datetime.now()
        for uid, u in users.items():
            if u['loan'] > 0 and u['loan_time']:
                if now - u['loan_time'] > timedelta(hours=12) and not u['notified']:
                    try:
                        bot.send_message(uid, "⚠️ **DIQQAT!** Qarz muddati o'tdi. Har soat uchun 5% penya hisoblanmoqda!")
                        u['notified'] = True
                    except: pass
        time.sleep(60)

threading.Thread(target=check_loans, daemon=True).start()

bot.polling(none_stop=True)
    
    
        
       

    
            
        
        
    
  
