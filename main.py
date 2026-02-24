
import telebot
from telebot import types
import sqlite3
import random
from datetime import datetime, timedelta

TOKEN = '8609558089:AAExgvs1_XR5jlj9RGC55zZStvc7nV_Z6hE'
bot = telebot.TeleBot(TOKEN)
ADMIN_ID = 8299021738
KARTA_RAQAM = "9860 6067 5582 9722"

def get_db_connection():
    return sqlite3.connect('casino_uzb.db', check_same_thread=False)

conn = get_db_connection()
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                  (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, 
                   balance REAL DEFAULT 0, debt REAL DEFAULT 0, 
                   last_debt_time TEXT, total_dep REAL DEFAULT 0, joined_at TEXT)''')
conn.commit()

def main_menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🎰 O'yinlar", "👤 Profil", "💳 Depozit", "🎁 Bonus")
    markup.add("💸 Nasiya olish", "💸 Pul yechish")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    cursor.execute("SELECT * FROM users WHERE id=?", (uid,))
    if cursor.fetchone():
        bot.send_message(message.chat.id, "Xush kelibsiz!", reply_markup=main_menu(uid))
    else:
        bot.send_message(message.chat.id, "Ismingizni kiriting:")
        bot.register_next_step_handler(message, get_name)

def get_name(message):
    name = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("📞 Raqamni yuborish", request_contact=True))
    bot.send_message(message.chat.id, "Telefon raqamingizni yuboring:", reply_markup=markup)
    bot.register_next_step_handler(message, lambda m: save_user(m, name))

def save_user(message, name):
    if message.contact:
        uid = message.from_user.id
        phone = message.contact.phone_number
        date_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                       (uid, name, phone, 0, 0, None, 0, date_now))
        conn.commit()
        bot.send_message(message.chat.id, "✅ Ro'yxatdan o'tdingiz!", reply_markup=main_menu(uid))
    else:
        bot.send_message(message.chat.id, "Tugmani bosing!")

# --- CHEKSIZ NASIYA TIZIMI ---
@bot.message_handler(func=lambda m: m.text == "💸 Nasiya olish")
def debt_menu(message):
    bot.send_message(message.chat.id, "Qancha nasiya olmoqchisiz? (Masalan: 10000)\nEslatma: 24 soatda to'lamasangiz ma'lumotlaringiz adminga yuboriladi!")
    bot.register_next_step_handler(message, apply_debt)

def apply_debt(message):
    try:
        amount = float(message.text)
        uid = message.from_user.id
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("UPDATE users SET balance = balance + ?, debt = debt + ?, last_debt_time = ? WHERE id=?", 
                       (amount, amount, now, uid))
        conn.commit()
        bot.send_message(message.chat.id, f"✅ {amount:,} so'm nasiya berildi. Hisobingiz: {amount:,} so'm.")
    except:
        bot.send_message(message.chat.id, "Faqat son kiriting!")

# --- QARZNI TEKSHIRISH VA PUL YECHISH ---
@bot.message_handler(func=lambda m: m.text == "💸 Pul yechish")
def withdraw(message):
    uid = message.from_user.id
    cursor.execute("SELECT debt, last_debt_time, name, phone FROM users WHERE id=?", (uid,))
    res = cursor.fetchone()
    debt, last_time, name, phone = res[0], res[1], res[2], res[3]

    if debt > 0:
        if last_time:
            debt_date = datetime.strptime(last_time, "%Y-%m-%d %H:%M:%S")
            if datetime.now() > debt_date + timedelta(hours=24):
                # 24 soat o'tgan bo'lsa adminga xabar yuborish
                bot.send_message(ADMIN_ID, f"🚨 **QARZDOR OGOHLANTIRISH!**\n👤 {name}\n📞 {phone}\n🔴 Qarz: {debt:,} so'm\n⏰ Muddat o'tgan!")
        
        bot.send_message(message.chat.id, f"⚠️ Sizning {debt:,} so'm qarzingiz bor! Uni to'lamaguncha pul yechib ololmaysiz.")
    else:
        bot.send_message(message.chat.id, "Pul yechish uchun admin @admin_user ga yozing.")

# --- ADMIN HISOBOTI ---
@bot.message_handler(commands=['malumot'])
def admin_report(message):
    if message.from_user.id == ADMIN_ID:
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()
        report = "📊 **Foydalanuvchilar:**\n"
        for u in users:
            report += f"👤 {u[1]} | 📞 {u[2]}\n💰 Balans: {u[3]:,} | 🔴 Qarz: {u[4]:,}\n" + "-"*15 + "\n"
        bot.send_message(ADMIN_ID, report, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🎰 O'yinlar")
def games(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🎲 O'ynash (5,000 so'm)", "🔙 Orqaga")
    bot.send_message(message.chat.id, "O'yinni boshlaymizmi?", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🎲 O'ynash (5,000 so'm)")
def play(message):
    uid = message.from_user.id
    cursor.execute("SELECT balance FROM users WHERE id=?", (uid,))
    balance = cursor.fetchone()[0]
    if balance < 5000:
        bot.send_message(message.chat.id, "Mablag' yetarli emas! Nasiya oling.")
        return
    if random.random() < 0.5:
        cursor.execute("UPDATE users SET balance = balance + 5000 WHERE id=?", (uid,))
        bot.send_message(message.chat.id, "🎉 +10,000 so'm!")
    else:
        cursor.execute("UPDATE users SET balance = balance - 5000 WHERE id=?", (uid,))
        bot.send_message(message.chat.id, "😔 Yutqazdingiz.")
    conn.commit()

@bot.message_handler(func=lambda m: m.text == "👤 Profil")
def profile(message):
    cursor.execute("SELECT balance, debt FROM users WHERE id=?", (message.from_user.id,))
    res = cursor.fetchone()
    bot.send_message(message.chat.id, f"💰 Balans: {res[0]:,} so'm\n🔴 Qarz: {res[1]:,} so'm")

bot.polling(none_stop=True)
    
        
        
    
  
