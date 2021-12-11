"""Test CppProperties flags generation."""
import imp
import platform
from os import path, environ
from unittest import TestCase

from EasyClangComplete.plugin.flags_sources import CppProperties
from EasyClangComplete.plugin.utils import tools
from EasyClangComplete.plugin.utils import flag
from EasyClangComplete.plugin.utils import file
from EasyClangComplete.plugin.utils import search_scope

imp.reload(CppProperties)
imp.reload(tools)
imp.reload(flag)
imp.reload(file)
imp.reload(search_scope)

CppProperties = CppProperties.CppProperties
SearchScope = search_scope.TreeSearchScope
Flag = flag.Flag
File = file.File


def _get_test_folder(name):
    return path.join(path.dirname(__file__), 'CppProperties_files', name)


class TestCppProperties(TestCase):
    """Test generating flags with a 'CppProperties.json' file."""

    def test_get_all_flags(self):
        """Test if CppProperties.json is found."""
        include_prefixes = ['-I']
        db = CppProperties(include_prefixes)

        expected = [
            Flag('-I', path.normpath('/folder/include/path')),
            Flag('-I', path.normpath('/another/file/path')),
        ]

        scope = SearchScope(from_folder=_get_test_folder('simple'))
        self.assertEqual(expected, db.get_flags(search_scope=scope))

    def test_expand_environment_variables(self):
        """Test environment variables are expanded."""
        include_prefixes = ['-I']
        db = CppProperties(include_prefixes)
        environ['TEST_VARIABLE_TO_EXPAND'] = '/lib_include_dir'

        expected = [
            Flag('-I', path.normpath('/lib_include_dir')),
        ]

        scope = SearchScope(from_folder=_get_test_folder('environment'))
        self.assertEqual(expected, db.get_flags(search_scope=scope))

    def test_no_db_in_folder(self):
        """Test if no json is found."""
        if platform.system() == "Darwin":
            # This test is disabled as the current path is trying to reach a
            # network resource on MacOS. I guess we have to deal with this at
            # some point later.
            return
        include_prefixes = ['-I']
        db = CppProperties(include_prefixes)

        expected = None

        self.assertEqual(expected, db.get_flags(
            File.canonical_path('/home/user/dummy_main.cpp')))

    def test_empty_include_and_defines(self):
        """Test that empty fields are handled correctly."""
        include_prefixes = ['-I']
        db = CppProperties(include_prefixes)

        expected = []

        scope = SearchScope(from_folder=_get_test_folder('empty'))
        self.assertEqual(expected, db.get_flags(search_scope=scope))
