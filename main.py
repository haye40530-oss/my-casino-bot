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

execute_query('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, 
                  balance REAL DEFAULT 0, debt REAL DEFAULT 0, 
                  last_debt_time TEXT, user_card TEXT DEFAULT 'Kiritilmagan')''')

# --- ASOSIY MENYU ---
def main_menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🎰 4 ta Quticha", "💎 VIP Slot (100k)")
    markup.add("👤 Profil", "💸 Nasiya olish")
    markup.add("💳 Depozit", "🔴 Qarzni to'lash")
    markup.add("💸 Pul yechish", "🔙 Orqaga")
    if uid == ADMIN_ID:
        markup.add("📊 Admin: Ma'lumot")
    return markup

# --- START ---
@bot.message_handler(commands=['start'])
def start(message):
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
    bot.send_message(message.chat.id, f"Rahmat {name}! Telefon yuboring:", reply_markup=markup)
    bot.register_next_step_handler(message, save_user, name)

def save_user(message, name):
    if message.contact:
        execute_query("INSERT OR IGNORE INTO users (id, name, phone, balance) VALUES (?, ?, ?, 5000)", 
                      (message.from_user.id, name, message.contact.phone_number))
        bot.send_message(message.chat.id, "✅ Ro'yxatdan o'tdingiz!", reply_markup=main_menu(message.from_user.id))

# --- DEPOZIT VA QARZ TO'LASH TIZIMI ---
@bot.message_handler(func=lambda m: m.text in ["💳 Depozit", "🔴 Qarzni to'lash"])
def payment_start(message):
    msg = (f"💳 To'lov qilish uchun karta: `{KARTA_RAQAM}`\n\n"
           f"To'lovni amalga oshirgach, summani (faqat raqamda) yozing.\n"
           f"Masalan: 50000")
    bot.send_message(message.chat.id, msg, parse_mode="Markdown")
    bot.register_next_step_handler(message, process_payment_request)

def process_payment_request(message):
    try:
        amount = int(message.text)
        uid = message.from_user.id
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"pay_confirm_{uid}_{amount}"),
                   types.InlineKeyboardButton("❌ Bekor qilish", callback_data=f"pay_cancel_{uid}"))
        
        bot.send_message(ADMIN_ID, f"🔔 **TO'LOV SO'ROVI!**\nID: {uid}\nSumma: {amount:,} so'm", reply_markup=markup)
        bot.send_message(message.chat.id, "✅ So'rovingiz adminga yuborildi. Tasdiqlanishini kuting.")
    except:
        bot.send_message(message.chat.id, "⚠️ Xato! Faqat raqam kiriting.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_"))
def admin_payment_callback(call):
    data = call.data.split("_")
    action = data[1]
    user_id = int(data[2])
    
    if action == "confirm":
        amount = float(data[3])
        # Balansni oshirish va qarzni kamaytirish mantig'i
        user = execute_query("SELECT debt, balance FROM users WHERE id=?", (user_id,), is_select=True)
        current_debt = user[0]
        
        if current_debt > 0:
            new_debt = max(0, current_debt - amount)
            remains = max(0, amount - current_debt)
            execute_query("UPDATE users SET debt = ?, balance = balance + ? WHERE id=?", (new_debt, remains, user_id))
            bot.send_message(user_id, f"✅ To'lovingiz qabul qilindi!\nQarzingiz yopildi. Ortiqcha summa balansga qo'shildi.")
        else:
            execute_query("UPDATE users SET balance = balance + ? WHERE id=?", (amount, user_id))
            bot.send_message(user_id, f"✅ To'lovingiz qabul qilindi! Balans: +{amount:,} s")
            
        bot.edit_message_text(f"✅ To'lov tasdiqlandi ({amount:,} s)", call.message.chat.id, call.message.message_id)
    else:
        bot.send_message(user_id, "❌ To'lovingiz bekor qilindi.")
        bot.edit_message_text("❌ To'lov rad etildi", call.message.chat.id, call.message.message_id)

# --- O'YINLAR VA BOSHQA MENYULAR ---
@bot.message_handler(func=lambda m: True)
def handler(message):
    uid = message.from_user.id
    if message.text == "👤 Profil":
        u = execute_query("SELECT balance, debt FROM users WHERE id=?", (uid,), is_select=True)
        bot.send_message(message.chat.id, f"💰 Balans: {u[0]:,} s\n🔴 Qarz: {u[1]:,} s")
    elif message.text == "💸 Nasiya olish":
        bot.send_message(message.chat.id, "Qancha nasiya kerak?")
        bot.register_next_step_handler(message, set_debt)
    elif message.text == "🔙 Orqaga":
        bot.send_message(message.chat.id, "Asosiy menyu:", reply_markup=main_menu(uid))
    elif message.text == "📊 Admin: Ma'lumot" and uid == ADMIN_ID:
        users = execute_query("SELECT name, phone, debt FROM users", is_select=True)
        rep = "📊 Foydalanuvchilar:\n"
        for u in users: rep += f"👤 {u[0]} | {u[1]} | Q: {u[2]:,}\n"
        bot.send_message(ADMIN_ID, rep)
    elif message.text == "📦 4 ta Quticha":
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(*[types.InlineKeyboardButton(f"📦 {i}-quti", callback_data=f"box_{i}") for i in range(1, 5)])
        bot.send_message(message.chat.id, "Qutini tanlang (5,000 s):", reply_markup=markup)

def set_debt(message):
    try:
        amt = float(message.text)
        execute_query("UPDATE users SET balance = balance + ?, debt = debt + ?, last_debt_time = ? WHERE id=?", 
                      (amt, amt, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), message.from_user.id))
        bot.send_message(message.chat.id, f"✅ {amt:,} s nasiya berildi.")
    except: bot.send_message(message.chat.id, "Faqat son!")

@bot.callback_query_handler(func=lambda call: call.data.startswith("box_"))
def box_res(call):
    uid = call.from_user.id
    user = execute_query("SELECT balance FROM users WHERE id=?", (uid,), is_select=True)
    if not user or user[0] < 5000:
        bot.answer_callback_query(call.id, "Mablag' yetarli emas!", show_alert=True)
        return
    if random.randint(1, 4) == 1:
        execute_query("UPDATE users SET balance = balance + 15000 WHERE id=?", (uid,))
        txt = "🎉 YUTDINGIZ! +20,000 s"
    else:
        execute_query("UPDATE users SET balance = balance - 5000 WHERE id=?", (uid,))
        txt = "😔 BO'SH! Yutqazdingiz."
    bot.edit_message_text(txt, call.message.chat.id, call.message.message_id)

bot.infinity_polling()
        

    
            
        
        
    
  
