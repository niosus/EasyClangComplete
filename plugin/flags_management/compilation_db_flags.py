from .flags import Flags
from ..tools import File
from ..utils import UniqueList

from os import path

import logging

log = logging.getLogger(__name__)


class CompilationDbFlags(Flags):
    _FILE_NAME = "compile_commands.json"

    def __init__(self, view, include_prefixes, search_scope):
        super(CompilationDbFlags, self).__init__(view, include_prefixes)
        self.__compilation_db_file = File()
        self.__search_scope = search_scope

    def as_list(self):
        if not self.__compilation_db_file.loaded():
            log.debug(" .clang_complete not loaded. Searching for one...")
            self.__compilation_db_file = File.search(
                file_name=CompilationDbFlags._FILE_NAME,
                from_folder=self.__search_scope.from_folder,
                to_folder=self.__search_scope.to_folder)

        if self.__compilation_db_file.was_modified():
            log.debug(" .clang_complete modified. Load new flags.")
            self._flags = self._flags_from_database(
                self.__compilation_db_file)
        return self._flags

    def _flags_from_database(self, database_file):
        """Get flags from cmake compilation database
        Args: database_file (tools.File): compilation database file
        Returns:
            str[]: flags
        """
        import json
        data = None
        with open(database_file.full_path()) as data_file:
            data = json.load(data_file)
        if not data:
            return []
        uniqie_list = UniqueList()
        # TODO(igor): All the entries will be unique, but still not separated
        # based on the file being compiled.
        for entry in data:
            command = entry['command']
            all_command_parts = command.split(' -')
            all_command_parts = ['-' + part for part in all_command_parts]
            current_flags = self._parse_flags(database_file.folder(),
                                              all_command_parts)
            uniqie_list += current_flags
        log.debug(" flags set: %s", uniqie_list)
        return uniqie_list.as_list()
