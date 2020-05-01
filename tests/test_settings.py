"""Tests for settings."""
import sublime
import imp

from os import path

from EasyClangComplete.tests.gui_test_wrapper import GuiTestWrapper

from EasyClangComplete.plugin.settings import settings_manager
from EasyClangComplete.plugin.settings import settings_storage
from EasyClangComplete.plugin.utils import flag

imp.reload(settings_manager)
imp.reload(settings_storage)
imp.reload(flag)

SettingsManager = settings_manager.SettingsManager
SettingsStorage = settings_storage.SettingsStorage
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

    def test_parse_cmake_flags(self):
        """Testing that we can parse cmake flags."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test_wrong_triggers.cpp')
        self.set_up_view(file_name)
        current_folder = path.dirname(__file__)
        flags_sources = [
            {
                "file": "CMakeLists.txt",
                "flags": [
                    "-DBLAH={}/*".format(current_folder),
                    "-DSMTH=ON",
                    "-D XXX=1",
                    "-D FLAG=word"
                ]
            }
        ]

        self.view.settings().set("flags_sources", flags_sources)
        settings = SettingsManager().user_settings()
        settings.update_from_view(self.view, project_specific=False)
        valid, _ = settings.is_valid()
        self.assertTrue(valid)
        self.assertEquals(len(settings.flags_sources), 1)
        entry = settings.flags_sources[0]
        self.assertIn('flags', entry)
        flags = entry['flags']
        self.assertEquals(len(flags), 4)
        self.assertIn('-DSMTH=ON', flags)
        self.assertIn('-D FLAG=word', flags)
        self.assertIn('-D XXX=1', flags)
        import glob
        all_files = glob.glob(path.join(current_folder, "*"))
        for file in all_files:
            self.assertIn(file, flags[0])

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
