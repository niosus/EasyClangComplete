"""Utilities for clang.

Attributes:
    log (logging.log): logger for this module
"""
import platform
import logging
import subprocess
import re

from os import path

from .tools import Tools
from .tools import PKG_NAME
from .subl.subl_bridge import SublBridge


log = logging.getLogger("ECC")


class ClangUtils:
    """Utils to help handling libclang, e.g. searching for it.

    Attributes:
        LINUX_SUFFIXES (list): suffixes for linux
        OSX_SUFFIXES (list): suffixes for osx
        WINDOWS_SUFFIXES (list): suffixes for windows
    """
    WINDOWS_SUFFIXES = ['.dll', '.lib']
    LINUX_SUFFIXES = ['.so', '.so.10', '.so.9', '.so.8', '.so.7', '.so.1']
    OSX_SUFFIXES = ['.dylib']

    SUFFIXES = {
        'Windows': WINDOWS_SUFFIXES,
        'Linux': LINUX_SUFFIXES,
        'Darwin': OSX_SUFFIXES
    }

    # MSYS2 has `clang.dll` instead of `libclang.dll`
    POSSIBLE_FILENAMES = {
        'Windows': ['libclang', 'clang'],
        'Linux': ['libclang-$version', 'libclang'],
        'Darwin': ['libclang']
    }

    OSX_CLANG_VERSION_DICT = {
        '4.2': '3.2',
        '5.0': '3.3',
        '5.1': '3.4',
        '6.0': '3.5',
        '6.1': '3.6',
        '7.0': '3.7',
        '7.3': '3.8',
        '8.0': '3.8',
        '8.1': '3.9',
        '8.2': '3.9',
        '9.0': '4.0',
        '9.1': '4.0',
        '10.0': '6.0',
        '11.0': '7.0'
    }

    SORTED_OSX_VERSION_KEYS = [str(k) for k in sorted(
        [float(key) for key in OSX_CLANG_VERSION_DICT.keys()]
    )]

    CINDEX_DICT = {
        '3.2': PKG_NAME + ".plugin.clang.cindex32",
        '3.3': PKG_NAME + ".plugin.clang.cindex33",
        '3.4': PKG_NAME + ".plugin.clang.cindex34",
        '3.5': PKG_NAME + ".plugin.clang.cindex35",
        '3.6': PKG_NAME + ".plugin.clang.cindex36",
        '3.7': PKG_NAME + ".plugin.clang.cindex37",
        '3.8': PKG_NAME + ".plugin.clang.cindex38",
        '3.9': PKG_NAME + ".plugin.clang.cindex39",
        '4.0': PKG_NAME + ".plugin.clang.cindex40",
        '5.0': PKG_NAME + ".plugin.clang.cindex50",
    }

    SORTED_CINDEX_KEYS = [k for k in sorted(CINDEX_DICT)]

    @staticmethod
    def get_cindex_module_for_version(version):
        """Get cindex module name from version string.

        Args:
            version (str): version string, such as "3.8" or "3.8.0"

        Returns:
            str: cindex module name
        """
        for version_str in ClangUtils.CINDEX_DICT.keys():
            if not version.startswith(version_str):
                continue
            if version_str in ClangUtils.CINDEX_DICT:
                return ClangUtils.CINDEX_DICT[version_str]
        return ClangUtils.CINDEX_DICT[ClangUtils.SORTED_CINDEX_KEYS[-1]]

    @staticmethod
    def dir_from_output(output):
        """Get library directory based on the output of clang.

        Args:
            output (str): raw output from clang

        Returns:
            str: path to folder with libclang
        """
        log.debug("Real output: %s", output)
        if platform.system() == "Darwin":
            # [HACK] uh... I'm not sure why it happens like this...
            folder_to_search = path.join(output, '..', '..')
            log.debug("Folder to search: %s", folder_to_search)
            return folder_to_search
        elif platform.system() == "Windows":
            log.debug("Architecture: %s", platform.architecture())
            folder_to_search = path.join(output, '..')
            log.debug("Folder to search: %s", folder_to_search)
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
        POSSIBLE_FILENAMES = []
        for suffix in ClangUtils.SUFFIXES[current_system]:
            for name in ClangUtils.POSSIBLE_FILENAMES[current_system]:
                if platform.system() == "Linux":
                    name = name.replace("$version", version_str)
                POSSIBLE_FILENAMES.append(
                    "{name}{suffix}".format(name=name, suffix=suffix))
        return POSSIBLE_FILENAMES

    @staticmethod
    def find_libclang(clang_binary, libclang_path, version_str):
        """Find libclang.

        We either use a user-provided directory/file for libclang or search for
        one by calling clang_binary with specific parameters. We return both a
        folder and a full path to the found library.

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
        user_libclang_dir = None

        current_system = platform.system()
        if current_system == "Linux":
            # We only care about first two digits on Linux.
            version_str = version_str[0:3]

        if path.exists(libclang_path):
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

    @classmethod
    def get_clang_version_str(cls, clang_binary):
        """Get Clang version string from subprocess run of "clang_binary -v".

        Args:
            clang_binary (str): clang binary, e.g. "clang++-3.8"

        Returns:
            str: clang version number like: 3.8.0

        Raises: RuntimeError: There is an error while getting version. This is
            too important to continue. If this fails the plugin will not work
            at all.
        """
        check_version_cmd = [clang_binary, "-v"]
        log.info("Getting version from command: `%s`",
                 " ".join(check_version_cmd))
        output_text = Tools.run_command(check_version_cmd)

        if "Apple" in output_text:
            return cls._get_apple_clang_version_str(output_text)
        else:
            return cls._get_regular_clang_version_str(output_text)

    @classmethod
    def _get_regular_clang_version_str(cls, output_text):
        # now we have the output, and can extract version from it
        version_regex = re.compile(r"\d+\.\d+\.*\d*")
        match = version_regex.search(output_text)
        if match:
            version_str = match.group()
            return version_str
        else:
            raise RuntimeError(" Couldn't find clang version in clang version "
                               "output.")

    @classmethod
    def _get_apple_clang_version_str(cls, output_text):
        version_regex = re.compile(r"\d+\.\d+\.*\d*")
        match = version_regex.search(output_text)
        if match:
            version_str = match.group()
            # throw away the patch number
            osx_ver = ".".join(version_str.split(".")[:-1])
            try:
                # info from this table:
                # https://gist.github.com/yamaya/2924292
                if osx_ver in ClangUtils.OSX_CLANG_VERSION_DICT:
                    version_str = ClangUtils.OSX_CLANG_VERSION_DICT[osx_ver]
                else:
                    version_str = ClangUtils.OSX_CLANG_VERSION_DICT[
                        ClangUtils.SORTED_OSX_VERSION_KEYS[-1]]
            except Exception as e:
                SublBridge.show_error_dialog(
                    "Version '{}' of AppleClang is not "
                    "supported yet. Please open an issue "
                    "for it".format(osx_ver))
                raise e
            log.warning("OSX version %s reported. Reducing it to %s.",
                        osx_ver,
                        version_str)
            log.info("Found clang version %s", version_str)
            return version_str
        else:
            raise RuntimeError(" Couldn't find clang version in clang version "
                               "output.")
