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

    def __init__(self, prefix, body, separator=' '):
        """Initialize a flag with two parts.

        Args:
            prefix (str): Flag's prefix. Can be empty.
            body (str): The body of the flag that combined with the prefix
                creates the full flag.
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
        skip_next_entry = False
        log.debug("Tokenizing: %s", all_split_line)
        for i, entry in enumerate(all_split_line):
            if entry.startswith("#"):
                continue
            if skip_next_entry:
                skip_next_entry = False
                continue
            if entry in Flag.SEPARABLE_PREFIXES:
                # add both this and next part to a flag
                if (i + 1) < len(all_split_line):
                    flags += Flag.Builder()\
                        .with_prefix(all_split_line[i])\
                        .with_body(all_split_line[i + 1])\
                        .build_with_expansion(current_folder)
                    skip_next_entry = True
                    continue
            flags += Flag.Builder()\
                .from_unparsed_string(entry)\
                .build_with_expansion(current_folder)
        return flags

    class Builder:
        """Builder for flags providing a nicer interface."""

        def __init__(self):
            """Initialize the empty internal flag."""
            self.__prefix = ''
            self.__body = ''

        def from_unparsed_string(self, chunk):
            """Parse an unknown string into body and prefix."""
            chunk = chunk.strip()
            for prefix in Flag.SEPARABLE_PREFIXES:
                if chunk.startswith(prefix):
                    self.__prefix = prefix
                    self.__body = chunk[len(prefix):]
                    break
            # We did not find any separable prefix, so it's all body.
            if not self.__body:
                self.__body = chunk
            return self

        def with_body(self, body):
            """Set the body to the internal flag."""
            self.__body = body.strip()
            return self

        def with_prefix(self, prefix):
            """Set the prefix to the internal flag."""
            self.__prefix = prefix.strip()
            if self.__prefix not in Flag.SEPARABLE_PREFIXES:
                log.warning("Unexpected flag prefix: '%s'", self.__prefix)
            return self

        def build_with_expansion(self, current_folder='', wildcard_values={}):
            """Expand all expandable entries and return a resulting list."""
            if self.__prefix in Flag.PREFIXES_WITH_PATHS:
                all_flags = []
                for expanded_body in File.expand_all(
                        input_path=self.__body,
                        wildcard_values=wildcard_values,
                        current_folder=current_folder):
                    all_flags.append(Flag(self.__prefix, expanded_body))
                return all_flags
            # This does not hold a path. Therefore we don't need to expand it.
            return [Flag(prefix=self.__prefix, body=self.__body)]

        def build(self):
            """Create a flag."""
            if self.__prefix in Flag.PREFIXES_WITH_PATHS:
                self.__body = File.canonical_path(self.__body)
            return Flag(self.__prefix, self.__body)

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
