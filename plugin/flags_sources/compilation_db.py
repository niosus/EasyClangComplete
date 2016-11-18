"""Stores a class that manages compilation database flags.

Attributes:
    log (logging.Logger): current logger.
"""
from .flags_source import FlagsSource
from ..tools import File
from ..utils.unique_list import UniqueList

from os import path

import logging

log = logging.getLogger(__name__)


class CompilationDb(FlagsSource):
    """Manages flags parsing from a compilation database.

    Attributes:
        cache (dict): Cache of all parsed databases to date. Stored by full
            database path. Needed to avoid reparsing same database.
        path_for_file (dict): A path to a database for every source file path.
            Needed for finding a corresponding database path for a view.
    """
    _FILE_NAME = "compile_commands.json"

    cache = {}
    path_for_file = {}

    def __init__(self, include_prefixes, search_scope):
        """Initialize a compilation database.

        Args:
            include_prefixes (str[]): A List of valid include prefixes.
            search_scope (SearchScope): Where to search for a database file.
        """
        super(CompilationDb, self).__init__(include_prefixes)
        self.__search_scope = search_scope

    def get_flags(self, file_path=None, current_db_path=None):
        """Get flags for file.

        Args:
            file_path (str, optional): A path to the query file. This function
                returns a list of flags for this specific file.

        Returns: str[]: Return a list of flags for a file. If no file is
            given, return a list of all unique flags in this compilation
            database
        """
        log.debug(" [db: get]: for file %s", file_path)
        cached_db_path = CompilationDb.get_cached_from(file_path)
        log.debug(" [db: cached]: '%s'", cached_db_path)
        if not current_db_path:
            current_db_path = CompilationDb.find_current_in(
                self.__search_scope)
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
            if not current_db_path:
                return None
            db = self._parse_database(File(current_db_path))
            CompilationDb.cache[current_db_path] = db
        # return nothing if we failed to load the db
        if not db:
            return None
        # TODO(igor): probably strip file_path from extension.
        if file_path and file_path in db:
            CompilationDb.path_for_file[file_path] = current_db_path
            return db[file_path]
        return db['all']

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

    def _parse_database(self, database_file):
        """Parse a compilation database file.

        Args:
            database_file (File): a file representing a database.

        Returns: dict: A dict that stores a list of flags per view and all
            unique entries for 'all' entry.
        """
        import json
        data = None
        with open(database_file.full_path()) as data_file:
            data = json.load(data_file)
        if not data:
            return None

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
        """Represent line as a list of flags.

        Args:
            line (str): a line from database file.

        Returns:
            str[]: A line parsed with shlex.
        """
        import shlex
        # first argument is always a command, like c++
        # last 4 entries are always object and filename
        # between them there are valuable flags
        return shlex.split(line)[1:-4]
