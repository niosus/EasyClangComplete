"""Test compilation database flags generation."""
import sys
from os import path
from unittest import TestCase

sys.path.append(path.dirname(path.dirname(__file__)))
from plugin.flags_sources.compilation_db import CompilationDb
from plugin.tools import SearchScope


class test_compilation_db(TestCase):
    """Test other things."""
    def test_get_all_flags(self):
        """Test if compilation db is found."""
        path_to_db = path.join(path.dirname(__file__),
                               'compilation_db_files',
                               'linux')
        scope = SearchScope(from_folder=path_to_db)
        include_prefixes = ['-I']
        db = CompilationDb(include_prefixes, scope)
        expected = ['-I/lib_include_dir', '-Dlib_EXPORTS', '-fPIC']
        self.assertEqual(expected, db.get_flags())

    def test_get_flags_for_path(self):
        """Test if compilation db is found."""
        path_to_db = path.join(path.dirname(__file__),
                               'compilation_db_files',
                               'linux')
        scope = SearchScope(from_folder=path_to_db)
        include_prefixes = ['-I']
        db = CompilationDb(include_prefixes, scope)
        expected_lib = ['-Dlib_EXPORTS', '-fPIC']
        expected_main = ['-I/lib_include_dir']
        lib_file_path = '/home/user/dummy_lib.cpp'
        main_file_path = '/home/user/dummy_main.cpp'
        self.assertEqual(expected_lib, db.get_flags(lib_file_path))
        self.assertEqual(expected_main, db.get_flags(main_file_path))
