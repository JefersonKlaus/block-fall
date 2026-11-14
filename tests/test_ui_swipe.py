"""Touch input: finger movement -> move direction."""

import asyncio
from types import SimpleNamespace

import flet as ft
import pytest

from config import COLOR_BG, SWIPE_MIN_DISTANCE
from ui.swipe import SwipeArea, swipe_direction


class TestSwipeDirection:
    def test_direction_from_the_finger_movement(self):
        assert swipe_direction(60, 10) == "right"
        assert swipe_direction(-60, -10) == "left"
        assert swipe_direction(5, 60) == "down"
        assert swipe_direction(-5, -60) == "up"

    def test_mostly_horizontal_or_vertical_diagonals(self):
        assert swipe_direction(50, 30) == "right"
        assert swipe_direction(30, -50) == "up"

    def test_short_or_exactly_diagonal_drags_are_not_moves(self):
        assert SWIPE_MIN_DISTANCE == 24
        assert swipe_direction(10, 5) is None
        assert swipe_direction(0, 0) is None
        assert swipe_direction(SWIPE_MIN_DISTANCE - 1, 0) is None
        assert swipe_direction(SWIPE_MIN_DISTANCE, 0) == "right"
        assert swipe_direction(40, 40) is None


@pytest.fixture
def swipes():
    """The directions the area reported."""
    return []


@pytest.fixture
def content():
    return ft.Text("game")


@pytest.fixture
def area(content, swipes):
    async def on_swipe(direction):
        swipes.append(direction)

    return SwipeArea(content, on_swipe)


def drag(area, *steps, end=True):
    gesture = area.control
    gesture.on_pan_start(None)
    for dx, dy in steps:
        gesture.on_pan_update(SimpleNamespace(local_delta=ft.Offset(dx, dy)))
    if end:
        asyncio.run(gesture.on_pan_end(None))


class TestSwipeArea:
    def test_a_drag_becomes_one_swipe(self, area, swipes):
        drag(area, (-30, 2), (-30, 1))
        assert swipes == ["left"]

    def test_a_tiny_drag_is_not_a_swipe(self, area, swipes):
        drag(area, (5, 5))
        assert swipes == []

    def test_each_drag_starts_from_zero(self, area, swipes):
        drag(area, (20, 0), end=False)  # interrupted: no pan end
        drag(area, (10, 0))
        assert swipes == []

    def test_the_whole_area_reacts_even_where_it_is_empty(self, area, content):
        gesture = area.control
        assert isinstance(gesture, ft.GestureDetector)
        assert gesture.content.content is content
        assert gesture.content.bgcolor == COLOR_BG  # painted
        assert gesture.expand and gesture.content.expand
