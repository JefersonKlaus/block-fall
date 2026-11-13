"""Look of the basic pieces: squares, blocks, the logo, dialogs.

Only builders here: no state and no game logic.
"""

from typing import Any, Callable

import flet as ft

from config import (
    BLUE,
    CELL_SIZE,
    COLOR_BG,
    COLOR_BOARD_BG,
    COLOR_GOLD,
    COLOR_LOGO_ACCENT,
    COLOR_MUTED_TEXT,
    COLOR_TEXT,
    GREEN,
    HEADER_BLOCK_HEIGHT,
    HEADER_BLOCK_WIDTH,
    PEACH,
    PURPLE,
    RED,
    TILE_COLORS,
    TILE_RADIUS,
)

# The logo's mark: a mini board whose middle row is a gold line of 3.
LOGO_MARK = (
    (TILE_COLORS[BLUE], TILE_COLORS[GREEN], TILE_COLORS[PURPLE]),
    (COLOR_GOLD, COLOR_GOLD, COLOR_GOLD),
    (TILE_COLORS[PEACH], TILE_COLORS[BLUE], TILE_COLORS[RED]),
)


def create_tile(
    value: int, width: float = CELL_SIZE, height: float = CELL_SIZE, gold: bool = False
) -> ft.Container:
    """One square: rounded, no border (like 2048). `gold`: about to disappear."""
    return ft.Container(
        width=width,
        height=height,
        bgcolor=COLOR_GOLD if gold else TILE_COLORS.get(value, COLOR_BOARD_BG),
        border_radius=TILE_RADIUS,
    )


def create_block(label: str, value: ft.Control) -> ft.Container:
    """A header block: a small label above a value (score, best, level...)."""
    return ft.Container(
        content=ft.Column(
            [ft.Text(label, size=10, color=COLOR_MUTED_TEXT), value],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=0,
        ),
        bgcolor=COLOR_BOARD_BG,
        border_radius=6,
        width=HEADER_BLOCK_WIDTH,
        height=HEADER_BLOCK_HEIGHT,
        alignment=ft.Alignment.CENTER,
    )


def create_logo() -> ft.Row:
    """The game's logo: a mini board with a gold line of 3, and "Block / Fall"."""
    mark = ft.Column(
        [
            ft.Row(
                [ft.Container(width=16, height=16, bgcolor=color, border_radius=3) for color in row],
                spacing=3,
            )
            for row in LOGO_MARK
        ],
        spacing=3,
    )
    # Tight line height: no gap between "Block" and "Fall".
    tight = ft.TextStyle(height=0.9)
    name = ft.Column(
        [
            ft.Text("Block", size=30, weight=ft.FontWeight.W_900, color=COLOR_TEXT, style=tight),
            ft.Text("Fall", size=30, weight=ft.FontWeight.W_900, color=COLOR_LOGO_ACCENT, style=tight),
        ],
        spacing=0,
    )
    return ft.Row([mark, name], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER)


def create_dialog_button(
    label: str, color: str, on_click: Callable[[Any], None]
) -> ft.Container:
    """A dialog button drawn as a block, like the rest of the app."""
    return ft.Container(
        content=ft.Text(label, size=13, weight=ft.FontWeight.BOLD, color=COLOR_TEXT),
        bgcolor=color,
        border_radius=6,
        padding=ft.Padding(16, 10, 16, 10),
        on_click=on_click,
        ink=True,
    )


def create_confirm_dialog(
    question: str,
    message: str,
    cancel_label: str,
    ok_label: str,
    ok_color: str,
    on_cancel: Callable[[Any], None],
    on_ok: Callable[[Any], None],
) -> ft.AlertDialog:
    """A modal question before losing the current game."""
    return ft.AlertDialog(
        modal=True,
        title=ft.Text(question, weight=ft.FontWeight.BOLD, color=COLOR_TEXT),
        content=ft.Text(message, color=COLOR_TEXT),
        actions=[
            create_dialog_button(cancel_label, COLOR_BOARD_BG, on_cancel),
            create_dialog_button(ok_label, ok_color, on_ok),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        bgcolor=COLOR_BG,
    )
