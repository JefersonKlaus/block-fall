"""The project layout: app code in src/, Flet configured to find it."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    tomllib = None


class LayoutTests(unittest.TestCase):
    def test_the_app_code_is_in_src(self):
        for name in ("main.py", "config.py", "game.py", "ui/__init__.py", "ui/app.py"):
            self.assertTrue((SRC / name).is_file(), name)

    def test_no_app_code_left_at_the_top(self):
        for name in ("main.py", "config.py", "game.py", "ui.py", "ui"):
            self.assertFalse((ROOT / name).exists(), name)

    def test_tests_stay_outside_src(self):
        self.assertFalse((SRC / "tests").exists())
        self.assertTrue((ROOT / "tests" / "test_game.py").is_file())


@unittest.skipIf(tomllib is None, "tomllib needs Python 3.11+")
class PyprojectTests(unittest.TestCase):
    def setUp(self):
        self.config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    def test_flet_builds_the_app_from_src(self):
        app = self.config["tool"]["flet"]["app"]
        self.assertEqual((app["path"], app["module"]), ("src", "main"))

    def test_app_name_and_requirements(self):
        self.assertEqual(self.config["tool"]["flet"]["product"], "Block Fall")
        self.assertEqual(self.config["project"]["name"], "block-fall")
        # What the built phone app needs: Flet alone (no desktop or CLI tools).
        self.assertEqual(self.config["project"]["dependencies"], ["flet==1.0.5"])


class FletRunTests(unittest.TestCase):
    """`flet run` from the project folder starts the app."""

    def test_local_setup_installs_the_flet_command_and_desktop_runner(self):
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8").split()
        self.assertIn("flet[cli,desktop]==1.0.5", requirements)

    def test_flet_run_finds_src_main_py(self):
        # `flet run` looks for main.py in the current folder; pyproject.toml's
        # [tool.flet.app] path sends it to src/main.py.
        self.assertFalse((ROOT / "main.py").exists())
        if tomllib is not None:
            config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
            path = config["tool"]["flet"]["app"]["path"]
            self.assertTrue((ROOT / path / "main.py").is_file())


def png_info(path):
    """(width, height, has_alpha) from a PNG file's header."""
    data = path.read_bytes()[:26]
    assert data[:8] == b"\x89PNG\r\n\x1a\n", f"{path} is not a PNG"
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    color_type = data[25]
    return width, height, color_type in (4, 6)


SHOTS = ROOT / "doc" / "screenshot"
LANGUAGES = ("en", "pt")
SCREENSHOT_SIZES = {  # (store, device) -> size
    ("google-play", "phone"): (1080, 1920),
    ("app-store", "iphone-6.9"): (1320, 2868),
    ("app-store", "iphone-6.5"): (1284, 2778),
    ("app-store", "ipad-13"): (2064, 2752),
}


def shots_of(store, language, device):
    return sorted((SHOTS / store / language / device).glob("*.png"))


class AppIconTests(unittest.TestCase):
    def test_flet_build_finds_a_1024_icon_in_src_assets(self):
        self.assertEqual(png_info(SRC / "assets" / "icon.png"), (1024, 1024, True))


class StoreImageTests(unittest.TestCase):
    def test_google_play_icon_and_a_feature_graphic_per_language(self):
        self.assertEqual(png_info(SHOTS / "google-play" / "icon-512.png")[:2], (512, 512))
        for language in LANGUAGES:
            graphic = SHOTS / "google-play" / language / "feature-graphic.png"
            self.assertEqual(png_info(graphic), (1024, 500, False), language)
        en, pt = (SHOTS / "google-play" / lang / "feature-graphic.png" for lang in LANGUAGES)
        self.assertNotEqual(en.read_bytes(), pt.read_bytes())  # translated tagline

    def test_app_store_icon_has_no_transparency(self):
        self.assertEqual(png_info(SHOTS / "app-store" / "icon-1024.png"), (1024, 1024, False))

    def test_screenshots_for_every_store_size_and_language(self):
        for (store, device), size in SCREENSHOT_SIZES.items():
            for language in LANGUAGES:
                with self.subTest(store=store, device=device, language=language):
                    shots = shots_of(store, language, device)
                    self.assertTrue(2 <= len(shots) <= 8, len(shots))  # Google Play allows 2 to 8
                    for shot in shots:
                        self.assertEqual(png_info(shot)[:2], size, shot.name)

    def test_every_store_and_language_gets_the_same_scenes(self):
        names = {
            (store, device, language): [p.name for p in shots_of(store, language, device)]
            for store, device in SCREENSHOT_SIZES for language in LANGUAGES
        }
        self.assertEqual(len({tuple(n) for n in names.values()}), 1, names)

    def test_portuguese_screenshots_differ_from_the_english_ones(self):
        for store, device in SCREENSHOT_SIZES:
            en, pt = (shots_of(store, lang, device)[0] for lang in LANGUAGES)
            self.assertNotEqual(en.read_bytes(), pt.read_bytes(), (store, device))

    def test_the_folder_explains_what_goes_where(self):
        readme = (SHOTS / "README.md").read_text(encoding="utf-8")
        for words in ("Google Play", "App Store", "python -m tools.store_assets", "Portuguese"):
            self.assertIn(words, readme)


def pins(path):
    """{package: version} pinned with == in a requirements file."""
    result = {}
    for line in (ROOT / path).read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if "==" in line:
            name, version = line.split("==")
            result[name.split("[")[0].strip().lower()] = version.strip()
    return result


class RequirementsTests(unittest.TestCase):
    """Every pinned version must exist and be the one the tests run on."""

    def test_flet_is_the_latest_stable_release(self):
        self.assertEqual(pins("requirements.txt")["flet"], "1.0.5")

    def test_the_tests_run_on_the_pinned_versions(self):
        from importlib.metadata import version

        pinned = {**pins("requirements.txt"), **pins("requirements-dev.txt")}
        for package, wanted in pinned.items():
            with self.subTest(package=package):
                self.assertEqual(version(package), wanted)

    @unittest.skipIf(tomllib is None, "tomllib needs Python 3.11+")
    def test_the_app_and_the_local_setup_use_the_same_flet(self):
        config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(config["project"]["dependencies"], [f"flet=={pins('requirements.txt')['flet']}"])

    def test_dev_requirements(self):
        self.assertEqual(pins("requirements-dev.txt"), {"coverage": "7.16.2", "pillow": "12.3.0"})
        self.assertNotIn("font-roboto", (ROOT / "requirements-dev.txt").read_text(encoding="utf-8"))

    def test_the_roboto_fonts_come_with_the_project(self):
        fonts = ROOT / "tools" / "fonts"
        for weight in ("Regular", "Medium", "Bold", "Black"):
            self.assertTrue((fonts / f"Roboto-{weight}.ttf").is_file(), weight)
        self.assertIn("Apache License", (fonts / "LICENSE.txt").read_text(encoding="utf-8"))
