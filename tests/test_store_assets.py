"""The tool that makes the app icon and the store images."""

import runpy

import pytest
from PIL import Image, ImageChops

import config
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
    splash_image,
    store_icon,
)

SMALL = Target("test", "phone", 216, 384, 0.525)  # same shape as a phone, tiny and fast


def rgb(hex_color):
    return tuple(int(hex_color[i:i + 2], 16) for i in (1, 3, 5))


class TestArtwork:
    def test_app_icon_is_1024_with_transparent_corners(self):
        icon = app_icon()
        assert (icon.size, icon.mode) == ((1024, 1024), "RGBA")
        assert icon.getpixel((0, 0))[3] == 0  # flet build fills the background
        assert icon.getpixel((512, 512))[3] == 255

    def test_app_icon_is_9_squares_with_no_frame_around_them(self):
        icon = app_icon()
        cell = (1024 - 2 * 0.04 * 1024) / 3
        gap_x = round(cell + 0.02 * 1024)  # the middle of the gap between two columns
        assert icon.getpixel((gap_x, 512))[3] == 0  # transparent between squares: no board behind them
        assert icon.getpixel((512, 512))[:3] == rgb(config.COLOR_GOLD)  # the gold middle row
        assert icon.getpixel((512, round(cell / 2)))[:3] == rgb(config.TILE_COLORS[config.GREEN])
        assert rgb(config.COLOR_BOARD_BG) not in {color[:3] for _, color in icon.getcolors(maxcolors=100_000)}

    def test_the_squares_fill_the_icon(self):
        # Edge to edge: flet build then gives each platform its own margin.
        assert app_icon().getbbox() == (0, 0, 1024, 1024)

    def test_store_icons_are_square_and_opaque(self):
        for size in (512, 1024):
            icon = store_icon(size)
            assert (icon.size, icon.mode) == ((size, size), "RGB")

    @pytest.mark.parametrize("size", [512, 1024])
    def test_store_icons_look_like_the_app_on_a_phone(self, size):
        # The squares take the middle 60% of the store icon, as flet build
        # makes them on an iPhone; the rest is the app's background.
        icon = store_icon(size)
        background = Image.new("RGB", icon.size, config.COLOR_BG)
        left, top, right, bottom = ImageChops.difference(icon, background).getbbox()
        assert (right - left) / size == pytest.approx(0.6, abs=0.01)
        assert (left, top) == pytest.approx(((size - (right - left)) / 2,) * 2, abs=1)
        assert icon.getpixel((size // 2, size // 2)) == rgb(config.COLOR_GOLD)

    def test_feature_graphic_is_1024_by_500_in_each_language(self):
        english, portuguese = feature_graphic("en"), feature_graphic("pt")
        for graphic in (english, portuguese):
            assert (graphic.size, graphic.mode) == ((1024, 500), "RGB")
        assert english.tobytes() != portuguese.tobytes()  # the tagline


class TestLaunchScreen:
    """src/assets/splash.png: what the phone shows while the app starts."""

    def test_square_and_transparent_around_the_logo(self):
        splash = splash_image()
        assert (splash.size, splash.mode) == ((1024, 1024), "RGBA")
        assert splash.getpixel((0, 0))[3] == 0  # the splash color (pyproject.toml) shows through
        assert splash.getpixel((1023, 1023))[3] == 0

    def test_the_logo_mark_above_the_name(self):
        splash = splash_image()

        def where(color):
            """Bounding box of the pixels drawn in exactly `color`."""
            diff = ImageChops.difference(splash.convert("RGB"), Image.new("RGB", splash.size, rgb(color)))
            r, g, b = diff.point(lambda v: 255 if v == 0 else 0).split()
            return ImageChops.darker(ImageChops.darker(r, g), b).getbbox()

        gold, name, fall = where(config.COLOR_GOLD), where(config.COLOR_TEXT), where(config.COLOR_LOGO_ACCENT)
        assert gold and name and fall  # the gold line, "Block", and "Fall"
        assert gold[3] < name[1] and gold[3] < fall[1]  # the mark is above the name
        assert name[2] < fall[0]  # "Block", then "Fall"

    def test_android_12_shows_it_whole(self):
        # Android 12+ crops the launch icon to its middle circle (2/3 wide):
        # the picture stays inside it, so flet build neither crops nor shrinks it.
        radial_extent = pytest.importorskip("flet_platform_assets._imaging").radial_extent
        assert radial_extent(splash_image()) <= 2 / 3


class TestScreenshot:
    @pytest.mark.parametrize("name, seed, scene", SCENES, ids=[name for name, _, _ in SCENES])
    def test_every_scene_makes_a_picture_of_the_target_size(self, name, seed, scene):
        shot = screenshot(SMALL, seed, scene)
        assert shot.size == (216, 384)
        assert len(shot.getcolors(maxcolors=100_000)) > 10  # not blank

    def test_screenshots_are_the_same_every_time(self):
        name, seed, scene = SCENES[1]
        assert screenshot(SMALL, seed, scene).tobytes() == screenshot(SMALL, seed, scene).tobytes()

    def test_store_sizes(self):
        sizes = {(t.store, t.device): (t.width, t.height) for t in TARGETS}
        assert sizes == {
            ("google-play", "phone"): (1080, 1920),
            ("app-store", "iphone-6.9"): (1320, 2868),
            ("app-store", "iphone-6.5"): (1284, 2778),
            ("app-store", "ipad-13"): (2064, 2752),
        }

    def test_screenshots_in_portuguese(self):
        name, seed, scene = SCENES[0]
        english = screenshot(SMALL, seed, scene, "en")
        portuguese = screenshot(SMALL, seed, scene, "pt")
        assert english.size == portuguese.size
        assert english.tobytes() != portuguese.tobytes()  # the texts differ

    def test_the_game_over_scene_shows_the_big_restart_button(self):
        shot = screenshot(SMALL, SCENES[-1][1], SCENES[-1][2])
        blue = tuple(int(config.COLOR_RESTART[i:i + 2], 16) for i in (1, 3, 5))
        bottom = shot.crop((0, 384 - 40, 216, 384))  # where the big button sits
        blue_pixels = sum(n for n, color in bottom.getcolors(maxcolors=100_000) if color == blue)
        assert blue_pixels > 0.5 * 216 * 25

    @pytest.mark.parametrize("name, seed, scene", SCENES, ids=[name for name, _, _ in SCENES])
    def test_only_the_game_over_scene_shows_the_colored_points(self, name, seed, scene):
        shot = screenshot(SMALL, seed, scene)
        # Below the header (whose logo uses the same purple), down to the middle.
        header_bottom = (config.PAGE_PADDING + config.LAYOUT_PADDING
                         + 2 * config.HEADER_BLOCK_HEIGHT + config.HEADER_BLOCK_SPACING)
        band = shot.crop((0, round(header_bottom * SMALL.scale) + 1, 216, 384 // 2))
        points = rgb(config.COLOR_FINAL_SCORE)
        shown = any(color == points for _, color in band.getcolors(maxcolors=100_000))
        assert shown == (name == "07-game-over")

    def test_still_page_records_the_background_tasks(self):
        page = StillPage(400, 800)
        page.run_task("handler", 1)
        assert page.tasks == [("handler", (1,))]


class TestBuild:
    def test_build_writes_the_icon_and_every_store_image(self, tmp_path):
        files = build(tmp_path, targets=[SMALL], scenes=SCENES[:2])
        names = sorted(p.relative_to(tmp_path).as_posix() for p in files)
        assert names == sorted([
            "src/assets/icon.png",
            "src/assets/splash.png",
            "doc/screenshot/google-play/icon-512.png",
            "doc/screenshot/app-store/icon-1024.png",
            "doc/screenshot/google-play/en/feature-graphic.png",
            "doc/screenshot/google-play/pt/feature-graphic.png",
        ] + [
            f"doc/screenshot/test/{language}/phone/{name}.png"
            for language in ("en", "pt") for name, _, _ in SCENES[:2]
        ])
        assert all(p.is_file() for p in files)
        assert Image.open(files[0]).size == (1024, 1024)

    def test_command_line_lists_the_files(self, monkeypatch, capsys):
        monkeypatch.setattr(store_assets, "build", lambda: [store_assets.ROOT / "a.png"])
        store_assets.main()
        assert capsys.readouterr().out == "a.png\n"

    def test_running_the_module_runs_the_command_line(self, monkeypatch, capsys):
        # The real images are never made here (that is slow and would write
        # into the project): the module's fresh copy picks up this fake.
        monkeypatch.setattr("tools.assets.build", lambda: [store_assets.ROOT / "b.png"])
        runpy.run_path(store_assets.__file__, run_name="__main__")
        assert capsys.readouterr().out == "b.png\n"


class TestWrap:
    def test_long_messages_wrap_to_the_width(self):
        from tools.screen import Canvas, wrap

        canvas = Canvas(400, 100, 1, "#FFFFFF")
        text = "Line up 3 or more squares of the same color."
        assert wrap(canvas, text, 1000, 13, "Bold") == [text]
        lines = wrap(canvas, text, 150, 13, "Bold")
        assert len(lines) > 1
        assert " ".join(lines) == text
        assert all(canvas.text_width(line, 13, "Bold") <= 150 for line in lines)
