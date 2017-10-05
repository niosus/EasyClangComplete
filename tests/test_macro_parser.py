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

    def test_definition_macro_without_definition(self):
        """Test parsing definition from macro that has no definition"""
        parser = MacroParser('TEST_MACRO', None)
        parser._parse_macro_file_lines(
            macro_file_lines=['#define TEST_MACRO'],
            macro_line_number=1)
        self.assertEqual(parser.definition, '')
        self.assertTrue(parser.definition_is_complete)

    def test_definition_non_function_like_macro(self):
        """Test parsing definition from a non-function-like macro"""
        parser = MacroParser('TEST_MACRO', None)
        parser._parse_macro_file_lines(
            macro_file_lines=['#define TEST_MACRO single_line_definition '],
            macro_line_number=1)
        self.assertEqual(parser.definition, 'single_line_definition')
        self.assertTrue(parser.definition_is_complete)

    def test_definition_function_like_macro(self):
        """Test parsing definition from a function-like macro"""
        parser = MacroParser('TEST_MACRO', None)
        parser._parse_macro_file_lines(
            macro_file_lines=['#define TEST_MACRO() single_line_definition'],
            macro_line_number=1)
        self.assertEqual(parser.definition, 'single_line_definition')
        self.assertTrue(parser.definition_is_complete)

    def test_definition_line_continuation_with_partial_definition(self):
        """Test parsing macro w/ partial definition before line continuation.
        """
        parser = MacroParser('TEST_MACRO', None)
        parser._parse_macro_file_lines(
            macro_file_lines=['#define TEST_MACRO some_definition\\',
                              'then_continuedon_next_line'],
            macro_line_number=1)
        self.assertEqual(parser.definition, 'some_definition')
        self.assertFalse(parser.definition_is_complete)

    def test_definition_line_continuation_without_definition(self):
        """Test parsing macro w/ line continuation w/o any definition.
        """
        parser = MacroParser('TEST_MACRO', None)
        parser._parse_macro_file_lines(
            macro_file_lines=['#define TEST_MACRO \\',
                              ' macro_definition_on_continued_line'],
            macro_line_number=1)
        self.assertEqual(parser.definition, '')
        self.assertFalse(parser.definition_is_complete)

    def test_definition_line_continuation_without_end_of_args(self):
        """Test parsing macro w/line continuation before closing args paren"""
        parser = MacroParser('TEST_MACRO', None)
        parser._parse_macro_file_lines(
            macro_file_lines=['#define TEST_MACRO( \\',
                              ') parenthesis_and_definition_on_continued_line'],
            macro_line_number=1)
        self.assertEqual(parser.definition, '')
        self.assertFalse(parser.definition_is_complete)
