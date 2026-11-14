"""The header: the logo, and the blocks  SCORE | BEST
                                           LEVEL | RESTART
"""

from typing import Any, Callable, Optional

import flet as ft

from config import (
    COLOR_RESTART,
    COLOR_TEXT,
    FALLBACK_PAGE_WIDTH,
    HEADER_BLOCK_SPACING,
    HEADER_ICON_SIZE,
    HEADER_LEVEL_SIZE,
    HEADER_LOGO_ROOM,
    HEADER_VALUE_SIZE,
    LAYOUT_PADDING,
    PAGE_PADDING,
)
from texts import Texts
from ui.widgets import create_block, create_logo


def block_width(page_width: Optional[float]) -> float:
    """Width of each block: two of them reach from the middle of the screen
    to its right side. On very narrow screens they stop where the logo needs
    room."""
    width = page_width or FALLBACK_PAGE_WIDTH
    side = PAGE_PADDING + LAYOUT_PADDING
    blocks = min(width / 2 - side, width - 2 * side - HEADER_LOGO_ROOM)
    return (blocks - HEADER_BLOCK_SPACING) / 2


class Header:
    """Shows the scores and the level; reports taps on LEVEL and RESTART."""

    def __init__(
        self,
        on_level: Callable[[Any], None],
        on_restart: Callable[[Any], None],
        page_width: Optional[float],
    ):
        width = block_width(page_width)
        self.logo = create_logo()
        self.score_text = ft.Text("0", size=HEADER_VALUE_SIZE, weight=ft.FontWeight.BOLD, color=COLOR_TEXT)
        self.best_text = ft.Text("0", size=HEADER_VALUE_SIZE, weight=ft.FontWeight.BOLD, color=COLOR_TEXT)
        self.level_text = ft.Text("", size=HEADER_LEVEL_SIZE, weight=ft.FontWeight.BOLD, color=COLOR_TEXT)

        self.level_button = create_block("", self.level_text, width)
        self.level_button.on_click = on_level
        self.level_button.ink = True

        self.restart_button = create_block(
            "", ft.Icon(ft.Icons.RESTART_ALT, size=HEADER_ICON_SIZE, color=COLOR_TEXT), width
        )
        self.restart_button.bgcolor = COLOR_RESTART
        self.restart_button.on_click = on_restart
        self.restart_button.ink = True

        self.blocks = [
            create_block("", self.score_text, width),
            create_block("", self.best_text, width),
            self.level_button,
            self.restart_button,
        ]
        self.control = ft.Row(
            [
                ft.Container(self.logo, expand=True),
                ft.Column(
                    [
                        ft.Row(self.blocks[:2], spacing=HEADER_BLOCK_SPACING),
                        ft.Row(self.blocks[2:], spacing=HEADER_BLOCK_SPACING),
                    ],
                    spacing=HEADER_BLOCK_SPACING,
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def resize(self, page_width: Optional[float]) -> None:
        """Keep the blocks reaching the middle of a screen of a new width."""
        for block in self.blocks:
            block.width = block_width(page_width)

    def show(self, score: int, best: int, level_name: str, level_color: str, texts: Texts) -> None:
        self.score_text.value = str(score)
        self.best_text.value = str(best)
        self.level_text.value = level_name
        self.level_button.bgcolor = level_color
        labels = (texts.score, texts.best, texts.level, texts.restart)
        for block, label in zip(self.blocks, labels):
            block.content.controls[0].value = label
        self.level_button.tooltip = texts.level_tip
        self.restart_button.tooltip = texts.restart_tip
