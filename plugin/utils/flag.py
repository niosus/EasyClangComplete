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
            self.__prefix = part_1
            self.__body = part_2
        else:
            self.__prefix = ""
            self.__body = part_1

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

    def __hash__(self):
        """Compute a hash of a flag."""
        if self.__prefix:
            return hash(self.__prefix + self.__body)
        return hash(self.__body)

    def __eq__(self, other):
        """Check if it is equal to another flag."""
        return self.__prefix == other.prefix() and self.__body == other.body()

    @staticmethod
    def tokenize_list(all_split_line, separable_prefixes):
        """Find flags, that need to be separated and separate them.

        Args:
            all_split_line (str[]): A list of all flags split.
            separable_prefixes (str[]): A list of all prefixes that require
                separation from the body.

        Returns (Flag[]): A list of flags containing two parts if needed.
        """
        flags = []
        skip = False
        for i in range(len(all_split_line)):
            if skip:
                skip = False
                continue
            if all_split_line[i] in separable_prefixes:
                # add both parts to a flag
                flags.append(Flag(all_split_line[i], all_split_line[i + 1]))
                skip = True
                continue
            flags.append(Flag(all_split_line[i]))
        return flags
