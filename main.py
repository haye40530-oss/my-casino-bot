import telebot
from telebot import types
import re
import threading
import time
from datetime import datetime, timedelta

# --- KONFIGURATSIYA ---
TOKEN = '8609558089:AAExgvs1_XR5jlj9RGC55zZStvc7nV_Z6hE'
ADMIN_ID = 8299021738 
bot = telebot.TeleBot(TOKEN)

users = {}

def get_user(uid):
    if uid not in users:
        users[uid] = {
            'reg': False, 'name': '', 'phone': '', 'balance': 0, 
            'loan': 0, 'loan_time': None, 'last_scare': None
        }
    return users[uid]

# --- 1. QARZ VA PENYA HISOBLASH ---
def calculate_loan(uid):
    user = get_user(uid)
    penya = 0
    if user['loan'] > 0 and user['loan_time']:
        passed = datetime.now() - user['loan_time']
        hours = int(passed.total_seconds() // 3600)
        if hours > 12:
            # 12 soatdan keyin har 1 soatda 5% penya
            penya = int(user['loan'] * 0.05 * (hours - 12))
    return user['loan'], penya, (user['loan'] + penya)

# --- 2. QARZ OLISH (OGOHLANTIRISH BILAN) ---
@bot.message_handler(func=lambda m: m.text == "💸 Qarz olish")
def loan_start(message):
    user = get_user(message.chat.id)
    if user['loan'] > 0:
        bot.send_message(message.chat.id, "⚠️ Sizda yopilmagan qarz bor! Avvalgisini to'lamasdan yangi qarz olish mumkin emas.")
        return

    # Qarz olishdan oldin ogohlantirish
    warning_text = (
        "⚠️ **DIQQAT: QARZ OLISH SHARTLARI!**\n\n"
        "1. Qarz muddati: **12 soat** (0%).\n"
        "2. 12 soatdan keyin: Har soatda **5% penya** qo'shiladi.\n"
        "3. To'lanmasa: Har 2 soatda qat'iy ogohlantirish xabarlari yuboriladi.\n\n"
        "Shartlarga rozimisiz? Rozilikingizni tasdiqlash uchun qarz miqdorini yozing (100,000 - 1,000,000):"
    )
    msg = bot.send_message(message.chat.id, warning_text, parse_mode="Markdown")
    bot.register_next_step_handler(msg, loan_process)

def loan_process(message):
    try:
        amt = int(re.sub(r'\D', '', message.text))
        if 100000 <= amt <= 1000000:
            user = get_user(message.chat.id)
            user['loan'] = amt
            user['balance'] += amt
            user['loan_time'] = datetime.now()
            bot.send_message(message.chat.id, f"✅ {amt:,} UZS qarz berildi. 12 soat ichida qaytaring!")
            bot.send_message(ADMIN_ID, f"🛡 **Qarz olindi:**\nUser: {user['name']}\nSumma: {amt:,} UZS")
        else:
            bot.send_message(message.chat.id, "❌ Limit: 100,000 - 1,000,000 UZS.")
    except:
        bot.send_message(message.chat.id, "⚠️ Faqat raqam kiriting!")

# --- 3. QARZNI TO'LASH (ADMIN TASDIQI BILAN) ---
@bot.message_handler(func=lambda m: m.text == "🏦 Qarzni to'lash")
def pay_loan_init(message):
    l, p, total = calculate_loan(message.chat.id)
    if l == 0:
        bot.send_message(message.chat.id, "✅ Sizning qarzingiz yo'q.")
        return
    
    msg = bot.send_message(message.chat.id, f"💰 Jami qarzingiz (penya bilan): {total:,} UZS.\nQancha to'lamoqchisiz?")
    bot.register_next_step_handler(msg, pay_loan_request)

def pay_loan_request(message):
    try:
        amt = int(re.sub(r'\D', '', message.text))
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Tastiqlayman", callback_data=f"pay_ok_{message.chat.id}_{amt}"),
                   types.InlineKeyboardButton("❌ XATO", callback_data=f"pay_no_{message.chat.id}"))
        
        # Adminga tasdiqlash uchun yuborish
        bot.send_message(ADMIN_ID, f"🏦 **Qarz to'lash so'rovi!**\nFoydalanuvchi: {message.chat.id}\nSumma: {amt:,} UZS", reply_markup=markup)
        bot.send_message(message.chat.id, "⌛️ To'lov so'rovi adminga yuborildi. Tasdiqlashni kiting.")
    except:
        bot.send_message(message.chat.id, "⚠️ Miqdorni raqamda yozing!")

# --- 4. CALLBACK (ADMIN TASDIQLASHI UCHUN) ---
@bot.callback_query_handler(func=lambda c: c.data.startswith('pay_'))
def pay_callback(call):
    data = call.data.split('_')
    uid = int(data[2])
    if data[1] == 'ok':
        amt = int(data[3])
        user = get_user(uid)
        # Qarzni ayirish mantiqi
        if amt >= user['loan']:
            user['loan'] = 0
            user['loan_time'] = None
        else:
            user['loan'] -= amt
        
        bot.send_message(uid, f"✅ Qarz to'lovingiz tasdiqlandi! Balansdan {amt:,} UZS ayirildi.")
        bot.edit_message_text(f"✅ Tasdiqlandi ({amt:,} UZS)", call.message.chat.id, call.message.message_id)
    else:
        bot.send_message(uid, "❌ Qarz to'lovi rad etildi (Xato miqdor).")
        bot.edit_message_text("❌ Rad etildi", call.message.chat.id, call.message.message_id)

# --- 5. QO'RQITISH TIZIMI (HAR 2 SOATDA) ---
def scare_loop():
    while True:
        now = datetime.now()
        for uid, u in users.items():
            if u['loan'] > 0 and u['loan_time']:
                if (now - u['loan_time']) > timedelta(hours=12):
                    if not u['last_scare'] or (now - u['last_scare']) > timedelta(hours=2):
                        try:
                            bot.send_message(uid, "‼️ **OGOHLANTIRISH!** Qarz muddati o'tdi. Har soatda 5% penya qo'shilmoqda! Tezroq to'lang!")
                            u['last_scare'] = now
                        except: pass
        time.sleep(60)

threading.Thread(target=scare_loop, daemon=True).start()

# --- ASOSIY MENYU ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎰 777 O'yini", "💰 Balans")
    markup.row("💳 Pul yechish", "💸 Qarz olish")
    markup.row("🏦 Qarzni to'lash", "ℹ️ Ma'lumot")
    return markup

@bot.message_handler(commands=['start'])
def start_bot(message):
    bot.send_message(message.chat.id, "Xush kelibsiz!", reply_markup=main_menu())

bot.polling(none_stop=True)

    
  
