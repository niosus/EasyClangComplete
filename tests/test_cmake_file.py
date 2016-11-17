"""Tests for cmake database generation."""
import sublime
import sys
import imp
import time
import platform
from os import path
from unittest import TestCase

sys.path.append(path.dirname(path.dirname(__file__)))
from plugin.flags_sources import cmake_file
from plugin.tools import SearchScope
from plugin.tools import PKG_NAME

imp.reload(cmake_file)

CMakeFile = cmake_file.CMakeFile

class test_cmake_file(TestCase):

    def setUp(self):
        """ Setup method run before every test. """

        # Ensure we have a window to work with.
        s = sublime.load_settings("Preferences.sublime-settings")
        s.set("close_windows_when_empty", False)
        s = sublime.load_settings(PKG_NAME + ".sublime-settings")
        s.set("verbose", True)
        s.set("cmake_flags_priority", "overwrite")

        self.view = None

    def tearDown(self):
        """ Cleanup method run after every test. """

        # If we have a view, close it.
        if self.view:
            self.view.set_scratch(True)
            self.view.window().focus_view(self.view)
            self.view.window().run_command("close_file")
            self.view = None

    def setUpView(self, filename):
        """
        Utility method to set up a view for a given file.

        Args:
            filename (str): The filename to open in a new view.
        """

        # Open the view.
        file_path = path.join(path.dirname(__file__), filename)
        self.view = sublime.active_window().open_file(file_path)

        # Ensure it's loaded.
        while self.view.is_loading():
            time.sleep(0.1)

    def getRow(self, row):
        """
        Get text of a particular row

        Args:
            row (int): number of row

        Returns:
            str: row contents
        """
        return self.view.substr(self.view.line(self.view.text_point(row, 0)))

    def test_setup_view(self):
        """Test that setup view correctly sets up the view."""
        self.setUpView(path.join('test_files', 'test.cpp'))

        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        self.assertEqual(self.view.file_name(), file_name)
        file = open(file_name, 'r')
        row = 0
        line = file.readline()
        while line:
            self.assertEqual(line[:-1], self.getRow(row))
            row += 1
            line = file.readline()
        file.close()

    def test_init(self):
        self.setUpView(path.join('test_files', 'test.cpp'))
        self.assertEqual(CMakeFile._FILE_NAME, 'CMakeLists.txt')
        self.assertEqual(len(CMakeFile.cache), 0)
        self.assertEqual(len(CMakeFile.path_for_file), 0)

    def test_cmake_generate(self):
        if platform.system() == "Windows":
            print("windows is not fully supported for cmake")
            return
        test_file_path = path.join('cmake_tests', 'test_a.cpp')
        self.setUpView(test_file_path)

        file_name = path.join(path.dirname(__file__), test_file_path)
        self.assertEqual(self.view.file_name(), file_name)

        path_to_cmake_proj = path.join(path.dirname(__file__), 'cmake_tests')
        search_scope = SearchScope(from_folder=path_to_cmake_proj)
        cmake_file = CMakeFile(['-I', '-isystem'], search_scope, [])
        expected_lib = path.join(path_to_cmake_proj, 'lib')
        flags = cmake_file.get_flags(file_name)
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0], '-I' + expected_lib)

    def test_cmake_fail(self):
        if platform.system() == "Windows":
            print("windows is not fully supported for cmake")
            return
        test_file_path = path.join('test_files', 'test.cpp')
        self.setUpView(test_file_path)

        file_name = path.join(path.dirname(__file__), test_file_path)
        self.assertEqual(self.view.file_name(), file_name)

        path_to_cmake_proj = path.join(path.dirname(__file__), 'test_files')
        search_scope = SearchScope(from_folder=path_to_cmake_proj)
        cmake_file = CMakeFile(['-I', '-isystem'], search_scope, [])
        flags = cmake_file.get_flags(file_name)
        self.assertTrue(flags is None)
