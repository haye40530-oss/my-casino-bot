import telebot
from telebot import types

# Siz taqdim etgan Token joylashtirildi
TOKEN = '8609558089:AAExgvs1_XR5jlj9RGC55zZStvc7nV_Z6hE'
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    # Asosiy menyu tugmalari
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    item1 = types.KeyboardButton("🎰 O'yinni boshlash")
    item2 = types.KeyboardButton("👤 Profil")
    item3 = types.KeyboardButton("ℹ️ Ma'lumot")
    item4 = types.KeyboardButton("🏆 Reyting")
    markup.add(item1, item2, item3, item4)
    
    welcome_text = f"Salom {message.from_user.first_name}! 🎰 Casino botga xush kelibsiz!\n\nO'yinni boshlash uchun quyidagi tugmalardan birini tanlang."
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if message.text == "🎰 O'yinni boshlash":
        bot.send_message(message.chat.id, "💰 O'yin menyusi tayyorlanmoqda... Tez orada yangi o'yinlar qo'shiladi!")
    
    elif message.text == "👤 Profil":
        user_info = (f"👤 Sizning profilingiz:\n\n"
                     f"🆔 ID: {message.from_user.id}\n"
                     f"📝 Ism: {message.from_user.first_name}\n"
                     f"💰 Balans: 0 $")
        bot.send_message(message.chat.id, user_info)
    
    elif message.text == "ℹ️ Ma'lumot":
        bot.send_message(message.chat.id, "📖 Bu bot orqali siz turli xil virtual kazino o'yinlarini o'ynashingiz mumkin. Bot hozirda test rejimida ishlamoqda.")
    
    elif message.text == "🏆 Reyting":
        bot.send_message(message.chat.id, "📊 Hozircha reyting tizimi shakllantirilmagan.")
    
    else:
        bot.send_message(message.chat.id, "Tushunmadim, iltimos menyudagi tugmalardan foydalaning.")

# Botni uzluksiz ishlatish
if __name__ == "__main__":
    print("Bot ishga tushdi...")
    bot.polling(none_stop=True)
    
  
