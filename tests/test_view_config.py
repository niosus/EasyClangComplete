"""Tests for setting up an using view configuration."""
import imp
import sublime
from os import path

from EasyClangComplete.plugin.settings import settings_manager
from EasyClangComplete.plugin.settings import settings_storage
from EasyClangComplete.plugin import view_config
from EasyClangComplete.plugin import tools

from EasyClangComplete.tests import gui_test_wrapper

imp.reload(gui_test_wrapper)
imp.reload(settings_manager)
imp.reload(settings_storage)
imp.reload(view_config)
imp.reload(tools)

SettingsManager = settings_manager.SettingsManager
ViewConfig = view_config.ViewConfig
ViewConfigManager = view_config.ViewConfigManager
GuiTestWrapper = gui_test_wrapper.GuiTestWrapper
File = tools.File


class TestViewConfig(GuiTestWrapper):
    """Test view configuration."""

    def test_setup_view(self):
        """Test that setup view correctly sets up the view."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        self.check_view(file_name)

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
        p = path.join(sublime.packages_path(),
                      "User",
                      "EasyClangComplete.sublime-settings")
        if path.exists(p):
            user = sublime.load_resource(
                "Packages/User/EasyClangComplete.sublime-settings")
            if "common_flags" in user:
                # The user modified the default common flags, just skip the
                # next few tests.
                return
        completer = view_config.completer
        self.assertEqual(len(completer.clang_flags), 14)
        # test from the start
        self.assertEqual(completer.clang_flags[0], '-c')
        self.assertEqual(completer.clang_flags[1], '-fsyntax-only')
        self.assertEqual(completer.clang_flags[2], '-x')
        self.assertEqual(completer.clang_flags[3], 'c++')
        self.assertEqual(completer.clang_flags[-1], '-std=c++14')
        # test last one
        expected = path.join(path.dirname(
            path.dirname(__file__)), 'local_folder')
        self.assertEqual(completer.clang_flags[11], '-I' + expected)

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

    def test_needs_update(self):
        """Test view config changing when needed."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        self.set_up_view(file_name)
        manager = SettingsManager()
        settings = manager.settings_for_view(self.view)
        view_config = ViewConfig(self.view, settings)
        flags = view_config.completer.clang_flags
        is_update_needed = view_config.needs_update(view_config.completer,
                                                    flags)
        self.assertFalse(is_update_needed)
        flags = []
        is_update_needed = view_config.needs_update(
            view_config.completer, flags)
        self.assertTrue(is_update_needed)

    def test_needs_update_on_file_change(self):
        """Test view config changing when file changed."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test_changes.cpp')
        self.set_up_view(file_name)
        File.update_mod_time(file_name)
        is_update_needed = ViewConfig.needs_reparse(self.view)
        self.assertFalse(is_update_needed)
        self.view.window().focus_view(self.view)
        self.view.window().run_command("save")
        is_reparse_needed = ViewConfig.needs_reparse(self.view)
        self.assertTrue(is_reparse_needed)

    def test_age(self):
        """Test view config age."""
        import time
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        self.set_up_view(file_name)
        manager = SettingsManager()
        settings = manager.settings_for_view(self.view)
        view_config = ViewConfig(self.view, settings)
        self.assertTrue(view_config.get_age() < 3)
        time.sleep(3)
        self.assertTrue(view_config.get_age() > 3)
        view_config.touch()
        self.assertTrue(view_config.get_age() < 3)
        time.sleep(4)
        self.assertTrue(view_config.is_older_than(3))


class TestViewConfigManager(GuiTestWrapper):
    """Test view configuration manager."""

    def test_setup_view(self):
        """Test that setup view correctly sets up the view."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        self.check_view(file_name)

    def test_update(self):
        """Test that update is triggered."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        self.set_up_view(file_name)
        manager = SettingsManager()
        config_manager = ViewConfigManager(timer_period=1)
        settings = manager.settings_for_view(self.view)
        view_config = config_manager.load_for_view(self.view, settings)
        self.assertEqual(view_config.completer.name, "lib")
        settings.use_libclang = False
        view_config = config_manager.load_for_view(self.view, settings)
        self.assertEqual(view_config.completer.name, "bin")
        config_manager.clear_for_view(self.view.buffer_id())

    def test_remove(self):
        """Test that config is removed."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        self.set_up_view(file_name)
        manager = SettingsManager()
        config_manager = ViewConfigManager(timer_period=1)
        settings = manager.settings_for_view(self.view)
        view_config = config_manager.load_for_view(self.view, settings)
        self.assertIsNotNone(view_config)
        config_manager.clear_for_view(self.view.buffer_id())
        view_config = config_manager.get_from_cache(self.view)
        self.assertIsNone(view_config)

    def test_timer(self):
        """Test that config is removed on timer."""
        import time
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        self.set_up_view(file_name)
        manager = SettingsManager()
        config_manager = ViewConfigManager(timer_period=1)
        settings = manager.settings_for_view(self.view)
        settings.max_cache_age = 2  # seconds
        initial_period = config_manager._ViewConfigManager__timer_period
        ViewConfigManager._ViewConfigManager__timer_period = 1
        view_config = config_manager.load_for_view(self.view, settings)
        self.assertIsNotNone(view_config)
        time.sleep(3)
        view_config = config_manager.get_from_cache(self.view)
        self.assertIsNone(view_config)
        ViewConfigManager._ViewConfigManager__timer_period = initial_period
