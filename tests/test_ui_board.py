"""The grid on screen."""

import pytest

from config import BLUE, BOARD_PADDING, CELL_SPACING, COLOR_EMPTY, COLOR_GOLD, RED, TILE_COLORS
from ui.board import SIDE_MARGIN, BoardView, fit_cell


class TestFitCell:
    def test_columns_fill_the_width(self):
        for width, cols in ((360, 6), (412, 5), (320, 4)):
            cell = fit_cell(width, cols, cols, None)
            assert cols * cell + (cols - 1) * CELL_SPACING + SIDE_MARGIN == pytest.approx(width)

    def test_unknown_width_assumes_a_small_phone(self):
        assert fit_cell(None, 6, 6, None) == fit_cell(320, 6, 6, None)

    def test_a_height_limit_makes_the_squares_smaller(self):
        cell = fit_cell(360, 5, 5, 200)
        assert 5 * cell + 4 * CELL_SPACING == pytest.approx(200)
        assert cell < fit_cell(360, 5, 5, None)

    def test_a_roomy_height_limit_changes_nothing(self):
        assert fit_cell(360, 5, 5, 2000) == fit_cell(360, 5, 5, None)

    def test_squares_stay_drawable_on_an_absurdly_small_window(self):
        assert fit_cell(360, 5, 5, -50) == 1


@pytest.fixture
def board():
    return BoardView(3, 4, 360)


class TestBoardView:
    def test_empty_grid_of_slots(self, board):
        assert len(board.slots) == 12
        assert all(s.bgcolor == COLOR_EMPTY for s in board.slots)
        assert board.stack.controls == board.slots
        assert board.outer_width == board.stack.width + 2 * BOARD_PADDING
        assert board.frame.content is board.stack

    def test_show_adds_moves_and_removes_tiles(self, board):
        board.show({1: (0, 0, BLUE), 2: (1, 0, RED)})
        tile = board.tiles[1]
        board.show({1: (3, 2, BLUE)})
        assert board.tiles[1] is tile  # same tile: it slides
        step = board.cell + CELL_SPACING
        assert (tile.left, tile.top) == (3 * step, 2 * step)
        assert 2 not in board.tiles
        assert len(board.stack.controls) == 12 + 1

    def test_gold_and_pop(self, board):
        new = board.show({5: (0, 0, RED)}, gold=frozenset({5}), pop=True)
        assert (new[0].bgcolor, new[0].scale) == (COLOR_GOLD, 0)
        board.show({5: (0, 0, RED)})
        assert board.tiles[5].bgcolor == TILE_COLORS[RED]

    def test_rebuild_changes_the_grid_size(self, board):
        board.show({1: (0, 0, BLUE)})
        board.rebuild(5, 5)
        assert (len(board.slots), board.tiles) == (25, {})

    def test_resize_keeps_squares_in_place(self, board):
        board.show({1: (3, 2, BLUE)})
        board.resize(412, {1: (3, 2, BLUE)}, None)
        assert board.cell == fit_cell(412, 4, 3, None)
        tile = board.tiles[1]
        assert tile.left + tile.width == pytest.approx(board.stack.width)
