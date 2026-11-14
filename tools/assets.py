"""The app icon, the launch screen, and the Google Play / App Store images.

Screenshots are drawn from the real game and view (see tools/screen.py),
with fixed random seeds so they come out the same every time.
"""

import asyncio
import random
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import flet as ft
from PIL import Image

import config
from texts import LANGUAGES
from tools.screen import LINE_HEIGHT, Canvas, render
from ui import BlockFallView
from ui.widgets import LOGO_MARK

ROOT = Path(__file__).resolve().parent.parent
SHOTS = Path("doc") / "screenshot"
DIRECTIONS = ("left", "right", "up", "down")


@dataclass(frozen=True)
class Target:
    """A store screenshot size: store, device, pixels, and device pixel ratio."""

    store: str
    device: str
    width: int
    height: int
    scale: float


TARGETS = (
    Target("google-play", "phone", 1080, 1920, 2.625),
    Target("app-store", "iphone-6.9", 1320, 2868, 3),
    Target("app-store", "iphone-6.5", 1284, 2778, 3),
    Target("app-store", "ipad-13", 2064, 2752, 2),
)
# The feature graphic's tagline, per language (store text, not app text).
TAGLINES = {
    "en": "Slide. Match 3. Unlock colors.",
    "pt": "Deslize. Combine 3. Desbloqueie cores.",
}


class StillPage:
    """A page with no Flet session: enough to build the real view offline."""

    def __init__(self, width: float, height: float):
        self.width, self.height = width, height
        # The store pictures show the app only: no phone system bars.
        self.media = ft.PageMediaData(
            padding=ft.Padding.zero(), view_padding=ft.Padding.zero(), view_insets=ft.Padding.zero(),
            device_pixel_ratio=1, orientation=ft.Orientation.PORTRAIT,
        )
        self.window = ft.Window()
        self.platform = None
        self.controls: list = []
        self.tasks: list = []

    def add(self, control) -> None:
        self.controls.append(control)

    def update(self) -> None:
        pass

    def run_task(self, handler, *args) -> None:
        self.tasks.append((handler, args))


@contextmanager
def instant_animations(on_pause: Callable[[float], None] = lambda seconds: None):
    """Animations take no time; `on_pause` sees each pause (e.g. the gold one)."""
    real_sleep = asyncio.sleep

    async def pause(seconds, result=None):  # asyncio.sleep's signature
        on_pause(seconds)
        return result

    asyncio.sleep = pause
    try:
        yield
    finally:
        asyncio.sleep = real_sleep


def swipe(view: BlockFallView, times: int = 1) -> None:
    for _ in range(times):
        asyncio.run(view._handle_move(random.choice(DIRECTIONS)))


def colors_on_board(view: BlockFallView) -> set[int]:
    return {color for _, _, color in view.game.squares().values()}


# --- scenes: each one plays a fixed game and calls shoot() once -------------

def scene_playing(view, shoot):
    swipe(view, 12)
    shoot()


def scene_match(view, shoot):
    shots = []

    def on_pause(seconds):
        if seconds == config.GOLD_FLASH_SECONDS and not shots:
            shots.append(shoot())

    with instant_animations(on_pause):
        while not shots:
            swipe(view)


def scene_unlock(view, shoot):
    view.game.score = 44
    while view.status_display.value != view.texts.unlocked:
        swipe(view)
    shoot()


def scene_all_colors(view, shoot):
    view.game.score = view.game.high_score = 352
    while len(colors_on_board(view)) < 5 or len(view.game.squares()) < 9:
        swipe(view)
    shoot()


def scene_beginner(view, shoot):
    view.header.level_button.on_click(None)  # MASTER
    view.header.level_button.on_click(None)  # BEGINNER
    swipe(view, 14)
    shoot()


def scene_master(view, shoot):
    view.header.level_button.on_click(None)  # MASTER
    swipe(view, 6)
    shoot()


def scene_game_over(view, shoot):
    view.header.level_button.on_click(None)  # MASTER
    while not view.game.game_over:
        swipe(view)
    shoot()


SCENES = (
    ("01-playing", 12, scene_playing),
    ("02-line-of-three", 5, scene_match),
    ("03-new-color", 4, scene_unlock),
    ("04-all-colors", 7, scene_all_colors),
    ("05-beginner", 21, scene_beginner),
    ("06-master", 3, scene_master),
    ("07-game-over", 1, scene_game_over),
)


def screenshot(target: Target, seed: int, scene, language: str = "en") -> Image.Image:
    """Play `scene` (with a fixed seed) on a screen of `target`'s size."""
    width, height = target.width / target.scale, target.height / target.scale
    random.seed(seed)
    with instant_animations():
        view = BlockFallView(StillPage(width, height), language=language)
        image: list[Image.Image] = []

        def shoot() -> Image.Image:
            image.append(render(view, width, height, target.scale))
            return image[-1]

        scene(view, shoot)
    return image[0].resize((target.width, target.height))


# --- artwork ----------------------------------------------------------------

# Share of the icon's width the mark takes on a phone: `flet build` scales
# the app icon to this on iOS (and to the matching safe circle on Android).
# The store icons use the same, so they look like the installed app.
ICON_MARK = 0.6
# Gap between the mark's squares, as a share of the mark's width.
MARK_GAP = 0.04


def draw_mark(canvas: Canvas, x: float, y: float, size: float) -> None:
    """The logo's mark: 3 x 3 rounded squares (no frame), the middle row a gold line of 3."""
    gap = MARK_GAP * size
    cell = (size - 2 * gap) / 3
    for r, row in enumerate(LOGO_MARK):
        for c, color in enumerate(row):
            canvas.box(x + c * (cell + gap), y + r * (cell + gap), cell, cell, 0.18 * cell, color)


def app_icon(size: int = 1024) -> Image.Image:
    """The mark alone, on transparency: `flet build` adds each platform's
    background (tool.flet.icon_background) and margins."""
    canvas = Canvas(size, size, 1, None)
    draw_mark(canvas, 0, 0, size)
    return canvas.image


def splash_image(size: int = 1024) -> Image.Image:
    """The launch screen: the logo's mark above "Block Fall", on transparency.

    `flet build` centers it on the splash color (tool.flet.splash in
    pyproject.toml) at a quarter of its pixel size (1024 px -> 256 dp). It all
    stays inside the middle circle (2/3 of the width) that Android 12+ shows,
    so no platform crops or shrinks it.
    """
    canvas = Canvas(size, size, 1, None)
    mark, text, gap = 0.32 * size, 0.1 * size, 0.05 * size
    space = canvas.text_width(" ", text, "Black")
    block, fall = canvas.text_width("Block", text, "Black"), canvas.text_width("Fall", text, "Black")
    top = (size - (mark + gap + LINE_HEIGHT * text)) / 2
    draw_mark(canvas, (size - mark) / 2, top, mark)
    left = (size - (block + space + fall)) / 2
    canvas.text("Block", left, top + mark + gap, text, "Black", config.COLOR_TEXT)
    canvas.text("Fall", left + block + space, top + mark + gap, text, "Black", config.COLOR_LOGO_ACCENT)
    return canvas.image


def store_icon(size: int) -> Image.Image:
    """Square and opaque, as both stores want (they round the corners)."""
    canvas = Canvas(size, size, 1, config.COLOR_BG)
    margin = (1 - ICON_MARK) / 2 * size
    draw_mark(canvas, margin, margin, ICON_MARK * size)
    return canvas.image


def feature_graphic(language: str) -> Image.Image:
    """Google Play's 1024x500 banner: the mark, the name, and a tagline."""
    canvas = Canvas(1024, 500, 1, config.COLOR_BG)
    draw_mark(canvas, 90, 100, 300)
    canvas.text("Block", 450, 120, 110, "Black", config.COLOR_TEXT)
    canvas.text("Fall", 450 + canvas.text_width("Block", 110, "Black") + 10, 120, 110, "Black",
                config.COLOR_LOGO_ACCENT)
    tagline = TAGLINES[language]
    size = min(38, 38 * 520 / canvas.text_width(tagline, 38, "Medium"))  # fits the banner
    canvas.text(tagline, 454, 280, size, "Medium", config.COLOR_MUTED_TEXT)
    return canvas.image


def build(root: Path = ROOT, targets=TARGETS, scenes=SCENES) -> list[Path]:
    """Write the icon and every store image under `root`; return the files."""
    files = {
        root / "src" / "assets" / "icon.png": app_icon(),
        root / "src" / "assets" / "splash.png": splash_image(),
        root / SHOTS / "google-play" / "icon-512.png": store_icon(512),
        root / SHOTS / "app-store" / "icon-1024.png": store_icon(1024),
    }
    for language in LANGUAGES:
        files[root / SHOTS / "google-play" / language / "feature-graphic.png"] = feature_graphic(language)
        for target in targets:
            folder = root / SHOTS / target.store / language / target.device
            for name, seed, scene in scenes:
                files[folder / f"{name}.png"] = screenshot(target, seed, scene, language)
    for path, image in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        image.save(path, optimize=True)
    return list(files)
