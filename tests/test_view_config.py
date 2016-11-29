"""Tests for setting up an using view configuration."""
import sublime
from os import path

from EasyClangComplete.plugin.settings.settings_manager import SettingsManager
from EasyClangComplete.plugin.view_config import ViewConfig

from EasyClangComplete.tests.gui_test_wrapper import GuiTestWrapper


class TestViewConfig(GuiTestWrapper):
    """Test view configuration."""

    def test_setup_view(self):
        """Test that setup view correctly sets up the view."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        self.check_view(file_name)
        self.tear_down()

    def test_init(self):
        """Test initializing a view configuration."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        self.set_up_view(file_name)
        manager = SettingsManager()
        settings = manager.settings_for_view(self.view)
        view_config = ViewConfig(self.view, settings)

        self.assertIsNotNone(view_config.completer)
        self.tear_down()

    def test_flags(self):
        """Test that flags are properly defined for a completer."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        self.set_up_view(file_name)
        manager = SettingsManager()
        settings = manager.settings_for_view(self.view)
        view_config = ViewConfig(self.view, settings)

        self.assertIsNotNone(view_config.completer)
        completer = view_config.completer
        self.assertEqual(len(completer.clang_flags), 12)
        # test from the start
        self.assertEqual(completer.clang_flags[0], '-x')
        self.assertEqual(completer.clang_flags[1], 'c++')
        self.assertEqual(completer.clang_flags[2], '-std=c++11')
        # test last one
        expected = path.join(path.dirname(
            path.dirname(__file__)), 'local_folder')
        self.assertEqual(completer.clang_flags[11], '-I' + expected)
        self.tear_down()

    def test_unsaved_views(self):
        """Test that we gracefully handle unsaved views."""
        # Construct an unsaved scratch view.
        self.view = sublime.active_window().new_file()
        self.view.set_scratch(True)

        # Manually set up a completer.
        manager = SettingsManager()
        settings = manager.settings_for_view(self.view)
        view_config = ViewConfig(self.view, settings)
        completer = view_config.completer
        self.assertIsNone(completer)
        self.tear_down()
