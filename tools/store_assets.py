"""Make the app icon and the Google Play / App Store images:

    python -m tools.store_assets

Writes src/assets/icon.png (used by `flet build`) and everything under
doc/screenshot/. Needs the dev requirements (Pillow); the Roboto fonts are in tools/fonts.
"""

from tools.assets import ROOT, build


def main() -> None:
    for path in build():
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
