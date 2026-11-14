"""The header: logo, SCORE, BEST, LEVEL, RESTART."""

from config import COLOR_RESTART
from texts import ENGLISH, PORTUGUESE
from ui.header import Header


class TestHeader:
    def test_shows_scores_and_level(self):
        header = Header(on_level=None, on_restart=None, page_width=360)
        header.show(12, 40, "MIDDLE", "#F9DF7A", ENGLISH)
        assert (header.score_text.value, header.best_text.value) == ("12", "40")
        assert (header.level_text.value, header.level_button.bgcolor) == ("MIDDLE", "#F9DF7A")

    def test_labels_in_the_language_shown(self):
        header = Header(on_level=None, on_restart=None, page_width=360)
        header.show(0, 0, "MÉDIO", "#F9DF7A", PORTUGUESE)
        labels = [block.content.controls[0].value for block in header.blocks]
        assert labels == ["PONTOS", "RECORDE", "NÍVEL", "REINICIAR"]

    def test_taps_are_reported(self):
        taps = []
        header = Header(on_level=lambda _event: taps.append("level"), on_restart=lambda _event: taps.append("restart"),
                        page_width=360)
        header.level_button.on_click(None)
        header.restart_button.on_click(None)
        assert taps == ["level", "restart"]
        assert header.restart_button.bgcolor == COLOR_RESTART
