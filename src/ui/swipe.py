"""Touch input: turn finger movement into a move direction."""

from typing import Any, Awaitable, Callable, Optional

import flet as ft

from config import COLOR_BG, SWIPE_MIN_DISTANCE


def swipe_direction(dx: float, dy: float) -> Optional[str]:
    """Which move a finger movement of (dx, dy) pixels means, if any.

    The longer axis wins; too-short or exactly diagonal drags are not moves.
    """
    if max(abs(dx), abs(dy)) < SWIPE_MIN_DISTANCE or abs(dx) == abs(dy):
        return None
    if abs(dx) > abs(dy):
        return "right" if dx > 0 else "left"
    return "down" if dy > 0 else "up"


class SwipeArea:
    """A screen area where swipes (touch, or mouse drags) trigger moves."""

    def __init__(self, content: ft.Control, on_swipe: Callable[[str], Awaitable[None]]):
        self._on_swipe = on_swipe
        self._drag = [0.0, 0.0]  # finger movement of the current swipe
        self.control = ft.GestureDetector(
            # Painted, so swipes also work on the empty space.
            content=ft.Container(content=content, bgcolor=COLOR_BG, expand=True),
            on_pan_start=self._on_pan_start,
            on_pan_update=self._on_pan_update,
            on_pan_end=self._on_pan_end,
            expand=True,
        )

    def _on_pan_start(self, _event: Any) -> None:
        # Also clears a swipe that was interrupted (no pan end).
        self._drag = [0.0, 0.0]

    def _on_pan_update(self, event: Any) -> None:
        self._drag[0] += event.local_delta.x
        self._drag[1] += event.local_delta.y

    async def _on_pan_end(self, _event: Any) -> None:
        direction = swipe_direction(*self._drag)
        self._drag = [0.0, 0.0]
        if direction is not None:
            await self._on_swipe(direction)
