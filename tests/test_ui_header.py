"""The header: logo, SCORE, BEST, LEVEL, RESTART."""

import unittest

from config import COLOR_RESTART
from ui.header import Header


class HeaderTests(unittest.TestCase):
    def test_shows_scores_and_level(self):
        header = Header(on_level=None, on_restart=None)
        header.show(12, 40, "MIDDLE", "#F9DF7A")
        self.assertEqual((header.score_text.value, header.best_text.value), ("12", "40"))
        self.assertEqual((header.level_text.value, header.level_button.bgcolor), ("MIDDLE", "#F9DF7A"))

    def test_taps_are_reported(self):
        taps = []
        header = Header(on_level=lambda e: taps.append("level"), on_restart=lambda e: taps.append("restart"))
        header.level_button.on_click(None)
        header.restart_button.on_click(None)
        self.assertEqual(taps, ["level", "restart"])
        self.assertEqual(header.restart_button.bgcolor, COLOR_RESTART)
