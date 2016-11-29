"""Tests for setting up an using view configuration."""
import imp
import sublime
from os import path

from EasyClangComplete.plugin.settings import settings_manager
from EasyClangComplete.plugin import view_config

from EasyClangComplete.tests import gui_test_wrapper

imp.reload(settings_manager)
imp.reload(view_config)
imp.reload(gui_test_wrapper)

SettingsManager = settings_manager.SettingsManager
ViewConfig = view_config.ViewConfig
ViewConfigManager = view_config.ViewConfigManager
GuiTestWrapper = gui_test_wrapper.GuiTestWrapper


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

    def test_needs_update(self):
        """Test initializing a view configuration."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        self.set_up_view(file_name)
        manager = SettingsManager()
        settings = manager.settings_for_view(self.view)
        view_config = ViewConfig(self.view, settings)
        needs_update = view_config.needs_update(
            view_config.completer, view_config.completer.clang_flags)
        self.assertFalse(needs_update)
        flags = []
        needs_update = view_config.needs_update(
            view_config.completer, flags)
        self.assertTrue(needs_update)
        self.tear_down()


class TestViewConfigManager(GuiTestWrapper):
    """Test view configuration manager."""

    def test_setup_view(self):
        """Test that setup view correctly sets up the view."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        self.check_view(file_name)
        self.tear_down()

    def test_update(self):
        """Test that update is triggered."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        self.set_up_view(file_name)
        manager = SettingsManager()
        config_manager = ViewConfigManager()
        settings = manager.settings_for_view(self.view)
        view_config = config_manager.get_config_for_view(self.view, settings)
        self.assertEqual(view_config.completer.name, "lib")
        settings.use_libclang = False
        view_config = config_manager.get_config_for_view(self.view, settings)
        self.assertEqual(view_config.completer.name, "bin")
        self.tear_down()

    def test_cache(self):
        """Test that configuration survives view reopening."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        self.set_up_view(file_name)
        manager = SettingsManager()
        config_manager = ViewConfigManager()
        settings = manager.settings_for_view(self.view)
        config_1 = config_manager.get_config_for_view(self.view, settings)
        self.tear_down()
        self.set_up_view(file_name)
        config_2 = config_manager.get_config_for_view(self.view, settings)
        self.assertIs(config_1, config_2)
        self.tear_down()
