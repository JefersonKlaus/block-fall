"""What shows when a game is over: the points of the game (in color) with
GAME OVER under them, above the level blocks, and a big RESTART button at
the bottom of the screen."""

from typing import Any, Callable

import flet as ft

from config import COLOR_FINAL_SCORE, COLOR_RESTART, COLOR_STATUS, COLOR_TEXT
from texts import Texts

# The banner: a gap between the points and GAME OVER, and more room under
# GAME OVER (before the level blocks).
LINE_SPACING = 8
GAP_BELOW = 12
BANNER_HEIGHT = 60
BUTTON_HEIGHT = 56


class GameEnd:
    """Hidden while playing; `banner` and `button` go where the layout wants them."""

    def __init__(self, on_restart: Callable[[Any], None]):
        self.points = ft.Text(
            "", size=20, weight=ft.FontWeight.BOLD, color=COLOR_FINAL_SCORE,
            max_lines=1, text_align=ft.TextAlign.CENTER,
        )
        self.title = ft.Text("", size=13, weight=ft.FontWeight.BOLD, color=COLOR_STATUS)
        self.banner = ft.Container(
            ft.Column(
                [self.points, self.title],
                spacing=LINE_SPACING,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            height=BANNER_HEIGHT,
            padding=ft.Padding(0, 0, 0, GAP_BELOW),
            alignment=ft.Alignment.CENTER,
            visible=False,
        )
        self.button = ft.Container(
            content=ft.Text("", size=22, weight=ft.FontWeight.BOLD, color=COLOR_TEXT),
            bgcolor=COLOR_RESTART,
            height=BUTTON_HEIGHT,
            border_radius=12,
            alignment=ft.Alignment.CENTER,
            visible=False,
            on_click=on_restart,
            ink=True,
        )

    def show(self, game_over: bool, score: int, texts: Texts) -> None:
        self.points.value = texts.final_score.format(points=score)
        self.title.value = texts.game_over
        self.button.content.value = texts.restart
        self.button.tooltip = texts.restart_tip
        self.banner.visible = self.button.visible = game_over

    def fit(self, width: float) -> None:
        """The big button is as wide as the grid."""
        self.button.width = width
