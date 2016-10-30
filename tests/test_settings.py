"""Tests for settings
"""
import sublime
import sys
import time
from os import path
from unittest import TestCase
sys.path.append(path.dirname(path.dirname(__file__)))

from plugin.plugin_settings import Settings


class test_settings(TestCase):
    """Tests for settings
    """
    def setUp(self):
        """Set up testing environment
        """
        self.view = None
        # make sure we have a window to work with
        s = sublime.load_settings("Preferences.sublime-settings")
        s.set("close_windows_when_empty", False)

    def setUpView(self, filename):
        """
        Utility method to set up a view for a given file.

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
        """ Cleanup method run after every test. """

        # If we have a view, close it.
        if self.view:
            self.view.set_scratch(True)
            self.view.window().focus_view(self.view)
            self.view.window().run_command("close_file")
            self.view = None

    def test_init(self):
        """Test that settings are correctly initialized

        """
        settings = Settings()
        self.assertIsNotNone(settings.subl_settings)
        # test other settings
        self.assertIsNotNone(settings.verbose)
        self.assertIsNotNone(settings.include_file_folder)
        self.assertIsNotNone(settings.include_file_parent_folder)
        self.assertIsNotNone(settings.triggers)
        self.assertIsNotNone(settings.common_flags)
        self.assertIsNotNone(settings.clang_binary)
        self.assertIsNotNone(settings.search_clang_complete_file)
        self.assertIsNotNone(settings.errors_on_save)

    def test_valid(self):
        """Test validity

        """
        settings = Settings()
        self.assertTrue(settings.is_valid())

    def test_populate_flags(self):
        """Testing include population
        """
        # open any existing file
        self.tearDown()
        self.setUpView('test_wrong_triggers.cpp')
        # now test the things
        settings = Settings()
        self.assertTrue(settings.is_valid())
        settings.include_file_folder = True
        settings.include_file_parent_folder = True
        settings.common_flags = [
            "-I" + path.realpath("/$project_name/src"),
            "-I" + path.realpath("/test/test")
        ]
        initial_flags = list(settings.common_flags)
        dirs = settings.populate_common_flags(self.view)

        current_folder = path.dirname(self.view.file_name())
        parent_folder = path.dirname(current_folder)
        self.assertLess(len(initial_flags), len(dirs))
        self.assertFalse(initial_flags[0] in dirs)
        self.assertTrue(initial_flags[1] in dirs)
        self.assertTrue(("-I" + current_folder) in dirs)
        self.assertTrue(("-I" + parent_folder) in dirs)
