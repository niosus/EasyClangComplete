"""Tests for cmake database generation."""
import imp
from os import path
from unittest import TestCase

from EasyClangComplete.plugin.flags_sources import flags_source
from EasyClangComplete.plugin.utils import flag

imp.reload(flags_source)
imp.reload(flag)

FlagsSource = flags_source.FlagsSource
Flag = flag.Flag


class TestFlagsSource(TestCase):
    """Test getting flags from a list of chunks."""

    def test_init(self):
        """Initialization test."""
        include_prefixes = ["-I", "-isystem"]
        flags_source = FlagsSource(include_prefixes)
        self.assertEqual(flags_source._include_prefixes, include_prefixes)

    def test_parse_flags(self):
        """Test that the flags are parsed correctly."""
        from os import listdir
        include_prefixes = ["-I", "-isystem"]
        current_folder = path.dirname(__file__)
        folder_to_expand = path.join(current_folder, '*')
        initial_str_flags = ["-I", current_folder, "-I" + current_folder,
                             "-isystem", current_folder, "-std=c++11",
                             "#simulate a comment",
                             "-Iblah\n", "-I", "blah", "-I" + folder_to_expand]
        flags = FlagsSource.parse_flags(
            current_folder, initial_str_flags, include_prefixes)
        expected_blah_path = path.join(current_folder, "blah")
        self.assertIn(Flag("-I", current_folder), flags)
        self.assertIn(Flag("-I" + current_folder), flags)
        self.assertIn(Flag("-isystem", current_folder), flags)
        self.assertIn(Flag("-I", expected_blah_path), flags)
        self.assertIn(Flag("-I" + expected_blah_path), flags)
        self.assertIn(Flag("-std=c++11"), flags)

        # Check star expansion for a flags source
        for child in listdir(current_folder):
            child = path.join(current_folder, child)
            if path.isdir(child):
                self.assertIn(Flag("-I" + child), flags)

        self.assertNotIn(Flag("-Iblah"), flags)
        self.assertNotIn(Flag("-I", "blah"), flags)
        self.assertNotIn(Flag("-isystem" + current_folder), flags)
