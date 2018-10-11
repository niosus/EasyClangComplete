"""Test tools.

Attributes:
    easy_clang_complete (module): this plugin module
    SublBridge (SublBridge): class for subl bridge
"""
import sublime
import time
import imp
import platform
from os import path
from unittest import TestCase

from EasyClangComplete.plugin import tools
from EasyClangComplete.plugin.settings import settings_manager
from EasyClangComplete.plugin.utils import singleton

imp.reload(tools)
imp.reload(settings_manager)
imp.reload(singleton)

singleton = singleton.singleton
SettingsManager = settings_manager.SettingsManager

SublBridge = tools.SublBridge
Tools = tools.Tools
File = tools.File
SearchScope = tools.SearchScope
PosStatus = tools.PosStatus
PKG_NAME = tools.PKG_NAME


class test_tools_command(TestCase):
    """Test sublime commands."""

    def setUp(self):
        """Set up testing environment."""
        self.view = sublime.active_window().new_file()
        # make sure we have a window to work with
        s = sublime.load_settings("Preferences.sublime-settings")
        s.set("close_windows_when_empty", False)

    def set_up_view(self, filename):
        """Set up a view for a given file.

        Args:
            filename (str): The filename to open in a new view.
        """
        # Open the view.
        file_path = path.join(path.dirname(__file__), filename)
        self.view = sublime.active_window().open_file(file_path)
        self.view.settings().set("disable_easy_clang_complete", True)

        # Ensure it's loaded.
        while self.view.is_loading():
            time.sleep(0.1)

    def tearDown(self):
        """Cleanup method run after every test."""
        # If we have a view, close it.
        if self.view:
            self.view.set_scratch(True)
            self.view.window().focus_view(self.view)
            self.view.window().run_command("close_file")
            self.view = None

    def setText(self, string):
        """Set text to a view.

        Args:
            string (str): some string to set
        """
        self.view.run_command("insert", {"characters": string})

    def appendText(self, string, scroll_to_end=True):
        """Append text to view. Moves the cursor too.

        Args:
            string (str): text to append
            scroll_to_end (bool, optional): should we scroll to the end?
        """
        self.view.run_command("append", {"characters": string,
                                         "scroll_to_end": scroll_to_end})

    def move(self, dist, forward=True):
        """Move the cursor by distance.

        Args:
            dist (int): pixels to move
            forward (bool, optional): forward or backward in the file

        """
        for _ in range(dist):
            self.view.run_command("move",
                                  {"by": "characters", "forward": forward})

    def getRow(self, row):
        """Get row text.

        Args:
            row (int): number of row

        Returns:
            str: text of this row
        """
        return self.view.substr(self.view.line(self.view.text_point(row, 0)))

    def test_cursor_pos(self):
        """Test cursor position."""
        self.setText("hello")
        (row, col) = SublBridge.cursor_pos(self.view)
        self.assertEqual(row, 1)
        self.assertEqual(col, 6)
        self.setText("\nworld!")
        (row, col) = SublBridge.cursor_pos(self.view)
        self.assertEqual(row, 2)
        self.assertEqual(col, 7)
        self.move(10, forward=False)
        (row, col) = SublBridge.cursor_pos(self.view)
        self.assertEqual(row, 1)
        self.assertEqual(col, 3)

    def test_next_line(self):
        """Test returning next line."""
        self.setText("hello\nworld!")
        self.move(10, forward=False)
        next_line = SublBridge.next_line(self.view)
        self.assertEqual(next_line, "world!")

    def test_wrong_triggers(self):
        """Test that we don't complete on numbers and wrong triggers."""
        self.tearDown()
        self.set_up_view(path.join('test_files', 'test_wrong_triggers.cpp'))
        # Load the completions.
        manager = SettingsManager()
        settings = manager.user_settings()

        # Check the current cursor position is completable.
        self.assertEqual(self.getRow(2), "  a > 2.")

        # check that '>' does not trigger completions
        pos = self.view.text_point(2, 5)
        current_word = self.view.substr(self.view.word(pos))
        self.assertEqual(current_word, "> ")

        status = Tools.get_pos_status(pos, self.view, settings)

        # Verify that we got the expected completions back.
        self.assertEqual(status, PosStatus.WRONG_TRIGGER)

        # check that 'a' does not trigger completions
        pos = self.view.text_point(2, 3)
        current_word = self.view.substr(self.view.word(pos))
        self.assertEqual(current_word, "a")

        status = Tools.get_pos_status(pos, self.view, settings)

        # Verify that we got the expected completions back.
        self.assertEqual(status, PosStatus.COMPLETION_NOT_NEEDED)

        # check that '2.' does not trigger completions
        pos = self.view.text_point(2, 8)
        current_word = self.view.substr(self.view.word(pos))
        self.assertEqual(current_word, ".\n")

        status = Tools.get_pos_status(pos, self.view, settings)

        # Verify that we got the expected completions back.
        self.assertEqual(status, PosStatus.WRONG_TRIGGER)


class test_tools(TestCase):
    """Test other things."""

    def test_pkg_name(self):
        """Test if the package name is correct."""
        self.assertEqual(PKG_NAME, "EasyClangComplete")

    def test_expand_star(self):
        """Check that expanding a star at the end of folder works."""
        this_folder = path.dirname(__file__)
        this_folder_with_star = path.join(this_folder, '*')
        print(this_folder_with_star)
        expanded = Tools.expand_star_wildcard(this_folder_with_star)
        expected_folders = [
            path.join(this_folder, 'c_cpp_properties_files'),
            path.join(this_folder, 'catkin_tests'),
            path.join(this_folder, 'cmake_tests'),
            path.join(this_folder, 'compilation_db_files'),
            path.join(this_folder, 'CppProperties_files'),
            path.join(this_folder, 'makefile_files'),
            path.join(this_folder, 'test_files'),
        ]
        self.assertEqual(len(expanded), len(expected_folders))
        self.assertEqual(sorted(expected_folders), sorted(expanded))

    def test_singleton(self):
        """Test if singleton returns a unique reference."""
        @singleton
        class A(object):
            """Class A."""
            pass

        @singleton
        class B(object):
            """Class B different from class A."""
            pass

        a = A()
        aa = A()
        b = B()
        bb = B()
        self.assertEqual(id(a), id(aa))
        self.assertEqual(id(b), id(bb))
        self.assertNotEqual(id(a), id(b))

    def test_get_clang_version(self):
        """Test getting clang version."""
        version = Tools.get_clang_version_str('clang++')
        print("version: ", version)
        self.assertIn('.', version)

    def test_ignore(self):
        """Test ignoring glob patterns."""
        self.assertTrue(Tools.is_ignored('/tmp/hello', ['/tmp/*']))
        self.assertTrue(Tools.is_ignored('/tmp/hello', ['/tmp*']))
        self.assertTrue(Tools.is_ignored('/tmp/hello', ['', '/tmp*']))
        self.assertTrue(Tools.is_ignored('/tmp/hello', ['', '/tmp/hell*']))
        self.assertFalse(Tools.is_ignored('/tmp/hello', ['/tmp/c*']))


class test_file(TestCase):
    """Testing file related stuff."""

    def test_find_file(self):
        """Test if we can find a file."""
        current_folder = path.dirname(path.abspath(__file__))
        parent_folder = path.dirname(current_folder)
        search_scope = SearchScope(from_folder=current_folder,
                                   to_folder=parent_folder)
        file = File.search(
            file_name='README.md',
            search_scope=search_scope)
        expected = path.join(parent_folder, 'README.md')
        self.assertTrue(file.loaded())
        self.assertEqual(file.full_path, expected)

    def test_find_file_content_string(self):
        """Test if we can find a file."""
        current_folder = path.dirname(path.abspath(__file__))
        parent_folder = path.dirname(current_folder)
        search_scope = SearchScope(from_folder=current_folder,
                                   to_folder=parent_folder)
        file = File.search(
            file_name='README.md',
            search_scope=search_scope,
            search_content='plugin')
        self.assertIsNotNone(file)
        self.assertTrue(file.loaded())
        expected = path.join(parent_folder, 'README.md')
        self.assertEqual(file.full_path, expected)
        file_fail = File.search(
            file_name='README.md',
            search_scope=search_scope,
            search_content='text that is not in the file')
        self.assertIsNone(file_fail)

    def test_find_file_content_list(self):
        """Test if we can find a file."""
        current_folder = path.dirname(path.abspath(__file__))
        parent_folder = path.dirname(current_folder)
        search_scope = SearchScope(from_folder=current_folder,
                                   to_folder=parent_folder)
        file = File.search(
            file_name='README.md',
            search_scope=search_scope,
            search_content=['non existing text', 'plugin'])
        self.assertIsNotNone(file)
        self.assertTrue(file.loaded())
        expected = path.join(parent_folder, 'README.md')
        self.assertEqual(file.full_path, expected)
        file_fail = File.search(
            file_name='README.md',
            search_scope=search_scope,
            search_content=['non existing text'])
        self.assertIsNone(file_fail)

    def test_canonical_path(self):
        """Test creating canonical path."""
        if platform.system() == "Windows":
            original_path = "../hello/world.txt"
            folder = "D:\\folder"
            res = File.canonical_path(original_path, folder)
            self.assertEqual(res, "d:\\hello\\world.txt")
        else:
            original_path = "../hello/world.txt"
            folder = "/folder"
            res = File.canonical_path(original_path, folder)
            self.assertEqual(res, "/hello/world.txt")

    def test_canonical_path_absolute(self):
        """Test creating canonical path."""
        if platform.system() == "Windows":
            original_path = "D:\\hello\\world.txt"
            res = File.canonical_path(original_path)
            self.assertEqual(res, "d:\\hello\\world.txt")
        else:
            original_path = "/hello/world.txt"
            res = File.canonical_path(original_path)
            self.assertEqual(res, "/hello/world.txt")

    def test_canonical_path_empty(self):
        """Test failing for canonical path."""
        original_path = None
        res = File.canonical_path(original_path)
        self.assertIsNone(res)
