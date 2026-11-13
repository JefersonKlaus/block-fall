"""The app's texts: English by default, Portuguese on Portuguese devices."""

import dataclasses
import unittest

import flet as ft

from texts import DEFAULT_LANGUAGE, ENGLISH, LANGUAGES, PORTUGUESE, language_for


def locales(*codes):
    """Device locales, most preferred first, e.g. locales("pt-BR", "en")."""
    result = []
    for code in codes:
        language, _, country = code.partition("-")
        result.append(ft.Locale(language, country or None))
    return result


class LanguageChoiceTests(unittest.TestCase):
    def test_english_is_the_default(self):
        self.assertEqual(DEFAULT_LANGUAGE, "en")
        self.assertEqual(language_for([]), "en")

    def test_a_portuguese_device_gets_portuguese(self):
        for device in (locales("pt"), locales("pt-BR"), locales("pt-PT"), locales("pt-BR", "en-US")):
            with self.subTest(device=device):
                self.assertEqual(language_for(device), "pt")

    def test_any_other_device_gets_english(self):
        for device in (locales("en-US"), locales("es-ES"), locales("fr"), locales("de", "pt-BR")):
            with self.subTest(device=device):
                self.assertEqual(language_for(device), "en")

    def test_only_the_main_device_language_counts(self):
        self.assertEqual(language_for(locales("en-US", "pt-BR")), "en")

    def test_language_codes_in_any_case(self):
        self.assertEqual(language_for([ft.Locale("PT", "BR")]), "pt")


class TranslationTests(unittest.TestCase):
    def test_two_languages(self):
        self.assertEqual(LANGUAGES, {"en": ENGLISH, "pt": PORTUGUESE})

    def test_every_text_is_translated(self):
        for field in dataclasses.fields(ENGLISH):
            english, portuguese = getattr(ENGLISH, field.name), getattr(PORTUGUESE, field.name)
            with self.subTest(text=field.name):
                self.assertTrue(english and portuguese)
                if field.name not in ("cancel",):
                    self.assertNotEqual(english, portuguese)

    def test_placeholders_are_kept(self):
        for texts in (ENGLISH, PORTUGUESE):
            self.assertIn("{points}", texts.unlocks_at)
            self.assertIn("{level}", texts.change_level_question)

    def test_portuguese_texts(self):
        self.assertEqual(
            (PORTUGUESE.score, PORTUGUESE.best, PORTUGUESE.level, PORTUGUESE.restart),
            ("PONTOS", "RECORDE", "NÍVEL", "REINICIAR"),
        )
        self.assertEqual(PORTUGUESE.level_names, ("INICIANTE", "MÉDIO", "MESTRE"))
        self.assertEqual(PORTUGUESE.play, "Alinhe 3 ou mais quadrados da mesma cor.")
        self.assertEqual(PORTUGUESE.game_over, "FIM DE JOGO")
        self.assertEqual(PORTUGUESE.unlocked, "Nova cor desbloqueada!")

    def test_english_texts_are_the_ones_the_game_already_uses(self):
        self.assertEqual(ENGLISH.level_names, ("BEGINNER", "MIDDLE", "MASTER"))
        self.assertEqual(ENGLISH.play, "Line up 3 or more squares of the same color.")
        self.assertEqual(ENGLISH.game_over, "GAME OVER")

    def test_header_words_fit_their_blocks(self):
        # Measured in Roboto (Flutter's font) at the sizes the header uses.
        import os

        from PIL import ImageFont

        from config import HEADER_BLOCK_WIDTH
        from tools.screen import FONT_DIR as files

        def width(text, size, weight):
            font = ImageFont.truetype(os.path.join(files, f"Roboto-{weight}.ttf"), size * 10)
            return font.getlength(text) / 10

        room = HEADER_BLOCK_WIDTH - 6
        for texts in LANGUAGES.values():
            for label in (texts.score, texts.best, texts.level, texts.restart):
                self.assertLessEqual(width(label, 10, "Regular"), room, label)
            for name in texts.level_names:
                self.assertLessEqual(width(name, 11, "Bold"), room, name)
