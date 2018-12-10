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
        libclang_name (str): name of the libclang library file
        linux_suffixes (list): suffixes for linux
        osx_suffixes (list): suffixes for osx
        windows_suffixes (list): suffixes for windows
    """
    libclang_name = None

    windows_suffixes = ['.dll', '.lib']
    linux_suffixes = ['.so', '.so.1', 'so.7']
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
    def try_load_from_user_hint(libclang_path):
        """Load library hinted by the user.

        Args:
            libclang_path (str): full path to the libclang library file.

        Returns:
            str: folder of the libclang library or None if not found.
        """
        if path.exists(libclang_path):
            return path.dirname(libclang_path)

    @staticmethod
    def find_libclang_dir(clang_binary, libclang_path, version_str):
        """Find directory with libclang.

        Args:
            clang_binary (str): clang binary to call
            libclang_path (str): libclang path provided by user.
                Does not have to be valid.
            version_str(str): version of libclang to be used in format 3.8.0
        Returns:
            str: folder with libclang
        """
        stdin = None
        stderr = None
        log.debug("platform: %s", platform.architecture())
        log.debug("python version: %s", platform.python_version())
        current_system = platform.system()
        log.debug("we are on '%s'", platform.system())
        log.debug("user provided libclang_path: %s", libclang_path)
        # Get version string for help finding the proper libclang library on
        # Linux
        if libclang_path:
            # User thinks he knows better. Let him try his luck.
            libclang_dir = ClangUtils.try_load_from_user_hint(libclang_path)
            if libclang_dir:
                # It was found! No need to search any further!
                ClangUtils.libclang_name = path.basename(libclang_path)
                log.info("using user-provided libclang: '%s'", libclang_path)
                return libclang_dir
        # If the user hint did not work, we look for it normally
        if current_system == "Linux":
            # we only care about first two digits
            version_str = version_str[0:3]
        for suffix in ClangUtils.suffixes[current_system]:
            # pick a name for a file
            for name in ClangUtils.possible_filenames[current_system]:
                file = "{name}{suffix}".format(name=name, suffix=suffix)
                log.debug("searching for: '%s'", file)
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
                    file = file.replace("$version", version_str)
                    get_library_path_cmd = [
                        clang_binary, "-print-file-name={}".format(file)]
                output = subprocess.check_output(
                    get_library_path_cmd,
                    stdin=stdin,
                    stderr=stderr,
                    startupinfo=startupinfo).decode('utf8').strip()
                log.debug("libclang search output = '%s'", output)
                if output:
                    libclang_dir = ClangUtils.dir_from_output(output)
                    if path.isdir(libclang_dir):
                        full_libclang_path = path.join(libclang_dir, file)
                        log.debug("Checking path: %s", full_libclang_path)
                        if path.exists(full_libclang_path):
                            log.info("found libclang library file: '%s'",
                                     full_libclang_path)
                            ClangUtils.libclang_name = file
                            return libclang_dir
                log.warning("Clang could not find '%s'", file)
        # if we haven't found anything there is nothing to return
        log.error("no libclang found at all")
        return None
