"""Flet presentation and event handling for Block Fall."""

import flet as ft

from config import (
    COLOR_ACCENT,
    COLOR_BG,
    COLOR_BOARD_BG,
    COLOR_MUTED_TEXT,
    COLOR_STATUS_ERROR,
    COLOR_TEXT_DARK,
    COLOR_TEXT_LIGHT,
    CELL_SIZE,
    TILE_COLORS,
)
from game import BlockFallEngine, Piece


def create_tile(value: int, width: int = CELL_SIZE, height: int = CELL_SIZE) -> ft.Container:
    """Build one board or preview tile."""
    text_color = COLOR_TEXT_DARK if value in {2, 4, 8} else COLOR_TEXT_LIGHT
    return ft.Container(
        content=ft.Text(
            "",
            size=1,
            weight=ft.FontWeight.BOLD,
            color=text_color,
            text_align=ft.TextAlign.CENTER,
        ),
        width=width,
        height=height,
        bgcolor=TILE_COLORS.get(value, COLOR_BOARD_BG),
        border_radius=3,
        alignment=ft.Alignment.CENTER,
    )


def create_piece_preview(piece: Piece) -> ft.Control:
    """Build the current piece preview."""
    cells = {(column, row) for column, row in piece.cells}
    rows = piece.height
    columns = piece.width
    preview_rows = [
        ft.Row(
            [
                create_tile(piece.color, width=18, height=18)
                if (column, row) in cells
                else create_tile(0, width=18, height=18)
                for column in range(columns)
            ],
            spacing=2,
        )
        for row in range(rows)
    ]
    return ft.Column(preview_rows, spacing=2)


class BlockFallView:
    """Own the Flet controls and translate user actions into game commands."""

    def __init__(self, page: ft.Page):
        self.page = page
        self.game = BlockFallEngine()
        self.score_display = ft.Text(
            "0", size=16, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_LIGHT
        )
        self.high_score_display = ft.Text(
            "0", size=16, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_LIGHT
        )
        self.status_display = ft.Text(
            "", size=14, weight=ft.FontWeight.BOLD, color=COLOR_STATUS_ERROR
        )
        self.grid_container = ft.Column(spacing=5, alignment=ft.MainAxisAlignment.CENTER)
        self.preview_container = ft.Row(
            alignment=ft.MainAxisAlignment.CENTER, spacing=10
        )
        self._configure_page()
        self.page.add(self._build_layout())
        self.refresh()

    def _configure_page(self) -> None:
        self.page.title = "Block Fall"
        self.page.vertical_alignment = ft.MainAxisAlignment.CENTER
        self.page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        self.page.bgcolor = COLOR_BG
        self.page.window_width = 390
        self.page.window_height = 840
        self.page.window_resizable = False
        self.page.padding = 10

    def refresh(self) -> None:
        self.score_display.value = str(self.game.score)
        self.high_score_display.value = str(self.game.high_score)
        self.status_display.value = (
            "GAME OVER! Tap Restart."
            if self.game.game_over
            else "Rotate the piece, then tap Drop Piece."
        )
        self._refresh_grid()
        self._refresh_preview()
        self.page.update()

    def _refresh_grid(self) -> None:
        self.grid_container.controls.clear()
        for row in self.game.grid:
            self.grid_container.controls.append(
                ft.Row(
                    [create_tile(value) for value in row],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=5,
                )
            )

    def _refresh_preview(self) -> None:
        self.preview_container.controls.clear()
        self.preview_container.controls.append(
            create_piece_preview(self.game.current_piece)
        )

    def _handle_drop(self, _event: ft.ControlEvent) -> None:
        self.game.drop_piece()
        self.refresh()

    def _handle_rotate(self, _event: ft.ControlEvent) -> None:
        self.game.rotate_piece()
        self.refresh()

    def _handle_move(self, direction: str) -> None:
        self.game.move_board(direction)
        self.refresh()

    def _build_layout(self) -> ft.Control:
        rotate_button = ft.Button(
            "Rotate",
            icon=ft.Icons.REFRESH,
            on_click=self._handle_rotate,
            bgcolor=COLOR_ACCENT,
            color=COLOR_TEXT_LIGHT,
        )
        drop_button = ft.Button(
            "Drop Piece",
            on_click=self._handle_drop,
            bgcolor=COLOR_BOARD_BG,
            color=COLOR_TEXT_LIGHT,
        )
        return ft.Container(
            content=ft.Column(
                [
                    self._build_header(),
                    ft.Divider(height=5, color="transparent"),
                    ft.Container(
                        content=self.grid_container,
                        bgcolor=COLOR_BOARD_BG,
                        padding=8,
                        border_radius=12,
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Container(
                        content=self.status_display,
                        alignment=ft.Alignment.CENTER,
                        height=20,
                    ),
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Text("Next:", size=12, color=COLOR_TEXT_LIGHT),
                                        self.preview_container,
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                ),
                                ft.Divider(height=5, color="transparent"),
                                ft.Text(
                                    "The drop column is selected randomly.",
                                    size=11,
                                    color=COLOR_MUTED_TEXT,
                                ),
                                ft.Row(
                                    [rotate_button, drop_button],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    spacing=10,
                                ),
                            ],
                            spacing=5,
                        ),
                        bgcolor=COLOR_BOARD_BG,
                        padding=10,
                        border_radius=10,
                    ),
                    ft.Divider(height=5, color="transparent"),
                    ft.Row(
                        [
                            ft.IconButton(
                                icon=ft.Icons.ARROW_BACK,
                                tooltip="Move all blocks left",
                                bgcolor=COLOR_BOARD_BG,
                                icon_color=COLOR_TEXT_LIGHT,
                                on_click=lambda _event: self._handle_move("left"),
                            ),
                            ft.IconButton(
                                icon=ft.Icons.ARROW_FORWARD,
                                tooltip="Move all blocks right",
                                bgcolor=COLOR_BOARD_BG,
                                icon_color=COLOR_TEXT_LIGHT,
                                on_click=lambda _event: self._handle_move("right"),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=20,
                    ),
                ],
                alignment=ft.MainAxisAlignment.START,
            ),
            padding=5,
            expand=True,
        )

    def _build_header(self) -> ft.Row:
        return ft.Row(
            [
                ft.Text(
                    "Block Fall",
                    size=22,
                    weight=ft.FontWeight.BOLD,
                    color=COLOR_TEXT_LIGHT,
                ),
                ft.Row(
                    [
                        self._build_score_card("SCORE", self.score_display),
                        self._build_score_card("BEST", self.high_score_display),
                    ],
                    spacing=8,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

    @staticmethod
    def _build_score_card(label: str, value: ft.Text) -> ft.Container:
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(label, size=8, color=COLOR_MUTED_TEXT),
                    value,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=COLOR_BOARD_BG,
            padding=6,
            border_radius=6,
            width=80,
        )


def main(page: ft.Page) -> None:
    """Start the Block Fall application."""
    BlockFallView(page)
