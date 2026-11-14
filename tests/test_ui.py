import asyncio
import colorsys
import itertools
import math
from types import SimpleNamespace
from unittest.mock import call, patch

import flet as ft
import pytest

import ui
from config import (
    ANIMATION_SECONDS,
    BLUE,
    LEVEL_BLOCK_SIZE,
    CELL_SPACING,
    COLOR_BG,
    COLOR_BOARD_BG,
    COLOR_EMPTY,
    COLOR_FINAL_SCORE,
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
from tests.helpers import FakeStorage, MockPage, iter_controls, lab, lightness, media_with
from ui.widgets import create_tile

SWIPES = {"left": (-80, 5), "right": (80, -5), "up": (4, -80), "down": (-4, 80)}


def step(view):
    """Distance between two neighbouring squares on the board."""
    return view.board.cell + CELL_SPACING


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


def swipe(view, direction_or_dx, dy=None, steps=4):
    """Drag a finger across the game area (like a real touch)."""
    dx, dy = SWIPES[direction_or_dx] if dy is None else (direction_or_dx, dy)
    area = view.swipe_area.control
    area.on_pan_start(None)
    for _ in range(steps):
        area.on_pan_update(SimpleNamespace(local_delta=ft.Offset(dx / steps, dy / steps)))
    asyncio.run(area.on_pan_end(None))


def texts_on_screen(control):
    return [c.value for c in iter_controls(control) if isinstance(c, ft.Text)]


@pytest.fixture
def view(sleep):
    """The app on a fake page, with instant animations."""
    page = MockPage()
    # An empty 10x10 board (not tied to any level's size), so each test
    # sets up exactly the squares it needs.
    view = BlockFallView(page, BlockFallEngine(rows=10, cols=10, start_squares=0))
    # The constructor already calls refresh(); reset the flag so each
    # test proves its own action triggered a page update.
    page.updated = False
    return view


@pytest.fixture
def page(view):
    """The fake page the app runs on."""
    return view.page


@pytest.fixture
def game(view):
    return view.game


@pytest.fixture
def layout(view):
    return view.layout


class TestMockPage:
    def test_mock_rejects_attributes_that_ft_page_does_not_have(self):
        page = MockPage()
        for name in ("window_width", "window_height", "window_resizable"):
            with pytest.raises(AttributeError):
                setattr(page, name, 1)

    def test_mock_accepts_real_page_attributes(self):
        page = MockPage()
        page.title = "x"
        page.padding = 1
        assert (page.title, page.padding) == ("x", 1)


class TestUI:
    def test_view_builds_one_layout(self, page):
        assert len(page.controls) == 1

    def test_refresh_updates_page(self, page, view):
        view.refresh()
        assert page.updated

    def test_move_adds_exactly_one_square(self, page, view):
        move(view, "left")
        assert len(view.board.tiles) == 1
        assert page.updated

    def test_every_move_adds_one_square(self, view):
        with next_colors(BLUE, GREEN, RED, BLUE):  # never 3 alike: no match
            for presses, direction in enumerate(["left", "right", "up", "down"], start=1):
                move(view, direction)
                assert len(view.board.tiles) == presses

    def test_game_over_refresh_shows_game_over_above_the_blocks(self, view, game):
        game.game_over = True
        view.refresh()
        assert view.game_end.title.value == "GAME OVER"
        assert view.game_end.banner.visible

    def test_normal_refresh_shows_move_message(self, view):
        view.refresh()
        assert view.status_display.value == "Line up 3 or more squares of the same color."

    def test_move_refreshes_page(self, page, view):
        move(view, "left")
        assert page.updated


class TestNoBorder:
    """Blocks have no borders: rounded squares with small gaps, like 2048."""

    def test_tiles_have_no_border_and_rounded_corners(self):
        for tile in (create_tile(0), create_tile(BLUE), create_tile(RED)):
            assert tile.border is None
            assert tile.border_radius == TILE_RADIUS

    def test_board_squares_have_no_border(self, view, game):
        place(game, (0, 8, BLUE), (1, 8, GREEN), (0, 9, RED))
        view.refresh()
        assert all(t.border is None for t in view.board.tiles.values())
        assert all(s.border is None for s in view.board.slots)

    def test_squares_are_separated_by_a_small_gap(self, view, game):
        assert (LEVEL_BLOCK_SIZE, CELL_SPACING) == (30, 4)
        place(game, (0, 9, BLUE), (1, 9, GREEN), (2, 9, RED), (3, 9, BLUE))
        view.refresh()
        lefts = sorted(t.left for t in view.board.tiles.values())
        assert lefts == [0, step(view), 2 * step(view), 3 * step(view)]

    def test_ui_has_no_outline_helpers_left(self):
        assert not hasattr(ui, "outline_sides")


class TestNoNextCard:
    """The "Next" card is gone: only the board, the status and the controls."""

    def test_no_next_label_and_no_hint(self, layout):
        assert "Next:" not in texts_on_screen(layout)
        assert not any("next block" in (t or "").lower() for t in texts_on_screen(layout))

    def test_no_preview_anywhere(self, view):
        assert not hasattr(view, "preview_container")
        assert not hasattr(ui, "create_piece_preview")


class TestView:
    def test_layout_from_top_to_bottom(self, view, layout):
        # header (logo, score, best, restart), then the touch area with the
        # final score (at game over), the level blocks, the message, and the
        # grid. No arrow buttons.
        header, area, game_over_slot = layout.content.controls
        assert header is view.header.control
        assert area is view.swipe_area.control
        assert game_over_slot.content.controls == [view.help_button.control, view.game_end.button]
        final_score, levels, message, board_box = area.content.content.controls
        assert final_score is view.game_end.banner
        assert levels is view.level_bar.control
        assert message.content is view.status_display
        assert board_box.content is view.board.stack

    def test_message_is_below_the_level_blocks_and_above_the_grid(self, view):
        column = view.swipe_area.control.content.content.controls
        assert column.index(view.status_box) == column.index(view.level_bar.control) + 1
        board_box = next(c for c in column if getattr(c, "content", None) is view.board.stack)
        assert column.index(view.status_box) < column.index(board_box)

    def test_everything_from_the_color_blocks_down_is_pushed_to_the_bottom(self, view):
        # The free space goes between the logo and the color blocks (at game
        # over, the final score takes some of it, right above the blocks).
        column = view.swipe_area.control.content.content
        assert column.controls[:2] == [view.game_end.banner, view.level_bar.control]
        assert column.alignment == ft.MainAxisAlignment.END
        assert view.swipe_area.control.expand

    def test_the_only_space_at_the_bottom_is_kept_for_the_big_restart(self, view, layout):
        slot = layout.content.controls[-1]
        assert slot.height == view.game_end.button.height  # always reserved
        assert not view.game_end.button.visible  # ...even while hidden
        assert layout.content.spacing <= 10

    def test_header_stays_at_the_top_with_no_empty_space_above(self, page, view, layout):
        assert layout.content.controls[0] is view.header.control
        assert page.vertical_alignment == ft.MainAxisAlignment.START
        assert layout.content.alignment == ft.MainAxisAlignment.START
        assert getattr(page, "scroll", None) is None  # the header never scrolls away

    def test_page_is_configured(self, page):
        assert page.title == "Block Fall"
        assert page.bgcolor == COLOR_BG
        assert page.vertical_alignment == ft.MainAxisAlignment.START
        assert page.horizontal_alignment == ft.CrossAxisAlignment.CENTER
        assert (page.window.width, page.window.height) == (390, 840)
        assert (WINDOW_WIDTH, WINDOW_HEIGHT) == (390, 840)
        assert not page.window.resizable
        assert page.padding == 10

    def test_board_shows_every_empty_slot_of_the_configured_grid(self, view, game):
        rows, cols = game.rows, game.cols
        assert len(view.board.slots) == rows * cols
        positions = {(s.left, s.top) for s in view.board.slots}
        assert positions == {(c * step(view), r * step(view)) for r in range(rows) for c in range(cols)}
        assert all(s.bgcolor == COLOR_EMPTY for s in view.board.slots)
        cell = view.board.cell
        assert all((s.width, s.height) == (cell, cell) for s in view.board.slots)

    def test_board_is_a_stack_sized_for_the_grid(self, view, game):
        assert isinstance(view.board.stack, ft.Stack)
        size = game.cols * view.board.cell + (game.cols - 1) * CELL_SPACING
        assert (view.board.stack.width, view.board.stack.height) == (size, size)

    def test_board_height_leaves_room_for_the_rest(self, page, view):
        assert view.board.stack.height < page.window.height / 2

    def test_board_shows_the_engine_squares(self, view, game):
        place(game, (1, 8, BLUE), (0, 9, GREEN), (1, 9, RED), (2, 9, BLUE))
        view.refresh()
        colors = board_colors(view)
        assert colors[8][:3] == [COLOR_EMPTY, TILE_COLORS[BLUE], COLOR_EMPTY]
        assert colors[9][:3] == [TILE_COLORS[GREEN], TILE_COLORS[RED], TILE_COLORS[BLUE]]
        assert sum(c != COLOR_EMPTY for row in colors for c in row) == 4

    def test_refresh_does_not_duplicate_tiles(self, view, game):
        place(game, (0, 0, BLUE), (1, 0, GREEN))
        view.refresh()
        count = len(view.board.stack.controls)
        view.refresh()
        assert len(view.board.stack.controls) == count
        assert count == game.rows * game.cols + 2

    def test_new_square_appears_on_the_opposite_side(self, view):
        with next_position_last(RED):
            move(view, "down")
        # After moving down, the square appears on the top edge (last position).
        assert board_colors(view)[0][-1] == TILE_COLORS[RED]

    def test_refresh_shows_score_and_high_score(self, view, game):
        game.score = 120
        game.high_score = 340
        view.refresh()
        assert view.header.score_text.value == "120"
        assert view.header.best_text.value == "340"

    def test_layout_contains_score_cards(self, layout):
        texts = [c.value for c in iter_controls(layout) if isinstance(c, ft.Text)]
        for text in ("SCORE", "BEST"):
            assert text in texts

    def test_no_arrow_buttons_and_no_round_buttons(self, layout):
        buttons = [
            c for c in iter_controls(layout)
            if isinstance(c, (ft.Button, ft.IconButton, ft.TextButton, ft.FilledButton))
        ]
        assert buttons == []
        assert not hasattr(ui, "MOVE_BUTTONS")

    def test_swipe_up_and_down_end_to_end(self, view, game):
        place(game, (0, 9, BLUE), (1, 8, GREEN))
        with next_position_last(RED):
            swipe(view, "up")
        colors = board_colors(view)
        assert colors[0][:2] == [TILE_COLORS[BLUE], TILE_COLORS[GREEN]]
        # Squares went up, so the new one appeared on the bottom edge.
        assert colors[-1][-1] == TILE_COLORS[RED]
        with next_position_last(GREEN):
            swipe(view, "down")
        colors = board_colors(view)
        assert colors[-1][:2] == [TILE_COLORS[BLUE], TILE_COLORS[GREEN]]
        assert colors[-1][-1] == TILE_COLORS[RED]
        # Squares went down, so the new one appeared on the top edge.
        assert colors[0][-1] == TILE_COLORS[GREEN]

    def test_swipe_left_end_to_end(self, page, view, game):
        bottom = game.rows - 1
        place(game, (4, bottom, BLUE), (6, bottom, GREEN))
        with next_position_last(RED):
            swipe(view, "left")
        row = board_colors(view)[bottom]
        # Slid left; the new red square came in on the right edge (last row).
        assert row == ([TILE_COLORS[BLUE], TILE_COLORS[GREEN]]
                       + [COLOR_EMPTY] * (game.cols - 3) + [TILE_COLORS[RED]])
        assert page.updated

    def test_three_in_a_line_disappear_and_score_end_to_end(self, view, game):
        bottom = game.rows - 1
        place(game, (0, bottom, BLUE), (1, bottom, BLUE), (7, bottom, BLUE))
        with next_colors(GREEN):
            swipe(view, "left")
        assert board_colors(view)[bottom][:3] == [COLOR_EMPTY] * 3
        assert view.header.score_text.value == "3"

    def test_four_in_a_line_score_five(self, view, game):
        bottom = game.rows - 1
        place(game, *[(c, bottom, RED) for c in (0, 2, 5, 9)])
        with next_colors(GREEN):
            swipe(view, "left")
        assert view.header.score_text.value == "5"

    def test_move_handler_forwards_direction_to_engine(self, view, game):
        with patch.object(game, "play_move") as play_move:
            move(view, "right")
        play_move.assert_called_once_with("right")


def snapshot(view):
    return {sid: (t.left, t.top, t.bgcolor, t.scale) for sid, t in view.board.tiles.items()}


class TestAnimation:
    """Squares slide to their new place (like 2048), new squares pop in."""

    @pytest.fixture(autouse=True)
    def sent(self, page, view):
        """What the player saw at each page.update()."""
        sent = []
        page.update = lambda: sent.append(snapshot(view))
        return sent

    def test_every_square_tile_animates_its_position(self, view, game):
        place(game, (0, 0, BLUE), (1, 0, GREEN))
        view.refresh()
        for tile in view.board.tiles.values():
            assert tile.animate_position.duration == int(ANIMATION_SECONDS * 1000)
            assert tile.animate_scale.duration == int(ANIMATION_SECONDS * 1000)

    def test_a_moving_square_keeps_the_same_tile(self, view, game):
        place(game, (5, 8, BLUE), (6, 9, GREEN))
        view.refresh()
        tiles_before = dict(view.board.tiles)
        with next_colors(RED):
            move(view, "left")
        for square_id, tile in tiles_before.items():
            assert view.board.tiles[square_id] is tile  # same control: Flet animates it
        assert sorted(t.left for t in tiles_before.values()) == [0, 0]

    def test_slide_is_shown_then_given_time_to_finish(self, view, game, sleep, sent):
        place(game, (5, 8, BLUE), (6, 9, GREEN))
        view.refresh()
        sent.clear()
        seen_during_pause = []

        async def pause(seconds):
            seen_during_pause.append((seconds, sent[-1]))

        sleep.side_effect = pause
        with next_colors(RED):
            move(view, "left")
        seconds, on_screen = seen_during_pause[0]
        assert seconds == ANIMATION_SECONDS
        assert sorted(v[0] for v in on_screen.values()) == [0, 0]

    def test_no_slide_pause_when_nothing_moves(self, view, game, sleep):
        place(game, (0, 8, BLUE))
        view.refresh()
        with next_colors(RED):
            move(view, "left")
        assert call(ANIMATION_SECONDS) not in sleep.await_args_list

    def test_new_square_pops_in(self, view, sleep, sent):
        move(view, "left")
        (new_id,) = view.board.tiles
        first_seen = next(s for s in sent if new_id in s)
        assert first_seen[new_id][3] == 0  # tiny
        assert sent[-1][new_id][3] == 1  # full size
        assert call(POP_START_SECONDS) in sleep.await_args_list

    def test_refresh_shows_existing_squares_at_full_size(self, view, game):
        place(game, (0, 0, BLUE))
        view.refresh()
        assert all(t.scale == 1 for t in view.board.tiles.values())

    def test_removed_squares_leave_the_board(self, view, game):
        place(game, (0, 9, BLUE), (1, 9, BLUE), (7, 9, BLUE), (5, 3, RED))
        view.refresh()
        with next_colors(GREEN):
            move(view, "left")
        assert len(view.board.tiles) == 4 - 3 + 1
        assert len(view.board.stack.controls) == game.rows * game.cols + 2

    def test_last_frame_without_a_match_needs_no_pause(self, view, sleep):
        move(view, "left")  # empty board: only a spawn frame
        assert sleep.await_args_list == [call(POP_START_SECONDS)]

    def test_pause_order_for_slide_match_and_spawn(self, view, game, sleep):
        place(game, (0, 9, BLUE), (1, 9, BLUE), (7, 9, BLUE))
        view.refresh()
        with next_colors(GREEN):
            move(view, "left")
        assert sleep.await_args_list == [call(ANIMATION_SECONDS), call(GOLD_FLASH_SECONDS), call(POP_START_SECONDS)]

    def test_animation_is_quick(self):
        assert 0 < ANIMATION_SECONDS <= 0.1
        assert 0 < POP_START_SECONDS < ANIMATION_SECONDS


class TestGoldFlash:
    """Matched squares turn gold, stay visible for a moment, then disappear."""

    @pytest.fixture(autouse=True)
    def bottom(self, game, view):
        """Three blues on the bottom row, ready to line up; returns that row."""
        bottom = game.rows - 1
        place(game, (0, bottom, BLUE), (1, bottom, BLUE), (7, bottom, BLUE), (7, 5, GREEN))
        view.refresh()
        return bottom

    def test_matched_squares_turn_gold_then_disappear(self, page, view, sleep, bottom):
        frames = []
        sent_to_screen = []
        page.update = lambda: sent_to_screen.append(board_colors(view))

        async def pause(seconds):
            if seconds == GOLD_FLASH_SECONDS:
                # During the pause, the screen must already show the gold frame.
                frames.append((board_colors(view), sent_to_screen[-1]))

        sleep.side_effect = pause
        with next_colors(RED):
            move(view, "left")
        ((flash, on_screen),) = frames
        assert on_screen == flash
        assert flash[bottom][:4] == [COLOR_GOLD] * 3 + [COLOR_EMPTY]
        assert flash[5][0] == TILE_COLORS[GREEN]  # other squares keep their color
        after = board_colors(view)
        assert after[bottom][:3] == [COLOR_EMPTY] * 3
        assert COLOR_GOLD not in [c for row in after for c in row]
        assert view.header.score_text.value == "3"

    def test_no_gold_flash_without_a_match(self, view, sleep):
        # Moving up puts the blues in different rows: no line.
        with next_colors(RED):
            move(view, "up")
        assert view.header.score_text.value == "0"
        assert call(GOLD_FLASH_SECONDS) not in sleep.await_args_list

    def test_each_match_in_a_move_flashes_in_order(self, view, game, sleep):
        # Square 2 exists in both frames (a real move never brings one back).
        first = Frame("match", {1: (0, 0, BLUE), 2: (9, 9, RED)}, frozenset({1}))
        second = Frame("match", {2: (9, 9, RED)}, frozenset({2}))
        seen = []

        async def pause(_seconds):
            seen.append(board_colors(view))

        sleep.side_effect = pause

        def fake_play_move(direction):
            game.frames = [first, second]
            return True

        with patch.object(game, "play_move", side_effect=fake_play_move):
            move(view, "up")
        assert len(seen) == 2
        assert (seen[0][0][0], seen[0][9][9]) == (COLOR_GOLD, TILE_COLORS[RED])
        assert (seen[1][0][0], seen[1][9][9]) == (COLOR_EMPTY, COLOR_GOLD)

    def test_a_swipe_during_the_gold_flash_is_not_lost(self, view, game, sleep):
        async def swipe_again(seconds):
            if seconds == GOLD_FLASH_SECONDS:
                await view._handle_move("up")

        sleep.side_effect = swipe_again
        with patch.object(game, "play_move", wraps=game.play_move) as play_move:
            with next_colors(RED, RED):
                move(view, "left")
        assert [c.args[0] for c in play_move.call_args_list] == ["left", "up"]

    def test_a_waiting_swipe_skips_the_rest_of_the_animation(self, view, sleep):
        pauses = []

        async def pause(seconds):
            pauses.append(seconds)
            if len(pauses) == 1:  # during the slide, the player swipes again
                await view._handle_move("up")

        sleep.side_effect = pause
        with next_colors(RED, RED):
            move(view, "left")
        # Move 1: only its slide pause (gold + pop skipped).
        # Move 2 ("up" also slides): its slide pause and its pop.
        assert pauses == [ANIMATION_SECONDS, ANIMATION_SECONDS, POP_START_SECONDS]
        assert view.header.score_text.value == "3"  # move 1 still scored

    def test_the_latest_of_several_waiting_swipes_wins(self, view, game, sleep):
        fired = []

        async def many_swipes(seconds):
            if seconds == ANIMATION_SECONDS and not fired:
                fired.append(True)
                for direction in ("up", "right", "down"):
                    await view._handle_move(direction)

        sleep.side_effect = many_swipes
        with patch.object(game, "play_move", wraps=game.play_move) as play_move:
            with next_colors(RED, RED):
                move(view, "left")
        assert [c.args[0] for c in play_move.call_args_list] == ["left", "down"]

    def test_without_a_waiting_swipe_the_flash_plays_in_full(self, view, sleep):
        with next_colors(RED):
            move(view, "left")
        assert call(GOLD_FLASH_SECONDS) in sleep.await_args_list

    def test_handler_is_usable_again_after_the_animation(self, view):
        with next_colors(RED, GREEN):
            move(view, "left")
            assert not view.turns.busy
            tiles = len(view.board.tiles)
            move(view, "up")
        assert len(view.board.tiles) == tiles + 1

    def test_flash_pause_is_short(self):
        assert 0 < GOLD_FLASH_SECONDS <= 0.15

    def test_a_scoring_move_settles_in_under_0_3_seconds(self, view, sleep):
        with next_colors(RED):
            move(view, "left")  # slide, gold, new square
        assert sum(c.args[0] for c in sleep.await_args_list) < 0.3


class TestMain:
    @pytest.fixture
    def storage(self, monkeypatch):
        """The device's storage main() opens (ft.SharedPreferences)."""
        storage = FakeStorage()
        monkeypatch.setattr(ft, "SharedPreferences", lambda: storage)
        return storage

    @pytest.fixture
    def start(self, sleep, storage):
        """Start the app the way Flet does, on a fake page."""
        def start(**page_options):
            page = MockPage(**page_options)
            assert asyncio.run(ui.main(page)) is None
            return page

        return start

    def test_main_shows_the_best_saved_on_the_device(self, start, storage):
        storage.values = {"block_fall.best.middle": 95, "block_fall.best.master": 40}
        page = start()
        assert "95" in texts_on_screen(page.controls[0])  # MIDDLE, the first level shown

    def test_main_saves_a_new_best_on_the_device(self, start, storage):
        page = start()
        view = page.on_resize.__self__  # the view main() built
        view.game = BlockFallEngine(rows=5, cols=5, start_squares=0)
        place(view.game, (0, 4, BLUE), (1, 4, BLUE), (3, 4, BLUE))
        with next_colors(GREEN):
            move(view, "left")  # a line of 3: a new best of 3
        run_background_tasks(page)
        assert storage.values == {"block_fall.best.middle": 3}

    def test_a_new_player_first_sees_how_to_play(self, start, storage):
        page = start()
        assert page.dialog.title.value == "Swipe to move"
        finish_tutorial(page)
        run_background_tasks(page)
        assert storage.values["block_fall.tutorial_seen"] is True

    def test_a_player_who_has_seen_it_goes_straight_to_the_game(self, start, storage):
        storage.values = {"block_fall.tutorial_seen": True}
        page = start()
        assert getattr(page, "dialog", None) is None

    def test_without_a_flet_session_no_best_is_saved_and_the_game_goes_on(self, sleep):
        page = MockPage()  # the real ft.SharedPreferences raises with no Flet session
        asyncio.run(ui.main(page))
        view = page.on_resize.__self__
        assert view.best_scores == {0: 0, 1: 0, 2: 0}
        assert view.header.best_text.value == "0"

    def test_main_builds_the_view_on_the_page(self, start):
        page = start()
        assert len(page.controls) == 1
        assert page.title == "Block Fall"
        assert page.updated

    def test_a_portuguese_device_starts_in_portuguese(self, start):
        page = start(device_languages=("pt-BR", "en-US"))
        texts = [c.value for c in iter_controls(page.controls[0]) if isinstance(c, ft.Text)]
        assert "Alinhe 3 ou mais quadrados da mesma cor." in texts
        assert "PONTOS" in texts

    def test_any_other_device_starts_in_english(self, start):
        page = start(device_languages=("es-ES",))
        texts = [c.value for c in iter_controls(page.controls[0]) if isinstance(c, ft.Text)]
        assert "Line up 3 or more squares of the same color." in texts

    @pytest.mark.parametrize("answer", [None, RuntimeError("not available here")], ids=["no-info", "error"])
    def test_no_device_info_means_english(self, start, answer):
        page = start(device_languages=answer)
        texts = [c.value for c in iter_controls(page.controls[0]) if isinstance(c, ft.Text)]
        assert "SCORE" in texts

    def test_changing_the_device_language_switches_the_app(self, start):
        page = start()
        page.on_locale_change(SimpleNamespace(locales=[ft.Locale("pt", "BR")]))
        texts = [c.value for c in iter_controls(page.controls[0]) if isinstance(c, ft.Text)]
        assert "RECORDE" in texts
        page.on_locale_change(SimpleNamespace(locales=[ft.Locale("en", "GB")]))
        texts = [c.value for c in iter_controls(page.controls[0]) if isinstance(c, ft.Text)]
        assert "BEST" in texts


class TestOrientation:
    def test_window_is_portrait(self):
        page = MockPage()
        BlockFallView(page)
        assert page.window.height > page.window.width
        assert not page.window.resizable

    @pytest.mark.parametrize("platform", [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS], ids=str)
    def test_mobile_app_is_locked_to_portrait(self, platform):
        page = MockPage(platform=platform)
        BlockFallView(page)
        assert len(page.tasks) == 1
        handler, args = page.tasks[0]
        assert handler == page.set_allowed_device_orientations
        asyncio.run(handler(*args))
        assert page.orientations == [ft.DeviceOrientation.PORTRAIT_UP]

    # Flet raises FletUnsupportedPlatformException on non-mobile platforms.
    @pytest.mark.parametrize(
        "platform", [ft.PagePlatform.WINDOWS, ft.PagePlatform.MACOS, ft.PagePlatform.LINUX, None], ids=str,
    )
    def test_orientation_lock_is_not_requested_off_mobile(self, platform):
        page = MockPage(platform=platform)
        BlockFallView(page)
        assert page.tasks == []


class TestPastelTheme:
    """The whole app uses soft pastel colors."""

    SQUARES = [TILE_COLORS[c] for c in SQUARE_COLORS]

    def test_square_colors_are_pastel(self):
        for color in self.SQUARES:
            assert 0.7 <= lightness(color) <= 0.9, color

    def test_square_colors_are_easy_to_tell_apart(self):
        closest = min(math.dist(lab(a), lab(b)) for a, b in itertools.combinations(self.SQUARES, 2))
        assert closest >= 25

    def test_gold_flash_and_empty_slots_stand_out_from_every_square(self):
        for other in (COLOR_GOLD, COLOR_EMPTY):
            closest = min(math.dist(lab(other), lab(c)) for c in self.SQUARES)
            assert closest >= 25, other

    def test_light_background_with_dark_readable_text(self, page, layout):
        for background in (COLOR_BG, COLOR_BOARD_BG, COLOR_EMPTY):
            assert lightness(background) > 0.85, background
        assert lightness(COLOR_TEXT) < 0.4
        assert page.bgcolor == COLOR_BG
        texts = [c for c in iter_controls(layout) if isinstance(c, ft.Text)]
        colors = [t.color for t in texts]
        assert all(lightness(color) < 0.6 for color in colors), colors

    def test_header_blocks_are_pastel_too(self, view):
        for block in view.header.blocks:
            assert lightness(block.bgcolor) > 0.7


def level_colors(view):
    return [block.bgcolor for block in view.level_bar.control.controls]


class TestLevelBar:
    """5 blocks above the grid, one per color: black until unlocked."""

    def test_five_blocks_in_color_order(self, view):
        assert len(view.level_bar.control.controls) == 5
        assert view.level_bar.blocks == view.level_bar.control.controls

    def test_a_new_game_shows_two_colors_and_three_black_blocks(self, view):
        assert level_colors(view) == [TILE_COLORS[BLUE], TILE_COLORS[GREEN]] + [COLOR_LOCKED] * 3

    def test_locked_blocks_are_gray_with_a_lock(self, view):
        for block in view.level_bar.blocks[2:]:
            assert block.bgcolor == COLOR_LOCKED
            assert isinstance(block.content, ft.Icon)
            assert block.content.icon == ft.Icons.LOCK
            assert block.content.color == COLOR_LOCK_ICON
            assert block.alignment == ft.Alignment.CENTER  # lock in the middle
        for block in view.level_bar.blocks[:2]:
            assert block.content is None

    def test_locked_gray_cannot_be_mistaken_for_a_color(self):
        assert COLOR_LOCKED != "#000000"
        r, g, b = (int(COLOR_LOCKED[i:i + 2], 16) / 255 for i in (1, 3, 5))
        assert colorsys.rgb_to_hls(r, g, b)[2] < 0.15  # gray: almost no saturation
        for color in SQUARE_COLORS:
            assert math.dist(lab(COLOR_LOCKED), lab(TILE_COLORS[color])) >= 25
        assert math.dist(lab(COLOR_LOCKED), lab(COLOR_BG)) >= 20
        assert math.dist(lab(COLOR_LOCKED), lab(COLOR_LOCK_ICON)) >= 25

    def test_lock_disappears_when_the_color_unlocks(self, view, game):
        game.score = 50
        view.refresh()
        assert view.level_bar.blocks[2].content is None
        assert isinstance(view.level_bar.blocks[3].content, ft.Icon)

    def test_blocks_light_up_as_the_score_grows(self, view, game):
        expected = {
            49: 2, 50: 3, 99: 3, 100: 4, 149: 4, 150: 5,
        }
        for score, unlocked in expected.items():
            game.score = score
            view.refresh()
            expected_colors = [TILE_COLORS[c] for c in SQUARE_COLORS[:unlocked]] + [COLOR_LOCKED] * (5 - unlocked)
            assert level_colors(view) == expected_colors, score

    def test_each_block_tells_when_it_unlocks(self, view):
        tips = [block.tooltip for block in view.level_bar.blocks]
        assert tips[:2] == ["Starting color", "Starting color"]
        assert tips[2:] == [f"Unlocks at {UNLOCK_SCORES[i]} points" for i in (2, 3, 4)]

    def test_scoring_past_50_unlocks_the_third_block_end_to_end(self, page, view, game):
        bottom = game.rows - 1
        place(game, (0, bottom, BLUE), (1, bottom, BLUE), (7, bottom, BLUE))
        game.score = 48
        view.refresh()
        assert level_colors(view)[2] == COLOR_LOCKED
        with next_colors(GREEN):
            swipe(view, "left")
        assert view.header.score_text.value == "51"
        assert level_colors(view)[2] == COLOR_GOLD  # unlocking...
        run_background_tasks(page)
        assert level_colors(view)[2] == TILE_COLORS[RED]

    def test_blocks_are_squares_like_the_board(self, view):
        for block in view.level_bar.blocks:
            assert (block.width, block.height) == (LEVEL_BLOCK_SIZE, LEVEL_BLOCK_SIZE)
            assert block.border_radius == TILE_RADIUS


class TestStart:
    def test_a_new_game_shows_squares_on_the_grid(self, sleep):
        view = BlockFallView(MockPage())
        assert len(view.board.tiles) == round(GRID_ROWS * GRID_COLS * START_FILL)
        colors = {tile.bgcolor for tile in view.board.tiles.values()}
        assert colors <= {TILE_COLORS[BLUE], TILE_COLORS[GREEN]}
        assert all(tile.scale == 1 for tile in view.board.tiles.values())


def needed_width(view, page):
    """Screen width the board really takes: board + all paddings around it."""
    layout = view.layout
    board_box = next(c for c in iter_controls(layout) if getattr(c, "content", None) is view.board.stack)
    return view.board.stack.width + 2 * (page.padding + layout.padding + board_box.padding)


SCREEN_WIDTHS = (320, 360, 374, 375, 390, 412, 430, 800)


@pytest.fixture
def make_view(sleep):
    """A page `width` wide and the app on it (an empty MIDDLE game by default)."""
    def make_view(width, game=None):
        page = MockPage(width=width)
        view = BlockFallView(page, game or BlockFallEngine(start_squares=0))
        return page, view

    return make_view


class TestBoardFit:
    """The whole grid is visible on every screen (bug: right column cut in half)."""

    @pytest.mark.parametrize("width", SCREEN_WIDTHS)
    def test_board_fits_the_real_page_width(self, make_view, width):
        page, view = make_view(width)
        assert needed_width(view, page) <= width

    def test_regression_right_column_fully_visible_on_a_360_phone(self, make_view):
        page, view = make_view(360)
        for row in range(GRID_ROWS):
            view.game.place_square(GRID_COLS - 1, row, BLUE)
        view.refresh()
        for tile in view.board.tiles.values():
            assert tile.left + tile.width <= view.board.stack.width
        assert needed_width(view, page) <= 360

    def test_regression_fits_a_windows_window_of_390_with_its_frame(self, make_view):
        # window.width (390) includes the frame; the page only gets ~374.
        page, view = make_view(374)
        assert page.window.width == 390
        assert needed_width(view, page) <= 374

    @pytest.mark.parametrize("width", SCREEN_WIDTHS)
    def test_grid_uses_100_percent_of_the_width(self, make_view, width):
        page, view = make_view(width)
        assert needed_width(view, page) == pytest.approx(width)

    @pytest.mark.parametrize("width", (360, 412))
    @pytest.mark.parametrize("rows, cols", ((10, 10), (8, 12), (12, 8), (5, 5), (6, 10), (15, 7)))
    def test_any_grid_size_uses_100_percent_of_the_width(self, make_view, rows, cols, width):
        page, view = make_view(width, BlockFallEngine(rows=rows, cols=cols, start_squares=0))
        assert len(view.board.slots) == rows * cols
        assert needed_width(view, page) == pytest.approx(width)
        last = max(view.board.slots, key=lambda s: (s.left, s.top))
        assert last.left + last.width == pytest.approx(view.board.stack.width)
        assert last.top + last.height == pytest.approx(view.board.stack.height)
        assert view.board.stack.height == pytest.approx(rows * view.board.cell + (rows - 1) * CELL_SPACING)

    def test_squares_on_a_non_square_grid_land_in_the_right_place(self, make_view):
        page, view = make_view(360, BlockFallEngine(rows=6, cols=12, start_squares=0))
        view.game.place_square(11, 5, RED)
        view.refresh()
        (tile,) = view.board.tiles.values()
        assert tile.left + tile.width == pytest.approx(view.board.stack.width)
        assert tile.top + tile.height == pytest.approx(view.board.stack.height)

    def test_page_does_not_scroll_so_swipes_always_play(self, make_view):
        page, view = make_view(360, BlockFallEngine(rows=30, cols=10, start_squares=0))
        assert getattr(page, "scroll", None) is None

    def test_every_slot_and_square_uses_the_fitted_size(self, make_view):
        page, view = make_view(320)
        view.game.place_square(3, 4, GREEN)
        view.refresh()
        assert view.board.stack.width == GRID_COLS * view.board.cell + (GRID_COLS - 1) * CELL_SPACING
        for control in view.board.slots + list(view.board.tiles.values()):
            assert (control.width, control.height) == (view.board.cell, view.board.cell)
        (tile,) = view.board.tiles.values()
        assert (tile.left, tile.top) == (3 * step(view), 4 * step(view))

    def test_unknown_page_width_uses_a_small_safe_size(self, make_view):
        page, view = make_view(None)
        assert needed_width(view, page) == pytest.approx(320)

    def test_board_adapts_when_the_screen_size_changes(self, make_view):
        page, view = make_view(412)
        view.game.place_square(GRID_COLS - 1, 0, RED)
        view.refresh()
        assert page.on_resize == view._handle_resize
        page.width = 330
        page.updated = False
        view._handle_resize(type("ResizeEvent", (), {"width": 330, "height": 700})())
        assert needed_width(view, page) == pytest.approx(330)
        (tile,) = view.board.tiles.values()
        assert tile.left == (GRID_COLS - 1) * (view.board.cell + CELL_SPACING)
        assert tile.width == view.board.cell
        # The empty slots underneath follow too, and all stay inside the board.
        for index, slot in enumerate(view.board.slots):
            assert (slot.width, slot.left, slot.top) == (
                view.board.cell, index % GRID_COLS * step(view), index // GRID_COLS * step(view),
            )
            assert slot.left + slot.width <= view.board.stack.width + 1e-9
        assert page.updated

    def test_layout_still_fits_the_screen_height(self, make_view):
        page, view = make_view(360)
        assert view.board.stack.height < 640 / 2


class TestLogo:
    """A logo replaces the plain "Block Fall" title."""

    def test_logo_is_in_the_header_instead_of_a_plain_title(self, page, view):
        header = view.header.control
        assert header.controls[0].content is view.header.logo
        plain = [c.value for c in iter_controls(header) if isinstance(c, ft.Text) and c.value]
        assert "Block Fall" not in plain
        assert page.title == "Block Fall"  # still the window / app name


def tap_restart(view):
    view.header.restart_button.on_click(None)


class TestRestart:
    """A button to start a new game."""

    def test_restart_is_a_blue_block_below_best(self, view):
        score, best, level, restart = view.header.blocks
        assert restart is view.header.restart_button
        top_row, bottom_row = view.header.control.controls[1].controls
        assert top_row.controls == [score, best]
        assert bottom_row.controls == [level, restart]  # restart under BEST
        assert (restart.width, restart.height, restart.border_radius) == (best.width, best.height, best.border_radius)
        assert restart.bgcolor == COLOR_RESTART
        assert isinstance(restart, ft.Container)
        assert restart.tooltip == "Restart"

    def test_restart_color_is_blue(self):
        r, g, b = (int(COLOR_RESTART[i:i + 2], 16) / 255 for i in (1, 3, 5))
        hue = colorsys.rgb_to_hls(r, g, b)[0] * 360
        assert 190 <= hue <= 240, hue

    def test_restart_block_has_a_label_like_the_others(self, view):
        texts = [c.value for c in iter_controls(view.header.restart_button) if isinstance(c, ft.Text)]
        icons = [c.icon for c in iter_controls(view.header.restart_button) if isinstance(c, ft.Icon)]
        assert (texts, icons) == (["RESTART"], [ft.Icons.RESTART_ALT])

    def test_restart_starts_a_new_game_and_keeps_the_best_score(self, page, view, game):
        place(game, (0, 0, BLUE), (1, 0, GREEN))
        game.score = game.high_score = 200
        game.game_over = True
        view.refresh()
        old_tiles = set(view.board.tiles)
        game.start_squares = 10
        page.updated = False
        tap_restart(view)
        assert (game.score, game.high_score, game.game_over) == (0, 200, False)
        assert view.header.score_text.value == "0"
        assert view.header.best_text.value == "200"
        assert len(view.board.tiles) == 10
        assert old_tiles.isdisjoint(view.board.tiles)
        assert [b.bgcolor for b in view.level_bar.blocks[2:]] == [COLOR_LOCKED] * 3
        assert view.status_display.value == "Line up 3 or more squares of the same color."
        assert page.updated

    def test_message_box_has_a_fixed_height_so_nothing_jumps(self, view):
        assert view.status_display.max_lines == 2
        assert view.status_box.content is view.status_display
        assert view.status_box.height == 40

    def test_the_message_under_the_blocks_stays_the_same_at_game_over(self, view, game):
        before = (view.status_display.value, view.status_box.visible)
        game.game_over = True
        view.refresh()
        assert (view.status_display.value, view.status_box.visible) == before
        assert view.status_display.value == "Line up 3 or more squares of the same color."

    def test_restart_during_an_animation_happens_right_after_it(self, page, view, game, sleep):
        place(game, (0, 0, BLUE))
        squares_during = []

        async def restart_during_animation(_seconds):
            if not squares_during:
                tap_restart(view)  # a move is being played: asks first
                confirm(page)
                squares_during.append(len(game.squares()))

        sleep.side_effect = restart_during_animation
        with next_colors(GREEN):
            move(view, "down")
        assert all(n >= 1 for n in squares_during)  # not reset mid-animation
        assert game.squares() == {}  # ...but right after (new empty game)
        assert view.board.tiles == {}
        assert view.turns.pending is None


def run_background_tasks(page):
    """Run what the app handed to page.run_task (Flet runs it in the background)."""
    while page.tasks:
        handler, args = page.tasks.pop(0)
        asyncio.run(handler(*args))


class TestUnlockFlash:
    """A newly unlocked level turns gold, then shows its color, in the
    background: it never holds up the game."""

    @pytest.fixture(autouse=True)
    def seen(self, page, view, game, third):
        """The 3rd level block as sent to the screen, ready to unlock."""
        bottom = game.rows - 1
        place(game, (0, bottom, BLUE), (1, bottom, BLUE), (7, bottom, BLUE))
        game.score = 48  # the line of 3 brings it to 51: the 3rd color unlocks
        view.refresh()
        seen = []
        page.update = lambda: seen.append((third.bgcolor, third.content is not None, view.status_display.value))
        return seen

    @pytest.fixture
    def third(self, view):
        return view.level_bar.blocks[2]

    def test_locked_then_gold_then_its_color(self, page, view, seen):
        with next_colors(GREEN):
            move(view, "left")
        run_background_tasks(page)
        colors = [bg for bg, _, _ in seen]
        assert colors[0] == COLOR_LOCKED
        assert COLOR_GOLD in colors
        assert colors[-1] == TILE_COLORS[RED]
        first_gold = colors.index(COLOR_GOLD)
        assert TILE_COLORS[RED] not in colors[:first_gold]  # gold comes first

    def test_the_move_does_not_wait_for_the_flash(self, page, view, sleep, third):
        with next_colors(GREEN):
            move(view, "left")
        # Only the move's own pauses (slide, gold, pop): no extra wait for the level.
        assert sleep.await_args_list == [call(ANIMATION_SECONDS), call(GOLD_FLASH_SECONDS), call(POP_START_SECONDS)]
        assert not view.turns.busy  # the next swipe can play at once
        # ...while the level block is still gold, with the message:
        assert third.bgcolor == COLOR_GOLD
        assert view.status_display.value == "New color unlocked!"
        assert len(page.tasks) == 1  # the flash ends in the background

    def test_flash_ends_with_its_color_and_the_normal_message(self, page, view, sleep, seen, third):
        with next_colors(GREEN):
            move(view, "left")
        during = []

        async def pause(seconds):
            during.append((seconds, third.bgcolor))

        sleep.side_effect = pause
        run_background_tasks(page)
        assert during == [(UNLOCK_FLASH_SECONDS, COLOR_GOLD)]
        assert third.bgcolor == TILE_COLORS[RED]
        assert third.content is None
        assert view.status_display.value == "Line up 3 or more squares of the same color."
        assert seen[-1][0] == TILE_COLORS[RED]  # sent to the screen

    def test_the_flash_ending_does_not_touch_the_grid(self, page, view):
        with next_colors(GREEN):
            move(view, "left")
        before = {i: (t.left, t.top, t.bgcolor, t.scale) for i, t in view.board.tiles.items()}
        run_background_tasks(page)
        after = {i: (t.left, t.top, t.bgcolor, t.scale) for i, t in view.board.tiles.items()}
        assert after == before  # a move animating meanwhile is not disturbed

    def test_flash_ending_during_the_next_move_leaves_its_slide_alone(self, page, view, game, sleep):
        with next_colors(GREEN):
            move(view, "left")  # unlocks: the flash will end in the background
        (flash_end, args), = page.tasks
        page.tasks.clear()
        seen = []

        async def pause(seconds):
            if seconds == ANIMATION_SECONDS and not seen:  # the next move is sliding
                sleep.side_effect = None
                await flash_end(*args)  # ...when the flash ends
                seen.append({i: (t.left, t.top) for i, t in view.board.tiles.items()})

        sleep.side_effect = pause
        with next_colors(RED):
            move(view, "down")
        slide = game.frames[0]
        assert slide.kind == "slide"
        step = view.board.cell + CELL_SPACING
        # Mid-slide, the grid shows the slide step (not the end of the move).
        assert seen[0] == {i: (c * step, r * step) for i, (c, r, _) in slide.squares.items()}

    def test_flash_ending_after_game_over_shows_the_normal_message(self, page, view, game):
        with next_colors(GREEN):
            move(view, "left")
        game.game_over = True
        run_background_tasks(page)
        assert view.status_display.value == "Line up 3 or more squares of the same color."

    def test_no_unlock_flash_without_a_new_level(self, page, view, game, seen):
        game.score = 0
        view.refresh()
        with next_colors(GREEN):
            move(view, "left")
        assert page.tasks == []
        assert COLOR_GOLD not in [bg for bg, _, _ in seen]

    def test_two_levels_at_once_both_flash(self, page, view, game):
        def jump(direction):
            game.score = 110  # past 50 and 100
            game.frames = []
            return True

        game.score = 0
        view.refresh()
        with patch.object(game, "play_move", side_effect=jump):
            move(view, "left")
        assert [b.bgcolor for b in view.level_bar.blocks][2:] == [COLOR_GOLD, COLOR_GOLD, COLOR_LOCKED]
        run_background_tasks(page)
        assert [b.bgcolor for b in view.level_bar.blocks][2:4] == [TILE_COLORS[RED], TILE_COLORS[PEACH]]

    def test_unlock_flash_is_as_fast_as_the_gold_in_the_grid(self):
        assert UNLOCK_FLASH_SECONDS == GOLD_FLASH_SECONDS


def screen_height(view):
    """Height the whole screen needs: paddings, header, what is shown below it."""
    page = view.page
    layout = view.layout.content
    header_h = 2 * view.header.blocks[0].height + view.header.control.controls[1].spacing
    body = view.swipe_area.control.content.content
    heights = {
        id(view.game_end.banner): view.game_end.banner.height,
        id(view.level_bar.control): view.level_bar.blocks[0].height,
        id(view.status_box): view.status_box.height,
        id(view.board.frame): view.board.stack.height + 2 * view.board.frame.padding,
    }
    shown = [heights[id(c)] for c in body.controls if c.visible is not False]
    body_h = sum(shown) + (len(shown) - 1) * body.spacing
    slot_h = layout.controls[-1].height
    return 2 * (page.padding + view.layout.padding) + header_h + body_h + slot_h + 2 * layout.spacing


class TestHeader:
    """Logo on the left; SCORE and BEST, with LEVEL and RESTART below them."""

    def test_header_holds_the_logo_and_two_rows_of_blocks(self, view):
        logo_holder, blocks = view.header.control.controls
        assert logo_holder.content is view.header.logo
        rows = [row.controls for row in blocks.controls]
        assert rows == [view.header.blocks[:2], view.header.blocks[2:]]

    def test_all_header_blocks_have_the_same_size(self, view):
        sizes = {(b.width, b.height) for b in view.header.blocks}
        assert len(sizes) == 1

    def test_header_blocks_are_large(self, view):
        # Wider than the first 64 x 50 blocks (see the tests below), taller, and their texts too.
        block = view.header.blocks[0]
        assert block.width > 64
        assert block.height == 56
        label, value = block.content.controls
        assert label.size == 11
        assert value.size == 22
        assert view.header.level_text.size == 12
        icon = view.header.restart_button.content.controls[1]
        assert icon.size == 26

    @pytest.mark.parametrize("game_over", [False, True], ids=["playing", "game-over"])
    @pytest.mark.parametrize("width, height", [(360, 640), (375, 667), (390, 844), (412, 915), (800, 1280)])
    def test_everything_fits_the_screen(self, sleep, width, height, game_over):
        page = MockPage(width=width, height=height)
        view = BlockFallView(page)  # the real default game
        view.game.game_over = game_over
        view.refresh()
        assert screen_height(view) <= height

    def test_the_app_stays_clear_of_the_phone_s_status_bar_and_home_indicator(self, page, view):
        (safe_area,) = page.controls
        assert isinstance(safe_area, ft.SafeArea)
        assert safe_area.content is view.layout
        assert (safe_area.avoid_intrusions_top, safe_area.avoid_intrusions_bottom) == (True, True)
        assert (safe_area.avoid_intrusions_left, safe_area.avoid_intrusions_right) == (True, True)
        assert safe_area.expand

    @pytest.mark.parametrize("game_over", [False, True], ids=["playing", "game-over"])
    def test_everything_fits_between_the_status_bar_and_the_home_indicator(self, sleep, game_over):
        page = MockPage(width=360, height=640, system_bars=(24, 48))
        view = BlockFallView(page)
        view.game.game_over = game_over
        view.refresh()
        assert screen_height(view) <= 640 - 24 - 48

    def test_system_bars_known_later_make_everything_fit_again(self, sleep):
        page = MockPage(width=360, height=640)
        view = BlockFallView(page)
        assert page.on_media_change == view._handle_media_change
        page.updated = False
        view._handle_media_change(media_with((24, 48)))  # the phone tells its system bars
        view.game.game_over = True
        view.refresh()
        assert screen_height(view) <= 640 - 24 - 48
        assert page.updated

    def test_a_resize_keeps_room_for_the_system_bars(self, sleep):
        page = MockPage(width=412, height=915, system_bars=(24, 48))
        view = BlockFallView(page)
        view._handle_resize(type("ResizeEvent", (), {"width": 360, "height": 640})())
        view.game.game_over = True
        view.refresh()
        assert screen_height(view) <= 640 - 24 - 48

    def test_a_short_screen_gets_a_smaller_grid_with_room_for_the_final_score(self, sleep):
        page = MockPage(width=360, height=640)
        view = BlockFallView(page)
        assert view.board.outer_width < 360 - 2 * (page.padding + view.layout.padding)
        view.game.game_over = True
        view.refresh()
        assert screen_height(view) == pytest.approx(640)  # all of it, nothing more

    def test_a_tall_screen_keeps_the_grid_as_wide_as_the_page(self, sleep):
        page = MockPage(width=412, height=915)
        view = BlockFallView(page)
        assert needed_width(view, page) == pytest.approx(412)

    def test_nothing_moves_when_the_game_ends(self, sleep):
        page = MockPage(width=360, height=640)
        view = BlockFallView(page)
        before = (view.board.cell, view.board.stack.height, view.status_box.visible, view.status_display.value)
        view.game.game_over = True
        view.refresh()
        after = (view.board.cell, view.board.stack.height, view.status_box.visible, view.status_display.value)
        assert after == before  # the final score only takes free space above the blocks

    def test_the_grid_follows_a_new_screen_height(self, sleep):
        page = MockPage(width=360)
        view = BlockFallView(page)
        page.height = 640
        view._handle_resize(type("ResizeEvent", (), {"width": 360, "height": 640})())
        view.game.game_over = True
        view.refresh()
        assert screen_height(view) <= 640

    @pytest.mark.parametrize("width", [360, 375, 390, 412, 430, 800])
    def test_the_blocks_reach_the_middle_of_the_screen(self, make_view, width):
        page, view = make_view(width)
        _, blocks = view.header.control.controls
        top_row = blocks.controls[0]
        blocks_width = sum(b.width for b in top_row.controls) + top_row.spacing
        right = width - page.padding - view.layout.padding  # where the blocks end
        assert right - blocks_width == pytest.approx(width / 2)

    @pytest.mark.parametrize("width", [320, 360, 412])
    def test_the_logo_keeps_room_on_its_left(self, make_view, width):
        page, view = make_view(width)
        # Measured in Roboto Black (Flutter's font) at the logo's size.
        from PIL import ImageFont

        from tools.screen import FONT_DIR

        mark, name = view.header.logo.controls
        size = name.controls[0].size
        font = ImageFont.truetype(f"{FONT_DIR}/Roboto-Black.ttf", size * 10)
        name_width = max(font.getlength(t.value) for t in name.controls) / 10
        cell = mark.controls[0].controls[0].width
        logo_width = 3 * cell + 2 * mark.controls[0].spacing + view.header.logo.spacing + name_width
        _, blocks = view.header.control.controls
        top_row = blocks.controls[0]
        blocks_width = sum(b.width for b in top_row.controls) + top_row.spacing
        available = width - 2 * (page.padding + view.layout.padding)
        assert logo_width + view.header.control.spacing + blocks_width <= available

    def test_the_blocks_follow_a_new_screen_width(self, make_view):
        page, view = make_view(412)
        view._handle_resize(type("ResizeEvent", (), {"width": 360, "height": None})())
        _, blocks = view.header.control.controls
        top_row = blocks.controls[0]
        assert sum(b.width for b in top_row.controls) + top_row.spacing == pytest.approx(360 / 2 - 15)

    def test_logo_is_not_taller_than_the_two_rows_of_blocks(self, view):
        _, blocks = view.header.control.controls
        blocks_height = 2 * view.header.blocks[0].height + blocks.spacing
        mark, name = view.header.logo.controls
        cell = mark.controls[0].controls[0].height
        assert 3 * cell + 2 * mark.spacing <= blocks_height
        assert sum(1.25 * t.size for t in name.controls) <= blocks_height


class TestSwipe:
    """Play by touch: swipe anywhere in the game area, like 2048."""

    @pytest.mark.parametrize("direction", list(SWIPES))
    def test_each_swipe_plays_that_move(self, view, game, direction):
        with patch.object(game, "play_move") as play_move:
            swipe(view, direction)
        play_move.assert_called_once_with(direction)

    def test_a_tap_or_tiny_drag_does_not_play(self, view, game):
        with patch.object(game, "play_move") as play_move:
            swipe(view, 6, 3)
        play_move.assert_not_called()

    def test_a_new_swipe_starts_from_zero(self, view, game):
        with patch.object(game, "play_move") as play_move:
            swipe(view, 15, 0)  # too short on its own
            swipe(view, 15, 0)  # must not add up with the previous one
        play_move.assert_not_called()

    def test_an_interrupted_swipe_does_not_leak_into_the_next_one(self, view, game):
        area = view.swipe_area.control
        area.on_pan_start(None)
        area.on_pan_update(SimpleNamespace(local_delta=ft.Offset(20, 0)))
        # ...the gesture is cancelled: no pan end. Then a tiny new drag:
        with patch.object(game, "play_move") as play_move:
            swipe(view, 10, 0)
        play_move.assert_not_called()

    def test_the_movement_is_added_up_while_the_finger_moves(self, view, game):
        with patch.object(game, "play_move") as play_move:
            swipe(view, -40, 0, steps=8)  # 8 small steps of 5 px
        play_move.assert_called_once_with("left")

    def test_swipe_area_covers_levels_message_and_grid_but_not_the_header(self, view):
        area = view.swipe_area.control
        inside = list(iter_controls(area))
        for control in (view.level_bar.control, view.status_display, view.board.stack):
            assert control in inside
        assert view.header.restart_button not in inside
        assert area.expand
        assert area.content.expand
        assert area.content.bgcolor == COLOR_BG  # painted: swipes work on empty space too

    def test_real_swipe_moves_the_squares(self, view, game):
        place(game, (5, 5, BLUE))
        with next_colors(GREEN):
            swipe(view, "right")
        assert board_colors(view)[5][-1] == TILE_COLORS[BLUE]


def level_texts(view):
    return texts_on_screen(view.header.level_button)


def tap_level(view):
    view.header.level_button.on_click(None)


class TestDifficulty:
    """The LEVEL block (below SCORE) switches between 3 grid sizes."""

    @pytest.fixture
    def view(self, sleep):
        # The real default game: MIDDLE's grid (empty, for predictable tests).
        return BlockFallView(MockPage(), BlockFallEngine(start_squares=0))

    def test_the_three_levels(self):
        assert [(name, rows, cols) for name, rows, cols, _ in DIFFICULTIES] == [
            ("BEGINNER", 6, 6), ("MIDDLE", 5, 5), ("MASTER", 4, 4),
        ]
        assert DIFFICULTIES[DEFAULT_DIFFICULTY][0] == "MIDDLE"

    def test_level_colors_green_yellow_red(self):
        hues = []
        for _, _, _, color in DIFFICULTIES:
            r, g, b = (int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))
            hues.append(colorsys.rgb_to_hls(r, g, b)[0] * 360)
        green, yellow, red = hues
        assert 100 <= green <= 160, green
        assert 40 <= yellow <= 60, yellow
        assert red <= 15 or red >= 345, red

    def test_level_block_is_below_score(self, view):
        score, _best, level, _restart = view.header.blocks
        assert level is view.header.level_button
        top_row, bottom_row = view.header.control.controls[1].controls
        assert top_row.controls.index(score) == bottom_row.controls.index(level)

    def test_starts_at_middle_in_yellow(self, view, game):
        assert level_texts(view) == ["LEVEL", "MIDDLE"]
        assert view.header.level_button.bgcolor == DIFFICULTIES[1][3]
        assert (game.rows, game.cols) == (5, 5)

    def test_each_tap_goes_to_the_next_level_and_its_grid(self, view):
        # One after the other: each tap starts from the level the last one chose.
        for name, rows, cols, color in (DIFFICULTIES[2], DIFFICULTIES[0], DIFFICULTIES[1]):
            tap_level(view)
            assert level_texts(view) == ["LEVEL", name]
            assert view.header.level_button.bgcolor == color
            new_game = view.game
            assert (new_game.rows, new_game.cols) == (rows, cols), name
            assert len(view.board.slots) == rows * cols, name
            assert len(view.board.stack.controls) == rows * cols + len(view.board.tiles), name

    def test_new_level_starts_a_new_game_with_its_own_best(self, view, game):
        game.score = game.high_score = 120
        game.game_over = True
        view.refresh()
        tap_level(view)
        new_game = view.game
        assert (new_game.score, new_game.high_score, new_game.game_over) == (0, 0, False)
        assert len(view.board.tiles) == round(4 * 4 * START_FILL)  # MASTER
        assert view.header.best_text.value == "0"  # MASTER's best, not MIDDLE's
        assert not view.game_end.button.visible
        assert [b.bgcolor for b in view.level_bar.blocks[2:]] == [COLOR_LOCKED] * 3

    def test_the_new_grid_fills_the_width(self, page, view, layout):
        for _ in range(3):
            tap_level(view)
            needed = view.board.stack.width + 2 * (page.padding + layout.padding
                                                   + view.board.frame.padding)
            assert needed == pytest.approx(page.width)

    def test_swipes_play_on_the_new_grid(self, view):
        tap_level(view)  # MASTER 4x4
        game = view.game
        game.start_squares = 0
        game.reset()  # an empty 4x4 board
        game.place_square(1, 1, BLUE)
        view.refresh()
        with next_colors(GREEN):
            swipe(view, "right")
        assert game.grid[1][3] == BLUE
        assert board_colors(view)[1][3] == TILE_COLORS[BLUE]

    def test_level_change_during_an_animation_happens_right_after_it(self, page, view, game, sleep):
        place(game, (0, 0, BLUE))

        tapped = []

        async def tap_during_animation(_seconds):
            if not tapped:
                tapped.append(True)
                tap_level(view)  # a move is being played: asks first
                confirm(page)

        sleep.side_effect = tap_during_animation
        move(view, "down")  # real random: the new game needs many colors
        assert (view.game.rows, view.game.cols) == (4, 4)
        assert level_texts(view) == ["LEVEL", "MASTER"]


def tutorial_buttons(page):
    return {button.content.value: button for button in page.dialog.actions}


def finish_tutorial(page):
    """Go through every step, then PLAY!"""
    while "NEXT" in tutorial_buttons(page):
        tutorial_buttons(page)["NEXT"].on_click(None)
    tutorial_buttons(page)["PLAY!"].on_click(None)


class TestHowToPlay:
    """A HOW TO PLAY button at the bottom opens the tutorial; the device
    remembers once it has been seen."""

    @pytest.fixture
    def storage(self):
        return FakeStorage()

    @pytest.fixture
    def view(self, sleep, storage):
        return BlockFallView(MockPage(), BlockFallEngine(rows=10, cols=10, start_squares=0), storage=storage)

    def test_the_button_is_at_the_bottom_while_playing(self, view):
        slot = view.layout.content.controls[-1]
        assert view.help_button.control in slot.content.controls
        assert view.help_button.control.visible
        assert view.help_button.label.value == "HOW TO PLAY"

    def test_at_game_over_restart_takes_its_place(self, view):
        view.game.game_over = True
        view.refresh()
        assert not view.help_button.control.visible
        assert view.game_end.button.visible

    def test_it_opens_the_tutorial(self, view):
        view.help_button.control.on_click(None)
        assert isinstance(view.page.dialog, ft.AlertDialog)
        assert view.page.dialog.title.value == "Swipe to move"

    def test_each_step_reaches_the_screen(self, view):
        view.help_button.control.on_click(None)
        view.page.updated = False
        tutorial_buttons(view.page)["NEXT"].on_click(None)
        assert view.page.updated
        assert view.page.dialog.title.value == "A new square"

    def test_finishing_it_closes_it_and_saves_that_it_was_seen(self, view, storage):
        view.show_tutorial()
        finish_tutorial(view.page)
        assert view.page.dialog is None
        run_background_tasks(view.page)
        assert storage.values == {"block_fall.tutorial_seen": True}

    def test_skipping_it_counts_as_seen(self, view, storage):
        view.show_tutorial()
        tutorial_buttons(view.page)["SKIP"].on_click(None)
        run_background_tasks(view.page)
        assert (view.page.dialog, storage.values) == (None, {"block_fall.tutorial_seen": True})

    def test_the_game_goes_on_where_it_was(self, view):
        place(view.game, (0, 0, BLUE))
        view.game.score = 12
        view.show_tutorial()
        finish_tutorial(view.page)
        assert (len(view.game.squares()), view.game.score) == (1, 12)

    def test_without_storage_nothing_is_saved(self, sleep):
        view = BlockFallView(MockPage(), BlockFallEngine(start_squares=0))
        view.show_tutorial()
        finish_tutorial(view.page)
        assert view.page.tasks == []

    def test_in_portuguese(self, view):
        view.set_language("pt")
        assert view.help_button.label.value == "COMO JOGAR"
        view.help_button.control.on_click(None)
        assert view.page.dialog.title.value == "Deslize para mover"


def score_a_line(view):
    """Play a move that lines up 3 blues on the bottom row: 3 points."""
    bottom = view.game.rows - 1
    place(view.game, (0, bottom, BLUE), (1, bottom, BLUE), (3, bottom, BLUE))
    with next_colors(GREEN):
        move(view, "left")


class TestBestPerLevel:
    """Each level keeps its own best score, saved on the device; BEST shows
    the current level's."""

    @pytest.fixture
    def storage(self):
        return FakeStorage()

    @pytest.fixture
    def view(self, sleep, storage):
        return BlockFallView(MockPage(), BlockFallEngine(start_squares=0), storage=storage)

    def best_shown(self, view):
        return view.header.best_text.value

    def test_each_level_shows_its_own_best(self, sleep):
        view = BlockFallView(MockPage(), best_scores={0: 30, 1: 80, 2: 15})
        shown = [self.best_shown(view)]  # MIDDLE first
        for _ in range(3):
            tap_level(view)  # MASTER, BEGINNER, MIDDLE again
            shown.append(self.best_shown(view))
        assert shown == ["80", "15", "30", "80"]

    def test_coming_back_to_a_level_shows_its_best_again(self, view):
        score_a_line(view)
        assert self.best_shown(view) == "3"
        view.game.game_over = True  # so the level changes without a question
        tap_level(view)
        assert self.best_shown(view) == "0"  # MASTER: no best yet
        tap_level(view)
        tap_level(view)  # back to MIDDLE
        assert self.best_shown(view) == "3"

    def test_a_new_best_is_saved_on_the_device_for_its_level(self, view, storage):
        score_a_line(view)
        run_background_tasks(view.page)
        assert storage.values == {"block_fall.best.middle": 3}

    def test_no_saving_without_a_new_best(self, sleep, storage):
        view = BlockFallView(MockPage(), BlockFallEngine(start_squares=0), best_scores={1: 50}, storage=storage)
        score_a_line(view)
        assert self.best_shown(view) == "50"
        assert view.page.tasks == []
        assert storage.values == {}

    def test_a_restart_keeps_the_level_s_best(self, view):
        score_a_line(view)
        tap_restart(view)
        confirm(view.page)
        assert (view.game.score, self.best_shown(view)) == (0, "3")

    def test_a_best_reached_is_kept_when_the_level_changes(self, view, storage):
        view.game.high_score = 70  # however it was reached
        view.game.game_over = True
        tap_level(view)
        run_background_tasks(view.page)
        assert view.best_scores[1] == 70
        assert storage.values == {"block_fall.best.middle": 70}

    def test_without_storage_nothing_is_saved(self, sleep):
        view = BlockFallView(MockPage(), BlockFallEngine(start_squares=0))
        score_a_line(view)
        assert view.page.tasks == []
        assert self.best_shown(view) == "3"


def big_text(view):
    (text,) = [c for c in iter_controls(view.game_end.button) if isinstance(c, ft.Text)]
    return text


class TestGameOverButton:
    """When the game ends, a big blue RESTART button appears at the bottom."""

    def test_hidden_while_playing(self, view):
        assert not view.game_end.button.visible

    def test_shown_when_the_game_ends(self, view, game):
        game.game_over = True
        view.refresh()
        assert view.game_end.button.visible

    def test_it_is_at_the_bottom_of_the_app(self, view, layout):
        assert view.game_end.button in layout.content.controls[-1].content.controls

    def test_it_is_big_and_blue(self, view):
        button = view.game_end.button
        board_box = view.board.frame
        assert button.width == view.board.stack.width + 2 * board_box.padding  # full width
        assert button.height >= 56
        assert button.bgcolor == COLOR_RESTART
        assert big_text(view).value == "RESTART"
        assert big_text(view).size >= 20
        assert big_text(view).weight == ft.FontWeight.BOLD

    def test_tapping_it_starts_a_new_game_and_hides_it(self, view, game):
        game.game_over = True
        view.refresh()
        view.game_end.button.on_click(None)
        assert not game.game_over
        assert not view.game_end.button.visible

    def test_appears_after_the_move_that_fills_the_board(self, view, game):
        rows, cols = game.rows, game.cols
        colors = (BLUE, GREEN)
        for row in range(rows):
            for col in range(cols):
                if (row, col) != (rows - 1, cols - 1):
                    # a pattern with no 3 in a line
                    game.place_square(col, row, colors[(col // 2 + row) % 2])
        view.refresh()
        pick = RED if game.grid[rows - 1][cols - 3] != RED else BLUE
        with next_colors(pick):
            move(view, "left")
        assert game.game_over
        assert view.game_end.button.visible


class TestFinalScore:
    """At game over, the points of this game (in color) and GAME OVER under
    them show above the color blocks; the rest of the screen stays as it is."""

    def test_hidden_while_playing(self, view):
        assert not view.game_end.banner.visible

    def test_shown_above_the_color_blocks_at_game_over(self, view, game):
        game.score = 42
        game.game_over = True
        view.refresh()
        column = view.swipe_area.control.content.content.controls
        assert view.game_end.banner.visible
        assert column.index(view.game_end.banner) == column.index(view.level_bar.control) - 1
        points, title = view.game_end.banner.content.controls  # the points first, then GAME OVER
        assert (points.value, title.value) == ("You scored 42 points!", "GAME OVER")
        assert points.size > title.size  # the points stand out

    def test_space_between_the_points_game_over_and_the_blocks(self, view, game):
        game.game_over = True
        view.refresh()
        box = view.game_end.banner
        column = box.content
        assert column.spacing >= 8  # between the points and GAME OVER
        body_spacing = view.swipe_area.control.content.content.spacing
        assert box.padding.bottom + body_spacing >= 18  # between GAME OVER and the blocks
        # Both lines and the gaps fit in the box (Flutter's Roboto line height: 1.17).
        lines = sum(1.17 * text.size for text in column.controls) + column.spacing
        assert lines + box.padding.bottom <= box.height

    def test_the_points_are_colored(self, view, game):
        game.game_over = True
        view.refresh()
        points, title = view.game_end.banner.content.controls
        assert points.color == COLOR_FINAL_SCORE
        assert points.color not in (COLOR_TEXT, title.color)
        assert lightness(points.color) < 0.6  # still easy to read on the cream background

    def test_the_message_under_the_blocks_stays_in_place(self, view, game):
        game.game_over = True
        view.refresh()
        assert view.status_box.visible
        assert view.status_display.value == "Line up 3 or more squares of the same color."
        column = view.swipe_area.control.content.content.controls
        assert column.index(view.status_box) == column.index(view.level_bar.control) + 1

    def test_the_points_are_this_game_s_not_the_best(self, view, game):
        game.score, game.high_score = 15, 300
        game.game_over = True
        view.refresh()
        assert view.game_end.points.value == "You scored 15 points!"

    def test_shown_after_the_move_that_ends_the_game(self, view, game):
        rows, cols = game.rows, game.cols
        for row in range(rows):
            for col in range(cols):
                if (row, col) != (rows - 1, cols - 1):
                    game.place_square(col, row, (BLUE, GREEN)[(col // 2 + row) % 2])  # no 3 in a line
        game.score = 27
        view.refresh()
        pick = RED if game.grid[rows - 1][cols - 3] != RED else BLUE
        with next_colors(pick):
            move(view, "left")
        assert game.game_over
        assert view.game_end.banner.visible
        assert view.game_end.points.value == "You scored 27 points!"

    def test_a_new_game_hides_it(self, view, game):
        game.game_over = True
        view.refresh()
        view.game_end.button.on_click(None)
        assert not view.game_end.banner.visible

    def test_a_new_level_hides_it(self, view, game):
        game.game_over = True
        view.refresh()
        tap_level(view)  # no question: the game is over
        assert not view.game_end.banner.visible

    def test_in_portuguese(self, view, game):
        view.set_language("pt")
        game.score = 8
        game.game_over = True
        view.refresh()
        points, title = view.game_end.banner.content.controls
        assert (points.value, title.value) == ("Você fez 8 pontos!", "FIM DE JOGO")
        assert view.status_display.value == "Alinhe 3 ou mais quadrados da mesma cor."


def dialog_buttons(page):
    return {
        c.content.value: c
        for c in page.dialog.actions
    }


def confirm(page):
    page.dialog.actions[1].on_click(None)  # the second button: RESTART / CHANGE


def cancel(page):
    page.dialog.actions[0].on_click(None)  # the first button: CANCEL


def play_one_move(view):
    with next_colors(GREEN):
        move(view, "left")


class TestConfirm:
    """Restart or level change during a game asks first: the game would be lost."""

    def test_no_question_before_the_first_move(self, page, view):
        view.header.restart_button.on_click(None)
        assert getattr(page, "dialog", None) is None

    def test_restart_during_a_game_asks_first(self, page, view, game):
        play_one_move(view)
        view.header.restart_button.on_click(None)
        dialog = page.dialog
        assert isinstance(dialog, ft.AlertDialog)
        assert dialog.modal
        assert dialog.title.value == "Restart the game?"
        assert dialog.content.value == "You will lose the current game."
        assert len(game.squares()) == 1  # nothing lost yet

    def test_confirming_restarts(self, page, view, game):
        play_one_move(view)
        view.header.restart_button.on_click(None)
        confirm(page)
        assert page.dialog is None
        assert game.squares() == {}

    def test_cancelling_keeps_the_game(self, page, view, game):
        play_one_move(view)
        game.score = 42
        view.header.restart_button.on_click(None)
        cancel(page)
        assert page.dialog is None
        assert (len(game.squares()), game.score) == (1, 42)

    def test_level_change_during_a_game_asks_first(self, page, view):
        play_one_move(view)
        view.header.level_button.on_click(None)
        assert page.dialog.title.value == "Change to MASTER?"
        assert page.dialog.content.value == "You will lose the current game."
        assert (view.game.rows, view.game.cols) == (10, 10)  # unchanged
        confirm(page)
        assert (view.game.rows, view.game.cols) == (4, 4)

    def test_cancelling_the_level_change_keeps_level_and_game(self, page, view):
        play_one_move(view)
        game = view.game
        view.header.level_button.on_click(None)
        cancel(page)
        assert view.game is game
        assert view.header.level_text.value == "MIDDLE"

    def test_no_question_once_the_game_is_over(self, page, view, game):
        play_one_move(view)
        game.game_over = True
        view.refresh()
        view.header.restart_button.on_click(None)
        assert getattr(page, "dialog", None) is None
        assert game.squares() == {}

    def test_swipes_after_game_over_do_not_count_as_moves(self, page, view, game):
        game.game_over = True
        view.refresh()
        swipe(view, "left")  # the game refuses it
        game.game_over = False  # even if the game could go on again...
        view.header.restart_button.on_click(None)
        assert getattr(page, "dialog", None) is None  # ...no move was played

    def test_big_game_over_button_never_asks(self, page, view, game):
        play_one_move(view)
        game.game_over = True
        view.refresh()
        view.game_end.button.on_click(None)
        assert getattr(page, "dialog", None) is None
        assert not game.game_over

    def test_a_new_game_does_not_ask_until_a_move_is_played(self, page, view):
        play_one_move(view)
        view.header.restart_button.on_click(None)
        confirm(page)
        view.header.level_button.on_click(None)  # fresh game: no question
        assert page.dialog is None
        assert view.header.level_text.value == "MASTER"

    def test_dialog_buttons_are_blocks_like_the_rest(self, page, view):
        play_one_move(view)
        view.header.restart_button.on_click(None)
        buttons = dialog_buttons(page)
        assert set(buttons) == {"CANCEL", "RESTART"}
        assert buttons["RESTART"].bgcolor == COLOR_RESTART
        for button in buttons.values():
            assert isinstance(button, ft.Container)
            assert button.border_radius == 6
        assert [c for c in iter_controls(page.dialog) if isinstance(c, (ft.TextButton, ft.Button))] == []

    def test_level_dialog_button_uses_the_new_level_color(self, page, view):
        play_one_move(view)
        view.header.level_button.on_click(None)
        assert dialog_buttons(page)["CHANGE"].bgcolor == DIFFICULTIES[2][3]


def header_labels(view):
    return [block.content.controls[0].value for block in view.header.blocks]


class TestLanguage:
    """Every text on screen follows the chosen language."""

    def test_english_by_default(self, view):
        assert header_labels(view) == ["SCORE", "BEST", "LEVEL", "RESTART"]
        assert view.header.level_text.value == "MIDDLE"
        assert view.status_display.value == "Line up 3 or more squares of the same color."
        assert view.game_end.button.content.value == "RESTART"

    def test_header_and_message_in_portuguese(self, page, view):
        view.set_language("pt")
        assert header_labels(view) == ["PONTOS", "RECORDE", "NÍVEL", "REINICIAR"]
        assert view.header.level_text.value == "MÉDIO"
        assert view.status_display.value == "Alinhe 3 ou mais quadrados da mesma cor."
        assert view.game_end.button.content.value == "REINICIAR"
        assert page.updated

    def test_tooltips_in_portuguese(self, view):
        view.set_language("pt")
        assert view.header.restart_button.tooltip == "Reiniciar"
        assert view.header.level_button.tooltip == "Mudar de nível (começa um novo jogo)"
        assert view.game_end.button.tooltip == "Reiniciar"
        tips = [b.tooltip for b in view.level_bar.blocks]
        assert tips == ["Cor inicial", "Cor inicial", "Desbloqueia com 50 pontos",
                        "Desbloqueia com 100 pontos", "Desbloqueia com 150 pontos"]

    def test_game_over_in_portuguese(self, view, game):
        view.set_language("pt")
        game.game_over = True
        view.refresh()
        assert view.game_end.title.value == "FIM DE JOGO"
        assert view.status_display.value == "Alinhe 3 ou mais quadrados da mesma cor."

    def test_new_color_message_in_portuguese(self, page, view, game):
        view.set_language("pt")
        bottom = game.rows - 1
        place(game, (0, bottom, BLUE), (1, bottom, BLUE), (7, bottom, BLUE))
        game.score = 48
        with next_colors(GREEN):
            move(view, "left")
        assert view.status_display.value == "Nova cor desbloqueada!"
        run_background_tasks(page)
        assert view.status_display.value == "Alinhe 3 ou mais quadrados da mesma cor."

    def test_confirmations_in_portuguese(self, page, view):
        view.set_language("pt")
        with next_colors(GREEN):
            move(view, "left")
        view.header.restart_button.on_click(None)
        dialog = page.dialog
        assert (dialog.title.value, dialog.content.value) == ("Reiniciar o jogo?", "Você vai perder o jogo atual.")
        assert [b.content.value for b in dialog.actions] == ["CANCELAR", "REINICIAR"]
        cancel(page)
        view.header.level_button.on_click(None)
        assert page.dialog.title.value == "Mudar para MESTRE?"
        assert [b.content.value for b in page.dialog.actions] == ["CANCELAR", "MUDAR"]

    def test_level_names_follow_the_language(self, view):
        view.set_language("pt")
        names = []
        for _ in range(3):
            view.header.level_button.on_click(None)
            names.append(view.header.level_text.value)
        assert names == ["MESTRE", "INICIANTE", "MÉDIO"]

    def test_switching_back_to_english(self, view):
        view.set_language("pt")
        view.set_language("en")
        assert header_labels(view) == ["SCORE", "BEST", "LEVEL", "RESTART"]

    def test_flutter_is_told_the_language_too(self, page, view):
        config = page.locale_configuration
        assert [l.language_code for l in config.supported_locales] == ["en", "pt"]
        assert config.current_locale.language_code == "en"
        view.set_language("pt")
        assert page.locale_configuration.current_locale.language_code == "pt"

    def test_changing_language_keeps_the_game(self, view, game):
        place(game, (0, 0, BLUE))
        game.score = 42
        view.set_language("pt")
        assert (len(game.squares()), game.score) == (1, 42)
        assert view.header.score_text.value == "42"

