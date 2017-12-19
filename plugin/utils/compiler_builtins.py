"""Get compiler built-in flags."""

import logging as _logging

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

    __DEFINES_BLACKLIST = [
        "__USER_LABEL_PREFIX__",
        "__STDC_HOSTED__",
        "__REGISTER_PREFIX__",
        "__STDC__"
    ]

    def __init__(self, args):
        """
        Create an object holding the built-in flags of a compiler.

        This constructs a new object which holds the built-in flags
        used by a compiler. The `args` is the call to the compiler; either
        a string or a list of strings. If a list of strings is provided, it
        is interpreted as the call of a compiler (i.e. the first entry
        is the compiler to call and everything else are arguments to the
        compiler). If a single string is given, it is parsed into a string
        list first.
        """
        from shlex import split
        super().__init__()
        self._defines = list()
        self._include_paths = list()
        if isinstance(args, str):
            # Parse arguments into list of strings first
            args = split(args)
        # Guess the compiler and standard:
        (compiler, std) = self._guess_compiler(args)
        if compiler is not None:
            # Guess the language (we need to pass it to the compiler
            # explicitly):
            language = self._guess_language(compiler)
            # Get defines and include paths from the compier:
            cfg = (compiler, std, language)
            self._debug("Getting default flags for {}".format(cfg))
            if cfg in CompilerBuiltIns.__cache:
                self._debug("Reusing flags from cache")
                (defines, includes) = CompilerBuiltIns.__cache[cfg]
            else:
                self._debug("Querying compiler for defaults")
                defines = self._get_default_flags(compiler, std, language)
                includes = self._get_default_include_paths(
                    compiler, std, language)
                CompilerBuiltIns.__cache[cfg] = (defines, includes)
            self._defines = defines
            self._include_paths = includes

    @property
    def defines(self):
        """The built-in defines provided by the compiler."""
        return self._defines

    @property
    def include_paths(self):
        """The list of built-in include paths used by the compiler."""
        return self._include_paths

    @property
    def flags(self):
        """
        The list of built-in flags.

        This property holds the combined list of built-in defines and
        include paths of the compiler.
        """
        return self._defines + self._include_paths

    def _guess_compiler(self, args):
        compiler = None
        std = None
        if len(args) > 0:
            compiler = args[0]
        else:
            self._debug("Got empty command line - cannot extract compiler")
        if len(args) > 1:
            for arg in args[1:]:
                if arg.startswith("-std="):
                    std = arg[5:]
        return (compiler, std)

    def _guess_language(self, compiler):
        """
        Try to guess the language based on the compiler.

        This is required as we need to explicitly pass a language when asking
        the compiler later for its default flags.
        """
        if compiler.endswith("++"):
            return "c++"
        else:
            return "c"

    def _get_default_flags(self, compiler, std, language):
        import subprocess
        import re

        result = list()

        args = [compiler, "-x", language]
        if std is not None:
            args += ['-std=' + std]
        args += ["-dM", "-E", "-"]

        try:
            res = subprocess.Popen(
                args,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
            )
            res.wait()
            for line in res.stdout.read().decode().splitlines():
                m = re.search(r'#define ([\w()]+) (.+)', line)
                if m is not None:
                    result.append("-D{}={}".format(m.group(1), m.group(2)))
                else:
                    m = re.search(r'#define (\w+)', line)
                    if m is not None:
                        result.append("-D{}".format(m.group(1)))
        except FileNotFoundError:
            self._warn("Cannot find compiler %s in PATH." % compiler)

        return self._filter_defines(result)

    def _get_default_include_paths(self, compiler, std, language):
        import subprocess
        import re

        result = list()

        args = [compiler, '-x', language]
        if std is not None:
            args += ['-std=' + std]
        args += ['-Wp,-v', '-E', '-']

        try:
            res = subprocess.Popen(
                args,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
            )
            res.wait()
            pick = False
            for line in res.stdout.read().decode().splitlines():
                if '#include <...> search starts here:' in line:
                    pick = True
                    continue
                if '#include "..." search starts here:' in line:
                    pick = True
                    continue
                if 'End of search list.' in line:
                    break
                if pick:
                    m = re.search(r'\s*(.*)$', line)
                    if m is not None:
                        result.append("-I{}".format(m.group(1)))
        except FileNotFoundError:
            self._warn("Cannot find compiler %s in PATH." % compiler)

        return result

    def _filter_defines(self, defines):
        # Remove some default flags which get set by clang itself.
        # Otherwise, we will get error later:
        for flag in CompilerBuiltIns.__DEFINES_BLACKLIST:
            prefix = "-D%s" % flag
            for define in defines:
                if define.startswith(prefix):
                    defines.remove(define)
        return defines

    def _debug(self, msg):
        _log.debug("[compilerbuiltins] %s" % msg)

    def _warn(self, msg):
        _logging.warning("[compilerbuiltins] %s" % msg)
