"""Test file."""
import imp
import platform
from os import path
from unittest import TestCase

from EasyClangComplete.plugin.utils import file
from EasyClangComplete.plugin.utils import search_scope

imp.reload(file)
imp.reload(search_scope)

File = file.File
SearchScope = search_scope.TreeSearchScope


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
        self.assertIsNotNone(file)
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
            self.assertEqual(res, "D:\\hello\\world.txt")
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
            self.assertEqual(res, "D:\\hello\\world.txt")
        else:
            original_path = "/hello/world.txt"
            res = File.canonical_path(original_path)
            self.assertEqual(res, "/hello/world.txt")

    def test_canonical_path_empty(self):
        """Test failing for canonical path."""
        original_path = None
        res = File.canonical_path(original_path)
        self.assertIsNone(res)

    def test_temp_dir(self):
        """Test that we can expand star in path."""
        temp_folder = File.get_temp_dir()
        self.assertTrue(path.exists(temp_folder))

    def test_ignore(self):
        """Test ignoring glob patterns."""
        self.assertTrue(File.is_ignored('/tmp/hello', ['/tmp/*']))
        self.assertTrue(File.is_ignored('/tmp/hello', ['/tmp*']))
        self.assertTrue(File.is_ignored('/tmp/hello', ['', '/tmp*']))
        self.assertTrue(File.is_ignored('/tmp/hello', ['', '/tmp/hell*']))
        self.assertTrue(File.is_ignored('/tmp/hello/world', ['/tmp/*']))

        self.assertFalse(File.is_ignored('/tmp/hello', ['/tmp/c*']))

    def test_expand_all(self):
        """Test the globbing and wildcard expansion."""
        current_dir_glob = path.join(path.dirname(__file__), '*')
        result = File.expand_all(current_dir_glob)
        self.assertIn(__file__, result)

        result = File.expand_all(current_dir_glob, expand_globbing=False)
        self.assertEquals(len(result), 1)
        self.assertIn(current_dir_glob, result)

        path_with_wildcard = "hello$world"
        wildcards = {"world": "BLAH"}
        result = File.expand_all(path_with_wildcard, wildcard_values=wildcards)
        self.assertEquals(len(result), 1)
        self.assertIn("helloBLAH", result)
