"""Holds an abstract class defining a flags source.
"""
from os import path


class FlagsSource(object):
    """An abstract class defining a Flags Source.
    """
    def __init__(self, include_prefixes):
        """Initialize default flags storage.

        Args:
            include_prefixes (str[]): valid include prefixes.
        """
        self._include_prefixes = include_prefixes

    def get_flags(self, file_path=None):
        """An abstract function to gets flags for a view path.

        Raises:
            NotImplementedError: Should not be called directly.
        """
        raise NotImplementedError("calling abstract method")

    def _parse_flags(self, folder, lines):
        """Parse the flags from given lines.

        Args:
            folder (str): current folder
            lines (str[]): lines to parse

        Returns:
            str[]: flags
        """
        def to_absolute_include_path(flag, include_prefixes):
            """Change path of include paths to absolute if needed.

            Args:
                flag (str): flag to check for relative path and fix if needed
                include_prefixes (TYPE): Description

            Returns:
                str: either original flag or modified to have absolute path
            """
            for prefix in include_prefixes:
                if flag.startswith(prefix):
                    include_path = flag[len(prefix):].strip()
                    if not path.isabs(include_path):
                        include_path = path.join(folder, include_path)
                    return prefix + path.normpath(include_path)
            return flag

        flags = []
        for line in lines:
            line = line.strip()
            if line.startswith("#"):
                continue
            flags.append(to_absolute_include_path(
                line, self._include_prefixes))
        return flags
