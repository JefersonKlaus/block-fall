"""How to play: the tutorial's pictures tell the truth, and the dialog works."""

from unittest.mock import patch

import flet as ft
import pytest

from config import BLUE, COLOR_LOGO_ACCENT, GREEN, RED
from game import BlockFallEngine
from texts import ENGLISH, PORTUGUESE
from ui.tutorial import PICTURE_CELL, STEPS, SWIPE_ICONS, HelpButton, Tutorial, create_picture

LETTERS = {"B": BLUE, "G": GREEN, "R": RED}
NAMES = {color: letter for letter, color in LETTERS.items()}


def load(rows):
    """An engine with the picture's squares on its board."""
    engine = BlockFallEngine(rows=len(rows), cols=len(rows[0]), start_squares=0)
    for row, line in enumerate(rows):
        for column, letter in enumerate(line):
            if letter != ".":
                assert engine.place_square(column, row, LETTERS[letter])
    return engine


def drawn(squares, size, gold=frozenset(), new=frozenset()):
    """What the game shows, written like the pictures."""
    grid = [["."] * size for _ in range(size)]
    for square_id, (column, row, color) in squares.items():
        letter = "Y" if square_id in gold else NAMES[color]
        grid[row][column] = letter.lower() if square_id in new else letter
    return tuple("".join(row) for row in grid)


def play(step, new_square=None):
    """Play the step's swipe. `new_square`: (column, row, color) where the new
    square must go; it has to be one of the places the game offers."""
    engine = load(step.before)

    def choose(values):
        if all(isinstance(value, int) for value in values):  # the new square's color
            return new_square[2] if new_square else values[0]
        if new_square:
            assert new_square[:2] in values, "the game would not put a new square there"
            return new_square[:2]
        return values[0]

    before = set(engine.squares())
    with patch("game.random.choice", side_effect=choose):
        engine.play_move(step.swipe)
    return engine, before


class TestThePicturesShowTheRealGame:
    def test_every_picture_is_a_small_board_before_and_after_a_swipe(self):
        for step in STEPS:
            assert len(step.before) == len(step.after) == 4
            assert all(len(row) == 4 for row in step.before + step.after)
            assert step.swipe in SWIPE_ICONS

    def test_1_all_the_squares_slide_as_far_as_they_can(self):
        engine, _ = play(STEPS[0])
        slide = engine.frames[0]
        assert slide.kind == "slide"
        assert drawn(slide.squares, 4) == STEPS[0].after

    def test_2_then_a_new_square_appears_on_the_other_side(self):
        step = STEPS[1]
        assert step.before == STEPS[0].before  # the same swipe as step 1
        (row,) = [r for r, line in enumerate(step.after) if any(c.islower() for c in line)]
        column = next(c for c, letter in enumerate(step.after[row]) if letter.islower())
        assert column == 3  # on the right edge, for a swipe to the left
        color = LETTERS[step.after[row][column].upper()]
        engine, before = play(step, new_square=(column, row, color))
        new = set(engine.squares()) - before
        assert drawn(engine.squares(), 4, new=new) == step.after

    def test_3_three_in_a_line_turn_gold_then_disappear(self):
        engine, _ = play(STEPS[2])
        match = next(frame for frame in engine.frames if frame.kind == "match")
        assert drawn(match.squares, 4, gold=match.gold) == STEPS[2].after
        assert engine.score == 3

    def test_the_new_square_is_marked(self):
        (picture_after,) = [create_picture(STEPS[1]).controls[2]]
        squares = [square for row in picture_after.content.controls for square in row.controls]
        marked = [square for square in squares if square.content is not None]
        assert len(marked) == 1
        assert marked[0].content.icon == ft.Icons.ADD

    def test_two_boards_and_the_swipe_fit_a_small_phone_s_dialog(self):
        # A 320 px phone: the dialog keeps 40 px on each side, plus 24 px of padding.
        board = 4 * PICTURE_CELL + 3 * 2 + 2 * 4
        picture = create_picture(STEPS[0])
        icon = picture.controls[1]
        assert 2 * board + icon.size + 2 * picture.spacing <= 320 - 2 * 40 - 2 * 24
        assert icon.icon == ft.Icons.SWIPE_LEFT


class TestTutorialDialog:
    @pytest.fixture
    def events(self):
        return []

    @pytest.fixture
    def tutorial(self, events):
        return Tutorial(ENGLISH, update=lambda: events.append("update"), on_close=lambda: events.append("close"))

    def buttons(self, tutorial):
        return {button.content.value: button for button in tutorial.dialog.actions}

    def test_a_modal_dialog_that_starts_at_the_first_step(self, tutorial):
        assert isinstance(tutorial.dialog, ft.AlertDialog)
        assert tutorial.dialog.modal
        assert tutorial.dialog.title.value == "Swipe to move"
        picture, text, _dots = tutorial.dialog.content.controls
        assert text.value.startswith("Swipe left, right, up, or down")
        assert isinstance(picture, ft.Row)
        assert set(self.buttons(tutorial)) == {"SKIP", "NEXT"}

    def test_next_shows_the_following_step(self, tutorial, events):
        self.buttons(tutorial)["NEXT"].on_click(None)
        assert tutorial.dialog.title.value == "A new square"
        assert events == ["update"]

    def test_the_last_step_has_only_the_button_to_play(self, tutorial, events):
        for _ in range(len(STEPS) - 1):
            self.buttons(tutorial)["NEXT"].on_click(None)
        assert tutorial.dialog.title.value == "Line up 3"
        assert list(self.buttons(tutorial)) == ["PLAY!"]
        self.buttons(tutorial)["PLAY!"].on_click(None)
        assert events[-1] == "close"

    def test_skip_closes_it_at_once(self, tutorial, events):
        self.buttons(tutorial)["SKIP"].on_click(None)
        assert events == ["close"]

    def test_one_dot_per_step_the_current_one_colored(self, tutorial):
        self.buttons(tutorial)["NEXT"].on_click(None)
        dots = tutorial.dialog.content.controls[2].controls
        assert [dot.bgcolor == COLOR_LOGO_ACCENT for dot in dots] == [False, True, False]

    def test_in_portuguese(self):
        tutorial = Tutorial(PORTUGUESE, update=lambda: None, on_close=lambda: None)
        assert tutorial.dialog.title.value == "Deslize para mover"
        assert {button.content.value for button in tutorial.dialog.actions} == {"PULAR", "PRÓXIMO"}


class TestHelpButton:
    def test_shows_its_label_and_opens_the_tutorial(self):
        clicks = []
        button = HelpButton(on_click=lambda _event: clicks.append(True))
        button.show(True, PORTUGUESE)
        assert (button.label.value, button.control.visible) == ("COMO JOGAR", True)
        button.control.on_click(None)
        assert clicks == [True]

    def test_can_be_hidden(self):
        button = HelpButton(on_click=None)
        button.show(False, ENGLISH)
        assert not button.control.visible
