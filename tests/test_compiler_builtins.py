"""Tests for CompilerBuiltIns class."""
import imp
from unittest import TestCase

from EasyClangComplete.plugin.flags_sources import compiler_builtins

imp.reload(compiler_builtins)

CompilerBuiltIns = compiler_builtins.CompilerBuiltIns


class TestFlag(TestCase):
    """Test getting built in flags from a target compiler."""

    def test_empty(self):
        """Test empty."""
        built_ins = CompilerBuiltIns("", None)
        self.assertEqual(len(built_ins.includes), 0)
        self.assertEqual(len(built_ins.defines), 0)

    def test_plain(self):
        """Test retrieval of built ins when we are uncertain about the language.

        In this test we check retrieval of built ins when we cannot be sure
        about the target language. Input is a command line with the call to the
        compiler but without a filename. In this case, we expect only the
        compiler to be guessed correctly. Asking it for built ins should
        yield C flags (which are a sub-set of flags for other languages).
        """
        built_ins = CompilerBuiltIns("clang", None)
        self.assertTrue(len(built_ins.defines) > 0)
        self.assertTrue(len(built_ins.includes) > 0)
        self.assertEqual(len(built_ins.flags),
                         len(built_ins.defines) + len(built_ins.includes))

    def test_c(self):
        """Test retrieval of flags for a C compiler.

        Here, in addition to the compiler we have an explicit hint to the
        target language in use. Hence, the correct language (and also standard)
        must be guessed correctly.
        """
        built_ins = CompilerBuiltIns("clang", ["-std=c99", "-x", "c"])
        self.assertTrue(len(built_ins.defines) > 0)
        self.assertTrue(len(built_ins.includes) > 0)
        self.assertIn("-D__clang__=1", built_ins.flags)

    def test_cxx(self):
        """Test retrieval of flags for a C++ compiler.

        We check if we can get flags for a C++ compiler. The language
        can be derived from either the compiler name, an explicit
        language given in the flags to the compiler or the filename. To make
        sure, we check if C++ specific defines are in the retrieved flags.
        """
        test_data = [
            {
                "args": [],
                "filename": None,
                "compiler": "clang++"
            },
            {
                "args": ["-x", "c++"],
                "filename": None,
                "compiler": "clang"
            }
        ]
        for test_set in test_data:
            print("Testing using test set: {}".format(test_set))
            built_ins = CompilerBuiltIns(
                test_set["compiler"], test_set["args"], test_set["filename"])
            is_cpp = False
            for define in built_ins.defines:
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
                "args": ["-x", "objective-c"],
                "filename": None,
                "compiler": "clang"
            }
        ]
        for test_set in test_data:
            print("Testing using test set: {}".format(test_set))
            built_ins = CompilerBuiltIns(
                test_set["compiler"], test_set["args"], test_set["filename"])
            self.assertIn("-D__OBJC__=1", built_ins.flags)

    def test_objcpp(self):
        """Test retrieval of flags for an Objective-C++ compiler.

        We check if we can get flags for an Objective-C++ compiler.
        For this, we look if we can find an explicit language flag in the
        compiler argument list.
        """
        test_data = [
            {
                "args": ["-x", "objective-c++"],
                "filename": None,
                "compiler": "clang"
            }
        ]
        for test_set in test_data:
            print("Testing using test set: {}".format(test_set))
            built_ins = CompilerBuiltIns(
                test_set["compiler"], test_set["args"], test_set["filename"])
            self.assertIn("-D__OBJC__=1", built_ins.flags)
            is_cpp = False
            for define in built_ins.defines:
                if define.startswith("-D__cplusplus="):
                    is_cpp = True
            self.assertTrue(is_cpp)
