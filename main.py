import telebot
from telebot import types
import sqlite3
import random
import time
from datetime import datetime

# --- KONFIGURATSIYA ---
TOKEN = '8609558089:AAExgvs1_XR5jlj9RGC55zZStvc7nV_Z6hE'
bot = telebot.TeleBot(TOKEN)
ADMIN_ID = 8299021738
KARTA_RAQAM = "9860 6067 5582 9722"

def db_op(query, params=(), is_select=False):
    conn = sqlite3.connect('casino_uzb.db', check_same_thread=False, timeout=30)
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        if is_select: return cursor.fetchall()
        conn.commit()
    except Exception as e: print(f"Xato: {e}")
    finally: conn.close()

# Jadvallar
db_op('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, balance REAL DEFAULT 5000, debt REAL DEFAULT 0)''')
db_op('''CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, type TEXT, date TEXT)''')

def main_menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🎰 Slot (100k)", "🎯 Dart (50k)", "🏀 Basket (50k)")
    markup.add("👤 Profil", "🏆 Reyting", "📜 Tarix")
    markup.add("💸 Nasiya", "💳 To'lov")
    if uid == ADMIN_ID: markup.add("📊 Admin: Info")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    user = db_op("SELECT id FROM users WHERE id=?", (uid,), is_select=True)
    if user:
        bot.send_message(message.chat.id, "💰 Xush kelibsiz! Omad yoringiz bo'lsin!", reply_markup=main_menu(uid))
    else:
        bot.send_message(message.chat.id, "Ismingizni kiriting:")
        bot.register_next_step_handler(message, get_name)

def get_name(message):
    name = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("📞 Raqamni yuborish", request_contact=True))
    bot.send_message(message.chat.id, f"Salom {name}, raqamingizni yuboring:", reply_markup=markup)
    bot.register_next_step_handler(message, save_user, name)

def save_user(message, name):
    if message.contact:
        db_op("INSERT OR IGNORE INTO users (id, name, phone, balance) VALUES (?, ?, ?, 10000)", (message.from_user.id, name, message.contact.phone_number))
        bot.send_message(message.chat.id, "✅ Ro'yxatdan o'tdingiz! 10,000 s bonus berildi.", reply_markup=main_menu(message.from_user.id))

@bot.message_handler(func=lambda m: True)
def main_handler(message):
    uid = message.from_user.id
    text = message.text

    if text == "🎰 Slot (100k)":
        play_dice(message, '🎰', [1, 22, 43, 64], 100000, 500000)
    elif text == "🎯 Dart (50k)":
        play_dice(message, '🎯', [6, 5], 50000, 150000)
    elif text == "🏀 Basket (50k)":
        play_dice(message, '🏀', [4, 5], 50000, 120000)
    elif text == "👤 Profil":
        u = db_op("SELECT balance, debt FROM users WHERE id=?", (uid,), is_select=True)
        bot.send_message(message.chat.id, f"👤 **PROFIL**\n💰 Balans: {u[0][0]:,} s\n🔴 Qarz: {u[0][1]:,} s")
    elif text == "📜 Tarix":
        h = db_op("SELECT amount, type, date FROM history WHERE user_id=? ORDER BY id DESC LIMIT 5", (uid,), is_select=True)
        res = "📜 Oxirgi amallar:\n" + ("\n".join([f"{i[2]}: {i[0]:,} s ({i[1]})" for i in h]) if h else "Hali ma'lumot yo'q")
        bot.send_message(message.chat.id, res)
    elif text == "🏆 Reyting":
        top = db_op("SELECT name, balance FROM users ORDER BY balance DESC LIMIT 10", is_select=True)
        res = "🏆 **ENG BOY O'YINCHILAR:**\n\n"
        for i, u in enumerate(top, 1): res += f"{i}. {u[0]} — {u[1]:,} s\n"
        bot.send_message(message.chat.id, res)
    elif text == "💸 Nasiya":
        bot.send_message(message.chat.id, "Summani yozing:")
        bot.register_next_step_handler(message, set_debt)
    elif text == "💳 To'lov":
        bot.send_message(message.chat.id, f"Karta: `{KARTA_RAQAM}`\nTo'lov summasini yozing:")
        bot.register_next_step_handler(message, pay_req)

def play_dice(message, emoji, win_values, cost, prize):
    uid = message.from_user.id
    u = db_op("SELECT balance FROM users WHERE id=?", (uid,), is_select=True)
    if not u or u[0][0] < cost:
        bot.send_message(message.chat.id, f"⚠️ Mablag' yetarli emas! Kamida {cost:,} s kerak.")
        return
    db_op("UPDATE users SET balance = balance - ? WHERE id=?", (cost, uid))
    msg = bot.send_dice(message.chat.id, emoji=emoji)
    time.sleep(4)
    if msg.dice.value in win_values:
        db_op("UPDATE users SET balance = balance + ? WHERE id=?", (prize, uid))
        bot.reply_to(msg, f"🔥 DAHSHT! SIZ YUTDINGIZ!\n🎁 Mukofot: {prize:,} so'm balansga qo'shildi!")
    else:
        bot.reply_to(msg, "😔 Bu safar omad kelmadi. Yana urinib ko'ring!")

def set_debt(message):
    try:
        amt = float(message.text)
        date = datetime.now().strftime("%d.%m %H:%M")
        db_op("UPDATE users SET balance = balance + ?, debt = debt + ? WHERE id=?", (amt, amt, message.from_user.id))
        db_op("INSERT INTO history (user_id, amount, type, date) VALUES (?, ?, ?, ?)", (message.from_user.id, amt, "Nasiya", date))
        bot.send_message(message.chat.id, f"✅ Hisobingizga {amt:,} s nasiya berildi.")
    except: bot.send_message(message.chat.id, "Faqat son yozing!")

def pay_req(message):
    try:
        amt = float(message.text)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"p_y_{message.from_user.id}_{amt}"), types.InlineKeyboardButton("❌ Rad etish", callback_data=f"p_n_{message.from_user.id}"))
        bot.send_message(ADMIN_ID, f"🔔 TO'LOV: {amt:,} s\nID: {message.from_user.id}", reply_markup=markup)
        bot.send_message(message.chat.id, "✅ So'rov adminga yuborildi.")
    except: bot.send_message(message.chat.id, "Xato!")

@bot.callback_query_handler(func=lambda call: True)
def calls(call):
    d = call.data.split("_")
    if d[0] == "p" and d[1] == "y":
        tid, amt = int(d[2]), float(d[3])
        date = datetime.now().strftime("%d.%m %H:%M")
        db_op("UPDATE users SET debt = CASE WHEN debt >= ? THEN debt - ? ELSE 0 END WHERE id=?", (amt, amt, tid))
        db_op("INSERT INTO history (user_id, amount, type, date) VALUES (?, ?, ?, ?)", (tid, amt, "To'lov", date))
        bot.send_message(tid, f"✅ To'lovingiz tasdiqlandi: {amt:,} s qarz yopildi.")
        bot.edit_message_text(f"✅ Tasdiqlandi (ID: {tid})", call.message.chat.id, call.message.message_id)

bot.infinity_polling()
    



        

    
            
        
        
    
  
