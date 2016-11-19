"""Stores a class that manages flags generation using cmake.

Attributes:
    log (TYPE): Description
"""
from .compilation_db import CompilationDb
from ..tools import File
from ..tools import Tools
from ..tools import SearchScope

from os import path

import subprocess
import logging

log = logging.getLogger(__name__)


class CMakeFile(CompilationDb):
    """Manages generating a compilation database with cmake.

    Attributes:
        cache (dict): Cache of all parsed cmake files to date.
        path_for_file (dict): A path to a database for every source file path.
    """
    _FILE_NAME = 'CMakeLists.txt'
    _CMAKE_MASK = 'cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON "{path}"'

    cache = {}
    path_for_file = {}

    def __init__(self, include_prefixes, search_scope, prefix_paths):
        """Initialize a cmake-based flag storage.

        Args:
            include_prefixes (str[]): A List of valid include prefixes.
            search_scope (SearchScope): Where to search for a CMakeLists.txt.
            prefix_paths (str[]): A list of paths to append to
                CMAKE_PREFIX_PATH before invoking cmake.
        """
        super().__init__(include_prefixes, search_scope)
        self.__search_scope = search_scope
        self.__cmake_prefix_paths = prefix_paths

    def get_flags(self, file_path=None):
        """Get flags for file.

        Args:
            file_path (None, optional): A path to the query file. This
                function returns a list of flags for this specific file.

        Returns:
            str[]: List of flags for this view, or all flags merged if this
                view path is not found in the generated compilation db.
        """
        log.debug(" [cmake: get]: for file %s", file_path)
        cached_cmake_path = super().get_cached_from(file_path)
        log.debug(" [cmake]:[cached]: '%s'", cached_cmake_path)
        current_cmake_path = super().find_current_in(self.__search_scope)
        log.debug(" [cmake]:[current]: '%s'", current_cmake_path)

        cmake_path_unchanged = (current_cmake_path == cached_cmake_path)
        cmake_file_unchanged = File.is_unchanged(cached_cmake_path)
        if cmake_path_unchanged and cmake_file_unchanged:
            log.debug(" [cmake: unchanged]: search for db")
            db_path = CompilationDb.find_current_in(
                SearchScope(from_folder=path.dirname(cached_cmake_path)))
            return super().get_flags(file_path, db_path)
        else:
            log.debug(" [cmake: generate new db]")
            db_file = CMakeFile.__compile_cmake(
                cmake_file=File(current_cmake_path),
                prefix_paths=self.__cmake_prefix_paths)
            if not db_file:
                return None
            db_path = db_file.full_path()
            return super().get_flags(file_path, db_path)
        return None

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
