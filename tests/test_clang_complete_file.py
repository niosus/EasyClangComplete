"""Tests for cmake database generation.

Attributes:
    FlagsFile (TYPE): Description
"""
import imp
from os import path
from unittest import TestCase

from EasyClangComplete.plugin.flags_sources import flags_file
from EasyClangComplete.plugin.utils import flag
from EasyClangComplete.plugin.utils import search_scope

imp.reload(flags_file)
imp.reload(flag)
imp.reload(search_scope)

SearchScope = search_scope.TreeSearchScope

FlagsFile = flags_file.FlagsFile

Flag = flag.Flag


class TestFlagsFile(TestCase):
    """Test finding and generatgin flags from .clang_complete file.

    Attributes:
        view (TYPE): Description
    """

    def test_init(self):
        """Initialization test."""
        self.assertEqual(FlagsFile._FILE_NAME, '.clang_complete')

    def test_load_file(self):
        """Test finding and loading existing file."""
        test_file_path = path.join(
            path.dirname(__file__), 'test_files', 'test.cpp')

        flags_file = FlagsFile(['-I', '-isystem'])
        flags = flags_file.get_flags(test_file_path)
        # This flag only exists in .clang_complete to help us test that
        # we can read the flag.
        self.assertIn(Flag('', '-Wabi'), flags)

    def test_fail_to_find(self):
        """Test failing to find a .clang_complete file."""
        test_file_path = path.join(
            path.dirname(__file__), 'test_files', 'test.cpp')

        folder = path.dirname(test_file_path)
        flags_file = FlagsFile(['-I', '-isystem'])
        wrong_scope = SearchScope(from_folder=folder, to_folder=folder)
        flags = flags_file.get_flags(test_file_path, wrong_scope)
        self.assertIs(flags, None)
