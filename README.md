# Block Fall

Block Fall is a compact mobile puzzle game built with Python and
[Flet](https://flet.dev/). Slide colored squares around the board and line up
3 or more of the same color to score.

## Requirements

- Python 3.10 or newer
- Flet 1.0.5 (the latest stable release), installed with the project
- Android builds: Windows, macOS, or Linux; `flet build` installs the rest
  (see [Build for Android](#build-for-android))
- iOS builds: a Mac with Xcode and an Apple Developer account (see
  [Build for iOS](#build-for-ios))

## Project layout

The usual Flet layout: the app lives in `src/`, the tests in `tests/`.

```text
pyproject.toml        project, dependencies, pytest, and Flet build settings
src/
  main.py             entry point
  config.py           sizes, colors, timings, and the levels
  texts.py            every text, in English and Portuguese
  game.py             the game rules, independent of Flet
  saved.py            what is saved on the device (bests, tutorial seen)
  assets/icon.png     the app icon (used by flet build)
  assets/splash.png   the launch screen picture (used by flet build)
  ui/                 the Flet interface, one small module per job
tests/                pytest tests (100% coverage of src/ and tools/)
tools/                developer tools: the app icon, launch screen, and store images
doc/screenshot/       Google Play and App Store images
```

The code is organized by responsibility:

- [config.py](src/config.py): sizes, colors, timings, and the levels.
- [texts.py](src/texts.py): every text of the app, in English and
  Portuguese, and the rule that picks the language.
- [game.py](src/game.py): the game rules (squares, moves, lines, points, colors
  unlocked, game over), independent of Flet.
- [saved.py](src/saved.py): what the app saves on the device (Flet's
  `SharedPreferences`) between launches: the best score of each level, and
  whether the player has seen how to play.
- [ui/](src/ui): the Flet interface, one small module per job:
  - [app.py](src/ui/app.py): puts the pieces together and runs the game flow
    (moves, restart, level change, the confirmation before losing a game).
  - [header.py](src/ui/header.py): the logo and the SCORE, BEST, LEVEL, and
    RESTART blocks.
  - [level_bar.py](src/ui/level_bar.py): the 5 color blocks.
  - [tutorial.py](src/ui/tutorial.py): how to play, in 3 small pictures, and
    the HOW TO PLAY button that opens it.
  - [game_end.py](src/ui/game_end.py): what shows when a game is over (the
    points above the color blocks, the big RESTART button).
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

All dependencies are declared in `pyproject.toml` and installed with
`pip install -e`, **always inside a virtual environment** (`.venv`, in the
project folder). Create and activate it, then install the project with its
development tools. You need Python 3.10 or newer (`python3 --version`).

On **Linux** (and macOS):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

On Debian and Ubuntu, install Python's virtual environment support first
(once): `sudo apt install python3-venv`.

On **Windows** (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Activate the environment again in every new terminal (`source
.venv/bin/activate`, or `.venv\Scripts\Activate.ps1`): the prompt then starts
with `(.venv)`, and `python`, `pip`, `pytest`, and `flet` are the project's.
Keep the quotes around `".[dev]"`: without them, zsh (the macOS shell) reads
the square brackets as a file pattern.

### If the installation fails on Linux

- `error: externally-managed-environment`: pip was run outside the virtual
  environment. Recent Debian and Ubuntu versions do not let pip install into
  the system's Python. Activate the environment (`source .venv/bin/activate`)
  and run `python -m pip install -e ".[dev]"` again. Do not use `sudo pip` or
  `--break-system-packages`.
- `The virtual environment was not created successfully because ensurepip is
  not available`: run `sudo apt install python3-venv`, delete the unfinished
  environment (`rm -rf .venv`), and create it again.
- `Command 'python' not found`: on Linux the command is `python3` until the
  environment is active; inside it, `python` works too.
- `requires a different Python`: your Python is older than 3.10 (Ubuntu
  22.04 and newer already have a recent enough one). Install a newer Python,
  then create the environment with it, e.g. `rm -rf .venv` and
  `python3.12 -m venv .venv`.
- `flet run` then fails with a missing library (such as `libgtk-3.so.0`): the
  desktop window needs GTK 3 (`sudo apt install libgtk-3-0`). The first
  `flet run` also downloads Flet's desktop app once, so it needs the internet.

What the command does:

- `-e` (editable) installs the project from this folder instead of copying
  it: `src/` is added to the environment's import path, so `import game`,
  `import ui`, ... work from anywhere, and your code changes apply at once,
  with no reinstall.
- `.` installs what the app itself needs: `flet` (the `dependencies` list in
  `pyproject.toml`). This is also exactly what `flet build` packs into the
  phone app.
- `[dev]` adds the development tools (the `dev` list under
  `[project.optional-dependencies]`): the `flet` command and the desktop
  runner (`flet[cli,desktop]`), `pytest` and `coverage` for the tests, and
  `pillow` for the store images.

`python -m pip install -e .` alone installs only what the app needs. That is
not enough to develop: it has no `flet` command to run or build the app.

To add a dependency, add it to `pyproject.toml` (pinned with `==`, like the
others) and run `python -m pip install -e ".[dev]"` again:

- a package the app imports goes in `dependencies`, so that `flet build`
  puts it in the phone app;
- a development tool goes in the `dev` list, so that it stays out of the
  phone app.

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

`flet run --android` (and `flet run --ios` on an iPhone) is the quickest way
to try the app on a phone, with no build: it prints a QR code that you scan
with the phone's camera to open the app in the Flet app (install "Flet" from
Google Play or the App Store first; the phone and the computer must be on the
same Wi-Fi network).

## Build for Android and iOS

`flet build` turns the app into a real Android or iOS app. It takes the code
from `src/` (`[tool.flet.app]`), the icon from `src/assets/icon.png` (its
background color is set in `pyproject.toml`), the launch screen (see
[Launch screen](#launch-screen)), and the packages listed in `dependencies`,
and writes the result to `build/<target>/` (ignored by git).

Before the first build:

1. Set `org` and `bundle_id` in `pyproject.toml` (`[tool.flet]`) to your own
   organization, e.g. `com.yourcompany` and `com.yourcompany.blockfall`. The
   bundle id becomes the Android package name and the iOS bundle id; it
   cannot change once the app is published.
2. Check the version: the version shown to users is `version` in
   `[project]`. Each upload to a store also needs a higher build number:
   pass `--build-number 2`, `3`, ... to `flet build` (or set
   `build_number` in `[tool.flet]`).

The first build downloads the Flutter SDK that Flet 1.0.5 needs (into
`~/flutter/`) and asks before installing it; add `--yes` to any `flet build`
command to accept without being asked. `flet doctor` shows what is
installed, and `flet clean` deletes the `build/` folder for a fresh build.

### Launch screen

While the app starts, the phone shows its launch screen (splash screen): the
logo's mark above "Block Fall", centered on the app's cream background. It
comes from two places, both picked up by every `flet build` (Android, iOS,
and web):

- the picture `src/assets/splash.png` (1024 x 1024, transparent around the
  logo), made with the app icon by `python -m tools.store_assets`. It shows
  at 256 x 256 dp, and everything stays inside the middle circle that
  Android 12 and newer show, so no phone crops it;
- the background color, `[tool.flet.splash]` in `pyproject.toml`: the app's
  cream, also in dark mode (the app has no dark theme).

The launch screen only exists in built apps (`flet build`, `flet debug`):
`flet run` starts straight in the game. `flet build` notices by itself when
`splash.png` or the colors change.

### Build for Android

Android builds run on Windows, macOS, and Linux. On the first build,
`flet build` also installs a Java JDK 17 (into `~/java/`) and the Android SDK
(into `~/Android/sdk`, or it uses the one from Android Studio).

Try a debug build on a connected phone (with USB debugging on) or an
emulator (`flet devices` lists them, `flet emulators` lists and starts
emulators):

```powershell
flet debug android
```

Build an APK to install directly on a phone:

```powershell
flet build apk
adb install build/apk/block-fall.apk
```

`adb` is in the `platform-tools` folder of the Android SDK; you can also copy
the `.apk` file to the phone and open it there. Add `--split-per-abi` to get
one smaller APK per processor type instead of a single one for all of them.

Build the Android App Bundle (`.aab`) for Google Play:

```powershell
flet build aab
```

The result is `build/aab/block-fall.aab`. Google Play only accepts bundles
signed with your upload key. Create the key once (`keytool` comes with a
Java JDK, for example the one in `~/java/`):

```powershell
keytool -genkey -v -keystore upload-keystore.jks -keyalg RSA -keysize 2048 -validity 10000 -alias upload
```

Keep `upload-keystore.jks` and its passwords safe and out of git (`*.jks` is
in `.gitignore`): every future update must be signed with the same key. Then
sign the bundle when you build it. The passwords are read from environment
variables, so they never end up in a file:

```powershell
$env:FLET_ANDROID_SIGNING_KEY_STORE_PASSWORD = "your store password"
$env:FLET_ANDROID_SIGNING_KEY_PASSWORD = "your key password"
flet build aab --android-signing-key-store upload-keystore.jks --android-signing-key-alias upload --build-number 2
```

(On macOS or Linux, set the variables with
`export FLET_ANDROID_SIGNING_KEY_STORE_PASSWORD="..."`.) Instead of the two
options, you can set `key_store` and `key_alias` under
`[tool.flet.android.signing]` in `pyproject.toml`; never put the passwords
there. Upload the `.aab` in the Google Play Console; the store images are in
[doc/screenshot](doc/screenshot/README.md).

### Build for iOS

iOS builds only run on a Mac, with:

- Xcode (from the Mac App Store), opened once to accept its license and
  install the iOS platform, and its command line tools
  (`xcode-select --install`);
- an Apple Developer account (the paid Apple Developer Program is needed for
  the App Store and TestFlight).

Try the app in the iOS Simulator (no signing needed):

```bash
flet build ios-simulator
open -a Simulator
xcrun simctl install booted build/ios-simulator/*.app
```

Or run a debug build on a connected iPhone (it is signed with your team: pass
your team id, see below):

```bash
flet debug ios --ios-team-id ABCDE12345
```

Build the iOS App Store package (`.ipa`). Apple requires it to be signed, so
first, in your Apple Developer account:

1. Register the bundle id (the `bundle_id` from `pyproject.toml`) and create
   the app in App Store Connect.
2. Install an "Apple Distribution" certificate in your Mac's keychain (Xcode,
   Settings, Accounts, Manage Certificates).
3. Create an "App Store Connect" provisioning profile for the bundle id, then
   download it and double-click it to install it.

Then build, with your team id (shown in your Apple Developer account, under
Membership) and the name of the provisioning profile:

```bash
flet build ipa --ios-team-id ABCDE12345 --ios-export-method app-store-connect --ios-provisioning-profile "Block Fall App Store" --ios-signing-certificate "Apple Distribution" --build-number 2
```

The result is in `build/ipa/`. Upload it to App Store Connect with Apple's
Transporter app, then publish it through TestFlight or the App Store. To
install the app on your own registered devices instead, use
`--ios-export-method release-testing` with an "Ad Hoc" provisioning profile.
Without a provisioning profile, `flet build ipa` only makes an Xcode archive
(`.xcarchive`) and no `.ipa`.

To avoid typing these options every time, put them in `pyproject.toml`:

```toml
[tool.flet.ios]
team_id = "ABCDE12345"
export_method = "app-store-connect"
provisioning_profile = "Block Fall App Store"
signing_certificate = "Apple Distribution"
```

## Languages

The app speaks English and Portuguese. It uses Portuguese when the device's
main language is Portuguese (Brazil, Portugal, ...) and English otherwise,
and it follows the device if the language changes while the app is open. All
texts are in [src/texts.py](src/texts.py).

## The game

The board is a grid of rounded squares with small gaps (like 2048). Its size
depends on the level, and whatever its size, the grid fills the full width of
the screen. On a short screen (such as 360 x 640) it gets a little narrower
instead, so that everything fits, the final score of game over included. The
app uses a soft pastel theme, with a logo (a mini board with a gold line of 3,
and "Block / Fall") in place of the title.

The header (the logo, and the blocks SCORE and BEST with LEVEL and RESTART
below them) stays at the top; the blocks reach from the middle of the screen
to its right side, the logo takes the left half. The 5 color blocks, the
message, and the grid
sit at the bottom, just above a space kept for the big blue RESTART button
that appears when the game is over. There are no buttons to move: you play by
touch.

### How to play

The first time the app starts, a short tutorial shows how to play, in 3 small
pictures (a board before and after a swipe): all the squares slide the way
you swipe; a new square then appears on the other side; and 3 of a color in a
line turn gold and disappear, for points. The **HOW TO PLAY** button at the
bottom of the screen shows it again at any time (at game over, the big RESTART
button takes its place). The pictures are checked by the tests against the
real game rules, so they always show what the game really does.

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
  with a lock until they are unlocked, one more every 50 points: the 3rd
  color at 50 points, the 4th at 100, and the 5th at 150. When a level unlocks,
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
- **Game over:** when the board is full. Above the 5 color blocks, the points
  of that game appear in color ("You scored 42 points!"), with "GAME OVER"
  under them, and the big blue RESTART button appears at the bottom. The rest
  of the screen stays as it is (the message under the blocks too). The blue
  **RESTART** block (below BEST) starts a new game at any time.
- **Best score:** each level (BEGINNER, MIDDLE, MASTER) has its own best
  score: BEST shows the best of the current level, and changes with it when
  you change level. The bests are saved on the device, so they are still
  there the next time the app starts (on a phone, on the desktop, and in the
  browser alike).

The app runs in portrait (vertical) orientation: phones and tablets are locked
to portrait, and on desktop the window is a fixed 390x840 portrait window. On
a phone, the app stays clear of the status bar (and the notch) at the top and
of the home indicator at the bottom, and the grid is sized to the room left
between them.

## Development checks

The tests use [pytest](https://docs.pytest.org/) (installed by
`pip install -e ".[dev]"`; its settings are in `pyproject.toml`). Run the
complete test suite from the project folder:

```powershell
python -m pytest
```

Useful variations:

```powershell
python -m pytest -v                         # one line per test
python -m pytest tests/test_game.py         # one file
python -m pytest -k swipe                   # only the tests whose name has "swipe"
python -m pytest -x                         # stop at the first failure
```

Shared fixtures (for example `sleep`, which makes the animation pauses
instant) are in [tests/conftest.py](tests/conftest.py).

Measure test coverage (it must stay at 100%, lines and branches):

```powershell
python -m coverage run -m pytest
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
