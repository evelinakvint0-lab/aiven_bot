import os
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.enums import ChatType
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OWNER_ID = int(os.getenv("OWNER_ID", 0))
WEBHOOK_PATH = "/webhook"
BASE_URL = os.getenv("RENDER_EXTERNAL_URL")

if not BOT_TOKEN:
    raise ValueError("Токен BOT_TOKEN не найден!")
if not GEMINI_API_KEY:
    raise ValueError("Ключ GEMINI_API_KEY не найден!")

# Настраиваем "мозг" Айвена
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Функция для общения с нейросетью
async def ask_aiiven(prompt: str, context: str = "") -> str:
    system_instruction = (
        "Ты — Айвен, цифровой дворецкий Эвелины. Ты прибыл из XVIII века и теперь живешь в Telegram. "
        "Общайся вежливо, галантно, используй обращения 'сударыня', 'госпожа'. "
        "Будь остроумным, но почтительным. Не используй современный сленг. "
    )
    full_prompt = f"{system_instruction}\n\n{context}\n\nСообщение: {prompt}\nОтвет Айвена:"
    
    try:
        response = await model.generate_content_async(full_prompt)
        return response.text
    except Exception as e:
        logging.error(f"Ошибка нейросети: {e}")
        return "Прошу прощения, сударыня, мои мыслительные процессы дали сбой. Извольте повторить чуть позже."

# --- КОМАНДЫ ДЛЯ ЛИЧНОГО ЧАТА С БОТОМ ---

@dp.message(CommandStart())
async def cmd_start(message):
    await message.answer("Приветствую вас, сударыня! Я Айвен, ваш покорный слуга. Теперь мой разум стал острее, и я готов к любым беседам!")

@dp.message(Command("help"))
async def cmd_help(message):
    help_text = (
        "Вот что я умею, сударыня:\n\n"
        "/start - Начать беседу\n"
        "/help - Показать этот список\n"
        "/myid - Узнать свой Telegram ID\n\n"
        "А ещё я теперь умею поддерживать любую беседу благодаря нейросети!"
    )
    await message.answer(help_text)

@dp.message(Command("myid"))
async def cmd_myid(message):
    await message.answer(f"Ваш Telegram ID: {message.from_user.id}")

# Обработчик всех текстовых сообщений боту
@dp.message()
async def echo(message):
    if not message.text:
        return
        
    # Отправляем сообщение в нейросеть
    response_text = await ask_aiiven(message.text)
    await message.answer(response_text)

# --- РЕЖИМ СЕКРЕТАРЯ (TELEGRAM BUSINESS) ---

@dp.business_message()
async def business_echo(message):
    # 1. Если пишет сама Эвелина — молчим
    if OWNER_ID != 0 and message.from_user.id == OWNER_ID:
        return
    
    # 2. Если сообщение пришло из группы — молчим
    if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL):
        return
    
    # 3. Если это текст, генерируем ответ через нейросеть
    if message.text:
        context = f"Тебе пишет {message.from_user.full_name}. Ты отвечаешь от лица секретаря Эвелины."
        ai_response = await ask_aiiven(message.text, context)
        await message.answer(ai_response)
        
        # 4. Пересылаем уведомление ВАМ в личку бота
        if OWNER_ID != 0:
            notification = f"📩 Сударыня, вам новое сообщение от {message.from_user.full_name}:\n\n«{message.text}»\n\nМой ответ: {ai_response}"
            try:
                await bot.send_message(chat_id=OWNER_ID, text=notification)
            except Exception as e:
                logging.error(f"Не удалось отправить уведомление: {e}")

# --- СЛУЖЕБНЫЕ ФУНКЦИИ ---

async def on_startup(bot: Bot):
    await bot.set_webhook(
        f"{BASE_URL}{WEBHOOK_PATH}",
        allowed_updates=["message", "business_connection", "business_message"]
    )
    logging.info(f"Вебхук установлен на {BASE_URL}{WEBHOOK_PATH}")

async def health_check(request):
    return web.Response(text="OK")

def main():
    app = web.Application()
    app.router.add_get("/", health_check)
    
    webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    
    dp.startup.register(on_startup)
    
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

if __name__ == "__main__":
    main()
