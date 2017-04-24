"""Test macro parsing"""
from unittest import TestCase

from EasyClangComplete.plugin.clang.utils import MacroParser


class TestMacroParser(TestCase):
    """Tests MacroParser"""
    def test_args_string_non_function_like_macro(self):
        """Test parsing a macro with no '()'."""
        parser = MacroParser('TEST_MACRO', None)
        parser._parse_macro_file_lines(
            macro_file_lines=['#define TEST_MACRO 1'],
            macro_line_number=1)
        self.assertEqual(parser.args_string, '')

    def test_args_string_function_macro_no_args(self):
        """Test parsing a function-like macro that takes no arguments."""
        parser = MacroParser('TEST_MACRO', None)
        parser._parse_macro_file_lines(
            macro_file_lines=['#define TEST_MACRO() 1'],
            macro_line_number=1)
        self.assertEqual(parser.args_string, '()')

    def test_args_string_function_macro_one_arg(self):
        """Test parsing a function-like macro that takes one argument."""
        parser = MacroParser('TEST_MACRO', None)
        parser._parse_macro_file_lines(
            macro_file_lines=['#define TEST_MACRO(x) (x)'],
            macro_line_number=1)
        self.assertEqual(parser.args_string, '(x)')

    def test_args_string_function_macro_multiple_args(self):
        """Test parsing a function-like macro that takes multiple arguments."""
        parser = MacroParser('TEST_MACRO', None)
        parser._parse_macro_file_lines(
            macro_file_lines=['#define TEST_MACRO(x, y, z) (x + y + z)'],
            macro_line_number=1)
        self.assertEqual(parser.args_string, '(x, y, z)')

    def test_args_string_macro_extra_whitespace(self):
        """Test parsing a function-like macro with extra whitespace."""
        parser = MacroParser('TEST_MACRO', None)
        parser._parse_macro_file_lines(
            macro_file_lines=[' #  define   TEST_MACRO( x ,   y,    z  ) (x)'],
            macro_line_number=1)
        self.assertEqual(parser.args_string, '(x, y, z)')
