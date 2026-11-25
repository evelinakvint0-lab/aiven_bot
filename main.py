import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from aiohttp import web
from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.types import BotCommand, Message
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from config import config
from handlers import router
from scheduler import proactive_loop, holiday_loop
from storage import mutate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

TZ = ZoneInfo("Asia/Almaty")

bot = Bot(token=config.bot_token)
dp = Dispatcher()


class LastMessageMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if isinstance(event, Message) and event.from_user and event.from_user.id == config.owner_id:
            try:
                def _mut(d: dict) -> None:
                    d["last_user_message"] = datetime.now(TZ).isoformat()
                await mutate(_mut)
            except Exception as e:
                logging.error(f"middleware error: {e}")
        return await handler(event, data)


router.message.middleware(LastMessageMiddleware())
dp.include_router(router)


async def on_startup(bot: Bot):
    await bot.set_webhook(
        f"{config.base_url}{config.webhook_path}",
        allowed_updates=["message"],
        drop_pending_updates=False,
    )
    await bot.set_my_commands([
        BotCommand(command="start", description="Приветствие"),
        BotCommand(command="help", description="Справка"),
        BotCommand(command="mode", description="Режим навязчивости"),
        BotCommand(command="remember", description="Запомнить дату"),
        BotCommand(command="memory", description="Мои даты"),
        BotCommand(command="reset", description="Сбросить диалог"),
        BotCommand(command="backup", description="Выгрузить память"),
        BotCommand(command="myid", description="Мой ID"),
    ])
    asyncio.create_task(proactive_loop(bot))
    asyncio.create_task(holiday_loop(bot))
    logging.info("Бот запущен")


async def on_shutdown(bot: Bot):
    await bot.delete_webhook()


async def health(request):
    return web.Response(text="OK")


def main():
    app = web.Application()
    app.router.add_get("/", health)
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=config.webhook_path)
    setup_application(app, dp, bot=bot)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    web.run_app(app, host="0.0.0.0", port=config.port)


if __name__ == "__main__":
    main()
