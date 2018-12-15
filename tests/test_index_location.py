"""Test index location."""
import imp
from unittest import TestCase

from EasyClangComplete.plugin.utils import index_location

imp.reload(index_location)

IndexLocation = index_location.IndexLocation


class test_index_location(TestCase):
    """Test generating an index location."""

    def test_simple_init(self):
        """Test short initialization."""
        location = IndexLocation(filename='test.cpp', line=10, column=10)
        self.assertEqual(location.file.name, 'test.cpp')
        self.assertEqual(location.file.extension, '.cpp')
        self.assertEqual(location.file.short_name, 'test.cpp')
        self.assertEqual(location.line, 10)
        self.assertEqual(location.column, 10)

    def test_full_init(self):
        """Test full initialization."""
        from os import path
        long_path = path.join('some', 'folder', 'test.cpp')
        location = IndexLocation(filename=long_path, line=10, column=10)
        self.assertEqual(location.file.name, long_path)
        self.assertEqual(location.file.extension, '.cpp')
        self.assertEqual(location.file.short_name, 'test.cpp')

    def test_no_extension(self):
        """Test if we can initialize without the extension."""
        from os import path
        long_path = path.join('some', 'folder', 'test')
        location = IndexLocation(filename=long_path, line=10, column=10)
        self.assertEqual(location.file.name, long_path)
        self.assertEqual(location.file.extension, '')
        self.assertEqual(location.file.short_name, 'test')
