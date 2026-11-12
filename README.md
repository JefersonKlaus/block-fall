# Block Fall

Block Fall is a compact mobile puzzle game built with Python and
[Flet](https://flet.dev/). Place randomly selected tetrominoes, rotate them
before placement, and clear complete rows.

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
- [game.py](game.py): 8x8 board, random tetrominoes, and game rules,
  independent of Flet.
- [ui.py](ui.py): Flet controls, layout, and event handling.

The board is an 8x8 square with small 20x20 pixel cells so it fits comfortably
on a mobile screen. Each new piece is randomly selected from the seven classic
tetromino shapes: I, O, T, S, Z, J, and L. The player can rotate a piece, move all placed blocks left or right, and drop
the current piece. The drop column is chosen randomly.

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
