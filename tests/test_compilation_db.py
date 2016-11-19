"""Test compilation database flags generation."""
from os import path
from unittest import TestCase

from EasyClangComplete.plugin.flags_sources import compilation_db
from EasyClangComplete.plugin import tools

CompilationDb = compilation_db.CompilationDb
SearchScope = tools.SearchScope


class TestCompilationDb(TestCase):
    """Test generating flags with a 'compile_commands.json' file."""

    def test_get_all_flags(self):
        """Test if compilation db is found."""
        path_to_db = path.join(path.dirname(__file__),
                               'compilation_db_files',
                               'linux')
        scope = SearchScope(from_folder=path_to_db)
        include_prefixes = ['-I']
        db = CompilationDb(include_prefixes, scope)
        expected = ['-I' + path.normpath('/lib_include_dir'),
                    '-Dlib_EXPORTS',
                    '-fPIC']
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
        expected_main = ['-I' + path.normpath('/lib_include_dir')]
        lib_file_path = path.normpath('/home/user/dummy_lib.cpp')
        main_file_path = path.normpath('/home/user/dummy_main.cpp')
        self.assertEqual(expected_lib, db.get_flags(lib_file_path))
        self.assertEqual(expected_main, db.get_flags(main_file_path))

    def test_no_db_in_folder(self):
        """Test if compilation db is found."""
        path_to_db = path.join(path.dirname(__file__))
        scope = SearchScope(from_folder=path_to_db)
        include_prefixes = ['-I']
        db = CompilationDb(include_prefixes, scope)
        flags = db.get_flags(path.normpath('/home/user/dummy_main.cpp'))
        self.assertTrue(flags is None)

    def test_persistence(self):
        """Test if compilation db is persistent."""
        CompilationDb.path_for_file = {}
        path_to_db = path.join(path.dirname(__file__),
                               'compilation_db_files',
                               'linux')
        scope = SearchScope(from_folder=path_to_db)
        include_prefixes = ['-I']
        db = CompilationDb(include_prefixes, scope)
        expected_lib = ['-Dlib_EXPORTS', '-fPIC']
        expected_main = ['-I' + path.normpath('/lib_include_dir')]
        lib_file_path = path.normpath('/home/user/dummy_lib.cpp')
        main_file_path = path.normpath('/home/user/dummy_main.cpp')
        self.assertEqual(expected_lib, db.get_flags(lib_file_path))
        self.assertEqual(expected_main, db.get_flags(main_file_path))
        # check persistence
        self.assertEqual(len(CompilationDb.path_for_file), 2)
        self.assertEqual(path.join(path_to_db, "compile_commands.json"),
                         CompilationDb.path_for_file[main_file_path])
        self.assertEqual(path.join(path_to_db, "compile_commands.json"),
                         CompilationDb.path_for_file[lib_file_path])
