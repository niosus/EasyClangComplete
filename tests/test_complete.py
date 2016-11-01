"""Tests for autocompletion
"""
import sublime
import sys
import time
import platform
from os import path
from unittest import TestCase

sys.path.append(path.dirname(path.dirname(__file__)))
from plugin.plugin_settings import Settings
from plugin.completion.bin_complete import Completer as CompleterBin
from plugin.completion.lib_complete import Completer as CompleterLib
from plugin.tools import CompletionRequest
from plugin.tools import PKG_NAME


def has_libclang():
    """
    Ensure libclang tests will run only on platforms that support this.

    Returns:
        str: row contents
    """
    # Older version of Sublime Text x64 have ctypes crash bug.
    if platform.system() == "Windows" and sublime.arch() == "x64" and \
            int(sublime.version()) < 3123:
        return False
    return True


class base_test_complete(object):
    """
    Base class for all tests that are independent of the Completer
    implementation.

    Attributes:
        view (sublime.View): view
        Completer (type): Completer class to use
    """
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

    def setUpCompleter(self):
        """
        Utility method to set up a completer for the current view.

        Returns:
            BaseCompleter: completer for the current view.
        """

        settings = Settings()

        clang_binary = settings.clang_binary
        completer = self.Completer(clang_binary)
        completer.init_for_view(
            view=self.view,
            settings=settings)

        return completer

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
        """ Test that setup view correctly sets up the view. """
        self.setUpView('test.cpp')

        file_name = path.join(path.dirname(__file__), 'test.cpp')
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
        """ Test that the completer is properly initialized. """
        self.setUpView('test.cpp')
        completer = self.setUpCompleter()

        self.assertTrue(completer.exists_for_view(self.view.buffer_id()))
        self.assertIsNotNone(completer.version_str)

    def test_complete(self):
        """ Test autocompletion for user type. """
        self.setUpView('test.cpp')

        completer = self.setUpCompleter()
        self.assertTrue(completer.exists_for_view(self.view.buffer_id()))

        # Check the current cursor position is completable.
        self.assertEqual(self.getRow(5), "  a.")
        pos = self.view.text_point(5, 4)
        current_word = self.view.substr(self.view.word(pos))
        self.assertEqual(current_word, ".\n")

        # Load the completions.
        settings = Settings()
        request = CompletionRequest(self.view, pos)
        (_, completions) = completer.complete(request)

        # Verify that we got the expected completions back.
        self.assertIsNotNone(completions)
        expected = ['a\tint a', 'a']
        self.assertIn(expected, completions)

    def test_complete_vector(self):
        """ Test that we can complete vector members. """
        self.setUpView('test_vector.cpp')

        completer = self.setUpCompleter()
        self.assertTrue(completer.exists_for_view(self.view.buffer_id()))

        # Check the current cursor position is completable.
        self.assertEqual(self.getRow(3), "  vec.")
        pos = self.view.text_point(3, 6)
        current_word = self.view.substr(self.view.word(pos))
        self.assertEqual(current_word, ".\n")

        # Load the completions.
        settings = Settings()
        request = CompletionRequest(self.view, pos)
        (_, completions) = completer.complete(request)

        # Verify that we got the expected completions back.
        self.assertIsNotNone(completions)
        if platform.system() == "Windows":
            # disable the windows tests for now until AppVeyor fixes things
            return
        expected = ['begin\titerator begin()', 'begin()']
        self.assertIn(expected, completions)

    def test_unsaved_views(self):
        """ Test that we gracefully handle unsaved views. """
        # Construct an unsaved scratch view.
        self.view = sublime.active_window().new_file()
        self.view.set_scratch(True)

        # Manually set up a completer.
        settings = Settings()
        clang_binary = settings.clang_binary
        completer = self.Completer(clang_binary)
        completer.init_for_view(
            view=self.view,
            settings=settings)

        # Verify that the completer ignores the scratch view.
        self.assertFalse(completer.exists_for_view(self.view.buffer_id()))

    def test_cooperation_with_default_completions(self):
        """
        Test that empty clang completions do not hide default completions.
        """
        self.setUpView("test_errors.cpp")

        completer = self.setUpCompleter()
        self.assertTrue(completer.exists_for_view(self.view.buffer_id()))

        # Undefined foo object has no completions.
        self.assertEqual(self.getRow(1), "  foo.")
        pos = self.view.text_point(1, 6)
        current_word = self.view.substr(self.view.word(pos))
        self.assertEqual(current_word, ".\n")

        # Trigger default completions popup.
        self.view.run_command('auto_complete')
        self.assertTrue(self.view.is_auto_complete_visible())

    def test_cmake_generate(self):
        """
        We search for cmakelists and generate .clang_complete file.
        Here we test that everything has happenede as expected.
        """
        if platform.system() == "Windows":
            print("windows is not fully supported for cmake")
            return
        test_file_path = path.join('cmake_tests', 'test_a.cpp')
        self.setUpView(test_file_path)

        file_name = path.join(path.dirname(__file__),
                              'cmake_tests',
                              'test_a.cpp')
        self.assertEqual(self.view.file_name(), file_name)
        completer = self.setUpCompleter()
        self.assertTrue(completer.exists_for_view(self.view.buffer_id()))
        expected_cmake_file = path.join('cmake_tests', 'CMakeLists.txt')
        expected_clang_file = path.join('cmake_tests', '.clang_complete')
        self.assertTrue(
            completer.flags_manager._cmake_file.full_path().endswith(
                expected_cmake_file))
        self.assertTrue(
            completer.flags_manager._clang_complete_file.full_path().endswith(
                expected_clang_file))
        flags_file = completer.flags_manager._clang_complete_file.full_path()
        file = open(flags_file, 'r')
        found = False
        line = file.readline()
        while line:
            print(line)
            real_line = line.strip()
            if line.startswith('-I'):
                if real_line.endswith('lib') or real_line.endswith('lib"'):
                    found = True
                    break
            line = file.readline()
        file.close()
        self.assertTrue(found)


class test_bin_complete(base_test_complete, TestCase):
    """ Test class for the binary based completer. """
    Completer = CompleterBin

if has_libclang():
    class test_lib_complete(base_test_complete, TestCase):
        """ Test class for the library based completer. """
        Completer = CompleterLib
