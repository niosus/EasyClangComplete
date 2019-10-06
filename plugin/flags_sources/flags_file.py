"""Stores a class that manages flags loading from .clang_complete files.

Attributes:
    log (logging.Logger): current logger.
"""
from .flags_source import FlagsSource
from ..utils.file import File
from ..utils.singleton import FlagsFileCache
from ..utils.flag import Flag

from os import path

import logging

log = logging.getLogger("ECC")


class FlagsFile(FlagsSource):
    """Manages flags parsing from .clang_complete file.

    Attributes:
        cache (dict): Cache of all parsed files to date. Stored by full file
            path. Needed to avoid reparsing the file multiple times.
        path_for_file (dict): A path to a database for every source file path.
    """
    _FILE_NAME = ".clang_complete"

    def __init__(self, include_prefixes):
        """Initialize a flag file storage.

        Args:
            include_prefixes (str[]): A List of valid include prefixes.
        """
        super().__init__(include_prefixes)
        self._cache = FlagsFileCache()

    def get_flags(self, file_path=None, search_scope=None):
        """Get flags for file.

        Args:
            file_path (None, optional): A path to the query file.
            search_scope (SearchScope, optional): Where to search for a
                .clang_complete file.

        Returns:
            str[]: Return a list of flags in this .clang_complete file
        """
        # prepare search scope
        search_scope = self._update_search_scope_if_needed(
            search_scope, file_path)
        # check if we have a hashed version
        log.debug("[clang_complete_file]:[get]: for file %s", file_path)
        cached_flags_path = self._get_cached_from(file_path)
        log.debug("[clang_complete_file]:[cached]: '%s'", cached_flags_path)
        flags_file = File.search(self._FILE_NAME, search_scope)
        if not flags_file:
            return None
        flags_file_path = flags_file.full_path
        log.debug("[clang_complete_file]:[current]: '%s'", flags_file_path)
        if not flags_file_path:
            return None

        flags = None
        parsed_before = flags_file_path in self._cache
        if parsed_before:
            log.debug("[clang_complete_file]: found cached .clang_complete")
            cached_flags_path = flags_file_path
        flags_file_path_same = (flags_file_path == cached_flags_path)
        flags_file_same = File.is_unchanged(cached_flags_path)
        if flags_file_path_same and flags_file_same:
            log.debug("[clang_complete_file]:[unchanged]: load cached")
            return self._cache[cached_flags_path]
        log.debug("[clang_complete_file]:[changed]: load new")
        if cached_flags_path and cached_flags_path in self._cache:
            del self._cache[cached_flags_path]
        flags = self.__flags_from_clang_file(File(flags_file_path))
        if flags:
            self._cache[cached_flags_path] = flags
        if file_path:
            self._cache[file_path] = flags_file_path
        # now we return whatever we have
        return flags

    def __flags_from_clang_file(self, file):
        """Get flags from .clang_complete file.

        Args:
            file (File): A file objects that represents the file to parse.

        Returns:
            str[]: List of flags from file.
        """
        if not path.exists(file.full_path):
            log.debug(".clang_complete does not exist yet. No flags present.")
            return []
        if not file.loaded():
            log.error("cannot get flags from clang_complete_file. No file.")
            return []

        return Flag.tokenize_list(file.lines, file.folder)
