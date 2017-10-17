"""Test Clang utils."""
from collections import namedtuple
from os import path
from unittest import TestCase

from EasyClangComplete.plugin.clang.utils import ClangUtils

test_file = namedtuple('test_file', 'name')
test_cursor = namedtuple('test_cursor', 'file line')
test_extent = namedtuple('test_extent', 'start end')


class TestClangUtils(TestCase):
    """Tests MacroParser."""

    def test_htmlize_text_ltgt(self):
        """Test a <> symbols convertion."""
        res = ClangUtils.htmlize_text('<>')
        self.assertEqual(res, '&lt;&gt;')

    def test_htmlize_text_newline(self):
        """Test a \n convertion."""
        res = ClangUtils.htmlize_text('text\ntext')
        self.assertEqual(res, 'text<br>text')

    def test_htmlize_text_tab(self):
        """Test a \t convertion."""
        res = ClangUtils.htmlize_text('text\ttext')
        self.assertEqual(res, 'text' + 4 * '&nbsp;' + 'text')

    def test_htmlize_text_quot(self):
        """Test a " symbol convertion."""
        res = ClangUtils.htmlize_text('text"text')
        self.assertEqual(res, 'text' + '&nbsp;' + 'text')

    def test_htmlize_text_spaces(self):
        """Test a single-line string with spaces."""
        res = ClangUtils.htmlize_text('   123')
        self.assertEqual(res, 3 * '&nbsp;' + '123')

    def test_get_text_by_extent_multifile(self):
        """Test getting text from multifile extent."""
        file1 = test_file('file1.c')
        file2 = test_file('file2.c')
        cursor1 = test_cursor(file1, 1)
        cursor2 = test_cursor(file2, 6)
        ext = test_extent(cursor1, cursor2)
        self.assertEqual(ClangUtils.get_text_by_extent(ext), None)

    def test_get_text_by_extent_oneline(self):
        """Test getting text from oneline extent."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        file1 = test_file(file_name)
        cursor1 = test_cursor(file1, 8)
        cursor2 = test_cursor(file1, 8)
        ext = test_extent(cursor1, cursor2)
        self.assertEqual(ClangUtils.get_text_by_extent(ext), '  A a;\n')

    def test_get_text_by_extent_multiline(self):
        """Test getting text from multiline extent."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        file1 = test_file(file_name)
        cursor1 = test_cursor(file1, 8)
        cursor2 = test_cursor(file1, 9)
        ext = test_extent(cursor1, cursor2)
        self.assertEqual(ClangUtils.get_text_by_extent(ext), '  A a;\n  a.\n')
