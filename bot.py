import os
import telebot
import requests
import whois
from flask import Flask, request

# Берем токен из переменных окружения Render
BOT_TOKEN = os.environ.get('9082313783:AAG0d10RC63ZTy66xV4nXlfcDp6QOgYH6Zk')
bot = telebot.TeleBot(9082313783:AAG0d10RC63ZTy66xV4nXlfcDp6QOgYH6Zk)
app = Flask(__name__)

# --- Команды бота ---
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Привет! Я OSINT-бот. Пиши:\n/nick username\n/domain example.com\n/phone +79001234567")

@bot.message_handler(commands=['nick'])
def search_nick(message):
    nick = message.text.replace('/nick', '').strip()
    if not nick:
        bot.reply_to(message, "Напиши ник: /nick username")
        return

    sites = {
        "Telegram": f"https://t.me/{nick}",
        "GitHub": f"https://github.com/{nick}",
        "TikTok": f"https://tiktok.com/@{nick}",
        "Instagram": f"https://instagram.com/{nick}",
        "VK": f"https://vk.com/{nick}"
    }
    
    result = f"👤 **Результаты по нику {nick}:**\n\n"
    for site, url in sites.items():
        try:
            r = requests.get(url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
            if r.status_code == 200:
                result += f"✅ {site}: {url}\n"
            else:
                result += f"❌ {site}: Не найден\n"
        except:
            result += f"⚠️ {site}: Ошибка\n"
            
    bot.send_message(message.chat.id, result, parse_mode='Markdown')

@bot.message_handler(commands=['domain'])
def search_domain(message):
    domain = message.text.replace('/domain', '').strip()
    if not domain:
        bot.reply_to(message, "Напиши домен: /domain example.com")
        return

    try:
        w = whois.whois(domain)
        result = f"🌐 **Данные по домену {domain}:**\n\n"
        result += f"👤 Владелец: {w.name if w.name else 'Скрыто'}\n"
        result += f"📅 Регистрация: {w.creation_date if w.creation_date else 'Нет данных'}\n"
        result += f"🏢 Организация: {w.org if w.org else 'Скрыто'}\n"
        result += f"📧 Email: {w.emails if w.emails else 'Скрыто'}\n"
        bot.send_message(message.chat.id, result, parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

@bot.message_handler(commands=['phone'])
def search_phone(message):
    phone = message.text.replace('/phone', '').strip()
    if not phone:
        bot.reply_to(message, "Напиши номер: /phone +79001234567")
        return

    wa_link = f"https://wa.me/{phone.replace('+', '')}"
    tg_link = f"https://t.me/{phone.replace('+', '')}"
    
    result = f"📱 **Открытые мессенджеры:**\n\n"
    result += f"🟢 WhatsApp: {wa_link}\n"
    result += f"🔵 Telegram: {tg_link}\n\n"
    result += "⚠️ *Данные паспорта и прописки не ищу.*"
    bot.send_message(message.chat.id, result, parse_mode='Markdown')

# --- Вебхук для Render ---
@app.route('/', methods=['GET'])
def index():
    return "Bot is alive!"

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        return 'Forbidden', 403

# Установка вебхука при старте
@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    # Замени URL на свой, который выдаст Render!
    render_url = os.environ.get('RENDER_EXTERNAL_URL')
    if render_url:
        bot.remove_webhook()
        bot.set_webhook(url=f"{render_url}/{BOT_TOKEN}")
        return f"Webhook set to {render_url}", 200
    return "RENDER_EXTERNAL_URL not found", 400
