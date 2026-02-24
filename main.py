import telebot
from telebot import types
import sqlite3
import random

# --- SOZLAMALAR ---
TOKEN = '8609558089:AAExgvs1_XR5jlj9RGC55zZStvc7nV_Z6hE'
bot = telebot.TeleBot(TOKEN)
ADMIN_ID = 8299021738
KARTA_RAQAM = "9860 6067 5582 9722"

# --- BAZA BILAN ISHLASH ---
def db_op(query, params=(), is_select=False):
    conn = sqlite3.connect('casino_uzb.db', check_same_thread=False, timeout=20)
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        if is_select: return cursor.fetchall()
        conn.commit()
    except Exception as e: print(f"Baza xatosi: {e}")
    finally: conn.close()

db_op('''CREATE TABLE IF NOT EXISTS users 
         (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, 
          balance REAL DEFAULT 0, debt REAL DEFAULT 0)''')

# --- MENYULAR ---
def main_menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📦 4 ta Quticha", "💎 VIP Slot (100k)")
    markup.add("👤 Profil", "💸 Nasiya olish")
    markup.add("💳 To'lov qilish", "📊 Admin: Ma'lumot")
    return markup

# --- START ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    user = db_op("SELECT id FROM users WHERE id=?", (uid,), is_select=True)
    if user:
        bot.send_message(message.chat.id, "💰 Live Kazino xush kelibsiz!", reply_markup=main_menu(uid))
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
        db_op("INSERT OR IGNORE INTO users (id, name, phone, balance) VALUES (?, ?, ?, 5000)", 
              (message.from_user.id, name, message.contact.phone_number))
        bot.send_message(message.chat.id, "✅ Ro'yxatdan o'tdingiz! 5,000 s bonus berildi.", reply_markup=main_menu(message.from_user.id))

# --- ASOSIY HANDLER ---
@bot.message_handler(func=lambda m: True)
def main_handler(message):
    uid = message.from_user.id
    text = message.text

    if text == "👤 Profil":
        u = db_op("SELECT balance, debt FROM users WHERE id=?", (uid,), is_select=True)
        if u: bot.send_message(message.chat.id, f"👤 Profil\n💰 Balans: {u[0][0]:,} s\n🔴 Qarz: {u[0][1]:,} s")

    elif text == "💸 Nasiya olish":
        bot.send_message(message.chat.id, "Qancha nasiya kerak? (Masalan: 50000)")
        bot.register_next_step_handler(message, get_debt)

    elif text == "💳 To'lov qilish":
        bot.send_message(message.chat.id, f"💳 Karta: `{KARTA_RAQAM}`\nTo'lov summasini yozing:")
        bot.register_next_step_handler(message, send_payment_request)

    elif text == "📦 4 ta Quticha":
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(*[types.InlineKeyboardButton(f"📦 {i}", callback_data=f"box_{i}") for i in range(1, 5)])
        bot.send_message(message.chat.id, "Qutini tanlang (5,000 s):", reply_markup=markup)

    elif text == "📊 Admin: Ma'lumot" and uid == ADMIN_ID:
        users = db_op("SELECT name, phone, debt FROM users", is_select=True)
        res = "📊 Foydalanuvchilar:\n"
        for u in users: res += f"👤 {u[0]} | {u[1]} | Q: {u[2]:,}\n"
        bot.send_message(ADMIN_ID, res)

# --- FUNKSIYALAR ---
def get_debt(message):
    try:
        amt = float(message.text)
        db_op("UPDATE users SET balance = balance + ?, debt = debt + ? WHERE id=?", (amt, amt, message.from_user.id))
        bot.send_message(message.chat.id, f"✅ Hisobingizga {amt:,} s nasiya qo'shildi.")
    except: bot.send_message(message.chat.id, "Faqat son yozing!")

def send_payment_request(message):
    try:
        amt = float(message.text)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"pay_yes_{message.from_user.id}_{amt}"),
                   types.InlineKeyboardButton("❌ Rad etish", callback_data=f"pay_no_{message.from_user.id}"))
        bot.send_message(ADMIN_ID, f"🔔 **TO'LOV SO'ROVI**\n👤 Foydalanuvchi ID: `{message.from_user.id}`\n💰 Summa: {amt:,} s", reply_markup=markup, parse_mode="Markdown")
        bot.send_message(message.chat.id, "✅ To'lov adminga yuborildi. Kuting...")
    except: bot.send_message(message.chat.id, "Xato summa!")

# --- CALLBACK JAVOBLARI ---
@bot.callback_query_handler(func=lambda call: True)
def callback_logic(call):
    data = call.data.split("_")
    
    # Quticha o'yini
    if data[0] == "box":
        uid = call.from_user.id
        user = db_op("SELECT balance FROM users WHERE id=?", (uid,), is_select=True)
        if user[0][0] < 5000:
            bot.answer_callback_query(call.id, "Mablag' yetarli emas!", show_alert=True)
            return
        if random.randint(1, 4) == 1:
            db_op("UPDATE users SET balance = balance + 15000 WHERE id=?", (uid,))
            bot.edit_message_text("🎉 Yutdingiz! +20,000 s", call.message.chat.id, call.message.message_id)
        else:
            db_op("UPDATE users SET balance = balance - 5000 WHERE id=?", (uid,))
            bot.edit_message_text("😔 Bo'sh!", call.message.chat.id, call.message.message_id)

    # Admin to'lovni tasdiqlashi
    elif data[0] == "pay":
        target_id = int(data[2])
        if data[1] == "yes":
            amt = float(data[3])
            # Qarzdorlikdan ayirish va balansi joyida qoldirish (qarzni to'lash uchun)
            db_op("UPDATE users SET debt = CASE WHEN debt >= ? THEN debt - ? ELSE 0 END WHERE id=?", (amt, amt, target_id))
            bot.send_message(target_id, f"✅ To'lovingiz tasdiqlandi! {amt:,} s qarz yopildi.")
            bot.edit_message_text(f"✅ ID {target_id} uchun {amt:,} s tasdiqlandi.", call.message.chat.id, call.message.message_id)
        else:
            bot.send_message(target_id, "❌ To'lovingiz admin tomonidan rad etildi.")
            bot.edit_message_text(f"❌ ID {target_id} uchun to'lov rad etildi.", call.message.chat.id, call.message.message_id)

bot.infinity_polling()



        

    
            
        
        
    
  
