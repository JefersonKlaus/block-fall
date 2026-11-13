"""The app icon and the Google Play / App Store images.

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
from PIL import Image, ImageDraw

import config
from texts import LANGUAGES
from tools.screen import Canvas, render
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
        self.window = ft.Window()
        self.platform = None
        self.controls: list = []
        self.tasks: list = []
        self.dialog = None

    def add(self, control) -> None:
        self.controls.append(control)

    def update(self) -> None:
        pass

    def run_task(self, handler, *args) -> None:
        self.tasks.append((handler, args))

    def show_dialog(self, dialog) -> None:
        self.dialog = dialog

    def pop_dialog(self) -> None:
        self.dialog = None


@contextmanager
def instant_animations(on_pause: Callable[[float], None] = lambda seconds: None):
    """Animations take no time; `on_pause` sees each pause (e.g. the gold one)."""
    real_sleep = asyncio.sleep

    async def pause(seconds, *args, **kwargs):
        on_pause(seconds)

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
            image.append(render(view, width, height, target.scale, view.page.dialog))
            return image[-1]

        scene(view, shoot)
    return image[0].resize((target.width, target.height))


# --- artwork ----------------------------------------------------------------

def draw_mark(canvas: Canvas, x: float, y: float, size: float) -> None:
    """The logo's mark: a board with a gold line of 3 in the middle row."""
    canvas.box(x, y, size, size, 0.2 * size, config.COLOR_BOARD_BG)
    pad, gap = 0.12 * size, 0.05 * size
    cell = (size - 2 * pad - 2 * gap) / 3
    for r, row in enumerate(LOGO_MARK):
        for c, color in enumerate(row):
            canvas.box(x + pad + c * (cell + gap), y + pad + r * (cell + gap), cell, cell, 0.18 * cell, color)


def app_icon(size: int = 1024) -> Image.Image:
    """Transparent around the mark: `flet build` adds each platform's
    background (tool.flet.icon_background) and margins."""
    canvas = Canvas(size, size, 1, config.COLOR_BG)
    draw_mark(canvas, 0, 0, size)
    icon = canvas.image.convert("RGBA")
    mask = Image.new("L", icon.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size - 1, size - 1], radius=0.2 * size, fill=255)
    icon.putalpha(mask)
    return icon


def store_icon(size: int) -> Image.Image:
    """Square and opaque, as both stores want (they round the corners)."""
    canvas = Canvas(size, size, 1, config.COLOR_BG)
    draw_mark(canvas, 0.12 * size, 0.12 * size, 0.76 * size)
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
