from .flags_source import FlagsSource
from ..tools import File
from ..utils.unique_list import UniqueList

import logging

log = logging.getLogger(__name__)


class CompilationDb(FlagsSource):
    _FILE_NAME = "compile_commands.json"

    def __init__(self, include_prefixes, search_scope):
        super(CompilationDb, self).__init__(include_prefixes)
        self.__compilation_db_file = File()
        self.__search_scope = search_scope
        # we treat flags as dictionary
        self._flags = {}

    def get_flags(self, file_name=None):
        if not self.__compilation_db_file.loaded():
            log.debug(" .clang_complete not loaded. Searching for one...")
            self.__compilation_db_file = File.search(
                file_name=CompilationDb._FILE_NAME,
                from_folder=self.__search_scope.from_folder,
                to_folder=self.__search_scope.to_folder)

        if self.__compilation_db_file.was_modified() or not self._flags:
            log.debug(" .clang_complete modified. Load new flags.")
            self._flags = self._parse_database(self.__compilation_db_file)
        if file_name:
            return self._flags[file_name]
        return self._flags['all']

    def _parse_database(self, database_file):
        import json
        data = None
        with open(database_file.full_path()) as data_file:
            data = json.load(data_file)
        if not data:
            return []

        parsed_db = {}
        unique_list_of_flags = UniqueList()
        for entry in data:
            file_name = entry['file']
            command_as_list = CompilationDb.line_as_list(entry['command'])
            flags = self._parse_flags(database_file.folder(), command_as_list)
            # set these flags for current file
            parsed_db[file_name] = flags
            # also maintain merged flags
            unique_list_of_flags += flags
        # set an entry for merged flags
        parsed_db['all'] = unique_list_of_flags.as_list()
        # return parsed_db
        return parsed_db

    @staticmethod
    def line_as_list(line):
        import shlex
        # first argument is always a command, like c++
        # last 4 entries are always object and filename
        # between them there are valuable flags
        return shlex.split(line)[1:-4]

class CompilationDbCache(object):
    flags_per_file = {}
