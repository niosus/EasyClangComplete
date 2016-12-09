"""Stores a class that manages compilation database flags.

Attributes:
    log (logging.Logger): current logger.
"""
from .flags_source import FlagsSource
from ..tools import File
from ..tools import singleton
from ..utils.unique_list import UniqueList

from os import path

import logging

log = logging.getLogger(__name__)


@singleton
class ComplationDbCache(dict):
    """Singleton for compilation database cache."""
    pass


class CompilationDb(FlagsSource):
    """Manages flags parsing from a compilation database.

    Attributes:
        _cache (dict): Cache of all parsed databases to date. Stored by full
            database path. Needed to avoid reparsing same database.
    """
    _FILE_NAME = "compile_commands.json"

    def __init__(self, include_prefixes):
        """Initialize a compilation database.

        Args:
            include_prefixes (str[]): A List of valid include prefixes.
        """
        super().__init__(include_prefixes)
        self._cache = ComplationDbCache()

    def get_flags(self, file_path=None, search_scope=None):
        """Get flags for file.

        Args:
            file_path (str, optional): A path to the query file. This function
                returns a list of flags for this specific file.
            search_scope (SearchScope, optional): Where to search for a
                compile_commands.json file.

        Returns: str[]: Return a list of flags for a file. If no file is
            given, return a list of all unique flags in this compilation
            database
        """
        # prepare search scope
        search_scope = self._update_search_scope(search_scope, file_path)
        # make sure the file name conforms to standard
        file_path = File.canonical_path(file_path)
        # remove extension from a file
        if file_path:
            # strip the file path from extension.
            file_path = path.splitext(file_path)[0]
        # initialize search scope if not initialized before
        # check if we have a hashed version
        log.debug(" [db]:[get]: for file %s", file_path)
        cached_db_path = self._get_cached_from(file_path)
        log.debug(" [db]:[cached]: '%s'", cached_db_path)
        current_db_path = self._find_current_in(search_scope)
        log.debug(" [db]:[current]: '%s'", current_db_path)
        db = None
        parsed_before = current_db_path in self._cache
        if parsed_before:
            log.debug(" [db]: found cached compile_commands.json")
            cached_db_path = current_db_path
        db_path_unchanged = (current_db_path == cached_db_path)
        db_is_unchanged = File.is_unchanged(cached_db_path)
        if db_path_unchanged and db_is_unchanged:
            log.debug(" [db]:[load cached]")
            db = self._cache[cached_db_path]
        else:
            log.debug(" [db]:[load new]")
            # clear old value, parse db and set new value
            if not current_db_path:
                log.debug(" [db]:[no new]: return None")
                return None
            if cached_db_path and cached_db_path in self._cache:
                del self._cache[cached_db_path]
            db = self._parse_database(File(current_db_path))
            log.debug(" [db]: put into cache: '%s'", current_db_path)
            self._cache[current_db_path] = db
        # return nothing if we failed to load the db
        if not db:
            log.debug(" [db]: not found, return None.")
            return None
        if file_path and file_path in db:
            self._cache[file_path] = current_db_path
            File.update_mod_time(current_db_path)
            return db[file_path]
        log.debug(" [db]: return entry for 'all'.")
        return db['all']

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
            file_path = File.canonical_path(entry['file'],
                                            database_file.folder())
            file_path = path.splitext(file_path)[0]
            command_as_list = CompilationDb.line_as_list(entry['command'])
            flags = FlagsSource.parse_flags(database_file.folder(),
                                            command_as_list,
                                            self._include_prefixes)
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
