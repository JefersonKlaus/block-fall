"""The 5 color blocks, one per level: locked, unlocking (gold), or unlocked."""

import flet as ft

from config import (
    COLOR_GOLD,
    COLOR_LOCK_ICON,
    COLOR_LOCKED,
    LEVEL_BLOCK_SIZE,
    TILE_COLORS,
    TILE_RADIUS,
    UNLOCK_SCORES,
)
from game import SQUARE_COLORS
from texts import Texts


class LevelBar:
    """Gray with a lock until a color is unlocked; gold while it unlocks."""

    def __init__(self):
        self.blocks = [
            ft.Container(
                width=LEVEL_BLOCK_SIZE,
                height=LEVEL_BLOCK_SIZE,
                border_radius=TILE_RADIUS,
                alignment=ft.Alignment.CENTER,
            )
            for _ in UNLOCK_SCORES
        ]
        self.control = ft.Row(self.blocks, alignment=ft.MainAxisAlignment.CENTER, spacing=12)

    def show(self, unlocked: tuple[int, ...], unlocking: frozenset[int], texts: Texts) -> None:
        """`unlocking`: colors just unlocked, shown gold for a moment."""
        for block, needed in zip(self.blocks, UNLOCK_SCORES):
            block.tooltip = (
                texts.starting_color if needed == 0 else texts.unlocks_at.format(points=needed)
            )
        for block, color in zip(self.blocks, SQUARE_COLORS):
            if color in unlocking:
                block.bgcolor, block.content = COLOR_GOLD, None
            elif color in unlocked:
                block.bgcolor, block.content = TILE_COLORS[color], None
            else:
                block.bgcolor = COLOR_LOCKED
                block.content = ft.Icon(ft.Icons.LOCK, size=16, color=COLOR_LOCK_ICON)
