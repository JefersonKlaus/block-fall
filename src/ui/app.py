"""The app: puts the pieces together and runs the game flow."""

import asyncio
from typing import Any, Callable, Optional

import flet as ft

from config import (
    COLOR_BG,
    COLOR_RESTART,
    COLOR_STATUS,
    COLOR_TEXT,
    DEFAULT_DIFFICULTY,
    DIFFICULTIES,
    LAYOUT_PADDING,
    PAGE_PADDING,
    UNLOCK_FLASH_SECONDS,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from game import BlockFallEngine
from texts import DEFAULT_LANGUAGE, LANGUAGES, Texts, language_for
from ui.animation import Animator
from ui.board import BoardView
from ui.header import Header
from ui.level_bar import LevelBar
from ui.swipe import SwipeArea
from ui.turns import TurnQueue
from ui.widgets import create_confirm_dialog

def status_text(game: BlockFallEngine, unlocking: frozenset[int], texts: Texts) -> str:
    if game.game_over:
        return texts.game_over
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
    on_locale_change: Callable[[Any], None],
    language: str,
) -> None:
    """Window, colors, language, and a portrait-only screen."""
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
    ):
        self.page = page
        self.game = game if game is not None else BlockFallEngine()
        self.texts = LANGUAGES[language]
        self.difficulty = DEFAULT_DIFFICULTY
        self._moves_played = 0  # with none, restarting loses nothing

        self.header = Header(on_level=self._handle_level, on_restart=self._handle_restart)
        self.level_bar = LevelBar()
        # Up to 2 lines in a fixed-height box: the layout never jumps.
        self.status_display = ft.Text(
            "", size=13, weight=ft.FontWeight.BOLD, color=COLOR_STATUS,
            max_lines=2, text_align=ft.TextAlign.CENTER,
        )
        self.status_box = ft.Container(self.status_display, height=40, alignment=ft.Alignment.CENTER)
        self.board = BoardView(self.game.rows, self.game.cols, page.width)
        self.swipe_area = SwipeArea(
            ft.Column(
                [self.level_bar.control, self.status_box, self.board.frame],
                # Pushed to the bottom: the free space stays under the header.
                alignment=ft.MainAxisAlignment.END,
                spacing=6,
            ),
            on_swipe=self._handle_move,
        )
        # Shown at the bottom when the game is over: a big RESTART button.
        self.game_over_button = ft.Container(
            content=ft.Text("", size=22, weight=ft.FontWeight.BOLD, color=COLOR_TEXT),
            bgcolor=COLOR_RESTART,
            height=56,
            border_radius=12,
            alignment=ft.Alignment.CENTER,
            visible=False,
            on_click=self._handle_restart,
            ink=True,
        )
        self.turns = TurnQueue()
        # Look up page.update on each use (never keep a stale bound method).
        self.animator = Animator(
            self.board, update=lambda: self.page.update(), hurry=lambda: self.turns.hurry
        )

        configure_page(
            page,
            on_resize=self._handle_resize,
            on_locale_change=self._handle_locale_change,
            language=language,
        )
        page.add(self._build_layout())
        self.refresh()

    def _build_layout(self) -> ft.Control:
        return ft.Container(
            content=ft.Column(
                [
                    self.header.control,
                    self.swipe_area.control,
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

    # --- showing the game -------------------------------------------------

    def refresh(self, unlocking: frozenset[int] = frozenset()) -> None:
        """Show the current game. Levels in `unlocking` are shown gold."""
        texts = self.texts
        color = DIFFICULTIES[self.difficulty][3]
        level_name = texts.level_names[self.difficulty]
        self.header.show(self.game.score, self.game.high_score, level_name, color, texts)
        self.level_bar.show(self.game.unlocked_colors(), unlocking, texts)
        self.status_display.value = status_text(self.game, unlocking, texts)
        self.game_over_button.content.value = texts.restart
        self.game_over_button.tooltip = texts.restart_tip
        self.board.show(self.game.squares())
        self.game_over_button.width = self.board.outer_width
        self.game_over_button.visible = self.game.game_over
        self.page.update()

    def set_language(self, language: str) -> None:
        """Show every text in `language` ("en" or "pt"); the game goes on."""
        self.texts = LANGUAGES[language]
        self.page.locale_configuration = locale_configuration(language)
        self.refresh()

    def _handle_locale_change(self, event: Any) -> None:
        """The device's language changed while the app was open."""
        self.set_language(language_for(event.locales))

    def _handle_resize(self, event: Any) -> None:
        self.board.resize(event.width, self.game.squares())
        self.game_over_button.width = self.board.outer_width
        self.page.update()

    # --- playing ----------------------------------------------------------

    async def _handle_move(self, direction: str) -> None:
        """A swipe: played now, or right after the running animation."""
        await self.turns.submit(direction, self._play)

    async def _play(self, direction: str) -> None:
        """Play one move and animate it; a newly unlocked level flashes gold."""
        unlocked_before = set(self.game.unlocked_colors())
        if self.game.play_move(direction):
            self._moves_played += 1
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
        self.status_display.value = status_text(self.game, frozenset(), self.texts)
        self.page.update()

    # --- restart and level change ----------------------------------------

    def _game_in_progress(self) -> bool:
        """Would starting over lose something? (a move played, not over)"""
        return self._moves_played > 0 and not self.game.game_over

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
        self._moves_played = 0
        self.refresh()

    def _next_level(self) -> None:
        """A new game on the next level's grid (the best score is kept)."""
        self.difficulty = (self.difficulty + 1) % len(DIFFICULTIES)
        _, rows, cols, _ = DIFFICULTIES[self.difficulty]
        best = self.game.high_score
        self.game = BlockFallEngine(rows=rows, cols=cols)
        self.game.high_score = best
        self._moves_played = 0
        self.board.rebuild(rows, cols)
        self.refresh()


async def main(page: ft.Page) -> None:
    """Start the Block Fall application, in the device's language."""
    BlockFallView(page, language=await device_language(page))
