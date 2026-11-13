"""The grid on screen."""

import unittest

from config import BLUE, BOARD_PADDING, CELL_SPACING, COLOR_EMPTY, COLOR_GOLD, RED, TILE_COLORS
from ui.board import SIDE_MARGIN, BoardView, fit_cell


class FitCellTests(unittest.TestCase):
    def test_columns_fill_the_width(self):
        for width, cols in ((360, 6), (412, 5), (320, 4)):
            cell = fit_cell(width, cols)
            self.assertAlmostEqual(cols * cell + (cols - 1) * CELL_SPACING + SIDE_MARGIN, width)

    def test_unknown_width_assumes_a_small_phone(self):
        self.assertEqual(fit_cell(None, 6), fit_cell(320, 6))


class BoardViewTests(unittest.TestCase):
    def setUp(self):
        self.board = BoardView(3, 4, 360)

    def test_empty_grid_of_slots(self):
        self.assertEqual(len(self.board.slots), 12)
        self.assertTrue(all(s.bgcolor == COLOR_EMPTY for s in self.board.slots))
        self.assertEqual(self.board.stack.controls, self.board.slots)
        self.assertEqual(self.board.outer_width, self.board.stack.width + 2 * BOARD_PADDING)
        self.assertIs(self.board.frame.content, self.board.stack)

    def test_show_adds_moves_and_removes_tiles(self):
        self.board.show({1: (0, 0, BLUE), 2: (1, 0, RED)})
        tile = self.board.tiles[1]
        self.board.show({1: (3, 2, BLUE)})
        self.assertIs(self.board.tiles[1], tile)  # same tile: it slides
        step = self.board.cell + CELL_SPACING
        self.assertEqual((tile.left, tile.top), (3 * step, 2 * step))
        self.assertNotIn(2, self.board.tiles)
        self.assertEqual(len(self.board.stack.controls), 12 + 1)

    def test_gold_and_pop(self):
        new = self.board.show({5: (0, 0, RED)}, gold=frozenset({5}), pop=True)
        self.assertEqual((new[0].bgcolor, new[0].scale), (COLOR_GOLD, 0))
        self.board.show({5: (0, 0, RED)})
        self.assertEqual(self.board.tiles[5].bgcolor, TILE_COLORS[RED])

    def test_rebuild_changes_the_grid_size(self):
        self.board.show({1: (0, 0, BLUE)})
        self.board.rebuild(5, 5)
        self.assertEqual((len(self.board.slots), self.board.tiles), (25, {}))

    def test_resize_keeps_squares_in_place(self):
        self.board.show({1: (3, 2, BLUE)})
        self.board.resize(412, {1: (3, 2, BLUE)})
        self.assertEqual(self.board.cell, fit_cell(412, 4))
        tile = self.board.tiles[1]
        self.assertAlmostEqual(tile.left + tile.width, self.board.stack.width)
