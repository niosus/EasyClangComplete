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
        flag = Flag("hello")
        self.assertEqual(flag.as_list(), ["hello"])
        self.assertEqual(flag.prefix, "")
        self.assertEqual(flag.body, "hello")
        self.assertEqual(str(flag), "hello")
        flag = Flag("hello", "world")
        self.assertEqual(flag.as_list(), ["hello", "world"])
        self.assertEqual(flag.prefix, "hello")
        self.assertEqual(flag.body, "world")
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
        flag1 = Flag("hello")
        flag2 = Flag("world")
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
        self.assertIn(Flag("-I", "hello"), list_of_flags)
        self.assertIn(Flag("-Iblah"), list_of_flags)
        self.assertIn(Flag("-isystem", "world"), list_of_flags)
