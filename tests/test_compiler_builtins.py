"""Tests for CompilerBuiltIns class."""
import imp
from unittest import TestCase

from EasyClangComplete.plugin.utils import compiler_builtins

imp.reload(compiler_builtins)

CompilerBuiltIns = compiler_builtins.CompilerBuiltIns


class TestFlag(TestCase):
    """Test getting built in flags from a target compiler."""

    def test_empty(self):
        """Test empty."""
        builtIns = CompilerBuiltIns([], None)
        self.assertEqual(len(builtIns.include_paths), 0)
        self.assertEqual(len(builtIns.defines), 0)
        self.assertEqual(builtIns.compiler, None)
        self.assertEqual(builtIns.std, None)
        self.assertEqual(builtIns.language, None)

    def test_plain(self):
        """Test retrieval of built ins when we are uncertain about the language.

        In this test we check retrieval of built ins when we cannot be sure
        about the target language. Input is a command line with the call to the
        compiler but without a filename. In this case, we expect only the
        compiler to be guessed correctly. Asking it for built ins should
        yield C flags (which are mostly a sub-set of flags for other languages).
        """
        builtIns = CompilerBuiltIns(["clang"], None)
        self.assertTrue(len(builtIns.defines) > 0)
        self.assertTrue(len(builtIns.include_paths) > 0)
        self.assertEqual(builtIns.compiler, "clang")
        self.assertEqual(builtIns.std, None)
        self.assertEqual(builtIns.language, None)

    def test_c(self):
        """Test retrieval of flags for a C compiler.

        In this test we have in addition to the compiler an explicit hint to the
        target language in use. Hence, the correct language (and also standard)
        must be guessed correctly.
        """
        builtIns = CompilerBuiltIns(["clang", "-std=c99", "-x", "c"], None)
        self.assertTrue(len(builtIns.defines) > 0)
        self.assertTrue(len(builtIns.include_paths) > 0)
        self.assertEqual(builtIns.compiler, "clang")
        self.assertEqual(builtIns.std, "c99")
        self.assertEqual(builtIns.language, "c")
        self.assertIn("-D__clang__=1", builtIns.flags)
        # TODO: It seems STDC is not set everywhere (at least the test on
        # Appveyor fails when we check for this). Maybe there's another,
        # C specific define which it is worth checking for?
        # self.assertIn("-D__STDC__=1", builtIns.flags)

    def test_cxx(self):
        """Test retrieval of flags for a C++ compiler.

        We check if we can get flags for a C++ compiler. The language
        can be derived from either the compiler name, an explicit
        language given in the flags to the compiler or the filename. To make
        sure, we check if C++ specific defines are in the retrieved flags.
        """
        test_data = [
            {
                "args": ["clang++"],
                "filename": None,
                "compiler": "clang++"
            },
            {
                "args": ["clang", "-x", "c++"],
                "filename": None,
                "compiler": "clang"
            },
            {
                "args": ["clang"],
                "filename": "myfile.cpp",
                "compiler": "clang"
            },
            {
                "args": ["clang"],
                "filename": "myfile.cc",
                "compiler": "clang"
            },
            {
                "args": ["clang"],
                "filename": "myfile.cxx",
                "compiler": "clang"
            },
            {
                "args": ["clang"],
                "filename": "myfile.C",
                "compiler": "clang"
            },
            {
                "args": ["clang"],
                "filename": "myfile.c++",
                "compiler": "clang"
            }
        ]
        for test_set in test_data:
            print("Testing using test set: {}".format(test_set))
            builtIns = CompilerBuiltIns(test_set["args"], test_set["filename"])
            self.assertEqual(builtIns.compiler, test_set["compiler"])
            self.assertEqual(builtIns.language, "c++")
            is_cpp = False
            for define in builtIns.defines:
                if define.startswith("-D__cplusplus="):
                    is_cpp = True
            self.assertTrue(is_cpp)

    def test_objc(self):
        """Test retrieval of flags for an Objective-C compiler.

        We check if we can get flags for an Objective-C compiler.
        For this, we make sure we recognize if a compilation is for Objective-C
        by looking at explicit target languages or the filename of the input
        file.
        """
        test_data = [
            {
                "args": ["clang", "-x", "objective-c"],
                "filename": None,
                "compiler": "clang"
            },
            {
                "args": ["clang"],
                "filename": "myfile.m",
                "compiler": "clang"
            },
            {
                "args": ["clang"],
                "filename": "myfile.mm",
                "compiler": "clang"
            },
        ]
        for test_set in test_data:
            print("Testing using test set: {}".format(test_set))
            builtIns = CompilerBuiltIns(test_set["args"], test_set["filename"])
            self.assertEqual(builtIns.compiler, test_set["compiler"])
            self.assertEqual(builtIns.language, "objective-c")
            self.assertIn("-D__OBJC__=1", builtIns.flags)

    def test_objcpp(self):
        """Test retrieval of flags for an Objective-C++ compiler.

        We check if we can get flags for an Objective-C++ compiler.
        For this, we look if we can find an explicit language flag in the
        compiler argument list.
        """
        test_data = [
            {
                "args": ["clang", "-x", "objective-c++"],
                "filename": None,
                "compiler": "clang"
            }
        ]
        for test_set in test_data:
            print("Testing using test set: {}".format(test_set))
            builtIns = CompilerBuiltIns(test_set["args"], test_set["filename"])
            self.assertEqual(builtIns.compiler, test_set["compiler"])
            self.assertEqual(builtIns.language, "objective-c++")
            self.assertIn("-D__OBJC__=1", builtIns.flags)
            is_cpp = False
            for define in builtIns.defines:
                if define.startswith("-D__cplusplus="):
                    is_cpp = True
            self.assertTrue(is_cpp)
