"""The 5 color blocks."""

import flet as ft

from config import BLUE, COLOR_GOLD, COLOR_LOCKED, GREEN, RED, TILE_COLORS
from texts import ENGLISH
from ui.level_bar import LevelBar


class TestLevelBar:
    def test_locked_unlocking_and_unlocked(self):
        bar = LevelBar()
        bar.show((BLUE, GREEN, RED), frozenset({RED}), ENGLISH)
        colors = [b.bgcolor for b in bar.blocks]
        assert colors == [TILE_COLORS[BLUE], TILE_COLORS[GREEN], COLOR_GOLD, COLOR_LOCKED, COLOR_LOCKED]
        assert [isinstance(b.content, ft.Icon) for b in bar.blocks] == [False, False, False, True, True]
        assert bar.control.controls == bar.blocks
