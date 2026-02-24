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

# --- MENYU ---
def main_menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📦 4 ta Quticha", "💎 VIP Slot (100k)")
    markup.add("👤 Profil", "💸 Nasiya olish")
    markup.add("💳 Depozit", "💸 Pul yechish")
    if uid == ADMIN_ID:
        markup.add("📊 Admin: Ma'lumot")
    return markup

# --- JARIMA VA OGOHLANTIRISH ---
def check_debt_and_punish(uid):
    user = execute_query("SELECT debt, last_debt_time FROM users WHERE id=?", (uid,), is_select=True)
    if user and user[0] > 0 and user[1]:
        debt, last_time = user[0], user[1]
        last_date = datetime.strptime(last_time, "%Y-%m-%d %H:%M:%S")
        days_passed = (datetime.now() - last_date).days
        if days_passed >= 1:
            interest = debt * 0.10 * days_passed
            new_debt = debt + interest
            execute_query("UPDATE users SET debt = ?, last_debt_time = ? WHERE id=?", 
                          (new_debt, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), uid))
            bot.send_message(uid, f"🚨 **QARZ OSHDI!**\nJarima qo'shildi. Jami qarz: {new_debt:,} s\nTo'lamasangiz DXX va Kredit so'rovi yuboriladi!")

# --- O'YINLAR ---

# 1. 4 ta Quticha (25% yutish shansi)
@bot.message_handler(func=lambda m: m.text == "📦 4 ta Quticha")
def game_boxes(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(*[types.InlineKeyboardButton(f"📦 {i}-quti", callback_data=f"box_{i}") for i in range(1, 5)])
    bot.send_message(message.chat.id, "Qutini tanlang (Tikish: 5,000 s):", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("box_"))
def box_res(call):
    uid = call.from_user.id
    user = execute_query("SELECT balance FROM users WHERE id=?", (uid,), is_select=True)
    if not user or user[0] < 5000:
        bot.answer_callback_query(call.id, "Mablag' yetarli emas!", show_alert=True)
        return
    # 25% yutish shansi
    if random.randint(1, 4) == 1:
        execute_query("UPDATE users SET balance = balance + 15000 WHERE id=?", (uid,))
        txt = "🎉 YUTDINGIZ! +20,000 s"
    else:
        execute_query("UPDATE users SET balance = balance - 5000 WHERE id=?", (uid,))
        txt = "😔 BO'SH! Yutqazdingiz."
    bot.edit_message_text(txt, call.message.chat.id, call.message.message_id)

# 2. VIP SLOT (100,000 so'm - FOYDALANUVCHI YUTMASLIGI UCHUN)
@bot.message_handler(func=lambda m: m.text == "💎 VIP Slot (100k)")
def vip_slot(message):
    uid = message.from_user.id
    user = execute_query("SELECT balance FROM users WHERE id=?", (uid,), is_select=True)
    
    if not user or user[0] < 100000:
        bot.send_message(message.chat.id, "⚠️ Bu o'yin uchun hisobingizda kamida 100,000 so'm bo'lishi kerak! Nasiya oling.")
        return

    # O'YIN BOSHLANADI
    bot.send_message(message.chat.id, "🎰 Slot aylanyapti... Katta yutuq kutilmoqda! 🚀")
    import time
    time.sleep(2) # Effekt uchun kutish

    # Yutish ehtimoli 1% dan ham kam (Deyarli imkonsiz)
    if random.random() < 0.005: # 0.5% shans
        execute_query("UPDATE users SET balance = balance + 500000 WHERE id=?", (uid,))
        bot.send_message(message.chat.id, "😱 MO'JIZA! Siz 500,000 yutdingiz!")
    else:
        execute_query("UPDATE users SET balance = balance - 100000 WHERE id=?", (uid,))
        bot.send_message(message.chat.id, "😔 AFSUKI OMAD KELMADI!\nSlotlarda kombinatsiya chiqmadi. \nHisobingizdan **100,000 so'm** yechildi.")

# --- BOSHQA FUNKSIYALAR ---
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
    bot.send_message(message.chat.id, f"Rahmat {name}! Telefon yuboring:", reply_markup=markup)
    bot.register_next_step_handler(message, save_user, name)

def save_user(message, name):
    if message.contact:
        execute_query("INSERT OR IGNORE INTO users (id, name, phone, balance) VALUES (?, ?, ?, 5000)", 
                      (message.from_user.id, name, message.contact.phone_number))
        bot.send_message(message.chat.id, "✅ Ro'yxatdan o'tdingiz!", reply_markup=main_menu(message.from_user.id))

@bot.message_handler(func=lambda m: True)
def handler(message):
    uid = message.from_user.id
    check_debt_and_punish(uid)
    if message.text == "👤 Profil":
        u = execute_query("SELECT balance, debt FROM users WHERE id=?", (uid,), is_select=True)
        bot.send_message(message.chat.id, f"💰 Balans: {u[0]:,} s\n🔴 Qarz: {u[1]:,} s")
    elif message.text == "💸 Nasiya olish":
        bot.send_message(message.chat.id, "Qancha nasiya kerak?")
        bot.register_next_step_handler(message, set_debt)
    elif message.text == "📊 Admin: Ma'lumot" and uid == ADMIN_ID:
        users = execute_query("SELECT name, phone, debt FROM users", is_select=True)
        rep = "📊 Foydalanuvchilar:\n"
        for u in users: rep += f"👤 {u[0]} | {u[1]} | Q: {u[2]:,}\n"
        bot.send_message(ADMIN_ID, rep)

def set_debt(message):
    try:
        amt = float(message.text)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        execute_query("UPDATE users SET balance = balance + ?, debt = debt + ?, last_debt_time = ? WHERE id=?", 
                      (amt, amt, now, message.from_user.id))
        bot.send_message(message.chat.id, f"✅ {amt:,} s nasiya berildi.")
    except: bot.send_message(message.chat.id, "Faqat son!")

bot.infinity_polling()

    
            
        
        
    
  
