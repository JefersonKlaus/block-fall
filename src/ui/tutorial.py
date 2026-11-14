"""How to play: a tutorial of 3 small pictures, in a dialog, and the button
that opens it. The app shows it by itself the first time it starts."""

from dataclasses import dataclass
from typing import Any, Callable

import flet as ft

from config import (
    BLUE,
    COLOR_BG,
    COLOR_BOARD_BG,
    COLOR_EMPTY,
    COLOR_GOLD,
    COLOR_LOGO_ACCENT,
    COLOR_RESTART,
    COLOR_TEXT,
    GREEN,
    RED,
    TILE_COLORS,
)
from texts import Texts
from ui.widgets import create_dialog_button

# The pictures' squares: B blue, G green, R red, Y gold (a line about to
# disappear), . empty. A lowercase letter is a new square, marked with a +.
PICTURE_COLORS = {
    "B": TILE_COLORS[BLUE],
    "G": TILE_COLORS[GREEN],
    "R": TILE_COLORS[RED],
    "Y": COLOR_GOLD,
    ".": COLOR_EMPTY,
}
SWIPE_ICONS = {
    "left": ft.Icons.SWIPE_LEFT,
    "right": ft.Icons.SWIPE_RIGHT,
    "up": ft.Icons.SWIPE_UP,
    "down": ft.Icons.SWIPE_DOWN,
}
PICTURE_CELL = 14  # small enough for two boards side by side on a 320 px phone


@dataclass(frozen=True)
class Step:
    """A picture: a board before a swipe, and what the game shows after it."""

    before: tuple[str, ...]
    swipe: str
    after: tuple[str, ...]


STEPS = (
    # All the squares slide as far as they can.
    Step(("B..G", "..R.", ".B..", "G..R"), "left", ("BG..", "R...", "B...", "GR..")),
    # Then a new square appears on the other side (here: on the right).
    Step(("B..G", "..R.", ".B..", "G..R"), "left", ("BG..", "R...", "B..g", "GR..")),
    # 3 of a color in a line turn gold, then disappear.
    Step(("B.BB", "G...", "..R.", "...."), "left", ("YYY.", "G...", "R...", "....")),
)


def create_picture_square(letter: str) -> ft.Container:
    new = letter.islower()
    return ft.Container(
        ft.Icon(ft.Icons.ADD, size=PICTURE_CELL - 2, color=COLOR_TEXT) if new else None,
        width=PICTURE_CELL, height=PICTURE_CELL,
        bgcolor=PICTURE_COLORS[letter.upper()], border_radius=3,
        alignment=ft.Alignment.CENTER,
    )


def create_picture_board(rows: tuple[str, ...]) -> ft.Container:
    return ft.Container(
        ft.Column(
            [
                ft.Row(
                    [create_picture_square(letter) for letter in row],
                    spacing=2,
                    tight=True,
                )
                for row in rows
            ],
            spacing=2,
            tight=True,
        ),
        bgcolor=COLOR_BOARD_BG,
        padding=4,
        border_radius=6,
    )


def create_picture(step: Step) -> ft.Row:
    """The board before, the swipe, and the board after."""
    return ft.Row(
        [
            create_picture_board(step.before),
            ft.Icon(SWIPE_ICONS[step.swipe], size=28, color=COLOR_TEXT),
            create_picture_board(step.after),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=8,
    )


class Tutorial:
    """The dialog, one step at a time. `on_close` runs when the player skips
    it or reaches the end; `update` sends the next step to the screen."""

    def __init__(self, texts: Texts, update: Callable[[], None], on_close: Callable[[], None]):
        self.texts = texts
        self.step = 0
        self._update = update
        self._on_close = on_close
        self.dialog = ft.AlertDialog(
            modal=True, bgcolor=COLOR_BG, actions_alignment=ft.MainAxisAlignment.END
        )
        self._show()

    def _show(self) -> None:
        texts, step = self.texts, self.step
        last = step == len(STEPS) - 1
        self.dialog.title = ft.Text(texts.tutorial_titles[step], weight=ft.FontWeight.BOLD, color=COLOR_TEXT)
        self.dialog.content = ft.Column(
            [
                create_picture(STEPS[step]),
                ft.Text(texts.tutorial_texts[step], size=14, color=COLOR_TEXT, text_align=ft.TextAlign.CENTER),
                ft.Row(  # which step this is: one dot per step
                    [
                        ft.Container(
                            width=8, height=8, border_radius=4,
                            bgcolor=COLOR_LOGO_ACCENT if index == step else COLOR_BOARD_BG,
                        )
                        for index in range(len(STEPS))
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=6,
                ),
            ],
            tight=True,
            spacing=14,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        if last:
            self.dialog.actions = [create_dialog_button(texts.start, COLOR_RESTART, self._close)]
        else:
            self.dialog.actions = [
                create_dialog_button(texts.skip, COLOR_BOARD_BG, self._close),
                create_dialog_button(texts.next, COLOR_RESTART, self._next),
            ]

    def _next(self, _event: Any) -> None:
        self.step += 1
        self._show()
        self._update()

    def _close(self, _event: Any) -> None:
        self._on_close()


class HelpButton:
    """HOW TO PLAY, at the bottom of the screen while playing."""

    def __init__(self, on_click: Callable[[Any], None]):
        self.label = ft.Text("", size=13, weight=ft.FontWeight.BOLD, color=COLOR_TEXT)
        self.control = ft.Container(
            ft.Row(
                [ft.Icon(ft.Icons.HELP_OUTLINE, size=18, color=COLOR_TEXT), self.label],
                spacing=6,
                tight=True,
            ),
            bgcolor=COLOR_BOARD_BG,
            border_radius=18,
            padding=ft.Padding(14, 8, 14, 8),
            on_click=on_click,
            ink=True,
        )

    def show(self, visible: bool, texts: Texts) -> None:
        self.label.value = texts.how_to_play
        self.control.visible = visible
