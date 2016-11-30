""" Utilities for clang

Attributes:
    log (logging.log): logger for this module
"""
import platform
import logging
import subprocess

from os import path

log = logging.getLogger(__name__)


class ClangUtils:
    """
    Utils to help handling liblclang, e.g. searching for it

    Attributes:
        libclang_name (str): name of the libclang library file
        linux_suffixes (list): suffixes for linux
        osx_suffixes (list): suffixes for osx
        windows_suffixes (list): suffixes for windows
    """
    libclang_name = None

    linux_suffixes = ['.so', '.so.1']
    osx_suffixes = ['.dylib']
    windows_suffixes = ['.dll', '.lib']

    @staticmethod
    def get_suffixes():
        """ get suffixes for current system """
        if platform.system() == "Windows":
            return ClangUtils.windows_suffixes
        if platform.system() == "Linux":
            return ClangUtils.linux_suffixes
        if platform.system() == "Darwin":
            return ClangUtils.osx_suffixes
        return None

    @staticmethod
    def dir_from_output(output):
        """ Get library directory based on the output of clang

        Args:
            output (str): raw output from clang

        Returns:
            str: path to folder with libclang
        """
        log.debug(" real output: %s", output)
        if platform.system() == "Darwin":
            # [HACK] uh... I'm not sure why it happens like this...
            folder_to_search = path.join(output, '..', '..')
            log.debug(" folder to search: %s", folder_to_search)
            return folder_to_search
        elif platform.system() == "Windows":
            log.debug(" architecture: %s", platform.architecture())
            return path.normpath(output)
        elif platform.system() == "Linux":
            return path.dirname(output)
        return None

    @staticmethod
    def find_libclang_dir(clang_binary):
        """ Find directory with libclang

        Args:
            clang_binary (str): clang binary to call

        Returns:
            str: folder with libclang
        """
        stdin = None
        stderr = None
        log.debug(" platform: %s", platform.architecture())
        log.debug(" python version: %s", platform.python_version())
        for suffix in ClangUtils.get_suffixes():
            # pick a name for a file
            log.info(" we are on '%s'", platform.system())
            file = "libclang{}".format(suffix)
            log.info(" searching for: '%s'", file)
            startupinfo = None
            # let's find the library
            if platform.system() == "Darwin":
                # [HACK]: wtf??? why does it not find libclang.dylib?
                get_library_path_cmd = [clang_binary, "-print-file-name="]
            elif platform.system() == "Windows":
                get_library_path_cmd = [clang_binary, "-print-prog-name="]
                # Don't let console window pop-up briefly.
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                stdin = subprocess.PIPE
                stderr = subprocess.PIPE
            else:
                get_library_path_cmd = [clang_binary, "-print-file-name={}".format(file)]
            output = subprocess.check_output(
                get_library_path_cmd,
                stdin=stdin,
                stderr=stderr,
                startupinfo=startupinfo).decode('utf8').strip()
            log.info(" libclang search output = '%s'", output)
            if output:
                libclang_dir = ClangUtils.dir_from_output(output)
                if path.isdir(libclang_dir) and path.exists(path.join(libclang_dir, file)):
                    log.info(" found libclang dir: '%s'", libclang_dir)
                    log.info(" found library file: '%s'", file)
                    ClangUtils.libclang_name = file
                    return libclang_dir
            log.warning(" clang could not find '%s'", file)
        # if we haven't found anything there is nothing to return
        log.error(" no libclang found at all")
        return None
