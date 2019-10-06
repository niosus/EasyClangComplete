"""Stores a class that manages flags generation using cpp_properies.

see https://blogs.msdn.microsoft.com/vcblog/2017/11/02/customizing-your-environment-with-visual-c-and-open-folder/ # noqa

Attributes:
    log (logging.Log): Current logger.
"""
from .flags_source import FlagsSource
from ..utils.file import File
from ..utils.singleton import CppPropertiesCache
from ..utils.flag import Flag

import os
import re
import logging

log = logging.getLogger("ECC")


class CppProperties(FlagsSource):
    """Manages flags parsing from CppProperties.json file.

    Attributes:
        cache (dict): Cache of all parsed files to date. Stored by full file
            path. Needed to avoid reparsing the file multiple times.
        path_for_file (dict): A path to a database for every source file path.
    """
    _FILE_NAME = "CppProperties.json"

    def __init__(self, include_prefixes):
        """Initialize a flag file storage.

        Args:
            include_prefixes (str[]): A List of valid include prefixes.
        """
        super().__init__(include_prefixes)
        self._cache = CppPropertiesCache()

    def get_flags(self, file_path=None, search_scope=None):
        """Get flags for file.

        Args:
            file_path (None, optional): A path to the query file.
            search_scope (SearchScope, optional): c_ to search for a
                CppProperties.json file.

        Returns:
            str[]: Return a list of flags in this CppProperties.json file
        """
        # prepare search scope
        search_scope = self._update_search_scope_if_needed(
            search_scope, file_path)
        # check if we have a hashed version
        log.debug("[CppProperties]:[get]: for file %s", file_path)
        cached_flags_path = self._get_cached_from(file_path)
        log.debug("[CppProperties]:[cached]: '%s'", cached_flags_path)
        flags_file = File.search(self._FILE_NAME, search_scope)
        if not flags_file:
            return None
        flags_file_path = flags_file.full_path
        log.debug("[CppProperties]:[current]: '%s'", flags_file_path)
        if not flags_file_path:
            return None

        flags = None
        parsed_before = flags_file_path in self._cache
        if parsed_before:
            log.debug("[CppProperties]: found cached CppProperties.json")
            cached_flags_path = flags_file_path
        flags_file_path_same = (flags_file_path == cached_flags_path)
        flags_file_same = File.is_unchanged(cached_flags_path)
        if flags_file_path_same and flags_file_same:
            log.debug("[CppProperties]:[unchanged]: load cached")
            return self._cache[cached_flags_path]
        log.debug("[CppProperties]:[changed]: load new")
        if cached_flags_path and cached_flags_path in self._cache:
            del self._cache[cached_flags_path]
        flags = self.__flags_from_cpp_properties_file(File(flags_file_path))
        if flags:
            self._cache[cached_flags_path] = flags
        if file_path:
            self._cache[file_path] = flags_file_path
        # now we return whatever we have
        return flags

    def __flags_from_cpp_properties_file(self, file):
        """Get flags from cpp properties file.

        Args:
            file (File): A file objects that represents the file to parse.

        Returns:
            str[]: List of flags from file.
        """
        def expand_env_vars(paths):
            expandable_path = re.sub(r'\$\{env\.', '${', paths)
            return os.path.expandvars(expandable_path)

        def parse_includes_from_json(content):
            try:
                include_paths = content["configurations"][0]["includePath"]
            except Exception:
                include_paths = []
            includes = [expand_env_vars(i) for i in include_paths]
            includes = ["-I{}".format(include) for include in includes]
            return includes

        def parse_defines_from_json(content):
            try:
                defines = content["configurations"][0]["defines"]
            except Exception:
                defines = []
            defines = ["-D{}".format(define) for define in defines]
            return defines

        if not os.path.exists(file.full_path):
            log.error("File '%s' does not exist yet. No flags present.",
                      CppProperties._FILE_NAME)
            return []
        if not file.loaded():
            log.error("cannot get flags from %s. No file.",
                      CppProperties._FILE_NAME)
            return []

        import json
        flags = []
        with open(file.full_path) as f:
            content = json.load(f)
            includes = parse_includes_from_json(content)
            defines = parse_defines_from_json(content)

            content = includes + defines
            flags = Flag.tokenize_list(content, file.folder)
        return flags
