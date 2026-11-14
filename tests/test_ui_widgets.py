"""The basic pieces: squares, blocks, the logo, dialogs."""

import flet as ft

from config import (
    BLUE,
    COLOR_BOARD_BG,
    COLOR_EMPTY,
    COLOR_GOLD,
    COLOR_MUTED_TEXT,
    GREEN,
    HEADER_BLOCK_HEIGHT,
    PEACH,
    PURPLE,
    RED,
    TILE_COLORS,
)
from game import SQUARE_COLORS
from tests.helpers import lightness
from ui.widgets import create_block, create_confirm_dialog, create_logo, create_tile


class TestTile:
    def test_empty_tile_uses_empty_color(self):
        assert create_tile(0).bgcolor == COLOR_EMPTY

    def test_every_configured_value_uses_its_color(self):
        for value, color in TILE_COLORS.items():
            assert create_tile(value).bgcolor == color

    def test_tiles_use_five_pastel_colors(self):
        assert TILE_COLORS == {
            0: COLOR_EMPTY, BLUE: "#8EC5FF", GREEN: "#9EE5B8", RED: "#FF9AA2",
            PEACH: "#FFC89A", PURPLE: "#C9A7F5",
        }

    def test_gold_is_never_a_square_color(self):
        assert COLOR_GOLD not in TILE_COLORS.values()


class TestLogo:
    def test_logo_is_big_with_the_name_on_two_lines(self):
        mark, name = create_logo().controls
        block, fall = name.controls
        assert (block.value, fall.value) == ("Block", "Fall")
        assert block.size >= 28
        assert block.size == fall.size
        assert block.color != fall.color
        for text in (block, fall):
            assert lightness(text.color) < 0.6  # readable on the cream background

    def test_no_gap_between_block_and_fall(self):
        _, name = create_logo().controls
        assert name.spacing == 0
        for text in name.controls:
            assert text.style.height <= 0.95  # tight line height

    def test_mark_is_a_big_mini_board_with_a_gold_line_of_three(self):
        mark, _ = create_logo().controls
        rows = [[cell.bgcolor for cell in row.controls] for row in mark.controls]
        assert len(rows) == 3
        assert all(len(row) == 3 for row in rows)
        assert rows[1] == [COLOR_GOLD] * 3  # the game: line up 3
        assert set(rows[0] + rows[2]) <= {TILE_COLORS[c] for c in SQUARE_COLORS}
        assert mark.controls[0].controls[0].width >= 16


class TestBlock:
    def test_a_block_is_a_small_label_above_a_value(self):
        value = ft.Text("7")
        block = create_block("SCORE", value, 80)
        label, shown = block.content.controls
        assert (label.value, label.color) == ("SCORE", COLOR_MUTED_TEXT)
        assert shown is value
        assert (block.width, block.height) == (80, HEADER_BLOCK_HEIGHT)
        assert block.bgcolor == COLOR_BOARD_BG


class TestConfirmDialog:
    def test_a_modal_question_with_two_block_buttons(self):
        clicks = []
        dialog = create_confirm_dialog(
            "Restart the game?", "You will lose the current game.", "CANCEL", "RESTART", "#7FB3F5",
            on_cancel=lambda _event: clicks.append("cancel"), on_ok=lambda _event: clicks.append("ok"),
        )
        assert dialog.modal
        assert dialog.title.value == "Restart the game?"
        assert dialog.content.value == "You will lose the current game."
        cancel, ok = dialog.actions
        assert [(b.content.value, b.bgcolor) for b in (cancel, ok)] == [
            ("CANCEL", COLOR_BOARD_BG), ("RESTART", "#7FB3F5"),
        ]
        cancel.on_click(None)
        ok.on_click(None)
        assert clicks == ["cancel", "ok"]

