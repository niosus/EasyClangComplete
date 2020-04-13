"""Stores a class that manages flags generation using cmake.

Attributes:
    log (logging.Log): Current logger.
"""
from .flags_source import FlagsSource
from .compilation_db import CompilationDb
from ..utils.file import File
from ..utils.tools import Tools
from ..utils.singleton import CMakeFileCache
from ..utils.catkinizer import Catkinizer
from ..utils.search_scope import TreeSearchScope
from ..utils.subl.subl_bridge import SublBridge
from ..utils.output_panel_handler import OutputPanelHandler

from os import path

import logging
import re
import os

log = logging.getLogger("ECC")


class CMakeFile(FlagsSource):
    """Manages generating a compilation database with cmake.

    Attributes:
        _cache (dict): Cache of database filenames for each analyzed
            CMakeLists.txt file and of CMakeLists.txt file paths for each
            analyzed view path.
    """
    _FILE_NAME = 'CMakeLists.txt'
    _DEP_REGEX = re.compile(r'\"(.+\..+)\"')
    _CMAKE_PREFIX_PATHS_TAG = 'CMAKE_PREFIX_PATH'

    def __init__(self,
                 include_prefixes,
                 prefix_paths,
                 flags,
                 cmake_binary,
                 header_to_source_mapping,
                 target_compilers,
                 lazy_flag_parsing):
        """Initialize a cmake-based flag storage.

        Args:
            include_prefixes (str[]): A List of valid include prefixes.
            prefix_paths (str[]): A list of paths to append to
                CMAKE_PREFIX_PATH before invoking cmake.
            flags (str[]): flags to pass to CMake
        """
        super().__init__(include_prefixes)
        self._cache = CMakeFileCache()
        self.__cmake_prefix_paths = prefix_paths
        self.__cmake_flags = flags
        self.__cmake_binary = cmake_binary
        self.__header_to_source_mapping = header_to_source_mapping
        self.__target_compilers = target_compilers
        self.__lazy_flag_parsing = lazy_flag_parsing

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
        # prepare search scope
        search_scope = self._update_search_scope_if_needed(
            search_scope, file_path)
        # TODO(igor): probably can be simplified. Why do we need to load
        # cached? should we just test if currently found one is in cache?
        log.debug("[cmake]:[get]: for file %s", file_path)
        cached_cmake_path = self._get_cached_from(file_path)
        log.debug("[cmake]:[cached]: '%s'", cached_cmake_path)
        current_cmake_file = File.search(
            file_name=self._FILE_NAME,
            search_scope=search_scope,
            search_content=['project(', 'project ('])
        if not current_cmake_file:
            log.debug("No CMakeLists.txt file with 'project' in it found.")
            return None
        current_cmake_path = current_cmake_file.full_path
        log.debug("[cmake]:[current]: '%s'", current_cmake_path)

        parsed_before = current_cmake_path in self._cache
        if parsed_before:
            log.debug("[cmake]: found cached CMakeLists.txt.")
            cached_cmake_path = current_cmake_path
            # remember that for this file we have found this cmakelists
            self._cache[file_path] = current_cmake_path
        path_unchanged = (current_cmake_path == cached_cmake_path)
        file_unchanged = File.is_unchanged(cached_cmake_path)
        if path_unchanged and file_unchanged:
            use_cached = True
            if CMakeFile.__need_cmake_rerun(cached_cmake_path):
                use_cached = False
            if cached_cmake_path not in self._cache:
                use_cached = False
            if use_cached:
                log.debug("[cmake]:[unchanged]: use existing db.")
                db_file_path = self._cache[cached_cmake_path]
                db = CompilationDb(
                    self._include_prefixes,
                    self.__header_to_source_mapping,
                    self.__lazy_flag_parsing)
                db_search_scope = TreeSearchScope(
                    from_folder=path.dirname(db_file_path))
                return db.get_flags(file_path, db_search_scope)

        # Check if CMakeLists.txt is a catkin project and add needed settings.
        catkinizer = Catkinizer(current_cmake_file)
        catkinizer.catkinize_if_needed()

        # Generate a new compilation database file and return flags from it.
        log.debug("[cmake]:[generate new db]")
        db_file = CMakeFile.__compile_cmake(
            cmake_file=File(current_cmake_path),
            cmake_binary=self.__cmake_binary,
            prefix_paths=self.__cmake_prefix_paths,
            flags=self.__cmake_flags,
            target_compilers=self.__target_compilers)
        if not db_file:
            return None
        if file_path:
            # write the current cmake file to cache
            self._cache[file_path] = current_cmake_path
            self._cache[current_cmake_path] = db_file.full_path
            File.update_mod_time(current_cmake_path)
        db = CompilationDb(
            self._include_prefixes,
            self.__header_to_source_mapping,
            self.__lazy_flag_parsing)
        db_search_scope = TreeSearchScope(from_folder=db_file.folder)
        flags = db.get_flags(file_path, db_search_scope)
        return flags

    @staticmethod
    def unique_folder_name(cmake_path):
        """Get unique build folder name.

        Args:
            cmake_path (str): Path to CMakeLists of this project.

        Returns:
            str: Path to a unique temp folder.
        """
        return File.get_temp_dir('cmake_builds',
                                 Tools.get_unique_str(cmake_path))

    @staticmethod
    def __prepend_prefix_paths(prefix_paths):
        updated_environment = os.environ.copy()
        log.debug("Prefix paths to prepend: %s", prefix_paths)
        merged_paths = ""
        for prefix_path in prefix_paths:
            merged_paths += prefix_path + ":"
        log.debug("Prepended prefix paths: %s", merged_paths)
        if CMakeFile._CMAKE_PREFIX_PATHS_TAG not in updated_environment:
            updated_environment[CMakeFile._CMAKE_PREFIX_PATHS_TAG] = ''
        merged_paths = "{}{}".format(
            merged_paths,
            updated_environment[CMakeFile._CMAKE_PREFIX_PATHS_TAG])
        updated_environment[CMakeFile._CMAKE_PREFIX_PATHS_TAG] = merged_paths
        log.debug("Updated CMAKE_PREFIX_PATH: %s",
                  updated_environment[CMakeFile._CMAKE_PREFIX_PATHS_TAG])
        return updated_environment

    @staticmethod
    def __compile_cmake(cmake_file, cmake_binary, prefix_paths, flags,
                        target_compilers):
        """Compile cmake given a CMakeLists.txt file.

        This returns  a new compilation database path to further parse the
        generated flags. The build is performed in a temporary folder with a
        unique folder name for the project being built - a hex number
        generated from the pull path to current CMakeListst.txt file.

        Args:
            cmake_file (tools.file): file object for CMakeLists.txt file
            prefix_paths (str[]): paths to add to CMAKE_PREFIX_PATH before
                                  running `cmake`
            flags (str[]): flags to pass to cmake
            target_compilers(dict): Compilers to use
        """
        if not cmake_file or not cmake_file.loaded():
            return None

        OutputPanelHandler.hide_panel()

        if not prefix_paths:
            prefix_paths = []
        if not flags:
            flags = []

        cmake_cmd = [cmake_binary, '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON'] \
            + flags + [cmake_file.folder]
        tempdir = CMakeFile.unique_folder_name(cmake_file.full_path)
        # sometimes there are variables missing to carry out the build. We
        # can set them here from the settings.
        updated_environment = CMakeFile.__prepend_prefix_paths(prefix_paths)

        # If target compilers are set, create a toolchain file to force
        # cmake using them:
        c_compiler = target_compilers.get(SublBridge.LANG_C_TAG, None)
        cpp_compiler = target_compilers.get(SublBridge.LANG_CPP_TAG, None)
        # Note: CMake does not let us explicitly set Objective-C/C++ compilers.
        #       Hence, we only set ones for C/C++ and let it derive the rest.
        if c_compiler is not None or cpp_compiler is not None:
            toolchain_file_path = path.join(tempdir, "ECC-Toolchain.cmake")
            with open(toolchain_file_path, "w") as file:
                file.write("include(CMakeForceCompiler)\n")
                if c_compiler is not None:
                    file.write(
                        "set(CMAKE_C_COMPILER  {})\n".format(c_compiler))
                if cpp_compiler is not None:
                    file.write(
                        "set(CMAKE_CPP_COMPILER  {})\n".format(cpp_compiler))
            cmake_cmd += ["-DCMAKE_TOOLCHAIN_FILE={}".format(
                toolchain_file_path)]

        log.debug(' running command: %s', cmake_cmd)
        output_text = Tools.run_command(
            command=cmake_cmd, cwd=tempdir, env=updated_environment)
        log.debug("Cmake produced output: \n%s", output_text)
        if "CMake Error" in output_text:
            error_msg = "Error in file:\n{}\n\n{}".format(
                cmake_file.full_path, output_text)
            OutputPanelHandler.show(error_msg)
            return None
        database_path = path.join(tempdir, CompilationDb._FILE_NAME)
        if not path.exists(database_path):
            log.error(
                "Cmake has finished, but generated no compilation database.")
            OutputPanelHandler.show(output_text)
            return None
        # update the dependency modification time
        dep_file_path = path.join(tempdir, 'CMakeFiles', 'Makefile.cmake')
        if path.exists(dep_file_path):
            for dep_path in CMakeFile.__get_cmake_deps(dep_file_path):
                File.update_mod_time(dep_path)
        return File(database_path)

    @staticmethod
    def __get_cmake_deps(deps_file):
        """Parse dependencies from Makefile.cmake.

        Args:
            deps_file (str): Full path to Makefile.cmake file.

        Returns:
            str[]: List of full paths to dependency files.
        """
        folder = path.dirname(path.dirname(deps_file))
        deps = []
        with open(deps_file, 'r') as f:
            content = f.read()
            found = CMakeFile._DEP_REGEX.findall(content)
            for dep in found:
                if not path.isabs(dep):
                    dep = path.join(folder, dep)
                deps.append(dep)
        return deps

    @staticmethod
    def __need_cmake_rerun(cmake_path):
        tempdir = CMakeFile.unique_folder_name(cmake_path)
        if not path.exists(tempdir):
            # temp folder not there. We need to run cmake to generate one.
            return True
        dep_file_path = path.join(tempdir, 'CMakeFiles', 'Makefile.cmake')
        if not path.exists(dep_file_path):
            # no file that manages dependencies, we need to run cmake.
            return True

        # now check if the deps actually changed since we last saw them
        for dep_file in CMakeFile.__get_cmake_deps(dep_file_path):
            if not path.exists(dep_file):
                return True
            if not File.is_unchanged(dep_file):
                return True
        return False
