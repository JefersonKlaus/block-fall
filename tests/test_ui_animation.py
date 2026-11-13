"""Playing a move's steps with pauses that can be skipped."""

import asyncio
import unittest
from unittest.mock import AsyncMock, call, patch

from config import ANIMATION_SECONDS, BLUE, GOLD_FLASH_SECONDS, POP_START_SECONDS
from game import Frame
from ui.animation import Animator
from ui.board import BoardView


class AnimatorTests(unittest.TestCase):
    def setUp(self):
        patcher = patch("ui.animation.asyncio.sleep", new_callable=AsyncMock)
        self.sleep = patcher.start()
        self.addCleanup(patcher.stop)
        self.board = BoardView(4, 4, 360)
        self.updates = []
        self.hurry = False
        self.animator = Animator(self.board, lambda: self.updates.append(len(self.board.tiles)),
                                 hurry=lambda: self.hurry)

    def play(self, *frames):
        asyncio.run(self.animator.play(list(frames)))

    def test_each_kind_of_step_gets_its_pause_except_a_quiet_last_one(self):
        slide = Frame("slide", {1: (0, 0, BLUE)})
        match = Frame("match", {1: (0, 0, BLUE)}, frozenset({1}))
        self.board.show({1: (1, 0, BLUE)})
        self.play(slide, match)
        self.assertEqual(self.sleep.await_args_list, [call(ANIMATION_SECONDS), call(GOLD_FLASH_SECONDS)])

    def test_a_new_square_pops_in(self):
        self.play(Frame("spawn", {7: (2, 2, BLUE)}))
        self.assertEqual(self.sleep.await_args_list, [call(POP_START_SECONDS)])
        self.assertEqual(self.board.tiles[7].scale, 1)
        self.assertEqual(self.updates, [1, 1])  # shown tiny, then grown

    def test_no_pauses_when_hurried(self):
        self.hurry = True
        self.play(Frame("slide", {1: (0, 0, BLUE)}), Frame("spawn", {1: (0, 0, BLUE), 2: (3, 3, BLUE)}))
        self.sleep.assert_not_awaited()
        self.assertEqual(self.board.tiles[2].scale, 1)  # still ends full size

    def test_pause_can_be_skipped(self):
        asyncio.run(self.animator.pause(0.8))
        self.hurry = True
        asyncio.run(self.animator.pause(0.8))
        self.assertEqual(self.sleep.await_args_list, [call(0.8)])
