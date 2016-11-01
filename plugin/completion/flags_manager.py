""" Module with a class for managing flags from different sources

Attributes:
    log (logging.log): logger for this module
"""
import logging
import sublime
import subprocess

from os import path

from ..tools import Tools
from ..tools import File

log = logging.getLogger(__name__)


class SearchScope:
    """
    Encapsulation of a search scope for code cleanness.
    """
    from_folder = None
    to_folder = None

    def __init__(self, from_folder=None, to_folder=None):
        """
        Initialize the search scope. If eny of the folders in None,
        set it to root

        Args:
            from_folder (str, optional): search from this folder
            to_folder (str, optional): search up to this folder
        """
        self.from_folder = from_folder
        self.to_folder = to_folder
        if not self.to_folder:
            self.to_folder = path.abspath('/')
        if not self.from_folder:
            self.from_folder = path.abspath('/')

    def valid(self):
        """ Is the search scope valid?

        Returns:
            bool: True if valid, False otherwise
        """
        if self.from_folder and self.to_folder:
            return True
        return False


class FlagsManager:
    """
    A class that manages all the work with flags generation and update.

    Attributes:
        CLANG_COMPLETE_FILE_NAME (str): constant name of file to store flags
        CMAKE_DB_FILE_NAME (str): constant name of cmake database file
        CMAKE_FILE_NAME (str): constant name of CMakeLists.txt file
        cmake_mask (str format): mask for cmake command with path to fill
    """
    _cmake_file = File()
    _clang_complete_file = File()
    _flags = []
    _initial_flags = []
    _search_scope = SearchScope()
    _use_cmake = False
    _flags_update_strategy = "ask"
    _cmake_prefix_paths = []

    cmake_mask = 'cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON "{path}"'

    CMAKE_FILE_NAME = "CMakeLists.txt"
    CMAKE_DB_FILE_NAME = "compile_commands.json"
    CLANG_COMPLETE_FILE_NAME = ".clang_complete"

    def __init__(self,
                 view,
                 settings,
                 compiler_variant,
                 search_scope=SearchScope()):
        """
        Initialize the flags manager

        Args:
            view (sublime.View): current view
            settings (plugin.Settings): current settings
            compiler_variant (completion.CompilerVariant): current compiler
                variant picks correct initial flags based on compiler in use
            search_scope (tools.SearchScope, optional): search scope where to
                search for CMakeLists.txt file and .clang_complete file.
        """
        if not search_scope.valid():
            log.critical(" search scope is wrong.")
            return
        # intialize important variables
        cmake_prefix_paths = settings.cmake_prefix_paths
        if cmake_prefix_paths is None:
            cmake_prefix_paths = []
        self._search_scope = search_scope
        self._use_cmake = settings.generate_flags_with_cmake
        self._flags_update_strategy = settings.cmake_flags_priority
        self._cmake_prefix_paths = cmake_prefix_paths
        self._use_clang_complete_file = settings.search_clang_complete_file
        self._include_prefixes = compiler_variant.include_prefixes
        # expand all entries containing "~"
        self._cmake_prefix_paths \
            = [path.expanduser(x) for x in self._cmake_prefix_paths]
        log.debug(" expanded CMAKE_PREFIX_PATHs: %s", self._cmake_prefix_paths)

        # initialize default flags (init_flags list needs to be copied).
        self._initial_flags = list(compiler_variant.init_flags)
        current_lang = Tools.get_view_syntax(view)
        if current_lang == 'C' or current_lang == 'C99':
            self._initial_flags += settings.c_flags
        else:
            self._initial_flags += settings.cpp_flags

        home_folder = path.expanduser('~')
        self._initial_flags += self.parse_flags(
            home_folder, settings.populate_common_flags(view))

    def any_file_modified(self):
        """
        Any of the checked files was modified since last use.

        Returns:
            bool: True if modified, False otherwise
        """
        if self._cmake_file.was_modified():
            return True
        if self._clang_complete_file.was_modified():
            return True
        return False

    def get_flags(self):
        """
        A function that handles getting all the flags. It will generate new
        flags in a lazy fashion. When any changes are detected and will update
        the needed files and flags generated from them. In case no changes have
        been made to .clang_complete file or to CMakeLists.txt file it will
        just return already existing flags.

        Returns:
            str[]: flags
        """
        if not self._use_clang_complete_file:
            log.debug(" user doesn't want to look for .clang_complete file")
            log.debug(" use flags from settings only")
            return self._initial_flags

        if self._use_cmake and not self._cmake_file.loaded():
            # CMakeLists.txt was not loaded yet, so search for it
            log.debug(" cmake file not loaded yet. Searching for one...")
            self._cmake_file = File.search(
                file_name=FlagsManager.CMAKE_FILE_NAME,
                from_folder=self._search_scope.from_folder,
                to_folder=self._search_scope.to_folder,
                search_content="project")

        if self._use_cmake and self._cmake_file.was_modified():
            # generate a .clang_complete file from cmake file if cmake file
            # exists and was modified
            log.debug(" CMakeLists.txt was modified."
                      " Generate new .clang_complete")
            compilation_db = FlagsManager.compile_cmake(
                cmake_file=self._cmake_file,
                prefix_paths=self._cmake_prefix_paths)
            if compilation_db:
                new_flags = self.flags_from_database(compilation_db)
                new_clang_file_path = path.join(
                    self._cmake_file.folder(),
                    FlagsManager.CLANG_COMPLETE_FILE_NAME)
                # there is no need to modify anything if the flags have not
                # changed since we have last read them
                curr_flags = self.flags_from_clang_file(
                    file=File(new_clang_file_path))
                difference = set(new_flags).symmetric_difference(
                    set(curr_flags))
                if len(difference) > 0:
                    log.debug("'%s' is not equal to '%s' by %s so update",
                              new_flags, curr_flags, difference)
                    if len(curr_flags) > 0:
                        strategy = self._flags_update_strategy
                    else:
                        # there are no current flags, so no need to ask user
                        # what to do, just write the new file content
                        strategy = "overwrite"
                    self.write_flags_to_file(new_flags,
                                             new_clang_file_path,
                                             strategy)
                else:
                    log.debug(" the flags have not changed so we don't "
                              "modify the .clang_complete file")
            else:
                log.warning(" could not get compilation database from cmake")

        if not self._clang_complete_file.loaded():
            log.debug(" .clang_complete not loaded. Searching for one...")
            self._clang_complete_file = File.search(
                file_name=FlagsManager.CLANG_COMPLETE_FILE_NAME,
                from_folder=self._search_scope.from_folder,
                to_folder=self._search_scope.to_folder)

        generated_flags = []
        if self._clang_complete_file.was_modified():
            log.debug(" .clang_complete modified. Load new flags.")
            generated_flags = list(self.flags_from_clang_file(
                self._clang_complete_file))

        # the flags are now in final state, we can return them
        return FlagsManager.merge_flags(self._initial_flags, generated_flags)

    @staticmethod
    def merge_flags(initial_flags, generated_flags):
        """ Handle merging of initial and generated flags. Handles situations
        where std flag has to be overridden.

        Args:
            initial_flags (list(str)): initial flags from settings
            generated_flags (list(str)): flags from .clang_complete file

        Returns:
            list(str): merged flags
        """
        initial_std_flag_idx = Tools.find_flag_idx(initial_flags, "-std")
        generated_std_flag_idx = Tools.find_flag_idx(generated_flags, "-std")
        if initial_std_flag_idx and generated_std_flag_idx:
            # we have std flags in both the initial flags and generated ones
            log.debug(" overriding initial std flag with '%s'",
                      generated_flags[generated_std_flag_idx])
            initial_flags[initial_std_flag_idx] \
                = generated_flags[generated_std_flag_idx]
            generated_flags.pop(generated_std_flag_idx)
        return initial_flags + generated_flags

    @staticmethod
    def compile_cmake(cmake_file, prefix_paths):
        """
        Compiles cmake given a CMakeLists.txt file and get a new compilation
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
        import hashlib
        cmake_cmd = FlagsManager.cmake_mask.format(path=cmake_file.folder())
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

        database_path = path.join(tempdir, FlagsManager.CMAKE_DB_FILE_NAME)
        if not path.exists(database_path):
            log.error(" cmake has finished, but no compilation database.")
            return None
        return File(database_path)

    def write_flags_to_file(self, new_flags, file_path, strategy):
        """
        Given new set of flags, check if we need to overwrite flags and then if
        needed write these flags to the `.clang_complete` file.

        Args:
            new_flags (str[]): new flags
            file_path (str): path to .clang_complete file
            strategy (str): strategy to deal with conflicts in flags

        """
        if path.exists(file_path):
            log.debug(" path already exists")
            flag_strategy = FlagsManager.get_flags_strategy(strategy)
            log.debug(" picked '%s' strategy.", flag_strategy)
            if flag_strategy == "keep_old":
                return
            if flag_strategy == "merge":
                # union of two flag arrays
                curr_flags = self.flags_from_clang_file(File(file_path))
                new_flags = curr_flags + list(set(new_flags) - set(curr_flags))
            # unhandled is only "overwrite". "ask" is not possible here.
        f = open(file_path, 'w')
        # write file
        f.seek(0)
        f.write('\n'.join(new_flags) + '\n')
        f.close()

    @staticmethod
    def get_flags_strategy(strategy):
        """
        Get a str representing strategy used when dealing with new flags. Does
        not change the default strategy unless "ask" starategy is default. Then
        the strategy will be picked by asking the user.

        Args:
            strategy (str): default strategy

        Returns:
            str: picked strategy
        """
        if strategy == "ask":
            user_pick = sublime.yes_no_cancel_dialog(
                ".clang_complete file exists. What do you want to do?",
                "Merge!", "Overwrite!")
            if user_pick == sublime.DIALOG_YES:
                return "merge"
            if user_pick == sublime.DIALOG_NO:
                return "overwrite"
            if user_pick == sublime.DIALOG_CANCEL:
                return "keep_old"
        else:
            return strategy

    def flags_from_database(self, database_file):
        """Get flags from cmake compilation database
        Args: database_file (tools.File): compilation database file
        Returns:
            str[]: flags
        """
        import json
        data = None
        with open(database_file.full_path()) as data_file:
            data = json.load(data_file)
        if not data:
            return None
        flags_set = set()
        # TODO: A list should be used so that flag order is preserved but that
        # is least of a problems when we have an elephant in the room. Namely
        # combining flags from different compilation units into one set of flags
        # which is error prone for more complicated projects.
        for entry in data:
            command = entry['command']
            all_command_parts = command.split(' -')
            all_command_parts = ['-' + part for part in all_command_parts]
            current_flags = self.parse_flags(database_file.folder(),
                                             all_command_parts)
            flags_set = flags_set.union(current_flags)
        log.debug(" flags set: %s", flags_set)
        return list(flags_set)

    def flags_from_clang_file(self, file):
        """
        Parse .clang_complete file

        Args:
            file(Tools.File): .clang_complete file handle

        Returns:
            str[]: parsed list of includes from the file
        """
        if not path.exists(file.full_path()):
            log.debug(" .clang_complete does not exist yet. No flags present.")
            return []
        if not file.loaded():
            log.error(" cannot get flags from clang_complete_file. No file.")
            return []

        flags = []
        with open(file.full_path()) as f:
            content = f.readlines()
            flags = self.parse_flags(file.folder(), content)
        log.debug(" .clang_complete contains flags: %s", flags)
        return flags

    def parse_flags(self, folder, lines):
        """
        Parse the flags in a given file

        Args:
            folder (str): current folder
            lines (str[]): lines to parse

        Returns:
            str[]: flags
        """

        def to_absolute_include_path(flag, include_prefixes):
            """ Change path of include paths to absolute if needed.

            Args:
                flag (str): flag to check for relative path and fix if needed

            Returns:
                str: either original flag or modified to have absolute path
            """
            for prefix in include_prefixes:
                if flag.startswith(prefix):
                    include_path = flag[len(prefix):].strip()
                    if not path.isabs(include_path):
                        include_path = path.join(folder, include_path)
                    return prefix + path.normpath(include_path)
            return flag

        flags = []
        for line in lines:
            line = line.strip()
            if line.startswith("#"):
                continue
            flags.append(to_absolute_include_path(line, self._include_prefixes))
        return flags
