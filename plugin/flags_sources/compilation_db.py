"""Stores a class that manages compilation database flags.

Attributes:
    log (logging.Logger): current logger.
"""
from .flags_source import FlagsSource
from ..utils.file import File
from ..utils.unique_list import UniqueList
from ..utils.singleton import ComplationDbCache
from ..utils.flag import Flag

from os import path
from fnmatch import fnmatch
from threading import Lock

import logging

log = logging.getLogger("ECC")


class CompilationDb(FlagsSource):
    """Manages flags parsing from a compilation database.

    In this class cache serves 2 purposes.
    - It stores a reference from a database file full path to a dictionary that
      represents a compilation database.
    - It is used as a reverse index to search for a compilation database name
      given a source file name.

    Attributes:
        _cache (dict): Cache of all parsed databases to date. Stored by full
            database path. Needed to avoid reparsing same database.
    """
    ALL_TAG = 'all'

    _FILE_NAME = "compile_commands.json"
    _LOCK = Lock()

    def __init__(self,
                 include_prefixes,
                 header_to_source_map,
                 lazy_flag_parsing):
        """Initialize a compilation database.

        Args:
            include_prefixes (str[]): A List of valid include prefixes.
            header_to_source_map (str[]): Templates to map header to sources.
            lazy_flag_parsing (bool): If true parse flags later than loading.
        """
        super().__init__(include_prefixes)
        self._cache = ComplationDbCache()
        self._header_to_source_map = header_to_source_map
        self._lazy_flag_parsing = lazy_flag_parsing

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
        file_path = File.canonical_path(file_path)
        current_db_path = self._get_db_path(file_path, search_scope)
        if not current_db_path:
            return None
        db = self._load_current_db(current_db_path)
        if not db:
            log.debug("Compilation db not found.")
            return None
        # If the file is not in the DB, try to find a related file:
        if file_path and file_path not in db:
            log.debug("Searching for related files in db.")
            related_file_path = self._find_related_sources(file_path, db)
            if related_file_path:
                db[file_path] = db[related_file_path]
                file_path = related_file_path
        # If there are any flags in the DB (directly or via a related file),
        # retrieve them:
        if file_path and file_path in db:
            self._cache[file_path] = current_db_path
            File.update_mod_time(current_db_path)
            if self._lazy_flag_parsing and isinstance(db[file_path], dict):
                # We only need to parse the entry if we have lazy parsing
                # enabled and we haven't parsed it before.
                list_of_flags = self._parse_entry(
                    db[file_path],
                    path.dirname(current_db_path))
                db[file_path] = list_of_flags  # Store parsed flags.
                self._cache[current_db_path] = db  # Update db in cache.
                return list_of_flags
            else:
                return db[file_path]
        if CompilationDb.ALL_TAG in db:
            log.debug("Return 'all' entry of the compilation db.")
            return db[CompilationDb.ALL_TAG]
        log.debug("No flags in compilation db for file: '%s'.", file_path)
        return None

    def _get_db_path(self, file_path, search_scope):
        search_scope = self._update_search_scope_if_needed(search_scope,
                                                           file_path)
        current_db_file = File.search(self._FILE_NAME, search_scope)
        if not current_db_file:
            return None
        current_db_path = current_db_file.full_path
        log.debug("Current compilation db path: '%s'", current_db_path)
        return current_db_path

    def _load_current_db(self, current_db_path):
        db_is_unchanged = File.is_unchanged(current_db_path)
        db = None
        if db_is_unchanged and current_db_path in self._cache:
            log.debug("Loading cached compilation db.")
            db = self._cache[current_db_path]
        else:
            log.debug("Loading new compilation db.")
            db = self._parse_database(current_db_path)
            log.debug("Putting new db into cache: '%s'", current_db_path)
            self._cache[current_db_path] = db
        return db

    def _parse_entry(self, entry, base_path):
        argument_list = []
        if 'directory' in entry:
            base_path = path.realpath(entry['directory'])
        if 'command' in entry:
            import shlex
            argument_list = shlex.split(entry['command'])
        elif 'arguments' in entry:
            argument_list = entry['arguments']
        else:
            # TODO(igor): maybe show message to the user instead here
            log.critical("Compilation database has unsupported format")
            return None
        return Flag.tokenize_list(argument_list, base_path)

    def _parse_database(self, current_db_path):
        """Parse a compilation database file.

        Args:
            current_db_path (File): a path representing a database.

        Returns: dict: A dict that stores a list of flags per view and all
            unique entries for CompilationDb.ALL_TAG entry.
        """
        import yaml
        data = None
        with open(current_db_path) as data_file:
            # We load our json file with yaml to allow for trailing commas.
            data = yaml.load(data_file, Loader=yaml.FullLoader)
        if not data:
            return None
        parsed_db = {}
        base_path = path.dirname(current_db_path)
        unique_list_of_flags = UniqueList()
        for entry in data:
            if 'directory' in entry:
                base_path = entry['directory']
            file_path = File.canonical_path(entry['file'], base_path)
            if self._lazy_flag_parsing:
                parsed_db[file_path] = entry
            else:
                flags = self._parse_entry(entry, base_path)
                # set these flags for current file
                parsed_db[file_path] = flags
                # also maintain merged flags
                unique_list_of_flags += flags
        if not self._lazy_flag_parsing:
            # We have all flags parsed, so we can set a fallback db entry.
            parsed_db[CompilationDb.ALL_TAG] = unique_list_of_flags.as_list()
        return parsed_db

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
