from .flags_source import CompilationDb
from ..tools import File
from ..tools import Tools

from os import path

import subprocess
import logging

log = logging.getLogger(__name__)


class CMake(CompilationDb):
    _FILE_NAME = '.clang_complete'
    _CMAKE_MASK = 'cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON "{path}"'

    def __init__(self, view, include_prefixes, search_scope):
        super(CMake, self).__init__(view, include_prefixes, search_scope)
        self.__cmake_lists_file = File()
        self.__search_scope = search_scope

    def as_list(self):
        if not self.__cmake_lists_file.loaded():
            # CMakeLists.txt was not loaded yet, so search for it
            log.debug(" cmake file not loaded yet. Searching for one...")
            self.__cmake_lists_file = File.search(
                file_name=CMake._FILE_NAME,
                from_folder=self.__search_scope.from_folder,
                to_folder=self.__search_scope.to_folder,
                search_content="project")

        if self._use_cmake and self.__cmake_lists_file.was_modified():
            # generate a .clang_complete file from cmake file if cmake file
            # exists and was modified
            log.debug(" CMakeLists.txt was modified."
                      " Generate new .clang_complete")
            compilation_db = CMake.__compile_cmake(
                cmake_file=self.__cmake_lists_file,
                prefix_paths=self._cmake_prefix_paths)
            if compilation_db:
                self._flags = super(CompilationDbFlags,
                                    self)._flags_from_database(compilation_db)
            else:
                self._flags = []
        return self._flags

    @staticmethod
    def __compile_cmake(cmake_file, prefix_paths):
        """
        Compile cmake given a CMakeLists.txt file and get a new compilation
        database path to further parse the generated flags. The build is
        performed in a temporary folder with a unique folder name for the
        project being built - a hex number generated from the pull path to
        current CMakeListst.txt file.

        Args:
            cmake_file (tools.file): file object for CMakeLists.txt file
            prefix_paths (str[]): paths to add to CMAKE_PREFIX_PATH before
            running `cmake`
        """
        import os
        import shutil
        cmake_cmd = CMake._CMAKE_MASK.format(path=cmake_file.folder())
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

        database_path = path.join(tempdir, CompilationDbFlags._FILE_NAME)
        if not path.exists(database_path):
            log.error(" cmake has finished, but no compilation database.")
            return None
        return File(database_path)
