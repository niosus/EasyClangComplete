"""Test compilation database flags generation."""
import imp
from os import path
from unittest import TestCase

from EasyClangComplete.plugin.flags_sources import compilation_db
from EasyClangComplete.plugin import tools
from EasyClangComplete.plugin.utils import flag
from EasyClangComplete.plugin.utils import search_scope
from EasyClangComplete.plugin.utils import singleton

imp.reload(compilation_db)
imp.reload(tools)
imp.reload(flag)
imp.reload(search_scope)

CompilationDb = compilation_db.CompilationDb
ComplationDbCache = singleton.ComplationDbCache
SearchScope = search_scope.TreeSearchScope
Flag = flag.Flag


class TestCompilationDb(object):
    """Test generating flags with a 'compile_commands.json' file."""

    def setUp(self):
        """Prepare the database."""
        ComplationDbCache().clear()

    def test_get_all_flags(self):
        """Test if compilation db is found."""
        include_prefixes = ['-I']
        db = CompilationDb(
            include_prefixes,
            header_to_source_map=[],
            lazy_flag_parsing=self.lazy_parsing
        )

        expected = [Flag('-I', path.normpath('/lib_include_dir')),
                    Flag('', '-Dlib_EXPORTS'),
                    Flag('', '-fPIC')]
        path_to_db = path.join(path.dirname(__file__),
                               'compilation_db_files',
                               'command')
        scope = SearchScope(from_folder=path_to_db)
        if self.lazy_parsing:
            self.assertIsNone(db.get_flags(search_scope=scope))
        else:
            self.assertEqual(expected, db.get_flags(search_scope=scope))

    def test_get_all_flags_arguments(self):
        """Test argument filtering."""
        arguments = [
            "/usr/bin/c++",
            "-I/lib_include_dir",
            "-o",
            "CMakeFiles/main_obj.o",
            "-c",
            "/home/user/dummy_main.cpp"]
        expected = ["-I/lib_include_dir"]
        result = CompilationDb.filter_bad_arguments(arguments)
        self.assertEqual(result, expected)

    def test_strip_wrong_arguments(self):
        """Test if compilation db is found and flags loaded from arguments."""
        include_prefixes = ['-I']
        db = CompilationDb(
            include_prefixes,
            header_to_source_map=[],
            lazy_flag_parsing=self.lazy_parsing
        )

        path_to_db = path.join(path.dirname(__file__),
                               'compilation_db_files',
                               'arguments')
        scope = SearchScope(from_folder=path_to_db)
        if self.lazy_parsing:
            import sublime
            if sublime.platform() != 'windows':
                expected = [Flag('', '-Dlib_EXPORTS'),
                            Flag('', '-fPIC')]
                file_path = path.realpath("/home/user/dummy_lib.cpp")
                self.assertEqual(expected, db.get_flags(file_path=file_path,
                                                        search_scope=scope))
            # Check that we don't get the 'all' entry.
            self.assertIsNone(db.get_flags(search_scope=scope))
        else:
            expected = [Flag('-I', path.normpath('/lib_include_dir')),
                        Flag('', '-Dlib_EXPORTS'),
                        Flag('', '-fPIC')]
            self.assertEqual(expected, db.get_flags(search_scope=scope))

    def test_get_flags_for_path(self):
        """Test if compilation db is found."""
        include_prefixes = ['-I']
        db = CompilationDb(
            include_prefixes,
            header_to_source_map=[],
            lazy_flag_parsing=self.lazy_parsing
        )

        expected_lib = [Flag('', '-Dlib_EXPORTS'), Flag('', '-fPIC')]
        expected_main = [Flag('-I', path.normpath('/lib_include_dir'))]
        lib_file_path = path.normpath('/home/user/dummy_lib.cpp')
        main_file_path = path.normpath('/home/user/dummy_main.cpp')
        # also try to test a header
        lib_file_path_h = path.normpath('/home/user/dummy_lib.h')
        path_to_db = path.join(path.dirname(__file__),
                               'compilation_db_files',
                               'command')
        scope = SearchScope(from_folder=path_to_db)
        self.assertEqual(expected_lib, db.get_flags(lib_file_path, scope))
        self.assertEqual(expected_lib, db.get_flags(lib_file_path_h, scope))
        self.assertEqual(expected_main, db.get_flags(main_file_path, scope))
        self.assertIn(lib_file_path, db._cache)
        self.assertIn(main_file_path, db._cache)
        path_to_db = path.join(path.dirname(__file__),
                               'compilation_db_files',
                               'command', 'compile_commands.json')
        self.assertEqual(path_to_db,
                         db._cache[lib_file_path])
        self.assertEqual(path_to_db,
                         db._cache[main_file_path])

        if self.lazy_parsing:
            self.assertNotIn(CompilationDb.ALL_TAG, db._cache[path_to_db])
        else:
            self.assertIn(expected_main[0],
                          db._cache[path_to_db][CompilationDb.ALL_TAG])
            self.assertIn(
                expected_lib[0], db._cache[path_to_db][CompilationDb.ALL_TAG])
            self.assertIn(
                expected_lib[1], db._cache[path_to_db][CompilationDb.ALL_TAG])

    def test_no_db_in_folder(self):
        """Test that a non-existing file is not found in db."""
        include_prefixes = ['-I']
        db = CompilationDb(
            include_prefixes,
            header_to_source_map=[],
            lazy_flag_parsing=self.lazy_parsing
        )

        flags = db.get_flags(path.normpath('/home/user/dummy_main.cpp'))
        self.assertTrue(flags is None)

    def test_persistence(self):
        """Test if compilation db is persistent."""
        include_prefixes = ['-I']
        db = CompilationDb(
            include_prefixes,
            header_to_source_map=[],
            lazy_flag_parsing=self.lazy_parsing
        )

        expected_lib = [Flag('', '-Dlib_EXPORTS'), Flag('', '-fPIC')]
        expected_main = [Flag('-I', path.normpath('/lib_include_dir'))]
        lib_file_path = path.normpath('/home/user/dummy_lib.cpp')
        main_file_path = path.normpath('/home/user/dummy_main.cpp')
        path_to_db = path.join(path.dirname(__file__),
                               'compilation_db_files',
                               'command')
        scope = SearchScope(from_folder=path_to_db)
        self.assertEqual(expected_lib, db.get_flags(lib_file_path, scope))
        self.assertEqual(expected_main, db.get_flags(main_file_path, scope))
        # check persistence
        self.assertGreater(len(db._cache), 2)
        self.assertEqual(path.join(path_to_db, "compile_commands.json"),
                         db._cache[main_file_path])
        self.assertEqual(path.join(path_to_db, "compile_commands.json"),
                         db._cache[lib_file_path])

    def test_relative_directory(self):
        """Test if compilation db 'directory' records are applied."""
        include_prefixes = ['-I', '-isystem']
        db = CompilationDb(
            include_prefixes,
            header_to_source_map=[],
            lazy_flag_parsing=self.lazy_parsing
        )

        expected = [Flag('-I', path.realpath('/foo/bar/test/include')),
                    Flag('-I', path.realpath('/foo/include')),
                    Flag('-isystem', path.realpath('/foo/bar/matilda'), ' ')]

        path_to_db = path.realpath(
            path.join(path.dirname(__file__),
                      'compilation_db_files',
                      'directory'))
        scope = SearchScope(from_folder=path_to_db)
        if self.lazy_parsing:
            import sublime
            if sublime.platform() != 'windows':
                file_path = path.realpath(
                    path.join("/foo/bar/test", "test.cpp"))
                self.assertEqual(expected, db.get_flags(file_path=file_path,
                                                        search_scope=scope))
            # Check that we don't get the 'all' entry.
            self.assertIsNone(db.get_flags(search_scope=scope))
        else:
            db.get_flags(search_scope=scope)
            self.assertEqual(expected, db.get_flags(search_scope=scope))

    def test_get_c_flags(self):
        """Test argument filtering for c language."""
        include_prefixes = ['-I']
        db = CompilationDb(
            include_prefixes,
            header_to_source_map=[],
            lazy_flag_parsing=self.lazy_parsing
        )

        main_file_path = path.normpath('/home/blah.c')
        # also try to test a header
        path_to_db = path.join(path.dirname(__file__),
                               'compilation_db_files',
                               'command_c')
        scope = SearchScope(from_folder=path_to_db)
        flags = db.get_flags(main_file_path, scope)
        self.assertNotIn(Flag('-c', ''), flags)
        self.assertNotIn(Flag('', '-c'), flags)
        self.assertNotIn(Flag('-o', ''), flags)
        self.assertNotIn(Flag('', '-o'), flags)
        self.assertIn(Flag('', '-Wno-poison-system-directories'), flags)
        self.assertIn(Flag('', '-march=armv7-a'), flags)


class LazyParsing(TestCompilationDb, TestCase):
    """Test that we can parse DB with lazy parsing."""
    lazy_parsing = True


class NonLazyParsing(TestCompilationDb, TestCase):
    """Test that we can parse DB WITHOUT lazy parsing."""
    lazy_parsing = False
