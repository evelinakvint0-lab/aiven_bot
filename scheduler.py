import asyncio
import logging
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot

from config import config
from ai import ask_aiiven
from prompts import PROACTIVE_PROMPTS, MORNING_PROMPT, EVENING_PROMPT
from storage import read, mutate

TZ = ZoneInfo("Asia/Almaty")

MODE_SETTINGS = {
    "quiet":  {"max_pings": 1, "interval_min": (180, 480)},
    "normal": {"max_pings": 3, "interval_min": (60, 240)},
    "clingy": {"max_pings": 8, "interval_min": (30, 120)},
}


async def proactive_loop(bot: Bot):
    while True:
        try:
            await _proactive_tick(bot)
        except Exception as e:
            logging.error(f"proactive error: {e}")
        await asyncio.sleep(900)


async def _proactive_tick(bot: Bot):
    now = datetime.now(TZ)

    def _reset_daily(data: dict) -> None:
        today = now.strftime("%Y-%m-%d")
        if data.get("ping_day") != today:
            data["ping_day"] = today
            data["ping_count_today"] = 0
            data["morning_sent"] = False
            data["evening_sent"] = False

    data = await mutate(_reset_daily)

    mode = data.get("mode", "normal")
    settings = MODE_SETTINGS.get(mode, MODE_SETTINGS["normal"])

    if now.hour >= 23 or now.hour < 8:
        return

    if data.get("ping_count_today", 0) >= settings["max_pings"]:
        return

    next_ping_iso = data.get("next_ping_at")
    if next_ping_iso:
        try:
            if now < datetime.fromisoformat(next_ping_iso):
                return
        except ValueError:
            pass

    last_user_iso = data.get("last_user_message")
    if last_user_iso:
        try:
            if (now - datetime.fromisoformat(last_user_iso)) < timedelta(minutes=30):
                return
        except ValueError:
            pass

    prompt = None
    mark_morning = False
    mark_evening = False

    if 8 <= now.hour < 10 and not data.get("morning_sent"):
        prompt = MORNING_PROMPT
        mark_morning = True
    elif 21 <= now.hour < 23 and not data.get("evening_sent"):
        prompt = EVENING_PROMPT
        mark_evening = True
    else:
        prompt = random.choice(PROACTIVE_PROMPTS)

    text = await ask_aiiven(prompt)

    try:
        await bot.send_message(config.owner_id, text)
    except Exception as e:
        logging.error(f"send proactive failed: {e}")
        return

    delay = random.randint(*settings["interval_min"])

    def _update(data: dict) -> None:
        data["ping_count_today"] = data.get("ping_count_today", 0) + 1
        data["last_bot_message"] = now.isoformat()
        data["next_ping_at"] = (now + timedelta(minutes=delay)).isoformat()
        if mark_morning:
            data["morning_sent"] = True
        if mark_evening:
            data["evening_sent"] = True

    await mutate(_update)
    logging.info(f"Proactive sent: {text[:60]}")


async def holiday_loop(bot: Bot):
    while True:
        try:
            await _holiday_tick(bot)
        except Exception as e:
            logging.error(f"holiday error: {e}")
        await asyncio.sleep(1800)


async def _holiday_tick(bot: Bot):
    now = datetime.now(TZ)
    if not (9 <= now.hour < 11):
        return

    today = now.strftime("%d.%m")
    sent_key = f"holiday_sent_{now.strftime('%Y-%m-%d')}"

    data = await read()
    if data.get(sent_key):
        return
    memory = data.get("memory", {})
    if today not in memory:
        return

    event = memory[today]
    greeting = await ask_aiiven(
        f"Сегодня {event}. Напиши поздравление госпоже в своём стиле. "
        f"Коротко, 2-3 предложения."
    )
    try:
        await bot.send_message(config.owner_id, f"🎉 {greeting}")
    except Exception as e:
        logging.error(f"holiday send failed: {e}")
        return

    def _mark(data: dict) -> None:
        data[sent_key] = True

    await mutate(_mark)
    logging.info(f"Holiday sent: {event}")
