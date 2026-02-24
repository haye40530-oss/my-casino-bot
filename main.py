import telebot
from telebot import types
import sqlite3
import random
import time
from datetime import datetime, timedelta

# --- SOZLAMALAR ---
TOKEN = '8609558089:AAExgvs1_XR5jlj9RGC55zZStvc7nV_Z6hE'
bot = telebot.TeleBot(TOKEN)
ADMIN_ID = 8299021738
KARTA_RAQAM = "9860 6067 5582 9722"
QARZ_LIMITI = 500000
MAX_YUTUQ = 100000 # Maksimal yutuq chegarasi

def db_op(query, params=(), is_select=False):
    conn = sqlite3.connect('casino_uzb.db', check_same_thread=False, timeout=30)
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        if is_select: return cursor.fetchall()
        conn.commit()
    except Exception as e: print(f"Baza xatosi: {e}")
    finally: conn.close()

# Jadvallar
db_op('''CREATE TABLE IF NOT EXISTS users 
         (id INTEGER PRIMARY KEY, name TEXT, balance REAL DEFAULT 10000, 
          debt REAL DEFAULT 0, debt_time TEXT, 
          nasiya_count INTEGER DEFAULT 0, last_nasiya_date TEXT)''')

# --- QARZNI YANGILASH ---
def get_updated_stats(uid):
    u = db_op("SELECT debt, debt_time, balance, nasiya_count, last_nasiya_date FROM users WHERE id=?", (uid,), is_select=True)
    if not u: return 0, 0, 0, ""
    debt, d_time_str, balance, n_count, last_date = u[0]
    
    today = datetime.now().strftime("%Y-%m-%d")
    if last_date != today:
        db_op("UPDATE users SET nasiya_count = 0, last_nasiya_date = ? WHERE id=?", (today, uid))
        n_count = 0

    if debt > 0 and d_time_str:
        d_time = datetime.strptime(d_time_str, "%Y-%m-%d %H:%M:%S")
        hours = (datetime.now() - d_time).total_seconds() / 3600
        new_debt = debt
        if hours >= 48: new_debt = debt * 1.5
        elif hours > 12:
            for _ in range(int(hours - 12)): new_debt += new_debt * 0.05
        if new_debt != debt:
            db_op("UPDATE users SET debt = ? WHERE id=?", (new_debt, uid))
            debt = new_debt
    return debt, balance, n_count, today

def main_menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🎰 Super Slot (100k)", "🎯 Dart (50k)", "🏀 Basket (50k)")
    markup.add("👤 Profil", "🏆 Reyting", "📜 Tarix")
    markup.add("💸 Nasiya olish", "🔴 Qarzni to'lash")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    user = db_op("SELECT id FROM users WHERE id=?", (uid,), is_select=True)
    if not user:
        bot.send_message(uid, "Ismingizni kiriting:")
        bot.register_next_step_handler(message, lambda m: db_op("INSERT INTO users (id, name, last_nasiya_date) VALUES (?, ?, ?)", (uid, m.text, datetime.now().strftime("%Y-%m-%d"))) or bot.send_message(uid, "Xush kelibsiz!", reply_markup=main_menu(uid)))
    else:
        bot.send_message(uid, "💰 Xush kelibsiz!", reply_markup=main_menu(uid))

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    uid = message.from_user.id
    debt, balance, n_count, _ = get_updated_stats(uid)
    
    if message.text == "👤 Profil":
        bot.send_message(uid, f"👤 **PROFIL**\n💰 Balans: {balance:,.0f} s\n🔴 Qarz: {debt:,.0f} s\n📅 Bugun: {n_count}/2 marta")
    
    elif message.text == "💸 Nasiya olish":
        if n_count >= 2:
            bot.send_message(uid, "⚠️ Kunlik limit (2 marta) tugadi!")
        elif debt >= QARZ_LIMITI:
            bot.send_message(uid, "❌ Qarz limitingiz to'lgan!")
        else:
            bot.send_message(uid, "Qancha nasiya kerak? Summani yozing:")
            bot.register_next_step_handler(message, confirm_nasiya_step)

    elif message.text == "🔴 Qarzni to'lash":
        if debt <= 0: bot.send_message(uid, "Qarzingiz yo'q.")
        else:
            bot.send_message(uid, f"To'lanadigan: {debt:,.0f} s\nKarta: `{KARTA_RAQAM}`\nSummani yozing:")
            bot.register_next_step_handler(message, pay_start)

    elif "k)" in message.text:
        cost = 100000 if "100k" in message.text else 50000
        if balance < cost: bot.send_message(uid, "Mablag' yetarli emas!")
        else:
            db_op("UPDATE users SET balance = balance - ? WHERE id=?", (cost, uid))
            emoji = '🎰' if "Slot" in message.text else ('🎯' if "Dart" in message.text else '🏀')
            res = bot.send_dice(uid, emoji=emoji)
            time.sleep(4)
            if res.dice.value in [1, 22, 43, 64, 6, 5]:
                win = cost * 4
                db_op("UPDATE users SET balance = balance + ? WHERE id=?", (win, uid))
                bot.send_message(uid, f"🎉 YUTDINGIZ! +{win:,} so'm!")
            else: bot.send_message(uid, "😔 Yutqazdingiz.")

# --- NASIYA TASDIQLASH BOSQICHI ---
def confirm_nasiya_step(message):
    try:
        amt = float(message.text)
        uid = message.from_user.id
        debt, _, n_count, _ = get_updated_stats(uid)
        
        if amt + debt > QARZ_LIMITI:
            bot.send_message(uid, "❌ Limitdan oshib ketmoqda!")
            return

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Tastiqlayman ✅", callback_data=f"nas_v_{amt}"),
                   types.InlineKeyboardButton("Orqaga 🔙", callback_data="nas_x"))
        
        shartnoma = (f"⚠️ **QARZ SHARTNOMASI**\n\n"
                     f"💰 Summa: {amt:,.0f} so'm\n"
                     f"⏰ Muddat: 12 soat (foizsiz)\n\n"
                     f"🔴 **Agar 12 soatda to'lanmasa:**\n"
                     f"- Har 1 soat uchun **5%** ustama qo'shiladi.\n"
                     f"- 48 soatdan keyin jarima **50%** ni tashkil etadi.\n\n"
                     f"Qarz olishga rozimisiz?")
        
        bot.send_message(uid, shartnoma, reply_markup=markup, parse_mode="Markdown")
    except:
        bot.send_message(message.chat.id, "Faqat son kiriting!")

def pay_start(message):
    try:
        amt = float(message.text)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Tastiqlash ✅", callback_data=f"pay_v_{message.from_user.id}_{amt}"),
                   types.InlineKeyboardButton("Otmadi ❌", callback_data=f"pay_x_{message.from_user.id}"))
        bot.send_message(ADMIN_ID, f"🔔 TO'LOV: {amt:,} s\nID: {message.from_user.id}", reply_markup=markup)
        bot.send_message(message.chat.id, "Adminga yuborildi.")
    except: pass

@bot.callback_query_handler(func=lambda call: True)
def callback_all(call):
    uid = call.from_user.id
    data = call.data.split("_")

    # Nasiyani tasdiqlash
    if data[0] == "nas":
        if data[1] == "v":
            amt = float(data[2])
            debt, _, n_count, today = get_updated_stats(uid)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            db_op("UPDATE users SET balance = balance + ?, debt = debt + ?, debt_time = ?, nasiya_count = nasiya_count + 1, last_nasiya_date = ? WHERE id=?", (amt, amt, now, today, uid))
            bot.edit_message_text(f"✅ {amt:,} so'm berildi. Omad!", call.message.chat.id, call.message.message_id)
        else:
            bot.edit_message_text("❌ Bekor qilindi.", call.message.chat.id, call.message.message_id)

    # Admin to'lovni tasdiqlashi
    elif data[0] == "pay":
        act, target_id = data[1], int(data[2])
        if act == "v":
            amount = float(data[3])
            db_op("UPDATE users SET debt = CASE WHEN debt > ? THEN debt - ? ELSE 0 END WHERE id=?", (amount, amount, target_id))
            u = db_op("SELECT debt FROM users WHERE id=?", (target_id,), is_select=True)
            if u[0][0] <= 0: db_op("UPDATE users SET debt_time = NULL WHERE id=?", (target_id,))
            bot.send_message(target_id, "✅ To'lovingiz Tastiqlandi!")
            bot.edit_message_text(f"Tastiqlandi ✅", call.message.chat.id, call.message.message_id)
        else:
            bot.send_message(target_id, "❌ To'lovingiz Otmadi!")
            bot.edit_message_text(f"Rad etildi ❌", call.message.chat.id, call.message.message_id)

bot.infinity_polling()
                
    
    



        

    
            
        
        
    
  
