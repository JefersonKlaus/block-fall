"""What the app keeps on the device between launches: the best score of each
level, and whether the player has already seen how to play.

`storage` is Flet's SharedPreferences (or anything with the same async `get`
and `set`). Saving is never allowed to stop the game: if the device's storage
cannot be read or written, the app simply starts as on a new device.
"""

import asyncio
from typing import Any

from config import DIFFICULTIES

TUTORIAL_KEY = "block_fall.tutorial_seen"


def storage_key(level: int) -> str:
    """Where a level's best is saved, e.g. "block_fall.best.middle"."""
    return f"block_fall.best.{DIFFICULTIES[level][0].lower()}"


async def _get(storage: Any, key: str) -> Any:
    try:
        return await storage.get(key)
    except Exception:  # no storage here (e.g. not in a Flet session): nothing saved
        return None


async def _set(storage: Any, key: str, value: Any) -> None:
    try:
        await storage.set(key, value)
    except Exception:  # not saved this time: the game just goes on
        pass


async def load_best_scores(storage: Any) -> dict[int, int]:
    """{level index: best score} for every level (0 when none is saved)."""
    values = await asyncio.gather(*(_get(storage, storage_key(level)) for level in range(len(DIFFICULTIES))))
    return {level: value if type(value) is int and value > 0 else 0 for level, value in enumerate(values)}


async def save_best_score(storage: Any, level: int, best: int) -> None:
    await _set(storage, storage_key(level), best)


async def load_tutorial_seen(storage: Any) -> bool:
    return await _get(storage, TUTORIAL_KEY) is True


async def save_tutorial_seen(storage: Any) -> None:
    await _set(storage, TUTORIAL_KEY, True)
