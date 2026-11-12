import unittest
from unittest.mock import patch
from game import BlockFallEngine, Piece, TETROMINOES
class PieceTests(unittest.TestCase):
    def test_piece_reports_dimensions(self):
        piece = Piece([(0, 0), (1, 0), (0, 1), (1, 1)], 2)
        self.assertEqual(piece.width, 2)
        self.assertEqual(piece.height, 2)
    def test_piece_rotation_keeps_four_cells(self):
        piece = Piece([(0, 0), (1, 0), (2, 0), (3, 0)], 2)
        piece.rotate()
        self.assertEqual(piece.cells, [(0, 0), (0, 1), (0, 2), (0, 3)])
        self.assertEqual(piece.width, 1)
        self.assertEqual(piece.height, 4)
    def test_piece_rotation_preserves_coordinates_origin(self):
        piece = Piece([(1, 0), (0, 1), (1, 1), (2, 1)], 8)
        piece.rotate()
        self.assertGreaterEqual(min(column for column, _ in piece.cells), 0)
        self.assertGreaterEqual(min(row for _, row in piece.cells), 0)
        self.assertEqual(len(piece.cells), 4)

    def test_four_rotations_restore_line_piece(self):
        piece = Piece([(0, 0), (1, 0), (2, 0), (3, 0)], 2)
        original = piece.cells[:]
        for _ in range(4):
            piece.rotate()
        self.assertEqual(piece.cells, original)

    def test_square_piece_keeps_dimensions_after_rotation(self):
        piece = Piece([(0, 0), (1, 0), (0, 1), (1, 1)], 4)
        piece.rotate()
        self.assertEqual((piece.width, piece.height), (2, 2))
        self.assertEqual(len(set(piece.cells)), 4)

    def test_piece_color_is_preserved_when_rotated(self):
        piece = Piece([(0, 0), (1, 0), (0, 1), (1, 1)], 64)
        piece.rotate()
        self.assertEqual(piece.color, 64)
class EngineSetupTests(unittest.TestCase):
    def test_engine_starts_with_square_empty_board(self):
        engine = BlockFallEngine()
        self.assertEqual((engine.rows, engine.cols), (8, 8))
        self.assertEqual(len(engine.grid), 8)
        self.assertTrue(all(len(row) == 8 for row in engine.grid))
        self.assertTrue(all(cell == 0 for row in engine.grid for cell in row))
        self.assertFalse(engine.game_over)
    def test_generated_pieces_are_valid_tetrominoes(self):
        engine = BlockFallEngine()
        self.assertEqual(len(engine.current_piece.cells), 4)
        self.assertEqual(len(engine.next_piece.cells), 4)
        self.assertIn(tuple(engine.current_piece.cells), TETROMINOES)
    def test_reset_clears_board_and_score(self):
        engine = BlockFallEngine()
        engine.grid[-1][0] = 4
        engine.score = 100
        engine.high_score = 100
        engine.game_over = True
        engine.reset()
        self.assertEqual(engine.score, 0)
        self.assertEqual(engine.high_score, 100)
        self.assertFalse(engine.game_over)
        self.assertTrue(all(cell == 0 for row in engine.grid for cell in row))

    def test_custom_board_dimensions_are_supported(self):
        engine = BlockFallEngine(rows=4, cols=6)
        self.assertEqual(len(engine.grid), 4)
        self.assertTrue(all(len(row) == 6 for row in engine.grid))

    def test_reset_generates_new_piece_queue(self):
        engine = BlockFallEngine()
        current = engine.current_piece
        upcoming = engine.next_piece
        engine.reset()
        self.assertIsNot(engine.current_piece, current)
        self.assertIsNot(engine.next_piece, upcoming)
class EngineDropTests(unittest.TestCase):
    def test_drop_places_exactly_four_cells(self):
        engine = BlockFallEngine()
        self.assertTrue(engine.drop_piece())
        occupied = sum(cell != 0 for row in engine.grid for cell in row)
        self.assertEqual(occupied, 4)
    def test_drop_uses_a_valid_random_column(self):
        engine = BlockFallEngine()
        with patch("game.random.choice", side_effect=lambda values: values[0]) as choice:
            self.assertTrue(engine.drop_piece())
            choice.assert_called()
        occupied_columns = {
            column
            for row in engine.grid
            for column, value in enumerate(row)
            if value
        }
        self.assertLessEqual(max(occupied_columns), 3)
    def test_drop_advances_to_next_piece(self):
        engine = BlockFallEngine()
        expected = engine.next_piece
        engine.drop_piece()
        self.assertIs(engine.current_piece, expected)
    def test_rotated_piece_can_be_dropped(self):
        engine = BlockFallEngine()
        engine.rotate_piece()
        self.assertTrue(engine.drop_piece())
        occupied = sum(cell != 0 for row in engine.grid for cell in row)
        self.assertEqual(occupied, 4)
    def test_drop_on_full_spawn_area_ends_game(self):
        engine = BlockFallEngine()
        engine.grid = [[9 for _ in range(engine.cols)] for _ in range(engine.rows)]
        self.assertFalse(engine.drop_piece())
        self.assertTrue(engine.game_over)

    def test_drop_fails_after_game_over_without_changing_board(self):
        engine = BlockFallEngine()
        engine.game_over = True
        before = [row[:] for row in engine.grid]
        self.assertFalse(engine.drop_piece())
        self.assertEqual(engine.grid, before)

    def test_drop_stacks_pieces_without_overlapping(self):
        engine = BlockFallEngine()
        with patch("game.random.choice", side_effect=lambda values: values[0]):
            self.assertTrue(engine.drop_piece())
            self.assertTrue(engine.drop_piece())
        occupied = sum(cell != 0 for row in engine.grid for cell in row)
        self.assertEqual(occupied, 8)
class EngineBoardTests(unittest.TestCase):
    def test_gravity_moves_cells_to_bottom(self):
        engine = BlockFallEngine()
        engine.grid[0][0] = 2
        engine.grid[3][0] = 4
        engine.apply_gravity()
        self.assertEqual([engine.grid[row][0] for row in range(8)], [0, 0, 0, 0, 0, 0, 2, 4])
    def test_left_movement_compacts_values(self):
        engine = BlockFallEngine()
        engine.grid[7] = [0, 2, 0, 4, 0, 0, 0, 0]
        self.assertTrue(engine.move_board("left"))
        self.assertEqual(engine.grid[7], [2, 4, 0, 0, 0, 0, 0, 0])
    def test_right_movement_compacts_values(self):
        engine = BlockFallEngine()
        engine.grid[7] = [2, 0, 4, 0, 0, 0, 0, 0]
        self.assertTrue(engine.move_board("right"))
        self.assertEqual(engine.grid[7], [0, 0, 0, 0, 0, 0, 2, 4])
    def test_equal_values_merge_and_score(self):
        engine = BlockFallEngine()
        engine.grid[7] = [2, 2, 0, 0, 0, 0, 0, 0]
        self.assertTrue(engine.move_board("left"))
        self.assertEqual(engine.grid[7][0], 4)
        self.assertEqual(engine.score, 4)
    def test_invalid_direction_does_not_change_board(self):
        engine = BlockFallEngine()
        before = [row[:] for row in engine.grid]
        self.assertFalse(engine.move_board("diagonal"))
        self.assertEqual(engine.grid, before)

    def test_empty_board_does_not_move(self):
        engine = BlockFallEngine()
        self.assertFalse(engine.move_board("left"))
        self.assertFalse(engine.move_board("right"))
        self.assertFalse(engine.move_board("up"))
        self.assertFalse(engine.move_board("down"))

    def test_down_movement_preserves_bottom_alignment(self):
        engine = BlockFallEngine()
        engine.grid[0][0] = 2
        self.assertTrue(engine.move_board("down"))
        self.assertEqual(engine.grid[-1][0], 2)

    def test_multiple_complete_rows_are_cleared(self):
        engine = BlockFallEngine()
        engine.grid[-2] = [2] * engine.cols
        engine.grid[-1] = [4] * engine.cols
        engine.process_complete_lines()
        self.assertEqual(engine.grid[-2:], [[0] * engine.cols, [0] * engine.cols])
        self.assertEqual(engine.score, 160)

    def test_high_score_is_not_reduced_by_reset(self):
        engine = BlockFallEngine()
        engine.score = 250
        engine._update_high_score()
        engine.reset()
        self.assertEqual(engine.high_score, 250)

    def test_merge_values_pads_to_board_width(self):
        engine = BlockFallEngine()
        self.assertEqual(engine._merge_values([2, 2, 4]), [4, 4, 0, 0, 0, 0, 0, 0])

    def test_can_place_rejects_out_of_bounds_cells(self):
        engine = BlockFallEngine()
        piece = Piece([(0, 0), (1, 0), (2, 0), (3, 0)], 2)
        self.assertFalse(engine._can_place(piece, -1, 0))
        self.assertFalse(engine._can_place(piece, 5, 0))
        self.assertFalse(engine._can_place(piece, 0, 8))

    def test_can_place_rejects_occupied_cell(self):
        engine = BlockFallEngine()
        engine.grid[0][0] = 2
        piece = Piece([(0, 0), (1, 0), (2, 0), (3, 0)], 2)
        self.assertFalse(engine._can_place(piece, 0, 0))
    def test_vertical_movement_is_supported(self):
        engine = BlockFallEngine()
        engine.grid[7][0] = 2
        engine.grid[6][0] = 2
        self.assertTrue(engine.move_board("up"))
        self.assertEqual(engine.grid[-1][0], 4)
    def test_complete_row_is_cleared_and_scored(self):
        engine = BlockFallEngine()
        engine.grid[-1] = [2] * engine.cols
        engine.process_complete_lines()
        self.assertEqual(engine.grid[-1], [0] * engine.cols)
        self.assertEqual(engine.score, 80)
        self.assertEqual(engine.high_score, 80)
    def test_game_over_blocks_future_moves(self):
        engine = BlockFallEngine()
        engine.game_over = True
        self.assertFalse(engine.move_board("left"))
        self.assertFalse(engine.drop_piece())
