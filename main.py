import telebot
from telebot import types
import sqlite3
import random
from datetime import datetime, timedelta

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

# Bazani yaratish (Kredit va Karta ustunlari bilan)
execute_query('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, 
                  balance REAL DEFAULT 0, debt REAL DEFAULT 0, 
                  last_debt_time TEXT, user_card TEXT DEFAULT 'Kiritilmagan')''')

# --- MENYU TIZIMI ---
def main_menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🎰 4 ta Quticha", "👤 Profil")
    markup.add("💳 Depozit", "💸 Nasiya olish")
    markup.add("🔴 Qarzni to'lash", "💸 Pul yechish")
    if uid == ADMIN_ID:
        markup.add("📊 Admin: Ma'lumot")
    return markup

# --- QARZNI VA JARIMANI TEKSHIRISH ---
def check_debt_status(uid):
    user = execute_query("SELECT debt, last_debt_time FROM users WHERE id=?", (uid,), is_select=True)
    if user and user[0] > 0 and user[1]:
        debt, last_time = user[0], user[1]
        last_date = datetime.strptime(last_time, "%Y-%m-%d %H:%M:%S")
        now = datetime.now()
        days_passed = (now - last_date).days

        if days_passed >= 1:
            # Har bir kun uchun 10% jarima
            punishment = debt * 0.10 * days_passed
            new_debt = debt + punishment
            execute_query("UPDATE users SET debt = ?, last_debt_time = ? WHERE id=?", 
                          (new_debt, now.strftime("%Y-%m-%d %H:%M:%S"), uid))
            
            warning = (f"🚨 **DIQQAT: QARZINGIZ OSHDI!**\n\n"
                       f"To'lanmagan {days_passed} kun uchun 10% dan jarima qo'shildi.\n"
                       f"Hozirgi qarz: **{new_debt:,} so'm**.\n\n"
                       f"⚠️ **OGOHLANTIRISH:** Agar 12 soatda to'lamasangiz, ma'lumotlaringiz **DXX**ga topshiriladi "
                       f"va bankdan sizning nomingizga **KREDIT** olish so'rovi yuboriladi!")
            bot.send_message(uid, warning, parse_mode="Markdown")

# --- START VA REGISTRATSIYA ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    check_debt_status(uid)
    user = execute_query("SELECT * FROM users WHERE id=?", (uid,), is_select=True)
    if user:
        bot.send_message(message.chat.id, "Xush kelibsiz! O'yinni tanlang:", reply_markup=main_menu(uid))
    else:
        bot.send_message(message.chat.id, "Assalomu alaykum! Ismingizni kiriting:")
        bot.register_next_step_handler(message, get_name)

def get_name(message):
    name = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("📞 Raqamni yuborish", request_contact=True))
    bot.send_message(message.chat.id, f"Rahmat {name}! Telefon raqamingizni tasdiqlang:", reply_markup=markup)
    bot.register_next_step_handler(message, save_user, name)

def save_user(message, name):
    uid = message.from_user.id
    if message.contact:
        phone = message.contact.phone_number
        execute_query("INSERT OR IGNORE INTO users (id, name, phone, balance) VALUES (?, ?, ?, 5000)", (uid, name, phone))
        bot.send_message(message.chat.id, "✅ Ro'yxatdan o'tdingiz! 5,000 so'm bonus berildi.", reply_markup=main_menu(uid))
    else:
        bot.send_message(message.chat.id, "Iltimos, tugmani bosing!")
        bot.register_next_step_handler(message, save_user, name)

# --- ASOSIY ISHLASH ---
@bot.message_handler(func=lambda m: True)
def handle_text(message):
    uid = message.from_user.id
    text = message.text
    check_debt_status(uid)

    if text == "🎰 4 ta Quticha":
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(*[types.InlineKeyboardButton(f"📦 {i}-Quti", callback_data=f"box_{i}") for i in range(1, 5)])
        bot.send_message(message.chat.id, "Qutini tanlang (Tikish: 5,000 so'm):", reply_markup=markup)

    elif text == "👤 Profil":
        u = execute_query("SELECT balance, debt, name, phone, user_card FROM users WHERE id=?", (uid,), is_select=True)
        msg = f"👤 Ism: {u[2]}\n📞 Tel: {u[3]}\n💰 Balans: {u[0]:,} s\n🔴 Qarz: {u[1]:,} s\n💳 Karta: {u[4]}"
        bot.send_message(message.chat.id, msg)

    elif text == "💸 Nasiya olish":
        bot.send_message(message.chat.id, "Qancha nasiya kerak? (Faqat son yozing):")
        bot.register_next_step_handler(message, set_debt)

    elif text == "💸 Pul yechish":
        u = execute_query("SELECT balance, debt FROM users WHERE id=?", (uid,), is_select=True)
        if u[1] > 0:
            bot.send_message(message.chat.id, "⚠️ Avval qarzingizni to'lang!")
        elif u[0] < 10000:
            bot.send_message(message.chat.id, "⚠️ Balansda kamida 10,000 so'm bo'lishi kerak.")
        else:
            bot.send_message(message.chat.id, "Karta raqamingizni yozing:")
            bot.register_next_step_handler(message, get_withdraw_card)

    elif text == "💳 Depozit" or text == "🔴 Qarzni to'lash":
        bot.send_message(message.chat.id, f"💳 To'lov uchun karta: `{KARTA_RAQAM}`\nTo'lov miqdorini yozing:", parse_mode="Markdown")
        bot.register_next_step_handler(message, admin_pay_request)

    elif text == "📊 Admin: Ma'lumot" and uid == ADMIN_ID:
        users = execute_query("SELECT name, phone, debt, user_card FROM users", is_select=True)
        report = "📊 **Barcha Foydalanuvchilar:**\n\n"
        for user in users: report += f"👤 {user[0]} | {user[1]}\n🔴 Qarz: {user[2]:,} | 💳 Karta: {user[3]}\n---\n"
        bot.send_message(ADMIN_ID, report, parse_mode="Markdown")

# --- QUTI CALLBACK ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("box_"))
def box_callback(call):
    uid = call.from_user.id
    user = execute_query("SELECT balance FROM users WHERE id=?", (uid,), is_select=True)
    if not user or user[0] < 5000:
        bot.answer_callback_query(call.id, "Mablag' yetarli emas!", show_alert=True)
        return
    win = random.randint(1, 4)
    choice = int(call.data.split("_")[1])
    if choice == win:
        execute_query("UPDATE users SET balance = balance + 15000 WHERE id=?", (uid,))
        txt = f"🎉 YUTDINGIZ! {win}-quti yutuqli edi! +20,000 s"
    else:
        execute_query("UPDATE users SET balance = balance - 5000 WHERE id=?", (uid,))
        txt = f"😔 YUTQAZDINGIZ. Yutuq {win}-qutida edi."
    bot.edit_message_text(txt, call.message.chat.id, call.message.message_id)

# --- FUNKSIYALAR ---
def set_debt(message):
    try:
        amt = float(message.text)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        execute_query("UPDATE users SET balance = balance + ?, debt = debt + ?, last_debt_time = ? WHERE id=?", (amt, amt, now, message.from_user.id))
        bot.send_message(message.chat.id, f"✅ {amt:,} s nasiya berildi.")
    except: bot.send_message(message.chat.id, "Faqat son!")

def get_withdraw_card(message):
    card = message.text
    execute_query("UPDATE users SET user_card = ? WHERE id=?", (card, message.from_user.id))
    bot.send_message(message.chat.id, "Summani kiriting:")
    bot.register_next_step_handler(message, lambda m: bot.send_message(ADMIN_ID, f"💸 **YECHISH:** {m.text} s\nKarta: {card}\nID: {m.from_user.id}"))

def admin_pay_request(message):
    bot.send_message(ADMIN_ID, f"🔔 **TO'LOV:** {message.text} s\nID: {message.from_user.id}")
    bot.send_message(message.chat.id, "Tasdiqlash uchun yuborildi.")

bot.infinity_polling()
    
            
        
        
    
  
