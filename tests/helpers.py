"""Shared test helpers: a strict fake page, color maths, control walking."""

import colorsys
import dataclasses
from types import SimpleNamespace

import flet as ft


def lab(hex_color):
    """CIELAB coordinates: distances match how different colors look."""
    r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    lin = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4  # noqa: E731
    r, g, b = map(lin, (r, g, b))
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116  # noqa: E731
    return (116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z)))


def lightness(hex_color):
    return colorsys.rgb_to_hls(*(int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)))[1]


def iter_controls(control):
    """Yield a control and all of its descendants."""
    yield control
    content = getattr(control, "content", None)
    if content is not None:
        yield from iter_controls(content)
    for child in getattr(control, "controls", None) or []:
        yield from iter_controls(child)


REAL_PAGE_ATTRIBUTES = {f.name for f in dataclasses.fields(ft.Page)} | set(dir(ft.Page))


class MockPage:
    """Stand-in for ft.Page that only accepts attributes ft.Page really has.

    A permissive mock hid a real bug: `page.window_width` (Flet 0.x) was
    silently ignored by Flet 1.x, so the window was never sized.
    """

    _MOCK_ONLY = {"updated", "tasks", "orientations", "dialog", "device_languages"}

    def __init__(self, platform=ft.PagePlatform.WINDOWS, width=400, device_languages=("en-US",)):
        self.window = ft.Window()
        self.platform = platform
        self.width = width  # the space the app really gets (not the window size)
        self.tasks = []
        self.device_languages = device_languages

    def __setattr__(self, name, value):
        if name not in self._MOCK_ONLY and name not in REAL_PAGE_ATTRIBUTES:
            raise AttributeError(f"ft.Page has no attribute {name!r}")
        object.__setattr__(self, name, value)

    def add(self, control):
        self.controls = [control]

    def update(self):
        self.updated = True

    def run_task(self, handler, *args):
        self.tasks.append((handler, args))

    def show_dialog(self, dialog):
        self.dialog = dialog

    def pop_dialog(self):
        self.dialog = None

    async def get_device_info(self):
        """Like Flet's: the device's languages, most preferred first."""
        if isinstance(self.device_languages, Exception):
            raise self.device_languages
        if self.device_languages is None:
            return None
        locales = []
        for code in self.device_languages:
            language, _, country = code.partition("-")
            locales.append(ft.Locale(language, country or None))
        return SimpleNamespace(locales=locales)

    async def set_allowed_device_orientations(self, orientations):
        self.orientations = orientations
