import telebot
from telebot import types
import sqlite3
import time
from datetime import datetime

# --- SOZLAMALAR ---
TOKEN = '8609558089:AAExgvs1_XR5jlj9RGC55zZStvc7nV_Z6hE'
bot = telebot.TeleBot(TOKEN)
ADMIN_ID = 8299021738
ADMIN_LINK = "https://t.me/Vebiy_001"
KARTA_RAQAM = "9860 6067 5582 9722"

QARZ_LIMITI_1 = 300000
QARZ_LIMITI_2 = 2000000
MAX_YUTUQ = 110000
YECHISH_MIN = 250000
REFERAL_BONUS = 5000

def db_op(query, params=(), is_select=False):
    conn = sqlite3.connect('casino_uzb.db', check_same_thread=False, timeout=30)
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        if is_select: return cursor.fetchall()
        conn.commit()
    except Exception as e: print(f"Baza xatosi: {e}")
    finally: conn.close()

# Jadvallarni yangilash (referal va qarz sanog'i qo'shildi)
db_op('''CREATE TABLE IF NOT EXISTS users 
         (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, balance REAL DEFAULT 10000, 
          debt REAL DEFAULT 0, debt_time TEXT, 
          nasiya_count INTEGER DEFAULT 0, total_nasiya_taken INTEGER DEFAULT 0,
          referred_by INTEGER, last_nasiya_date TEXT)''')

def get_updated_stats(uid):
    u = db_op("SELECT debt, debt_time, balance, nasiya_count, total_nasiya_taken FROM users WHERE id=?", (uid,), is_select=True)
    if not u: return 0, 0, 0, 0
    debt, d_time_str, balance, n_count, total_n_taken = u[0]
    
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
    return debt, balance, n_count, total_n_taken

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🎰 O'yinlar", "👤 Profil")
    markup.add("💸 Nasiya olish", "🔴 Qarzni to'lash")
    markup.add("💰 Pul yechish", "👥 Do'stlarni taklif qilish")
    markup.add("👨‍💻 Admin murojaat")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    args = message.text.split()
    
    user = db_op("SELECT id FROM users WHERE id=?", (uid,), is_select=True)
    
    if not user:
        referred_by = args[1] if len(args) > 1 and args[1].isdigit() else None
        bot.send_message(uid, "Xush kelibsiz! Ro'yxatdan o'tish uchun ismingizni kiriting:")
        bot.register_next_step_handler(message, lambda m: get_name(m, referred_by))
    else:
        bot.send_message(uid, "Xush kelibsiz!", reply_markup=main_menu())

def get_name(message, referred_by):
    name = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("📞 Raqamni tasdiqlash", request_contact=True))
    bot.send_message(message.chat.id, f"Salom {name}, raqamingizni yuboring:", reply_markup=markup)
    bot.register_next_step_handler(message, lambda m: save_user(m, name, referred_by))

def save_user(message, name, referred_by):
    if not message.contact:
        return bot.send_message(message.chat.id, "Iltimos, tugmani bosing!")
    
    uid = message.from_user.id
    phone = message.contact.phone_number
    db_op("INSERT INTO users (id, name, phone, referred_by) VALUES (?, ?, ?, ?)", (uid, name, phone, referred_by))
    
    if referred_by:
        db_op("UPDATE users SET balance = balance + ? WHERE id=?", (REFERAL_BONUS, referred_by))
        bot.send_message(referred_by, f"🎉 Do'stingiz qo'shildi! Sizga {REFERAL_BONUS:,} UZS bonus berildi.")

    bot.send_message(uid, "Muvaffaqiyatli ro'yxatdan o'tdingiz!", reply_markup=main_menu())

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    uid = message.from_user.id
    text = message.text
    debt, balance, n_count, total_n_taken = get_updated_stats(uid)

    if text == "👤 Profil":
        bot.send_message(uid, f"👤 **PROFIL**\n\n💰 Balans: {balance:,.0f} s\n🔴 Qarz: {debt:,.0f} s\n🆔 ID: `{uid}`")

    elif text == "👥 Do'stlarni taklif qilish":
        link = f"https://t.me/{(bot.get_me()).username}?start={uid}"
        bot.send_message(uid, f"Do'stlaringizni taklif qiling va har biri uchun {REFERAL_BONUS:,} UZS oling!\n\nSizning havolangiz:\n{link}")

    elif text == "💸 Nasiya olish":
        if debt > 0:
            bot.send_message(uid, f"⚠️ Avvalgi qarzingizni to'lang: {debt:,.0f} s")
            return
        
        limit = QARZ_LIMITI_1 if total_n_taken == 0 else QARZ_LIMITI_2
        bot.send_message(uid, f"Qancha nasiya olasiz?\nSiz uchun limit: {limit:,} UZS\n(Eng kamida 10,000 UZS)")
        bot.register_next_step_handler(message, lambda m: process_nasiya(m, limit))

    elif text == "🔴 Qarzni to'lash":
        if debt <= 0: bot.send_message(uid, "Qarzingiz yo'q.")
        else:
            bot.send_message(uid, f"To'lanadigan: {debt:,.0f} s\nKarta: `{KARTA_RAQAM}`\nSummani yozing:")
            bot.register_next_step_handler(message, pay_start)

    elif text == "💰 Pul yechish":
        if debt > 0: bot.send_message(uid, "Qarzingiz bor paytda pul yechib bo'lmaydi!")
        elif balance < YECHISH_MIN: bot.send_message(uid, f"Minimal yechish: {YECHISH_MIN:,} UZS")
        else:
            bot.send_message(uid, "Yechiladigan summani yozing:")
            bot.register_next_step_handler(message, withdraw_init)
    
    elif text == "🎰 O'yinlar":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🎰 Slot", "🔙 Orqaga")
        bot.send_message(uid, "O'yinni tanlang", reply_markup=markup)

    elif text == "🔙 Orqaga":
        bot.send_message(uid, "Bosh menyu", reply_markup=main_menu())

    elif text == "🎰 Slot":
        if balance < 50000: bot.send_message(uid, "Kamida 50,000 s kerak!")
        else:
            db_op("UPDATE users SET balance = balance - 50000 WHERE id=?", (uid,))
            res = bot.send_dice(uid, emoji='🎰')
            time.sleep(4)
            if res.dice.value in [1, 22, 43, 64]:
                db_op("UPDATE users SET balance = balance + 110000 WHERE id=?", (uid,))
                bot.send_message(uid, "🎉 YUTDINGIZ! +110,000 s")
            else: bot.send_message(uid, "😔 Yutqazdingiz.")

    elif text == "👨‍💻 Admin murojaat":
        bot.send_message(uid, f"Admin: {ADMIN_LINK}")

def process_nasiya(message, limit):
    try:
        amt = float(message.text)
        if 10000 <= amt <= limit:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("Tasdiqlash ✅", callback_data=f"nas_v_{amt}"))
            bot.send_message(message.chat.id, f"{amt:,} UZS nasiya olasizmi?", reply_markup=markup)
        else:
            bot.send_message(message.chat.id, f"❌ Xato! Summa 10,000 va {limit:,} UZS orasida bo'lishi kerak.")
    except: bot.send_message(message.chat.id, "Faqat son kiriting!")

# --- ADMIN BUYRUQLARI ---
@bot.message_handler(commands=['malumot', 'backup', 'qarz_ber', 'qarz_ol'])
def admin_cmd(message):
    if message.from_user.id != ADMIN_ID: return
    c = message.text.split()
    if c[0] == '/malumot':
        res = db_op("SELECT name, phone, balance, debt FROM users", is_select=True)
        out = "📋 Foydalanuvchilar:\n"
        for r in res: out += f"👤 {r[0]} | {r[1]} | B: {r[2]:,} | Q: {r[3]:,}\n"
        bot.send_message(ADMIN_ID, out[:4000])
    elif c[0] == '/backup':
        with open('casino_uzb.db', 'rb') as f: bot.send_document(ADMIN_ID, f)

@bot.callback_query_handler(func=lambda call: True)
def cb(call):
    d = call.data.split("_")
    uid = call.from_user.id
    if d[0] == "nas" and d[1] == "v":
        amt = float(d[2])
        db_op("UPDATE users SET balance = balance + ?, debt = debt + ?, debt_time = ?, total_nasiya_taken = total_nasiya_taken + 1 WHERE id=?", 
              (amt, amt, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), uid))
        bot.edit_message_text(f"✅ {amt:,} UZS hisobingizga qo'shildi.", call.message.chat.id, call.message.message_id)

# Pul yechish va To'lov boshlanishi (avvalgi koddagidek davom etadi)
def withdraw_init(message):
    try:
        amt = float(message.text)
        bot.send_message(message.chat.id, "Karta raqami va ismingizni yozing:")
        bot.register_next_step_handler(message, lambda m: bot.send_message(ADMIN_ID, f"YECHISH: {amt:,}\nKarta: {m.text}\nID: {uid}"))
    except: pass

def pay_start(message):
    try:
        amt = float(message.text)
        bot.send_message(ADMIN_ID, f"TO'LOV: {amt:,} s\nID: {message.from_user.id}")
        bot.send_message(message.chat.id, "Adminga yuborildi.")
    except: pass

bot.infinity_polling()
                



        

    
            
        
        
    
  
