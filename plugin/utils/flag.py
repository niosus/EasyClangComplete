"""Wraps a flag class."""


class Flag:
    """Utility class for storing possibly separated flag."""

    def __init__(self, part_1, part_2=None):
        """Initialize a flag with two parts.

        Args:
            part_1 (str): First (or only) part of the flag.
            part_2 (str, optional): Second part if present.
        """
        if part_2:
            self.__prefix = part_1.strip()
            self.__body = part_2.strip()
        else:
            self.__prefix = ""
            self.__body = part_1.strip()

    def prefix(self):
        """Prefix of the flag. Empty if not separable."""
        return self.__prefix

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
        return self.__prefix == other.prefix() and self.__body == other.body()

    @staticmethod
    def tokenize_list(all_split_line):
        """Find flags, that need to be separated and separate them.

        Args:
            all_split_line (str[]): A list of all flags split.

        Returns (Flag[]): A list of flags containing two parts if needed.
        """
        # FIXME(igor): probably need to get it from `clang -help`
        separable_prefixes = ["-I", "/I", "-isystem",
                              "-cxx-isystem", "-F",
                              "-isysroot", "-iprefix", "-x"]

        flags = []
        skip = False
        for i, entry in enumerate(all_split_line):
            if entry.startswith("#"):
                continue
            if skip:
                skip = False
                continue
            if entry in separable_prefixes:
                # add both this and next part to a flag
                flags.append(Flag(all_split_line[i], all_split_line[i + 1]))
                skip = True
                continue
            flags.append(Flag(entry))
        return flags
