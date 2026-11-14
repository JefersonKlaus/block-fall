"""Core game rules, independent of the UI framework.

Rules:
- The board holds single colored squares. There are 5 colors, one per level:
  a game starts with 2, and one more unlocks every 50 points (50, 100, 150).
- A new game starts with about 10% of the board (START_FILL) already filled
  with squares (in the starting colors, never already forming a line).
- Every move slides all squares as far as they go in one direction, like
  2048, but squares never merge.
- After every move one new square (random unlocked color) appears on the opposite side
  of the board: push right and it appears on the left edge, at a random free
  position along that edge (or on the nearest line inward if the edge is full).
- MATCH_LENGTH or more squares of the same color in a horizontal or vertical
  line disappear. A line scores 3 points for its first 3 squares and 2 points
  for every extra square (3, 5, 7, ...). Crossing lines each score.
- The game ends when the board is full.
"""

from dataclasses import dataclass
from itertools import groupby
import random
from typing import Optional

from config import (
    BLUE,
    GREEN,
    GRID_COLS,
    GRID_ROWS,
    PEACH,
    PURPLE,
    RED,
    START_FILL,
    UNLOCK_SCORES,
)


SQUARE_COLORS = (BLUE, GREEN, RED, PEACH, PURPLE)
MATCH_LENGTH = 3
# The move directions, each with the side where its new square appears.
OPPOSITE = {"left": "right", "right": "left", "up": "down", "down": "up"}

# square id -> (column, row, color)
Squares = dict[int, tuple[int, int, int]]
Cell = tuple[int, int]  # (column, row)


def line_points(length: int) -> int:
    """Points for a line: 1 per square for the first 3, then 2 per square."""
    return MATCH_LENGTH + 2 * (length - MATCH_LENGTH)


def lines_from(rows: int, cols: int, side: str) -> list[list[Cell]]:
    """Rows or columns of the board, each listed starting from `side`.

    "left": every row from left to right; "up": every column from top to
    bottom; and so on. Squares sliding toward `side` pack at the front.
    """
    columns, row_range = range(cols), range(rows)
    if side in ("left", "right"):
        ordered = columns if side == "left" else columns[::-1]
        return [[(column, row) for column in ordered] for row in row_range]
    ordered = row_range if side == "up" else row_range[::-1]
    return [[(column, row) for row in ordered] for column in columns]


def find_lines(grid: list[list[int]]) -> list[list[Cell]]:
    """Every horizontal or vertical run of MATCH_LENGTH+ same-colored squares."""
    rows, cols = len(grid), len(grid[0])
    found = []
    for line in lines_from(rows, cols, "left") + lines_from(rows, cols, "up"):
        for color, run in groupby(line, key=lambda cell: grid[cell[1]][cell[0]]):
            run = list(run)
            if color and len(run) >= MATCH_LENGTH:
                found.append(run)
    return found


@dataclass(frozen=True)
class Frame:
    """One step of a move, recorded so the UI can animate it.

    kind is "slide" (squares moved), "match" (`gold` squares are about to
    disappear) or "spawn" (a new square appeared). `squares` is a snapshot.
    """

    kind: str
    squares: Squares
    gold: frozenset[int] = frozenset()


class BlockFallEngine:
    """Manage the board, the squares, scoring, and game state."""

    def __init__(
        self, rows: int = GRID_ROWS, cols: int = GRID_COLS, start_squares: Optional[int] = None
    ):
        self.rows = rows
        self.cols = cols
        # By default about 10% of the board starts filled.
        self.start_squares = (
            round(rows * cols * START_FILL) if start_squares is None else start_squares
        )
        self.grid: list[list[int]] = []
        # Parallel to grid: a unique id per square that travels with it, so
        # the UI can show each square sliding to its new place.
        self.square_ids: list[list[int]] = []
        self._next_square_id = 1
        # What happened during the last play_move, step by step (for display).
        self.frames: list[Frame] = []
        self.score = 0
        self.high_score = 0
        self.game_over = False
        self._clear_board()
        self._add_starting_squares(self.start_squares)

    def reset(self) -> None:
        """Start a new game while preserving the high score."""
        self._clear_board()
        self.frames = []
        self.score = 0
        self.game_over = False
        self._add_starting_squares(self.start_squares)

    def unlocked_colors(self) -> tuple[int, ...]:
        """The colors new squares can have, given the current score."""
        return tuple(
            color for color, needed in zip(SQUARE_COLORS, UNLOCK_SCORES) if self.score >= needed
        )

    def play_move(self, direction: str) -> bool:
        """Play one turn: slide every square, then add one new square.

        Returns False if the move is not allowed (invalid direction or game
        over). The game is over when the board is full after the turn.
        """
        self.frames = []
        if self.game_over or direction not in OPPOSITE:
            return False
        self.move_board(direction)
        self.spawn_square(direction)
        self.game_over = all(all(row) for row in self.grid)
        return True

    def move_board(self, direction: str) -> bool:
        """Slide every square as far as possible toward `direction` (one of
        OPPOSITE's keys); then clear lines. Returns True if any square moved.
        """
        moved = False
        for line in lines_from(self.rows, self.cols, direction):
            squares = [self._take(column, row) for column, row in line]
            packed = [square for square in squares if square[0]]
            packed += [(0, 0)] * (len(line) - len(packed))
            moved = moved or packed != squares
            for (column, row), (color, square_id) in zip(line, packed):
                self.grid[row][column] = color
                self.square_ids[row][column] = square_id
        if moved:
            self.frames.append(Frame("slide", self.squares()))
        self.clear_matches()
        return moved

    def spawn_square(self, direction: str) -> bool:
        """Add one random square on the side opposite to `direction`.

        Returns False if the board is full.
        """
        for line in self._edges_from(OPPOSITE[direction]):
            free = [(column, row) for column, row in line if not self.grid[row][column]]
            if free:
                column, row = random.choice(free)
                self.place_square(column, row, random.choice(self.unlocked_colors()))
                self.frames.append(Frame("spawn", self.squares()))
                self.clear_matches()
                return True
        return False

    def place_square(self, column: int, row: int, color: int) -> bool:
        """Put one square on a free cell."""
        if not (0 <= column < self.cols and 0 <= row < self.rows) or self.grid[row][column]:
            return False
        self.grid[row][column] = color
        self.square_ids[row][column] = self._next_square_id
        self._next_square_id += 1
        return True

    def squares(self) -> Squares:
        """Every square on the board: id -> (column, row, color)."""
        return {
            square_id: (column, row, self.grid[row][column])
            for row, ids in enumerate(self.square_ids)
            for column, square_id in enumerate(ids)
            if square_id
        }

    def clear_matches(self) -> int:
        """Remove every line of MATCH_LENGTH or more same-colored squares.

        Each line scores line_points(length); a square shared by a horizontal
        and a vertical line counts in both but is removed once. Returns the
        number of squares removed.
        """
        lines = find_lines(self.grid)
        matched = {cell for line in lines for cell in line}
        if matched:
            gold = frozenset(self.square_ids[row][column] for column, row in matched)
            self.frames.append(Frame("match", self.squares(), gold))
        for column, row in matched:
            self.grid[row][column] = 0
            self.square_ids[row][column] = 0
        self.score += sum(line_points(len(line)) for line in lines)
        self.high_score = max(self.high_score, self.score)
        return len(matched)

    def _clear_board(self) -> None:
        self.grid = [[0] * self.cols for _ in range(self.rows)]
        self.square_ids = [[0] * self.cols for _ in range(self.rows)]

    def _add_starting_squares(self, count: int) -> None:
        """Put up to `count` squares on random free cells, without any line."""
        cells = [
            (column, row)
            for row in range(self.rows)
            for column in range(self.cols)
            if not self.grid[row][column]
        ]
        random.shuffle(cells)
        added = 0
        for column, row in cells:
            if added == count:
                break
            allowed = [
                color for color in self.unlocked_colors()
                if not self._would_make_line(column, row, color)
            ]
            if allowed:
                self.place_square(column, row, random.choice(allowed))
                added += 1

    def _would_make_line(self, column: int, row: int, color: int) -> bool:
        """Would a `color` square at (column, row) complete a line?"""
        for step_col, step_row in ((1, 0), (0, 1)):
            length = 1
            for sign in (1, -1):
                c, r = column + sign * step_col, row + sign * step_row
                while 0 <= c < self.cols and 0 <= r < self.rows and self.grid[r][c] == color:
                    length += 1
                    c, r = c + sign * step_col, r + sign * step_row
            if length >= MATCH_LENGTH:
                return True
        return False

    def _take(self, column: int, row: int) -> tuple[int, int]:
        return self.grid[row][column], self.square_ids[row][column]

    def _edges_from(self, side: str) -> list[list[Cell]]:
        """Columns (or rows) starting at the `side` edge and going inward."""
        lines = lines_from(self.rows, self.cols, "up" if side in ("left", "right") else "left")
        return lines if side in ("left", "up") else lines[::-1]
