"""Holds an abstract class defining a flags source."""
from os import path

from ..tools import Tools
from ..tools import SearchScope
from ..utils.flag import Flag


class FlagsSource(object):
    """An abstract class defining a Flags Source."""

    def __init__(self, include_prefixes):
        """Initialize default flags storage."""
        self._include_prefixes = include_prefixes

    def get_flags(self, file_path=None, search_scope=None):
        """Get flags for a view path [ABSTRACT].

        Raises:
            NotImplementedError: Should not be called directly.
        """
        raise NotImplementedError("calling abstract method")

    @staticmethod
    def parse_flags(folder, chunks, include_prefixes):
        """Parse the flags from given chunks produced by separating string.

        Args:
            folder (str): Current folder
            chunks (str[]): Chunks to parse. Can be lines of a file or parts
                of flags produced with shlex.split.
            include_prefixes (str[]): Allowed include prefixes.

        Returns:
            Flag[]: Flags with absolute include paths.
        """
        def normalize_and_expand(flag, include_prefixes):
            """Change path of include paths to absolute if needed.

            Args:
                flag (Flag): flag to check for relative path and fix if needed
                include_prefixes (str[]): allowed include prefixes

            Returns:
                Flag[]: a list of flags with absolute paths and expanded stars
            """
            flags = []
            for prefix in include_prefixes:
                if flag.prefix == prefix:
                    include_path = flag.body
                    if not path.isabs(include_path):
                        include_path = path.join(folder, include_path)
                    paths = Tools.expand_star_wildcard(include_path)
                    for expanded_path in paths:
                        flags.append(
                            Flag(prefix, path.normpath(expanded_path)))
                    return flags
                # this flag is not separable, check if we still need to update
                # relative path to absolute one
                if flag.body.startswith(prefix):
                    include_path = flag.body[len(prefix):]
                    if not path.isabs(include_path):
                        include_path = path.normpath(
                            path.join(folder, include_path))
                    paths = Tools.expand_star_wildcard(include_path)
                    for expanded_path in paths:
                        flags.append(
                            Flag(prefix + path.normpath(expanded_path)))
                    return flags
            # We did not expand anything and did no changes.
            return [flag]

        local_flags = Flag.tokenize_list(chunks)
        absolute_flags = []
        for flag in local_flags:
            absolute_flags += normalize_and_expand(flag, include_prefixes)
        return absolute_flags

    @staticmethod
    def _update_search_scope(search_scope, file_path):
        if search_scope:
            # we already know what we are doing. Leave search scope unchanged.
            return search_scope
        # search database from current file up the tree
        return SearchScope(from_folder=path.dirname(file_path))

    def _get_cached_from(self, file_path):
        """Get cached path for file path.

        Args:
            file_path (str): Input file path.

        Returns:
            str: Path to the cached flag source path.
        """
        if file_path and file_path in self._cache:
            return self._cache[file_path]
        return None
