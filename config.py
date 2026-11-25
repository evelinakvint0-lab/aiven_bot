import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    bot_token: str
    gemini_key: str
    owner_id: int
    base_url: str
    webhook_path: str
    port: int


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Переменная окружения {name} не задана")
    return value


def load_config() -> Config:
    return Config(
        bot_token=_required("BOT_TOKEN"),
        gemini_key=_required("GEMINI_API_KEY"),
        owner_id=int(_required("OWNER_ID")),
        base_url=_required("RENDER_EXTERNAL_URL").rstrip("/"),
        webhook_path="/webhook",
        port=int(os.getenv("PORT", "8080")),
    )


config = load_config()
