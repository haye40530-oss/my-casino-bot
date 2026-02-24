import telebot
from telebot import types
import sqlite3
import random

TOKEN = '8609558089:AAExgvs1_XR5jlj9RGC55zZStvc7nV_Z6hE'
bot = telebot.TeleBot(TOKEN)
ADMIN_ID = 8299021738
# Siz bergan yangi karta raqami
KARTA_RAQAM = "9860 6067 5582 9722" 

def init_db():
    conn = sqlite3.connect('casino_uzb.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (id INTEGER PRIMARY KEY, name TEXT, balance REAL DEFAULT 0)''')
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
        bot.send_message(message.chat.id, "Ro'yxatdan o'tish uchun ismingizni kiriting:")
        bot.register_next_step_handler(message, save_user)
    conn.close()

def save_user(message):
    uid = message.from_user.id
    name = message.text
    conn = sqlite3.connect('casino_uzb.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (id, name, balance) VALUES (?, ?, ?)", (uid, name, 0))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, "✅ Ro'yxatdan o'tdingiz!", reply_markup=main_menu(uid))

@bot.message_handler(func=lambda m: m.text == "🎁 Kunlik Bonus")
def get_bonus(message):
    uid = message.from_user.id
    bonus_amount = random.randint(5000, 10000)
    conn = sqlite3.connect('casino_uzb.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE id=?", (bonus_amount, uid))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, f"🎁 Tabriklaymiz! Sizga {bonus_amount:,} so'm tasodifiy bonus berildi!")

@bot.message_handler(func=lambda m: m.text == "💳 Depozit")
def deposit(message):
    bot.send_message(message.chat.id, "Qancha depozit qilmoqchisiz?\nMin: 10 000 | Max: 10 000 000 so'm")
    bot.register_next_step_handler(message, get_dep_amount)

def get_dep_amount(message):
    try:
        amount = int(message.text)
        if 10000 <= amount <= 10000000:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ To'ladim", callback_data=f"payed_{amount}"))
            bot.send_message(message.chat.id, f"💳 Karta: `{KARTA_RAQAM}`\n💰 Miqdor: {amount:,} so'm\n\nTo'lovni amalga oshirib 'To'ladim' tugmasini bosing.", parse_mode="Markdown", reply_markup=markup)
        else:
            bot.send_message(message.chat.id, "Limit xatosi!")
    except:
        bot.send_message(message.chat.id, "Faqat raqam yozing!")

@bot.callback_query_handler(func=lambda call: call.data.startswith("payed_"))
def notify_admin(call):
    amount = call.data.split("_")[1]
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"confirm_{call.from_user.id}_{amount}"),
               types.InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_{call.from_user.id}"))
    bot.send_message(ADMIN_ID, f"🔔 Yangi depozit!\nID: {call.from_user.id}\nMiqdor: {amount} so'm", reply_markup=markup)
    bot.answer_callback_query(call.id, "Adminga xabar yuborildi.")

@bot.callback_query_handler(func=lambda call: call.data.startswith(("confirm_", "reject_")))
def handle_payment(call):
    data = call.data.split("_")
    uid, status = int(data[1]), data[0]
    conn = sqlite3.connect('casino_uzb.db')
    cursor = conn.cursor()
    if status == "confirm":
        amt = float(data[2])
        cursor.execute("UPDATE users SET balance = balance + ? WHERE id=?", (uid,))
        bot.send_message(uid, f"✅ To'lovingiz tasdiqlandi! Hisobingizga {amt:,} so'm qo'shildi.")
    else:
        bot.send_message(uid, "❌ To'lovingiz tasdiqlanmadi.")
    conn.commit()
    conn.close()
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: m.text == "👤 Profil")
def profile(message):
    conn = sqlite3.connect('casino_uzb.db')
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE id=?", (message.from_user.id,))
    res = cursor.fetchone()
    bot.send_message(message.chat.id, f"👤 Profilingiz:\n💰 Balans: {res[0]:,} so'm\n\n💸 Pul yechish limiti:\nMin: 250 000 so'm")
    conn.close()

bot.polling(none_stop=True)

        
        
    
  
