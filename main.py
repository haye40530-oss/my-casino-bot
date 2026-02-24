import telebot
from telebot import types
import sqlite3
import random

TOKEN = '8609558089:AAExgvs1_XR5jlj9RGC55zZStvc7nV_Z6hE'
bot = telebot.TeleBot(TOKEN)
ADMIN_ID = 8299021738
KARTA_RAQAM = "8600 0000 0000 0000" # O'z kartangizni yozing

def init_db():
    conn = sqlite3.connect('casino_uzb.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (id INTEGER PRIMARY KEY, name TEXT, balance REAL DEFAULT 0, last_bonus TEXT)''')
    conn.commit()
    conn.close()

init_db()

def main_menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🎰 O'yinlar", "👤 Profil", "💳 Depozit", "🎁 Kunlik Bonus")
    markup.add("💸 Pul yechish")
    if uid == ADMIN_ID:
        markup.add("📊 Statistika")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    conn = sqlite3.connect('casino_uzb.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id=?", (message.from_user.id,))
    if cursor.fetchone():
        bot.send_message(message.chat.id, "Xush kelibsiz!", reply_markup=main_menu(message.from_user.id))
    else:
        bot.send_message(message.chat.id, "Ro'yxatdan o'tish uchun ismingizni yozing:")
        bot.register_next_step_handler(message, save_user)
    conn.close()

def save_user(message):
    uid = message.from_user.id
    name = message.text
    conn = sqlite3.connect('casino_uzb.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (id, name, balance) VALUES (?, ?, ?)", (uid, name, 0))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, "Ro'yxatdan o'tdingiz!", reply_markup=main_menu(uid))

# --- TASODIFIY BONUS TIZIMI ---
@bot.message_handler(func=lambda m: m.text == "🎁 Kunlik Bonus")
def get_bonus(message):
    uid = message.from_user.id
    # Siz so'ragan limitlar: 5,000 dan 10,000 so'mgacha
    bonus_amount = random.randint(5000, 10000)
    
    conn = sqlite3.connect('casino_uzb.db')
    cursor = conn.cursor()
    
    # Balansni yangilash
    cursor.execute("UPDATE users SET balance = balance + ? WHERE id=?", (bonus_amount, uid))
    conn.commit()
    conn.close()
    
    bot.send_message(message.chat.id, f"🎁 Tabriklaymiz! Sizga {bonus_amount:,} so'm bonus berildi!")

# --- DEPOZIT VA ADMIN TASDIQLASH ---
@bot.message_handler(func=lambda m: m.text == "💳 Depozit")
def deposit(message):
    bot.send_message(message.chat.id, "Qancha depozit qilmoqchisiz? (Min: 10 000, Max: 10 000 000 so'm)")
    bot.register_next_
        
        
    
  
