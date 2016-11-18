from .flags_source import FlagsSource
from ..tools import File

from os import path

import logging

log = logging.getLogger(__name__)


class FlagsFile(FlagsSource):
    _FILE_NAME = ".clang_complete"

    cache = {}
    path_for_file = {}

    def __init__(self, include_prefixes, search_scope):
        super(FlagsFile, self).__init__(include_prefixes)
        self.__search_scope = search_scope

    def get_flags(self, file_path=None):
        log.debug(" [clang_complete_file]: for file %s", file_path)
        cached_file_path = FlagsFile.get_cached_from(file_path)
        log.debug(" [clang_complete_file]:[cached]: '%s'", cached_file_path)
        current_file_path = FlagsFile.find_current_in(
            self.__search_scope)
        log.debug(" [clang_complete_file]:[current]: '%s'", current_file_path)

        flags = None
        flags_file_path_same = (current_file_path == cached_file_path)
        flags_file_same = File.is_unchanged(cached_file_path)
        if flags_file_path_same and flags_file_same:
            log.debug(" [clang_complete_file]:[unchanged]: load cached")
            flags = FlagsFile.cache[cached_file_path]
        else:
            log.debug(" [clang_complete_file]:[changed]: load new")
            if cached_file_path and cached_file_path in FlagsFile.cache:
                del FlagsFile.cache[cached_file_path]
            if not current_file_path:
                return None
            flags = self.__flags_from_clang_file(File(current_file_path))
            FlagsFile.cache[cached_file_path] = flags
        # now we return whatever we have
        return flags

    @classmethod
    def get_cached_from(cls, file_path):
        """Get cached path for file path.

        Args:
            file_path (str): Input file path.

        Returns:
            str: Path to the cached flag source path.
        """
        if file_path and file_path in cls.path_for_file:
            return cls.path_for_file[file_path]
        return None

    @classmethod
    def find_current_in(cls, search_scope):
        """Find current path in a search scope.

        Args:
            search_scope (SearchScope): Find in a search scope.

        Returns:
            str: Path to the current flag source path.
        """
        return File.search(
            file_name=cls._FILE_NAME,
            from_folder=search_scope.from_folder,
            to_folder=search_scope.to_folder).full_path()

    def __flags_from_clang_file(self, file):
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
