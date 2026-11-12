import unittest

from ui import BlockFallView, create_piece_preview, create_tile
from game import Piece


class MockPage:
    def add(self, control):
        self.controls = [control]

    def update(self):
        self.updated = True


class UITests(unittest.TestCase):

    def setUp(self):
        self.page = MockPage()
        self.view = BlockFallView(self.page)

    def test_view_builds_one_layout(self):
        self.assertEqual(len(self.page.controls), 1)

    def test_refresh_updates_page(self):
        self.view.refresh()
        self.assertTrue(self.page.updated)

    def test_rotate_handler_changes_piece(self):
        before = self.view.game.current_piece.cells[:]
        self.view._handle_rotate(None)
        self.assertNotEqual(self.view.game.current_piece.cells, before)

    def test_drop_handler_places_piece(self):
        self.view._handle_drop(None)
        occupied = sum(cell != 0 for row in self.view.game.grid for cell in row)
        self.assertEqual(occupied, 4)

    def test_move_handler_accepts_horizontal_directions(self):
        self.view._handle_drop(None)
        self.view._handle_move("left")
        self.view._handle_move("right")
        self.assertFalse(self.view.game.game_over)

    def test_tile_uses_requested_dimensions(self):
        tile = create_tile(2, width=20, height=20)
        self.assertEqual((tile.width, tile.height), (20, 20))

    def test_preview_contains_piece_cells(self):
        preview = create_piece_preview(Piece([(0, 0), (1, 0), (0, 1), (1, 1)], 2))
        self.assertEqual(len(preview.controls), 2)

    def test_game_over_refresh_shows_game_over_message(self):
        self.view.game.game_over = True
        self.view.refresh()
        self.assertEqual(self.view.status_display.value, "GAME OVER! Tap Restart.")

    def test_normal_refresh_shows_drop_message(self):
        self.view.refresh()
        self.assertEqual(
            self.view.status_display.value,
            "Rotate the piece, then tap Drop Piece.",
        )

    def test_preview_dimensions_match_piece_shape(self):
        piece = Piece([(0, 0), (0, 1), (0, 2), (1, 2)], 8)
        preview = create_piece_preview(piece)
        self.assertEqual(len(preview.controls), 3)
        self.assertEqual(len(preview.controls[0].controls), 2)

    def test_empty_tile_uses_empty_color(self):
        tile = create_tile(0)
        self.assertEqual(tile.bgcolor, "#3f3f46")

    def test_non_empty_tile_uses_tile_color(self):
        tile = create_tile(16)
        self.assertEqual(tile.bgcolor, "#fb7185")

    def test_drop_refreshes_page(self):
        self.view._handle_drop(None)
        self.assertTrue(self.page.updated)

    def test_move_refreshes_page(self):
        self.view._handle_move("left")
        self.assertTrue(self.page.updated)
