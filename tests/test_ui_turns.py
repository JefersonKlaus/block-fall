"""Player input in order around animations."""

import asyncio
import unittest

from ui.turns import TurnQueue


class TurnQueueTests(unittest.TestCase):
    def setUp(self):
        self.queue = TurnQueue()
        self.played = []

    def run_move(self, direction, during=None):
        async def play(move):
            self.played.append(move)
            if during and len(self.played) == 1:
                await during()

        asyncio.run(self.queue.submit(direction, play))

    def test_a_move_is_played_at_once_when_idle(self):
        self.run_move("left")
        self.assertEqual(self.played, ["left"])
        self.assertFalse(self.queue.busy)

    def test_a_move_during_another_one_is_played_right_after(self):
        async def swipe_again():
            self.assertTrue(self.queue.busy)
            await self.queue.submit("up", None)
            self.assertTrue(self.queue.hurry)  # the running move should speed up

        self.run_move("left", during=swipe_again)
        self.assertEqual(self.played, ["left", "up"])
        self.assertFalse(self.queue.hurry)

    def test_the_latest_waiting_move_wins(self):
        async def swipe_many():
            for direction in ("up", "right", "down"):
                await self.queue.submit(direction, None)

        self.run_move("left", during=swipe_many)
        self.assertEqual(self.played, ["left", "down"])

    def test_an_action_runs_now_when_idle(self):
        done = []
        self.queue.when_idle(lambda: done.append(True))
        self.assertEqual(done, [True])

    def test_an_action_during_a_move_runs_right_after_it(self):
        done = []

        async def ask():
            self.queue.when_idle(lambda: done.append(list(self.played)))
            self.assertEqual(done, [])

        self.run_move("left", during=ask)
        self.assertEqual(done, [["left"]])
        self.assertIsNone(self.queue.pending)

    def test_busy_is_cleared_even_if_a_move_fails(self):
        async def broken(_move):
            raise RuntimeError("boom")

        with self.assertRaises(RuntimeError):
            asyncio.run(self.queue.submit("left", broken))
        self.assertFalse(self.queue.busy)
