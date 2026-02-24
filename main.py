import telebot
from telebot import types
import sqlite3
import random

TOKEN = '8609558089:AAExgvs1_XR5jlj9RGC55zZStvc7nV_Z6hE'
bot = telebot.TeleBot(TOKEN)
ADMIN_ID = 8299021738

# --- BAZA BILAN ISHLASH ---
def init_db():
    conn = sqlite3.connect('casino.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, lang TEXT, balance REAL)''')
    conn.commit()
    conn.close()

init_db()

# --- RO'YXATDAN O'TISH BOSQICHLARI ---
user_data = {}

@bot.message_handler(commands=['start'])
def start(message):
    conn = sqlite3.connect('casino.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id=?", (message.from_user.id,))
    user = cursor.fetchone()
    conn.close()

    if user:
        main_menu(message)
    else:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="lang_uz"),
                   types.InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"))
        bot.send_message(message.chat.id, "Tilni tanlang / Выберите язык:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("lang_"))
def set_lang(call):
    lang = call.data.split("_")[1]
    user_data[call.from_user.id] = {'lang': lang}
    bot.edit_message_text("Ism va familiyangizni kiriting:", call.message.chat.id, call.message.message_id)
    bot.register_next_step_handler(call.message, get_name)

def get_name(message):
    user_data[message.from_user.id]['name'] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("📞 Raqamni yuborish", request_contact=True))
    bot.send_message(message.chat.id, "Telefon raqamingizni yuboring:", reply_markup=markup)
    bot.register_next_step_handler(message, get_phone)

def get_phone(message):
    if message.contact:
        phone = message.contact.phone_number
        uid = message.from_user.id
        data = user_data[uid]
        
        conn = sqlite3.connect('casino.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?)", (uid, data['name'], phone, data['lang'], 100.0))
        conn.commit()
        conn.close()
        
        bot.send_message(message.chat.id, "✅ Ro'yxatdan o'tdingiz! Sizga 100$ bonus berildi.")
        main_menu(message)

def main_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🎰 O'yin (50/50)", "👤 Profil", "ℹ️ Ma'lumot")
    if message.from_user.id == ADMIN_ID:
        markup.add("💰 Admin: Pul qo'shish")
    bot.send_message(message.chat.id, "Asosiy menyu:", reply_markup=markup)

@bot.message_handler(func=lambda message: True)
def handle_all(message):
    uid = message.from_user.id
    if message.text == "🎰 O'yin (50/50)":
        # 50% foyda algoritmi
        chance = random.randint(1, 100)
        conn = sqlite3.connect('casino.db')
        cursor = conn.cursor()
        
        if chance <= 50: # 50% yutqazish (Siz foydasiz)
            cursor.execute("UPDATE users SET balance = balance - 10 WHERE id=?", (uid,))
            bot.send_message(message.chat.id, "📉 Afsus, yutqazdingiz! -10$")
        else: # 50% yutish (Foydalanuvchi yutadi)
            cursor.execute("UPDATE users SET balance = balance + 10 WHERE id=?", (uid,))
            bot.send_message(message.chat.id, "🎉 Tabriklayman! +10$ yutdingiz!")
        
        conn.commit()
        conn.close()

    elif message.text == "👤 Profil":
        conn = sqlite3.connect('casino.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name, balance FROM users WHERE id=?", (uid,))
        user = cursor.fetchone()
        conn.close()
        bot.send_message(message.chat.id, f"👤 Ism: {user[0]}\n💰 Balans: {user[1]}$")

    elif message.text == "💰 Admin: Pul qo'shish" and uid == ADMIN_ID:
        conn = sqlite3.connect('casino.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance = balance + 5000 WHERE id=?", (uid,))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, "✅ Admin hisobiga 5000$ qo'shildi!")

bot.polling(none_stop=True)
        
    
  
