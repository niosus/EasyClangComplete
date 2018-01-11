"""Test macro parsing."""
from unittest import TestCase

from EasyClangComplete.plugin.utils.macro_parser import MacroParser


class TestMacroParser(TestCase):
    """Tests MacroParser."""

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

    def test_body_string_macro_empty(self):
        """Test parsing a macro without parameters."""
        parser = MacroParser('TEST_MACRO', None)
        parser._parse_macro_file_lines(
            macro_file_lines=[' #  define   TEST_MACRO'],
            macro_line_number=1)
        self.assertEqual(parser.body_string, '')

    def test_body_string_macro_inline(self):
        """Test parsing a single-line macro."""
        parser = MacroParser('TEST_MACRO', None)
        parser._parse_macro_file_lines(
            macro_file_lines=[' #  define   TEST_MACRO 42'],
            macro_line_number=1)
        self.assertEqual(parser.body_string, '42')

    def test_body_string_macro_next_line(self):
        """Test parsing a macro with val on next line."""
        parser = MacroParser('TEST_MACRO', None)
        parser._parse_macro_file_lines(
            macro_file_lines=[' #  define   TEST_MACRO \\\n 42'],
            macro_line_number=1)
        self.assertEqual(parser.body_string, '\\\n 42')

    def test_body_string_macro_curr_next_line(self):
        """Test parsing a macro with val on current and next lines."""
        parser = MacroParser('TEST_MACRO', None)
        parser._parse_macro_file_lines(
            macro_file_lines=[' #  define   TEST_MACRO 24\\\n 42'],
            macro_line_number=1)
        self.assertEqual(parser.body_string, '24\\\n 42')

    def test_body_string_macro_curr_next_lines(self):
        """Test parsing a function macro on multiple lines."""
        parser = MacroParser('TEST_MACRO', None)
        parser._parse_macro_file_lines(
            macro_file_lines=[' #define TEST_MACRO(x) 24\\\n 42\\\n11\\\n123'],
            macro_line_number=1)
        self.assertEqual(parser.body_string, '24\\\n 42\\\n11\\\n123')
