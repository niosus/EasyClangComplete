"""Tests for setting up an using view configuration."""
from os import path

from EasyClangComplete.plugin.settings.settings_manager import SettingsManager
from EasyClangComplete.plugin.view_configuration import ViewConfig

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
        """Test that the completer is properly initialized."""
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
        """Test that the completer is properly initialized."""
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
