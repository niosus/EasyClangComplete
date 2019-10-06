"""Test clang utilities."""
import imp
from unittest import TestCase

from EasyClangComplete.plugin.utils import clang_utils

imp.reload(clang_utils)

ClangUtils = clang_utils.ClangUtils


class test_clang_utils(TestCase):
    """Test other things."""

    def test_get_cindex(self):
        """Test that we get a correct clang module."""
        module = ClangUtils.get_cindex_module_for_version("3.8")
        self.assertTrue(module.endswith('cindex38'))
        module = ClangUtils.get_cindex_module_for_version("9.0")
        self.assertTrue(module.endswith('cindex50'))
        # Check that we return the latest cindex for unsupported ones.
        module = ClangUtils.get_cindex_module_for_version("999.0")
        self.assertTrue(module.endswith('cindex50'))

    def test_get_apple_version(self):
        """Test that we get a correct clang module."""
        apple_version_output = 'Apple LLVM version 10.0.1'
        version = ClangUtils._get_apple_clang_version_str(apple_version_output)
        self.assertEquals(version, '6.0')
        # Check that we are pretty future proof.
        apple_version_output = 'Apple LLVM version 99.0.1'
        version = ClangUtils._get_apple_clang_version_str(apple_version_output)
        self.assertEquals(version, '7.0')

    def test_get_all_possible_filenames(self):
        """Test that we get a correct clang module."""
        all_paths = ClangUtils.get_all_possible_filenames('3.8')
        self.assertGreater(len(all_paths), 0)
        for path in all_paths:
            self.assertNotIn('$version', path)

    def test_find_libclang(self):
        """Test that we get a correct clang module."""
        version_str = ClangUtils.get_clang_version_str('clang++')
        libclang_dir, full_libclang_path = ClangUtils.find_libclang(
            'clang++', 'blah', version_str)
        self.assertIsNotNone(libclang_dir)
        self.assertIsNotNone(full_libclang_path)
        from os import path
        self.assertEquals(path.dirname(full_libclang_path), libclang_dir)
