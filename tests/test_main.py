"""Tests for the application entry point."""

import importlib
import runpy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import ui

MAIN_PATH = Path(__file__).resolve().parent.parent / "main.py"


class EntryPointTests(unittest.TestCase):
    def test_running_as_script_starts_flet_with_ui_main(self):
        with patch("flet.run") as run:
            runpy.run_path(str(MAIN_PATH), run_name="__main__")
        run.assert_called_once_with(ui.main)

    def test_importing_does_not_start_the_app(self):
        sys.modules.pop("main", None)
        with patch("flet.run") as run:
            module = importlib.import_module("main")
        run.assert_not_called()
        self.assertIs(module.main, ui.main)
