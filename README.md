# Block Fall

Block Fall is a compact mobile puzzle game built with Python and
[Flet](https://flet.dev/). Slide colored squares around the board and line up
3 or more of the same color to score.

## Requirements

- Python 3.10 or newer
- Flet 1.1.2
- Android SDK and a connected device or emulator for Android builds

## Local setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install the project dependencies:

```

Install development and test dependencies:

```powershell
python -m pip install -r requirements-dev.txt
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

### Editable development installation

The command below is commonly used by Python packages that have a
`pyproject.toml` file:

```powershell
python -m pip install -e ".[dev]"
```

The `-e` option installs the project in editable mode, so source changes are
available immediately without reinstalling. The `.[dev]` part means "install
this project and its optional `dev` dependencies". This project currently uses
`requirements.txt` instead, so use `python -m pip install -r requirements.txt`
for the supported setup command.

## Run the application

Run the desktop development version:

```powershell
flet run main.py
```

Run on an Android device or emulator:

```powershell
flet run --android main.py
```

The application entry point is [main.py](main.py). The code is organized by
responsibility:

- [config.py](config.py): shared visual and board configuration.
- [game.py](game.py): 10x10 board, squares, and game rules, independent of
  Flet.
- [ui.py](ui.py): Flet controls, animation, and event handling.

The board is a grid of rounded squares with small gaps (like 2048). Its size
depends on the level, and whatever its size, the grid always fills the full
width of the screen. The app uses a soft pastel theme, with a logo (a mini
board with a gold line of 3, and "Block / Fall") in place of the title.

The header (the logo, and the blocks SCORE and BEST with LEVEL and RESTART
below them) stays at the top. The 5 color blocks, the message, and the grid
sit at the bottom, just above a space kept for the big blue RESTART button
that appears when the game is over. There are no buttons to move: you play by
touch.

### How to play

- **Level:** tap the LEVEL block (below SCORE) to switch level; it starts a
  new game on that level's grid: BEGINNER (green) 12x12, MIDDLE (yellow) 8x8,
  MASTER (red) 6x6. The game starts at BEGINNER. Once you have played a move,
  RESTART and LEVEL first ask you to confirm, because the current game would
  be lost.
- **Start:** a new game already has about 10% of the grid filled with squares
  (never already forming a line).
- **Squares:** the board holds single squares in pastel colors.
- **Levels:** the 5 blocks above the board are the 5 colors of the game, one
  per level. A game starts with 2 colors (blue and green); the others are gray
  with a lock until they are unlocked: the 3rd color at 50 points, the 4th at
  150 points (+100), and the 5th at 350 points (+200). When a level unlocks,
  its block flashes gold ("New color unlocked!") and then shows its color. New
  squares only use unlocked colors.
- **Moves:** swipe left, right, up, or down anywhere below the header (with a
  finger, or by dragging the mouse on desktop). Every square slides as far as
  it can go. As in 2048, you see the squares slide, but squares never merge.
  You can swipe again at any time, even during an animation: the swipe is
  never lost and the animation hurries up.
- **New square:** every move adds one new square, in a random unlocked color,
  on the opposite side of the board: push right and it appears on the left edge,
  push up and it appears on the bottom edge, and so on, at a random free
  position along that edge.
- **Points:** 3 or more squares of the same color in a horizontal or vertical
  line flash gold and disappear. The first 3 squares of a line are worth
  1 point each, every extra square 2 points: 3 in a line = 3 points,
  4 = 3 + 2 = 5, 5 = 3 + 2 + 2 = 7. Two lines at once both score.
- **Game over:** when the board is full. The blue **RESTART** block (below
  BEST) starts a new game at any time; the best score is kept, also when you
  change level.

The app runs in portrait (vertical) orientation: phones and tablets are locked
to portrait, and on desktop the window is a fixed 390x840 portrait window.

## Development checks

Run the complete test suite:

```powershell
python -m unittest discover -s tests -v
```

Measure test coverage:

```powershell
python -m coverage run -m unittest discover -s tests
python -m coverage report -m
```

Compile all Python modules to detect syntax errors:

```powershell
python -m compileall .
```
