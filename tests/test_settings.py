"""Tests for settings."""
import sublime
import imp

from os import path

from EasyClangComplete.tests.gui_test_wrapper import GuiTestWrapper

from EasyClangComplete.plugin.settings import settings_manager
from EasyClangComplete.plugin.utils import flag

imp.reload(settings_manager)
imp.reload(flag)

SettingsManager = settings_manager.SettingsManager
Flag = flag.Flag


class test_settings(GuiTestWrapper):
    """Test settings."""

    def test_setup_view(self):
        """Test that setup view correctly sets up the view."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        self.check_view(file_name)

    def test_init(self):
        """Test that settings are correctly initialized."""
        manager = SettingsManager()
        settings = manager.user_settings()
        self.assertIsNotNone(settings.verbose)
        self.assertIsNotNone(settings.triggers)
        self.assertIsNotNone(settings.common_flags)
        self.assertIsNotNone(settings.clang_binary)
        self.assertIsNotNone(settings.flags_sources)
        self.assertIsNotNone(settings.show_errors)
        self.assertIsNotNone(settings.valid_lang_syntaxes)

    def test_valid(self):
        """Test validity."""
        manager = SettingsManager()
        settings = manager.user_settings()
        valid, _ = settings.is_valid()
        self.assertTrue(valid)

    def test_populate_flags(self):
        """Testing include population."""
        # open any existing file
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test_wrong_triggers.cpp')
        self.set_up_view(file_name)
        # now test the things
        manager = SettingsManager()
        settings = manager.user_settings()
        valid, _ = settings.is_valid()
        self.assertTrue(valid)

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

        initial_common_flags = list(settings.common_flags)
        settings = manager.settings_for_view(self.view)
        dirs = settings.common_flags

        self.assertTrue(len(initial_common_flags) <= len(dirs))

        reference_flag_0 = Flag.Builder().from_unparsed_string(
            initial_common_flags[0]).build()
        self.assertIn(reference_flag_0, dirs)

        reference_flag_1 = Flag.Builder().from_unparsed_string(
            initial_common_flags[1]).build()
        self.assertNotIn(reference_flag_1, dirs)
