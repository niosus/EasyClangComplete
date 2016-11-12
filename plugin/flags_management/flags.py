import logging


class Flags(object):

    def __init__(self, view, include_prefixes):
        self._include_prefixes = include_prefixes
        self._flags = []

    def as_list(self):
        raise NotImplementedError("calling abstract method")

    def valid(self):
        if self._flags:
            return True
        return False

    def _parse_flags(self, folder, lines):
        """
        Parse the flags in a given file

        Args:
            folder (str): current folder
            lines (str[]): lines to parse

        Returns:
            str[]: flags
        """

        def to_absolute_include_path(flag, include_prefixes):
            """ Change path of include paths to absolute if needed.

            Args:
                flag (str): flag to check for relative path and fix if needed

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
            flags.append(to_absolute_include_path(line,
                                                  self._include_prefixes))
        return flags
