"""Touch input: finger movement -> move direction."""

import asyncio
import unittest
from types import SimpleNamespace

import flet as ft

from config import COLOR_BG, SWIPE_MIN_DISTANCE
from ui.swipe import SwipeArea, swipe_direction


class SwipeDirectionTests(unittest.TestCase):
    def test_direction_from_the_finger_movement(self):
        self.assertEqual(swipe_direction(60, 10), "right")
        self.assertEqual(swipe_direction(-60, -10), "left")
        self.assertEqual(swipe_direction(5, 60), "down")
        self.assertEqual(swipe_direction(-5, -60), "up")

    def test_mostly_horizontal_or_vertical_diagonals(self):
        self.assertEqual(swipe_direction(50, 30), "right")
        self.assertEqual(swipe_direction(30, -50), "up")

    def test_short_or_exactly_diagonal_drags_are_not_moves(self):
        self.assertEqual(SWIPE_MIN_DISTANCE, 24)
        self.assertIsNone(swipe_direction(10, 5))
        self.assertIsNone(swipe_direction(0, 0))
        self.assertIsNone(swipe_direction(SWIPE_MIN_DISTANCE - 1, 0))
        self.assertEqual(swipe_direction(SWIPE_MIN_DISTANCE, 0), "right")
        self.assertIsNone(swipe_direction(40, 40))


class SwipeAreaTests(unittest.TestCase):
    def setUp(self):
        self.swipes = []

        async def on_swipe(direction):
            self.swipes.append(direction)

        self.content = ft.Text("game")
        self.area = SwipeArea(self.content, on_swipe)

    def drag(self, *steps, end=True):
        gesture = self.area.control
        gesture.on_pan_start(None)
        for dx, dy in steps:
            gesture.on_pan_update(SimpleNamespace(local_delta=ft.Offset(dx, dy)))
        if end:
            asyncio.run(gesture.on_pan_end(None))

    def test_a_drag_becomes_one_swipe(self):
        self.drag((-30, 2), (-30, 1))
        self.assertEqual(self.swipes, ["left"])

    def test_a_tiny_drag_is_not_a_swipe(self):
        self.drag((5, 5))
        self.assertEqual(self.swipes, [])

    def test_each_drag_starts_from_zero(self):
        self.drag((20, 0), end=False)  # interrupted: no pan end
        self.drag((10, 0))
        self.assertEqual(self.swipes, [])

    def test_the_whole_area_reacts_even_where_it_is_empty(self):
        gesture = self.area.control
        self.assertIsInstance(gesture, ft.GestureDetector)
        self.assertIs(gesture.content.content, self.content)
        self.assertEqual(gesture.content.bgcolor, COLOR_BG)  # painted
        self.assertTrue(gesture.expand and gesture.content.expand)

