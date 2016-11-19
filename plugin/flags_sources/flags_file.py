"""Stores a class that manages flags loading from .clang_complete files.

Attributes:
    log (logging.Logger): current logger.
"""
from .flags_source import FlagsSource
from ..tools import File

from os import path

import logging

log = logging.getLogger(__name__)


class FlagsFile(FlagsSource):
    """Manages flags parsing from .clang_complete file.

    Attributes:
        cache (dict): Cache of all parsed files to date. Stored by full file
            path. Needed to avoid reparsing the file multiple times.
        path_for_file (dict): A path to a database for every source file path.
    """
    _FILE_NAME = ".clang_complete"

    cache = {}
    # TODO(igor): Do we need to cache the found flags file?
    path_for_file = {}

    def __init__(self, include_prefixes, search_scope):
        """Initialize a flag file storage.

        Args:
            include_prefixes (str[]): A List of valid include prefixes.
            search_scope (SearchScope): Where to search for a flags file.
        """
        super().__init__(include_prefixes)
        # TODO(igor): Do we need a search scope here?
        self.__search_scope = search_scope

    def get_flags(self, file_path=None):
        """Get flags for file.

        Args:
            file_path (None, optional): A path to the query file.

        Returns: str[]: Return a list of flags in this .clang_complete file
        """
        log.debug(" [clang_complete_file]: for file %s", file_path)
        cached_flags_path = super().get_cached_from(file_path)
        log.debug(" [clang_complete_file]:[cached]: '%s'", cached_flags_path)
        flags_file_path = super().find_current_in(
            self.__search_scope)
        log.debug(" [clang_complete_file]:[current]: '%s'", flags_file_path)

        flags = None
        flags_file_path_same = (flags_file_path == cached_flags_path)
        flags_file_same = File.is_unchanged(cached_flags_path)
        if flags_file_path_same and flags_file_same:
            log.debug(" [clang_complete_file]:[unchanged]: load cached")
            flags = FlagsFile.cache[cached_flags_path]
        else:
            log.debug(" [clang_complete_file]:[changed]: load new")
            if cached_flags_path and cached_flags_path in FlagsFile.cache:
                del FlagsFile.cache[cached_flags_path]
            if not flags_file_path:
                return None
            flags = self.__flags_from_clang_file(File(flags_file_path))
            FlagsFile.cache[cached_flags_path] = flags
            if file_path:
                FlagsFile.path_for_file[file_path] = flags_file_path
        # now we return whatever we have
        return flags

    def __flags_from_clang_file(self, file):
        """Get flags from .clang_complete file.

        Args:
            file (File): A file objects that represents the file to parse.

        Returns:
            str[]: List of flags from file.
        """
        if not path.exists(file.full_path()):
            log.debug(" .clang_complete does not exist yet. No flags present.")
            return []
        if not file.loaded():
            log.error(" cannot get flags from clang_complete_file. No file.")
            return []

        flags = []
        with open(file.full_path()) as f:
            content = f.readlines()
            flags = self._parse_flags(file.folder(), content)
        log.debug(" .clang_complete contains flags: %s", flags)
        return flags
