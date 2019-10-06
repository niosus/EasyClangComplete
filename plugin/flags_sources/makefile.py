"""Stores a class that manages flags loading from Makefiles.

Attributes:
    log (logging.Logger): current logger.
"""
from os import path
import subprocess
import shlex
import logging

from .flags_source import FlagsSource
from ..utils.file import File
from ..utils.singleton import MakefileCache
from ..utils.flag import Flag

log = logging.getLogger("ECC")


class Makefile(FlagsSource):
    """Manages flags parsing from Makefiles.

    Attributes:
        cache (dict): Cache of all parsed files to date. Stored by full file
            path. Needed to avoid reparsing the file multiple times.
    """
    _FILE_NAME = "Makefile"

    def __init__(self, include_prefixes):
        """Initialize a flag file storage.

        Args:
            include_prefixes (str[]): A List of valid include prefixes.
        """
        super().__init__(include_prefixes)
        self._cache = MakefileCache()

    def get_flags(self, file_path=None, search_scope=None):
        """Get flags for file.

        Args:
            file_path (None, optional): A path to the query file.
            search_scope (SearchScope, optional): Where to search for a
                Makefile

        Returns:
            str[]: Return a list of flags in this Makefile
        """
        search_scope = self._update_search_scope_if_needed(
            search_scope, file_path)
        log.debug("[Makefile]:[get]: for file %s", file_path)
        makefile = File.search(self._FILE_NAME, search_scope)
        if not makefile:
            return None
        makefile_path = makefile.full_path
        log.debug("[Makefile]:[current]: '%s'", makefile_path)
        if not makefile_path:
            return None
        cached_makefile_path = self._get_cached_from(file_path)
        log.debug("[Makefile]:[cached]: '%s'", cached_makefile_path)

        if makefile_path in self._cache:
            log.debug("[Makefile]: found cached Makefile")
            cached_makefile_path = makefile_path
            if makefile_path == cached_makefile_path:
                if File.is_unchanged(cached_makefile_path):
                    log.debug("[Makefile]:[unchanged]: load cached")
                    return self._cache[cached_makefile_path]
        log.debug("[Makefile]:[changed]: load new")
        if cached_makefile_path and cached_makefile_path in self._cache:
            del self._cache[cached_makefile_path]
        flags = self.__flags_from_makefile(File(makefile_path))
        if flags:
            self._cache[makefile_path] = flags
        if file_path:
            self._cache[file_path] = makefile_path
        return flags

    def __flags_from_makefile(self, file):
        """Get flags from Makefile.

        Args:
            file (File): A file objects that represents the file to parse.

        Returns:
            str[]: List of flags from Makefile.
        """
        if not path.exists(file.full_path) or not file.loaded():
            log.error("cannot get flags from Makefile. No file.")
            return []

        cmd = [
            "make", "-s", "-C", file.folder,
            "-f", self._FILE_NAME, "-f", "-",
        ]
        makevars = [
            "DEFAULT_INCLUDES",
            "INCLUDES",
            "AM_CPPFLAGS",
            "CPPFLAGS",
            "AM_CFLAGS",
            "CFLAGS",
        ]
        for makevar in makevars:
            cmd.append("print-" + makevar)
        pipe = subprocess.PIPE
        make = subprocess.Popen(cmd, stdout=pipe, stdin=pipe, stderr=pipe)
        printer = "print-%:\n\t@echo '$($*)'\n".encode("utf-8")
        output = make.communicate(input=printer)[0].decode("utf-8")
        tokens = []
        for line in output.split("\n"):
            if line:
                tokens += shlex.split(line)
        return Flag.tokenize_list(tokens, file.folder)
