"""Test OutputPanelHandler."""

from EasyClangComplete.plugin.utils import output_panel_handler
from unittest import TestCase

import sublime
import imp

imp.reload(output_panel_handler)

OutputPanelHandler = output_panel_handler.OutputPanelHandler


class TestOutputPanelHandler(TestCase):
    """Test that we can create an output panel."""

    def tearDown(self):
        """Cleanup method run after every test."""
        window = sublime.active_window()
        window.run_command("show_panel", {"panel": "output.UnitTesting"})

    def test_panel_creation(self):
        """Test that we can open a panel."""
        OutputPanelHandler.show("hello world")
        window = sublime.active_window()
        self.assertIsNotNone(window.active_panel())
        self.assertEquals(window.active_panel(), "output.ECC")
        panel_view = window.find_output_panel(OutputPanelHandler._PANEL_TAG)
        contents = panel_view.substr(sublime.Region(0, panel_view.size()))
        self.assertEquals(contents, "hello world")

    def test_panel_closing(self):
        """Test that we can close a panel."""
        OutputPanelHandler.show("hello world")
        window = sublime.active_window()
        self.assertEquals(window.active_panel(), "output.ECC")
        OutputPanelHandler.hide_panel()
        self.assertIsNone(window.active_panel())
