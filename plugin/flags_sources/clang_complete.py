from .flags_source import FlagsSource
from ..tools import File

from os import path

import logging

log = logging.getLogger(__name__)


class ClangComplete(FlagsSource):
    _FILE_NAME = ".clang_complete"

    def __init__(self, view, include_prefixes, search_scope):
        super(ClangComplete, self).__init__(view, include_prefixes)
        self.__clang_complete_file = File()
        self.__search_scope = search_scope

    def get_flags(self):
        if not self.__clang_complete_file.loaded():
            log.debug(" .clang_complete not loaded. Searching for one...")
            self.__clang_complete_file = File.search(
                file_name=ClangComplete._FILE_NAME,
                from_folder=self.__search_scope.from_folder,
                to_folder=self.__search_scope.to_folder)

        if self._clang_complete_file.was_modified():
            log.debug(" .clang_complete modified. Load new flags.")
            self._flags = self.__flags_from_clang_file()
        return self._flags

    def __flags_from_clang_file(self):
        file = self.__clang_complete_file
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
