0:20



## Task
This is a mobile game, this is a 'one finger game', so the player uses only one finger to play it. The ideia is very simple, appears one block in the grid and you need send ALL block to rigth, dow, up or left to close a line, if you do it, you make a point.
The first goal, is fix a bug in the controls, for some reason the UP and DOWN action is not working well.
The second goal is change one rule, at this version you press when you want to block (add new one) the new rule will be, you move the blocks, you get a new block.
The last goal, is improve tests, the current version has only teste to the basic functions


## How to judge completion
Run the app, and play the entire game, you can run it in the computer or build it and play in your mobile device. So the game ends when you do not gave more space to insert a block in the grid.
After play the game, run the pytest and see the results


## Notes
This is a mobile game, this is a 'one finger game', so the player uses only one finger to play it. The ideia is very simple, appears one block in the grid and you need send ALL block to rigth, dow, up or left to close a line, if you do it, you make a point.
This is an open source project, where you can find in this URL https://github.com/JefersonKlaus/block-fall
This version has only 47 tests and some bugs, in the controls and in the UI, the ideia of this task is solve the bugs and add more tests.


## How to test

O ran the and i test it manually, adding PDFs, analyzing and reviwing the metadata, I created a new library and imported many PDFs. After I got a existent library and imported new books in there. Alfter that I ran pytest.

SETUP:
cd workspace/personal_library
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt


ACTION: flet run
RESULT: The app opened and I used it

ACTION: pytest
RESULT: 234 passed, 5 skipped in 12.7


O ran the and i test it manually, adding PDFs, analyzing and reviwing the metadata, I created a new library and imported many PDFs. After I got a existent library and imported new books in there. Alfter that I ran pytest.

Run the automated tests:

```powershell
python -m pytest
```

Tests should cover library reading and display, metadata and covers, invalid or empty libraries, refresh after export/import/undo, and all existing analysis, organization, undo, and `calibredb` integration behavior.

## Evidence

```text
ACTION: python main.py
RESULT: The app opened, books were exported, and the Calibre-like library view was verified.

ACTION: python -m pytest
RESULT: [number] passed
```


UPDATED:
pdf2calibre\metadata.py
pdf2calibre\models.py
pdf2calibre\naming.py
pdf2calibre\opf.py
pdf2calibre\organizer.py
pdf2calibre\planner.py
pdf2calibre\settings.py
pdf2calibre\ui.py
pdf2calibre\calibre.py
main.py

CREATED:
pdf2calibre\exporter.py
pdf2calibre\gallery_ui.py
pdf2calibre\library_import.py
pdf2calibre\library.py

TESTS:
tests\conftest.py
tests\test_exporter_import.py (CREATED)
tests\test_library.py (CREATED)
tests\test_metadata.py
tests\test_naming.py
tests\test_opf_calibre_settings.py
tests\test_organizer.py
tests\test_planner.py
tests\test_ui_wiring.py