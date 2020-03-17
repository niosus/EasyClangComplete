"""Test OutputPanelHandler."""
import imp
import sublime
from unittest import TestCase

from EasyClangComplete.plugin.utils import output_panel_handler

imp.reload(output_panel_handler)

OutputPanelHandler = output_panel_handler.OutputPanelHandler


class test_output_panel_handler(TestCase):
    """Test other things."""

    def test_panel_creation(self):
        """Test that we can convert time to seconds."""
        OutputPanelHandler.show("hello world")
        window = sublime.active_window()
        panel_view = window.find_output_panel(OutputPanelHandler._PANEL_TAG)
        contents = panel_view.substr(sublime.Region(0, panel_view.size()))
        self.assertEquals(contents, "hello world")
