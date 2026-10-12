import os, telebot, google.genai as genai
import requests, re, json
from urllib.parse import quote
from io import BytesIO

bot = telebot.TeleBot(os.environ.get('BOT_TOKEN', '111:AAA'))
client = genai.Client(api_key=os.environ.get('KEY', '222:BBB'))

DB = 'memory.json'
if os.path.exists(DB):
    with open(DB, 'r', encoding='utf-8') as f:
        history = json.load(f)
else:
    history = {}

def save():
    with open(DB, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False)

def humanize_error(e):
    s = str(e)
    if '429' in s or 'RESOURCE_EXHAUSTED' in s:
        m = re.search(r'retry in (\\d+)m(\\d+\\.?\\d*)s', s)
        if m:
            mins = int(m.group(1))
            secs = round(float(m.group(2)))
            if mins >= 30:
                return f'😔 Лимит запросов исчерпан. Бот сможет отвечать через {mins} мин {secs} сек. Можно подождать или вернуться завтра.'
            return f'⚠️ Лимит запросов исчерпан. Попробуй через {mins} мин {secs} сек.'
        return '😔 Лимит запросов на сегодня исчерпан. Бот ответит завтра. Спасибо за понимание!'
    if '503' in s or 'UNAVAILABLE' in s:
        return '⏳ Сервер ИИ сейчас перегружен. Подожди 2-3 минуты и попробуй снова.'
    if '404' in s or 'NOT_FOUND' in s:
        return '🔧 Модель временно недоступна. Мы уже чиним. Попробуй позже.'
    if '401' in s or 'Unauthorized' in s:
        return '🔐 Техническая ошибка доступа. Администратор уже уведомлён.'
    return '❌ Что-то пошло не так. Попробуй позже.'

def menu():
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row('🎨 Нарисовать', '🧹 Очистить память')
    kb.row('ℹ️ Помощь')
    return kb

@bot.message_handler(commands=['start'])
def start(m):
    history[str(m.chat.id)] = []
    save()
    bot.send_message(m.chat.id, 'Привет! Я ИИ-помощник. Выбирай кнопки или пиши текстом.', reply_markup=menu())

@bot.message_handler(commands=['help'])
def help_cmd(m):
    bot.send_message(m.chat.id, 'Просто пиши мне вопросы. Или жми кнопки внизу.\n/draw <текст> — картинка')

@bot.message_handler(commands=['clear'])
def clear(m):
    history[str(m.chat.id)] = []
    save()
    bot.send_message(m.chat.id, '🧹 Память очищена')

@bot.message_handler(func=lambda m: m.text == 'ℹ️ Помощь')
def help_btn(m):
    help_cmd(m)

@bot.message_handler(func=lambda m: m.text == '🧹 Очистить память')
def clear_btn(m):
    clear(m)

@bot.message_handler(func=lambda m: m.text == '🎨 Нарисовать')
def draw_btn(m):
    bot.send_message(m.chat.id, 'Напиши: /draw кошка в космосе')

@bot.message_handler(commands=['draw'])
def draw(m):
    p = m.text.replace('/draw','').strip()
    if not p:
        bot.send_message(m.chat.id, '/draw кошка')
        return
    bot.send_message(m.chat.id, 'Рисую...')
    try:
        tr = client.models.generate_content(model='gemini-3.8-flash', contents='Translate to English, only the translation: ' + p)
        en = tr.text.strip()
        url = 'https://image.pollinations.ai/prompt/' + quote(en) + '?width=1024&height=1024&nologo=true'
        r = requests.get(url, timeout=90)
        if r.status_code == 200 and r.headers.get('content-type', '').startswith('image'):
            bot.send_photo(m.chat.id, BytesIO(r.content), caption=p)
        else:
            bot.send_message(m.chat.id, 'Не получилось. Другой запрос?')
    except Exception as e:
        bot.send_message(m.chat.id, humanize_error(e))

@bot.message_handler(func=lambda m: True)
def h(m):
    u = str(m.chat.id)
    if u not in history: history[u] = []
    history[u].append(m.text)
    history[u] = history[u][-15:]
    save()
    try:
        r = client.models.generate_content(model='gemini-3.8-flash', contents=chr(10).join(history[u]))
        bot.send_message(m.chat.id, r.text, reply_markup=menu())
        history[u].append(r.text)
        save()
    except Exception as e:
        bot.send_message(m.chat.id, humanize_error(e), reply_markup=menu())

print('START')
bot.polling(none_stop=True)
