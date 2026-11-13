"""The tool that makes the app icon and the store images."""

import importlib
import io
import runpy
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from PIL import Image

import config
import tools
from tools import store_assets
from tools.assets import (
    SCENES,
    TARGETS,
    StillPage,
    Target,
    app_icon,
    build,
    feature_graphic,
    screenshot,
    store_icon,
)

SMALL = Target("test", "phone", 216, 384, 0.525)  # same shape as a phone, tiny and fast


class ArtworkTests(unittest.TestCase):
    def test_app_icon_is_1024_with_transparent_corners(self):
        icon = app_icon()
        self.assertEqual((icon.size, icon.mode), ((1024, 1024), "RGBA"))
        self.assertEqual(icon.getpixel((0, 0))[3], 0)  # flet build fills the background
        self.assertEqual(icon.getpixel((512, 512))[3], 255)

    def test_store_icons_are_square_and_opaque(self):
        for size in (512, 1024):
            icon = store_icon(size)
            self.assertEqual((icon.size, icon.mode), ((size, size), "RGB"))

    def test_the_icon_is_the_logo_mark_with_a_gold_middle_row(self):
        icon = store_icon(1024)
        gold = tuple(int(config.COLOR_GOLD[i:i + 2], 16) for i in (1, 3, 5))
        self.assertEqual(icon.getpixel((512, 512)), gold)

    def test_feature_graphic_is_1024_by_500_in_each_language(self):
        english, portuguese = feature_graphic("en"), feature_graphic("pt")
        for graphic in (english, portuguese):
            self.assertEqual((graphic.size, graphic.mode), ((1024, 500), "RGB"))
        self.assertNotEqual(english.tobytes(), portuguese.tobytes())  # the tagline


class ScreenshotTests(unittest.TestCase):
    def test_every_scene_makes_a_picture_of_the_target_size(self):
        for name, seed, scene in SCENES:
            with self.subTest(scene=name):
                shot = screenshot(SMALL, seed, scene)
                self.assertEqual(shot.size, (216, 384))
                self.assertGreater(len(shot.getcolors(maxcolors=100_000)), 10)  # not blank

    def test_screenshots_are_the_same_every_time(self):
        name, seed, scene = SCENES[1]
        self.assertEqual(screenshot(SMALL, seed, scene).tobytes(), screenshot(SMALL, seed, scene).tobytes())

    def test_store_sizes(self):
        sizes = {(t.store, t.device): (t.width, t.height) for t in TARGETS}
        self.assertEqual(sizes, {
            ("google-play", "phone"): (1080, 1920),
            ("app-store", "iphone-6.9"): (1320, 2868),
            ("app-store", "iphone-6.5"): (1284, 2778),
            ("app-store", "ipad-13"): (2064, 2752),
        })

    def test_screenshots_in_portuguese(self):
        name, seed, scene = SCENES[0]
        english = screenshot(SMALL, seed, scene, "en")
        portuguese = screenshot(SMALL, seed, scene, "pt")
        self.assertEqual(english.size, portuguese.size)
        self.assertNotEqual(english.tobytes(), portuguese.tobytes())  # the texts differ

    def test_the_game_over_scene_shows_the_big_restart_button(self):
        shot = screenshot(SMALL, SCENES[-1][1], SCENES[-1][2])
        blue = tuple(int(config.COLOR_RESTART[i:i + 2], 16) for i in (1, 3, 5))
        bottom = shot.crop((0, 384 - 40, 216, 384))  # where the big button sits
        blue_pixels = sum(n for n, color in bottom.getcolors(maxcolors=100_000) if color == blue)
        self.assertGreater(blue_pixels, 0.5 * 216 * 25)

    def test_a_dialog_can_be_drawn_over_the_screen(self):
        def scene_with_dialog(view, shoot):
            view._moves_played = 1
            view.header.restart_button.on_click(None)  # asks first
            shoot()

        shot = screenshot(SMALL, 1, scene_with_dialog)
        self.assertEqual(shot.size, (216, 384))

    def test_still_page_records_what_the_app_asks(self):
        page = StillPage(400, 800)
        page.show_dialog("dialog")
        page.run_task("handler", 1)
        self.assertEqual((page.dialog, page.tasks), ("dialog", [("handler", (1,))]))
        page.pop_dialog()
        self.assertIsNone(page.dialog)


class BuildTests(unittest.TestCase):
    def test_build_writes_the_icon_and_every_store_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            files = build(Path(tmp), targets=[SMALL], scenes=SCENES[:2])
            names = sorted(str(p.relative_to(tmp)) for p in files)
            self.assertEqual(names, sorted([
                "src/assets/icon.png",
                "doc/screenshot/google-play/icon-512.png",
                "doc/screenshot/app-store/icon-1024.png",
                "doc/screenshot/google-play/en/feature-graphic.png",
                "doc/screenshot/google-play/pt/feature-graphic.png",
            ] + [
                f"doc/screenshot/test/{language}/phone/{name}.png"
                for language in ("en", "pt") for name, _, _ in SCENES[:2]
            ]))
            self.assertTrue(all(p.is_file() for p in files))
            self.assertEqual(Image.open(files[0]).size, (1024, 1024))

    def test_command_line_lists_the_files(self):
        with patch.object(store_assets, "build", return_value=[store_assets.ROOT / "a.png"]):
            out = io.StringIO()
            with redirect_stdout(out):
                store_assets.main()
        self.assertEqual(out.getvalue(), "a.png\n")

    def test_running_the_module_runs_the_command_line(self):
        # The real images are never made here (that is slow and would write
        # into the project): the module's fresh copy picks up this fake.
        out = io.StringIO()
        with patch("tools.assets.build", return_value=[store_assets.ROOT / "b.png"]), redirect_stdout(out):
            runpy.run_path(store_assets.__file__, run_name="__main__")
        self.assertEqual(out.getvalue(), "b.png\n")


class ToolsPackageTests(unittest.TestCase):
    def test_the_tools_can_import_the_app_from_src(self):
        without_src = [p for p in sys.path if p != tools.SRC]
        with patch.object(sys, "path", without_src):
            importlib.reload(tools)
            self.assertEqual(sys.path[0], tools.SRC)


class WrapTests(unittest.TestCase):
    def test_long_messages_wrap_to_the_width(self):
        from tools.screen import Canvas, wrap

        canvas = Canvas(400, 100, 1, "#FFFFFF")
        text = "Line up 3 or more squares of the same color."
        self.assertEqual(wrap(canvas, text, 1000, 13, "Bold"), [text])
        lines = wrap(canvas, text, 150, 13, "Bold")
        self.assertGreater(len(lines), 1)
        self.assertEqual(" ".join(lines), text)
        self.assertTrue(all(canvas.text_width(line, 13, "Bold") <= 150 for line in lines))
