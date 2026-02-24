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

# Baza bilan ishlashda xatoliklarni oldini olish (Timeout bilan)
def db_op(query, params=(), is_select=False):
    conn = sqlite3.connect('casino_uzb.db', check_same_thread=False, timeout=20)
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        if is_select:
            return cursor.fetchall()
        conn.commit()
    except Exception as e:
        print(f"Baza xatosi: {e}")
    finally:
        conn.close()

# Jadvallarni yaratish
db_op('''CREATE TABLE IF NOT EXISTS users 
         (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, 
          balance REAL DEFAULT 0, debt REAL DEFAULT 0, 
          last_debt_time TEXT, user_card TEXT DEFAULT 'Kiritilmagan')''')

# --- ASOSIY MENYU ---
def main_menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📦 4 ta Quticha", "💎 VIP Slot (100k)")
    markup.add("👤 Profil", "💸 Nasiya olish")
    markup.add("💳 Depozit", "🔴 Qarzni to'lash")
    markup.add("💸 Pul yechish")
    if uid == ADMIN_ID:
        markup.add("📊 Admin: Ma'lumot")
    return markup

# --- START ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = message.from_user.id
    user = db_op("SELECT id FROM users WHERE id=?", (uid,), is_select=True)
    if user:
        bot.send_message(message.chat.id, "💰 Live Kazino xush kelibsiz! O'yinni tanlang:", reply_markup=main_menu(uid))
    else:
        bot.send_message(message.chat.id, "Ismingizni kiriting:")
        bot.register_next_step_handler(message, get_name)

def get_name(message):
    name = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("📞 Raqamni yuborish", request_contact=True))
    bot.send_message(message.chat.id, f"Rahmat {name}, endi pastdagi tugma orqali raqamingizni yuboring:", reply_markup=markup)
    bot.register_next_step_handler(message, save_user, name)

def save_user(message, name):
    if message.contact:
        db_op("INSERT OR IGNORE INTO users (id, name, phone, balance) VALUES (?, ?, ?, 5000)", 
              (message.from_user.id, name, message.contact.phone_number))
        bot.send_message(message.chat.id, "✅ Ro'yxatdan o'tdingiz! Sizga 5,000 so'm bonus berildi.", reply_markup=main_menu(message.from_user.id))
    else:
        bot.send_message(message.chat.id, "⚠️ Xato! Tugmani bosishingiz shart.")
        bot.register_next_step_handler(message, save_user, name)

# --- HAMMA FUNKSIYALAR HANDLERI ---
@bot.message_handler(func=lambda m: True)
def main_handler(message):
    uid = message.from_user.id
    text = message.text

    if text == "👤 Profil":
        u = db_op("SELECT balance, debt, name, phone FROM users WHERE id=?", (uid,), is_select=True)
        if u:
            msg = f"👤 **PROFILINGIZ**\n\n🆔 ID: `{uid}`\n👤 Ism: {u[0][2]}\n📞 Tel: {u[0][3]}\n💰 Balans: {u[0][0]:,} so'm\n🔴 Qarz: {u[0][1]:,} so'm"
            bot.send_message(message.chat.id, msg, parse_mode="Markdown")

    elif text == "💸 Nasiya olish":
        bot.send_message(message.chat.id, "Qancha nasiya (qarz) kerak? Summani raqamda yozing:")
        bot.register_next_step_handler(message, process_debt)

    elif text == "📦 4 ta Quticha":
        markup = types.InlineKeyboardMarkup(row_width=2)
        btns = [types.InlineKeyboardButton(f"📦 {i}-quti", callback_data=f"game_box_{i}") for i in range(1, 5)]
        markup.add(*btns)
        bot.send_message(message.chat.id, "Omadingizni sinang! Bitta quti tanlang (Tikish: 5,000 s):", reply_markup=markup)

    elif text == "💎 VIP Slot (100k)":
        user = db_op("SELECT balance FROM users WHERE id=?", (uid,), is_select=True)
        if user and user[0][0] >= 100000:
            bot.send_message(message.chat.id, "🎰 Slot aylanyapti...")
            if random.random() < 0.01: # 1% yutish shansi
                db_op("UPDATE users SET balance = balance + 400000 WHERE id=?", (uid,))
                bot.send_message(message.chat.id, "😱 DAHSHAT! 500,000 so'm yutdingiz!")
            else:
                db_op("UPDATE users SET balance = balance - 100000 WHERE id=?", (uid,))
                bot.send_message(message.chat.id, "😔 Omad kelmadi! 100,000 so'm yutqazdingiz.")
        else:
            bot.send_message(message.chat.id, "⚠️ Balansingizda kamida 100,000 so'm bo'lishi kerak!")

    elif text in ["💳 Depozit", "🔴 Qarzni to'lash"]:
        bot.send_message(message.chat.id, f"💳 To'lov qilish uchun karta: `{KARTA_RAQAM}`\n\nTo'lov qilgan summani yozing (masalan: 20000):")
        bot.register_next_step_handler(message, process_payment)

    elif text == "📊 Admin: Ma'lumot" and uid == ADMIN_ID:
        users = db_op("SELECT name, phone, balance, debt FROM users", is_select=True)
        rep = "📊 **HAMMA FOYDALANUVCHILAR:**\n\n"
        for u in users:
            rep += f"👤 {u[0]} | {u[1]}\n💰 B: {u[2]:,} | 🔴 Q: {u[3]:,}\n---\n"
        bot.send_message(ADMIN_ID, rep, parse_mode="Markdown")

# --- QO'SHIMCHA FUNKSIYALAR ---
def process_debt(message):
    try:
        amt = float(message.text)
        db_op("UPDATE users SET balance = balance + ?, debt = debt + ? WHERE id=?", (amt, amt, message.from_user.id))
        bot.send_message(message.chat.id, f"✅ Hisobingizga {amt:,} so'm nasiya qo'shildi.")
    except:
        bot.send_message(message.chat.id, "⚠️ Xato! Faqat raqam kiriting.")

def process_payment(message):
    try:
        amt = float(message.text)
        bot.send_message(ADMIN_ID, f"🔔 **TO'LOV SO'ROVI!**\nID: `{message.from_user.id}`\nSumma: {amt:,} so'm")
        bot.send_message(message.chat.id, "✅ To'lov adminga yuborildi. Tez orada tasdiqlanadi.")
    except:
        bot.send_message(message.chat.id, "⚠️ Faqat raqam kiriting.")

# --- O'YINLARNING JAVOBI (CALLBACK) ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("game_box_"))
def game_callback(call):
    uid = call.from_user.id
    user = db_op("SELECT balance FROM users WHERE id=?", (uid,), is_select=True)
    if not user or user[0][0] < 5000:
        bot.answer_callback_query(call.id, "⚠️ Balansda pul yetarli emas!", show_alert=True)
        return

    # 25% yutish, 75% yutqazish (Siz aytgandek)
    if random.randint(1, 4) == 1:
        db_op("UPDATE users SET balance = balance + 15000 WHERE id=?", (uid,))
        res = "🎉 YUTDINGIZ! +20,000 so'm balansga qo'shildi."
    else:
        db_op("UPDATE users SET balance = balance - 5000 WHERE id=?", (uid,))
        res = "😔 BU QUTI BO'SH! 5,000 so'm yutqazdingiz."
    
    bot.edit_message_text(res, call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "Asosiy menyu:", reply_markup=main_menu(uid))

# Botni uzluksiz ishga tushirish
if __name__ == "__main__":
    bot.infinity_polling(timeout=20, long_polling_timeout=10)
    


        

    
            
        
        
    
  
