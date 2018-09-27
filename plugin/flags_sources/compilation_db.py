"""Stores a class that manages compilation database flags.

Attributes:
    log (logging.Logger): current logger.
"""
from .flags_source import FlagsSource
from ..tools import File
from ..utils.unique_list import UniqueList
from ..utils.singleton import ComplationDbCache

from os import path
from fnmatch import fnmatch

import logging

log = logging.getLogger("ECC")


class CompilationDb(FlagsSource):
    """Manages flags parsing from a compilation database.

    Attributes:
        _cache (dict): Cache of all parsed databases to date. Stored by full
            database path. Needed to avoid reparsing same database.
    """
    _FILE_NAME = "compile_commands.json"

    def __init__(self, include_prefixes,
                 header_to_source_map,
                 use_target_compiler_builtins):
        """Initialize a compilation database.

        Args:
            include_prefixes (str[]): A List of valid include prefixes.
            header_to_source_map (str[]): Templates to map header to sources.
            use_target_compiler_builtins (bool): Retrieve target compiler built
                                                 ins.
        """
        super().__init__(include_prefixes)
        self._cache = ComplationDbCache()
        self._header_to_source_map = header_to_source_map
        self._use_target_compiler_builtins = use_target_compiler_builtins

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
        # initialize search scope if not initialized before
        # check if we have a hashed version
        log.debug("[db]:[get]: for file %s", file_path)
        cached_db_path = self._get_cached_from(file_path)
        log.debug("[db]:[cached]: '%s'", cached_db_path)
        current_db_file = File.search(self._FILE_NAME, search_scope)
        if not current_db_file:
            return None
        current_db_path = current_db_file.full_path
        log.debug("[db]:[current]: '%s'", current_db_path)
        db = None
        parsed_before = current_db_path in self._cache
        if parsed_before:
            log.debug("[db]: found cached compile_commands.json")
            cached_db_path = current_db_path
        db_path_unchanged = (current_db_path == cached_db_path)
        db_is_unchanged = File.is_unchanged(cached_db_path)
        if db_path_unchanged and db_is_unchanged:
            log.debug("[db]:[load cached]")
            db = self._cache[cached_db_path]
        else:
            log.debug("[db]:[load new]")
            # clear old value, parse db and set new value
            if not current_db_path:
                log.debug("[db]:[no new]: return None")
                return None
            if cached_db_path and cached_db_path in self._cache:
                del self._cache[cached_db_path]
            db = self._parse_database(current_db_file)
            log.debug("[db]: put into cache: '%s'", current_db_path)
            self._cache[current_db_path] = db
        # return nothing if we failed to load the db
        if not db:
            log.debug("[db]: not found, return None.")
            return None
        # If the file is not in the DB, try to find a related file:
        if file_path and file_path not in db:
            related_file_path = self._find_related_sources(file_path, db)
            if related_file_path:
                db[file_path] = db[related_file_path]
                file_path = related_file_path
        # If there are any flags in the DB (directly or via a related file),
        # retrieve them:
        if file_path and file_path in db:
            self._cache[file_path] = current_db_path
            File.update_mod_time(current_db_path)
            return db[file_path]
        log.debug("[db]: return entry for 'all'.")
        return db['all']

    def _parse_database(self, database_file):
        """Parse a compilation database file.

        Args:
            database_file (File): a file representing a database.

        Returns: dict: A dict that stores a list of flags per view and all
            unique entries for 'all' entry.
        """
        import json
        from ..utils.compiler_builtins import CompilerBuiltIns

        data = None

        with open(database_file.full_path) as data_file:
            data = json.load(data_file)
        if not data:
            return None

        parsed_db = {}
        unique_list_of_flags = UniqueList()
        for entry in data:
            file_path = File.canonical_path(entry['file'],
                                            database_file.folder)
            argument_list = []

            base_path = database_file.folder
            if 'directory' in entry:
                base_path = entry['directory']

            if 'command' in entry:
                import shlex
                argument_list = shlex.split(entry['command'])
            elif 'arguments' in entry:
                argument_list = entry['arguments']
            else:
                # TODO(igor): maybe show message to the user instead here
                log.critical(" compilation database has unsupported format")
                return None

            # If enabled, try to retrieve default flags for the compiler
            # and language combination:
            if self._use_target_compiler_builtins:
                # Note: Calling the CompilerBuiltIns constructor shells out to
                # calling the compiler; however, for every
                # compiler/standard/language
                # combination, the results are cached by the class internally.
                builtins = CompilerBuiltIns(argument_list, file_path)

                # Append built-in flags to the end of the list:
                # Note: We keep the last argument as last, as it
                # usually is the file name.
                argument_list = (
                    argument_list[:-1] + builtins.flags +
                    argument_list[-1:])

            argument_list = CompilationDb.filter_bad_arguments(argument_list)
            flags = FlagsSource.parse_flags(base_path,
                                            argument_list,
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
    def filter_bad_arguments(argument_list):
        """Filter out the arguments that we don't care about.

        Args:
            argument_list (str[]): a list of flags.

        Returns:
            str[]: Flags without the unneeded ones.
        """
        new_args = []
        skip_next = False
        for i, argument in enumerate(argument_list):
            if skip_next:
                # somebody told us to skip this
                skip_next = False
                continue
            if i == 0:
                # ignore first element as it is always the program to run,
                # something like 'c++'
                continue
            if i == len(argument_list) - 1:
                # ignore the last element as it is a file to compile, something
                # like 'test.cpp'
                continue
            if argument == '-c':
                # ignore -c too
                continue
            if argument == '-o':
                # ignore the -o flag and whatever comes after it
                skip_next = True
                continue
            new_args.append(argument)
        return new_args

    def _find_related_sources(self, file_path, db):
        if not file_path:
            log.debug("[db]:[header-to-source]: skip retrieving related "
                      "files for invalid file_path input")
            return
        templates = self._get_templates()
        log.debug("[db]:[header-to-source]: using lookup table:" +
                  str(templates))

        dirname = path.dirname(file_path)
        basename = path.basename(file_path)
        (stamp, ext) = path.splitext(basename)
        # Search in all templates plus a set of default ones:
        for template in templates:
            log.debug("[db]:[header-to-source]: looking up via %s" % template)
            # Construct a globbing pattern by taking the dirname of the input
            # file and join it with the template part which may contain
            # some pre-defined placeholders:
            pattern = template.format(
                basename=basename,
                stamp=stamp,
                ext=ext
            )
            pattern = path.join(dirname, pattern)
            # Normalize the path, as templates might contain references
            # to parent directories:
            pattern = path.normpath(pattern)
            for key in db:
                if fnmatch(key, pattern):
                    log.debug("[db]:[header-to-source]: found match %s" % key)
                    return key

    def _get_templates(self):
        templates = self._header_to_source_map
        # If we use the plain default (None), make it an empty array
        if templates is None:
            templates = list()
        # Flatten directory entries (i.e. templates which end with a trailing
        # path delimiter):

        result = list()
        for template in templates:
            if template.endswith("/") or template.endswith("\\"):
                result.append(template + "{stamp}.*")
                result.append(template + "*.*")
            else:
                result.append(template)

        # Include default templates:
        default_templates = ["{stamp}.*", "*.*"]
        for default_template in default_templates:
            if default_template not in result:
                result.append(default_template)
        return result
