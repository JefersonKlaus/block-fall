# Store images

Images for the Google Play and App Store listings, in English (`en/`) and
Portuguese (`pt/`), the two languages of the app. They are made from the real
game (its rules, layout, colors, and texts) by a script, so they always match
the app:

```powershell
python -m tools.store_assets
```

This also writes the app icon used by `flet build`: `src/assets/icon.png`.
Run it again after changing the look of the app. It needs the development
requirements (`python -m pip install -r requirements-dev.txt`).

## Google Play (`google-play/`)

| File | Use | Size |
| --- | --- | --- |
| `icon-512.png` | App icon (all languages) | 512 x 512 |
| `en/feature-graphic.png`, `pt/feature-graphic.png` | Feature graphic | 1024 x 500 |
| `en/phone/*.png`, `pt/phone/*.png` | Phone screenshots (2 to 8) | 1080 x 1920 |

## App Store (`app-store/`)

| File | Use | Size |
| --- | --- | --- |
| `icon-1024.png` | App Store icon (all languages, no transparency) | 1024 x 1024 |
| `en/iphone-6.9/*.png`, `pt/iphone-6.9/*.png` | iPhone 6.9" screenshots | 1320 x 2868 |
| `en/iphone-6.5/*.png`, `pt/iphone-6.5/*.png` | iPhone 6.5" screenshots | 1284 x 2778 |
| `en/ipad-13/*.png`, `pt/ipad-13/*.png` | iPad 13" screenshots | 2064 x 2752 |

Use the `en/` images for the English store listing and the `pt/` images for
the Portuguese (Brazil / Portugal) store listing.

## Screenshots

1. `01-playing`: a game in progress (MIDDLE level, 5x5).
2. `02-line-of-three`: three squares in a line turning gold.
3. `03-new-color`: a new color unlocked at 50 points.
4. `04-all-colors`: all 5 colors unlocked.
5. `05-beginner`: the BEGINNER level (6x6).
6. `06-master`: the MASTER level (4x4).
7. `07-game-over`: a full board and the big RESTART button.

The pictures are drawn from the app's real screen state, not captured from a
phone, so the phone's own status bar is not shown, and the Restart and lock
icons are close drawings of the Material icons the app uses.
