import asyncio
import colorsys
import itertools
import math
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, call, patch

import flet as ft

import ui
from config import (
    ANIMATION_SECONDS,
    BLUE,
    CELL_SIZE,
    CELL_SPACING,
    COLOR_BG,
    COLOR_BOARD_BG,
    COLOR_EMPTY,
    COLOR_GOLD,
    COLOR_LOCK_ICON,
    COLOR_LOCKED,
    COLOR_RESTART,
    COLOR_TEXT,
    DEFAULT_DIFFICULTY,
    DIFFICULTIES,
    GOLD_FLASH_SECONDS,
    GREEN,
    GRID_COLS,
    GRID_ROWS,
    PEACH,
    POP_START_SECONDS,
    RED,
    START_FILL,
    TILE_COLORS,
    TILE_RADIUS,
    UNLOCK_FLASH_SECONDS,
    UNLOCK_SCORES,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from game import SQUARE_COLORS, BlockFallEngine, Frame
from ui import BlockFallView
from tests.helpers import MockPage, iter_controls, lab, lightness
from ui.widgets import create_tile

SWIPES = {"left": (-80, 5), "right": (80, -5), "up": (4, -80), "down": (-4, 80)}


def step(view):
    """Distance between two neighbouring squares on the board."""
    return view.board.cell + CELL_SPACING


def last_choice(values):
    """Deterministic stand-in for random.choice: rightmost column, etc."""
    return values[-1]


def move(view, direction):
    """Run the (async) move handler to completion."""
    asyncio.run(view._handle_move(direction))


def place(game, *squares):
    """Put squares on the board: place(game, (column, row, color), ...)."""
    for column, row, color in squares:
        assert game.place_square(column, row, color), "bad test setup"


def is_colors(values):
    """True for the random.choice call that picks a color (not a position)."""
    return all(isinstance(value, int) for value in values)


def next_colors(*colors):
    """Make new squares get these colors (and the first free position)."""
    queue = iter(colors)
    return patch(
        "game.random.choice",
        side_effect=lambda v: next(queue) if is_colors(v) else v[0],
    )


def next_position_last(color):
    """Make the new square take the last free position on its edge."""
    return patch(
        "game.random.choice",
        side_effect=lambda v: color if is_colors(v) else v[-1],
    )


def board_colors(view):
    """What the player sees: the color shown at each (row, column)."""
    colors = [[COLOR_EMPTY] * view.game.cols for _ in range(view.game.rows)]
    for tile in view.board.tiles.values():
        assert tile in view.board.stack.controls
        colors[round(tile.top / step(view))][round(tile.left / step(view))] = tile.bgcolor
    return colors


class NoDelay:
    """Mixin: replace animation pauses with instant, recorded ones."""

    def setUp(self):
        super().setUp()
        patcher = patch("ui.animation.asyncio.sleep", new_callable=AsyncMock)
        self.sleep = patcher.start()
        self.addCleanup(patcher.stop)


class MockPageTests(unittest.TestCase):
    def test_mock_rejects_attributes_that_ft_page_does_not_have(self):
        page = MockPage()
        for name in ("window_width", "window_height", "window_resizable"):
            with self.assertRaises(AttributeError):
                setattr(page, name, 1)

    def test_mock_accepts_real_page_attributes(self):
        page = MockPage()
        page.title = "x"
        page.padding = 1
        self.assertEqual((page.title, page.padding), ("x", 1))


class ViewCase(NoDelay, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.page = MockPage()
        # An empty 10x10 board (not tied to any level's size), so each test
        # sets up exactly the squares it needs.
        self.view = BlockFallView(self.page, BlockFallEngine(rows=10, cols=10, start_squares=0))
        self.game = self.view.game
        # The constructor already calls refresh(); reset the flag so each
        # test proves its own action triggered a page update.
        self.page.updated = False
        self.layout = self.page.controls[0]

    def find_buttons(self, button_type):
        return [c for c in iter_controls(self.layout) if isinstance(c, button_type)]

    def swipe(self, direction_or_dx, dy=None, steps=4):
        """Drag a finger across the game area (like a real touch)."""
        dx, dy = SWIPES[direction_or_dx] if dy is None else (direction_or_dx, dy)
        area = self.view.swipe_area.control
        area.on_pan_start(None)
        for _ in range(steps):
            area.on_pan_update(SimpleNamespace(local_delta=ft.Offset(dx / steps, dy / steps)))
        asyncio.run(area.on_pan_end(None))


class UITests(ViewCase):
    def test_view_builds_one_layout(self):
        self.assertEqual(len(self.page.controls), 1)

    def test_refresh_updates_page(self):
        self.view.refresh()
        self.assertTrue(self.page.updated)

    def test_move_adds_exactly_one_square(self):
        move(self.view, "left")
        self.assertEqual(len(self.view.board.tiles), 1)
        self.assertTrue(self.page.updated)

    def test_every_move_adds_one_square(self):
        with next_colors(BLUE, GREEN, RED, BLUE):  # never 3 alike: no match
            for presses, direction in enumerate(["left", "right", "up", "down"], start=1):
                move(self.view, direction)
                self.assertEqual(len(self.view.board.tiles), presses)

    def test_game_over_refresh_shows_game_over_message(self):
        self.game.game_over = True
        self.view.refresh()
        self.assertEqual(self.view.status_display.value, "GAME OVER")

    def test_normal_refresh_shows_move_message(self):
        self.view.refresh()
        self.assertEqual(
            self.view.status_display.value, "Line up 3 or more squares of the same color."
        )

    def test_move_refreshes_page(self):
        move(self.view, "left")
        self.assertTrue(self.page.updated)


class NoBorderTests(ViewCase):
    """Blocks have no borders: rounded squares with small gaps, like 2048."""

    def test_tiles_have_no_border_and_rounded_corners(self):
        for tile in (create_tile(0), create_tile(BLUE), create_tile(RED, gold=True)):
            self.assertIsNone(tile.border)
            self.assertEqual(tile.border_radius, TILE_RADIUS)

    def test_board_squares_have_no_border(self):
        place(self.game, (0, 8, BLUE), (1, 8, GREEN), (0, 9, RED))
        self.view.refresh()
        self.assertTrue(all(t.border is None for t in self.view.board.tiles.values()))
        self.assertTrue(all(s.border is None for s in self.view.board.slots))

    def test_squares_are_separated_by_a_small_gap(self):
        self.assertEqual((CELL_SIZE, CELL_SPACING), (30, 4))
        place(self.game, (0, 9, BLUE), (1, 9, GREEN), (2, 9, RED), (3, 9, BLUE))
        self.view.refresh()
        lefts = sorted(t.left for t in self.view.board.tiles.values())
        self.assertEqual(lefts, [0, step(self.view), 2 * step(self.view), 3 * step(self.view)])

    def test_ui_has_no_outline_helpers_left(self):
        self.assertFalse(hasattr(ui, "outline_sides"))


class NoNextCardTests(ViewCase):
    """The "Next" card is gone: only the board, the status and the controls."""

    def texts(self):
        return [c.value for c in iter_controls(self.layout) if isinstance(c, ft.Text)]

    def test_no_next_label_and_no_hint(self):
        self.assertNotIn("Next:", self.texts())
        self.assertFalse(any("next block" in (t or "").lower() for t in self.texts()))

    def test_no_preview_anywhere(self):
        self.assertFalse(hasattr(self.view, "preview_container"))
        self.assertFalse(hasattr(ui, "create_piece_preview"))


class ViewTests(ViewCase):
    def test_layout_from_top_to_bottom(self):
        # header (logo, score, best, restart), then the touch area with the
        # level blocks, the message, and the grid. No arrow buttons.
        header, area, game_over_slot = self.layout.content.controls
        self.assertIs(header, self.view.header.control)
        self.assertIs(area, self.view.swipe_area.control)
        self.assertIs(game_over_slot.content, self.view.game_over_button)
        levels, message, board_box = area.content.content.controls
        self.assertIs(levels, self.view.level_bar.control)
        self.assertIs(message.content, self.view.status_display)
        self.assertIs(board_box.content, self.view.board.stack)

    def test_message_is_below_the_level_blocks_and_above_the_grid(self):
        column = self.view.swipe_area.control.content.content.controls
        self.assertEqual(column.index(self.view.status_box), column.index(self.view.level_bar.control) + 1)
        board_box = next(c for c in column if getattr(c, "content", None) is self.view.board.stack)
        self.assertLess(column.index(self.view.status_box), column.index(board_box))

    def test_everything_from_the_color_blocks_down_is_pushed_to_the_bottom(self):
        # The free space goes between the logo and the color blocks.
        column = self.view.swipe_area.control.content.content
        self.assertIs(column.controls[0], self.view.level_bar.control)
        self.assertEqual(column.alignment, ft.MainAxisAlignment.END)
        self.assertTrue(self.view.swipe_area.control.expand)

    def test_the_only_space_at_the_bottom_is_kept_for_the_big_restart(self):
        slot = self.layout.content.controls[-1]
        self.assertEqual(slot.height, self.view.game_over_button.height)  # always reserved
        self.assertFalse(self.view.game_over_button.visible)  # ...even while hidden
        self.assertLessEqual(self.layout.content.spacing, 10)

    def test_header_stays_at_the_top_with_no_empty_space_above(self):
        self.assertIs(self.layout.content.controls[0], self.view.header.control)
        self.assertEqual(self.page.vertical_alignment, ft.MainAxisAlignment.START)
        self.assertEqual(self.layout.content.alignment, ft.MainAxisAlignment.START)
        self.assertIsNone(getattr(self.page, "scroll", None))  # the header never scrolls away

    def test_page_is_configured(self):
        self.assertEqual(self.page.title, "Block Fall")
        self.assertEqual(self.page.bgcolor, COLOR_BG)
        self.assertEqual(self.page.vertical_alignment, ft.MainAxisAlignment.START)
        self.assertEqual(self.page.horizontal_alignment, ft.CrossAxisAlignment.CENTER)
        self.assertEqual((self.page.window.width, self.page.window.height), (390, 840))
        self.assertEqual((WINDOW_WIDTH, WINDOW_HEIGHT), (390, 840))
        self.assertFalse(self.page.window.resizable)
        self.assertEqual(self.page.padding, 10)

    def test_board_shows_every_empty_slot_of_the_configured_grid(self):
        rows, cols = self.game.rows, self.game.cols
        self.assertEqual(len(self.view.board.slots), rows * cols)
        positions = {(s.left, s.top) for s in self.view.board.slots}
        self.assertEqual(
            positions,
            {(c * step(self.view), r * step(self.view)) for r in range(rows) for c in range(cols)},
        )
        self.assertTrue(all(s.bgcolor == COLOR_EMPTY for s in self.view.board.slots))
        cell = self.view.board.cell
        self.assertTrue(all((s.width, s.height) == (cell, cell) for s in self.view.board.slots))

    def test_board_is_a_stack_sized_for_the_grid(self):
        self.assertIsInstance(self.view.board.stack, ft.Stack)
        size = self.game.cols * self.view.board.cell + (self.game.cols - 1) * CELL_SPACING
        self.assertEqual((self.view.board.stack.width, self.view.board.stack.height), (size, size))

    def test_board_height_leaves_room_for_the_rest(self):
        self.assertLess(self.view.board.stack.height, self.page.window.height / 2)

    def test_board_shows_the_engine_squares(self):
        place(self.game, (1, 8, BLUE), (0, 9, GREEN), (1, 9, RED), (2, 9, BLUE))
        self.view.refresh()
        colors = board_colors(self.view)
        self.assertEqual(colors[8][:3], [COLOR_EMPTY, TILE_COLORS[BLUE], COLOR_EMPTY])
        self.assertEqual(colors[9][:3], [TILE_COLORS[GREEN], TILE_COLORS[RED], TILE_COLORS[BLUE]])
        self.assertEqual(sum(c != COLOR_EMPTY for row in colors for c in row), 4)

    def test_refresh_does_not_duplicate_tiles(self):
        place(self.game, (0, 0, BLUE), (1, 0, GREEN))
        self.view.refresh()
        count = len(self.view.board.stack.controls)
        self.view.refresh()
        self.assertEqual(len(self.view.board.stack.controls), count)
        self.assertEqual(count, self.game.rows * self.game.cols + 2)

    def test_new_square_appears_on_the_opposite_side(self):
        with next_position_last(RED):
            move(self.view, "down")
        # After moving down, the square appears on the top edge (last position).
        self.assertEqual(board_colors(self.view)[0][-1], TILE_COLORS[RED])

    def test_refresh_shows_score_and_high_score(self):
        self.game.score = 120
        self.game.high_score = 340
        self.view.refresh()
        self.assertEqual(self.view.header.score_text.value, "120")
        self.assertEqual(self.view.header.best_text.value, "340")

    def test_layout_contains_score_cards(self):
        texts = [c.value for c in iter_controls(self.layout) if isinstance(c, ft.Text)]
        for text in ("SCORE", "BEST"):
            self.assertIn(text, texts)

    def test_no_arrow_buttons_and_no_round_buttons(self):
        buttons = [
            c for c in iter_controls(self.layout)
            if isinstance(c, (ft.Button, ft.IconButton, ft.TextButton, ft.FilledButton))
        ]
        self.assertEqual(buttons, [])
        self.assertFalse(hasattr(ui, "MOVE_BUTTONS"))

    def test_swipe_up_and_down_end_to_end(self):
        place(self.game, (0, 9, BLUE), (1, 8, GREEN))
        with next_position_last(RED):
            self.swipe("up")
        colors = board_colors(self.view)
        self.assertEqual(colors[0][:2], [TILE_COLORS[BLUE], TILE_COLORS[GREEN]])
        # Squares went up, so the new one appeared on the bottom edge.
        self.assertEqual(colors[-1][-1], TILE_COLORS[RED])
        with next_position_last(GREEN):
            self.swipe("down")
        colors = board_colors(self.view)
        self.assertEqual(colors[-1][:2], [TILE_COLORS[BLUE], TILE_COLORS[GREEN]])
        self.assertEqual(colors[-1][-1], TILE_COLORS[RED])
        # Squares went down, so the new one appeared on the top edge.
        self.assertEqual(colors[0][-1], TILE_COLORS[GREEN])

    def test_swipe_left_end_to_end(self):
        bottom = self.game.rows - 1
        place(self.game, (4, bottom, BLUE), (6, bottom, GREEN))
        with next_position_last(RED):
            self.swipe("left")
        row = board_colors(self.view)[bottom]
        # Slid left; the new red square came in on the right edge (last row).
        self.assertEqual(row, [TILE_COLORS[BLUE], TILE_COLORS[GREEN]]
                         + [COLOR_EMPTY] * (self.game.cols - 3) + [TILE_COLORS[RED]])
        self.assertTrue(self.page.updated)

    def test_three_in_a_line_disappear_and_score_end_to_end(self):
        bottom = self.game.rows - 1
        place(self.game, (0, bottom, BLUE), (1, bottom, BLUE), (7, bottom, BLUE))
        with next_colors(GREEN):
            self.swipe("left")
        self.assertEqual(board_colors(self.view)[bottom][:3], [COLOR_EMPTY] * 3)
        self.assertEqual(self.view.header.score_text.value, "3")

    def test_four_in_a_line_score_five(self):
        bottom = self.game.rows - 1
        place(self.game, *[(c, bottom, RED) for c in (0, 2, 5, 9)])
        with next_colors(GREEN):
            self.swipe("left")
        self.assertEqual(self.view.header.score_text.value, "5")

    def test_move_handler_forwards_direction_to_engine(self):
        with patch.object(self.game, "play_move") as play_move:
            move(self.view, "right")
        play_move.assert_called_once_with("right")


class AnimationTests(ViewCase):
    """Squares slide to their new place (like 2048), new squares pop in."""

    def setUp(self):
        super().setUp()
        self.sent = []  # what the player saw at each page.update()
        self.page.update = lambda: self.sent.append(self.snapshot())

    def snapshot(self):
        return {sid: (t.left, t.top, t.bgcolor, t.scale) for sid, t in self.view.board.tiles.items()}

    def test_every_square_tile_animates_its_position(self):
        place(self.game, (0, 0, BLUE), (1, 0, GREEN))
        self.view.refresh()
        for tile in self.view.board.tiles.values():
            self.assertEqual(tile.animate_position.duration, int(ANIMATION_SECONDS * 1000))
            self.assertEqual(tile.animate_scale.duration, int(ANIMATION_SECONDS * 1000))

    def test_a_moving_square_keeps_the_same_tile(self):
        place(self.game, (5, 8, BLUE), (6, 9, GREEN))
        self.view.refresh()
        tiles_before = dict(self.view.board.tiles)
        with next_colors(RED):
            move(self.view, "left")
        for square_id, tile in tiles_before.items():
            self.assertIs(self.view.board.tiles[square_id], tile)  # same control: Flet animates it
        self.assertEqual(sorted(t.left for t in tiles_before.values()), [0, 0])

    def test_slide_is_shown_then_given_time_to_finish(self):
        place(self.game, (5, 8, BLUE), (6, 9, GREEN))
        self.view.refresh()
        self.sent.clear()
        seen_during_pause = []

        async def pause(seconds):
            seen_during_pause.append((seconds, self.sent[-1]))

        self.sleep.side_effect = pause
        with next_colors(RED):
            move(self.view, "left")
        seconds, on_screen = seen_during_pause[0]
        self.assertEqual(seconds, ANIMATION_SECONDS)
        self.assertEqual(sorted(v[0] for v in on_screen.values()), [0, 0])

    def test_no_slide_pause_when_nothing_moves(self):
        place(self.game, (0, 8, BLUE))
        self.view.refresh()
        with next_colors(RED):
            move(self.view, "left")
        self.assertNotIn(call(ANIMATION_SECONDS), self.sleep.await_args_list)

    def test_new_square_pops_in(self):
        move(self.view, "left")
        (new_id,) = self.view.board.tiles
        first_seen = next(s for s in self.sent if new_id in s)
        self.assertEqual(first_seen[new_id][3], 0)  # tiny
        self.assertEqual(self.sent[-1][new_id][3], 1)  # full size
        self.assertIn(call(POP_START_SECONDS), self.sleep.await_args_list)

    def test_refresh_shows_existing_squares_at_full_size(self):
        place(self.game, (0, 0, BLUE))
        self.view.refresh()
        self.assertTrue(all(t.scale == 1 for t in self.view.board.tiles.values()))

    def test_removed_squares_leave_the_board(self):
        place(self.game, (0, 9, BLUE), (1, 9, BLUE), (7, 9, BLUE), (5, 3, RED))
        self.view.refresh()
        with next_colors(GREEN):
            move(self.view, "left")
        self.assertEqual(len(self.view.board.tiles), 4 - 3 + 1)
        self.assertEqual(len(self.view.board.stack.controls), self.game.rows * self.game.cols + 2)

    def test_last_frame_without_a_match_needs_no_pause(self):
        move(self.view, "left")  # empty board: only a spawn frame
        self.assertEqual(self.sleep.await_args_list, [call(POP_START_SECONDS)])

    def test_pause_order_for_slide_match_and_spawn(self):
        place(self.game, (0, 9, BLUE), (1, 9, BLUE), (7, 9, BLUE))
        self.view.refresh()
        with next_colors(GREEN):
            move(self.view, "left")
        self.assertEqual(
            self.sleep.await_args_list,
            [call(ANIMATION_SECONDS), call(GOLD_FLASH_SECONDS), call(POP_START_SECONDS)],
        )

    def test_animation_is_quick(self):
        self.assertTrue(0 < ANIMATION_SECONDS <= 0.1)
        self.assertTrue(0 < POP_START_SECONDS < ANIMATION_SECONDS)


class GoldFlashTests(ViewCase):
    """Matched squares turn gold, stay visible for a moment, then disappear."""

    def setUp(self):
        super().setUp()
        self.bottom = self.game.rows - 1
        place(self.game, (0, self.bottom, BLUE), (1, self.bottom, BLUE),
              (7, self.bottom, BLUE), (7, 5, GREEN))
        self.view.refresh()

    def test_matched_squares_turn_gold_then_disappear(self):
        frames = []
        sent_to_screen = []
        self.page.update = lambda: sent_to_screen.append(board_colors(self.view))

        async def pause(seconds):
            if seconds == GOLD_FLASH_SECONDS:
                # During the pause, the screen must already show the gold frame.
                frames.append((board_colors(self.view), sent_to_screen[-1]))

        self.sleep.side_effect = pause
        with next_colors(RED):
            move(self.view, "left")
        ((flash, on_screen),) = frames
        self.assertEqual(on_screen, flash)
        self.assertEqual(flash[self.bottom][:4], [COLOR_GOLD] * 3 + [COLOR_EMPTY])
        self.assertEqual(flash[5][0], TILE_COLORS[GREEN])  # other squares keep their color
        after = board_colors(self.view)
        self.assertEqual(after[self.bottom][:3], [COLOR_EMPTY] * 3)
        self.assertNotIn(COLOR_GOLD, [c for row in after for c in row])
        self.assertEqual(self.view.header.score_text.value, "3")

    def test_no_gold_flash_without_a_match(self):
        # Moving up puts the blues in different rows: no line.
        with next_colors(RED):
            move(self.view, "up")
        self.assertEqual(self.view.header.score_text.value, "0")
        self.assertNotIn(call(GOLD_FLASH_SECONDS), self.sleep.await_args_list)

    def test_each_match_in_a_move_flashes_in_order(self):
        # Square 2 exists in both frames (a real move never brings one back).
        first = Frame("match", {1: (0, 0, BLUE), 2: (9, 9, RED)}, frozenset({1}))
        second = Frame("match", {2: (9, 9, RED)}, frozenset({2}))
        seen = []

        async def pause(_seconds):
            seen.append(board_colors(self.view))

        self.sleep.side_effect = pause

        def fake_play_move(direction):
            self.game.frames = [first, second]
            return True

        with patch.object(self.game, "play_move", side_effect=fake_play_move):
            move(self.view, "up")
        self.assertEqual(len(seen), 2)
        self.assertEqual((seen[0][0][0], seen[0][9][9]), (COLOR_GOLD, TILE_COLORS[RED]))
        self.assertEqual((seen[1][0][0], seen[1][9][9]), (COLOR_EMPTY, COLOR_GOLD))

    def test_a_swipe_during_the_gold_flash_is_not_lost(self):
        async def swipe_again(seconds):
            if seconds == GOLD_FLASH_SECONDS:
                await self.view._handle_move("up")

        self.sleep.side_effect = swipe_again
        with patch.object(self.game, "play_move", wraps=self.game.play_move) as play_move:
            with next_colors(RED, RED):
                move(self.view, "left")
        self.assertEqual([c.args[0] for c in play_move.call_args_list], ["left", "up"])

    def test_a_waiting_swipe_skips_the_rest_of_the_animation(self):
        pauses = []

        async def pause(seconds):
            pauses.append(seconds)
            if len(pauses) == 1:  # during the slide, the player swipes again
                await self.view._handle_move("up")

        self.sleep.side_effect = pause
        with next_colors(RED, RED):
            move(self.view, "left")
        # Move 1: only its slide pause (gold + pop skipped).
        # Move 2 ("up" also slides): its slide pause and its pop.
        self.assertEqual(pauses, [ANIMATION_SECONDS, ANIMATION_SECONDS, POP_START_SECONDS])
        self.assertEqual(self.view.header.score_text.value, "3")  # move 1 still scored

    def test_the_latest_of_several_waiting_swipes_wins(self):
        fired = []

        async def many_swipes(seconds):
            if seconds == ANIMATION_SECONDS and not fired:
                fired.append(True)
                for direction in ("up", "right", "down"):
                    await self.view._handle_move(direction)

        self.sleep.side_effect = many_swipes
        with patch.object(self.game, "play_move", wraps=self.game.play_move) as play_move:
            with next_colors(RED, RED):
                move(self.view, "left")
        self.assertEqual([c.args[0] for c in play_move.call_args_list], ["left", "down"])

    def test_without_a_waiting_swipe_the_flash_plays_in_full(self):
        with next_colors(RED):
            move(self.view, "left")
        self.assertIn(call(GOLD_FLASH_SECONDS), self.sleep.await_args_list)

    def test_handler_is_usable_again_after_the_animation(self):
        with next_colors(RED, GREEN):
            move(self.view, "left")
            self.assertFalse(self.view.turns.busy)
            tiles = len(self.view.board.tiles)
            move(self.view, "up")
        self.assertEqual(len(self.view.board.tiles), tiles + 1)

    def test_flash_pause_is_short(self):
        self.assertTrue(0 < GOLD_FLASH_SECONDS <= 0.15)

    def test_a_scoring_move_settles_in_under_0_3_seconds(self):
        with next_colors(RED):
            move(self.view, "left")  # slide, gold, new square
        self.assertLess(sum(c.args[0] for c in self.sleep.await_args_list), 0.3)


class MainTests(unittest.TestCase):
    def start(self, **page_options):
        page = MockPage(**page_options)
        with patch("ui.animation.asyncio.sleep", new_callable=AsyncMock):
            self.assertIsNone(asyncio.run(ui.main(page)))
        return page

    def test_main_builds_the_view_on_the_page(self):
        page = self.start()
        self.assertEqual(len(page.controls), 1)
        self.assertEqual(page.title, "Block Fall")
        self.assertTrue(page.updated)

    def test_a_portuguese_device_starts_in_portuguese(self):
        page = self.start(device_languages=("pt-BR", "en-US"))
        texts = [c.value for c in iter_controls(page.controls[0]) if isinstance(c, ft.Text)]
        self.assertIn("Alinhe 3 ou mais quadrados da mesma cor.", texts)
        self.assertIn("PONTOS", texts)

    def test_any_other_device_starts_in_english(self):
        page = self.start(device_languages=("es-ES",))
        texts = [c.value for c in iter_controls(page.controls[0]) if isinstance(c, ft.Text)]
        self.assertIn("Line up 3 or more squares of the same color.", texts)

    def test_no_device_info_means_english(self):
        for answer in (None, RuntimeError("not available here")):
            with self.subTest(answer=answer):
                page = self.start(device_languages=answer)
                texts = [c.value for c in iter_controls(page.controls[0]) if isinstance(c, ft.Text)]
                self.assertIn("SCORE", texts)

    def test_changing_the_device_language_switches_the_app(self):
        page = self.start()
        page.on_locale_change(SimpleNamespace(locales=[ft.Locale("pt", "BR")]))
        texts = [c.value for c in iter_controls(page.controls[0]) if isinstance(c, ft.Text)]
        self.assertIn("RECORDE", texts)
        page.on_locale_change(SimpleNamespace(locales=[ft.Locale("en", "GB")]))
        texts = [c.value for c in iter_controls(page.controls[0]) if isinstance(c, ft.Text)]
        self.assertIn("BEST", texts)


class OrientationTests(unittest.TestCase):
    def test_window_is_portrait(self):
        page = MockPage()
        BlockFallView(page)
        self.assertGreater(page.window.height, page.window.width)
        self.assertFalse(page.window.resizable)

    def test_mobile_app_is_locked_to_portrait(self):
        for platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS):
            with self.subTest(platform=platform):
                page = MockPage(platform=platform)
                BlockFallView(page)
                self.assertEqual(len(page.tasks), 1)
                handler, args = page.tasks[0]
                self.assertEqual(handler, page.set_allowed_device_orientations)
                asyncio.run(handler(*args))
                self.assertEqual(page.orientations, [ft.DeviceOrientation.PORTRAIT_UP])

    def test_orientation_lock_is_not_requested_off_mobile(self):
        # Flet raises FletUnsupportedPlatformException on non-mobile platforms.
        for platform in (ft.PagePlatform.WINDOWS, ft.PagePlatform.MACOS,
                         ft.PagePlatform.LINUX, None):
            with self.subTest(platform=platform):
                page = MockPage(platform=platform)
                BlockFallView(page)
                self.assertEqual(page.tasks, [])


class PastelThemeTests(ViewCase):
    """The whole app uses soft pastel colors."""

    SQUARES = [TILE_COLORS[c] for c in SQUARE_COLORS]

    def test_square_colors_are_pastel(self):
        for color in self.SQUARES:
            self.assertTrue(0.7 <= lightness(color) <= 0.9, color)

    def test_square_colors_are_easy_to_tell_apart(self):
        closest = min(math.dist(lab(a), lab(b)) for a, b in itertools.combinations(self.SQUARES, 2))
        self.assertGreaterEqual(closest, 25)

    def test_gold_flash_and_empty_slots_stand_out_from_every_square(self):
        for other in (COLOR_GOLD, COLOR_EMPTY):
            closest = min(math.dist(lab(other), lab(c)) for c in self.SQUARES)
            self.assertGreaterEqual(closest, 25, other)

    def test_light_background_with_dark_readable_text(self):
        for background in (COLOR_BG, COLOR_BOARD_BG, COLOR_EMPTY):
            self.assertGreater(lightness(background), 0.85, background)
        self.assertLess(lightness(COLOR_TEXT), 0.4)
        self.assertEqual(self.page.bgcolor, COLOR_BG)
        texts = [c for c in iter_controls(self.layout) if isinstance(c, ft.Text)]
        colors = [t.color for t in texts]
        self.assertTrue(all(lightness(color) < 0.6 for color in colors), colors)

    def test_header_blocks_are_pastel_too(self):
        for block in self.view.header.blocks:
            self.assertGreater(lightness(block.bgcolor), 0.7)


class LevelBarTests(ViewCase):
    """5 blocks above the grid, one per color: black until unlocked."""

    def colors(self):
        return [block.bgcolor for block in self.view.level_bar.control.controls]

    def test_five_blocks_in_color_order(self):
        self.assertEqual(len(self.view.level_bar.control.controls), 5)
        self.assertEqual(self.view.level_bar.blocks, self.view.level_bar.control.controls)

    def test_a_new_game_shows_two_colors_and_three_black_blocks(self):
        self.assertEqual(self.colors(), [TILE_COLORS[BLUE], TILE_COLORS[GREEN]] + [COLOR_LOCKED] * 3)

    def test_locked_blocks_are_gray_with_a_lock(self):
        for block in self.view.level_bar.blocks[2:]:
            self.assertEqual(block.bgcolor, COLOR_LOCKED)
            self.assertIsInstance(block.content, ft.Icon)
            self.assertEqual(block.content.icon, ft.Icons.LOCK)
            self.assertEqual(block.content.color, COLOR_LOCK_ICON)
            self.assertEqual(block.alignment, ft.Alignment.CENTER)  # lock in the middle
        for block in self.view.level_bar.blocks[:2]:
            self.assertIsNone(block.content)

    def test_locked_gray_cannot_be_mistaken_for_a_color(self):
        self.assertNotEqual(COLOR_LOCKED, "#000000")
        r, g, b = (int(COLOR_LOCKED[i:i + 2], 16) / 255 for i in (1, 3, 5))
        self.assertLess(colorsys.rgb_to_hls(r, g, b)[2], 0.15)  # gray: almost no saturation
        for color in SQUARE_COLORS:
            self.assertGreaterEqual(math.dist(lab(COLOR_LOCKED), lab(TILE_COLORS[color])), 25)
        self.assertGreaterEqual(math.dist(lab(COLOR_LOCKED), lab(COLOR_BG)), 20)
        self.assertGreaterEqual(math.dist(lab(COLOR_LOCKED), lab(COLOR_LOCK_ICON)), 25)

    def test_lock_disappears_when_the_color_unlocks(self):
        self.game.score = 50
        self.view.refresh()
        self.assertIsNone(self.view.level_bar.blocks[2].content)
        self.assertIsInstance(self.view.level_bar.blocks[3].content, ft.Icon)

    def test_blocks_light_up_as_the_score_grows(self):
        expected = {
            49: 2, 50: 3, 149: 3, 150: 4, 349: 4, 350: 5,
        }
        for score, unlocked in expected.items():
            self.game.score = score
            self.view.refresh()
            self.assertEqual(
                self.colors(),
                [TILE_COLORS[c] for c in SQUARE_COLORS[:unlocked]] + [COLOR_LOCKED] * (5 - unlocked),
                score,
            )

    def test_each_block_tells_when_it_unlocks(self):
        tips = [block.tooltip for block in self.view.level_bar.blocks]
        self.assertEqual(tips[:2], ["Starting color", "Starting color"])
        self.assertEqual(tips[2:], [f"Unlocks at {UNLOCK_SCORES[i]} points" for i in (2, 3, 4)])

    def test_scoring_past_50_unlocks_the_third_block_end_to_end(self):
        bottom = self.game.rows - 1
        place(self.game, (0, bottom, BLUE), (1, bottom, BLUE), (7, bottom, BLUE))
        self.game.score = 48
        self.view.refresh()
        self.assertEqual(self.colors()[2], COLOR_LOCKED)
        with next_colors(GREEN):
            self.swipe("left")
        self.assertEqual(self.view.header.score_text.value, "51")
        self.assertEqual(self.colors()[2], COLOR_GOLD)  # unlocking...
        run_background_tasks(self.page)
        self.assertEqual(self.colors()[2], TILE_COLORS[RED])

    def test_blocks_are_squares_like_the_board(self):
        for block in self.view.level_bar.blocks:
            self.assertEqual((block.width, block.height), (CELL_SIZE, CELL_SIZE))
            self.assertEqual(block.border_radius, TILE_RADIUS)


class StartTests(unittest.TestCase):
    def test_a_new_game_shows_squares_on_the_grid(self):
        with patch("ui.animation.asyncio.sleep", new_callable=AsyncMock):
            view = BlockFallView(MockPage())
        self.assertEqual(len(view.board.tiles), round(GRID_ROWS * GRID_COLS * START_FILL))
        colors = {tile.bgcolor for tile in view.board.tiles.values()}
        self.assertLessEqual(colors, {TILE_COLORS[BLUE], TILE_COLORS[GREEN]})
        self.assertTrue(all(tile.scale == 1 for tile in view.board.tiles.values()))


def needed_width(view, page):
    """Screen width the board really takes: board + all paddings around it."""
    layout = page.controls[0]
    board_box = next(c for c in iter_controls(layout) if getattr(c, "content", None) is view.board.stack)
    return view.board.stack.width + 2 * (page.padding + layout.padding + board_box.padding)


class BoardFitTests(unittest.TestCase):
    """The whole grid is visible on every screen (bug: right column cut in half)."""

    WIDTHS = (320, 360, 374, 375, 390, 412, 430, 800)

    def view(self, width, game=None):
        with patch("ui.animation.asyncio.sleep", new_callable=AsyncMock):
            page = MockPage(width=width)
            view = BlockFallView(page, game or BlockFallEngine(start_squares=0))
        return page, view

    def test_board_fits_the_real_page_width(self):
        for width in self.WIDTHS:
            with self.subTest(width=width):
                page, view = self.view(width)
                self.assertLessEqual(needed_width(view, page), width)

    def test_regression_right_column_fully_visible_on_a_360_phone(self):
        page, view = self.view(360)
        for row in range(GRID_ROWS):
            view.game.place_square(GRID_COLS - 1, row, BLUE)
        view.refresh()
        for tile in view.board.tiles.values():
            self.assertLessEqual(tile.left + tile.width, view.board.stack.width)
        self.assertLessEqual(needed_width(view, page), 360)

    def test_regression_fits_a_windows_window_of_390_with_its_frame(self):
        # window.width (390) includes the frame; the page only gets ~374.
        page, view = self.view(374)
        self.assertEqual(page.window.width, 390)
        self.assertLessEqual(needed_width(view, page), 374)

    def test_grid_uses_100_percent_of_the_width(self):
        for width in self.WIDTHS:
            with self.subTest(width=width):
                page, view = self.view(width)
                self.assertAlmostEqual(needed_width(view, page), width)

    def test_any_grid_size_uses_100_percent_of_the_width(self):
        for rows, cols in ((10, 10), (8, 12), (12, 8), (5, 5), (6, 10), (15, 7)):
            for width in (360, 412):
                with self.subTest(rows=rows, cols=cols, width=width):
                    page, view = self.view(width, BlockFallEngine(rows=rows, cols=cols, start_squares=0))
                    self.assertEqual(len(view.board.slots), rows * cols)
                    self.assertAlmostEqual(needed_width(view, page), width)
                    last = max(view.board.slots, key=lambda s: (s.left, s.top))
                    self.assertAlmostEqual(last.left + last.width, view.board.stack.width)
                    self.assertAlmostEqual(last.top + last.height, view.board.stack.height)
                    self.assertAlmostEqual(
                        view.board.stack.height, rows * view.board.cell + (rows - 1) * CELL_SPACING
                    )

    def test_squares_on_a_non_square_grid_land_in_the_right_place(self):
        page, view = self.view(360, BlockFallEngine(rows=6, cols=12, start_squares=0))
        view.game.place_square(11, 5, RED)
        view.refresh()
        (tile,) = view.board.tiles.values()
        self.assertAlmostEqual(tile.left + tile.width, view.board.stack.width)
        self.assertAlmostEqual(tile.top + tile.height, view.board.stack.height)

    def test_page_does_not_scroll_so_swipes_always_play(self):
        page, view = self.view(360, BlockFallEngine(rows=30, cols=10, start_squares=0))
        self.assertIsNone(getattr(page, "scroll", None))

    def test_every_slot_and_square_uses_the_fitted_size(self):
        page, view = self.view(320)
        view.game.place_square(3, 4, GREEN)
        view.refresh()
        self.assertEqual(view.board.stack.width, GRID_COLS * view.board.cell + (GRID_COLS - 1) * CELL_SPACING)
        for control in view.board.slots + list(view.board.tiles.values()):
            self.assertEqual((control.width, control.height), (view.board.cell, view.board.cell))
        (tile,) = view.board.tiles.values()
        self.assertEqual((tile.left, tile.top), (3 * step(view), 4 * step(view)))

    def test_unknown_page_width_uses_a_small_safe_size(self):
        page, view = self.view(None)
        self.assertAlmostEqual(needed_width(view, page), 320)

    def test_board_adapts_when_the_screen_size_changes(self):
        page, view = self.view(412)
        view.game.place_square(GRID_COLS - 1, 0, RED)
        view.refresh()
        self.assertEqual(page.on_resize, view._handle_resize)
        page.width = 330
        page.updated = False
        view._handle_resize(type("ResizeEvent", (), {"width": 330, "height": 700})())
        self.assertAlmostEqual(needed_width(view, page), 330)
        (tile,) = view.board.tiles.values()
        self.assertEqual(tile.left, (GRID_COLS - 1) * (view.board.cell + CELL_SPACING))
        self.assertEqual(tile.width, view.board.cell)
        # The empty slots underneath follow too, and all stay inside the board.
        for index, slot in enumerate(view.board.slots):
            self.assertEqual((slot.width, slot.left, slot.top),
                             (view.board.cell, index % GRID_COLS * step(view), index // GRID_COLS * step(view)))
            self.assertLessEqual(slot.left + slot.width, view.board.stack.width + 1e-9)
        self.assertTrue(page.updated)

    def test_layout_still_fits_the_screen_height(self):
        page, view = self.view(360)
        self.assertLess(view.board.stack.height, 640 / 2)


class LogoTests(ViewCase):
    """A logo replaces the plain "Block Fall" title."""

    def test_logo_is_in_the_header_instead_of_a_plain_title(self):
        header = self.view.header.control
        self.assertIs(header.controls[0].content, self.view.header.logo)
        plain = [c.value for c in iter_controls(header) if isinstance(c, ft.Text) and c.value]
        self.assertNotIn("Block Fall", plain)
        self.assertEqual(self.page.title, "Block Fall")  # still the window / app name


class RestartTests(ViewCase):
    """A button to start a new game."""

    def restart(self):
        self.view.header.restart_button.on_click(None)

    def test_restart_is_a_blue_block_below_best(self):
        score, best, level, restart = self.view.header.blocks
        self.assertIs(restart, self.view.header.restart_button)
        top_row, bottom_row = self.view.header.control.controls[1].controls
        self.assertEqual(top_row.controls, [score, best])
        self.assertEqual(bottom_row.controls, [level, restart])  # restart under BEST
        self.assertEqual((restart.width, restart.height, restart.border_radius),
                         (best.width, best.height, best.border_radius))
        self.assertEqual(restart.bgcolor, COLOR_RESTART)
        self.assertIsInstance(restart, ft.Container)
        self.assertEqual(restart.tooltip, "Restart")

    def test_restart_color_is_blue(self):
        r, g, b = (int(COLOR_RESTART[i:i + 2], 16) / 255 for i in (1, 3, 5))
        hue = colorsys.rgb_to_hls(r, g, b)[0] * 360
        self.assertTrue(190 <= hue <= 240, hue)

    def test_restart_block_has_a_label_like_the_others(self):
        texts = [c.value for c in iter_controls(self.view.header.restart_button) if isinstance(c, ft.Text)]
        icons = [c.icon for c in iter_controls(self.view.header.restart_button) if isinstance(c, ft.Icon)]
        self.assertEqual((texts, icons), (["RESTART"], [ft.Icons.RESTART_ALT]))

    def test_restart_starts_a_new_game_and_keeps_the_best_score(self):
        place(self.game, (0, 0, BLUE), (1, 0, GREEN))
        self.game.score = self.game.high_score = 200
        self.game.game_over = True
        self.view.refresh()
        old_tiles = set(self.view.board.tiles)
        self.game.start_squares = 10
        self.page.updated = False
        self.restart()
        self.assertEqual((self.game.score, self.game.high_score, self.game.game_over), (0, 200, False))
        self.assertEqual(self.view.header.score_text.value, "0")
        self.assertEqual(self.view.header.best_text.value, "200")
        self.assertEqual(len(self.view.board.tiles), 10)
        self.assertTrue(old_tiles.isdisjoint(self.view.board.tiles))
        self.assertEqual([b.bgcolor for b in self.view.level_bar.blocks[2:]], [COLOR_LOCKED] * 3)
        self.assertEqual(self.view.status_display.value, "Line up 3 or more squares of the same color.")
        self.assertTrue(self.page.updated)

    def test_message_box_has_a_fixed_height_so_nothing_jumps(self):
        self.assertEqual(self.view.status_display.max_lines, 2)
        self.assertIs(self.view.status_box.content, self.view.status_display)
        self.assertEqual(self.view.status_box.height, 40)

    def test_game_over_message_is_only_game_over(self):
        self.game.game_over = True
        self.view.refresh()
        self.assertEqual(self.view.status_display.value, "GAME OVER")

    def test_restart_during_an_animation_happens_right_after_it(self):
        place(self.game, (0, 0, BLUE))
        squares_during = []

        async def restart_during_animation(_seconds):
            if not squares_during:
                self.restart()  # a move is being played: asks first
                confirm(self.page)
                squares_during.append(len(self.game.squares()))

        self.sleep.side_effect = restart_during_animation
        with next_colors(GREEN):
            move(self.view, "down")
        self.assertTrue(all(n >= 1 for n in squares_during))  # not reset mid-animation
        self.assertEqual(self.game.squares(), {})  # ...but right after (new empty game)
        self.assertEqual(self.view.board.tiles, {})
        self.assertIsNone(self.view.turns.pending)


def run_background_tasks(page):
    """Run what the app handed to page.run_task (Flet runs it in the background)."""
    while page.tasks:
        handler, args = page.tasks.pop(0)
        asyncio.run(handler(*args))


class UnlockFlashTests(ViewCase):
    """A newly unlocked level turns gold, then shows its color, in the
    background: it never holds up the game."""

    def setUp(self):
        super().setUp()
        self.bottom = self.game.rows - 1
        place(self.game, (0, self.bottom, BLUE), (1, self.bottom, BLUE), (7, self.bottom, BLUE))
        self.game.score = 48  # the line of 3 brings it to 51: the 3rd color unlocks
        self.view.refresh()
        self.third = self.view.level_bar.blocks[2]
        self.seen = []  # the 3rd level block as sent to the screen
        self.page.update = lambda: self.seen.append(
            (self.third.bgcolor, self.third.content is not None, self.view.status_display.value)
        )

    def test_locked_then_gold_then_its_color(self):
        with next_colors(GREEN):
            move(self.view, "left")
        run_background_tasks(self.page)
        colors = [bg for bg, _, _ in self.seen]
        self.assertEqual(colors[0], COLOR_LOCKED)
        self.assertIn(COLOR_GOLD, colors)
        self.assertEqual(colors[-1], TILE_COLORS[RED])
        first_gold = colors.index(COLOR_GOLD)
        self.assertNotIn(TILE_COLORS[RED], colors[:first_gold])  # gold comes first

    def test_the_move_does_not_wait_for_the_flash(self):
        with next_colors(GREEN):
            move(self.view, "left")
        # Only the move's own pauses (slide, gold, pop): no extra wait for the level.
        self.assertEqual(
            self.sleep.await_args_list,
            [call(ANIMATION_SECONDS), call(GOLD_FLASH_SECONDS), call(POP_START_SECONDS)],
        )
        self.assertFalse(self.view.turns.busy)  # the next swipe can play at once
        # ...while the level block is still gold, with the message:
        self.assertEqual(self.third.bgcolor, COLOR_GOLD)
        self.assertEqual(self.view.status_display.value, "New color unlocked!")
        self.assertEqual(len(self.page.tasks), 1)  # the flash ends in the background

    def test_flash_ends_with_its_color_and_the_normal_message(self):
        with next_colors(GREEN):
            move(self.view, "left")
        during = []

        async def pause(seconds):
            during.append((seconds, self.third.bgcolor))

        self.sleep.side_effect = pause
        run_background_tasks(self.page)
        self.assertEqual(during, [(UNLOCK_FLASH_SECONDS, COLOR_GOLD)])
        self.assertEqual(self.third.bgcolor, TILE_COLORS[RED])
        self.assertIsNone(self.third.content)
        self.assertEqual(self.view.status_display.value, "Line up 3 or more squares of the same color.")
        self.assertEqual(self.seen[-1][0], TILE_COLORS[RED])  # sent to the screen

    def test_the_flash_ending_does_not_touch_the_grid(self):
        with next_colors(GREEN):
            move(self.view, "left")
        before = {i: (t.left, t.top, t.bgcolor, t.scale) for i, t in self.view.board.tiles.items()}
        run_background_tasks(self.page)
        after = {i: (t.left, t.top, t.bgcolor, t.scale) for i, t in self.view.board.tiles.items()}
        self.assertEqual(after, before)  # a move animating meanwhile is not disturbed

    def test_flash_ending_during_the_next_move_leaves_its_slide_alone(self):
        with next_colors(GREEN):
            move(self.view, "left")  # unlocks: the flash will end in the background
        (flash_end, args), = self.page.tasks
        self.page.tasks.clear()
        seen = []

        async def pause(seconds):
            if seconds == ANIMATION_SECONDS and not seen:  # the next move is sliding
                self.sleep.side_effect = None
                await flash_end(*args)  # ...when the flash ends
                seen.append({i: (t.left, t.top) for i, t in self.view.board.tiles.items()})

        self.sleep.side_effect = pause
        with next_colors(RED):
            move(self.view, "down")
        slide = self.game.frames[0]
        self.assertEqual(slide.kind, "slide")
        step = self.view.board.cell + CELL_SPACING
        # Mid-slide, the grid shows the slide step (not the end of the move).
        self.assertEqual(seen[0], {i: (c * step, r * step) for i, (c, r, _) in slide.squares.items()})

    def test_flash_ending_after_game_over_keeps_game_over(self):
        with next_colors(GREEN):
            move(self.view, "left")
        self.game.game_over = True
        run_background_tasks(self.page)
        self.assertEqual(self.view.status_display.value, "GAME OVER")

    def test_no_unlock_flash_without_a_new_level(self):
        self.game.score = 0
        self.view.refresh()
        with next_colors(GREEN):
            move(self.view, "left")
        self.assertEqual(self.page.tasks, [])
        self.assertNotIn(COLOR_GOLD, [bg for bg, _, _ in self.seen])

    def test_two_levels_at_once_both_flash(self):
        def jump(direction):
            self.game.score = 160  # past 50 and 150
            self.game.frames = []
            return True

        self.game.score = 0
        self.view.refresh()
        with patch.object(self.game, "play_move", side_effect=jump):
            move(self.view, "left")
        self.assertEqual([b.bgcolor for b in self.view.level_bar.blocks][2:],
                         [COLOR_GOLD, COLOR_GOLD, COLOR_LOCKED])
        run_background_tasks(self.page)
        self.assertEqual([b.bgcolor for b in self.view.level_bar.blocks][2:4],
                         [TILE_COLORS[RED], TILE_COLORS[PEACH]])

    def test_unlock_flash_is_as_fast_as_the_gold_in_the_grid(self):
        self.assertEqual(UNLOCK_FLASH_SECONDS, GOLD_FLASH_SECONDS)


class HeaderTests(ViewCase):
    """Logo on the left; SCORE and BEST, with LEVEL and RESTART below them."""

    def test_header_holds_the_logo_and_two_rows_of_blocks(self):
        logo_holder, blocks = self.view.header.control.controls
        self.assertIs(logo_holder.content, self.view.header.logo)
        rows = [row.controls for row in blocks.controls]
        self.assertEqual(rows, [self.view.header.blocks[:2], self.view.header.blocks[2:]])

    def test_all_header_blocks_have_the_same_size(self):
        sizes = {(b.width, b.height) for b in self.view.header.blocks}
        self.assertEqual(len(sizes), 1)

    def test_header_blocks_are_large(self):
        block = self.view.header.blocks[0]
        self.assertGreaterEqual((block.width, block.height), (64, 50))
        label, value = block.content.controls
        self.assertGreaterEqual(label.size, 10)
        self.assertGreaterEqual(value.size, 20)
        self.assertGreaterEqual(self.view.header.level_text.size, 11)
        icon = self.view.header.restart_button.content.controls[1]
        self.assertGreaterEqual(icon.size, 24)

    def test_everything_fits_a_small_360x640_phone(self):
        page = MockPage(width=360)
        with patch("ui.animation.asyncio.sleep", new_callable=AsyncMock):
            view = BlockFallView(page)  # the real default game
        layout = page.controls[0].content
        header_h = 2 * view.header.blocks[0].height + view.header.control.controls[1].spacing
        body = view.swipe_area.control.content.content
        levels_h = view.level_bar.blocks[0].height
        board_h = view.board.stack.height + 2 * view.board.frame.padding
        body_h = levels_h + view.status_box.height + board_h + 2 * body.spacing
        slot_h = layout.controls[-1].height
        total = 2 * (page.padding + page.controls[0].padding) + header_h + body_h + slot_h + 2 * layout.spacing
        self.assertLessEqual(total, 640)

    def test_whole_header_with_the_big_logo_fits_a_360_phone(self):
        available = 360 - 2 * (self.page.padding + self.layout.padding)
        _, blocks = self.view.header.control.controls
        top_row = blocks.controls[0]
        blocks_width = sum(b.width for b in top_row.controls) + top_row.spacing
        mark, name = self.view.header.logo.controls
        cell = mark.controls[0].controls[0].width
        mark_width = 3 * cell + 2 * mark.controls[0].spacing
        # No font measuring in tests: estimate the name generously (heavy bold
        # letters average about 0.62 of the font size; the longer line counts).
        name_width = max(0.62 * t.size * len(t.value) for t in name.controls)
        total = mark_width + self.view.header.logo.spacing + name_width + self.view.header.control.spacing + blocks_width
        self.assertLessEqual(total, available)

    def test_logo_is_not_taller_than_the_two_rows_of_blocks(self):
        _, blocks = self.view.header.control.controls
        blocks_height = 2 * self.view.header.blocks[0].height + blocks.spacing
        mark, name = self.view.header.logo.controls
        cell = mark.controls[0].controls[0].height
        self.assertLessEqual(3 * cell + 2 * mark.spacing, blocks_height)
        self.assertLessEqual(sum(1.25 * t.size for t in name.controls), blocks_height)


class SwipeTests(ViewCase):
    """Play by touch: swipe anywhere in the game area, like 2048."""

    def test_each_swipe_plays_that_move(self):
        for direction in SWIPES:
            with self.subTest(direction=direction):
                with patch.object(self.game, "play_move") as play_move:
                    self.swipe(direction)
                play_move.assert_called_once_with(direction)

    def test_a_tap_or_tiny_drag_does_not_play(self):
        with patch.object(self.game, "play_move") as play_move:
            self.swipe(6, 3)
        play_move.assert_not_called()

    def test_a_new_swipe_starts_from_zero(self):
        with patch.object(self.game, "play_move") as play_move:
            self.swipe(15, 0)  # too short on its own
            self.swipe(15, 0)  # must not add up with the previous one
        play_move.assert_not_called()

    def test_an_interrupted_swipe_does_not_leak_into_the_next_one(self):
        area = self.view.swipe_area.control
        area.on_pan_start(None)
        area.on_pan_update(SimpleNamespace(local_delta=ft.Offset(20, 0)))
        # ...the gesture is cancelled: no pan end. Then a tiny new drag:
        with patch.object(self.game, "play_move") as play_move:
            self.swipe(10, 0)
        play_move.assert_not_called()

    def test_the_movement_is_added_up_while_the_finger_moves(self):
        with patch.object(self.game, "play_move") as play_move:
            self.swipe(-40, 0, steps=8)  # 8 small steps of 5 px
        play_move.assert_called_once_with("left")

    def test_swipe_area_covers_levels_message_and_grid_but_not_the_header(self):
        area = self.view.swipe_area.control
        inside = list(iter_controls(area))
        for control in (self.view.level_bar.control, self.view.status_display, self.view.board.stack):
            self.assertIn(control, inside)
        self.assertNotIn(self.view.header.restart_button, inside)
        self.assertTrue(area.expand)
        self.assertTrue(area.content.expand)
        self.assertEqual(area.content.bgcolor, COLOR_BG)  # painted: swipes work on empty space too

    def test_real_swipe_moves_the_squares(self):
        place(self.game, (5, 5, BLUE))
        with next_colors(GREEN):
            self.swipe("right")
        self.assertEqual(board_colors(self.view)[5][-1], TILE_COLORS[BLUE])


class DifficultyTests(ViewCase):
    """The LEVEL block (below SCORE) switches between 3 grid sizes."""

    def setUp(self):
        super().setUp()
        # The real default game: MIDDLE's grid (empty, for predictable tests).
        self.view.game = self.game = BlockFallEngine(start_squares=0)
        self.view.board.rebuild(self.game.rows, self.game.cols)
        self.view.refresh()

    def level_texts(self):
        return [c.value for c in iter_controls(self.view.header.level_button) if isinstance(c, ft.Text)]

    def tap(self):
        self.view.header.level_button.on_click(None)

    def test_the_three_levels(self):
        self.assertEqual(
            [(name, rows, cols) for name, rows, cols, _ in DIFFICULTIES],
            [("BEGINNER", 6, 6), ("MIDDLE", 5, 5), ("MASTER", 4, 4)],
        )
        self.assertEqual(DIFFICULTIES[DEFAULT_DIFFICULTY][0], "MIDDLE")

    def test_level_colors_green_yellow_red(self):
        hues = []
        for _, _, _, color in DIFFICULTIES:
            r, g, b = (int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))
            hues.append(colorsys.rgb_to_hls(r, g, b)[0] * 360)
        green, yellow, red = hues
        self.assertTrue(100 <= green <= 160, green)
        self.assertTrue(40 <= yellow <= 60, yellow)
        self.assertTrue(red <= 15 or red >= 345, red)

    def test_level_block_is_below_score(self):
        score, _best, level, _restart = self.view.header.blocks
        self.assertIs(level, self.view.header.level_button)
        top_row, bottom_row = self.view.header.control.controls[1].controls
        self.assertEqual(top_row.controls.index(score), bottom_row.controls.index(level))

    def test_starts_at_middle_in_yellow(self):
        self.assertEqual(self.level_texts(), ["LEVEL", "MIDDLE"])
        self.assertEqual(self.view.header.level_button.bgcolor, DIFFICULTIES[1][3])
        self.assertEqual((self.game.rows, self.game.cols), (5, 5))

    def test_each_tap_goes_to_the_next_level_and_its_grid(self):
        for name, rows, cols, color in (DIFFICULTIES[2], DIFFICULTIES[0], DIFFICULTIES[1]):
            with self.subTest(level=name):
                self.tap()
                self.assertEqual(self.level_texts(), ["LEVEL", name])
                self.assertEqual(self.view.header.level_button.bgcolor, color)
                game = self.view.game
                self.assertEqual((game.rows, game.cols), (rows, cols))
                self.assertEqual(len(self.view.board.slots), rows * cols)
                self.assertEqual(len(self.view.board.stack.controls), rows * cols + len(self.view.board.tiles))

    def test_new_level_starts_a_new_game_and_keeps_the_best(self):
        self.game.score = self.game.high_score = 120
        self.game.game_over = True
        self.view.refresh()
        self.tap()
        game = self.view.game
        self.assertEqual((game.score, game.high_score, game.game_over), (0, 120, False))
        self.assertEqual(len(self.view.board.tiles), round(4 * 4 * START_FILL))  # MASTER
        self.assertEqual(self.view.header.best_text.value, "120")
        self.assertFalse(self.view.game_over_button.visible)
        self.assertEqual([b.bgcolor for b in self.view.level_bar.blocks[2:]], [COLOR_LOCKED] * 3)

    def test_the_new_grid_fills_the_width(self):
        for _ in range(3):
            self.tap()
            needed = self.view.board.stack.width + 2 * (self.page.padding + self.layout.padding
                                                  + self.view.swipe_area.control.content.content.controls[2].padding)
            self.assertAlmostEqual(needed, self.page.width)

    def test_swipes_play_on_the_new_grid(self):
        self.tap()  # MASTER 4x4
        game = self.view.game
        game.start_squares = 0
        game.reset()  # an empty 4x4 board
        game.place_square(1, 1, BLUE)
        self.view.refresh()
        with next_colors(GREEN):
            self.swipe("right")
        self.assertEqual(game.grid[1][3], BLUE)
        self.assertEqual(board_colors(self.view)[1][3], TILE_COLORS[BLUE])

    def test_level_change_during_an_animation_happens_right_after_it(self):
        place(self.game, (0, 0, BLUE))

        tapped = []

        async def tap_during_animation(_seconds):
            if not tapped:
                tapped.append(True)
                self.tap()  # a move is being played: asks first
                confirm(self.page)

        self.sleep.side_effect = tap_during_animation
        move(self.view, "down")  # real random: the new game needs many colors
        self.assertEqual((self.view.game.rows, self.view.game.cols), (4, 4))
        self.assertEqual(self.level_texts(), ["LEVEL", "MASTER"])


class GameOverButtonTests(ViewCase):
    """When the game ends, a big blue RESTART button appears at the bottom."""

    def big_text(self):
        (text,) = [c for c in iter_controls(self.view.game_over_button) if isinstance(c, ft.Text)]
        return text

    def test_hidden_while_playing(self):
        self.assertFalse(self.view.game_over_button.visible)

    def test_shown_when_the_game_ends(self):
        self.game.game_over = True
        self.view.refresh()
        self.assertTrue(self.view.game_over_button.visible)

    def test_it_is_at_the_bottom_of_the_app(self):
        self.assertIs(self.layout.content.controls[-1].content, self.view.game_over_button)

    def test_it_is_big_and_blue(self):
        button = self.view.game_over_button
        board_box = self.view.swipe_area.control.content.content.controls[2]
        self.assertEqual(button.width, self.view.board.stack.width + 2 * board_box.padding)  # full width
        self.assertGreaterEqual(button.height, 56)
        self.assertEqual(button.bgcolor, COLOR_RESTART)
        self.assertEqual(self.big_text().value, "RESTART")
        self.assertGreaterEqual(self.big_text().size, 20)
        self.assertEqual(self.big_text().weight, ft.FontWeight.BOLD)

    def test_tapping_it_starts_a_new_game_and_hides_it(self):
        self.game.game_over = True
        self.view.refresh()
        self.view.game_over_button.on_click(None)
        self.assertFalse(self.game.game_over)
        self.assertFalse(self.view.game_over_button.visible)

    def test_appears_after_the_move_that_fills_the_board(self):
        rows, cols = self.game.rows, self.game.cols
        colors = (BLUE, GREEN)
        for row in range(rows):
            for col in range(cols):
                if (row, col) != (rows - 1, cols - 1):
                    # a pattern with no 3 in a line
                    self.game.place_square(col, row, colors[(col // 2 + row) % 2])
        self.view.refresh()
        pick = RED if self.game.grid[rows - 1][cols - 3] != RED else BLUE
        with next_colors(pick):
            move(self.view, "left")
        self.assertTrue(self.game.game_over)
        self.assertTrue(self.view.game_over_button.visible)


def dialog_buttons(page):
    return {
        c.content.value: c
        for c in page.dialog.actions
    }


def confirm(page):
    page.dialog.actions[1].on_click(None)  # the second button: RESTART / CHANGE


def cancel(page):
    page.dialog.actions[0].on_click(None)  # the first button: CANCEL


class ConfirmTests(ViewCase):
    """Restart or level change during a game asks first: the game would be lost."""

    def play_one_move(self):
        with next_colors(GREEN):
            move(self.view, "left")

    def test_no_question_before_the_first_move(self):
        self.view.header.restart_button.on_click(None)
        self.assertIsNone(getattr(self.page, "dialog", None))

    def test_restart_during_a_game_asks_first(self):
        self.play_one_move()
        self.view.header.restart_button.on_click(None)
        dialog = self.page.dialog
        self.assertIsInstance(dialog, ft.AlertDialog)
        self.assertTrue(dialog.modal)
        self.assertEqual(dialog.title.value, "Restart the game?")
        self.assertEqual(dialog.content.value, "You will lose the current game.")
        self.assertEqual(len(self.game.squares()), 1)  # nothing lost yet

    def test_confirming_restarts(self):
        self.play_one_move()
        self.view.header.restart_button.on_click(None)
        confirm(self.page)
        self.assertIsNone(self.page.dialog)
        self.assertEqual(self.game.squares(), {})

    def test_cancelling_keeps_the_game(self):
        self.play_one_move()
        self.game.score = 42
        self.view.header.restart_button.on_click(None)
        cancel(self.page)
        self.assertIsNone(self.page.dialog)
        self.assertEqual((len(self.game.squares()), self.game.score), (1, 42))

    def test_level_change_during_a_game_asks_first(self):
        self.play_one_move()
        self.view.header.level_button.on_click(None)
        self.assertEqual(self.page.dialog.title.value, "Change to MASTER?")
        self.assertEqual(self.page.dialog.content.value, "You will lose the current game.")
        self.assertEqual((self.view.game.rows, self.view.game.cols), (10, 10))  # unchanged
        confirm(self.page)
        self.assertEqual((self.view.game.rows, self.view.game.cols), (4, 4))

    def test_cancelling_the_level_change_keeps_level_and_game(self):
        self.play_one_move()
        game = self.view.game
        self.view.header.level_button.on_click(None)
        cancel(self.page)
        self.assertIs(self.view.game, game)
        self.assertEqual(self.view.header.level_text.value, "MIDDLE")

    def test_no_question_once_the_game_is_over(self):
        self.play_one_move()
        self.game.game_over = True
        self.view.refresh()
        self.view.header.restart_button.on_click(None)
        self.assertIsNone(getattr(self.page, "dialog", None))
        self.assertEqual(self.game.squares(), {})

    def test_swipes_after_game_over_do_not_count_as_moves(self):
        self.game.game_over = True
        self.view.refresh()
        self.swipe("left")  # the game refuses it
        self.game.game_over = False  # even if the game could go on again...
        self.view.header.restart_button.on_click(None)
        self.assertIsNone(getattr(self.page, "dialog", None))  # ...no move was played

    def test_big_game_over_button_never_asks(self):
        self.play_one_move()
        self.game.game_over = True
        self.view.refresh()
        self.view.game_over_button.on_click(None)
        self.assertIsNone(getattr(self.page, "dialog", None))
        self.assertFalse(self.game.game_over)

    def test_a_new_game_does_not_ask_until_a_move_is_played(self):
        self.play_one_move()
        self.view.header.restart_button.on_click(None)
        confirm(self.page)
        self.view.header.level_button.on_click(None)  # fresh game: no question
        self.assertIsNone(self.page.dialog)
        self.assertEqual(self.view.header.level_text.value, "MASTER")

    def test_dialog_buttons_are_blocks_like_the_rest(self):
        self.play_one_move()
        self.view.header.restart_button.on_click(None)
        buttons = dialog_buttons(self.page)
        self.assertEqual(set(buttons), {"CANCEL", "RESTART"})
        self.assertEqual(buttons["RESTART"].bgcolor, COLOR_RESTART)
        for button in buttons.values():
            self.assertIsInstance(button, ft.Container)
            self.assertEqual(button.border_radius, 6)
        self.assertEqual(
            [c for c in iter_controls(self.page.dialog) if isinstance(c, (ft.TextButton, ft.Button))], []
        )

    def test_level_dialog_button_uses_the_new_level_color(self):
        self.play_one_move()
        self.view.header.level_button.on_click(None)
        self.assertEqual(dialog_buttons(self.page)["CHANGE"].bgcolor, DIFFICULTIES[2][3])


class LanguageTests(ViewCase):
    """Every text on screen follows the chosen language."""

    def portuguese(self):
        self.view.set_language("pt")

    def header_labels(self):
        return [block.content.controls[0].value for block in self.view.header.blocks]

    def test_english_by_default(self):
        self.assertEqual(self.header_labels(), ["SCORE", "BEST", "LEVEL", "RESTART"])
        self.assertEqual(self.view.header.level_text.value, "MIDDLE")
        self.assertEqual(self.view.status_display.value, "Line up 3 or more squares of the same color.")
        self.assertEqual(self.view.game_over_button.content.value, "RESTART")

    def test_header_and_message_in_portuguese(self):
        self.portuguese()
        self.assertEqual(self.header_labels(), ["PONTOS", "RECORDE", "NÍVEL", "REINICIAR"])
        self.assertEqual(self.view.header.level_text.value, "MÉDIO")
        self.assertEqual(self.view.status_display.value, "Alinhe 3 ou mais quadrados da mesma cor.")
        self.assertEqual(self.view.game_over_button.content.value, "REINICIAR")
        self.assertTrue(self.page.updated)

    def test_tooltips_in_portuguese(self):
        self.portuguese()
        self.assertEqual(self.view.header.restart_button.tooltip, "Reiniciar")
        self.assertEqual(self.view.header.level_button.tooltip, "Mudar de nível (começa um novo jogo)")
        self.assertEqual(self.view.game_over_button.tooltip, "Reiniciar")
        tips = [b.tooltip for b in self.view.level_bar.blocks]
        self.assertEqual(tips, ["Cor inicial", "Cor inicial", "Desbloqueia com 50 pontos",
                                "Desbloqueia com 150 pontos", "Desbloqueia com 350 pontos"])

    def test_game_over_in_portuguese(self):
        self.portuguese()
        self.game.game_over = True
        self.view.refresh()
        self.assertEqual(self.view.status_display.value, "FIM DE JOGO")

    def test_new_color_message_in_portuguese(self):
        self.portuguese()
        bottom = self.game.rows - 1
        place(self.game, (0, bottom, BLUE), (1, bottom, BLUE), (7, bottom, BLUE))
        self.game.score = 48
        with next_colors(GREEN):
            move(self.view, "left")
        self.assertEqual(self.view.status_display.value, "Nova cor desbloqueada!")
        run_background_tasks(self.page)
        self.assertEqual(self.view.status_display.value, "Alinhe 3 ou mais quadrados da mesma cor.")

    def test_confirmations_in_portuguese(self):
        self.portuguese()
        with next_colors(GREEN):
            move(self.view, "left")
        self.view.header.restart_button.on_click(None)
        dialog = self.page.dialog
        self.assertEqual((dialog.title.value, dialog.content.value),
                         ("Reiniciar o jogo?", "Você vai perder o jogo atual."))
        self.assertEqual([b.content.value for b in dialog.actions], ["CANCELAR", "REINICIAR"])
        cancel(self.page)
        self.view.header.level_button.on_click(None)
        self.assertEqual(self.page.dialog.title.value, "Mudar para MESTRE?")
        self.assertEqual([b.content.value for b in self.page.dialog.actions], ["CANCELAR", "MUDAR"])

    def test_level_names_follow_the_language(self):
        self.portuguese()
        names = []
        for _ in range(3):
            self.view.header.level_button.on_click(None)
            names.append(self.view.header.level_text.value)
        self.assertEqual(names, ["MESTRE", "INICIANTE", "MÉDIO"])

    def test_switching_back_to_english(self):
        self.portuguese()
        self.view.set_language("en")
        self.assertEqual(self.header_labels(), ["SCORE", "BEST", "LEVEL", "RESTART"])

    def test_flutter_is_told_the_language_too(self):
        config = self.page.locale_configuration
        self.assertEqual([l.language_code for l in config.supported_locales], ["en", "pt"])
        self.assertEqual(config.current_locale.language_code, "en")
        self.portuguese()
        self.assertEqual(self.page.locale_configuration.current_locale.language_code, "pt")

    def test_changing_language_keeps_the_game(self):
        place(self.game, (0, 0, BLUE))
        self.game.score = 42
        self.portuguese()
        self.assertEqual((len(self.game.squares()), self.game.score), (1, 42))
        self.assertEqual(self.view.header.score_text.value, "42")

