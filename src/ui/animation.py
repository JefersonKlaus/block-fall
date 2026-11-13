"""Plays the steps of a move on the board, with pauses that can be skipped."""

import asyncio
from typing import Callable

from config import ANIMATION_SECONDS, GOLD_FLASH_SECONDS, POP_START_SECONDS
from game import Frame
from ui.board import BoardView

# How long to wait after showing each kind of step before the next one.
PAUSES = {"slide": ANIMATION_SECONDS, "spawn": ANIMATION_SECONDS, "match": GOLD_FLASH_SECONDS}


class Animator:
    """Shows frames (slide, gold flash, new square) one after the other.

    `hurry()` says whether to skip pauses (the player is already waiting
    with another swipe), so the game never feels frozen.
    """

    def __init__(self, board: BoardView, update: Callable[[], None], hurry: Callable[[], bool]):
        self.board = board
        self.update = update
        self.hurry = hurry

    async def pause(self, seconds: float) -> None:
        if not self.hurry():
            await asyncio.sleep(seconds)

    async def play(self, frames: list[Frame]) -> None:
        for index, frame in enumerate(frames):
            await self._show(frame, is_last=index == len(frames) - 1)

    async def _show(self, frame: Frame, is_last: bool) -> None:
        new_tiles = self.board.show(frame.squares, frame.gold, pop=True)
        self.update()
        if new_tiles:
            await self.pause(POP_START_SECONDS)  # let them appear tiny first
            for tile in new_tiles:
                tile.scale = 1
            self.update()
        if frame.kind == "match" or not is_last:
            await self.pause(PAUSES[frame.kind])
