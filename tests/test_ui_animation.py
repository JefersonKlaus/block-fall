"""Playing a move's steps with pauses that can be skipped."""

import asyncio
from types import SimpleNamespace
from unittest.mock import call

import pytest

from config import ANIMATION_SECONDS, BLUE, GOLD_FLASH_SECONDS, POP_START_SECONDS
from game import Frame
from ui.animation import Animator
from ui.board import BoardView


@pytest.fixture
def board():
    return BoardView(4, 4, 360)


@pytest.fixture
def player(sleep, board):
    """An animator on a small board; set `player.hurry` to skip its pauses."""
    player = SimpleNamespace(updates=[], hurry=False)
    player.animator = Animator(board, lambda: player.updates.append(len(board.tiles)),
                               hurry=lambda: player.hurry)
    return player


def play(player, *frames):
    asyncio.run(player.animator.play(list(frames)))


class TestAnimator:
    def test_each_kind_of_step_gets_its_pause_except_a_quiet_last_one(self, sleep, board, player):
        slide = Frame("slide", {1: (0, 0, BLUE)})
        match = Frame("match", {1: (0, 0, BLUE)}, frozenset({1}))
        board.show({1: (1, 0, BLUE)})
        play(player, slide, match)
        assert sleep.await_args_list == [call(ANIMATION_SECONDS), call(GOLD_FLASH_SECONDS)]

    def test_a_new_square_pops_in(self, sleep, board, player):
        play(player, Frame("spawn", {7: (2, 2, BLUE)}))
        assert sleep.await_args_list == [call(POP_START_SECONDS)]
        assert board.tiles[7].scale == 1
        assert player.updates == [1, 1]  # shown tiny, then grown

    def test_no_pauses_when_hurried(self, sleep, board, player):
        player.hurry = True
        play(player, Frame("slide", {1: (0, 0, BLUE)}), Frame("spawn", {1: (0, 0, BLUE), 2: (3, 3, BLUE)}))
        sleep.assert_not_awaited()
        assert board.tiles[2].scale == 1  # still ends full size

    def test_pause_can_be_skipped(self, sleep, player):
        asyncio.run(player.animator.pause(0.8))
        player.hurry = True
        asyncio.run(player.animator.pause(0.8))
        assert sleep.await_args_list == [call(0.8)]
