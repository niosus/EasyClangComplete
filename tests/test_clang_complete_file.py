"""Tests for cmake database generation.

Attributes:
    FlagsFile (TYPE): Description
"""
import imp
from os import path

from EasyClangComplete.plugin.flags_sources import flags_file
from EasyClangComplete.plugin import tools

from EasyClangComplete.tests.gui_test_wrapper import GuiTestWrapper

imp.reload(flags_file)
imp.reload(tools)

SearchScope = tools.SearchScope
PKG_NAME = tools.PKG_NAME

FlagsFile = flags_file.FlagsFile


class TestFlagsFile(GuiTestWrapper):
    """Test finding and generatgin flags from .clang_complete file.

    Attributes:
        view (TYPE): Description
    """

    def test_setup_view(self):
        """Test that setup view correctly sets up the view."""
        file_path = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        self.check_view(file_path)

    def test_init(self):
        """Initialization test."""
        test_file_path = path.join(
            path.dirname(__file__), 'test_files', 'test.cpp')
        self.set_up_view(test_file_path)
        self.assertEqual(FlagsFile._FILE_NAME, '.clang_complete')
        self.assertEqual(len(FlagsFile.cache), 0)
        self.assertEqual(len(FlagsFile.path_for_file), 0)

    def test_load_file(self):
        """Test finding and loading existing file."""
        test_file_path = path.join(
            path.dirname(__file__), 'test_files', 'test.cpp')
        self.set_up_view(test_file_path)

        file_name = path.join(test_file_path)
        self.assertEqual(self.view.file_name(), file_name)

        search_scope = SearchScope(from_folder=path.dirname(file_name))
        flags_file = FlagsFile(['-I', '-isystem'], search_scope)
        flags = flags_file.get_flags(file_name)
        self.assertIn('-std=c++11', flags)

    def test_fail_to_find(self):
        """Test failing to find a .clang_complete file."""
        test_file_path = path.join(
            path.dirname(__file__), 'test_files', 'test.cpp')
        self.set_up_view(test_file_path)

        file_name = path.join(test_file_path)
        self.assertEqual(self.view.file_name(), file_name)

        folder = path.dirname(file_name)
        search_scope = SearchScope(from_folder=folder, to_folder=folder)
        flags_file = FlagsFile(['-I', '-isystem'], search_scope)
        flags = flags_file.get_flags(file_name)
        self.assertIs(flags, None)
