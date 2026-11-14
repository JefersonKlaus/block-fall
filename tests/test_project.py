"""The project layout: app code in src/, Flet configured to find it."""

import sys
from importlib.metadata import version
from pathlib import Path

import pytest
from packaging.requirements import Requirement

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10: pytest brings tomli
    import tomli as tomllib

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


class TestLayout:
    @pytest.mark.parametrize("name", ["main.py", "config.py", "game.py", "ui/__init__.py", "ui/app.py"])
    def test_the_app_code_is_in_src(self, name):
        assert (SRC / name).is_file()

    @pytest.mark.parametrize("name", ["main.py", "config.py", "game.py", "ui.py", "ui"])
    def test_no_app_code_left_at_the_top(self, name):
        assert not (ROOT / name).exists()

    def test_tests_stay_outside_src(self):
        assert not (SRC / "tests").exists()
        assert (ROOT / "tests" / "test_game.py").is_file()


class TestPyproject:
    def test_flet_builds_the_app_from_src(self):
        app = PYPROJECT["tool"]["flet"]["app"]
        assert (app["path"], app["module"]) == ("src", "main")

    def test_app_name_and_requirements(self):
        assert PYPROJECT["tool"]["flet"]["product"] == "Block Fall"
        assert PYPROJECT["project"]["name"] == "block-fall"
        # What the built phone app needs: Flet alone (no desktop or CLI tools).
        assert PYPROJECT["project"]["dependencies"] == ["flet==1.0.5"]


class TestFletRun:
    """`flet run` from the project folder starts the app."""

    def test_local_setup_installs_the_flet_command_and_desktop_runner(self):
        assert "flet[cli,desktop]==1.0.5" in PYPROJECT["project"]["optional-dependencies"]["dev"]

    def test_flet_run_finds_src_main_py(self):
        # `flet run` looks for main.py in the current folder; pyproject.toml's
        # [tool.flet.app] path sends it to src/main.py.
        assert not (ROOT / "main.py").exists()
        path = PYPROJECT["tool"]["flet"]["app"]["path"]
        assert (ROOT / path / "main.py").is_file()


class TestEditableInstall:
    """`pip install -e ".[dev]"` sets everything up (see the README)."""

    def test_the_project_can_be_installed(self):
        assert PYPROJECT["build-system"]["build-backend"] == "hatchling.build"

    def test_the_editable_install_puts_the_app_on_the_path(self):
        wheel = PYPROJECT["tool"]["hatch"]["build"]["targets"]["wheel"]
        assert wheel["dev-mode-dirs"] == ["src"]
        assert wheel["sources"] == ["src"]

    def test_pytest_finds_the_tests_and_the_app(self):
        options = PYPROJECT["tool"]["pytest"]["ini_options"]
        assert options["testpaths"] == ["tests"]
        assert "src" in options["pythonpath"]

    @pytest.mark.parametrize("name", ["requirements.txt", "requirements-dev.txt"])
    def test_dependencies_live_only_in_pyproject(self, name):
        assert not (ROOT / name).exists()

    def test_the_readme_explains_setup_tests_and_mobile_builds(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for words in ('pip install -e ".[dev]"', "python -m pytest",
                      "flet build apk", "flet build aab", "flet build ipa", "Launch screen"):
            assert words in readme


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


class TestAppIcon:
    def test_flet_build_finds_a_1024_icon_in_src_assets(self):
        assert png_info(SRC / "assets" / "icon.png") == (1024, 1024, True)


class TestLaunchScreen:
    def test_flet_build_finds_the_launch_picture_in_src_assets(self):
        assert png_info(SRC / "assets" / "splash.png") == (1024, 1024, True)

    def test_launch_screen_uses_the_app_background_in_light_and_dark_mode(self):
        import config

        splash = PYPROJECT["tool"]["flet"]["splash"]
        assert splash["color"] == splash["dark_color"] == config.COLOR_BG


class TestStoreImages:
    def test_google_play_icon_and_a_feature_graphic_per_language(self):
        assert png_info(SHOTS / "google-play" / "icon-512.png")[:2] == (512, 512)
        for language in LANGUAGES:
            graphic = SHOTS / "google-play" / language / "feature-graphic.png"
            assert png_info(graphic) == (1024, 500, False), language
        en, pt = (SHOTS / "google-play" / lang / "feature-graphic.png" for lang in LANGUAGES)
        assert en.read_bytes() != pt.read_bytes()  # translated tagline

    def test_app_store_icon_has_no_transparency(self):
        assert png_info(SHOTS / "app-store" / "icon-1024.png") == (1024, 1024, False)

    @pytest.mark.parametrize("language", LANGUAGES)
    @pytest.mark.parametrize("store, device", list(SCREENSHOT_SIZES))
    def test_screenshots_for_every_store_size_and_language(self, store, device, language):
        shots = shots_of(store, language, device)
        assert 2 <= len(shots) <= 8, len(shots)  # Google Play allows 2 to 8
        for shot in shots:
            assert png_info(shot)[:2] == SCREENSHOT_SIZES[store, device], shot.name

    def test_every_store_and_language_gets_the_same_scenes(self):
        names = {
            (store, device, language): [p.name for p in shots_of(store, language, device)]
            for store, device in SCREENSHOT_SIZES for language in LANGUAGES
        }
        assert len({tuple(n) for n in names.values()}) == 1, names

    def test_portuguese_screenshots_differ_from_the_english_ones(self):
        for store, device in SCREENSHOT_SIZES:
            en, pt = (shots_of(store, lang, device)[0] for lang in LANGUAGES)
            assert en.read_bytes() != pt.read_bytes(), (store, device)

    def test_the_folder_explains_what_goes_where(self):
        readme = (SHOTS / "README.md").read_text(encoding="utf-8")
        for words in ("Google Play", "App Store", "python -m tools.store_assets", "Portuguese"):
            assert words in readme


def pins(requirements):
    """{package: version} for the requirements pinned with ==."""
    result = {}
    for line in requirements:
        requirement = Requirement(line)
        (spec,) = requirement.specifier
        assert spec.operator == "==", f"pin {line} with =="
        result[requirement.name.lower()] = spec.version
    return result


APP_PINS = pins(PYPROJECT["project"]["dependencies"])
DEV_PINS = pins(PYPROJECT["project"]["optional-dependencies"]["dev"])


class TestRequirements:
    """Every pinned version must exist and be the one the tests run on."""

    def test_flet_is_the_latest_stable_release(self):
        assert APP_PINS["flet"] == "1.0.5"

    @pytest.mark.parametrize("package, wanted", sorted({**APP_PINS, **DEV_PINS}.items()))
    def test_the_tests_run_on_the_pinned_versions(self, package, wanted):
        # Another version means these tests ran outside the project's virtual
        # environment (or it was changed by hand): they would not test what
        # ships, since flet build packs the pinned flet into the phone app.
        installed = version(package)
        assert installed == wanted, (
            f"{package} {installed} is installed in {sys.prefix}, but pyproject.toml pins {wanted}. "
            "Run the tests in the project's virtual environment, after "
            'python -m pip install -e ".[dev]" (README: "If the tests find other versions").'
        )

    def test_the_app_and_the_local_setup_use_the_same_flet(self):
        assert DEV_PINS["flet"] == APP_PINS["flet"]

    def test_dev_requirements(self):
        assert DEV_PINS == {"flet": "1.0.5", "pytest": "9.2.0", "coverage": "7.16.2", "pillow": "12.3.0"}
        assert "font-roboto" not in DEV_PINS

    def test_the_roboto_fonts_come_with_the_project(self):
        fonts = ROOT / "tools" / "fonts"
        for weight in ("Regular", "Medium", "Bold", "Black"):
            assert (fonts / f"Roboto-{weight}.ttf").is_file(), weight
        assert "Apache License" in (fonts / "LICENSE.txt").read_text(encoding="utf-8")
