import os
import telebot
import requests
import whois
from flask import Flask, request

# Берем токен из переменных окружения Render, а если их нет - берем твой (для теста)
BOT_TOKEN = os.environ.get('BOT_TOKEN', '9082313783:AAG0d10RC63ZTy66xV4nXlfcDp6QOgYH6Zk')

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# --- Команды бота ---
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Привет! Я OSINT-бот. Пиши:\n/nick username\n/domain example.com\n/nick +79001234567")

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
    
    # Используем HTML-разметку, она безопаснее для ников с дефисами и подчеркиваниями
    result = f"👤 <b>Результаты по нику {nick}:</b>\n\n"
    for site, url in sites.items():
        try:
            r = requests.get(url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
            if r.status_code == 200:
                result += f"✅ {site}: {url}\n"
            else:
                result += f"❌ {site}: Не найден\n"
        except:
            result += f"⚠️ {site}: Ошибка сети\n"
            
    bot.send_message(message.chat.id, result, parse_mode='HTML')

@bot.message_handler(commands=['domain'])
def search_domain(message):
    domain = message.text.replace('/domain', '').strip()
    if not domain:
        bot.reply_to(message, "Напиши домен: /domain example.com")
        return

    try:
        w = whois.whois(domain)
        result = f"🌐 <b>Данные по домену {domain}:</b>\n\n"
        result += f"👤 Владелец: {w.name if w.name else 'Скрыто'}\n"
        result += f"📅 Регистрация: {w.creation_date if w.creation_date else 'Нет данных'}\n"
        result += f"🏢 Организация: {w.org if w.org else 'Скрыто'}\n"
        result += f"📧 Email: {w.emails if w.emails else 'Скрыто'}\n"
        bot.send_message(message.chat.id, result, parse_mode='HTML')
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
    
    result = f"📱 <b>Открытые мессенджеры:</b>\n\n"
    result += f"🟢 WhatsApp: {wa_link}\n"
    result += f"🔵 Telegram: {tg_link}\n\n"
    result += "⚠️ <i>Данные паспорта и прописки не ищу.</i>"
    bot.send_message(message.chat.id, result, parse_mode='HTML')
@bot.message_handler(commands=['doks'])
def handle_doks(message):
    user_query = message.text.replace('/doks', '').strip()
    if not user_query:
        bot.reply_to(message, "Напиши что искать: /doks +79991234567")
        return

    bot.reply_to(message, "🕵️‍♂️ <b>Этап 1: Первичный поиск (номер/ник)...</b>", parse_mode='HTML')

    # 1. ИИ создает запросы для первичного поиска
    queries = ask_groq_agent(f"Придумай 5 запросов в Google, чтобы найти имя и профили по этому запросу: {user_query}")
    queries_list = [q.strip() for q in queries.split('\n') if q.strip()]

    all_results = ""
    for q in queries_list[:5]:
        all_results += search_google(q)

    if not all_results:
        bot.reply_to(message, "❌ Первичный поиск не дал результатов.")
        return

    bot.reply_to(message, "🧠 <b>Этап 2: Анализ и поиск геолокации...</b>\nИИ ищет связи с городами и улицами...", parse_mode='HTML')

    # 2. ИИ анализирует первичные данные и пытается вытащить имя
    prompt_analysis = f"""
    Пользователь ищет инфу по: {user_query}.
    Вот результаты поиска: {all_results}.
    
    1. Найди настоящее имя/фамилию человека (если это возможно).
    2. Если нашел имя, напиши мне 3 новых поисковых запроса, чтобы найти его город, работу и улицу (например: "Иван Иванов site:vk.com", "Иван Иванов адрес", "Иван Иванов дом"). 
    3. Верни ТОЛЬКО список из 3-х новых запросов, если нашел имя. Если имя не нашел — напиши "НЕТ ИМЕНИ".
    """
    
    deep_queries = ask_groq_agent(prompt_analysis)

    # 3. Если ИИ нашел имя, делаем второй каскад запросов
    if "НЕТ ИМЕНИ" not in deep_queries:
        deep_list = [q.strip() for q in deep_queries.split('\n') if q.strip()]
        bot.reply_to(message, f"🎯 Найдено имя! ИИ запускает каскадный поиск: {deep_list[0]}...")
        
        for q in deep_list[:3]:
            all_results += search_google(q)
    else:
        bot.reply_to(message, "⚠️ Имя не найдено, но продолжаю анализ.")

    bot.reply_to(message, "🧠 <b>Этап 3: Финальный отчет...</b>", parse_mode='HTML')

    # 4. ИИ выдает финальный отчет
    final_report = ask_groq_agent(user_query, all_results)
    
    if len(final_report) > 4000:
        for i in range(0, len(final_report), 4000):
            bot.reply_to(message, final_report[i:i+4000])
    else:
        bot.reply_to(message, final_report)
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
    render_url = os.environ.get('RENDER_EXTERNAL_URL')
    if render_url:
        bot.remove_webhook()
        bot.set_webhook(url=f"{render_url}/{BOT_TOKEN}")
        return f"Webhook set to {render_url}", 200
    return "RENDER_EXTERNAL_URL not found", 400
