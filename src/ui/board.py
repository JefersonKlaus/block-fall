"""The grid on screen: sized to the page, showing and moving the squares."""

from typing import Optional

import flet as ft

from config import (
    ANIMATION_SECONDS,
    BOARD_PADDING,
    CELL_SPACING,
    COLOR_BOARD_BG,
    COLOR_GOLD,
    FALLBACK_PAGE_WIDTH,
    LAYOUT_PADDING,
    PAGE_PADDING,
    TILE_COLORS,
)
from game import Squares
from ui.widgets import create_tile

# Everything around the board on each side: the grid fills the rest.
SIDE_MARGIN = 2 * (PAGE_PADDING + LAYOUT_PADDING + BOARD_PADDING)
SLIDE = ft.Animation(int(ANIMATION_SECONDS * 1000), ft.AnimationCurve.EASE_OUT)


def fit_cell(page_width: Optional[float], cols: int) -> float:
    """Square size that makes `cols` columns fill the whole page width.

    `page_width` is the space the app really gets (Flet's page.width), not
    the window size, which includes the window frame on desktop.
    """
    available = (page_width or FALLBACK_PAGE_WIDTH) - SIDE_MARGIN
    return (available - (cols - 1) * CELL_SPACING) / cols


class BoardView:
    """Empty slots underneath, one tile per square on top.

    A square keeps its tile for life, so moving it animates (like 2048).
    """

    def __init__(self, rows: int, cols: int, page_width: Optional[float]):
        self.stack = ft.Stack()
        self.frame = ft.Container(
            content=self.stack,
            bgcolor=COLOR_BOARD_BG,
            padding=BOARD_PADDING,
            border_radius=12,
            alignment=ft.Alignment.CENTER,
        )
        self.page_width = page_width
        self.rebuild(rows, cols)

    @property
    def outer_width(self) -> float:
        """Width of the board with its frame."""
        return self.stack.width + 2 * BOARD_PADDING

    def rebuild(self, rows: int, cols: int) -> None:
        """An empty grid of a (new) size."""
        self.rows, self.cols = rows, cols
        self.cell = fit_cell(self.page_width, cols)
        self.slots = [
            self._place(create_tile(0), column, row)
            for row in range(rows)
            for column in range(cols)
        ]
        self.stack.controls = list(self.slots)
        self.tiles: dict[int, ft.Container] = {}
        self._size()

    def resize(self, page_width: Optional[float], squares: Squares) -> None:
        """Fit the grid to a new page width (it always fills the width)."""
        self.page_width = page_width
        self.cell = fit_cell(page_width, self.cols)
        self._size()
        for index, slot in enumerate(self.slots):
            self._place(slot, index % self.cols, index // self.cols)
        self.show(squares)

    def show(
        self, squares: Squares, gold: frozenset[int] = frozenset(), pop: bool = False
    ) -> list[ft.Container]:
        """Make the tiles match `squares` (id -> (column, row, color)).

        Existing tiles are moved (Flet animates the change), tiles of squares
        that are gone are removed, and new squares get new tiles, created tiny
        when `pop` is set so they can grow in. Returns the new tiles.
        """
        for square_id in [i for i in self.tiles if i not in squares]:
            self.stack.controls.remove(self.tiles.pop(square_id))
        new_tiles = []
        for square_id, (column, row, color) in squares.items():
            tile = self.tiles.get(square_id)
            if tile is None:
                tile = self._new_tile(color, pop)
                self.tiles[square_id] = tile
                self.stack.controls.append(tile)
                new_tiles.append(tile)
            self._place(tile, column, row)
            tile.bgcolor = COLOR_GOLD if square_id in gold else TILE_COLORS.get(color, COLOR_BOARD_BG)
        return new_tiles

    @staticmethod
    def _new_tile(color: int, pop: bool) -> ft.Container:
        tile = create_tile(color)
        tile.animate_position = SLIDE
        tile.animate_scale = SLIDE
        tile.scale = 0 if pop else 1
        return tile

    def _place(self, tile: ft.Container, column: int, row: int) -> ft.Container:
        step = self.cell + CELL_SPACING
        tile.left = column * step
        tile.top = row * step
        tile.width = tile.height = self.cell
        return tile

    def _size(self) -> None:
        self.stack.width = self.cols * self.cell + (self.cols - 1) * CELL_SPACING
        self.stack.height = self.rows * self.cell + (self.rows - 1) * CELL_SPACING
