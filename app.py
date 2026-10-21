import os
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.enums import ChatType
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", 0))
WEBHOOK_PATH = "/webhook"
BASE_URL = os.getenv("RENDER_EXTERNAL_URL")

if not BOT_TOKEN:
    raise ValueError("Токен BOT_TOKEN не найден!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- КОМАНДЫ ДЛЯ ЛИЧНОГО ЧАТА С БОТОМ ---

@dp.message(CommandStart())
async def cmd_start(message):
    await message.answer("Приветствую вас, сударыня! Я Айвен, ваш покорный слуга.")

@dp.message(Command("help"))
async def cmd_help(message):
    help_text = (
        "Вот что я умею, сударыня:\n\n"
        "/start - Начать беседу\n"
        "/help - Показать этот список\n"
        "/notes - Мои записи\n"
        "/myid - Узнать свой Telegram ID\n"
    )
    await message.answer(help_text)

@dp.message(Command("notes"))
async def cmd_notes(message):
    await message.answer("Ваши записи пусты, сударыня.")

@dp.message(Command("myid"))
async def cmd_myid(message):
    await message.answer(f"Ваш Telegram ID: {message.from_user.id}")

@dp.message()
async def echo(message):
    await message.answer("Приветствую вас, сударыня! Я Айвен, ваш покорный слуга.")

# --- РЕЖИМ СЕКРЕТАРЯ (TELEGRAM BUSINESS) ---

@dp.business_message()
async def business_echo(message):
    # 1. Если пишет сама Эвелина — молчим
    if OWNER_ID != 0 and message.from_user.id == OWNER_ID:
        return
    
    # 2. Если сообщение пришло из группы или канала — молчим (не лезем)
    if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL):
        logging.info("Сообщение из группы. Молчим.")
        return
    
    # 3. Отвечаем собеседнику вашим красивым текстом
    text_for_guest = (
        "Создатель сейчас отсутствует. Но не извольте беспокоиться, "
        "ваше сообщение будет доставлено в целости и сохранности. "
        "С глубочайшим почтением, ваш Айвен."
    )
    await message.answer(text_for_guest)
    
    # 4. Пересылаем уведомление ВАМ в личку бота
    if OWNER_ID != 0:
        sender_name = message.from_user.full_name
        notification = f"📩 Сударыня, вам новое сообщение от {sender_name}:\n\n«{message.text}»"
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
