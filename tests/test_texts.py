"""The app's texts: English by default, Portuguese on Portuguese devices."""

import dataclasses

import flet as ft
import pytest

from texts import DEFAULT_LANGUAGE, ENGLISH, LANGUAGES, PORTUGUESE, language_for


def locales(*codes):
    """Device locales, most preferred first, e.g. locales("pt-BR", "en")."""
    result = []
    for code in codes:
        language, _, country = code.partition("-")
        result.append(ft.Locale(language, country or None))
    return result


class TestLanguageChoice:
    def test_english_is_the_default(self):
        assert DEFAULT_LANGUAGE == "en"
        assert language_for([]) == "en"

    @pytest.mark.parametrize("device", ["pt", "pt-BR", "pt-PT", "pt-BR,en-US"])
    def test_a_portuguese_device_gets_portuguese(self, device):
        assert language_for(locales(*device.split(","))) == "pt"

    @pytest.mark.parametrize("device", ["en-US", "es-ES", "fr", "de,pt-BR"])
    def test_any_other_device_gets_english(self, device):
        assert language_for(locales(*device.split(","))) == "en"

    def test_only_the_main_device_language_counts(self):
        assert language_for(locales("en-US", "pt-BR")) == "en"

    def test_language_codes_in_any_case(self):
        assert language_for([ft.Locale("PT", "BR")]) == "pt"


class TestTranslation:
    def test_two_languages(self):
        assert LANGUAGES == {"en": ENGLISH, "pt": PORTUGUESE}

    @pytest.mark.parametrize("text", [field.name for field in dataclasses.fields(ENGLISH)])
    def test_every_text_is_translated(self, text):
        english, portuguese = getattr(ENGLISH, text), getattr(PORTUGUESE, text)
        assert english and portuguese
        if text not in ("cancel",):
            assert english != portuguese

    def test_placeholders_are_kept(self):
        for texts in (ENGLISH, PORTUGUESE):
            assert "{points}" in texts.unlocks_at
            assert "{points}" in texts.final_score
            assert "{level}" in texts.change_level_question

    def test_portuguese_texts(self):
        assert (PORTUGUESE.score, PORTUGUESE.best, PORTUGUESE.level, PORTUGUESE.restart) == (
            "PONTOS", "RECORDE", "NÍVEL", "REINICIAR",
        )
        assert PORTUGUESE.level_names == ("INICIANTE", "MÉDIO", "MESTRE")
        assert PORTUGUESE.play == "Alinhe 3 ou mais quadrados da mesma cor."
        assert PORTUGUESE.game_over == "FIM DE JOGO"
        assert PORTUGUESE.unlocked == "Nova cor desbloqueada!"
        assert PORTUGUESE.final_score.format(points=12) == "Você fez 12 pontos!"

    def test_english_texts_are_the_ones_the_game_already_uses(self):
        assert ENGLISH.level_names == ("BEGINNER", "MIDDLE", "MASTER")
        assert ENGLISH.play == "Line up 3 or more squares of the same color."
        assert ENGLISH.game_over == "GAME OVER"
        assert ENGLISH.final_score.format(points=12) == "You scored 12 points!"

    def test_header_words_fit_their_blocks(self):
        # Measured in Roboto (Flutter's font) at the sizes the header uses, in
        # the narrowest blocks (on the smallest screen).
        import os

        from PIL import ImageFont

        from config import FALLBACK_PAGE_WIDTH, HEADER_LABEL_SIZE, HEADER_LEVEL_SIZE
        from ui.header import block_width
        from tools.screen import FONT_DIR as files

        def width(text, size, weight):
            font = ImageFont.truetype(os.path.join(files, f"Roboto-{weight}.ttf"), size * 10)
            return font.getlength(text) / 10

        room = block_width(FALLBACK_PAGE_WIDTH) - 6
        for texts in LANGUAGES.values():
            for label in (texts.score, texts.best, texts.level, texts.restart):
                assert width(label, HEADER_LABEL_SIZE, "Regular") <= room, label
            for name in texts.level_names:
                assert width(name, HEADER_LEVEL_SIZE, "Bold") <= room, name
