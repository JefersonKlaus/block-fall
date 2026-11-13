"""Application and game configuration."""

# Levels (difficulty): name, grid rows, grid columns, button color.
DIFFICULTIES = (
    ("BEGINNER", 6, 6, "#93DDAA"),  # green
    ("MIDDLE", 5, 5, "#F9DF7A"),  # yellow
    ("MASTER", 4, 4, "#F28B8B"),  # red
)
DEFAULT_DIFFICULTY = 1  # MIDDLE
GRID_ROWS, GRID_COLS = DIFFICULTIES[DEFAULT_DIFFICULTY][1:3]
# Portrait window (desktop). Mobile devices are locked to portrait in ui.py.
WINDOW_WIDTH = 390
WINDOW_HEIGHT = 840
# 2048-style squares: rounded, no border, small gaps. The grid always takes
# the full width of the screen, whatever GRID_ROWS and GRID_COLS are, so the
# board squares are sized at run time. CELL_SIZE is the size of the level
# blocks above the grid.
CELL_SIZE = 30
CELL_SPACING = 4
# Space around the board (page, layout, and the board's own frame). The grid
# fills whatever width is left.
PAGE_PADDING = 10
LAYOUT_PADDING = 5
BOARD_PADDING = 8
# Header blocks (score, best, restart): all the same size.
HEADER_BLOCK_WIDTH = 64
HEADER_BLOCK_HEIGHT = 50
# Play by touch: a finger must move at least this far (px) to count as a swipe.
SWIPE_MIN_DISTANCE = 24
# Screen width to assume until the real one is known (a small phone).
FALLBACK_PAGE_WIDTH = 320
TILE_RADIUS = 4

# Pastel theme: light backgrounds, dark readable text.
COLOR_BG = "#FFF8F1"
COLOR_BOARD_BG = "#E4D9F0"
COLOR_EMPTY = "#F7F3FB"
COLOR_TEXT = "#4B4453"
COLOR_MUTED_TEXT = "#857B93"
COLOR_STATUS = "#B4536A"
# Restart buttons (the header block and the big one at game over): blue.
COLOR_RESTART = "#7FB3F5"
# Second color of the logo's wordmark ("Block" + "Fall").
COLOR_LOGO_ACCENT = "#7A56BF"
# Matched squares flash gold before they disappear.
COLOR_GOLD = "#FFD700"
GOLD_FLASH_SECONDS = 0.15
# Like 2048: squares slide to their new place, new squares pop in.
ANIMATION_SECONDS = 0.1
# New squares are first shown tiny, then grown after this short delay.
POP_START_SECONDS = 0.03

# Square colors, one per level (pastel, but easy to tell apart).
BLUE, GREEN, RED, PEACH, PURPLE = 1, 2, 3, 4, 5
TILE_COLORS = {
    0: COLOR_EMPTY,
    BLUE: "#8EC5FF",
    GREEN: "#9EE5B8",
    RED: "#FF9AA2",
    PEACH: "#FFC89A",
    PURPLE: "#C9A7F5",
}
# Score needed for each color: 2 to start, then +50, +100, +200 points.
UNLOCK_SCORES = (0, 0, 50, 150, 350)
# A newly unlocked level block shows gold this long, then its color. As fast
# as the gold in the grid, and it never holds up the game.
UNLOCK_FLASH_SECONDS = GOLD_FLASH_SECONDS
# Level blocks of colors not unlocked yet: gray with a lock.
COLOR_LOCKED = "#B8B3BF"
COLOR_LOCK_ICON = "#5F5969"
# Part of the grid already filled with squares when a game starts (10%).
START_FILL = 0.10
