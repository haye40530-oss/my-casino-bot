import telebot
from telebot import types
import sqlite3
import time
from datetime import datetime, timedelta

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

# Baza jadvallari (O'yinlar hisoblagichi qo'shildi)
db_op('''CREATE TABLE IF NOT EXISTS users 
         (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, balance REAL DEFAULT 10000, 
          debt REAL DEFAULT 0, debt_time TEXT, 
          total_nasiya_taken INTEGER DEFAULT 0, referred_by INTEGER,
          games_played INTEGER DEFAULT 0)''')

def get_updated_stats(uid):
    u = db_op("SELECT debt, debt_time, balance, total_nasiya_taken, games_played FROM users WHERE id=?", (uid,), is_select=True)
    if not u: return 0, 0, 0, 0
    debt, d_time_str, balance, total_n_taken, g_played = u[0]
    
    if debt > 0 and d_time_str:
        d_time = datetime.strptime(d_time_str, "%Y-%m-%d %H:%M:%S")
        deadline = d_time + timedelta(hours=12)
        if datetime.now() > deadline:
            overdue_hours = int((datetime.now() - deadline).total_seconds() / 3600)
            if overdue_hours > 0:
                new_debt = debt * (1.05 ** overdue_hours)
                db_op("UPDATE users SET debt = ? WHERE id=?", (new_debt, uid))
                debt = new_debt
    return debt, balance, total_n_taken, g_played

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
        ref_by = args[1] if len(args) > 1 and args[1].isdigit() else None
        bot.send_message(uid, "Xush kelibsiz! Pul yechishda xatolik bo'lmasligi uchun Ism va Familiyangizni kiriting:")
        bot.register_next_step_handler(message, lambda m: get_name(m, ref_by))
    else:
        bot.send_message(uid, "💰 Xush kelibsiz!", reply_markup=main_menu())

def get_name(message, ref_by):
    name = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("📞 Telefonni tasdiqlash", request_contact=True))
    bot.send_message(message.chat.id, "Xavfsizlik uchun telefon raqamingizni yuboring:", reply_markup=markup)
    bot.register_next_step_handler(message, lambda m: save_user(m, name, ref_by))

def save_user(message, name, ref_by):
    if not message.contact: return start(message)
    db_op("INSERT INTO users (id, name, phone, referred_by) VALUES (?, ?, ?, ?)", (message.from_user.id, name, message.contact.phone_number, ref_by))
    if ref_by:
        db_op("UPDATE users SET balance = balance + ? WHERE id=?", (REFERAL_BONUS, ref_by))
        bot.send_message(ref_by, f"🎉 Do'stingiz qo'shildi! +{REFERAL_BONUS:,} s")
    bot.send_message(message.from_user.id, "✅ Tayyor!", reply_markup=main_menu())

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    uid = message.from_user.id
    text = message.text
    debt, balance, total_n_taken, g_played = get_updated_stats(uid)

    if text == "👤 Profil":
        bot.send_message(uid, f"👤 **PROFIL**\n\n💰 Balans: {balance:,.0f} s\n🔴 Qarz: {debt:,.0f} s\n🆔 ID: `{uid}`")

    elif text == "🎰 O'yinlar":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🎰 Slot (100k)", "🎯 Dart (50k)", "🔙 Orqaga")
        bot.send_message(uid, "O'yinni tanlang:", reply_markup=markup)

    elif text in ["🎰 Slot (100k)", "🎯 Dart (50k)"]:
        cost = 100000 if "100k" in text else 50000
        if balance < cost:
            bot.send_message(uid, "Mablag' yetarli emas!")
        else:
            # --- AQLLI ALGORITM (3 marta yutqazib, 1 marta yutish) ---
            g_played += 1
            db_op("UPDATE users SET balance = balance - ?, games_played = ? WHERE id=?", (cost, g_played, uid))
            
            res = bot.send_dice(uid, emoji='🎰' if "Slot" in text else '🎯')
            time.sleep(4)

            # Har 4-o'yinda yutadi (qolgan 3 tasida yutqazadi)
            if g_played % 4 == 0:
                db_op("UPDATE users SET balance = balance + ? WHERE id=?", (MAX_YUTUQ, uid))
                bot.send_message(uid, f"🎉 TABRIKLAYMIZ! Yutdingiz: +{MAX_YUTUQ:,} s")
            else:
                bot.send_message(uid, "😔 Yutqazdingiz. Keyingi safar omad keladi!")

    elif text == "💰 Pul yechish":
        if debt > 0: bot.send_message(uid, "⚠️ Qarzingiz bor!")
        elif balance < 250000: bot.send_message(uid, "⚠️ Minimal 250,000 s")
        else:
            bot.send_message(uid, "Qancha yechmoqchisiz?")
            bot.register_next_step_handler(message, withdraw_amount)

    elif text == "🔴 Qarzni to'lash":
        if debt <= 0: bot.send_message(uid, "Qarzingiz yo'q.")
        else:
            bot.send_message(uid, f"Qarz: {debt:,.0f} s\nKarta: `{KARTA_RAQAM}`\nSummani yozing:")
            bot.register_next_step_handler(message, pay_init)

    elif text == "💸 Nasiya olish":
        limit = QARZ_LIMITI_1 if total_n_taken == 0 else QARZ_LIMITI_2
        bot.send_message(uid, f"⚠️ 12 soatdan keyin har soatga 5% jarima!\nLimit: {limit:,} s. Summa:")
        bot.register_next_step_handler(message, lambda m: process_nasiya(m, limit))

    elif text == "👥 Do'stlarni taklif qilish":
        link = f"https://t.me/{(bot.get_me()).username}?start={uid}"
        bot.send_message(uid, f"Har bir do'st uchun {REFERAL_BONUS:,} s! Havola:\n{link}")

    elif text == "👨‍💻 Admin murojaat":
        bot.send_message(uid, f"Admin: {ADMIN_LINK}")

    elif text == "🔙 Orqaga":
        bot.send_message(uid, "Asosiy menyu", reply_markup=main_menu())

# --- ADMIN PANEL (KUCHAYTIRILGAN) ---
@bot.message_handler(commands=['malumot', 'backup', 'qarz_ber', 'qarz_ol', 'plus_balans', 'user'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID: return
    c = message.text.split()
    
    # 1. Barcha foydalanuvchilar ro'yxati (Agar bermayotgan bo'lsa, try-except bilan)
    if c[0] == '/malumot':
        try:
            res = db_op("SELECT id, name, balance, debt FROM users", is_select=True)
            if not res:
                bot.send_message(ADMIN_ID, "Bazada foydalanuvchilar yo'q.")
                return
            out = "📊 **FOYDALANUVCHILAR RO'YXATI**\n\n"
            for r in res:
                out += f"🆔 `{r[0]}` | 👤 {r[1]} | 💰 {r[2]:,.0f} | 🔴 {r[3]:,.0f}\n---\n"
            # Telegramda xabar uzunligi 4096 belgidan oshmasligi kerak
            for i in range(0, len(out), 4000):
                bot.send_message(ADMIN_ID, out[i:i+4000], parse_mode="Markdown")
        except Exception as e:
            bot.send_message(ADMIN_ID, f"Xato yuz berdi: {e}")

    # 2. Aniq bir user ma'lumotlarini ID orqali ko'rish
    elif c[0] == '/user' and len(c) == 2:
        u = db_op("SELECT * FROM users WHERE id=?", (c[1],), is_select=True)
        if u:
            r = u[0]
            bot.send_message(ADMIN_ID, f"👤 **Ma'lumot:**\nID: `{r[0]}`\nIsm: {r[1]}\nTel: {r[2]}\nBalans: {r[3]:,}\nQarz: {r[4]:,}\nNasiyalar: {r[6]} ta", parse_mode="Markdown")
        else: bot.send_message(ADMIN_ID, "Topilmadi.")

    # 3. Qarz va Balans boshqaruvi
    elif len(c) >= 3:
        target, amt = int(c[1]), float(c[2])
        if 'qarz_ber' in c[0]:
            db_op("UPDATE users SET debt = debt + ?, debt_time = ? WHERE id=?", (amt, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), target))
        elif 'qarz_ol' in c[0]:
            db_op("UPDATE users SET debt = 0 WHERE id=?", (target,))
        elif 'plus_balans' in c[0]:
            db_op("UPDATE users SET balance = balance + ? WHERE id=?", (amt, target))
        bot.send_message(ADMIN_ID, "Amal bajarildi! ✅")

# --- QOLGAN FUNKSIYALAR ---
def withdraw_amount(message):
    try:
        amt = float(message.text)
        bot.send_message(message.chat.id, "💳 Karta raqamini kiriting:")
        bot.register_next_step_handler(message, lambda m: withdraw_owner(m, amt))
    except: bot.send_message(message.chat.id, "Faqat son yozing!")

def withdraw_owner(message, amt):
    card = message.text
    bot.send_message(message.chat.id, "👤 Karta egasining ism-familiyasi:")
    bot.register_next_step_handler(message, lambda m: withdraw_phone(m, amt, card))

def withdraw_phone(message, amt, card):
    owner = message.text
    bot.send_message(message.chat.id, "📞 Karta egasining telefoni:")
    bot.register_next_step_handler(message, lambda m: withdraw_final(m, amt, card, owner))

def withdraw_final(message, amt, card, owner):
    phone = message.text
    uid = message.from_user.id
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Tastiqlash ✅", callback_data=f"wd_v_{uid}_{amt}"),
               types.InlineKeyboardButton("Rad etish ❌", callback_data=f"wd_x_{uid}"))
    rep = f"💸 **YECHISH**\nSumma: {amt:,}\nKarta: {card}\nEgasi: {owner}\nTel: {phone}\nID: `{uid}`"
    bot.send_message(ADMIN_ID, rep, reply_markup=markup, parse_mode="Markdown")
    bot.send_message(uid, "So'rov yuborildi.")

@bot.callback_query_handler(func=lambda call: True)
def cb(call):
    d = call.data.split("_")
    uid = int(d[2])
    if d[0] == "pay":
        if d[1] == "v":
            amt = float(d[3])
            db_op("UPDATE users SET debt = CASE WHEN debt > ? THEN debt - ? ELSE 0 END WHERE id=?", (amt, amt, uid))
            bot.send_message(uid, "✅ To'lov tasdiqlandi!")
        bot.edit_message_text("Bajarildi", call.message.chat.id, call.message.message_id)
    elif d[0] == "wd" and d[1] == "v":
        amt = float(d[3])
        db_op("UPDATE users SET balance = balance - ? WHERE id=?", (amt, uid))
        bot.send_message(uid, "✅ Pul o'tkazildi!")
        bot.edit_message_text("O'tkazildi ✅", call.message.chat.id, call.message.message_id)

def pay_init(message):
    try:
        amt = float(message.text)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Tastiqlash ✅", callback_data=f"pay_v_{message.from_user.id}_{amt}"),
                   types.InlineKeyboardButton("Rad etish ❌", callback_data=f"pay_x_{message.from_user.id}"))
        bot.send_message(ADMIN_ID, f"💳 TO'LOV: {amt:,}\nID: `{message.from_user.id}`", reply_markup=markup, parse_mode="Markdown")
        bot.send_message(message.chat.id, "Adminga yuborildi.")
    except: pass

def process_nasiya(message, limit):
    try:
        amt = float(message.text)
        if 10000 <= amt <= limit:
            db_op("UPDATE users SET balance = balance + ?, debt = debt + ?, debt_time = ?, total_nasiya_taken = total_nasiya_taken + 1 WHERE id=?", 
                  (amt, amt, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), message.from_user.id))
            bot.send_message(message.chat.id, f"✅ {amt:,} s berildi.")
        else: bot.send_message(message.chat.id, "Limit xato!")
    except: pass

bot.infinity_polling()
        
    
                



        

    
            
        
        
    
  
