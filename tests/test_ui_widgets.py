"""The basic pieces: squares and the logo."""

import unittest

from config import (
    BLUE,
    CELL_SIZE,
    COLOR_BOARD_BG,
    COLOR_EMPTY,
    COLOR_GOLD,
    GREEN,
    PEACH,
    PURPLE,
    RED,
    TILE_COLORS,
)
from game import SQUARE_COLORS
from tests.helpers import lightness
import flet as ft

from config import COLOR_MUTED_TEXT, HEADER_BLOCK_HEIGHT, HEADER_BLOCK_WIDTH
from ui.widgets import create_block, create_confirm_dialog, create_logo, create_tile


class TileTests(unittest.TestCase):
    def test_tile_uses_requested_dimensions(self):
        tile = create_tile(BLUE, width=20, height=20)
        self.assertEqual((tile.width, tile.height), (20, 20))

    def test_default_tile_size_is_cell_size(self):
        tile = create_tile(BLUE)
        self.assertEqual((tile.width, tile.height), (CELL_SIZE, CELL_SIZE))

    def test_empty_tile_uses_empty_color(self):
        self.assertEqual(create_tile(0).bgcolor, COLOR_EMPTY)

    def test_every_configured_value_uses_its_color(self):
        for value, color in TILE_COLORS.items():
            self.assertEqual(create_tile(value).bgcolor, color)

    def test_tiles_use_five_pastel_colors(self):
        self.assertEqual(
            TILE_COLORS,
            {0: COLOR_EMPTY, BLUE: "#8EC5FF", GREEN: "#9EE5B8", RED: "#FF9AA2",
             PEACH: "#FFC89A", PURPLE: "#C9A7F5"},
        )

    def test_unknown_value_falls_back_to_board_background(self):
        self.assertEqual(create_tile(256).bgcolor, COLOR_BOARD_BG)

    def test_gold_tile(self):
        self.assertEqual(create_tile(RED, gold=True).bgcolor, COLOR_GOLD)
        self.assertNotIn(COLOR_GOLD, TILE_COLORS.values())


class LogoTests(unittest.TestCase):
    def test_logo_is_big_with_the_name_on_two_lines(self):
        mark, name = create_logo().controls
        block, fall = name.controls
        self.assertEqual((block.value, fall.value), ("Block", "Fall"))
        self.assertGreaterEqual(block.size, 28)
        self.assertEqual(block.size, fall.size)
        self.assertNotEqual(block.color, fall.color)
        for text in (block, fall):
            self.assertLess(lightness(text.color), 0.6)  # readable on the cream background

    def test_no_gap_between_block_and_fall(self):
        _, name = create_logo().controls
        self.assertEqual(name.spacing, 0)
        for text in name.controls:
            self.assertLessEqual(text.style.height, 0.95)  # tight line height

    def test_mark_is_a_big_mini_board_with_a_gold_line_of_three(self):
        mark, _ = create_logo().controls
        rows = [[cell.bgcolor for cell in row.controls] for row in mark.controls]
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(len(row) == 3 for row in rows))
        self.assertEqual(rows[1], [COLOR_GOLD] * 3)  # the game: line up 3
        self.assertTrue(set(rows[0] + rows[2]) <= {TILE_COLORS[c] for c in SQUARE_COLORS})
        self.assertGreaterEqual(mark.controls[0].controls[0].width, 16)


class BlockTests(unittest.TestCase):
    def test_a_block_is_a_small_label_above_a_value(self):
        value = ft.Text("7")
        block = create_block("SCORE", value)
        label, shown = block.content.controls
        self.assertEqual((label.value, label.color), ("SCORE", COLOR_MUTED_TEXT))
        self.assertIs(shown, value)
        self.assertEqual((block.width, block.height), (HEADER_BLOCK_WIDTH, HEADER_BLOCK_HEIGHT))
        self.assertEqual(block.bgcolor, COLOR_BOARD_BG)


class ConfirmDialogTests(unittest.TestCase):
    def test_a_modal_question_with_two_block_buttons(self):
        clicks = []
        dialog = create_confirm_dialog(
            "Restart the game?", "You will lose the current game.", "CANCEL", "RESTART", "#7FB3F5",
            on_cancel=lambda e: clicks.append("cancel"), on_ok=lambda e: clicks.append("ok"),
        )
        self.assertTrue(dialog.modal)
        self.assertEqual(dialog.title.value, "Restart the game?")
        self.assertEqual(dialog.content.value, "You will lose the current game.")
        cancel, ok = dialog.actions
        self.assertEqual([(b.content.value, b.bgcolor) for b in (cancel, ok)],
                         [("CANCEL", COLOR_BOARD_BG), ("RESTART", "#7FB3F5")])
        cancel.on_click(None)
        ok.on_click(None)
        self.assertEqual(clicks, ["cancel", "ok"])

