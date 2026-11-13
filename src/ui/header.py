"""The header: the logo, and the blocks  SCORE | BEST
                                           LEVEL | RESTART
"""

from typing import Any, Callable

import flet as ft

from config import COLOR_RESTART, COLOR_TEXT
from texts import ENGLISH, Texts
from ui.widgets import create_block, create_logo


class Header:
    """Shows the scores and the level; reports taps on LEVEL and RESTART."""

    def __init__(self, on_level: Callable[[Any], None], on_restart: Callable[[Any], None]):
        self.logo = create_logo()
        self.score_text = ft.Text("0", size=20, weight=ft.FontWeight.BOLD, color=COLOR_TEXT)
        self.best_text = ft.Text("0", size=20, weight=ft.FontWeight.BOLD, color=COLOR_TEXT)
        self.level_text = ft.Text("", size=11, weight=ft.FontWeight.BOLD, color=COLOR_TEXT)

        self.level_button = create_block("", self.level_text)
        self.level_button.on_click = on_level
        self.level_button.ink = True

        self.restart_button = create_block(
            "", ft.Icon(ft.Icons.RESTART_ALT, size=24, color=COLOR_TEXT)
        )
        self.restart_button.bgcolor = COLOR_RESTART
        self.restart_button.on_click = on_restart
        self.restart_button.ink = True

        self.blocks = [
            create_block("", self.score_text),
            create_block("", self.best_text),
            self.level_button,
            self.restart_button,
        ]
        self.control = ft.Row(
            [
                ft.Container(self.logo, expand=True),
                ft.Column(
                    [ft.Row(self.blocks[:2], spacing=6), ft.Row(self.blocks[2:], spacing=6)],
                    spacing=6,
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def show(
        self, score: int, best: int, level_name: str, level_color: str, texts: Texts = ENGLISH
    ) -> None:
        self.score_text.value = str(score)
        self.best_text.value = str(best)
        self.level_text.value = level_name
        self.level_button.bgcolor = level_color
        labels = (texts.score, texts.best, texts.level, texts.restart)
        for block, label in zip(self.blocks, labels):
            block.content.controls[0].value = label
        self.level_button.tooltip = texts.level_tip
        self.restart_button.tooltip = texts.restart_tip
