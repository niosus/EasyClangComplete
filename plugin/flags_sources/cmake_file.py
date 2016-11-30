"""Stores a class that manages flags generation using cmake.

Attributes:
    log (logging.Log): Current logger.
"""
from .flags_source import FlagsSource
from .compilation_db import CompilationDb
from ..tools import File
from ..tools import Tools
from ..tools import SearchScope
from ..tools import singleton

from os import path

import subprocess
import logging

log = logging.getLogger(__name__)


@singleton
class CMakeFileCache(dict):
    """Singleton for CMakeLists.txt file cache."""
    pass


class CMakeFile(FlagsSource):
    """Manages generating a compilation database with cmake.

    Attributes:
        cache (dict): Cache of database filenames for each analyzed
            CMakeLists.txt file and of CMakeLists.txt file paths for each
            analyzed view path.
    """
    _FILE_NAME = 'CMakeLists.txt'
    _CMAKE_MASK = 'cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON "{path}"'

    def __init__(self, include_prefixes, prefix_paths):
        """Initialize a cmake-based flag storage.

        Args:
            include_prefixes (str[]): A List of valid include prefixes.
            prefix_paths (str[]): A list of paths to append to
                CMAKE_PREFIX_PATH before invoking cmake.
        """
        super().__init__(include_prefixes)
        self._cache = CMakeFileCache()
        self.__cmake_prefix_paths = prefix_paths

    def get_flags(self, file_path=None, search_scope=None):
        """Get flags for file.

        Args:
            file_path (None, optional): A path to the query file. This
                function returns a list of flags for this specific file.
            search_scope (SearchScope, optional): Where to search for a
                CMakeLists.txt file.

        Returns:
            str[]: List of flags for this view, or all flags merged if this
                view path is not found in the generated compilation db.
        """
        # initialize search scope if not initialized before
        if not search_scope:
            search_scope = SearchScope(from_folder=path.dirname(file_path))
        # check if we have a hashed version TODO(igor): probably can be
        # simplified. Why do we need to load chached? should we just test if
        # currently found one is in cache?
        log.debug(" [cmake]:[get]: for file %s", file_path)
        cached_cmake_path = self._get_cached_from(file_path)
        log.debug(" [cmake]:[cached]: '%s'", cached_cmake_path)
        current_cmake_path = self._find_current_in(search_scope, 'project')
        log.debug(" [cmake]:[current]: '%s'", current_cmake_path)

        parsed_before = current_cmake_path in self._cache
        if parsed_before:
            log.debug(" [cmake]: found cached CMakeLists.txt.")
            cached_cmake_path = current_cmake_path
            # remember that for this file we have found this cmakelists
            self._cache[file_path] = current_cmake_path
        path_unchanged = (current_cmake_path == cached_cmake_path)
        file_unchanged = File.is_unchanged(cached_cmake_path)
        if path_unchanged and file_unchanged:
            log.debug(" [cmake]:[unchanged]: use existing db.")
            if cached_cmake_path in self._cache:
                db_file_path = self._cache[cached_cmake_path]
                db = CompilationDb(self._include_prefixes)
                db_search_scope = SearchScope(
                    from_folder=path.dirname(db_file_path))
                return db.get_flags(file_path, db_search_scope)

        log.debug(" [cmake]:[generate new db]")
        db_file = CMakeFile.__compile_cmake(
            cmake_file=File(current_cmake_path),
            prefix_paths=self.__cmake_prefix_paths)
        if not db_file:
            return None
        if file_path:
            # write the current cmake file to cache
            self._cache[file_path] = current_cmake_path
            self._cache[current_cmake_path] = db_file.full_path()
            File.update_mod_time(current_cmake_path)
        db = CompilationDb(self._include_prefixes)
        db_search_scope = SearchScope(from_folder=db_file.folder())
        flags = db.get_flags(file_path, db_search_scope)
        return flags

    @staticmethod
    def __compile_cmake(cmake_file, prefix_paths):
        """Compile cmake given a CMakeLists.txt file.

        This returns  a new compilation database path to further parse the
        generated flags. The build is performed in a temporary folder with a
        unique folder name for the project being built - a hex number
        generated from the pull path to current CMakeListst.txt file.

        Args:
            cmake_file (tools.file): file object for CMakeLists.txt file
            prefix_paths (str[]): paths to add to CMAKE_PREFIX_PATH before
            running `cmake`
        """
        if not cmake_file or not cmake_file.loaded():
            return None

        import os
        import shutil
        cmake_cmd = CMakeFile._CMAKE_MASK.format(path=cmake_file.folder())
        unique_proj_str = Tools.get_unique_str(cmake_file.full_path())
        tempdir = path.join(
            Tools.get_temp_dir(), 'cmake_builds', unique_proj_str)
        # ensure a clean build
        shutil.rmtree(tempdir, ignore_errors=True)
        os.makedirs(tempdir)
        try:
            # sometimes there are variables missing to carry out the build. We
            # can set them here from the settings.
            my_env = os.environ.copy()
            my_env['CMAKE_PREFIX_PATH'] = ":".join(prefix_paths)
            log.info(' running command: %s', cmake_cmd)
            output = subprocess.check_output(cmake_cmd,
                                             stderr=subprocess.STDOUT,
                                             shell=True,
                                             cwd=tempdir,
                                             env=my_env)
            output_text = ''.join(map(chr, output))
        except subprocess.CalledProcessError as e:
            output_text = e.output.decode("utf-8")
            log.info(" cmake process finished with code: %s", e.returncode)
        log.info(" cmake produced output: \n%s", output_text)

        database_path = path.join(tempdir, CompilationDb._FILE_NAME)
        if not path.exists(database_path):
            log.error(" cmake has finished, but no compilation database.")
            return None
        return File(database_path)
