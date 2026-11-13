"""The 5 color blocks."""

import unittest

import flet as ft

from config import BLUE, COLOR_GOLD, COLOR_LOCKED, GREEN, RED, TILE_COLORS
from ui.level_bar import LevelBar


class LevelBarTests(unittest.TestCase):
    def test_locked_unlocking_and_unlocked(self):
        bar = LevelBar()
        bar.show((BLUE, GREEN, RED), unlocking=frozenset({RED}))
        colors = [b.bgcolor for b in bar.blocks]
        self.assertEqual(colors, [TILE_COLORS[BLUE], TILE_COLORS[GREEN], COLOR_GOLD, COLOR_LOCKED, COLOR_LOCKED])
        self.assertEqual([isinstance(b.content, ft.Icon) for b in bar.blocks], [False, False, False, True, True])
        self.assertEqual(bar.control.controls, bar.blocks)
