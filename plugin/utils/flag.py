"""Wraps a flag class."""
import logging
from ..tools import File


log = logging.getLogger("ECC")


class Flag:
    """Utility class for storing possibly separated flag.

    Attributes:
        PREFIXES_WITH_PATHS (str[]): Full list of prefixes that are followed
                                     by paths.
        SEPARABLE_PREFIXES (str[]): Full list of prefixes that may take a
                                    second part as an input.
    """

    def __init__(self, prefix, body):
        """Initialize a flag with two parts.

        Args:
            prefix (str): Flag's prefix. Can be empty.
            body (str): The body of the flag that combined with the prefix
                creates the full flag.
        """
        self.__prefix = prefix
        self.__body = body

    @staticmethod
    def create(part_1, part_2=None, current_folder=''):
        """Initialize a flag with two parts.

        There is a number of sutuations that can happen here. It can be that
        part_1 holds a separable prefix and part_2 the actual flag. Another
        alternative is that part_2 is empty and part_1 holds a separable prefix
        merged with the body of the flag. If non of these happen, then part_1
        holds a non-separable flag.

        Args:
            part_1 (str): First (or only) part of the flag.
            part_2 (str, optional): Second part if present.

        Returns:
           (Flag[]): A list of flags in canonical form.
        """
        def expand_paths(prefix, body):
            """Return all expanded flags from given unexpanded body."""
            if prefix in Flag.PREFIXES_WITH_PATHS:
                all_flags = []
                for expanded_body in File.expand_all(
                        body, current_folder=current_folder):
                    all_flags.append(Flag(prefix, expanded_body))
                return all_flags
            # This does not hold a path. Therefore we don't need to expand it.
            return [Flag(prefix, body)]

        part_1 = part_1.strip()
        if part_2:
            # We have been provided a prefix.
            part_2 = part_2.strip()
            if part_1 not in Flag.SEPARABLE_PREFIXES:
                log.warning("Unexpected flag prefix: '%s'", part_1)
            return expand_paths(prefix=part_1, body=part_2)
        for prefix in Flag.SEPARABLE_PREFIXES:
            if part_1.startswith(prefix):
                body = part_1.split(prefix)[1].strip()
                return expand_paths(prefix, body)
        return expand_paths(prefix="", body=part_1)

    @property
    def prefix(self):
        """Prefix of the flag. Empty if not separable."""
        return self.__prefix

    @property
    def body(self):
        """Body of the flag. Full flag if not separable."""
        return self.__body

    def as_list(self):
        """Return flag as list of its parts."""
        if self.__prefix:
            return [self.__prefix] + [self.__body]
        return [self.__body]

    def __str__(self):
        """Return flag as a string."""
        if self.__prefix:
            return self.__prefix + " " + self.__body
        return self.__body

    def __repr__(self):
        """Return flag as a printable string."""
        if self.__prefix:
            return '({}, {})'.format(self.__prefix, self.__body)
        return '({})'.format(self.__body)

    def __hash__(self):
        """Compute a hash of a flag."""
        if self.__prefix:
            return hash(self.__prefix + self.__body)
        return hash(self.__body)

    def __eq__(self, other):
        """Check if it is equal to another flag."""
        return self.__prefix == other.prefix and self.__body == other.body

    @staticmethod
    def tokenize_list(all_split_line, current_folder=''):
        """Find flags, that need to be separated and separate them.

        Args:
            all_split_line (str[]): A list of all flags split.

        Returns (Flag[]): A list of flags containing two parts if needed.
        """
        flags = []
        skip = False
        log.debug("Tokenizing: %s", all_split_line)
        for i, entry in enumerate(all_split_line):
            if entry.startswith("#"):
                continue
            if skip:
                skip = False
                continue
            if entry in Flag.SEPARABLE_PREFIXES:
                # add both this and next part to a flag
                if (i + 1) < len(all_split_line):
                    flags += Flag.create(all_split_line[i],
                                         all_split_line[i + 1],
                                         current_folder)
                    skip = True
                    continue
            flags += Flag.create(entry, current_folder=current_folder)
        return flags

    # All prefixes that denote includes.
    PREFIXES_WITH_PATHS = ["-isystem",
                           "-I",
                           "-isysroot",
                           "/I",
                           "-msvc",
                           "/msvc",
                           "-B",
                           "--cuda-path",
                           "-fmodules-cache-path",
                           "-fmodules-user-build-path",
                           "-fplugin",
                           "-fprebuilt-module-path"
                           "-fprofile-use",
                           "-F",
                           "-idirafter",
                           "-iframework",
                           "-iquote",
                           "-iwithprefix",
                           "-L",
                           "-objcmt-whitelist-dir-path",
                           "--ptxas-path"]

    # Generated from `clang -help` with regex: ([-/][\w-]+)\s\<\w+\>\s
    SEPARABLE_PREFIXES = ["-arcmt-migrate-report-output",
                          "-cxx-isystem",
                          "-dependency-dot",
                          "-dependency-file",
                          "-fmodules-user-build-path",
                          "-F",
                          "-idirafter",
                          "-iframework",
                          "-imacros",
                          "-include-pch",
                          "-include",
                          "-iprefix",
                          "-iquote",
                          "-isysroot",
                          "-isystem",
                          "-ivfsoverlay",
                          "-iwithprefixbefore",
                          "-iwithprefix",
                          "-iwithsysroot",
                          "-I",
                          "-meabi",
                          "-MF",
                          "-mllvm",
                          "-Xclang",
                          "-module-dependency-dir",
                          "-MQ",
                          "-mthread-model",
                          "-MT",
                          "-o",
                          "-serialize-diagnostics",
                          "-working-directory",
                          "-Xanalyzer",
                          "-Xassembler",
                          "-Xlinker",
                          "-Xpreprocessor",
                          "-x",
                          "-z",
                          "/FI",
                          "/I",
                          "/link",
                          "/Tc",
                          "/Tp",
                          "/U"]
