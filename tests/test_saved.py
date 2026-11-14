"""What the app saves on the device: the bests, and the tutorial seen."""

import asyncio

import pytest

from saved import load_best_scores, load_tutorial_seen, save_best_score, save_tutorial_seen, storage_key
from tests.helpers import FakeStorage


def test_one_key_per_level():
    assert [storage_key(level) for level in range(3)] == [
        "block_fall.best.beginner", "block_fall.best.middle", "block_fall.best.master",
    ]


def test_loads_the_saved_best_of_every_level():
    storage = FakeStorage({"block_fall.best.beginner": 12, "block_fall.best.master": 40})
    assert asyncio.run(load_best_scores(storage)) == {0: 12, 1: 0, 2: 40}  # MIDDLE: none saved


@pytest.mark.parametrize("saved, loaded", [
    (25, 25), (25.0, 0), (0, 0), (-5, 0), ("25", 0), (True, 0), (None, 0), (["25"], 0),
])
def test_anything_that_is_not_a_score_counts_as_none(saved, loaded):
    storage = FakeStorage({"block_fall.best.middle": saved})
    assert asyncio.run(load_best_scores(storage))[1] == loaded


def test_no_storage_means_no_saved_bests():
    assert asyncio.run(load_best_scores(FakeStorage(fail=True))) == {0: 0, 1: 0, 2: 0}


def test_saves_a_level_s_best():
    storage = FakeStorage()
    asyncio.run(save_best_score(storage, 2, 33))
    assert storage.values == {"block_fall.best.master": 33}


def test_a_failed_save_does_not_stop_the_game():
    asyncio.run(save_best_score(FakeStorage(fail=True), 1, 10))  # no error


def test_the_tutorial_is_new_until_it_is_saved_as_seen():
    storage = FakeStorage()
    assert asyncio.run(load_tutorial_seen(storage)) is False
    asyncio.run(save_tutorial_seen(storage))
    assert storage.values == {"block_fall.tutorial_seen": True}
    assert asyncio.run(load_tutorial_seen(storage)) is True


def test_without_storage_the_tutorial_shows_again():
    assert asyncio.run(load_tutorial_seen(FakeStorage(fail=True))) is False
    asyncio.run(save_tutorial_seen(FakeStorage(fail=True)))  # no error
