"""Tests for cmake database generation."""
import sublime
import time
from unittest import TestCase

from EasyClangComplete.plugin.utils.tools import PKG_NAME


class GuiTestWrapper(TestCase):
    """A class that makes gui tests easier.

    Attributes:
        view (sublime.View): Current view.
    """

    def setUp(self):
        """Prepare the view every run."""
        # Ensure we have a window to work with.
        s = sublime.load_settings("Preferences.sublime-settings")
        s.set("close_windows_when_empty", False)
        s = sublime.load_settings(PKG_NAME + ".sublime-settings")
        s.set("verbose", True)
        s.set("cmake_flags_priority", "overwrite")
        self.view = None

    def tearDown(self):
        """Cleanup method run after every test."""
        # If we have a view, close it.
        if self.view:
            self.view.set_scratch(True)
            self.view.window().focus_view(self.view)
            self.view.window().run_command("close_file")
            self.view = None

    def set_up_view(self, file_path=None, cursor_position=None):
        """Open the view and wait until its open.

        Args:
            file_path (str): The path to a file to open in a new view.
            cursor_position (ZeroIndexedRowCol): row and column of the cursor.
        """
        # Open the view.
        if file_path:
            self.view = sublime.active_window().open_file(file_path)
        else:
            self.view = sublime.active_window().new_file()
        self.view.settings().set("disable_easy_clang_complete", True)

        # Ensure it's loaded.
        while self.view.is_loading():
            time.sleep(0.1)

        if cursor_position:
            self.view.sel().clear()
            self.view.sel().add(
                sublime.Region(cursor_position.as_1d_location(self.view)))

    def get_row(self, row):
        """Get text of a particular row.

        Args:
            row (int): number of row

        Returns:
            str: row contents
        """
        return self.view.substr(self.view.line(self.view.text_point(row, 0)))

    def check_view(self, file_path):
        """Test that setup view correctly sets up the view."""
        self.set_up_view(file_path)

        self.assertEqual(self.view.file_name(), file_path)
        file = open(file_path, 'r')
        row = 0
        line = file.readline()
        while line:
            self.assertEqual(line[:-1], self.get_row(row))
            row += 1
            line = file.readline()
        file.close()
