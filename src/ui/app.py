"""The app: puts the pieces together and runs the game flow."""

import asyncio
from typing import Any, Callable, Optional

import flet as ft

from config import (
    BOARD_PADDING,
    COLOR_BG,
    COLOR_RESTART,
    COLOR_STATUS,
    DEFAULT_DIFFICULTY,
    DIFFICULTIES,
    HEADER_BLOCK_HEIGHT,
    HEADER_BLOCK_SPACING,
    LAYOUT_PADDING,
    LEVEL_BLOCK_SIZE,
    PAGE_PADDING,
    UNLOCK_FLASH_SECONDS,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from game import BlockFallEngine
from saved import load_best_scores, load_tutorial_seen, save_best_score, save_tutorial_seen
from texts import DEFAULT_LANGUAGE, LANGUAGES, Texts, language_for
from ui.animation import Animator
from ui.board import BoardView
from ui.game_end import GameEnd
from ui.header import Header
from ui.level_bar import LevelBar
from ui.swipe import SwipeArea
from ui.turns import TurnQueue
from ui.tutorial import HelpButton, Tutorial
from ui.widgets import create_confirm_dialog

# Gaps between the header, the game area, and the bottom slot; and between
# the rows of the game area (final score, level blocks, message, grid).
LAYOUT_SPACING = 10
BODY_SPACING = 6


def status_text(unlocking: frozenset[int], texts: Texts) -> str:
    """The message under the level blocks (the same when the game is over)."""
    return texts.unlocked if unlocking else texts.play


def locale_configuration(language: str) -> ft.LocaleConfiguration:
    """Tells Flutter (its own built-in texts) which language the app uses."""
    return ft.LocaleConfiguration(
        supported_locales=[ft.Locale(code) for code in LANGUAGES],
        current_locale=ft.Locale(language),
    )


async def device_language(page: ft.Page) -> str:
    """The app's language for this device: Portuguese or English."""
    try:
        info = await page.get_device_info()
    except Exception:  # no device info here (e.g. an old client): use the default
        return DEFAULT_LANGUAGE
    return language_for(info.locales if info else [])


def configure_page(
    page: ft.Page,
    on_resize: Callable[[Any], None],
    on_media_change: Callable[[Any], None],
    on_locale_change: Callable[[Any], None],
    language: str,
) -> None:
    """Window, colors, language, and a portrait-only screen. `on_media_change`:
    the phone's system bars (status bar, home indicator) changed size."""
    page.title = "Block Fall"
    # Everything starts at the top: no empty space above the header.
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.bgcolor = COLOR_BG
    page.window.width = WINDOW_WIDTH
    page.window.height = WINDOW_HEIGHT
    page.window.resizable = False
    # No page scrolling: the header stays at the top, and vertical swipes
    # always play instead of scrolling.
    page.padding = PAGE_PADDING
    page.on_resize = on_resize
    page.on_media_change = on_media_change
    page.locale_configuration = locale_configuration(language)
    page.on_locale_change = on_locale_change
    # Flet can only lock the orientation on mobile (it raises elsewhere); on
    # desktop the portrait-shaped window does the job.
    if page.platform is not None and page.platform.is_mobile():
        page.run_task(page.set_allowed_device_orientations, [ft.DeviceOrientation.PORTRAIT_UP])


class BlockFallView:
    """Connects the screen to the game: input in, game state out."""

    def __init__(
        self,
        page: ft.Page,
        game: Optional[BlockFallEngine] = None,
        language: str = DEFAULT_LANGUAGE,
        best_scores: Optional[dict[int, int]] = None,
        storage: Any = None,
    ):
        """`best_scores`: {level index: best} saved before; `storage`: where a
        new best is saved (Flet's SharedPreferences; None: nowhere)."""
        self.page = page
        self.game = game if game is not None else BlockFallEngine()
        self.texts = LANGUAGES[language]
        self.difficulty = DEFAULT_DIFFICULTY
        self._move_played = False  # with none, restarting loses nothing
        # Each level keeps its own best score; BEST shows the current level's.
        self.best_scores = dict(best_scores or {})
        self.storage = storage
        self.game.high_score = self.best_scores.get(self.difficulty, 0)
        # What is known of the screen: its size, and the room its system bars take.
        self._screen_size = (page.width, page.height)
        self._system_bars = page.media.padding

        width, height = self._usable_size()
        self.header = Header(
            on_level=self._handle_level, on_restart=self._handle_restart, page_width=width
        )
        self.level_bar = LevelBar()
        # Up to 2 lines in a fixed-height box: the layout never jumps.
        self.status_display = ft.Text(
            "", size=13, weight=ft.FontWeight.BOLD, color=COLOR_STATUS,
            max_lines=2, text_align=ft.TextAlign.CENTER,
        )
        self.status_box = ft.Container(self.status_display, height=40, alignment=ft.Alignment.CENTER)
        # At game over: the points above the color blocks, and a big RESTART
        # button at the bottom. Everything else stays in place: the grid
        # always leaves room for them (see _board_height_limit).
        self.game_end = GameEnd(on_restart=self._handle_restart)
        # While playing, the bottom of the screen has a HOW TO PLAY button.
        self.help_button = HelpButton(on_click=lambda _event: self.show_tutorial())
        self.board = BoardView(
            self.game.rows, self.game.cols, width, self._board_height_limit(height)
        )
        self.swipe_area = SwipeArea(
            ft.Column(
                [self.game_end.banner, self.level_bar.control, self.status_box, self.board.frame],
                # Pushed to the bottom: the free space stays under the header.
                alignment=ft.MainAxisAlignment.END,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=BODY_SPACING,
            ),
            on_swipe=self._handle_move,
        )
        self.turns = TurnQueue()
        # Look up page.update on each use (never keep a stale bound method).
        self.animator = Animator(
            self.board, update=lambda: self.page.update(), hurry=lambda: self.turns.hurry
        )

        configure_page(
            page,
            on_resize=self._handle_resize,
            on_media_change=self._handle_media_change,
            on_locale_change=self._handle_locale_change,
            language=language,
        )
        self.layout = self._build_layout()
        # Below the phone's status bar (and notch), above its home indicator.
        page.add(ft.SafeArea(self.layout, expand=True))
        self.refresh()

    def _build_layout(self) -> ft.Control:
        return ft.Container(
            content=ft.Column(
                [
                    self.header.control,
                    self.swipe_area.control,
                    # Always reserved at the bottom, so nothing moves when the
                    # big RESTART button appears at game over (in place of
                    # the HOW TO PLAY button).
                    ft.Container(
                        ft.Column(
                            [self.help_button.control, self.game_end.button],
                            alignment=ft.MainAxisAlignment.CENTER,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        height=self.game_end.button.height,
                        alignment=ft.Alignment.CENTER,
                    ),
                ],
                alignment=ft.MainAxisAlignment.START,
                spacing=LAYOUT_SPACING,
            ),
            padding=LAYOUT_PADDING,
            expand=True,
        )

    # --- showing the game -------------------------------------------------

    def refresh(self, unlocking: frozenset[int] = frozenset()) -> None:
        """Show the current game. Levels in `unlocking` are shown gold."""
        texts = self.texts
        color = DIFFICULTIES[self.difficulty][3]
        level_name = texts.level_names[self.difficulty]
        self.header.show(self.game.score, self.game.high_score, level_name, color, texts)
        self.level_bar.show(self.game.unlocked_colors(), unlocking, texts)
        self.status_display.value = status_text(unlocking, texts)
        self.game_end.show(self.game.game_over, self.game.score, texts)
        self.help_button.show(not self.game.game_over, texts)
        self.board.show(self.game.squares())
        self.game_end.fit(self.board.outer_width)
        self.page.update()

    def set_language(self, language: str) -> None:
        """Show every text in `language` ("en" or "pt"); the game goes on."""
        self.texts = LANGUAGES[language]
        self.page.locale_configuration = locale_configuration(language)
        self.refresh()

    def show_tutorial(self) -> None:
        """How to play, in a dialog; once closed, the device remembers it was seen."""
        tutorial = Tutorial(self.texts, update=lambda: self.page.update(), on_close=self._close_tutorial)
        self.page.show_dialog(tutorial.dialog)

    def _close_tutorial(self) -> None:
        self.page.pop_dialog()
        if self.storage is not None:
            self.page.run_task(save_tutorial_seen, self.storage)

    def _handle_locale_change(self, event: Any) -> None:
        """The device's language changed while the app was open."""
        self.set_language(language_for(event.locales))

    def _usable_size(self) -> tuple[Optional[float], Optional[float]]:
        """The screen's width and height without the phone's system bars (the
        status bar, the notch, the home indicator): the room the SafeArea
        leaves. None when not known yet."""
        insets = self._system_bars
        width, height = self._screen_size
        return (
            width - insets.left - insets.right if width else None,
            height - insets.top - insets.bottom if height else None,
        )

    def _board_height_limit(self, page_height: Optional[float]) -> Optional[float]:
        """The tallest grid that leaves room for everything else on the screen,
        the final score of game over included (so nothing moves when it shows).

        None when the page height is not known: the grid just fills the width.
        """
        if not page_height:
            return None
        header = 2 * HEADER_BLOCK_HEIGHT + HEADER_BLOCK_SPACING
        rows = self.game_end.banner.height + LEVEL_BLOCK_SIZE + self.status_box.height
        body = rows + 3 * BODY_SPACING + 2 * BOARD_PADDING
        around = 2 * (PAGE_PADDING + LAYOUT_PADDING) + header + body + self.game_end.button.height
        return page_height - around - 2 * LAYOUT_SPACING

    def _handle_resize(self, event: Any) -> None:
        self._screen_size = (event.width, event.height)
        self._fit_to_screen()

    def _handle_media_change(self, event: Any) -> None:
        """The phone's system bars changed (e.g. the status bar appeared)."""
        self._system_bars = event.padding
        self._fit_to_screen()

    def _fit_to_screen(self) -> None:
        width, height = self._usable_size()
        self.header.resize(width)
        self.board.resize(width, self.game.squares(), self._board_height_limit(height))
        self.game_end.fit(self.board.outer_width)
        self.page.update()

    # --- playing ----------------------------------------------------------

    async def _handle_move(self, direction: str) -> None:
        """A swipe: played now, or right after the running animation."""
        await self.turns.submit(direction, self._play)

    async def _play(self, direction: str) -> None:
        """Play one move and animate it; a newly unlocked level flashes gold."""
        unlocked_before = set(self.game.unlocked_colors())
        if self.game.play_move(direction):
            self._move_played = True
        self._remember_best()
        await self.animator.play(self.game.frames)
        unlocking = frozenset(set(self.game.unlocked_colors()) - unlocked_before)
        self.refresh(unlocking)
        if unlocking:
            # In the background: the game goes on while the level is gold.
            self.page.run_task(self._end_unlock_flash)

    async def _end_unlock_flash(self) -> None:
        """After a short gold flash, show the unlocked level in its color.

        Only the level blocks and the message change: a move that may be
        animating on the grid meanwhile is left alone.
        """
        await asyncio.sleep(UNLOCK_FLASH_SECONDS)
        self.level_bar.show(self.game.unlocked_colors(), frozenset(), self.texts)
        self.status_display.value = status_text(frozenset(), self.texts)
        self.page.update()

    def _remember_best(self) -> None:
        """Keep a new best of the current level, and save it in the background."""
        best = self.game.high_score
        if best > self.best_scores.get(self.difficulty, 0):
            self.best_scores[self.difficulty] = best
            if self.storage is not None:
                self.page.run_task(save_best_score, self.storage, self.difficulty, best)

    # --- restart and level change ----------------------------------------

    def _game_in_progress(self) -> bool:
        """Would starting over lose something? (a move played, not over)"""
        return self._move_played and not self.game.game_over

    def _handle_restart(self, _event: Any) -> None:
        texts = self.texts
        self._ask_then(texts.restart_question, texts.restart, COLOR_RESTART, self._restart)

    def _handle_level(self, _event: Any) -> None:
        texts = self.texts
        following = (self.difficulty + 1) % len(DIFFICULTIES)
        question = texts.change_level_question.format(level=texts.level_names[following])
        self._ask_then(question, texts.change, DIFFICULTIES[following][3], self._next_level)

    def _ask_then(
        self, question: str, ok_label: str, ok_color: str, action: Callable[[], None]
    ) -> None:
        """Run `action` (when idle), first asking if a game would be lost."""
        if not self._game_in_progress():
            self.turns.when_idle(action)
            return

        def cancel(_event: Any) -> None:
            self.page.pop_dialog()

        def accept(_event: Any) -> None:
            self.page.pop_dialog()
            self.turns.when_idle(action)

        self.page.show_dialog(create_confirm_dialog(
            question, self.texts.lose_game, self.texts.cancel, ok_label, ok_color, cancel, accept
        ))

    def _restart(self) -> None:
        self.game.reset()
        self._move_played = False
        self.refresh()

    def _next_level(self) -> None:
        """A new game on the next level's grid, with that level's best score."""
        self._remember_best()
        self.difficulty = (self.difficulty + 1) % len(DIFFICULTIES)
        _, rows, cols, _ = DIFFICULTIES[self.difficulty]
        self.game = BlockFallEngine(rows=rows, cols=cols)
        self.game.high_score = self.best_scores.get(self.difficulty, 0)
        self._move_played = False
        self.board.rebuild(rows, cols)
        self.refresh()


async def main(page: ft.Page) -> None:
    """Start the Block Fall application, in the device's language, with the
    best score of each level saved on the device. A new player first sees how
    to play."""
    storage = ft.SharedPreferences()
    view = BlockFallView(
        page,
        language=await device_language(page),
        best_scores=await load_best_scores(storage),
        storage=storage,
    )
    if not await load_tutorial_seen(storage):
        view.show_tutorial()
