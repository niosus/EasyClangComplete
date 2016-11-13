"""Test compilation database flags generation."""
import sys
from os import path
from unittest import TestCase

sys.path.append(path.dirname(path.dirname(__file__)))
from plugin.utils.unique_list import UniqueList

class test_unique_list(TestCase):
    """Test unique list."""
    def test_init(self):
        """Test initialization."""
        unique_list = UniqueList()
        self.assertEqual([], unique_list.as_list())
        self.assertEqual("[]", str(unique_list))
        unique_list = UniqueList([1, 2, 3])
        self.assertEqual([1, 2, 3], unique_list.as_list())
        self.assertEqual("[1, 2, 3]", str(unique_list))

    def test_append(self):
        """Test appending single values to unique list."""
        unique_list = UniqueList()
        unique_list.append(1)
        self.assertEqual([1], unique_list.as_list())
        unique_list.append(3)
        self.assertEqual([1, 3], unique_list.as_list())
        unique_list.append(1)
        self.assertEqual([1, 3], unique_list.as_list())
        unique_list.append(2)
        self.assertEqual([1, 3, 2], unique_list.as_list())

    def test_clear(self):
        """Test clearing the list."""
        unique_list = UniqueList([1, 2, 3])
        self.assertEqual([1, 2, 3], unique_list.as_list())
        unique_list.clear()
        self.assertEqual([], unique_list.as_list())

    def test_iterable(self):
        """Test iterating over values."""
        unique_list = UniqueList([0, 1, 2])
        counter = 0
        for i in unique_list:
            self.assertEqual(i, counter)
            counter += 1

    def test_add(self):
        """Test merging with other iterable."""
        unique_list = UniqueList([1, 2, 3])
        other_list = [1, 4, 2, 5]
        unique_list += other_list
        self.assertEqual([1, 2, 3, 4, 5], unique_list.as_list())
