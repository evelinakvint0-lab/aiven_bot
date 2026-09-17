import os
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# Включаем логирование, чтобы видеть ошибки в Render
logging.basicConfig(level=logging.INFO)

# Токен берем из переменных окружения Render
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_PATH = "/webhook"
# Render сам подставляет свой адрес в эту переменную
BASE_URL = os.getenv("RENDER_EXTERNAL_URL")

if not BOT_TOKEN:
    raise ValueError("Токен BOT_TOKEN не найден!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message()
async def echo(message):
    # Здесь Айвен отвечает в стиле дворецкого
    await message.answer("Приветствую вас, сударыня! Я Айвен, ваш покорный слуга. Чем могу быть полезен?")

async def on_startup(bot: Bot):
    # Устанавливаем вебхук при запуске
    await bot.set_webhook(f"{BASE_URL}{WEBHOOK_PATH}")
    logging.info(f"Вебхук установлен на {BASE_URL}{WEBHOOK_PATH}")

def main():
    app = web.Application()
    webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    
    dp.startup.register(on_startup)
    
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

if __name__ == "__main__":
    main()
