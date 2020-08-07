"""Wraps a flag class."""
import logging
import platform
from .file import File


log = logging.getLogger("ECC")


class Flag:
    """Utility class for storing possibly separated flag.

    Note that only flags that start with a valid indicator ("-" or "/") are
    considered valid.

    Attributes:
        PREFIXES_WITH_PATHS (str[]): Full list of prefixes that are followed
                                     by paths.
        SEPARABLE_PREFIXES (str[]): Full list of prefixes that may take a
                                    second part as an input.
        POSSIBLE_SEPARATORS (str[]): A list of strings that can separate the
                                    prefix of a flag from its body.
        FLAG_INDICATORS (str[]): A list of all chars that indicate a flag prefix
    """

    def __init__(self, prefix, body, separator=''):
        """Initialize a flag with two parts.

        Args:
            prefix (str): Flag's prefix. Can be empty.
            body (str): The body of the flag that combined with the prefix
                creates the full flag.
            separator(str): A separator between the prefix and the body.
        """
        self.__body = body
        self.__prefix = prefix
        self.__separator = separator

    @property
    def prefix(self):
        """Prefix of the flag. Empty if not separable."""
        return self.__prefix

    @property
    def body(self):
        """Body of the flag. Full flag if not separable."""
        return self.__body

    @property
    def separator(self):
        """Separator of the flag. Empty if not separable."""
        return self.__separator

    @staticmethod
    def indicates_flag(string):
        """Check if the flag starts with a valid flag indicator."""
        for flag_indicator in Flag.FLAG_INDICATORS:
            if string.startswith(flag_indicator):
                return True
        log.debug("'%s' doesn't start with any valid flag prefix: %s",
                  string, Flag.FLAG_INDICATORS)
        return False

    def as_list(self):
        """Return flag as list of its parts."""
        if self.__prefix:
            return [self.__prefix] + [self.__body]
        return [self.__body]

    def __str__(self):
        """Return flag as a string."""
        if self.__prefix:
            return self.__prefix + self.__separator + self.__body
        return self.__body

    def __repr__(self):
        """Return flag as a printable string."""
        if self.__prefix:
            return '({}{}{})'.format(self.__prefix,
                                     self.__separator,
                                     self.__body)
        return '({})'.format(self.__body)

    def __hash__(self):
        """Compute a hash of a flag."""
        if self.__prefix:
            return hash(self.__prefix + self.__body)
        return hash(self.__body)

    def __eq__(self, other):
        """Check if it is equal to another flag."""
        return self.__prefix == other.prefix\
            and self.__body == other.body\
            and self.__separator == other.separator

    @staticmethod
    def tokenize_list(all_split_line,
                      current_folder=''):
        """Find flags, that need to be separated and separate them.

        Args:
            all_split_line (str[]): A list of all flags split.
            current_folder (str): Current folder.

        Returns (Flag[]): A list of flags containing two parts if needed.
        """
        flags = []
        skip_next_entry = False
        log.debug("Tokenizing: %s", all_split_line)
        for i, entry in enumerate(all_split_line):
            entry = entry.strip()
            if entry.startswith("#"):
                continue
            if skip_next_entry:
                # Previous entry was a separable flag, so this one is its
                # contents and we have already processed it.
                skip_next_entry = False
                continue
            if entry in Flag.SEPARABLE_PREFIXES:
                # add both this and next part to a flag
                if (i + 1) < len(all_split_line):
                    next_entry = all_split_line[i + 1].strip()
                    flags += Flag.Builder()\
                        .with_prefix(entry)\
                        .with_separator(' ')\
                        .with_body(next_entry)\
                        .build_with_expansion(current_folder)
                    skip_next_entry = True
                    continue
            flags += Flag.Builder()\
                .from_unparsed_string(entry)\
                .build_with_expansion(current_folder)
        return flags

        @staticmethod
        def find_flag_idx(flags, prefix):
            """Find index of flag with given prefix in list.

            Args:
            flags (str[]): A list of all flags.
            prefix (str): A query prefix that the flag has to start with.

            Returns: index of found flag or None if not found
            """
            for idx, flag in enumerate(flags):
                if flag.startswith(prefix):
                    return idx
            return None

    class Builder:
        """Builder for flags providing a nicer interface."""

        def __init__(self):
            """Initialize the empty internal flag."""
            self.__prefix = ''
            self.__body = ''
            self.__separator = ''

        def from_unparsed_string(self, chunk):
            """Parse an unknown string into body and prefix."""
            chunk = chunk.strip()
            if not Flag.indicates_flag(chunk):
                # This is not a valid flag, so reset all values to default.
                return Flag.Builder()
            for prefix in Flag.SEPARABLE_PREFIXES:
                if chunk.startswith(prefix):
                    self.__prefix = prefix
                    rest = chunk[len(prefix):]
                    if rest and rest[0] in Flag.POSSIBLE_SEPARATORS:
                        self.__separator = rest[0]
                        rest = rest[1:]
                    self.__body = rest.strip()
                    return self
            # We did not find any separable prefix, so it's all body.
            if not self.__body:
                self.__body = chunk
            return self

        def with_body(self, body):
            """Set the body to the internal flag."""
            self.__body = body.strip()
            return self

        def with_separator(self, separator):
            """Set the separator to the internal flag."""
            self.__separator = separator
            return self

        def with_prefix(self, prefix):
            """Set the prefix to the internal flag."""
            self.__prefix = prefix.strip()
            if self.__prefix not in Flag.SEPARABLE_PREFIXES:
                log.warning("Unexpected flag prefix: '%s'", self.__prefix)
            return self

        def build_with_expansion(self, current_folder='', wildcard_values={}):
            """Expand all expandable entries and return a resulting list."""
            if not self.__body and not self.__prefix:
                return []
            if self.__prefix in Flag.PREFIXES_WITH_PATHS:
                all_flags = []
                for expanded_body in File.expand_all(
                        input_path=self.__body,
                        wildcard_values=wildcard_values,
                        current_folder=current_folder):
                    all_flags.append(Flag(prefix=self.__prefix,
                                          body=expanded_body,
                                          separator=self.__separator))
                return all_flags
            # This does not hold a path. Therefore we don't need to expand it.
            return [Flag(prefix=self.__prefix,
                         body=self.__body,
                         separator=self.__separator)]

        def build(self):
            """Create a flag."""
            if self.__prefix in Flag.PREFIXES_WITH_PATHS:
                self.__body = File.canonical_path(self.__body)
            return Flag(prefix=self.__prefix,
                        body=self.__body,
                        separator=self.__separator)

    # All strings that might separate the prefix of a flag from its body.
    POSSIBLE_SEPARATORS = [" ", "="]

    # All strings that indicate that a string is a flag.
    ALL_FLAG_INDICATORS = {
        "Windows": ["-", "/"],
        "Linux": ["-"],
        "Darwin": ["-"],
    }

    FLAG_INDICATORS = ALL_FLAG_INDICATORS[platform.system()]

    # All prefixes that denote includes.
    PREFIXES_WITH_PATHS = set([
        "--cuda-path",
        "--ptxas-path"
        "-B",
        "-cxx-isystem",
        "-F",
        "-fmodules-cache-path",
        "-fmodules-user-build-path",
        "-fplugin",
        "-fprebuilt-module-path"
        "-fprofile-use",
        "-I",
        "-idirafter",
        "-iframework",
        "-iframeworkwithsysroot",
        "-imacros",
        "-include",
        "-include-pch",
        "-iprefix",
        "-iquote",
        "-isysroot",
        "-isystem",
        "-isystem",
        "-isystem-after",
        "-iwithprefix",
        "-iwithprefixbefore",
        "-iwithsysroot",
        "-L",
        "-MF",
        "-module-dependency-dir",
        "-msvc",
        "-o"
        "-objcmt-whitelist-dir-path",
        "/cxx-isystem",
        "/I",
        "/msvc",
    ])

    # Generated from `clang -help` with regex: ([-/][\w-]+)\s\<\w+\>\s
    SEPARABLE_PREFIXES = set([
        "--analyzer-output",
        "--config",
        "-arcmt-migrate-report-output",
        "-cxx-isystem",
        "-dependency-dot",
        "-dependency-file",
        "-F",
        "-fmodules-cache-path",
        "-fmodules-user-build-path",
        "-I",
        "-idirafter",
        "-iframework",
        "-imacros",
        "-include",
        "-include-pch",
        "-iprefix",
        "-iquote",
        "-isysroot",
        "-isystem",
        "-ivfsoverlay",
        "-iwithprefix",
        "-iwithprefixbefore",
        "-iwithsysroot",
        "-meabi",
        "-MF",
        "-MJ",
        "-mllvm",
        "-module-dependency-dir",
        "-MQ",
        "-MT",
        "-mthread-model",
        "-o",
        "-serialize-diagnostics",
        "-target",
        "-T",
        "-Tbss",
        "-Tdata",
        "-Ttext",
        "-working-directory",
        "-x",
        "-Xanalyzer",
        "-Xassembler",
        "-Xclang",
        "-Xlinker",
        "-Xopenmp-target",
        "-Xpreprocessor",
        "-z",
        "/FI",
        "/I",
        "/link",
        "/Tc",
        "/Tp",
        "/U"
    ])
