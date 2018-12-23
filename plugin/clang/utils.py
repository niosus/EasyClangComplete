"""Utilities for clang.

Attributes:
    log (logging.log): logger for this module
"""
import platform
import logging
import subprocess

from os import path

log = logging.getLogger("ECC")


class ClangUtils:
    """Utils to help handling libclang, e.g. searching for it.

    Attributes:
        linux_suffixes (list): suffixes for linux
        osx_suffixes (list): suffixes for osx
        windows_suffixes (list): suffixes for windows
    """
    windows_suffixes = ['.dll', '.lib']
    linux_suffixes = ['.so', '.so.1', '.so.7']
    osx_suffixes = ['.dylib']

    suffixes = {
        'Windows': windows_suffixes,
        'Linux': linux_suffixes,
        'Darwin': osx_suffixes
    }

    # MSYS2 has `clang.dll` instead of `libclang.dll`
    possible_filenames = {
        'Windows': ['libclang', 'clang'],
        'Linux': ['libclang-$version', 'libclang'],
        'Darwin': ['libclang']
    }

    @staticmethod
    def dir_from_output(output):
        """Get library directory based on the output of clang.

        Args:
            output (str): raw output from clang

        Returns:
            str: path to folder with libclang
        """
        log.debug("real output: %s", output)
        if platform.system() == "Darwin":
            # [HACK] uh... I'm not sure why it happens like this...
            folder_to_search = path.join(output, '..', '..')
            log.debug("folder to search: %s", folder_to_search)
            return folder_to_search
        elif platform.system() == "Windows":
            log.debug("architecture: %s", platform.architecture())
            folder_to_search = path.join(output, '..')
            log.debug("folder to search: %s", folder_to_search)
            return path.normpath(folder_to_search)
        elif platform.system() == "Linux":
            return path.normpath(path.dirname(output))
        return None

    @staticmethod
    def get_folder_and_name(libclang_path):
        """Load library hinted by the user.

        Args:
            libclang_path (str): full path to the libclang library file.

        Returns:
            str: folder of the libclang library or None if not found.
        """
        if not path.exists(libclang_path):
            log.debug("User provided wrong libclang path: '%s'", libclang_path)
            return None, None
        if path.isdir(libclang_path):
            log.debug("User provided folder for libclang: '%s'", libclang_path)
            return libclang_path, None
        # The user has provided a file. We will anyway search for the proper
        # file in the folder that contains this file.
        log.debug("User provided full libclang path: '%s'", libclang_path)
        return path.dirname(libclang_path), path.basename(libclang_path)

    @staticmethod
    def prepare_search_libclang_cmd(clang_binary, lib_file_name):
        """Prepare a command that we use to search for libclang paths."""
        stdin = None
        stdout = None
        stderr = None
        startupinfo = None
        # let's find the library
        if platform.system() == "Darwin":
            # [HACK]: wtf??? why does it not find libclang.dylib?
            get_library_path_cmd = [clang_binary, "-print-file-name="]
        elif platform.system() == "Windows":
            get_library_path_cmd = [clang_binary,
                                    "-print-prog-name=clang"]
            # Don't let console window pop-up briefly.
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            stdin = subprocess.PIPE
            stderr = subprocess.PIPE
        elif platform.system() == "Linux":
            get_library_path_cmd = [
                clang_binary, "-print-file-name={}".format(lib_file_name)]
        return get_library_path_cmd, stdin, stdout, stderr, startupinfo

    @staticmethod
    def get_all_possible_filenames(version_str):
        """Get a list of all filename on this system."""
        current_system = platform.system()
        possible_filenames = []
        for suffix in ClangUtils.suffixes[current_system]:
            for name in ClangUtils.possible_filenames[current_system]:
                if platform.system() == "Linux":
                    name = name.replace("$version", version_str)
                possible_filenames.append(
                    "{name}{suffix}".format(name=name, suffix=suffix))
        return possible_filenames

    @staticmethod
    def find_libclang(clang_binary, libclang_path, version_str):
        """Find libclang.

        We either use a user-provided directory/file for libclang or search for
        one by calling clang_binary with specific parameters. We return both the
        folder and full path to the found library.

        Args:
            clang_binary (str): clang binary to call
            libclang_path (str): libclang path provided by user.
                Does not have to be valid.
            version_str(str): version of libclang to be used in format 3.8.0
        Returns:
            str: folder with libclang
            str: full path to libclang library
        """
        log.debug("Platform: %s, %s", platform.system(),
                  platform.architecture())
        log.debug("Python version: %s", platform.python_version())
        log.debug("User provided libclang_path: '%s'", libclang_path)

        current_system = platform.system()
        if current_system == "Linux":
            # We only care about first two digits on Linux.
            version_str = version_str[0:3]

        if libclang_path:
            # User thinks he knows better. Let him try his luck.
            user_libclang_dir, libclang_file = ClangUtils.get_folder_and_name(
                libclang_path)
            if user_libclang_dir and libclang_file:
                # It was found! No need to search any further!
                log.info("Using user-provided libclang: '%s'", libclang_path)
                return user_libclang_dir, path.join(
                    user_libclang_dir, libclang_file)

        # If the user hint did not work, we look for it normally
        possible_filenames = ClangUtils.get_all_possible_filenames(version_str)
        for libclang_filename in possible_filenames:
            log.debug("Searching for: '%s'", libclang_filename)
            if user_libclang_dir:
                log.debug("Searching in user provided folder: '%s'",
                          user_libclang_dir)
                user_hinted_file = path.join(
                    user_libclang_dir, libclang_filename)
                if path.exists(user_hinted_file):
                    # Found valid file in the folder that the user provided.
                    return user_libclang_dir, user_hinted_file

            log.debug("Generating search folder")
            get_library_path_cmd, stdin, stdout, stderr, startupinfo = \
                ClangUtils.prepare_search_libclang_cmd(
                    clang_binary, libclang_filename)
            output = subprocess.check_output(
                get_library_path_cmd,
                stdin=stdin,
                stderr=stderr,
                startupinfo=startupinfo).decode('utf8').strip()
            log.debug("Libclang search output = '%s'", output)
            if output:
                libclang_dir = ClangUtils.dir_from_output(output)
                if path.isdir(libclang_dir):
                    full_libclang_path = path.join(
                        libclang_dir, libclang_filename)
                    log.debug("Checking path: %s", full_libclang_path)
                    if path.exists(full_libclang_path):
                        log.info("Found libclang library file: '%s'",
                                 full_libclang_path)
                        return libclang_dir, full_libclang_path
                log.debug("Clang could not find '%s'", full_libclang_path)
        # if we haven't found anything there is nothing to return
        log.error("No libclang found!")
        return None, None
