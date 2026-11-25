import asyncio
import json
import os
from typing import Any, Callable

DATA_FILE = "data.json"
_lock = asyncio.Lock()


def _load_sync() -> dict:
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_sync(data: dict) -> None:
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)


async def read() -> dict:
    async with _lock:
        return _load_sync()


async def write(data: dict) -> None:
    async with _lock:
        _save_sync(data)


async def mutate(mutator: Callable[[dict], None]) -> dict:
    async with _lock:
        data = _load_sync()
        mutator(data)
        _save_sync(data)
        return data


async def get_key(key: str, default: Any = None) -> Any:
    async with _lock:
        return _load_sync().get(key, default)
