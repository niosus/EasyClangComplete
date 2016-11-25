"""Tests for cmake database generation."""
import imp
import platform
from os import path
from unittest import TestCase

from EasyClangComplete.plugin.flags_sources import cmake_file
from EasyClangComplete.plugin.flags_sources import compilation_db
from EasyClangComplete.plugin.utils import flag
from EasyClangComplete.plugin import tools

imp.reload(cmake_file)
imp.reload(compilation_db)
imp.reload(tools)
imp.reload(flag)

CMakeFile = cmake_file.CMakeFile
CompilationDb = compilation_db.CompilationDb

SearchScope = tools.SearchScope
PKG_NAME = tools.PKG_NAME

Flag = flag.Flag


class TestCmakeFile(object):
    """Test getting flags from CMakeLists.txt."""

    def test_init(self):
        """Initialization test."""
        self.assertEqual(CMakeFile._FILE_NAME, 'CMakeLists.txt')

    def test_cmake_generate(self):
        """Test that cmake can generate flags."""
        test_file_path = path.join(
            path.dirname(__file__), 'cmake_tests', 'test_a.cpp')

        path_to_cmake_proj = path.dirname(test_file_path)
        cmake_file = CMakeFile(['-I', '-isystem'], [])
        expected_lib = path.join(path_to_cmake_proj, 'lib')
        flags = cmake_file.get_flags(test_file_path)
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0], Flag('-I' + expected_lib))
        self.assertIn(test_file_path, cmake_file._cache)
        expected_cmake_file = path.join(
            path_to_cmake_proj, CMakeFile._FILE_NAME)
        found_cmake_file = cmake_file._cache[test_file_path]
        self.assertEqual(expected_cmake_file, found_cmake_file)

    def test_cmake_with_existing_header(self):
        """Test that cmake can generate flags."""
        test_file_path = path.join(
            path.dirname(__file__), 'cmake_tests', 'lib', 'a.h')

        path_to_file_folder = path.dirname(test_file_path)
        expected_lib_include = Flag('-I' + path_to_file_folder)
        cmake_file = CMakeFile(['-I', '-isystem'], [])
        flags = cmake_file.get_flags(test_file_path)
        db = CompilationDb(['-I', '-isystem'])
        self.assertEqual(len(flags), 2)
        self.assertEqual(flags[0], Flag('-Dliba_EXPORTS'))
        self.assertEqual(flags[1], Flag('-fPIC'))
        self.assertIn(test_file_path, cmake_file._cache)
        expected_cmake_file = path.join(
            path.dirname(path_to_file_folder), CMakeFile._FILE_NAME)
        found_cmake_file = cmake_file._cache[test_file_path]
        self.assertEqual(expected_cmake_file, found_cmake_file)
        used_db_path = cmake_file._cache[found_cmake_file]
        used_db = db._cache[used_db_path]
        self.assertIn(expected_lib_include, used_db['all'])

    def test_cmake_fail(self):
        """Test behavior when no CMakeLists.txt found."""
        test_file_path = path.join(
            path.dirname(__file__), 'cmake_tests', 'test_a.cpp')

        folder_with_no_cmake = path.dirname(__file__)
        cmake_file = CMakeFile(['-I', '-isystem'], [])
        wrong_scope = SearchScope(from_folder=folder_with_no_cmake)
        flags = cmake_file.get_flags(test_file_path, wrong_scope)
        self.assertTrue(flags is None)


if platform.system() != "Windows":
    class CMakeTestRunner(TestCmakeFile, TestCase):
        """Run cmake only if we are not on windows."""
        pass
