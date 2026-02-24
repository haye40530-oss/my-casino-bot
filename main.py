import telebot
from telebot import types
import sqlite3
import random
from datetime import datetime

# --- KONFIGURATSIYA ---
TOKEN = '8609558089:AAExgvs1_XR5jlj9RGC55zZStvc7nV_Z6hE'
bot = telebot.TeleBot(TOKEN, threaded=False) # Bot qotib qolmasligi uchun False
ADMIN_ID = 8299021738
KARTA_RAQAM = "9860 6067 5582 9722"

# --- BAZA BILAN ISHLASH (Xavfsiz usul) ---
def execute_query(query, params=(), is_select=False):
    conn = sqlite3.connect('casino_uzb.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute(query, params)
    if is_select:
        res = cursor.fetchone() if "LIMIT 1" in query or "WHERE id" in query else cursor.fetchall()
        conn.close()
        return res
    conn.commit()
    conn.close()

# Bazani yaratish
execute_query('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, 
                  balance REAL DEFAULT 0, debt REAL DEFAULT 0, 
                  last_debt_time TEXT, user_card TEXT)''')

# --- MENYU ---
def main_menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🎰 O'yinlar", "👤 Profil", "💳 Depozit", "🎁 Bonus")
    markup.add("💸 Nasiya olish", "🔴 Qarzni to'lash", "💸 Pul yechish")
    if uid == ADMIN_ID:
        markup.add("📊 Admin: Ma'lumot")
    return markup

# --- START VA REGISTRATSIYA ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    user = execute_query("SELECT * FROM users WHERE id=?", (uid,), is_select=True)
    
    if user:
        bot.send_message(message.chat.id, "Xush kelibsiz!", reply_markup=main_menu(uid))
    else:
        bot.send_message(message.chat.id, "Assalomu alaykum! Ismingizni kiriting:")
        bot.register_next_step_handler(message, get_name)

def get_name(message):
    if message.text in ["/start", "🔙 Orqaga"]: return
    name = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("📞 Raqamni yuborish", request_contact=True))
    bot.send_message(message.chat.id, f"Rahmat {name}! Pastdagi tugmani bosib telefon raqamingizni tasdiqlang:", reply_markup=markup)
    bot.register_next_step_handler(message, save_user, name)

def save_user(message, name):
    uid = message.from_user.id
    if message.contact:
        phone = message.contact.phone_number
        execute_query("INSERT OR IGNORE INTO users (id, name, phone, user_card) VALUES (?, ?, ?, ?)", 
                      (uid, name, phone, "Kiritilmagan"))
        bot.send_message(message.chat.id, "✅ Ro'yxatdan o'tdingiz!", reply_markup=main_menu(uid))
    else:
        # Agar foydalanuvchi tugmani bosmasa, qayta so'raymiz
        msg = bot.send_message(message.chat.id, "Iltimos, faqat tugma orqali raqamingizni yuboring!")
        bot.register_next_step_handler(msg, save_user, name)

# --- ASOSIY ISHLASH TIZIMI ---
@bot.message_handler(func=lambda m: True)
def global_handler(message):
    uid = message.from_user.id
    text = message.text

    # Profil ma'lumotlarini olish
    u = execute_query("SELECT balance, debt, name, phone, user_card FROM users WHERE id=?", (uid,), is_select=True)
    if not u: 
        start(message)
        return

    if text == "🎰 O'yinlar":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📦 4 ta Quticha", "🚀 Crash", "🔙 Orqaga")
        bot.send_message(message.chat.id, "O'yinni tanlang (5,000 so'm):", reply_markup=markup)

    elif text == "👤 Profil":
        msg = f"👤 Ism: {u[2]}\n📞 Tel: {u[3]}\n💰 Balans: {u[0]:,} s\n🔴 Qarz: {u[1]:,} s\n💳 Karta: {u[4]}"
        bot.send_message(message.chat.id, msg)

    elif text == "🔙 Orqaga":
        bot.send_message(message.chat.id, "Asosiy menyu:", reply_markup=main_menu(uid))

    elif text == "💸 Nasiya olish":
        bot.send_message(message.chat.id, "Qancha qarz (nasiya) olmoqchisiz? Miqdorni yozing:")
        bot.register_next_step_handler(message, take_debt)

    elif text == "📊 Admin: Ma'lumot" and uid == ADMIN_ID:
        users = execute_query("SELECT name, phone, debt FROM users", is_select=True)
        report = "📊 **Foydalanuvchilar:**\n"
        for user in users: report += f"👤 {user[0]} | {user[1]} | Q: {user[2]:,} s\n"
        bot.send_message(ADMIN_ID, report)

def take_debt(message):
    try:
        amt = float(message.text)
        uid = message.from_user.id
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        execute_query("UPDATE users SET balance = balance + ?, debt = debt + ?, last_debt_time = ? WHERE id=?", 
                      (amt, amt, now, uid))
        bot.send_message(message.chat.id, f"✅ {amt:,} so'm qarz berildi.", reply_markup=main_menu(uid))
    except:
        bot.send_message(message.chat.id, "Xato! Faqat raqam yozing.")

# Botni uzluksiz ishga tushirish
bot.infinity_polling(timeout=10, long_polling_timeout=5)

        
            
        
        
    
  
