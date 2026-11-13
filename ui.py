"""Flet presentation and event handling for Block Fall."""

import asyncio
from typing import Any, Callable, Optional

import flet as ft

from config import (
    ANIMATION_SECONDS,
    BLUE,
    CELL_SIZE,
    CELL_SPACING,
    COLOR_BG,
    COLOR_BOARD_BG,
    COLOR_GOLD,
    COLOR_LOCK_ICON,
    COLOR_LOCKED,
    COLOR_LOGO_ACCENT,
    COLOR_MUTED_TEXT,
    COLOR_RESTART,
    COLOR_STATUS,
    COLOR_TEXT,
    DEFAULT_DIFFICULTY,
    DIFFICULTIES,
    FALLBACK_PAGE_WIDTH,
    GOLD_FLASH_SECONDS,
    GREEN,
    HEADER_BLOCK_HEIGHT,
    HEADER_BLOCK_WIDTH,
    PEACH,
    POP_START_SECONDS,
    PURPLE,
    RED,
    SWIPE_MIN_DISTANCE,
    TILE_COLORS,
    TILE_RADIUS,
    UNLOCK_FLASH_SECONDS,
    UNLOCK_SCORES,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from game import SQUARE_COLORS, BlockFallEngine, Frame, Squares

# Paddings around the board. The board fills the rest of the page width.
PAGE_PADDING = 10
LAYOUT_PADDING = 5
BOARD_PADDING = 8
SIDE_MARGIN = 2 * (PAGE_PADDING + LAYOUT_PADDING + BOARD_PADDING)
SLIDE = ft.Animation(int(ANIMATION_SECONDS * 1000), ft.AnimationCurve.EASE_OUT)
# How long to wait after showing each kind of step before the next one.
PAUSES = {"slide": ANIMATION_SECONDS, "spawn": ANIMATION_SECONDS, "match": GOLD_FLASH_SECONDS}

STATUS_PLAY = "Line up 3 or more squares of the same color."
STATUS_GAME_OVER = "GAME OVER! Tap Restart."
STATUS_UNLOCKED = "New color unlocked!"

# The logo's mark: a mini board whose middle row is a gold line of 3.
LOGO_MARK = (
    (TILE_COLORS[BLUE], TILE_COLORS[GREEN], TILE_COLORS[PURPLE]),
    (COLOR_GOLD, COLOR_GOLD, COLOR_GOLD),
    (TILE_COLORS[PEACH], TILE_COLORS[BLUE], TILE_COLORS[RED]),
)


def swipe_direction(dx: float, dy: float) -> Optional[str]:
    """Which move a finger movement of (dx, dy) pixels means, if any.

    The longer axis wins; too-short or exactly diagonal drags are not moves.
    """
    if max(abs(dx), abs(dy)) < SWIPE_MIN_DISTANCE or abs(dx) == abs(dy):
        return None
    if abs(dx) > abs(dy):
        return "right" if dx > 0 else "left"
    return "down" if dy > 0 else "up"


def fit_cell(page_width: Optional[float], cols: int) -> float:
    """Square size that makes `cols` columns fill the whole page width.

    `page_width` is the space the app really gets (Flet's page.width), not
    the window size, which includes the window frame on desktop.
    """
    available = (page_width or FALLBACK_PAGE_WIDTH) - SIDE_MARGIN
    return (available - (cols - 1) * CELL_SPACING) / cols


def create_tile(
    value: int,
    width: float = CELL_SIZE,
    height: float = CELL_SIZE,
    gold: bool = False,
) -> ft.Container:
    """Build one square: rounded, no border (like 2048).

    `gold` shows a matched square about to disappear.
    """
    return ft.Container(
        width=width,
        height=height,
        bgcolor=COLOR_GOLD if gold else TILE_COLORS.get(value, COLOR_BOARD_BG),
        border_radius=TILE_RADIUS,
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
    name = ft.Column(
        [
            # Tight line height: no gap between "Block" and "Fall".
            ft.Text("Block", size=30, weight=ft.FontWeight.W_900, color=COLOR_TEXT,
                    style=ft.TextStyle(height=0.9)),
            ft.Text("Fall", size=30, weight=ft.FontWeight.W_900, color=COLOR_LOGO_ACCENT,
                    style=ft.TextStyle(height=0.9)),
        ],
        spacing=0,
    )
    return ft.Row([mark, name], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER)


class BlockFallView:
    """Own the Flet controls and translate user actions into game commands."""

    def __init__(self, page: ft.Page, game: Optional[BlockFallEngine] = None):
        self.page = page
        self.game = game if game is not None else BlockFallEngine()
        self.score_display = ft.Text(
            "0", size=16, weight=ft.FontWeight.BOLD, color=COLOR_TEXT
        )
        self.high_score_display = ft.Text(
            "0", size=16, weight=ft.FontWeight.BOLD, color=COLOR_TEXT
        )
        # Up to 2 lines: the longest message wraps on narrow phones.
        self.status_display = ft.Text(
            "", size=13, weight=ft.FontWeight.BOLD, color=COLOR_STATUS, max_lines=2
        )
        # Fixed height, so the layout never jumps when the message changes
        # between one and two lines.
        self.status_box = ft.Container(
            self.status_display, height=40, alignment=ft.Alignment.CENTER
        )
        self.status_display.text_align = ft.TextAlign.CENTER
        # Header: logo, then the blocks  SCORE | BEST
        #                                LEVEL | RESTART
        self.logo = create_logo()
        self.difficulty = DEFAULT_DIFFICULTY
        self.level_value = ft.Text("", size=9, weight=ft.FontWeight.BOLD, color=COLOR_TEXT)
        self.level_button = self._build_block("LEVEL", self.level_value)
        self.level_button.tooltip = "Change level (starts a new game)"
        self.level_button.on_click = self._handle_level
        self.level_button.ink = True
        self.restart_block = self._build_block(
            "RESTART", ft.Icon(ft.Icons.RESTART_ALT, size=18, color=COLOR_TEXT)
        )
        self.restart_block.bgcolor = COLOR_RESTART
        self.restart_block.tooltip = "Restart"
        self.restart_block.on_click = self._handle_restart
        self.restart_block.ink = True
        self.header_blocks = [
            self._build_block("SCORE", self.score_display),
            self._build_block("BEST", self.high_score_display),
            self.level_button,
            self.restart_block,
        ]
        self.header = ft.Row(
            [
                ft.Container(self.logo, expand=True),
                ft.Column(
                    [
                        ft.Row(self.header_blocks[:2], spacing=6),
                        ft.Row(self.header_blocks[2:], spacing=6),
                    ],
                    spacing=6,
                ),
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        # Shown at the bottom when the game is over: a big RESTART button.
        self.game_over_button = ft.Container(
            content=ft.Text("RESTART", size=22, weight=ft.FontWeight.BOLD, color=COLOR_TEXT),
            bgcolor=COLOR_RESTART,
            height=56,
            border_radius=12,
            alignment=ft.Alignment.CENTER,
            visible=False,
            on_click=self._handle_restart,
            ink=True,
            tooltip="Restart",
        )
        # The board: empty slots underneath, one tile per square on top. A
        # square keeps its tile for life, so moving it animates (like 2048).
        # It always fills the page width, whatever the grid size.
        self._page_width = page.width
        self.board = ft.Stack()
        self.tiles: dict[int, ft.Container] = {}
        self._build_board()
        # One block per color (level), above the grid: gray with a lock until
        # the color is unlocked.
        self.level_blocks = [
            ft.Container(
                width=CELL_SIZE,
                height=CELL_SIZE,
                border_radius=TILE_RADIUS,
                alignment=ft.Alignment.CENTER,
                tooltip="Starting color" if needed == 0 else f"Unlocks at {needed} points",
            )
            for needed in UNLOCK_SCORES
        ]
        self.level_bar = ft.Row(
            self.level_blocks, alignment=ft.MainAxisAlignment.CENTER, spacing=12
        )
        # True while a move is being animated; presses are ignored meanwhile.
        self._busy = False
        # A restart or level change asked for during an animation happens
        # right after it.
        self._pending: Optional[Callable[[], None]] = None
        # A swipe made during an animation: played right after it, and the
        # running animation skips its remaining pauses meanwhile.
        self._queued_move: Optional[str] = None
        # Moves played in this game: with none, there is nothing to lose.
        self._moves_played = 0
        # Finger movement of the current swipe (dx, dy).
        self._drag = [0.0, 0.0]
        self.swipe_area = self._build_swipe_area()
        self._configure_page()
        self.page.add(self._build_layout())
        self.refresh()

    def _configure_page(self) -> None:
        self.page.title = "Block Fall"
        # Everything starts at the top: no empty space above the header.
        self.page.vertical_alignment = ft.MainAxisAlignment.START
        self.page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        self.page.bgcolor = COLOR_BG
        self.page.window.width = WINDOW_WIDTH
        self.page.window.height = WINDOW_HEIGHT
        self.page.window.resizable = False
        # No page scrolling: the header stays at the top, and vertical swipes
        # always play instead of scrolling.
        self.page.padding = PAGE_PADDING
        self.page.on_resize = self._handle_resize
        self._lock_portrait()

    def _lock_portrait(self) -> None:
        """Keep phones and tablets in portrait (vertical) orientation.

        Flet only supports this on mobile and raises elsewhere; on desktop the
        fixed portrait-shaped window above serves the same purpose.
        """
        if self.page.platform is not None and self.page.platform.is_mobile():
            self.page.run_task(
                self.page.set_allowed_device_orientations,
                [ft.DeviceOrientation.PORTRAIT_UP],
            )

    def refresh(self, unlocking: frozenset[int] = frozenset()) -> None:
        """Show the current game. Levels in `unlocking` are shown gold."""
        self.score_display.value = str(self.game.score)
        self.high_score_display.value = str(self.game.high_score)
        if self.game.game_over:
            self.status_display.value = STATUS_GAME_OVER
        elif unlocking:
            self.status_display.value = STATUS_UNLOCKED
        else:
            self.status_display.value = STATUS_PLAY
        self._show_levels(unlocking)
        self._show_squares(self.game.squares())
        name, _, _, color = DIFFICULTIES[self.difficulty]
        self.level_value.value = name
        self.level_button.bgcolor = color
        self.game_over_button.visible = self.game.game_over
        self.page.update()

    def _show_levels(self, unlocking: frozenset[int] = frozenset()) -> None:
        unlocked = self.game.unlocked_colors()
        for block, color in zip(self.level_blocks, SQUARE_COLORS):
            if color in unlocking:
                block.bgcolor = COLOR_GOLD
                block.content = None
            elif color in unlocked:
                block.bgcolor = TILE_COLORS[color]
                block.content = None
            else:
                block.bgcolor = COLOR_LOCKED
                block.content = ft.Icon(ft.Icons.LOCK, size=16, color=COLOR_LOCK_ICON)

    def _position(self, tile: ft.Container, column: int, row: int) -> ft.Container:
        step = self.cell + CELL_SPACING
        tile.left = column * step
        tile.top = row * step
        tile.width = tile.height = self.cell
        return tile

    def _build_board(self) -> None:
        """(Re)build the empty grid for the current game's size."""
        self.cell = fit_cell(self._page_width, self.game.cols)
        self.slots = [
            self._position(create_tile(0), column, row)
            for row in range(self.game.rows)
            for column in range(self.game.cols)
        ]
        self.board.controls = list(self.slots)
        self.tiles = {}
        self._size_board()

    def _size_board(self) -> None:
        self.board.width = self.game.cols * self.cell + (self.game.cols - 1) * CELL_SPACING
        self.board.height = self.game.rows * self.cell + (self.game.rows - 1) * CELL_SPACING
        self.game_over_button.width = self.board.width + 2 * BOARD_PADDING

    def _handle_resize(self, event: Any) -> None:
        """Fit the grid to the new page width (it always fills the width)."""
        self._page_width = event.width
        self.cell = fit_cell(event.width, self.game.cols)
        self._size_board()
        for index, slot in enumerate(self.slots):
            self._position(slot, index % self.game.cols, index // self.game.cols)
        self._show_squares(self.game.squares())
        self.page.update()

    def _show_squares(
        self, squares: Squares, gold: frozenset[int] = frozenset(), pop: bool = False
    ) -> list[ft.Container]:
        """Make the board tiles match `squares` (id -> (column, row, color)).

        Existing tiles are moved (Flet animates the change), tiles of squares
        that are gone are removed, and new squares get new tiles, created tiny
        when `pop` is set so they can grow in. Returns the new tiles.
        """
        for square_id in [i for i in self.tiles if i not in squares]:
            self.board.controls.remove(self.tiles.pop(square_id))
        new_tiles = []
        for square_id, (column, row, color) in squares.items():
            tile = self.tiles.get(square_id)
            if tile is None:
                tile = create_tile(color)
                tile.animate_position = SLIDE
                tile.animate_scale = SLIDE
                tile.scale = 0 if pop else 1
                self.tiles[square_id] = tile
                self.board.controls.append(tile)
                new_tiles.append(tile)
            self._position(tile, column, row)
            tile.bgcolor = COLOR_GOLD if square_id in gold else TILE_COLORS.get(color, COLOR_BOARD_BG)
        return new_tiles

    async def _pause(self, seconds: float) -> None:
        """Wait for an animation, unless the player already swiped again."""
        if self._queued_move is None:
            await asyncio.sleep(seconds)

    async def _show_frame(self, frame: Frame, is_last: bool) -> None:
        """Show one step of a move and give its animation time to play."""
        new_tiles = self._show_squares(frame.squares, frame.gold, pop=True)
        self.page.update()
        if new_tiles:
            await self._pause(POP_START_SECONDS)  # let them appear tiny first
            for tile in new_tiles:
                tile.scale = 1
            self.page.update()
        if frame.kind == "match" or not is_last:
            await self._pause(PAUSES[frame.kind])

    async def _handle_move(self, direction: str) -> None:
        """Play a move and animate it: slide, gold flash, new square, and a
        gold flash on any level that this move unlocked.

        A swipe made meanwhile is never lost: it is played right after, and
        the running animation skips its remaining pauses (no "frozen" game).
        """
        if self._busy:
            self._queued_move = direction  # the latest swipe wins
            return
        self._busy = True
        try:
            next_move: Optional[str] = direction
            while next_move is not None:
                await self._play(next_move)
                next_move, self._queued_move = self._queued_move, None
        finally:
            self._busy = False
        if self._pending is not None:
            action, self._pending = self._pending, None
            action()

    async def _play(self, direction: str) -> None:
        unlocked_before = set(self.game.unlocked_colors())
        if self.game.play_move(direction):
            self._moves_played += 1
        frames = self.game.frames
        for index, frame in enumerate(frames):
            await self._show_frame(frame, is_last=index == len(frames) - 1)
        unlocking = frozenset(set(self.game.unlocked_colors()) - unlocked_before)
        self.refresh(unlocking)
        if unlocking:
            await self._pause(UNLOCK_FLASH_SECONDS)
            self.refresh()

    def _when_idle(self, action: Callable[[], None]) -> None:
        """Run `action` now, or right after the running animation."""
        if self._busy:
            self._pending = action
        else:
            action()

    def _game_in_progress(self) -> bool:
        """Would restarting now lose something? (a move played, not over)"""
        return self._moves_played > 0 and not self.game.game_over

    def _handle_restart(self, _event: Any) -> None:
        if self._game_in_progress():
            self._confirm("Restart the game?", "RESTART", COLOR_RESTART, self._restart)
        else:
            self._when_idle(self._restart)

    def _restart(self) -> None:
        self.game.reset()
        self._moves_played = 0
        self.refresh()

    def _handle_level(self, _event: Any) -> None:
        if self._game_in_progress():
            name, _, _, color = DIFFICULTIES[(self.difficulty + 1) % len(DIFFICULTIES)]
            self._confirm(f"Change to {name}?", "CHANGE", color, self._next_level)
        else:
            self._when_idle(self._next_level)

    def _confirm(
        self, question: str, ok_label: str, ok_color: str, action: Callable[[], None]
    ) -> None:
        """Ask before losing the current game (a modal dialog)."""

        def close(_event: Any) -> None:
            self.page.pop_dialog()

        def accept(_event: Any) -> None:
            self.page.pop_dialog()
            self._when_idle(action)

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(question, weight=ft.FontWeight.BOLD, color=COLOR_TEXT),
            content=ft.Text("You will lose the current game.", color=COLOR_TEXT),
            actions=[
                self._build_dialog_button("CANCEL", COLOR_BOARD_BG, close),
                self._build_dialog_button(ok_label, ok_color, accept),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=COLOR_BG,
        )
        self.page.show_dialog(dialog)

    @staticmethod
    def _build_dialog_button(
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

    def _next_level(self) -> None:
        """Switch to the next level: a new game on that level's grid."""
        self.difficulty = (self.difficulty + 1) % len(DIFFICULTIES)
        _, rows, cols, _ = DIFFICULTIES[self.difficulty]
        game = BlockFallEngine(rows=rows, cols=cols)
        game.high_score = self.game.high_score
        self.game = game
        self._moves_played = 0
        self._build_board()
        self.refresh()

    def _on_pan_start(self, _event: Any) -> None:
        self._drag = [0.0, 0.0]

    def _on_pan_update(self, event: Any) -> None:
        self._drag[0] += event.local_delta.x
        self._drag[1] += event.local_delta.y

    async def _on_pan_end(self, _event: Any) -> None:
        direction = swipe_direction(*self._drag)
        self._drag = [0.0, 0.0]
        if direction is not None:
            await self._handle_move(direction)

    def _build_layout(self) -> ft.Control:
        return ft.Container(
            content=ft.Column(
                [
                    self.header,
                    self.swipe_area,
                    # Always reserved at the bottom, so nothing moves when the
                    # big RESTART button appears at game over.
                    ft.Container(self.game_over_button, height=self.game_over_button.height),
                ],
                alignment=ft.MainAxisAlignment.START,
                spacing=10,
            ),
            padding=LAYOUT_PADDING,
            expand=True,
        )

    def _build_swipe_area(self) -> ft.GestureDetector:
        """Everything below the header reacts to swipes (touch or mouse)."""
        return ft.GestureDetector(
            content=ft.Container(
                content=ft.Column(
                    [
                        self.level_bar,
                        self.status_box,
                        ft.Container(
                            content=self.board,
                            bgcolor=COLOR_BOARD_BG,
                            padding=BOARD_PADDING,
                            border_radius=12,
                            alignment=ft.Alignment.CENTER,
                        ),
                    ],
                    # Pushed to the bottom: the free space stays between the
                    # logo and the color blocks.
                    alignment=ft.MainAxisAlignment.END,
                    spacing=6,
                ),
                # Painted, so swipes also work on the empty space.
                bgcolor=COLOR_BG,
                expand=True,
            ),
            on_pan_start=self._on_pan_start,
            on_pan_update=self._on_pan_update,
            on_pan_end=self._on_pan_end,
            expand=True,
        )

    @staticmethod
    def _build_block(label: str, value: ft.Control) -> ft.Container:
        """A header block: a small label above a value (score, best, restart)."""
        return ft.Container(
            content=ft.Column(
                [ft.Text(label, size=8, color=COLOR_MUTED_TEXT), value],
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


def main(page: ft.Page) -> None:
    """Start the Block Fall application."""
    BlockFallView(page)
