"""Test compilation database flags generation."""
import imp
import time
import sublime

from os import path
from copy import copy

from unittest import TestCase
from unittest.mock import MagicMock

from EasyClangComplete.plugin.utils import include_parser
from EasyClangComplete.plugin.utils import thread_pool
from EasyClangComplete.plugin.utils.tools import PKG_FOLDER

imp.reload(include_parser)
imp.reload(thread_pool)

IncludeCompleter = include_parser.IncludeCompleter
ThreadPool = thread_pool.ThreadPool


TIMEOUT = 5.0


class TestCallbackReceiver():
    """A test container to store results of the operation."""

    def __init__(self):
        """Initialize this object."""
        self.futures = []

    def on_job_done(self, future):
        """Call this when the job is done."""
        self.futures.append(future)

    def wait_until_got_number_of_callbacks(self, number):
        """Wait until callback is called."""
        slept = 0.0
        time_step = 0.1
        while not len(self.futures) == number and slept < TIMEOUT:
            time.sleep(time_step)
            slept += time_step


class TestIncludeParser(TestCase):
    """Test unique list."""

    def test_create_empty(self):
        """Test that getting no includes works."""
        receiver = TestCallbackReceiver()
        view = MagicMock()
        pool = ThreadPool(common_callback=receiver.on_job_done)
        include_completer = IncludeCompleter(view, "<", pool)
        self.assertIsNotNone(include_completer)
        self.assertEqual(include_completer.opening_char, "<")
        include_completer.start_completion(["non_existing_folder"])
        receiver.wait_until_got_number_of_callbacks(1)
        view.window().show_quick_panel.assert_called_once_with(
            [], include_completer.on_include_picked, sublime.MONOSPACE_FONT, 0)

    def test_load_includes(self):
        """Test that getting no includes works."""
        receiver = TestCallbackReceiver()
        view = MagicMock()
        pool = ThreadPool(common_callback=receiver.on_job_done)
        include_completer = IncludeCompleter(view, "<", pool)
        self.assertIsNotNone(include_completer)
        self.assertEqual(include_completer.opening_char, "<")
        test_folders = [
            path.join(PKG_FOLDER, "tests", "cmake_tests"),
            path.join(PKG_FOLDER, "tests", "cmake_tests", "lib")
        ]
        expected_folder = path.join(PKG_FOLDER, "tests", "cmake_tests", "lib")
        expected_file = path.join(expected_folder, "a.h")
        include_completer.start_completion(test_folders)
        receiver.wait_until_got_number_of_callbacks(1)
        self.assertEqual(len(include_completer.folders_and_headers), 2)
        self.assertEqual(len(include_completer.folders_and_headers[0]), 3)
        self.assertEqual(len(include_completer.folders_and_headers[1]), 3)
        first_tag = include_completer.folders_and_headers[0][0]
        if first_tag == include_parser.FOLDER_TAG:
            expected_argument = [
                [include_parser.FOLDER_TAG + 'lib', expected_folder],
                [include_parser.FILE_TAG + 'a.h', expected_file]
            ]
            folder_index = 0
            file_index = 1
        else:
            expected_argument = [
                [include_parser.FILE_TAG + 'a.h', expected_file],
                [include_parser.FOLDER_TAG + 'lib', expected_folder]
            ]
            folder_index = 1
            file_index = 0
        view.window().show_quick_panel.assert_called_once_with(
            expected_argument,
            include_completer.on_include_picked,
            sublime.MONOSPACE_FONT, 0)
        view.window().show_quick_panel.reset_mock()

        wrong_choice_completer = copy(include_completer)
        wrong_choice_completer.on_include_picked(-1)
        view.run_command.assert_called_once_with("insert", {"characters": "<"})
        view.run_command.reset_mock()

        file_choice_completer = copy(include_completer)
        file_choice_completer.on_include_picked(file_index)
        view.run_command.assert_called_once_with(
            "insert", {"characters": "<a.h>"})
        view.run_command.reset_mock()

        include_completer.on_include_picked(folder_index)
        receiver.wait_until_got_number_of_callbacks(2)
        view.window().show_quick_panel.assert_called_once_with(
            [[include_parser.FILE_TAG + 'a.h', expected_file]],
            include_completer.on_include_picked, sublime.MONOSPACE_FONT, 0)
