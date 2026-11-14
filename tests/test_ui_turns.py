"""Player input in order around animations."""

import asyncio

import pytest

from ui.turns import TurnQueue


@pytest.fixture
def queue():
    return TurnQueue()


@pytest.fixture
def played():
    """The moves, in the order they were really played."""
    return []


@pytest.fixture
def run_move(queue, played):
    """Submit a move; `during` runs (once) while the first move is playing."""
    def run_move(direction, during=None):
        async def play(move):
            played.append(move)
            if during and len(played) == 1:
                await during()

        asyncio.run(queue.submit(direction, play))

    return run_move


class TestTurnQueue:
    def test_a_move_is_played_at_once_when_idle(self, queue, played, run_move):
        run_move("left")
        assert played == ["left"]
        assert not queue.busy

    def test_a_move_during_another_one_is_played_right_after(self, queue, played, run_move):
        async def swipe_again():
            assert queue.busy
            await queue.submit("up", None)
            assert queue.hurry  # the running move should speed up

        run_move("left", during=swipe_again)
        assert played == ["left", "up"]
        assert not queue.hurry

    def test_the_latest_waiting_move_wins(self, queue, played, run_move):
        async def swipe_many():
            for direction in ("up", "right", "down"):
                await queue.submit(direction, None)

        run_move("left", during=swipe_many)
        assert played == ["left", "down"]

    def test_an_action_runs_now_when_idle(self, queue):
        done = []
        queue.when_idle(lambda: done.append(True))
        assert done == [True]

    def test_an_action_during_a_move_runs_right_after_it(self, queue, played, run_move):
        done = []

        async def ask():
            queue.when_idle(lambda: done.append(list(played)))
            assert done == []

        run_move("left", during=ask)
        assert done == [["left"]]
        assert queue.pending is None

    def test_busy_is_cleared_even_if_a_move_fails(self, queue):
        async def broken(_move):
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError):
            asyncio.run(queue.submit("left", broken))
        assert not queue.busy
