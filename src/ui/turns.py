"""Puts player input in order around animations."""

from typing import Awaitable, Callable, Optional


class TurnQueue:
    """One move at a time, without losing input.

    - A swipe made during an animation is kept (the latest wins) and played
      right after; meanwhile `hurry` is true so the animation speeds up.
    - An action (restart, level change) asked for during an animation runs
      right after it.
    """

    def __init__(self):
        self.busy = False
        self.queued_move: Optional[str] = None
        self.pending: Optional[Callable[[], None]] = None

    @property
    def hurry(self) -> bool:
        return self.queued_move is not None

    async def submit(self, direction: str, play: Callable[[str], Awaitable[None]]) -> None:
        if self.busy:
            self.queued_move = direction
            return
        self.busy = True
        try:
            move: Optional[str] = direction
            while move is not None:
                await play(move)
                move, self.queued_move = self.queued_move, None
        finally:
            self.busy = False
        if self.pending is not None:
            action, self.pending = self.pending, None
            action()

    def when_idle(self, action: Callable[[], None]) -> None:
        """Run `action` now, or right after the running animation."""
        if self.busy:
            self.pending = action
        else:
            action()
