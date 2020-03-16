"""Tests for flag class."""
import imp
from unittest import TestCase

from EasyClangComplete.plugin.utils import flag

imp.reload(flag)

Flag = flag.Flag


class TestFlag(TestCase):
    """Test getting flags from CMakeLists.txt."""

    def test_init(self):
        """Initialization test."""
        flag = Flag.Builder().from_unparsed_string("-Ihello").build()
        self.assertEqual(flag.as_list(), ["-I", "hello"])
        self.assertEqual(flag.prefix, "-I")
        self.assertEqual(flag.body, "hello")
        self.assertEqual(str(flag), "-Ihello")
        flag = Flag("hello", "world", " ")
        self.assertEqual(flag.as_list(), ["hello", "world"])
        self.assertEqual(flag.prefix, "hello")
        self.assertEqual(flag.body, "world")
        self.assertEqual(flag.separator, " ")
        self.assertEqual(str(flag), "hello world")

    def test_hash(self):
        """Test that hash is always the same when needed."""
        flag1 = Flag("hello", "world")
        flag2 = Flag("hello", "world")
        flag3 = Flag("world", "hello")
        self.assertEqual(hash(flag1), hash(flag2))
        self.assertNotEqual(hash(flag1), hash(flag3))

    def test_put_into_container(self):
        """Test adding to hashed container."""
        flags_set = set()
        flag1 = Flag("", "hello")
        flag2 = Flag("", "world")
        flag3 = Flag("hello", "world")
        flag4 = Flag("world", "hello")
        flags_set.add(flag1)
        flags_set.add(flag2)
        flags_set.add(flag3)
        self.assertIn(flag1, flags_set)
        self.assertIn(flag2, flags_set)
        self.assertIn(flag3, flags_set)
        self.assertNotIn(flag4, flags_set)

    def test_tokenize(self):
        """Test tokenizing a list of all split flags."""
        split_str = ["-I", "hello", "-Iblah", "-isystem", "world"]
        list_of_flags = Flag.tokenize_list(split_str)
        self.assertTrue(len(list_of_flags), 3)
        self.assertIn(Flag("-I", "hello", " "), list_of_flags)
        self.assertIn(Flag("-I", "blah"), list_of_flags)
        self.assertIn(Flag("-isystem", "world", " "), list_of_flags)

    def test_builder(self):
        """Test tokenizing a list of all split flags."""
        flag1 = Flag.Builder().with_prefix('hello').with_body('world').build()
        self.assertEqual(Flag("hello", "world"), flag1)
        flag3 = Flag.Builder().from_unparsed_string('-Iworld').build()
        self.assertEqual(Flag("-I", "world"), flag3)
        flag4 = Flag.Builder().from_unparsed_string('-include world').build()
        self.assertEqual(Flag("-include", "world", " "), flag4)
        # Check that we don't trigger on /U flag.
        import platform
        if platform.system() != "Windows":
            flag5 = Flag.Builder().from_unparsed_string('/User/blah').build()
            self.assertEqual(Flag("", "", ""), flag5)

    def test_builder_invalid(self):
        """Test tokenizing invalid flags."""
        flag2 = Flag.Builder().from_unparsed_string('hello world').build()
        self.assertEqual(Flag("", ""), flag2)
