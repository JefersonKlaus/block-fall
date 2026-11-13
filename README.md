# Block Fall

Block Fall is a compact mobile puzzle game built with Python and
[Flet](https://flet.dev/). Slide colored squares around the board and line up
3 or more of the same color to score.

## Requirements

- Python 3.10 or newer
- Flet 1.0.5 (the latest stable release)
- Android SDK and a connected device or emulator for Android builds

## Project layout

The usual Flet layout: the app lives in `src/`, the tests in `tests/`.

```text
pyproject.toml        project and Flet build settings (app in src/)
requirements*.txt     dependencies for pip
src/
  main.py             entry point
  config.py           sizes, colors, timings, and the levels
  texts.py            every text, in English and Portuguese
  game.py             the game rules, independent of Flet
  assets/icon.png     the app icon (used by flet build)
  ui/                 the Flet interface, one small module per job
tests/                unit tests (100% coverage of src/ and tools/)
tools/                developer tools: store images and the app icon
doc/screenshot/       Google Play and App Store images
```

The code is organized by responsibility:

- [config.py](src/config.py): sizes, colors, timings, and the levels.
- [texts.py](src/texts.py): every text of the app, in English and
  Portuguese, and the rule that picks the language.
- [game.py](src/game.py): the game rules (squares, moves, lines, points, colors
  unlocked, game over), independent of Flet.
- [ui/](src/ui): the Flet interface, one small module per job:
  - [app.py](src/ui/app.py): puts the pieces together and runs the game flow
    (moves, restart, level change, the confirmation before losing a game).
  - [header.py](src/ui/header.py): the logo and the SCORE, BEST, LEVEL, and
    RESTART blocks.
  - [level_bar.py](src/ui/level_bar.py): the 5 color blocks.
  - [board.py](src/ui/board.py): the grid, sized to the screen; draws and
    moves the squares.
  - [animation.py](src/ui/animation.py): plays a move step by step (slide,
    gold, new square) with pauses that can be skipped.
  - [turns.py](src/ui/turns.py): keeps player input in order around
    animations.
  - [swipe.py](src/ui/swipe.py): turns finger movement into a move.
  - [widgets.py](src/ui/widgets.py): the look of squares, blocks, the logo,
    and dialogs.

## Local setup

Create and activate a virtual environment, then install the dependencies.
`requirements.txt` installs Flet with its `flet` command and desktop runner
(`flet[cli,desktop]`); the development requirements add the test and
store-image tools:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

## Run the application

From the project folder, run the desktop development version:

```powershell
flet run
```

`flet run` finds the app through `pyproject.toml` (`[tool.flet.app]`, path
`src`), so no file name is needed. Run on an Android device or emulator, or
in a web browser:

```powershell
flet run --android
flet run --web
```

## Build for the stores

Before the first build, set `org` and `bundle_id` in `pyproject.toml` to your
own organization. Then build the Android App Bundle for Google Play and the
iOS package for the App Store:

```powershell
flet build aab
flet build ipa
```

`flet build` takes the app from `src/` and the icon from
`src/assets/icon.png` (its background color is set in `pyproject.toml`). The
store images are in [doc/screenshot](doc/screenshot/README.md).

## Languages

The app speaks English and Portuguese. It uses Portuguese when the device's
main language is Portuguese (Brazil, Portugal, ...) and English otherwise,
and it follows the device if the language changes while the app is open. All
texts are in [src/texts.py](src/texts.py).

## The game

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
  new game on that level's grid: BEGINNER (green) 6x6, MIDDLE (yellow) 5x5,
  MASTER (red) 4x4. The game starts at MIDDLE. Once you have played a move,
  RESTART and LEVEL first ask you to confirm, because the current game would
  be lost.
- **Start:** a new game already has about 10% of the grid filled with squares
  (never already forming a line).
- **Squares:** the board holds single squares in pastel colors.
- **Levels:** the 5 blocks above the board are the 5 colors of the game, one
  per level. A game starts with 2 colors (blue and green); the others are gray
  with a lock until they are unlocked: the 3rd color at 50 points, the 4th at
  150 points (+100), and the 5th at 350 points (+200). When a level unlocks,
  its block flashes gold ("New color unlocked!") and then shows its color; the
  game goes on meanwhile. New squares only use unlocked colors.
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
- **Game over:** when the board is full; the message shows "GAME OVER". The
  blue **RESTART** block (below BEST) starts a new game at any time; the best
  score is kept, also when you change level.

The app runs in portrait (vertical) orientation: phones and tablets are locked
to portrait, and on desktop the window is a fixed 390x840 portrait window.

## Development checks

Run the complete test suite (from the project folder):

```powershell
python -m unittest -v
```

Measure test coverage (it must stay at 100%, lines and branches):

```powershell
python -m coverage run -m unittest
python -m coverage report
```

Make the store images and the app icon again after changing the look of the
app:

```powershell
python -m tools.store_assets
```

Compile all Python modules to detect syntax errors:

```powershell
python -m compileall src tools
```
