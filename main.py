import telebot
from telebot import types
import sqlite3
import random
from datetime import datetime

# --- KONFIGURATSIYA ---
TOKEN = '8609558089:AAExgvs1_XR5jlj9RGC55zZStvc7nV_Z6hE'
bot = telebot.TeleBot(TOKEN, threaded=False)
ADMIN_ID = 8299021738
KARTA_RAQAM = "9860 6067 5582 9722"

# --- BAZA BILAN ISHLASH ---
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

# --- O'YIN: 4 TA QUTICHA (BARQAROR TIZIM) ---
@bot.message_handler(func=lambda m: m.text == "📦 4 ta Quticha")
def game_boxes_start(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    # Tugmalar har doim callback_data orqali ishlaydi
    btn1 = types.InlineKeyboardButton("📦 1-quti", callback_data="box_1")
    btn2 = types.InlineKeyboardButton("📦 2-quti", callback_data="box_2")
    btn3 = types.InlineKeyboardButton("📦 3-quti", callback_data="box_3")
    btn4 = types.InlineKeyboardButton("📦 4-quti", callback_data="box_4")
    markup.add(btn1, btn2, btn3, btn4)
    bot.send_message(message.chat.id, "Bitta qutini tanlang (Tikish: 5,000 s):", reply_markup=markup)

# --- O'YIN: VIP SLOT ---
@bot.message_handler(func=lambda m: m.text == "💎 VIP Slot (100k)")
def vip_slot_game(message):
    uid = message.from_user.id
    user = execute_query("SELECT balance FROM users WHERE id=?", (uid,), is_select=True)
    
    if not user or user[0] < 100000:
        bot.send_message(message.chat.id, "⚠️ Balansda kamida 100,000 so'm bo'lishi kerak!")
        return

    bot.send_message(message.chat.id, "🎰 Slot aylanyapti...")
    
    # Qarz olganlarni tezroq yutqazdirish uchun shans 0.5%
    if random.random() < 0.005: 
        execute_query("UPDATE users SET balance = balance + 500000 WHERE id=?", (uid,))
        bot.send_message(message.chat.id, "😱 MO'JIZA! 500,000 yutdingiz!")
    else:
        execute_query("UPDATE users SET balance = balance - 100000 WHERE id=?", (uid,))
        bot.send_message(message.chat.id, "😔 Yutqazdingiz! 100,000 so'm yechildi.")

# --- CALLBACKLARNI QABUL QILISH (O'yin natijalari) ---
@bot.callback_query_handler(func=lambda call: True)
def callback_all(call):
    uid = call.from_user.id
    
    if call.data.startswith("box_"):
        user = execute_query("SELECT balance FROM users WHERE id=?", (uid,), is_select=True)
        if not user or user[0] < 5000:
            bot.answer_callback_query(call.id, "Mablag' yetarli emas!", show_alert=True)
            return

        # 3 marta yutqazib, 1 marta yutish (25% shans)
        if random.randint(1, 4) == 1:
            execute_query("UPDATE users SET balance = balance + 15000 WHERE id=?", (uid,))
            res_text = "🎉 YUTDINGIZ! +20,000 so'm balansga qo'shildi."
        else:
            execute_query("UPDATE users SET balance = balance - 5000 WHERE id=?", (uid,))
            res_text = "😔 BU QUTI BO'SH EDI! 5,000 so'm yutqazdingiz."
        
        bot.edit_message_text(res_text, call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "Yana o'ynash uchun menyudan tanlang:", reply_markup=main_menu(uid))

# --- BOSHQA MENYULAR ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = message.from_user.id
    user = execute_query("SELECT * FROM users WHERE id=?", (uid,), is_select=True)
    if user:
        bot.send_message(message.chat.id, "Xush kelibsiz!", reply_markup=main_menu(uid))
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
        bot.send_message(message.chat.id, f"💰 Balans: {u[0]:,} s\n🔴 Qarz: {u[1]:,} s")
    elif message.text == "💸 Nasiya olish":
        bot.send_message(message.chat.id, "Qancha nasiya kerak?")
        bot.register_next_step_handler(message, set_debt)

def set_debt(message):
    try:
        amt = float(message.text)
        execute_query("UPDATE users SET balance = balance + ?, debt = debt + ?, last_debt_time = ? WHERE id=?", 
                      (amt, amt, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), message.from_user.id))
        bot.send_message(message.chat.id, f"✅ {amt:,} s nasiya berildi.")
    except: bot.send_message(message.chat.id, "Faqat son!")

bot.infinity_polling()

        

    
            
        
        
    
  
