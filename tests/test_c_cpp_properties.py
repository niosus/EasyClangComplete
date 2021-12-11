"""Test c_cpp_properties flags generation."""
import imp
import platform
from os import path, environ
from unittest import TestCase

from EasyClangComplete.plugin.flags_sources import c_cpp_properties
from EasyClangComplete.plugin.utils import tools
from EasyClangComplete.plugin.utils import flag
from EasyClangComplete.plugin.utils import file
from EasyClangComplete.plugin.utils import search_scope


imp.reload(c_cpp_properties)
imp.reload(tools)
imp.reload(flag)
imp.reload(file)
imp.reload(search_scope)

CCppProperties = c_cpp_properties.CCppProperties
SearchScope = search_scope.TreeSearchScope
Flag = flag.Flag
File = file.File


class TestCCppProperties(TestCase):
    """Test generating flags with a 'c_cpp_properties.json' file."""

    def test_get_all_flags(self):
        """Test if c_cpp_properties.json is found."""
        include_prefixes = ['-I']
        db = CCppProperties(include_prefixes)

        expected = [Flag('-I', path.normpath('/lib_include_dir')),
                    Flag('', '-Dlib_EXPORTS')]
        path_to_db = path.join(path.dirname(__file__),
                               'c_cpp_properties_files',
                               'simple')
        scope = SearchScope(from_folder=path_to_db)
        self.assertEqual(expected, db.get_flags(search_scope=scope))

    def test_expand_environment_variables(self):
        """Test environment variables are expanded."""
        include_prefixes = ['-I']
        db = CCppProperties(include_prefixes)
        environ['TEST_VARIABLE_TO_EXPAND'] = '/lib_include_dir'

        expected = [Flag('-I', path.normpath('/lib_include_dir')),
                    Flag('', '-Dlib_EXPORTS')]
        path_to_db = path.join(path.dirname(__file__),
                               'c_cpp_properties_files',
                               'environment')
        scope = SearchScope(from_folder=path_to_db)
        print(scope)
        self.assertEqual(expected, db.get_flags(search_scope=scope))

    def test_no_db_in_folder(self):
        """Test if no json is found."""
        if platform.system() == "Darwin":
            # This test is disabled as the current path is trying to reach a
            # network resource on MacOS. I guess we have to deal with this at
            # some point later.
            return
        include_prefixes = ['-I']
        db = CCppProperties(include_prefixes)

        flags = db.get_flags(File.canonical_path('/home/user/dummy_main.cpp'))
        self.assertTrue(flags is None)

    def test_empty_include_and_defines(self):
        """Test that empty fields are handled correctly."""
        include_prefixes = ['-I']
        db = CCppProperties(include_prefixes)

        expected = []
        path_to_db = path.join(path.dirname(__file__),
                               'c_cpp_properties_files',
                               'empty')
        scope = SearchScope(from_folder=path_to_db)
        self.assertEqual(expected, db.get_flags(search_scope=scope))
