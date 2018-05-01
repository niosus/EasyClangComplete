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

    def __init__(self, args, filename):
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
        from shlex import split
        super().__init__()
        self._defines = list()
        self._include_paths = list()
        if isinstance(args, str):
            # Parse arguments into list of strings first
            args = split(args)
        # Guess the compiler and standard:
        (compiler, std) = self._guess_compiler(args)
        self._compiler = compiler
        self._std = std
        self._language = None
        if compiler is not None:
            # Guess the language (we need to pass it to the compiler
            # explicitly):
            language = self._guess_language(compiler, args, filename)
            # Get defines and include paths from the compier:
            cfg = (compiler, std, language)
            _log.debug("Getting default flags for {}".format(cfg))
            if cfg in CompilerBuiltIns.__cache:
                _log.debug("Reusing flags from cache")
                (defines, includes) = CompilerBuiltIns.__cache[cfg]
            else:
                _log.debug("Querying compiler for defaults")
                defines = self._get_default_flags(compiler, std, language)
                includes = self._get_default_include_paths(
                    compiler, std, language)
                CompilerBuiltIns.__cache[cfg] = (defines, includes)
            self._defines = defines
            self._include_paths = includes
            self._language = language

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

    @property
    def compiler(self):
        """The detected compiler."""
        return self._compiler

    @property
    def std(self):
        """The detected standard to use."""
        return self._std

    @property
    def language(self):
        """The detected target language."""
        return self._language

    def _guess_compiler(self, args):
        compiler = None
        std = None
        if len(args) > 0:
            compiler = args[0]
        else:
            _log.debug("Got empty command line - cannot extract compiler")
        if len(args) > 1:
            for arg in args[1:]:
                if arg.startswith("-std="):
                    std = arg[5:]
        return (compiler, std)

    def _guess_language(self, compiler, args, filename):
        """
        Try to guess the language based on the compiler.

        This is required as we need to explicitly pass a language when asking
        the compiler later for its default flags.

        TODO: It might be better to bind the view's language to the
              one we pass to the compiler instead of trying to guess
              stuff.
        """
        # First, we look for a `-x` flag in the arguments. This flag usually
        # is used to select the language the compiler shall use to parse
        # the input file.
        from os.path import splitext
        language = None
        try:
            index = args.index("-x")
            try:
                language = args[index + 1]
            except IndexError:
                # The "-x" switch was given as last argument.
                _log.warning("Encountered -x switch without argument")
        except ValueError:
            # There's no "-x" flag. Hence, we try to guess the language from
            # the file name:
            if filename is not None:
                ext = splitext(filename)[1][1:]
                if ext in ["cc", "cpp", "cxx", "C", "c++"]:
                    language = "c++"
                elif ext in ["m", "mm"]:
                    language = "objective-c"
            if language is None:
                # If we still are not sure, we try to guess the language
                # from the compiler's name:
                if compiler.endswith("++"):
                    language = "c++"
        # Note: It could be that language is unset, in this case we just
        # won't pass any language flag to the compiler later, which
        # will cause the compiler's "native" flags to be used,
        #  i.e. usually for C.
        return language

    def _get_default_flags(self, compiler, std, language):
        import subprocess
        import re
        from ..tools import Tools

        result = list()

        args = [compiler]
        if language is not None:
            args += ["-x", language]
        if std is not None:
            args += ['-std=' + std]
        args += ["-dM", "-E", "-"]

        output = Tools.run_command(args, stdin=subprocess.DEVNULL, default="")
        for line in output.splitlines():
            m = re.search(r'#define ([\w()]+) (.+)', line)
            if m is not None:
                result.append("-D{}={}".format(m.group(1), m.group(2)))
            else:
                m = re.search(r'#define (\w+)', line)
                if m is not None:
                    result.append("-D{}".format(m.group(1)))
        return result

    def _get_default_include_paths(self, compiler, std, language):
        import subprocess
        import re
        from ..tools import Tools

        result = list()

        args = [compiler]
        if language is not None:
            args += ["-x", language]
        if std is not None:
            args += ['-std=' + std]
        args += ['-Wp', '-v', '-E', '-']

        output = Tools.run_command(args, stdin=subprocess.DEVNULL, default="")
        pick = False
        for line in output.splitlines():
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
        return result
