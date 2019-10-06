"""Get compiler built-in flags."""

import logging as _logging

from os import path
from ..utils.file import File
from ..utils.tools import Tools

_log = _logging.getLogger("ECC")


class CompilerBuiltIns:
    """
    Get the built in flags used by a compiler.

    This class tries to retrieve the built-in flags of a compiler.
    As an input, it gets the call to a compiler plus some default
    flags. It tries to guess some further required inputs and then
    queries the compiler for its built-in defines and include paths.
    """

    __cache = dict()
    __TEMP_DEFAULT_FILE_NAME = "ECC_temp_file.cpp"

    def __init__(self, compiler, lang_flags, filename=None):
        """
        Create an object holding the built-in flags of a compiler.

        This constructs a new object which holds the built-in flags
        used by a compiler. The `args` is the call to the compiler; either
        a string or a list of strings. If a list of strings is provided, it
        is interpreted as the call of a compiler (i.e. the first entry
        is the compiler to call and everything else are arguments to the
        compiler). If a single string is given, it is parsed into a string
        list first. The `filename` is the name of the file that is compiled
        by the arguments. It can be passed in to derive additional
        information.
        """
        super().__init__()
        self.__defines = []
        self.__includes = []

        working_dir = None
        if filename is None:
            working_dir = File.get_temp_dir()
            filename = CompilerBuiltIns.__TEMP_DEFAULT_FILE_NAME
            # Creates the file on disk.
            File(path.join(working_dir, filename))
        else:
            working_dir = path.dirname(filename)
            filename = path.basename(filename)
        _log.debug("Generating default flags from file '%s' in folder '%s'",
                   filename, working_dir)

        self.__generate_flags(compiler=compiler,
                              filename=filename,
                              working_dir=working_dir,
                              lang_flags=lang_flags)

    def __generate_flags(self, compiler, filename, working_dir, lang_flags):
        if not lang_flags:
            lang_flags = []
        if not compiler:
            return
        cmd = [compiler] + lang_flags + ['-c', filename, '-dM', '-v', '-E']
        cmd_str = ' '.join(cmd)
        if cmd_str in CompilerBuiltIns.__cache:
            _log.debug("Using cached default flags.")
            self.__includes, self.__defines = CompilerBuiltIns.__cache[cmd_str]
            return
        _log.debug("Generating new default flags with cmd: '%s'", cmd)
        output = Tools.run_command(cmd, cwd=working_dir)
        if not output:
            _log.warning("No output from cmd to get default flags: %s", cmd)
            return

        def get_includes(clang_output):
            lines = clang_output.split('\n')
            start_idx_quotes = 0
            start_idx_angular = 0
            end_idx_quotes = 0
            end_idx_angular = 0
            for idx, line in enumerate(lines):
                if line.startswith('#include "..." search starts here'):
                    start_idx_quotes = idx + 1
                elif line.startswith('#include <...> search starts here'):
                    end_idx_quotes = idx
                    start_idx_angular = idx + 1
                elif line.startswith('End of search list'):
                    end_idx_angular = idx
            includes = []
            for idx in range(start_idx_quotes, end_idx_quotes):
                includes.append('-I' + path.normpath(lines[idx].strip()))
            for idx in range(start_idx_angular, end_idx_angular):
                # We should append these also with -I to avoid errors in g++.
                include_path = path.normpath(lines[idx].strip())
                if "framework directory" in include_path:
                    includes.append('-F' + path.normpath(lines[idx].strip()))
                else:
                    includes.append('-I' + path.normpath(lines[idx].strip()))
            return includes

        def get_defines(clang_output):
            import re
            defines = []
            for line in output.splitlines():
                m = re.search(r'#define ([\w()]+) (.+)', line)
                if m is not None:
                    defines.append("-D{}={}".format(m.group(1), m.group(2)))
                else:
                    m = re.search(r'#define (\w+)', line)
                    if m is not None:
                        defines.append("-D{}".format(m.group(1)))
            _log.debug("Got defines: %s", defines)
            return defines

        self.__includes = get_includes(output)
        self.__defines = get_defines(output)
        CompilerBuiltIns.__cache[cmd_str] = (self.__includes, self.__defines)

    @property
    def defines(self):
        """The built-in defines provided by the compiler."""
        return self.__defines

    @property
    def includes(self):
        """The list of built-in include paths used by the compiler."""
        return self.__includes

    @property
    def flags(self):
        """
        The list of built-in flags.

        This property holds the combined list of built-in defines and
        include paths of the compiler.
        """
        return self.__defines + self.__includes

    @staticmethod
    def clean_cache():
        """Clear all entries in the cache."""
        CompilerBuiltIns.__cache.clear()
