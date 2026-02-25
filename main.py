import telebot
from telebot import types
import sqlite3
import time
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

# --- SOZLAMALAR ---
TOKEN = '8609558089:AAExgvs1_XR5jlj9RGC55zZStvc7nV_Z6hE'
bot = telebot.TeleBot(TOKEN)
ADMIN_ID = 8299021738
ADMIN_LINK = "https://t.me/Vebiy_001"
KARTA_RAQAM = "9860 6067 5582 9722"

QARZ_LIMITI_1 = 300000
QARZ_LIMITI_2 = 2000000
REFERAL_BONUS = 5000
MAX_YUTUQ = 110000 

def db_op(query, params=(), is_select=False):
    conn = sqlite3.connect('casino_uzb.db', check_same_thread=False, timeout=30)
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        if is_select: return cursor.fetchall()
        conn.commit()
    except Exception as e: print(f"Baza xatosi: {e}")
    finally: conn.close()

db_op('''CREATE TABLE IF NOT EXISTS users 
         (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, balance REAL DEFAULT 10000, 
          debt REAL DEFAULT 0, debt_time TEXT, 
          total_nasiya_taken INTEGER DEFAULT 0, referred_by INTEGER,
          games_played INTEGER DEFAULT 0)''')

# --- AVTOMATIK OGOHLANTIRISH VA JARIMA TIZIMI ---
def hourly_debt_checker():
    debtors = db_op("SELECT id, name, phone, debt, debt_time FROM users WHERE debt > 0", is_select=True)
    for d in debtors:
        uid, name, phone, debt, d_time_str = d
        d_time = datetime.strptime(d_time_str, "%Y-%m-%d %H:%M:%S")
        deadline = d_time + timedelta(hours=12)
        
        # 12 soatdan keyin 5% penya
        if datetime.now() > deadline:
            debt = debt * 1.05
            db_op("UPDATE users SET debt = ? WHERE id=?", (debt, uid))

        # Qarzdorni qo'rqitish
        msg = (f"❗ **QARZNI TO'LASH VAQTI KELDI!**\n\n"
               f"Sizning {debt:,.0f} so'm qarzingiz bor. Agar 1 soat ichida to'lov qilmasangiz, "
               f"ismingiz ({name}) va raqamingiz ({phone}) 'FIRG'ARBLAR' bazasiga yuklanadi!")
        try: bot.send_message(uid, msg)
        except: pass

        # Adminga muntazam hisobot
        bot.send_message(ADMIN_ID, f"🚨 **NAZORAT:** {name} ({phone})\n💰 Qarz: {debt:,.0f} s\n🆔 `{uid}`")

scheduler = BackgroundScheduler()
scheduler.add_job(hourly_debt_checker, 'interval', hours=1)
scheduler.start()

# --- BOT INTERFEYSI ---
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
    user = db_op("SELECT id FROM users WHERE id=?", (uid,), is_select=True)
    if not user:
        bot.send_message(uid, "🛑 **RO'YXATDAN O'TISH**\n\nIsm va Familiyangizni to'liq kiriting:")
        bot.register_next_step_handler(message, get_name)
    else:
        bot.send_message(uid, "💰 Xush kelibsiz!", reply_markup=main_menu())

def get_name(message):
    name = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("📞 Telefonni yuborish", request_contact=True))
    bot.send_message(message.chat.id, "Raqamingizni tasdiqlang:", reply_markup=markup)
    bot.register_next_step_handler(message, lambda m: save_user(m, name))

def save_user(message, name):
    if not message.contact: return start(message)
    db_op("INSERT INTO users (id, name, phone) VALUES (?, ?, ?)", (message.from_user.id, name, message.contact.phone_number))
    bot.send_message(message.from_user.id, "✅ Tayyor!", reply_markup=main_menu())

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    uid = message.from_user.id
    text = message.text
    u = db_op("SELECT debt, balance, games_played, total_nasiya_taken, name, phone FROM users WHERE id=?", (uid,), is_select=True)
    if not u: return
    debt, balance, g_played, t_nasiya, name, phone = u[0]

    if text == "👤 Profil":
        bot.send_message(uid, f"👤 **PROFIL**\n\n💰 Balans: {balance:,.0f} s\n🔴 Qarz: {debt:,.0f} s\n🆔 ID: `{uid}`")

    elif text == "🎰 O'yinlar":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🎰 Slot (100k)", "🎯 Dart (50k)", "🔙 Orqaga")
        bot.send_message(uid, "O'yinni tanlang:", reply_markup=markup)

    elif text in ["🎰 Slot (100k)", "🎯 Dart (50k)"]:
        cost = 100000 if "100k" in text else 50000
        if balance < cost: bot.send_message(uid, "⚠️ Mablag' yetarli emas!")
        else:
            g_played += 1
            db_op("UPDATE users SET balance = balance - ?, games_played = ? WHERE id=?", (cost, g_played, uid))
            res = bot.send_dice(uid, emoji='🎰' if "Slot" in text else '🎯')
            time.sleep(4)
            if g_played % 4 == 0:
                db_op("UPDATE users SET balance = balance + ? WHERE id=?", (MAX_YUTUQ, uid))
                bot.send_message(uid, f"🎉 YUTDINGIZ! +{MAX_YUTUQ:,} s")
            else: bot.send_message(uid, "😔 Yutqazdingiz.")

    elif text == "💸 Nasiya olish":
        if debt > 0:
            bot.send_message(uid, "❌ Avvalgi qarzingizni to'lang!")
            return
        limit = QARZ_LIMITI_1 if t_nasiya == 0 else QARZ_LIMITI_2
        bot.send_message(uid, f"Summani kiriting (Max: {limit:,} s):")
        bot.register_next_step_handler(message, lambda m: confirm_nasiya(m, limit))

    elif text == "🔙 Orqaga":
        bot.send_message(uid, "Asosiy menyu", reply_markup=main_menu())

# --- QARZNI TASDIQLASH BOSQICHI ---
def confirm_nasiya(message, limit):
    try:
        amt = float(message.text)
        if 10000 <= amt <= limit:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("Tastiqlayman ✅", callback_data=f"conf_y_{amt}"))
            markup.add(types.InlineKeyboardButton("Bekor qilish ❌", callback_data="conf_n"))
            
            rules = (f"⚠️ **DIQQAT: QARZ SHARTNOMASI**\n\n"
                     f"Summa: {amt:,.0f} so'm\n"
                     f"1. Qarzni 12 soat ichida to'lashga va'da beraman.\n"
                     f"2. To'lamasam, har soatda 5% penya qo'shilishiga roziman.\n"
                     f"3. Shaxsingizga doir barcha ma'lumotlar ochiqlanishiga rozilik berasiz.\n\n"
                     f"Rozimisiz?")
            bot.send_message(message.chat.id, rules, reply_markup=markup, parse_mode="Markdown")
        else: bot.send_message(message.chat.id, "Xato summa!")
    except: bot.send_message(message.chat.id, "Faqat raqam yozing!")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    uid = call.from_user.id
    d = call.data.split("_")
    
    if d[0] == "conf":
        if d[1] == "y":
            amt = float(d[2])
            u = db_op("SELECT name, phone FROM users WHERE id=?", (uid,), is_select=True)[0]
            
            # Bazani yangilash
            db_op("UPDATE users SET balance = balance + ?, debt = debt + ?, debt_time = ?, total_nasiya_taken = total_nasiya_taken + 1 WHERE id=?", 
                  (amt, amt, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), uid))
            
            bot.edit_message_text("✅ Qarz olindi. Hisobingiz to'ldirildi.", call.message.chat.id, call.message.message_id)
            
            # ADMINGA MA'LUMOT YUBORISH
            admin_msg = (f"📑 **YANGI QARZ TASDIQLANDI**\n\n"
                         f"👤 Ism: {u[0]}\n"
                         f"📞 Tel: {u[1]}\n"
                         f"💰 Summa: {amt:,.0f} so'm\n"
                         f"🆔 ID: `{uid}`\n"
                         f"✅ Foydalanuvchi barcha shartlarga rozilik berdi (Tastiqladi).")
            bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown")
            
        else:
            bot.edit_message_text("❌ Bekor qilindi.", call.message.chat.id, call.message.message_id)

    # ... (Avvalgi to'lov va yechish callbacklari shu yerda qoladi)

bot.infinity_polling()
        
        
    
                



        

    
            
        
        
    
  
