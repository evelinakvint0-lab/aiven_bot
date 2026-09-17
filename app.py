import os
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_PATH = "/webhook"
BASE_URL = os.getenv("RENDER_EXTERNAL_URL")

if not BOT_TOKEN:
    raise ValueError("Токен BOT_TOKEN не найден!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Этот блок отвечает, когда пишут ЛИЧНО боту
@dp.message()
async def echo(message):
    await message.answer("Приветствую вас, сударыня! Я Айвен, ваш покорный слуга. Чем могу быть полезен?")

# А этот блок отвечает, когда пишут ВАМ (в режиме секретаря)
@dp.business_message()
async def business_echo(message):
    await message.answer("Добрый день! Я цифровой дворецкий Эвелины. К сожалению, сударыня сейчас занята. Я обязательно передам ей ваше сообщение. Чем еще могу быть полезен?")

async def on_startup(bot: Bot):
    await bot.set_webhook(f"{BASE_URL}{WEBHOOK_PATH}")
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
