"""Tests for settings."""
import sublime
import time
from os import path
from unittest import TestCase

from EasyClangComplete.plugin.settings.settings_manager import SettingsManager


class test_settings(TestCase):
    """Tests for settings."""
    def setUp(self):
        """Set up testing environment."""
        self.view = None
        # make sure we have a window to work with
        s = sublime.load_settings("Preferences.sublime-settings")
        s.set("close_windows_when_empty", False)

    def setUpView(self, filename):
        """Utility method to set up a view for a given file.

        Args:
            filename (str): The filename to open in a new view.
        """
        # Open the view.
        file_path = path.join(path.dirname(__file__), filename)
        self.view = sublime.active_window().open_file(file_path)

        # Ensure it's loaded.
        while self.view.is_loading():
            time.sleep(0.1)

    def tearDown(self):
        """Cleanup method run after every test."""
        # If we have a view, close it.
        if self.view:
            self.view.set_scratch(True)
            self.view.window().focus_view(self.view)
            self.view.window().run_command("close_file")
            self.view = None

    def test_init(self):
        """Test that settings are correctly initialized."""
        manager = SettingsManager()
        settings = manager.user_settings()
        self.assertIsNotNone(settings.verbose)
        self.assertIsNotNone(settings.include_file_folder)
        self.assertIsNotNone(settings.include_file_parent_folder)
        self.assertIsNotNone(settings.triggers)
        self.assertIsNotNone(settings.common_flags)
        self.assertIsNotNone(settings.clang_binary)
        self.assertIsNotNone(settings.flags_sources)
        self.assertIsNotNone(settings.errors_on_save)

    def test_valid(self):
        """Test validity."""
        manager = SettingsManager()
        settings = manager.user_settings()
        self.assertTrue(settings.is_valid())

    def test_populate_flags(self):
        """Testing include population."""
        # open any existing file
        self.tearDown()
        self.setUpView(path.join('test_files', 'test_wrong_triggers.cpp'))
        # now test the things
        manager = SettingsManager()
        settings = manager.user_settings()
        self.assertTrue(settings.is_valid())

        initial_common_flags = list(settings.common_flags)
        settings = manager.settings_for_view(self.view)
        dirs = settings.common_flags

        current_folder = path.dirname(self.view.file_name())
        parent_folder = path.dirname(current_folder)
        self.assertLess(len(initial_common_flags), len(dirs))
        self.assertTrue(initial_common_flags[0] in dirs)
        self.assertFalse(initial_common_flags[1] in dirs)
        self.assertTrue(("-I" + current_folder) in dirs)
        self.assertTrue(("-I" + parent_folder) in dirs)
