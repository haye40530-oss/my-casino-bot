import telebot
import random
import sqlite3
import time
from telebot import types

# --- SOZLAMALAR ---
# O'zingizning bot tokengizni qo'ying
TOKEN = '8609558089:AAExgvs1_XR5jlj9RGC55zZStvc7nV_Z6hE'
ADMIN_ID = 8299021738 
UZB_CARD = "9860 6067 5582 9722"
VISA_CARD = "4916 9907 0644 0861"

bot = telebot.TeleBot(TOKEN)

# --- BAZA BILAN ISHLASH ---
def get_db():
    conn = sqlite3.connect('casino_pro_final.db', check_same_thread=False)
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, lang TEXT, bal INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

init_db()

# --- ASOSIY MENYU ---
def main_menu(lang):
    kb = types.InlineKeyboardMarkup(row_width=2)
    t = {
        'uz': ["💰 Depozit", "📦 6 ta Quti", "🎡 Omad Barabani", "👤 Profil"],
        'ru': ["💰 Депозит", "📦 6 Коробок", "🎡 Колесо Удачи", "👤 Профиль"],
        'en': ["💰 Deposit", "📦 6 Boxes", "🎡 Lucky Wheel", "👤 Profile"]
    }[lang]
    kb.add(types.InlineKeyboardButton(t[0], callback_data="dep"),
           types.InlineKeyboardButton(t
  
