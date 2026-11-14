"""Rules of the game.

Boards are written as text: B = blue, G = green, R = red, . = empty.
(Peach and purple are only needed for the level rules.)
"""

import random
from unittest.mock import patch

import pytest

import game
from config import (
    BLUE, DEFAULT_DIFFICULTY, DIFFICULTIES, GREEN, GRID_COLS, GRID_ROWS, PEACH, PURPLE, RED,
    START_FILL, UNLOCK_SCORES,
)
from game import (
    MATCH_LENGTH,
    SQUARE_COLORS,
    BlockFallEngine,
    Frame,
    find_lines,
    line_points,
)

LETTER = {"B": BLUE, "G": GREEN, "R": RED}
NAME = {color: letter for letter, color in LETTER.items()}
DIRECTIONS = ("left", "right", "up", "down")


def load(*rows):
    """An engine whose board is drawn as text (the size follows the drawing)."""
    engine = BlockFallEngine(rows=len(rows), cols=len(rows[0]), start_squares=0)
    for row, line in enumerate(rows):
        for column, letter in enumerate(line):
            if letter != ".":
                assert engine.place_square(column, row, LETTER[letter])
    return engine


def show(engine):
    return ["".join(NAME.get(v, ".") for v in row) for row in engine.grid]


def first_choice(values):
    return values[0]


def is_colors(values):
    """True for the random.choice call that picks a color (not a position)."""
    return all(isinstance(value, int) for value in values)


def color_then_first(color):
    """Mock for random.choice: new squares get `color`, first free position."""
    return lambda v: color if is_colors(v) else v[0]


def as_grid(*rows):
    """A raw grid (lists of color values) drawn as text."""
    return [[LETTER.get(ch, 0) for ch in row] for row in rows]


def spawn_calls(engine, direction, pick=first_choice):
    """Spawn one square with random.choice mocked; return the choices asked for."""
    with patch("game.random.choice", side_effect=pick) as choice:
        assert engine.spawn_square(direction)
    return choice.call_args_list


def count_squares(engine):
    return len(engine.squares())


class TestRules:
    def test_five_colors_one_per_level(self):
        assert SQUARE_COLORS == (BLUE, GREEN, RED, PEACH, PURPLE)

    def test_a_line_needs_three_squares(self):
        assert MATCH_LENGTH == 3

    def test_points_three_for_three_then_two_for_each_extra_square(self):
        assert [line_points(n) for n in (3, 4, 5, 6, 10)] == [3, 5, 7, 9, 17]

    def test_nothing_from_tetris_is_left(self):
        for name in ("TETROMINOES", "Piece", "MAX_SAME_COLOR", "PIECE_COLORS"):
            assert not hasattr(game, name), name
        for name in ("current_piece", "next_piece", "block_ids", "spawn_skipped",
                     "rotate_piece", "drop_piece", "place_piece"):
            assert not hasattr(BlockFallEngine(), name), name


class TestBoard:
    def test_default_board_is_the_middle_5_by_5(self):
        engine = BlockFallEngine(start_squares=0)
        assert DIFFICULTIES[DEFAULT_DIFFICULTY][0] == "MIDDLE"
        assert (GRID_ROWS, GRID_COLS) == (5, 5)
        assert (engine.rows, engine.cols) == (5, 5)
        assert engine.grid == [[0] * 5 for _ in range(5)]
        assert (engine.score, engine.high_score, engine.game_over) == (0, 0, False)

    def test_custom_size(self):
        engine = BlockFallEngine(rows=3, cols=5, start_squares=0)
        assert show(engine) == ["....."] * 3

    def test_place_square(self):
        engine = load("...", "...")
        assert engine.place_square(2, 1, RED)
        assert show(engine) == ["...", "..R"]

    def test_place_square_rejects_taken_or_outside_cells(self):
        engine = load("B..")
        assert not engine.place_square(0, 0, RED)
        assert not engine.place_square(3, 0, RED)
        assert not engine.place_square(0, -1, RED)
        assert show(engine) == ["B.."]

    def test_reset_clears_the_board_and_score_but_keeps_the_best(self):
        engine = load("BG.", "...")
        engine.score = engine.high_score = 9
        engine.game_over = True
        engine.frames = ["old"]
        engine.reset()  # this engine was made with no starting squares
        assert show(engine) == ["...", "..."]
        assert (engine.score, engine.high_score, engine.game_over) == (0, 9, False)
        assert (engine.squares(), engine.frames) == ({}, [])


class TestSlide:
    """Every square slides as far as it can, like 2048, but never merges."""

    def test_left_and_right(self):
        engine = load("B.G.R", ".R..B")
        assert engine.move_board("left")
        assert show(engine) == ["BGR..", "RB..."]
        assert engine.move_board("right")
        assert show(engine) == ["..BGR", "...RB"]

    def test_up_and_down(self):
        engine = load("B.", "..", "GR", "..", "RB")
        assert engine.move_board("up")
        assert show(engine) == ["BR", "GB", "R.", "..", ".."]
        assert engine.move_board("down")
        assert show(engine) == ["..", "..", "B.", "GR", "RB"]

    def test_same_colors_never_merge(self):
        engine = load("B.B.")
        engine.move_board("right")
        assert show(engine) == ["..BB"]
        assert engine.score == 0

    def test_blocked_move_reports_no_movement(self):
        engine = load("BG..", "R...")
        assert not engine.move_board("left")
        assert not engine.move_board("up")
        assert show(engine) == ["BG..", "R..."]

    def test_empty_board_does_not_move(self):
        engine = load("...", "...")
        for direction in DIRECTIONS:
            assert not engine.move_board(direction)


class TestFindLines:
    """Finding lines only looks at the board: nothing is removed or scored."""

    def test_finds_rows_and_columns_of_three_or_more(self):
        lines = find_lines(as_grid("BBB.", "G...", "G...", "GR.."))
        assert sorted(map(sorted, lines)) == [[(0, 0), (1, 0), (2, 0)], [(0, 1), (0, 2), (0, 3)]]

    def test_each_line_is_reported_whole(self):
        (line,) = find_lines(as_grid("RRRRR"))
        assert len(line) == 5

    def test_empty_cells_and_pairs_are_not_lines(self):
        assert find_lines(as_grid("...", "BB.", "GRG")) == []

    def test_the_board_is_left_untouched(self):
        grid = as_grid("BBB")
        find_lines(grid)
        assert grid == as_grid("BBB")


class TestMatch:
    """3 or more squares of one color in a line disappear and score points."""

    def test_three_in_a_row(self):
        engine = load("BBBG.")
        assert engine.clear_matches() == 3
        assert show(engine) == ["...G."]
        assert engine.score == 3

    def test_three_in_a_column(self):
        engine = load("R.", "R.", "RG")
        engine.clear_matches()
        assert show(engine) == ["..", "..", ".G"]
        assert engine.score == 3

    def test_two_in_a_line_stay(self):
        engine = load("BB.", "G..", "G..")
        assert engine.clear_matches() == 0
        assert engine.score == 0

    def test_four_in_a_line_score_3_plus_2(self):
        engine = load("GGGGB")
        engine.clear_matches()
        assert show(engine) == ["....B"]
        assert engine.score == 5

    def test_five_in_a_line_score_3_plus_2_plus_2(self):
        engine = load("RRRRR")
        engine.clear_matches()
        assert engine.score == 7

    def test_another_color_breaks_the_line(self):
        engine = load("BBGBB")
        assert engine.clear_matches() == 0

    def test_diagonals_do_not_count(self):
        engine = load("B..", ".B.", "..B")
        assert engine.clear_matches() == 0

    def test_two_lines_at_once_both_score(self):
        engine = load("BBB", "...", "GGG")
        assert engine.clear_matches() == 6
        assert engine.score == 6

    def test_crossing_lines_each_score_and_the_shared_square_goes_once(self):
        engine = load("RRR", "R..", "R..")
        assert engine.clear_matches() == 5
        assert engine.score == 3 + 3
        assert show(engine) == ["..."] * 3

    def test_other_squares_stay_where_they_are(self):
        engine = load("G..", "BBB", "..R")
        engine.clear_matches()
        assert show(engine) == ["G..", "...", "..R"]

    def test_a_move_that_lines_up_colors_scores(self):
        engine = load("BB.B")
        assert engine.move_board("left")
        assert show(engine) == ["...."]
        assert (engine.score, engine.high_score) == (3, 3)

    def test_high_score_follows_the_score_but_never_drops(self):
        engine = load("GGG")
        engine.high_score = 100
        engine.clear_matches()
        assert (engine.score, engine.high_score) == (3, 100)


class TestSpawn:
    """After a move, one new square appears on the opposite side."""

    def test_after_right_it_appears_on_the_left_edge(self):
        engine = load("..", "..", "..")
        calls = spawn_calls(engine, "right")
        assert calls[0].args[0] == [(0, 0), (0, 1), (0, 2)]

    def test_after_left_it_appears_on_the_right_edge(self):
        calls = spawn_calls(load("...", "..."), "left")
        assert calls[0].args[0] == [(2, 0), (2, 1)]

    def test_after_down_it_appears_on_the_top_edge(self):
        calls = spawn_calls(load("...", "..."), "down")
        assert calls[0].args[0] == [(0, 0), (1, 0), (2, 0)]

    def test_after_up_it_appears_on_the_bottom_edge(self):
        calls = spawn_calls(load("...", "..."), "up")
        assert calls[0].args[0] == [(0, 1), (1, 1), (2, 1)]

    def test_taken_cells_on_the_edge_are_skipped(self):
        engine = load("B..", "...", "G..")
        calls = spawn_calls(engine, "right")
        assert calls[0].args[0] == [(0, 1)]

    def test_full_edge_means_the_nearest_line_inward(self):
        engine = load("B..", "G..", "R..")
        calls = spawn_calls(engine, "right")
        assert calls[0].args[0] == [(1, 0), (1, 1), (1, 2)]

    def test_color_is_random_among_the_unlocked_colors(self):
        engine = load("...")
        calls = spawn_calls(engine, "down", pick=lambda v: v[-1])
        assert tuple(calls[1].args[0]) == (BLUE, GREEN)
        assert show(engine) == ["..G"]

    def test_new_squares_only_use_unlocked_colors(self):
        for score, expected in ((0, {BLUE, GREEN}), (50, {BLUE, GREEN, RED}),
                                (350, set(SQUARE_COLORS))):
            seen = set()
            for _ in range(120):
                engine = BlockFallEngine(rows=1, cols=1, start_squares=0)
                engine.score = score
                engine.spawn_square("down")
                seen.add(engine.grid[0][0])
            assert seen == expected, score

    def test_position_along_the_edge_is_random(self):
        engine = load("...", "...", "...")
        spawn_calls(engine, "right", pick=lambda v: v[1])
        assert [row[0] != 0 for row in engine.grid] == [False, True, False]

    def test_exactly_one_square_is_added(self):
        engine = load("...", "...")
        engine.spawn_square("left")
        assert len(engine.squares()) == 1

    def test_a_new_square_can_complete_a_line(self):
        engine = load(".BB")
        spawn_calls(engine, "right", pick=color_then_first(BLUE))
        assert show(engine) == ["..."]
        assert engine.score == 3

    def test_no_free_cell_no_square(self):
        engine = load("BG", "GB")
        assert not engine.spawn_square("left")
        assert show(engine) == ["BG", "GB"]


class TestPlayMove:
    """One press: slide everything, then add one square on the other side."""

    def test_move_first_then_the_new_square(self):
        engine = load("B..", "...")
        with patch("game.random.choice", side_effect=lambda v: v[-1]):
            assert engine.play_move("right")
        # B slid right, then a square in the last unlocked color (green)
        # appeared on the left edge, last row.
        assert show(engine) == ["..B", "G.."]

    def test_every_press_adds_one_square_even_if_nothing_moves(self):
        engine = load("....", "....")
        colors = iter([BLUE, GREEN, GREEN, BLUE])  # never 3 in a line: no match
        pick = lambda v: next(colors) if is_colors(v) else v[0]  # noqa: E731
        with patch("game.random.choice", side_effect=pick):
            for count in range(1, 5):
                engine.play_move("up")
                assert len(engine.squares()) == count
        assert show(engine) == ["BG..", "GB.."]

    def test_invalid_direction_does_nothing(self):
        engine = load("...")
        assert not engine.play_move("diagonal")
        assert engine.squares() == {}

    def test_no_moves_after_game_over(self):
        engine = load("B..")
        engine.game_over = True
        assert not engine.play_move("right")
        assert show(engine) == ["B.."]


class TestGameOver:
    """The game only ends when the board is full."""

    def test_board_filled_by_the_last_square_is_game_over(self):
        engine = load("BGR", "GRB", "RB.")
        with patch("game.random.choice", side_effect=color_then_first(GREEN)):
            engine.play_move("left")  # nothing moves; the free cell stays free on the right
        assert show(engine) == ["BGR", "GRB", "RBG"]
        assert engine.game_over

    def test_not_over_with_free_squares(self):
        engine = load("BGR", "GR.", "RB.")
        with patch("game.random.choice", side_effect=color_then_first(BLUE)):
            engine.play_move("left")
        assert sum(v == 0 for row in engine.grid for v in row) == 1
        assert not engine.game_over

    def test_a_match_on_the_last_free_cell_keeps_the_game_going(self):
        engine = load("BGR", "GRB", "BB.")
        with patch("game.random.choice", side_effect=color_then_first(BLUE)):
            engine.play_move("left")
        assert show(engine) == ["BGR", "GRB", "..."]
        assert not engine.game_over

    def test_full_board_is_game_over(self):
        engine = load("BG", "GB")
        assert engine.play_move("right")
        assert engine.game_over


class TestSquareIdentity:
    """Every square keeps one id for its whole life, so the UI can animate it."""

    def test_squares_lists_position_and_color_by_id(self):
        engine = load("B.", ".R")
        assert sorted(engine.squares().values()) == [(0, 0, BLUE), (1, 1, RED)]

    def test_ids_travel_with_their_squares(self):
        engine = load("B.G.", "....")
        before = engine.squares()
        engine.move_board("right")
        engine.move_board("down")
        after = engine.squares()
        assert set(after) == set(before)
        assert sorted(after.values()) == [(2, 1, BLUE), (3, 1, GREEN)]

    def test_ids_are_never_reused(self):
        engine = load("GGG", "...")
        gone = set(engine.squares())
        engine.clear_matches()
        with patch("game.random.choice", side_effect=color_then_first(BLUE)):
            engine.spawn_square("down")
            engine.spawn_square("down")
        new = set(engine.squares())
        assert len(new) == 2
        assert all(i > max(gone) for i in new)

    def test_cleared_squares_lose_their_ids(self):
        engine = load("GGG", "R..")
        red = [i for i, (_, _, c) in engine.squares().items() if c == RED]
        engine.clear_matches()
        assert list(engine.squares()) == red


class TestFrame:
    """Each press records what happened, step by step, for the animation."""

    def test_slide_then_match_then_spawn(self):
        engine = load("BB.B.", ".....")
        engine.play_move("left")
        assert [f.kind for f in engine.frames] == ["slide", "match", "spawn"]
        assert all(isinstance(f, Frame) for f in engine.frames)

    def test_slide_frame_shows_the_new_places_before_matches(self):
        engine = load("BB.B.", ".....")
        engine.play_move("left")
        slide = engine.frames[0]
        assert sorted(slide.squares.values()) == [(0, 0, BLUE), (1, 0, BLUE), (2, 0, BLUE)]
        assert slide.gold == frozenset()

    def test_match_frame_marks_the_matched_squares_gold(self):
        engine = load("BB.B.", ".....")
        engine.play_move("left")
        match = engine.frames[1]
        assert match.gold == frozenset(match.squares)
        assert match.gold.isdisjoint(engine.squares())

    def test_spawn_frame_shows_the_new_square(self):
        engine = load("G....", ".....")
        engine.play_move("right")
        spawn = engine.frames[-1]
        assert spawn.kind == "spawn"
        assert spawn.squares == engine.squares()
        assert len(spawn.squares) == 2

    def test_no_slide_frame_when_nothing_moves(self):
        engine = load("G..", "...")
        engine.play_move("left")
        assert [f.kind for f in engine.frames] == ["spawn"]

    def test_match_made_by_the_new_square_comes_after_its_spawn_frame(self):
        engine = load(".RR", "...")
        with patch("game.random.choice", side_effect=color_then_first(RED)):
            engine.play_move("right")
        assert [f.kind for f in engine.frames] == ["spawn", "match"]

    def test_each_press_starts_with_no_frames(self):
        engine = load("G..")
        engine.frames = ["stale"]
        engine.play_move("right")
        assert "stale" not in engine.frames

    def test_no_frames_after_game_over(self):
        engine = load("G..")
        engine.frames = ["stale"]
        engine.game_over = True
        engine.play_move("left")
        assert engine.frames == []


class TestLevel:
    """Start with 2 colors; unlock one more every 50 points: at 50, 100, 150."""

    def test_unlock_scores(self):
        assert UNLOCK_SCORES == (0, 0, 50, 100, 150)

    @pytest.mark.parametrize("score, count", [
        (0, 2), (49, 2), (50, 3), (99, 3), (100, 4), (149, 4), (150, 5), (10_000, 5),
    ])
    def test_colors_unlocked_by_score(self, score, count):
        engine = BlockFallEngine(start_squares=0)
        engine.score = score
        assert engine.unlocked_colors() == SQUARE_COLORS[:count]

    def test_one_more_color_every_50_points(self):
        steps = [b - a for a, b in zip(UNLOCK_SCORES[1:], UNLOCK_SCORES[2:])]
        assert steps == [50, 50, 50]

    def test_game_starts_with_two_colors(self):
        assert BlockFallEngine().unlocked_colors() == (BLUE, GREEN)

    def test_a_new_color_can_be_used_right_after_it_is_unlocked(self):
        engine = load("BB.B.")
        engine.score = 48
        with patch("game.random.choice", side_effect=first_choice) as choice:
            engine.play_move("left")  # the line scores 3: 48 -> 51
        assert engine.score == 51
        color_calls = [c.args[0] for c in choice.call_args_list if is_colors(c.args[0])]
        assert tuple(color_calls[-1]) == (BLUE, GREEN, RED)

    def test_a_new_game_locks_the_colors_again(self):
        engine = BlockFallEngine(start_squares=0)
        engine.score = 400
        engine.reset()
        assert engine.unlocked_colors() == (BLUE, GREEN)


class TestStartSquares:
    """A new game already has some squares on the board."""

    @pytest.mark.parametrize("rows, cols, expected", [(12, 12, 14), (8, 8, 6), (6, 6, 4), (10, 10, 10)])
    def test_a_new_game_fills_about_10_percent_of_the_grid(self, rows, cols, expected):
        assert START_FILL == 0.10
        assert count_squares(BlockFallEngine(rows=rows, cols=cols)) == expected

    def test_starting_squares_use_only_the_two_starting_colors(self):
        for _ in range(20):
            colors = {c for _, _, c in BlockFallEngine().squares().values()}
            assert colors <= {BLUE, GREEN}

    def test_starting_squares_never_form_a_line(self):
        for _ in range(50):
            engine = BlockFallEngine()
            assert _copy(engine).clear_matches() == 0
            assert engine.score == 0

    def test_starting_squares_are_placed_randomly(self):
        layouts = {frozenset((c, r) for c, r, _ in BlockFallEngine().squares().values())
                   for _ in range(5)}
        assert len(layouts) > 1

    def test_reset_puts_new_starting_squares_on_the_board(self):
        engine = BlockFallEngine(rows=10, cols=10)
        engine.play_move("left")
        engine.reset()
        assert count_squares(engine) == 10
        assert (engine.score, engine.frames) == (0, [])

    def test_an_explicit_count_still_wins(self):
        assert count_squares(BlockFallEngine(rows=8, cols=8, start_squares=3)) == 3

    def test_starting_squares_fit_small_boards(self):
        engine = BlockFallEngine(rows=2, cols=2, start_squares=10)
        assert count_squares(engine) == 4
        assert _copy(engine).clear_matches() == 0

    def test_a_cell_that_would_complete_a_line_is_left_empty(self):
        # Both colors would make 3 in a line at (2, 2): that cell must stay empty.
        engine = load("..B", "..B", "GG.")
        with patch("game.random.shuffle"):  # fill cells in reading order
            engine._add_starting_squares(9)
        assert engine.grid[2][2] == 0
        assert _copy(engine).clear_matches() == 0


class TestRandomPlay:
    def test_rules_hold_during_random_games(self):
        state = random.getstate()
        try:
            random.seed(2024)
            for _ in range(20):
                engine = BlockFallEngine()
                for _ in range(300):
                    if engine.game_over:
                        break
                    before = len(engine.squares())
                    score = engine.score
                    engine.play_move(random.choice(DIRECTIONS))
                    added = any(frame.kind == "spawn" for frame in engine.frames)
                    removed = before + added - len(engine.squares())
                    points = engine.score - score
                    # No line of 3 is ever left on the board.
                    assert BlockFallEngine.clear_matches(_copy(engine)) == 0
                    # Each removed square is worth at least 1 point, lines at least 3.
                    assert points >= removed and (removed == 0) == (points == 0)
                    # Only unlocked colors are ever on the board.
                    colors = {v for row in engine.grid for v in row if v}
                    assert colors <= set(engine.unlocked_colors())
                    # Game over exactly when the board is full.
                    full = all(all(row) for row in engine.grid)
                    assert engine.game_over == full
        finally:
            random.setstate(state)


def _copy(engine):
    clone = BlockFallEngine(rows=engine.rows, cols=engine.cols, start_squares=0)
    clone.grid = [row[:] for row in engine.grid]
    clone.square_ids = [row[:] for row in engine.square_ids]
    return clone
