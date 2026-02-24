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

def db_op(query, params=(), is_select=False):
    conn = sqlite3.connect('casino_uzb.db', check_same_thread=False, timeout=30)
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        if is_select: return cursor.fetchall()
        conn.commit()
    except Exception as e: print(f"Baza xatosi: {e}")
    finally: conn.close()

# Ma'lumotlar bazasini yangilash
db_op('''CREATE TABLE IF NOT EXISTS users 
         (id INTEGER PRIMARY KEY, name TEXT, balance REAL DEFAULT 10000, 
          debt REAL DEFAULT 0, debt_time TEXT)''')
db_op('''CREATE TABLE IF NOT EXISTS history 
         (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, 
          amount REAL, type TEXT, date TEXT)''')

# --- QARZNI VA FOIZNI TEKSHIRISH (LOGIKA) ---
def update_debt_and_get(uid):
    u = db_op("SELECT debt, debt_time, balance FROM users WHERE id=?", (uid,), is_select=True)
    if not u or u[0][0] <= 0 or not u[0][1]:
        return (u[0][0] if u else 0, u[0][2] if u else 0)

    debt = u[0][0]
    balance = u[0][2]
    debt_time = datetime.strptime(u[0][1], "%Y-%m-%d %H:%M:%S")
    now = datetime.now()
    diff = now - debt_time
    hours_passed = diff.total_seconds() / 3600

    old_debt = debt
    # 48 soatdan o'tsa +50% birdaniga
    if hours_passed >= 48:
        debt = debt * 1.5
    # 12 soatdan o'tsa, har 1 soat uchun +5%
    elif hours_passed > 12:
        extra_hours = int(hours_passed - 12)
        for _ in range(extra_hours):
            debt += debt * 0.05

    if debt != old_debt:
        db_op("UPDATE users SET debt = ? WHERE id=?", (debt, uid))
    
    return (debt, balance)

# --- MENYULAR ---
def main_menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🎰 Super Slot (100k)", "🎯 Dart (50k)", "🏀 Basket (50k)")
    markup.add("🎲 Kubik (20k)", "🎳 Bouling (30k)")
    markup.add("👤 Profil", "🏆 Reyting", "📜 Tarix")
    markup.add("💸 TEZKOR NASIYA", "🔴 Qarzni to'lash")
    if uid == ADMIN_ID: markup.add("📊 Admin Panel")
    return markup

# --- START ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    user = db_op("SELECT id FROM users WHERE id=?", (uid,), is_select=True)
    if user:
        bot.send_message(message.chat.id, "💰 Xush kelibsiz! Bugun omadingiz chopadi!\n\n💸 Pulingiz tugab qoldimi? **Nasiya olish** bo'limidan foydalaning!", reply_markup=main_menu(uid), parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "Ismingizni kiriting:")
        bot.register_next_step_handler(message, get_name)

def get_name(message):
    name = message.text
    db_op("INSERT OR IGNORE INTO users (id, name, balance) VALUES (?, ?, 10000)", (message.from_user.id, name))
    bot.send_message(message.chat.id, f"Tabriklayman {name}! Sizga 10,000 s bonus berildi. O'yinni boshlang!", reply_markup=main_menu(message.from_user.id))

# --- ASOSIY HANDLER ---
@bot.message_handler(func=lambda m: True)
def main_handler(message):
    uid = message.from_user.id
    text = message.text
    debt, balance = update_debt_and_get(uid)

    if text == "👤 Profil":
        msg = f"👤 **PROFILINGIZ**\n\n💰 Balans: {balance:,.0f} s\n🔴 Qarz: {debt:,.0f} s\n"
        if debt > 0:
            msg += "\n⚠️ **DIQQAT!** Qarzni 12 soat ichida to'lamasangiz, soatiga 5% dan qo'shiladi!"
        bot.send_message(message.chat.id, msg, parse_mode="Markdown")

    elif text == "💸 TEZKOR NASIYA":
        if debt > 0:
            bot.send_message(message.chat.id, "❌ Sizda amaldagi qarz bor. Avval uni to'lang!")
        else:
            bot.send_message(message.chat.id, "💰 **KAZINO SIZGA ISHONADI!**\n200,000 so'mgacha nasiya oling.\n\nSummani yozing (Masalan: 50000):")
            bot.register_next_step_handler(message, set_debt)

    elif text == "🎰 Super Slot (100k)":
        play_game(message, '🎰', [1, 22, 43, 64], 100000, 500000)
    elif text == "🎯 Dart (50k)":
        play_game(message, '🎯', [6, 5], 50000, 150000)
    elif text == "🏀 Basket (50k)":
        play_game(message, '🏀', [4, 5], 50000, 120000)
    elif text == "🎲 Kubik (20k)":
        play_game(message, '🎲', [6], 20000, 100000)
    elif text == "🎳 Bouling (30k)":
        play_game(message, '🎳', [6, 5], 30000, 90000)

    elif text == "🔴 Qarzni to'lash":
        if debt <= 0:
            bot.send_message(message.chat.id, "Sizda qarz mavjud emas. O'yindan zavqlaning!")
        else:
            bot.send_message(message.chat.id, f"Joriy qarz: {debt:,.0f} s\n\nKarta: `{KARTA_RAQAM}`\nTo'lagan summani yozing:")
            bot.register_next_step_handler(message, pay_req)

    elif text == "🏆 Reyting":
        top = db_op("SELECT name, balance FROM users ORDER BY balance DESC LIMIT 10", is_select=True)
        res = "🏆 **TOP 10 BOYVATCHALAR:**\n\n"
        for i, u in enumerate(top, 1): res += f"{i}. {u[0]} — {u[1]:,.0f} s\n"
        bot.send_message(message.chat.id, res)

    elif text == "📜 Tarix":
        h = db_op("SELECT amount, type, date FROM history WHERE user_id=? ORDER BY id DESC LIMIT 5", (uid,), is_select=True)
        res = "📜 **AMALLAR TARIXI:**\n\n" + ("\n".join([f"📅 {i[2]}: {i[0]:,.0f} s ({i[1]})" for i in h]) if h else "Hali harakat yo'q")
        bot.send_message(message.chat.id, res)

# --- FUNKSIYALAR ---
def play_game(message, emoji, win_values, cost, prize):
    uid = message.from_user.id
    debt, balance = update_debt_and_get(uid)
    
    if balance < cost:
        bot.send_message(message.chat.id, f"⚠️ Mablag' yetarli emas! Nasiya oling va omadingizni sinang!")
        return

    db_op("UPDATE users SET balance = balance - ? WHERE id=?", (cost, uid))
    msg = bot.send_dice(message.chat.id, emoji=emoji)
    time.sleep(4)

    if msg.dice.value in win_values:
        db_op("UPDATE users SET balance = balance + ? WHERE id=?", (prize, uid))
        bot.reply_to(msg, f"🚀 DAHSHT! SIZ YUTDINGIZ!\n💰 +{prize:,} so'm balansga!")
    else:
        bot.reply_to(msg, "😔 Omadsizlik... Yana bir bor urinib ko'ring!")

def set_debt(message):
    try:
        amt = float(message.text)
        if amt > 200000 or amt < 1000:
            bot.send_message(message.chat.id, "❌ Nasiya miqdori 1,000 - 200,000 oralig'ida bo'lishi kerak!")
            return
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        date_ui = datetime.now().strftime("%d.%m %H:%M")
        db_op("UPDATE users SET balance = balance + ?, debt = ?, debt_time = ? WHERE id=?", 
              (amt, amt, now_str, message.from_user.id))
        db_op("INSERT INTO history (user_id, amount, type, date) VALUES (?, ?, ?, ?)", (message.from_user.id, amt, "Nasiya olindi", date_ui))
        bot.send_message(message.chat.id, f"✅ Tabriklaymiz! {amt:,.0f} so'm berildi. 12 soatdan keyin foizlar ishga tushadi!")
    except: bot.send_message(message.chat.id, "Faqat raqam yozing!")

def pay_req(message):
    try:
        amt = float(message.text)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"p_y_{message.from_user.id}_{amt}"))
        bot.send_message(ADMIN_ID, f"🔔 **QARZ TO'LOVI**\nID: {message.from_user.id}\nSumma: {amt:,.0f} s", reply_markup=markup)
        bot.send_message(message.chat.id, "✅ So'rov yuborildi. Admin tasdiqlashi bilan qarz o'chadi.")
    except: pass

@bot.callback_query_handler(func=lambda call: True)
def calls(call):
    d = call.data.split("_")
    if d[0] == "p" and d[1] == "y":
        tid, amt = int(d[2]), float(d[3])
        date_ui = datetime.now().strftime("%d.%m %H:%M")
        db_op("UPDATE users SET debt = CASE WHEN debt >= ? THEN debt - ? ELSE 0 END WHERE id=?", (amt, amt, tid))
        u = db_op("SELECT debt FROM users WHERE id=?", (tid,), is_select=True)
        if u[0][0] <= 0:
            db_op("UPDATE users SET debt_time = NULL WHERE id=?", (tid,))
        db_op("INSERT INTO history (user_id, amount, type, date) VALUES (?, ?, ?, ?)", (tid, amt, "Qarz yopildi", date_ui))
        bot.send_message(tid, "✅ Adminga rahmat ayting! To'lovingiz tasdiqlandi va qarz o'chirildi.")
        bot.edit_message_text(f"✅ Tasdiqlandi (ID: {tid})", call.message.chat.id, call.message.message_id)

bot.infinity_polling()
    
    



        

    
            
        
        
    
  
