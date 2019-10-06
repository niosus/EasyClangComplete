"""Test tools.

Attributes:
    easy_clang_complete (module): this plugin module
    SublBridge (SublBridge): class for subl bridge
"""
import imp
from unittest import TestCase

from EasyClangComplete.plugin.utils import singleton


imp.reload(singleton)

singleton = singleton.singleton


class test_singleton(TestCase):
    """Test other things."""

    def test_singleton(self):
        """Test if singleton returns a unique reference."""
        @singleton
        class A(object):
            """Class A."""
            pass

        @singleton
        class B(object):
            """Class B different from class A."""
            pass

        a = A()
        aa = A()
        b = B()
        bb = B()
        self.assertEqual(id(a), id(aa))
        self.assertEqual(id(b), id(bb))
        self.assertNotEqual(id(a), id(b))
