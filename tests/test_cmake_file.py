"""Tests for cmake database generation."""
import imp
import platform
from os import path

from EasyClangComplete.plugin.flags_sources import cmake_file
from EasyClangComplete.plugin import tools

from EasyClangComplete.tests.gui_test_wrapper import GuiTestWrapper

imp.reload(cmake_file)
imp.reload(tools)

CMakeFile = cmake_file.CMakeFile

SearchScope = tools.SearchScope
PKG_NAME = tools.PKG_NAME


class TestCmakeFile(GuiTestWrapper):
    """Test getting flags from CMakeLists.txt."""

    def test_setup_view(self):
        """Test that setup view correctly sets up the view."""
        file_path = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        self.check_view(file_path)

    def test_init(self):
        """Initialization test."""
        file_path = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        self.set_up_view(file_path)
        self.assertEqual(CMakeFile._FILE_NAME, 'CMakeLists.txt')
        self.assertEqual(len(CMakeFile.cache), 0)
        self.assertEqual(len(CMakeFile.path_for_file), 0)

    def test_cmake_generate(self):
        """Test that cmake can generate flags."""
        if platform.system() == "Windows":
            print("windows is not fully supported for cmake")
            return
        test_file_path = path.join(
            path.dirname(__file__), 'cmake_tests', 'test_a.cpp')
        self.set_up_view(test_file_path)

        self.assertEqual(self.view.file_name(), test_file_path)

        path_to_cmake_proj = path.dirname(test_file_path)
        search_scope = SearchScope(from_folder=path_to_cmake_proj)
        cmake_file = CMakeFile(['-I', '-isystem'], search_scope, [])
        expected_lib = path.join(path_to_cmake_proj, 'lib')
        flags = cmake_file.get_flags(test_file_path)
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0], '-I' + expected_lib)

    def test_cmake_fail(self):
        """Test behavior when no CMakeLists.txt found."""
        if platform.system() == "Windows":
            print("windows is not fully supported for cmake")
            return
        test_file_path = path.join(
            path.dirname(__file__), 'cmake_tests', 'test_a.cpp')
        self.set_up_view(test_file_path)

        self.assertEqual(self.view.file_name(), test_file_path)

        folder_with_no_cmake = path.dirname(__file__)
        search_scope = SearchScope(from_folder=folder_with_no_cmake)
        cmake_file = CMakeFile(['-I', '-isystem'], search_scope, [])
        flags = cmake_file.get_flags(test_file_path)
        self.assertTrue(flags is None)
