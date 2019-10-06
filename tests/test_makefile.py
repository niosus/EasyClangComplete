"""Tests for Makefile flags extraction."""
import imp
import platform
from os import path
from unittest import TestCase

from EasyClangComplete.plugin.utils import flag
from EasyClangComplete.plugin.utils import search_scope
from EasyClangComplete.plugin.flags_sources import makefile

imp.reload(makefile)
imp.reload(flag)
imp.reload(search_scope)

SearchScope = search_scope.TreeSearchScope

Makefile = makefile.Makefile

Flag = flag.Flag


class TestMakefile(object):
    """Test finding and generating flags from Makeifles."""

    def test_init(self):
        """Initialization test."""
        self.assertEqual(Makefile._FILE_NAME, 'Makefile')

    def _get_project_root(self):
        return path.join(path.dirname(__file__), 'makefile_files')

    def _check_include(self, flags, include):
        expected = path.join(self._get_project_root(), include)
        self.assertIn(Flag('-I', expected), flags)

    def _check_define(self, flags, define):
        self.assertIn(Flag('', '-D' + define), flags)

    def _check_makefile(self, cache, flags, test_path, makefile_path):
        expected = path.join(self._get_project_root(), makefile_path)
        self.assertEqual(expected, cache[test_path])
        self.assertEqual(flags, cache[expected])

    def _check_cache(self, cache, flags, makefile_path):
        key = path.join(self._get_project_root(), makefile_path)
        self.assertEqual(flags, cache[key])

    def test_makefile_root(self):
        """Test finding and parsing root Makefile."""
        test_path = path.join(self._get_project_root(), 'main.c')

        mfile = Makefile(['-I', '-isystem'])
        flags = mfile.get_flags(test_path)
        self._check_include(flags, "inc")
        self._check_define(flags, "REQUIRED_DEFINE")
        self._check_makefile(mfile._cache, flags, test_path, "Makefile")

    def test_makefile_lib(self):
        """Test finding and parsing library Makefile."""
        test_path = path.join(self._get_project_root(), 'lib', 'bar.c')

        mfile = Makefile(['-I', '-isystem'])
        flags = mfile.get_flags(test_path)
        self._check_include(flags, path.join("lib", "foo"))
        self._check_makefile(mfile._cache, flags, test_path,
                             path.join("lib", "Makefile"))

    def test_makefile_sub(self):
        """Test finding and parsing Makefile for library subdir."""
        test_path = path.join(self._get_project_root(), 'lib', 'foo', 'foo.c')

        mfile = Makefile(['-I', '-isystem'])
        flags = mfile.get_flags(test_path)
        self._check_include(flags, path.join("lib", "foo"))
        self._check_makefile(mfile._cache, flags, test_path,
                             path.join("lib", "Makefile"))

    def test_makefile_fail(self):
        """Test behavior when no Makefile found."""
        test_path = path.join(path.dirname(__file__), 'test_files', 'test.cpp')

        mfile = Makefile(['-I', '-isystem'])
        flags = mfile.get_flags(test_path)
        self.assertTrue(flags is None)


if platform.system() != "Windows":
    class MakefileTestRunner(TestMakefile, TestCase):
        """Run make only if we are not on windows."""
        pass
