from .flags_source import FlagsSource
from ..tools import File
from ..utils.unique_list import UniqueList

from os import path

import logging

log = logging.getLogger(__name__)


class CompilationDb(FlagsSource):
    _FILE_NAME = "compile_commands.json"

    cache = {}
    path_for_file = {}

    def __init__(self, include_prefixes, search_scope):
        super(CompilationDb, self).__init__(include_prefixes)
        self.__search_scope = search_scope

    def get_flags(self, file_path=None):
        cached_db_path = None
        log.debug(" [db: get]: for file %s", file_path)
        if file_path and file_path in CompilationDb.path_for_file:
            cached_db_path = CompilationDb.path_for_file[file_path]
            log.debug(" [db: cached]: '%s'", cached_db_path)
        current_db_path = File.search(
            file_name=CompilationDb._FILE_NAME,
            from_folder=self.__search_scope.from_folder,
            to_folder=self.__search_scope.to_folder).full_path()
        log.debug(" [db: current]: '%s'", current_db_path)
        db = None
        db_path_unchanged = (current_db_path == cached_db_path)
        db_is_unchanged = File.is_unchanged(cached_db_path)
        if db_path_unchanged and db_is_unchanged:
            log.debug(" [db: load cached]")
            db = CompilationDb.cache[cached_db_path]
        else:
            log.debug(" [db: load new]")
            # clear old value, parse db and set new value
            if cached_db_path and cached_db_path in CompilationDb.cache:
                del CompilationDb.cache[cached_db_path]
            db = self._parse_database(File(current_db_path))
            CompilationDb.cache[current_db_path] = db

        if file_path:
            CompilationDb.path_for_file[file_path] = current_db_path
            return db[file_path]
        return db['all']

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
            file_path = path.normpath(entry['file'])
            command_as_list = CompilationDb.line_as_list(entry['command'])
            flags = self._parse_flags(database_file.folder(), command_as_list)
            # set these flags for current file
            parsed_db[file_path] = flags
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