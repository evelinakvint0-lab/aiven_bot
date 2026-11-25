import io
import json
import logging

from aiogram import Router, F, Bot
from aiogram.enums import ChatAction
from aiogram.filters import Command, CommandStart, Filter
from aiogram.types import Message, BufferedInputFile

from config import config
from ai import ask_aiiven, ask_with_media, reset_history
from storage import read, write, mutate


class IsOwner(Filter):
    async def __call__(self, message: Message) -> bool:
        return message.from_user is not None and message.from_user.id == config.owner_id


router = Router()
router.message.filter(IsOwner())


# --- Commands ---

@router.message(CommandStart())
async def cmd_start(message: Message):
    greeting = await ask_aiiven(
    "Поприветствуй госпожу. Ты только что впервые вышел на связь. "
    "Представься коротко, в своём стиле."
    )
    await message.answer(greeting)


@router.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "🎩 <b>Мои скромные возможности, сударыня:</b>\n\n"
        "Просто пишите мне — я отвечу.\n"
        "Можно отправить <b>голосовое</b> или <b>фото</b> — я пойму.\n\n"
        "<b>Команды:</b>\n"
        "/start — приветствие\n"
        "/help — эта справка\n"
        "/mode — навязчивость (quiet / normal / clingy)\n"
        "/remember — запомнить дату: <code>/remember 15.05 День рождения</code>\n"
        "/memory — все даты\n"
        "/forget — забыть дату: <code>/forget 15.05</code>\n"
        "/reset — очистить историю диалога\n"
        "/backup — выгрузить мою память\n"
        "/restore — восстановить память (ответом на файл)\n"
        "/myid — ваш Telegram ID"
    )
    await message.answer(text, parse_mode="HTML")


@router.message(Command("myid"))
async def cmd_myid(message: Message):
    await message.answer(
        f"Ваш ID, сударыня: <code>{message.from_user.id}</code>",
        parse_mode="HTML",
    )


@router.message(Command("reset"))
async def cmd_reset(message: Message):
    await reset_history()
    await message.answer("Я всё забыл, сударыня. Кто вы вообще? ...Шучу. Начнём заново.")


@router.message(Command("remember"))
async def cmd_remember(message: Message):
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer(
            "Укажите дату и событие, сударыня: "
            "<code>/remember 15.05 День рождения</code>",
            parse_mode="HTML",
        )
        return
    date, event = args[1], args[2]

    def _mut(data: dict) -> None:
        memory = data.get("memory", {})
        memory[date] = event
        data["memory"] = memory

    await mutate(_mut)
    await message.answer(
        f"Записано, сударыня: <b>{date}</b> — {event}. "
        f"Не извольте беспокоиться, я не забуду. В отличие от некоторых.",
        parse_mode="HTML",
    )


@router.message(Command("memory"))
async def cmd_memory(message: Message):
    data = await read()
    memory = data.get("memory", {})
    if not memory:
        await message.answer(
            "Моя книга памяти пуста, сударыня. Подозрительно. "
            "Вы точно ничего не забыли мне сказать?"
        )
        return
    lines = ["<b>Важные даты, что я храню:</b>", ""]
    for d, e in sorted(memory.items()):
        lines.append(f"• <b>{d}</b> — {e}")
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("forget"))
async def cmd_forget(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "Какую дату забыть, сударыня? <code>/forget 15.05</code>",
            parse_mode="HTML",
        )
        return
    date = args[1].strip()

    data_before = await read()
    if date not in data_before.get("memory", {}):
        await message.answer("Такой даты у меня и не было, сударыня. Не пытайтесь меня запутать.")
        return

    def _mut(data: dict) -> None:
        memory = data.get("memory", {})
        memory.pop(date, None)
        data["memory"] = memory

    await mutate(_mut)
    await message.answer(
        f"Дата <b>{date}</b> изгнана из моей памяти. Надеюсь, вы знали, что делали.",
        parse_mode="HTML",
    )


@router.message(Command("mode"))
async def cmd_mode(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or args[1] not in ("quiet", "normal", "clingy"):
        await message.answer(
            "Режимы навязчивости:\n"
            "• <code>quiet</code> — почти молчу\n"
            "• <code>normal</code> — в меру\n"
            "• <code>clingy</code> — не оставлю в покое\n\n"
            "Пример: <code>/mode normal</code>",
            parse_mode="HTML",
        )
        return
    mode = args[1]

    def _mut(data: dict) -> None:
        data["mode"] = mode

    await mutate(_mut)
    comments = {
        "quiet": "Я замолкну. Почти. Постараюсь. Не обещаю.",
        "normal": "Буду в меру навязчив, сударыня.",
        "clingy": "О, вы сами напросились.",
    }
    await message.answer(comments[mode])


@router.message(Command("backup"))
async def cmd_backup(message: Message):
    data = await read()
    raw = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    file = BufferedInputFile(raw, filename="aiven_backup.json")
    await message.answer_document(file, caption="Моя память, сударыня. Храните бережно.")


@router.message(Command("restore"))
async def cmd_restore(message: Message):
    r = message.reply_to_message
    if not r or not r.document:
        await message.answer(
            "Ответьте этой командой на файл с бэкапом, сударыня. "
            "Иначе я не пойму, что восстанавливать."
        )
        return
    if not (r.document.file_name or "").endswith(".json"):
        await message.answer("Мне нужен файл <code>.json</code>, сударыня.", parse_mode="HTML")
        return
    try:
        file = await message.bot.get_file(r.document.file_id)
        buf = io.BytesIO()
        await message.bot.download_file(file.file_path, buf)
        data = json.loads(buf.getvalue().decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("not a dict")
        await write(data)
        await message.answer(
            "Память восстановлена, сударыня. Чувствую себя... помолодевшим. "
            "Или постаревшим. Не разобрать."
        )
    except Exception as e:
        logging.error(f"restore error: {e}")
        await message.answer("Не вышло, сударыня. Файл, кажется, повреждён или проклят.")


# --- Text ---

@router.message(F.text & ~F.text.startswith("/"))
async def on_text(message: Message, bot: Bot):
    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    response = await ask_aiiven(message.text, context="Тебе пишет госпожа Эвелина.")
    await message.answer(response)


# --- Voice ---

@router.message(F.voice)
async def on_voice(message: Message, bot: Bot):
    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    try:
        file = await bot.get_file(message.voice.file_id)
        buf = io.BytesIO()
        await bot.download_file(file.file_path, buf)
        audio = buf.getvalue()
    except Exception as e:
        logging.error(f"voice download error: {e}")
        await message.answer("Я не расслышал, сударыня. Что-то с проводами.")
        return

    text = await ask_with_media(
        "Госпожа прислала голосовое сообщение. Послушай, пойми смысл "
        "и ответь в своём стиле.",
        audio,
        "audio/ogg",
    )
    if text is None:
        await message.answer("Мои уши сегодня заложило, сударыня. Повторите текстом?")
        return
    await message.answer(text)


# --- Photo ---

@router.message(F.photo)
async def on_photo(message: Message, bot: Bot):
    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    try:
        photo = message.photo[-1]
        file = await bot.get_file(photo.file_id)
        buf = io.BytesIO()
        await bot.download_file(file.file_path, buf)
        img = buf.getvalue()
    except Exception as e:
        logging.error(f"photo download error: {e}")
        await message.answer("Картинка не желает открываться, сударыня.")
        return

    caption = message.caption or (
        "Госпожа прислала фотографию без комментариев. "
        "Прокомментируй её в своём стиле, коротко."
    )
    text = await ask_with_media(caption, img, "image/jpeg")
    if text is None:
        await message.answer("Мои глаза отказываются это видеть. Технически, конечно.")
        return
    await message.answer(text)
