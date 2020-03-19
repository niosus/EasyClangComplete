"""Test compilation database flags generation."""
import imp
from unittest import TestCase

from os import path

from EasyClangComplete.plugin.utils import include_parser
imp.reload(include_parser)


class TestIncludeParser(TestCase):
    """Test unique list."""

    def test_get_all_includes(self):
        """Test getting all includes."""
        base_folder = path.dirname(__file__)
        _, res = include_parser.get_all_headers(
            folders=[base_folder],
            prefix='',
            force_unix_includes=False,
            completion_request=None)
        self.assertEqual(len(res), 9)
        local_file_path = path.normpath('cmake_tests/lib/a.h')
        expected_completion = [
            '{}\t{}'.format(local_file_path, base_folder), local_file_path]
        self.assertIn(expected_completion, res)

        local_file_path = path.normpath('makefile_files/inc/bar.h')
        expected_completion = [
            '{}\t{}'.format(local_file_path, base_folder), local_file_path]
        self.assertIn(expected_completion, res)

    def test_get_specific_includes(self):
        """Test getting only specific includes."""
        base_folder = path.dirname(__file__)
        _, res = include_parser.get_all_headers(
            folders=[base_folder],
            prefix='cmake_',
            force_unix_includes=False,
            completion_request=None)
        self.assertEqual(len(res), 1)
        local_file_path = path.normpath('cmake_tests/lib/a.h')
        expected_completion = [
            '{}\t{}'.format(local_file_path, base_folder), local_file_path]
        self.assertIn(expected_completion, res)

    def test_get_specific_includes_force_unix(self):
        """Test getting only specific includes."""
        base_folder = path.dirname(__file__)
        _, res = include_parser.get_all_headers(
            folders=[base_folder],
            prefix='cmake_',
            force_unix_includes=True,
            completion_request=None)
        self.assertEqual(len(res), 1)
        local_file_path = 'cmake_tests/lib/a.h'
        expected_completion = [
            '{}\t{}'.format(local_file_path, base_folder), local_file_path]
        self.assertIn(expected_completion, res)
