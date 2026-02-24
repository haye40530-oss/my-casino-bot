import telebot
from telebot import types
import sqlite3
import random
from datetime import datetime

# --- KONFIGURATSIYA ---
TOKEN = '8609558089:AAExgvs1_XR5jlj9RGC55zZStvc7nV_Z6hE'
bot = telebot.TeleBot(TOKEN)
ADMIN_ID = 8299021738
KARTA_RAQAM = "9860 6067 5582 9722"

# Baza bilan xavfsiz ishlash
def execute_query(query, params=(), is_select=False):
    conn = sqlite3.connect('casino_uzb.db', check_same_thread=False, timeout=10)
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        if is_select: return cursor.fetchall()
        conn.commit()
    except Exception as e: print(f"Xato: {e}")
    finally: conn.close()

# Jadvallarni yaratish
execute_query('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, 
                  balance REAL DEFAULT 0, debt REAL DEFAULT 0, 
                  last_debt_time TEXT, user_card TEXT DEFAULT 'Kiritilmagan')''')

# Asosiy menyu tugmalari
def main_menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📦 4 ta Quticha", "💎 VIP Slot (100k)")
    markup.add("👤 Profil", "💸 Nasiya olish")
    markup.add("💳 Depozit", "🔴 Qarzni to'lash")
    markup.add("💸 Pul yechish")
    if uid == ADMIN_ID: markup.add("📊 Admin: Ma'lumot")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    user = execute_query("SELECT * FROM users WHERE id=?", (uid,), is_select=True)
    if user: bot.send_message(message.chat.id, "Xush kelibsiz!", reply_markup=main_menu(uid))
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
        execute_query("INSERT OR IGNORE INTO users (id, name, phone, balance) VALUES (?, ?, ?, 5000)", 
                      (message.from_user.id, name, message.contact.phone_number))
        bot.send_message(message.chat.id, "✅ Ro'yxatdan o'tdingiz!", reply_markup=main_menu(message.from_user.id))

@bot.message_handler(func=lambda m: True)
def main_handler(message):
    uid = message.from_user.id
    if message.text == "👤 Profil":
        u = execute_query("SELECT balance, debt FROM users WHERE id=?", (uid,), is_select=True)
        if u: bot.send_message(message.chat.id, f"💰 Balans: {u[0][0]:,} s\n🔴 Qarz: {u[0][1]:,} s")
    elif message.text == "💸 Nasiya olish":
        bot.send_message(message.chat.id, "Qancha nasiya kerak? (Faqat raqam)")
        bot.register_next_step_handler(message, set_debt)
    elif message.text == "📦 4 ta Quticha":
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(*[types.InlineKeyboardButton(f"📦 {i}-quti", callback_data=f"box_{i}") for i in range(1, 5)])
        bot.send_message(message.chat.id, "Qutini tanlang (Tikish: 5,000 s):", reply_markup=markup)

def set_debt(message):
    try:
        amt = float(message.text)
        execute_query("UPDATE users SET balance = balance + ?, debt = debt + ? WHERE id=?", (amt, amt, message.from_user.id))
        bot.send_message(message.chat.id, f"✅ {amt:,} s nasiya berildi.", reply_markup=main_menu(message.from_user.id))
    except: bot.send_message(message.chat.id, "Xato! Faqat son kiriting.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("box_"))
def box_res(call):
    uid = call.from_user.id
    user = execute_query("SELECT balance FROM users WHERE id=?", (uid,), is_select=True)
    if not user or user[0][0] < 5000:
        bot.answer_callback_query(call.id, "Mablag' yetarli emas!", show_alert=True)
        return
    # 25% yutish imkoniyati (Siz xohlagandek)
    if random.randint(1, 4) == 1:
        execute_query("UPDATE users SET balance = balance + 15000 WHERE id=?", (uid,))
        txt = "🎉 TABRIKLAYMIZ! Yutdingiz! +20,000 so'm"
    else:
        execute_query("UPDATE users SET balance = balance - 5000 WHERE id=?", (uid,))
        txt = "😔 BO'SH! Yutqazdingiz."
    bot.edit_message_text(txt, call.message.chat.id, call.message.message_id)

bot.infinity_polling()


        

    
            
        
        
    
  
