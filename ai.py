import asyncio
import logging

from google import genai
from google.genai import types

from config import config
from prompts import CHARACTER_PROMPT
from storage import get_key, mutate

client = genai.Client(api_key=config.gemini_key)
MODEL = "gemini-2.5-flash"


def _build_contents(history: list, user_text: str) -> list:
    contents = []
    for item in history[-10:]:
        contents.append(types.Content(
            role=item["role"],
            parts=[types.Part(text=item["text"])],
        ))
    contents.append(types.Content(
        role="user",
        parts=[types.Part(text=user_text)],
    ))
    return contents


async def _save_exchange(user_text: str, model_text: str) -> None:
    def _mut(data: dict) -> None:
        history = data.get("history", [])
        history.append({"role": "user", "text": user_text})
        history.append({"role": "model", "text": model_text})
        data["history"] = history[-20:]
    await mutate(_mut)


async def ask_aiiven(prompt: str, context: str = "") -> str:
    history = await get_key("history", [])
    user_text = prompt if not context else f"{context}\n\n{prompt}"

    try:
        response = await asyncio.wait_for(
            client.aio.models.generate_content(
                model=MODEL,
                contents=_build_contents(history, user_text),
                config=types.GenerateContentConfig(
                    system_instruction=CHARACTER_PROMPT,
                    temperature=1.0,
                    max_output_tokens=500,
                ),
            ),
            timeout=45,
        )
        text = response.text or "..."
    except asyncio.TimeoutError:
        logging.error("Gemini timeout")
        return "Прошу прощения, сударыня, мои мысли застряли в пробке. Повторите."
    except Exception as e:
        logging.error(f"Gemini error: {e}")
        return "Мои извинения, сударыня. Что-то в моих шестерёнках заело."

    await _save_exchange(prompt, text)
    return text


async def ask_with_media(prompt: str, media_bytes: bytes, mime_type: str) -> str | None:
    try:
        response = await asyncio.wait_for(
            client.aio.models.generate_content(
                model=MODEL,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(text=prompt),
                            types.Part.from_bytes(data=media_bytes, mime_type=mime_type),
                        ],
                    )
                ],
                config=types.GenerateContentConfig(
                    system_instruction=CHARACTER_PROMPT,
                    temperature=1.0,
                    max_output_tokens=500,
                ),
            ),
            timeout=60,
        )
        return response.text or "..."
    except asyncio.TimeoutError:
        logging.error("Gemini media timeout")
        return None
    except Exception as e:
        logging.error(f"Gemini media error: {e}")
        return None


async def reset_history() -> None:
    def _mut(data: dict) -> None:
        data["history"] = []
    await mutate(_mut)
