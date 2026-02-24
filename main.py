import telebot
from telebot import types
import sqlite3
import random
import time
from datetime import datetime, timedelta

TOKEN = '8609558089:AAExgvs1_XR5jlj9RGC55zZStvc7nV_Z6hE'
bot = telebot.TeleBot(TOKEN)
ADMIN_ID = 8299021738
KARTA_RAQAM = "9860 6067 5582 9722"

# --- BAZA BILAN ISHLASH ---
def get_db_connection():
    conn = sqlite3.connect('casino_uzb.db', check_same_thread=False)
    return conn

conn = get_db_connection()
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                  (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, 
                   balance REAL DEFAULT 0, debt REAL DEFAULT 0, 
                   last_debt_time TEXT, total_dep REAL DEFAULT 0, joined_at TEXT)''')
conn.commit()

# --- JARIMA VA OGOHLANTIRISH TIZIMI ---
def apply_punishment(uid):
    cursor.execute("SELECT debt, last_debt_time, name, phone FROM users WHERE id=?", (uid,))
    res = cursor.fetchone()
    if res and res[0] > 0 and res[1]:
        debt, last_time, name, phone = res[0], res[1], res[2], res[3]
        last_date = datetime.strptime(last_time, "%Y-%m-%d %H:%M:%S")
        now = datetime.now()
        days_passed = (now - last_date).days

        if days_passed >= 1:
            interest = debt * 0.10 * days_passed
            new_debt = debt + interest
            new_time = now.strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("UPDATE users SET debt = ?, last_debt_time = ? WHERE id=?", (new_debt, new_time, uid))
            conn.commit()
            
            warning = (f"⚠️ **DIQQAT: QARZINGIZ OSHDI!**\n\nTo'lanmagan {days_passed} kun uchun 10% dan jarima qo'shildi.\n"
                       f"Hozirgi qarz: **{new_debt:,} so'm**.\n\nAgar 12 soatda to'lamasangiz, ma'lumotlaringiz **DXX**ga topshiriladi!")
            bot.send_message(uid, warning, parse_mode="Markdown")
            bot.send_message(ADMIN_ID, f"🚨 Qarzdor OGOHLANTIRILDI: {name} ({phone})\nQarz: {new_debt:,} so'm")

# --- MENYULAR ---
def main_menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🎰 O'yinlar", "👤 Profil", "💳 Depozit", "🎁 Bonus")
    markup.add("💸 Nasiya olish", "🔴 Qarzni to'lash", "💸 Pul yechish")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    apply_punishment(uid)
    cursor.execute("SELECT * FROM users WHERE id=?", (uid,))
    if cursor.fetchone():
        bot.send_message(message.chat.id, "Xush kelibsiz!", reply_markup=main_menu(uid))
    else:
        bot.send_message(message.chat.id, "Ro'yxatdan o'tish uchun ismingizni kiriting:")
        bot.register_next_step_handler(message, get_name)

def get_name(message):
    name = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("📞 Raqamni yuborish", request_contact=True))
    bot.send_message(message.chat.id, f"Rahmat {name}, endi telefon raqamingizni yuboring:", reply_markup=markup)
    bot.register_next_step_handler(message, lambda m: save_user(m, name))

def save_user(message, name):
    if message.contact:
        uid, phone = message.from_user.id, message.contact.phone_number
        date_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, 0, 0, None, 0, ?)", (uid, name, phone, date_now))
        conn.commit()
        bot.send_message(message.chat.id, "✅ Ro'yxatdan o'tdingiz!", reply_markup=main_menu(uid))
    else:
        bot.send_message(message.chat.id, "Iltimos, tugma orqali raqam yuboring!")

# --- O'YINLAR (QUTILARI VA CRASH) ---
@bot.message_handler(func=lambda m: m.text == "🎰 O'yinlar")
def games_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📦 4 ta Quticha", "🚀 Crash (Samolyot)", "🔙 Orqaga")
    bot.send_message(message.chat.id, "O'yinni tanlang (Har bir o'yin 5,000 so'm):", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📦 4 ta Quticha")
def boxes(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(*[types.InlineKeyboardButton(f"📦 {i}", callback_data=f"box_{i}") for i in range(1, 5)])
    bot.send_message(message.chat.id, "Qutini tanlang:", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("box_"))
def box_res(call):
    uid = call.from_user.id
    cursor.execute("SELECT balance FROM users WHERE id=?", (uid,))
    if cursor.fetchone()[0] < 5000:
        bot.answer_callback_query(call.id, "Mablag' yetarli emas!", show_alert=True)
        return
    win = random.randint(1, 4)
    if int(call.data.split("_")[1]) == win:
        cursor.execute("UPDATE users SET balance = balance + 15000 WHERE id=?", (uid,))
        bot.edit_message_text(f"🎉 YUTDINGIZ! Yutuq {win}-qutida edi.", call.message.chat.id, call.message.message_id)
    else:
        cursor.execute("UPDATE users SET balance = balance - 5000 WHERE id=?", (uid,))
        bot.edit_message_text(f"😔 YUTQAZDINGIZ. Yutuq {win}-qutida edi.", call.message.chat.id, call.message.message_id)
    conn.commit()

# --- NASIYA VA PUL YECHISH ---
@bot.message_handler(func=lambda m: m.text == "💸 Nasiya olish")
def get_debt(message):
    bot.send_message(message.chat.id, "Qancha nasiya kerak? (Faqat son yozing):")
    bot.register_next_step_handler(message, apply_debt)

def apply_debt(message):
    try:
        amt = float(message.text)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("UPDATE users SET balance = balance + ?, debt = debt + ?, last_debt_time = ? WHERE id=?", (amt, amt, now, message.from_user.id))
        conn.commit()
        bot.send_message(message.chat.id, f"✅ {amt:,} so'm nasiya berildi.")
    except: bot.send_message(message.chat.id, "Faqat son!")

@bot.message_handler(func=lambda m: m.text == "💸 Pul yechish")
def withdraw(message):
    cursor.execute("SELECT debt FROM users WHERE id=?", (message.from_user.id,))
    if cursor.fetchone()[0] > 0:
        bot.send_message(message.chat.id, "⚠️ Qarzni to'lamasdan pul yechib bo'lmaydi!")
    else:
        bot.send_message(message.chat.id, "Pul yechish uchun @admin_user ga yozing.")

# --- ADMIN BUYRUQLARI ---
@bot.message_handler(commands=['malumot'])
def admin_data(message):
    if message.from_user.id == ADMIN_ID:
        cursor.execute("SELECT * FROM users")
        res = cursor.fetchall()
        report = "📊 **Barcha foydalanuvchilar:**\n\n"
        for u in res:
            report += f"👤 {u[1]} | 📞 {u[2]}\n💰 Balans: {u[3]:,} | 🔴 Qarz: {u[4]:,}\n" + "-"*15 + "\n"
        bot.send_message(ADMIN_ID, report, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🔙 Orqaga")
def back(message):
    bot.send_message(message.chat.id, "Bosh menyu:", reply_markup=main_menu(message.from_user.id))

@bot.message_handler(func=lambda m: m.text == "👤 Profil")
def profile(message):
    apply_punishment(message.from_user.id)
    cursor.execute("SELECT balance, debt FROM users WHERE id=?", (message.from_user.id,))
    res = cursor.fetchone()
    bot.send_message(message.chat.id, f"💰 Balans: {res[0]:,} s\n🔴 Qarz: {res[1]:,} s")

bot.polling(none_stop=True)
            
        
        
    
  
