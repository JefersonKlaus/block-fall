"""Rules of the game.

Boards are written as text: B = blue, G = green, R = red, . = empty.
(Peach and purple are only needed for the level rules.)
"""

import random
import unittest
from unittest.mock import patch

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


class RulesTests(unittest.TestCase):
    def test_five_colors_one_per_level(self):
        self.assertEqual(SQUARE_COLORS, (BLUE, GREEN, RED, PEACH, PURPLE))

    def test_a_line_needs_three_squares(self):
        self.assertEqual(MATCH_LENGTH, 3)

    def test_points_three_for_three_then_two_for_each_extra_square(self):
        self.assertEqual([line_points(n) for n in (3, 4, 5, 6, 10)], [3, 5, 7, 9, 17])

    def test_nothing_from_tetris_is_left(self):
        for name in ("TETROMINOES", "Piece", "MAX_SAME_COLOR", "PIECE_COLORS"):
            self.assertFalse(hasattr(game, name), name)
        for name in ("current_piece", "next_piece", "block_ids", "spawn_skipped",
                     "rotate_piece", "drop_piece", "place_piece"):
            self.assertFalse(hasattr(BlockFallEngine(), name), name)


class BoardTests(unittest.TestCase):
    def test_default_board_is_the_middle_5_by_5(self):
        engine = BlockFallEngine(start_squares=0)
        self.assertEqual(DIFFICULTIES[DEFAULT_DIFFICULTY][0], "MIDDLE")
        self.assertEqual((GRID_ROWS, GRID_COLS), (5, 5))
        self.assertEqual((engine.rows, engine.cols), (5, 5))
        self.assertEqual(engine.grid, [[0] * 5 for _ in range(5)])
        self.assertEqual((engine.score, engine.high_score, engine.game_over), (0, 0, False))

    def test_custom_size(self):
        engine = BlockFallEngine(rows=3, cols=5, start_squares=0)
        self.assertEqual(show(engine), ["....."] * 3)

    def test_place_square(self):
        engine = load("...", "...")
        self.assertTrue(engine.place_square(2, 1, RED))
        self.assertEqual(show(engine), ["...", "..R"])

    def test_place_square_rejects_taken_or_outside_cells(self):
        engine = load("B..")
        self.assertFalse(engine.place_square(0, 0, RED))
        self.assertFalse(engine.place_square(3, 0, RED))
        self.assertFalse(engine.place_square(0, -1, RED))
        self.assertEqual(show(engine), ["B.."])

    def test_reset_clears_the_board_and_score_but_keeps_the_best(self):
        engine = load("BG.", "...")
        engine.score = engine.high_score = 9
        engine.game_over = True
        engine.frames = ["old"]
        engine.reset()  # this engine was made with no starting squares
        self.assertEqual(show(engine), ["...", "..."])
        self.assertEqual((engine.score, engine.high_score, engine.game_over), (0, 9, False))
        self.assertEqual((engine.squares(), engine.frames), ({}, []))


class SlideTests(unittest.TestCase):
    """Every square slides as far as it can, like 2048, but never merges."""

    def test_left_and_right(self):
        engine = load("B.G.R", ".R..B")
        self.assertTrue(engine.move_board("left"))
        self.assertEqual(show(engine), ["BGR..", "RB..."])
        self.assertTrue(engine.move_board("right"))
        self.assertEqual(show(engine), ["..BGR", "...RB"])

    def test_up_and_down(self):
        engine = load("B.", "..", "GR", "..", "RB")
        self.assertTrue(engine.move_board("up"))
        self.assertEqual(show(engine), ["BR", "GB", "R.", "..", ".."])
        self.assertTrue(engine.move_board("down"))
        self.assertEqual(show(engine), ["..", "..", "B.", "GR", "RB"])

    def test_same_colors_never_merge(self):
        engine = load("B.B.")
        engine.move_board("right")
        self.assertEqual(show(engine), ["..BB"])
        self.assertEqual(engine.score, 0)

    def test_blocked_move_reports_no_movement(self):
        engine = load("BG..", "R...")
        self.assertFalse(engine.move_board("left"))
        self.assertFalse(engine.move_board("up"))
        self.assertEqual(show(engine), ["BG..", "R..."])

    def test_empty_board_does_not_move(self):
        engine = load("...", "...")
        for direction in DIRECTIONS:
            self.assertFalse(engine.move_board(direction))

    def test_invalid_direction_or_game_over_changes_nothing(self):
        engine = load("B..")
        self.assertFalse(engine.move_board("diagonal"))
        engine.game_over = True
        self.assertFalse(engine.move_board("right"))
        self.assertEqual(show(engine), ["B.."])


class FindLinesTests(unittest.TestCase):
    """Finding lines only looks at the board: nothing is removed or scored."""

    def grid(self, *rows):
        return [[LETTER.get(ch, 0) for ch in row] for row in rows]

    def test_finds_rows_and_columns_of_three_or_more(self):
        lines = find_lines(self.grid("BBB.", "G...", "G...", "GR.."))
        self.assertEqual(sorted(map(sorted, lines)),
                         [[(0, 0), (1, 0), (2, 0)], [(0, 1), (0, 2), (0, 3)]])

    def test_each_line_is_reported_whole(self):
        (line,) = find_lines(self.grid("RRRRR"))
        self.assertEqual(len(line), 5)

    def test_empty_cells_and_pairs_are_not_lines(self):
        self.assertEqual(find_lines(self.grid("...", "BB.", "GRG")), [])

    def test_the_board_is_left_untouched(self):
        grid = self.grid("BBB")
        find_lines(grid)
        self.assertEqual(grid, self.grid("BBB"))


class MatchTests(unittest.TestCase):
    """3 or more squares of one color in a line disappear and score points."""

    def test_three_in_a_row(self):
        engine = load("BBBG.")
        self.assertEqual(engine.clear_matches(), 3)
        self.assertEqual(show(engine), ["...G."])
        self.assertEqual(engine.score, 3)

    def test_three_in_a_column(self):
        engine = load("R.", "R.", "RG")
        engine.clear_matches()
        self.assertEqual(show(engine), ["..", "..", ".G"])
        self.assertEqual(engine.score, 3)

    def test_two_in_a_line_stay(self):
        engine = load("BB.", "G..", "G..")
        self.assertEqual(engine.clear_matches(), 0)
        self.assertEqual(engine.score, 0)

    def test_four_in_a_line_score_3_plus_2(self):
        engine = load("GGGGB")
        engine.clear_matches()
        self.assertEqual(show(engine), ["....B"])
        self.assertEqual(engine.score, 5)

    def test_five_in_a_line_score_3_plus_2_plus_2(self):
        engine = load("RRRRR")
        engine.clear_matches()
        self.assertEqual(engine.score, 7)

    def test_another_color_breaks_the_line(self):
        engine = load("BBGBB")
        self.assertEqual(engine.clear_matches(), 0)

    def test_diagonals_do_not_count(self):
        engine = load("B..", ".B.", "..B")
        self.assertEqual(engine.clear_matches(), 0)

    def test_two_lines_at_once_both_score(self):
        engine = load("BBB", "...", "GGG")
        self.assertEqual(engine.clear_matches(), 6)
        self.assertEqual(engine.score, 6)

    def test_crossing_lines_each_score_and_the_shared_square_goes_once(self):
        engine = load("RRR", "R..", "R..")
        self.assertEqual(engine.clear_matches(), 5)
        self.assertEqual(engine.score, 3 + 3)
        self.assertEqual(show(engine), ["..."] * 3)

    def test_other_squares_stay_where_they_are(self):
        engine = load("G..", "BBB", "..R")
        engine.clear_matches()
        self.assertEqual(show(engine), ["G..", "...", "..R"])

    def test_a_move_that_lines_up_colors_scores(self):
        engine = load("BB.B")
        self.assertTrue(engine.move_board("left"))
        self.assertEqual(show(engine), ["...."])
        self.assertEqual((engine.score, engine.high_score), (3, 3))

    def test_high_score_follows_the_score_but_never_drops(self):
        engine = load("GGG")
        engine.high_score = 100
        engine.clear_matches()
        self.assertEqual((engine.score, engine.high_score), (3, 100))


class SpawnTests(unittest.TestCase):
    """After a move, one new square appears on the opposite side."""

    def spawn(self, engine, direction, pick=first_choice):
        with patch("game.random.choice", side_effect=pick) as choice:
            self.assertTrue(engine.spawn_square(direction))
        return choice.call_args_list

    def test_after_right_it_appears_on_the_left_edge(self):
        engine = load("..", "..", "..")
        calls = self.spawn(engine, "right")
        self.assertEqual(calls[0].args[0], [(0, 0), (0, 1), (0, 2)])

    def test_after_left_it_appears_on_the_right_edge(self):
        calls = self.spawn(load("...", "..."), "left")
        self.assertEqual(calls[0].args[0], [(2, 0), (2, 1)])

    def test_after_down_it_appears_on_the_top_edge(self):
        calls = self.spawn(load("...", "..."), "down")
        self.assertEqual(calls[0].args[0], [(0, 0), (1, 0), (2, 0)])

    def test_after_up_it_appears_on_the_bottom_edge(self):
        calls = self.spawn(load("...", "..."), "up")
        self.assertEqual(calls[0].args[0], [(0, 1), (1, 1), (2, 1)])

    def test_taken_cells_on_the_edge_are_skipped(self):
        engine = load("B..", "...", "G..")
        calls = self.spawn(engine, "right")
        self.assertEqual(calls[0].args[0], [(0, 1)])

    def test_full_edge_means_the_nearest_line_inward(self):
        engine = load("B..", "G..", "R..")
        calls = self.spawn(engine, "right")
        self.assertEqual(calls[0].args[0], [(1, 0), (1, 1), (1, 2)])

    def test_color_is_random_among_the_unlocked_colors(self):
        engine = load("...")
        calls = self.spawn(engine, "down", pick=lambda v: v[-1])
        self.assertEqual(tuple(calls[1].args[0]), (BLUE, GREEN))
        self.assertEqual(show(engine), ["..G"])

    def test_new_squares_only_use_unlocked_colors(self):
        for score, expected in ((0, {BLUE, GREEN}), (50, {BLUE, GREEN, RED}),
                                (350, set(SQUARE_COLORS))):
            seen = set()
            for _ in range(120):
                engine = BlockFallEngine(rows=1, cols=1, start_squares=0)
                engine.score = score
                engine.spawn_square("down")
                seen.add(engine.grid[0][0])
            self.assertEqual(seen, expected, score)

    def test_position_along_the_edge_is_random(self):
        engine = load("...", "...", "...")
        self.spawn(engine, "right", pick=lambda v: v[1])
        self.assertEqual([row[0] != 0 for row in engine.grid], [False, True, False])

    def test_exactly_one_square_is_added(self):
        engine = load("...", "...")
        engine.spawn_square("left")
        self.assertEqual(len(engine.squares()), 1)

    def test_a_new_square_can_complete_a_line(self):
        engine = load(".BB")
        self.spawn(engine, "right", pick=color_then_first(BLUE))
        self.assertEqual(show(engine), ["..."])
        self.assertEqual(engine.score, 3)

    def test_no_free_cell_no_square(self):
        engine = load("BG", "GB")
        self.assertFalse(engine.spawn_square("left"))
        self.assertEqual(show(engine), ["BG", "GB"])


class PlayMoveTests(unittest.TestCase):
    """One press: slide everything, then add one square on the other side."""

    def test_move_first_then_the_new_square(self):
        engine = load("B..", "...")
        with patch("game.random.choice", side_effect=lambda v: v[-1]):
            self.assertTrue(engine.play_move("right"))
        # B slid right, then a square in the last unlocked color (green)
        # appeared on the left edge, last row.
        self.assertEqual(show(engine), ["..B", "G.."])

    def test_every_press_adds_one_square_even_if_nothing_moves(self):
        engine = load("....", "....")
        colors = iter([BLUE, GREEN, GREEN, BLUE])  # never 3 in a line: no match
        pick = lambda v: next(colors) if is_colors(v) else v[0]  # noqa: E731
        with patch("game.random.choice", side_effect=pick):
            for count in range(1, 5):
                engine.play_move("up")
                self.assertEqual(len(engine.squares()), count)
        self.assertEqual(show(engine), ["BG..", "GB.."])

    def test_invalid_direction_does_nothing(self):
        engine = load("...")
        self.assertFalse(engine.play_move("diagonal"))
        self.assertEqual(engine.squares(), {})

    def test_no_moves_after_game_over(self):
        engine = load("B..")
        engine.game_over = True
        self.assertFalse(engine.play_move("right"))
        self.assertEqual(show(engine), ["B.."])


class GameOverTests(unittest.TestCase):
    """The game only ends when the board is full."""

    def test_board_filled_by_the_last_square_is_game_over(self):
        engine = load("BGR", "GRB", "RB.")
        with patch("game.random.choice", side_effect=color_then_first(GREEN)):
            engine.play_move("left")  # nothing moves; the free cell stays free on the right
        self.assertEqual(show(engine), ["BGR", "GRB", "RBG"])
        self.assertTrue(engine.game_over)

    def test_not_over_with_free_squares(self):
        engine = load("BGR", "GR.", "RB.")
        with patch("game.random.choice", side_effect=color_then_first(BLUE)):
            engine.play_move("left")
        self.assertEqual(sum(v == 0 for row in engine.grid for v in row), 1)
        self.assertFalse(engine.game_over)

    def test_a_match_on_the_last_free_cell_keeps_the_game_going(self):
        engine = load("BGR", "GRB", "BB.")
        with patch("game.random.choice", side_effect=color_then_first(BLUE)):
            engine.play_move("left")
        self.assertEqual(show(engine), ["BGR", "GRB", "..."])
        self.assertFalse(engine.game_over)

    def test_full_board_is_game_over(self):
        engine = load("BG", "GB")
        self.assertTrue(engine.play_move("right"))
        self.assertTrue(engine.game_over)


class SquareIdentityTests(unittest.TestCase):
    """Every square keeps one id for its whole life, so the UI can animate it."""

    def test_squares_lists_position_and_color_by_id(self):
        engine = load("B.", ".R")
        self.assertEqual(sorted(engine.squares().values()), [(0, 0, BLUE), (1, 1, RED)])

    def test_ids_travel_with_their_squares(self):
        engine = load("B.G.", "....")
        before = engine.squares()
        engine.move_board("right")
        engine.move_board("down")
        after = engine.squares()
        self.assertEqual(set(after), set(before))
        self.assertEqual(sorted(after.values()), [(2, 1, BLUE), (3, 1, GREEN)])

    def test_ids_are_never_reused(self):
        engine = load("GGG", "...")
        gone = set(engine.squares())
        engine.clear_matches()
        with patch("game.random.choice", side_effect=color_then_first(BLUE)):
            engine.spawn_square("down")
            engine.spawn_square("down")
        new = set(engine.squares())
        self.assertEqual(len(new), 2)
        self.assertTrue(all(i > max(gone) for i in new))

    def test_cleared_squares_lose_their_ids(self):
        engine = load("GGG", "R..")
        red = [i for i, (_, _, c) in engine.squares().items() if c == RED]
        engine.clear_matches()
        self.assertEqual(list(engine.squares()), red)


class FrameTests(unittest.TestCase):
    """Each press records what happened, step by step, for the animation."""

    def test_slide_then_match_then_spawn(self):
        engine = load("BB.B.", ".....")
        engine.play_move("left")
        self.assertEqual([f.kind for f in engine.frames], ["slide", "match", "spawn"])
        self.assertTrue(all(isinstance(f, Frame) for f in engine.frames))

    def test_slide_frame_shows_the_new_places_before_matches(self):
        engine = load("BB.B.", ".....")
        engine.play_move("left")
        slide = engine.frames[0]
        self.assertEqual(sorted(slide.squares.values()), [(0, 0, BLUE), (1, 0, BLUE), (2, 0, BLUE)])
        self.assertEqual(slide.gold, frozenset())

    def test_match_frame_marks_the_matched_squares_gold(self):
        engine = load("BB.B.", ".....")
        engine.play_move("left")
        match = engine.frames[1]
        self.assertEqual(match.gold, frozenset(match.squares))
        self.assertTrue(match.gold.isdisjoint(engine.squares()))

    def test_spawn_frame_shows_the_new_square(self):
        engine = load("G....", ".....")
        engine.play_move("right")
        spawn = engine.frames[-1]
        self.assertEqual(spawn.kind, "spawn")
        self.assertEqual(spawn.squares, engine.squares())
        self.assertEqual(len(spawn.squares), 2)

    def test_no_slide_frame_when_nothing_moves(self):
        engine = load("G..", "...")
        engine.play_move("left")
        self.assertEqual([f.kind for f in engine.frames], ["spawn"])

    def test_match_made_by_the_new_square_comes_after_its_spawn_frame(self):
        engine = load(".RR", "...")
        with patch("game.random.choice", side_effect=color_then_first(RED)):
            engine.play_move("right")
        self.assertEqual([f.kind for f in engine.frames], ["spawn", "match"])

    def test_each_press_starts_with_no_frames(self):
        engine = load("G..")
        engine.frames = ["stale"]
        engine.play_move("right")
        self.assertNotIn("stale", engine.frames)

    def test_no_frames_after_game_over(self):
        engine = load("G..")
        engine.frames = ["stale"]
        engine.game_over = True
        engine.play_move("left")
        self.assertEqual(engine.frames, [])


class LevelTests(unittest.TestCase):
    """Start with 2 colors; unlock one at 50, 150 (50 + 100), 350 (150 + 200)."""

    def test_unlock_scores(self):
        self.assertEqual(UNLOCK_SCORES, (0, 0, 50, 150, 350))

    def test_colors_unlocked_by_score(self):
        cases = {0: 2, 49: 2, 50: 3, 149: 3, 150: 4, 349: 4, 350: 5, 10_000: 5}
        for score, count in cases.items():
            engine = BlockFallEngine(start_squares=0)
            engine.score = score
            self.assertEqual(engine.unlocked_colors(), SQUARE_COLORS[:count], score)

    def test_game_starts_with_two_colors(self):
        self.assertEqual(BlockFallEngine().unlocked_colors(), (BLUE, GREEN))

    def test_a_new_color_can_be_used_right_after_it_is_unlocked(self):
        engine = load("BB.B.")
        engine.score = 48
        with patch("game.random.choice", side_effect=first_choice) as choice:
            engine.play_move("left")  # the line scores 3: 48 -> 51
        self.assertEqual(engine.score, 51)
        color_calls = [c.args[0] for c in choice.call_args_list if is_colors(c.args[0])]
        self.assertEqual(tuple(color_calls[-1]), (BLUE, GREEN, RED))

    def test_a_new_game_locks_the_colors_again(self):
        engine = BlockFallEngine(start_squares=0)
        engine.score = 400
        engine.reset()
        self.assertEqual(engine.unlocked_colors(), (BLUE, GREEN))


class StartSquaresTests(unittest.TestCase):
    """A new game already has some squares on the board."""

    def count(self, engine):
        return len(engine.squares())

    def test_a_new_game_fills_about_10_percent_of_the_grid(self):
        self.assertEqual(START_FILL, 0.10)
        for rows, cols, expected in ((12, 12, 14), (8, 8, 6), (6, 6, 4), (10, 10, 10)):
            with self.subTest(size=(rows, cols)):
                self.assertEqual(self.count(BlockFallEngine(rows=rows, cols=cols)), expected)

    def test_starting_squares_use_only_the_two_starting_colors(self):
        for _ in range(20):
            colors = {c for _, _, c in BlockFallEngine().squares().values()}
            self.assertLessEqual(colors, {BLUE, GREEN})

    def test_starting_squares_never_form_a_line(self):
        for _ in range(50):
            engine = BlockFallEngine()
            self.assertEqual(_copy(engine).clear_matches(), 0)
            self.assertEqual(engine.score, 0)

    def test_starting_squares_are_placed_randomly(self):
        layouts = {frozenset((c, r) for c, r, _ in BlockFallEngine().squares().values())
                   for _ in range(5)}
        self.assertGreater(len(layouts), 1)

    def test_reset_puts_new_starting_squares_on_the_board(self):
        engine = BlockFallEngine(rows=10, cols=10)
        engine.play_move("left")
        engine.reset()
        self.assertEqual(self.count(engine), 10)
        self.assertEqual((engine.score, engine.frames), (0, []))

    def test_an_explicit_count_still_wins(self):
        self.assertEqual(self.count(BlockFallEngine(rows=8, cols=8, start_squares=3)), 3)

    def test_starting_squares_fit_small_boards(self):
        engine = BlockFallEngine(rows=2, cols=2, start_squares=10)
        self.assertEqual(self.count(engine), 4)
        self.assertEqual(_copy(engine).clear_matches(), 0)

    def test_a_cell_that_would_complete_a_line_is_left_empty(self):
        # Both colors would make 3 in a line at (2, 2): that cell must stay empty.
        engine = load("..B", "..B", "GG.")
        with patch("game.random.shuffle"):  # fill cells in reading order
            engine._add_starting_squares(9)
        self.assertEqual(engine.grid[2][2], 0)
        self.assertEqual(_copy(engine).clear_matches(), 0)


class RandomPlayTests(unittest.TestCase):
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
                    self.assertEqual(BlockFallEngine.clear_matches(_copy(engine)), 0)
                    # Each removed square is worth at least 1 point, lines at least 3.
                    self.assertTrue(points >= removed and (removed == 0) == (points == 0))
                    # Only unlocked colors are ever on the board.
                    colors = {v for row in engine.grid for v in row if v}
                    self.assertLessEqual(colors, set(engine.unlocked_colors()))
                    # Game over exactly when the board is full.
                    full = all(all(row) for row in engine.grid)
                    self.assertEqual(engine.game_over, full)
        finally:
            random.setstate(state)


def _copy(engine):
    clone = BlockFallEngine(rows=engine.rows, cols=engine.cols, start_squares=0)
    clone.grid = [row[:] for row in engine.grid]
    clone.square_ids = [row[:] for row in engine.square_ids]
    return clone
