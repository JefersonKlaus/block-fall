"""Core Block Fall game rules, independent of the UI framework."""

from dataclasses import dataclass
import random

from config import GRID_COLS, GRID_ROWS


TETROMINOES = (
    ((0, 0), (1, 0), (2, 0), (3, 0)),  # I
    ((0, 0), (1, 0), (0, 1), (1, 1)),  # O
    ((1, 0), (0, 1), (1, 1), (2, 1)),  # T
    ((1, 0), (2, 0), (0, 1), (1, 1)),  # S
    ((0, 0), (1, 0), (1, 1), (2, 1)),  # Z
    ((0, 0), (0, 1), (1, 1), (2, 1)),  # J
    ((2, 0), (0, 1), (1, 1), (2, 1)),  # L
)
PIECE_COLORS = (2, 4, 8, 16, 32, 64, 128)


@dataclass
class Piece:
    """A randomly selected tetromino and its board color."""

    cells: list[tuple[int, int]]
    color: int

    def rotate(self) -> None:
        """Rotate the tetromino clockwise and keep coordinates non-negative."""
        rotated = [(-row, column) for column, row in self.cells]
        min_column = min(column for column, _ in rotated)
        min_row = min(row for _, row in rotated)
        self.cells = [
            (column - min_column, row - min_row) for column, row in rotated
        ]

    @property
    def width(self) -> int:
        return max(column for column, _ in self.cells) + 1

    @property
    def height(self) -> int:
        return max(row for _, row in self.cells) + 1


class BlockFallEngine:
    """Manage the square board, tetrominoes, scoring, and game state."""

    def __init__(self, rows: int = GRID_ROWS, cols: int = GRID_COLS):
        self.rows = rows
        self.cols = cols
        self.grid: list[list[int]] = []
        self.score = 0
        self.high_score = 0
        self.game_over = False
        self.current_piece = self._generate_piece()
        self.next_piece = self._generate_piece()
        self._clear_board()

    def reset(self) -> None:
        """Start a new game while preserving the high score."""
        self._clear_board()
        self.score = 0
        self.game_over = False
        self.current_piece = self._generate_piece()
        self.next_piece = self._generate_piece()

    def rotate_piece(self) -> None:
        """Rotate the current tetromino before it is placed."""
        self.current_piece.rotate()

    def drop_piece(self) -> bool:
        """Drop the current tetromino into a randomly selected valid column."""
        if self.game_over:
            return False

        valid_columns = [
            column
            for column in range(self.cols - self.current_piece.width + 1)
            if self._can_place(self.current_piece, column, 0)
        ]
        if not valid_columns:
            self.game_over = True
            return False

        target_col = random.choice(valid_columns)
        row = 0
        while self._can_place(self.current_piece, target_col, row + 1):
            row += 1

        if not self._can_place(self.current_piece, target_col, row):
            self.game_over = True
            return False

        for column, piece_row in self.current_piece.cells:
            self.grid[row + piece_row][target_col + column] = self.current_piece.color

        self.process_complete_lines()
        self._advance_piece()
        self._update_game_over()
        return True

    def move_board(self, direction: str) -> bool:
        """Move and merge board values in the requested direction."""
        if self.game_over or direction not in {"left", "right", "up", "down"}:
            return False

        moved = (
            self._merge_horizontal(direction)
            if direction in {"left", "right"}
            else self._merge_vertical(direction)
        )
        self.apply_gravity()
        self.process_complete_lines()
        self._update_high_score()
        return moved

    def apply_gravity(self) -> None:
        """Move non-empty cells toward the bottom of each column."""
        for col in range(self.cols):
            values = [self.grid[row][col] for row in range(self.rows) if self.grid[row][col]]
            new_column = [0] * (self.rows - len(values)) + values
            for row in range(self.rows):
                self.grid[row][col] = new_column[row]

    def process_complete_lines(self) -> None:
        """Remove full rows and award points for cleared tetromino lines."""
        remaining_rows = []
        cleared = 0
        for row in self.grid:
            if all(row):
                cleared += 1
            else:
                remaining_rows.append(row)

        self.grid = [[0] * self.cols for _ in range(cleared)] + remaining_rows
        self.score += cleared * self.cols * 10
        self._update_high_score()

    def _clear_board(self) -> None:
        self.grid = [[0 for _ in range(self.cols)] for _ in range(self.rows)]

    @staticmethod
    def _generate_piece() -> Piece:
        shape = random.choice(TETROMINOES)
        return Piece(list(shape), random.choice(PIECE_COLORS))

    def _can_place(self, piece: Piece, column: int, row: int) -> bool:
        return all(
            0 <= column + piece_column < self.cols
            and 0 <= row + piece_row < self.rows
            and self.grid[row + piece_row][column + piece_column] == 0
            for piece_column, piece_row in piece.cells
        )

    def _advance_piece(self) -> None:
        self.current_piece = self.next_piece
        self.next_piece = self._generate_piece()

    def _update_game_over(self) -> None:
        self.game_over = not any(
            self._can_place(self.current_piece, column, 0)
            for column in range(self.cols)
        )

    def _update_high_score(self) -> None:
        self.high_score = max(self.high_score, self.score)

    def _merge_horizontal(self, direction: str) -> bool:
        moved = False
        for row_index, row in enumerate(self.grid):
            values = [value for value in row if value]
            if direction == "right":
                values.reverse()
            merged = self._merge_values(values)
            if direction == "right":
                merged.reverse()
            if merged != row:
                moved = True
            self.grid[row_index] = merged
        return moved

    def _merge_vertical(self, direction: str) -> bool:
        moved = False
        for col in range(self.cols):
            values = [self.grid[row][col] for row in range(self.rows) if self.grid[row][col]]
            if direction == "down":
                values.reverse()
            merged = self._merge_values(values)
            if direction == "down":
                merged.reverse()
            for row in range(self.rows):
                if merged[row] != self.grid[row][col]:
                    moved = True
                self.grid[row][col] = merged[row]
        return moved

    def _merge_values(self, values: list[int]) -> list[int]:
        merged = []
        index = 0
        while index < len(values):
            if index + 1 < len(values) and values[index] == values[index + 1]:
                merged_value = values[index] * 2
                merged.append(merged_value)
                self.score += merged_value
                index += 2
            else:
                merged.append(values[index])
                index += 1
        return merged + [0] * (self.cols - len(merged))
