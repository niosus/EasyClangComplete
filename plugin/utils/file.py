"""Encapsulate file processing."""

import logging
import sublime
import tempfile
from os import path
from os import listdir
from os import makedirs

from .tools import PKG_NAME


log = logging.getLogger("ECC")


class File:
    """Encapsulates a file."""
    __modification_cache = {}

    def __init__(self, file_path=None):
        """Initialize a new file and create it if needed.

        Args:
            file_path (str, optional): generate file object from this path
        """
        # intialize full path
        self.__full_path = None

        # fill the object if possible
        if not file_path:
            # leave the object unitialized
            return
        self.__full_path = path.abspath(file_path)
        # initialize the file if it does not exist already
        if path.isfile(self.__full_path):
            open(self.__full_path, 'r').close()
        else:
            open(self.__full_path, 'a+').close()

    @property
    def full_path(self):
        """Get full path to file.

        Returns:
            str: full path
        """
        return self.__full_path

    @property
    def folder(self):
        """Get parent folder to the file.

        Returns:
            str: parent folder of a file
        """
        return path.dirname(self.__full_path)

    @property
    def lines(self):
        """Return as list of all lines in the file."""
        if not self.loaded():
            log.warning("Trying to read file that has not been loaded.")
            return None
        with open(self.__full_path, encoding='utf-8') as f:
            return f.readlines()

    def loaded(self):
        """Check if the file is loaded."""
        if self.__full_path:
            return True
        return False

    def contains(self, query):
        """Check if file contains a query (only lowercase)."""
        for line in self.lines:
            if line.lower().startswith(query):
                log.debug("found needed line: '%s'", line.strip())
                return True
        return False

    @staticmethod
    def is_unchanged(file_path):
        """Check if file is unchanged since last access.

        Args:
            file_path (str): Path to a file.

        Returns:
            bool: True if unchanged, False otherwise.
        """
        if not file_path:
            return False
        if not path.exists(file_path):
            return False
        actual_mod_time = path.getmtime(file_path)
        if file_path not in File.__modification_cache:
            log.debug("never seen file '%s' before. Updating.", file_path)
            File.__modification_cache[file_path] = actual_mod_time
            return False
        cached_mod_time = File.__modification_cache[file_path]
        if actual_mod_time != cached_mod_time:
            File.__modification_cache[file_path] = actual_mod_time
            return False
        return True

    @staticmethod
    def is_ignored(file_name, glob_ignore_list):
        """Check if the current view must be ignored.

        Args:
            file_name (str): current view file name
            glob_ignore_list (str[]): a list of glob-like ignore patterns

        Returns:
            bool: True if valid, False otherwise
        """
        import fnmatch
        for ignore_glob in glob_ignore_list:
            if fnmatch.fnmatch(file_name, ignore_glob):
                # We have found at least one matching ignore pattern.
                return True
        return False

    @staticmethod
    def canonical_path(input_path, folder=''):
        """Return a canonical path of the file.

        Args:
            input_path (str): path to convert.
            folder (str, optional): parent folder.

        Returns:
            str: canonical path
        """
        if not input_path:
            return None
        input_path = path.expanduser(input_path)
        if not path.isabs(input_path):
            input_path = path.join(folder, input_path)
        normpath = path.normpath(input_path)
        if path.exists(normpath):
            return path.realpath(normpath)
        return normpath

    @staticmethod
    def expand_all(input_path,
                   wildcard_values={},
                   current_folder='',
                   expand_globbing=True):
        """Expand everything in this path.

        This returns a list of canonical paths.
        """
        expanded_path = path.expandvars(input_path)
        expanded_path = sublime.expand_variables(
            expanded_path, wildcard_values)
        expanded_path = File.canonical_path(expanded_path, current_folder)
        if not expanded_path:
            return []
        if expand_globbing:
            from glob import glob
            all_paths = glob(expanded_path)
        else:
            all_paths = [expanded_path]
        if len(all_paths) > 0 and all_paths[0] != input_path:
            log.debug("Populated '%s' to '%s'", input_path, all_paths)
            return all_paths
        elif expanded_path != input_path:
            log.debug("Populated '%s' to '%s'", input_path, expanded_path)
        return [expanded_path]

    @staticmethod
    def update_mod_time(full_path):
        """Update modification time.

        Args:
            full_path (str): current full path to file.
        """
        log.debug("updating modification time for file '%s'", full_path)
        mod_time = path.getmtime(full_path)
        File.__modification_cache[full_path] = mod_time

    @staticmethod
    def search(file_name, search_scope, search_content=None):
        """Search for a file up the tree.

        Args:
            file_name (str): Search for the file with this name
            search_scope (SearchScope): scope where to search for file
            search_content (str, list, optional): the file must contain these

        Returns:
            File: found file
        """
        log.debug("Searching '%s' file in: %s",
                  file_name, search_scope)
        for current_folder in search_scope:
            import os
            if not os.access(current_folder, os.R_OK):
                continue
            for file in listdir(current_folder):
                if file == file_name:
                    found_file = File(path.join(current_folder, file))
                    log.debug("Found '%s' file: %s",
                              file_name, found_file.full_path)
                    if not search_content:
                        log.debug("Nothing to search for in file so its ok.")
                        return found_file
                    if isinstance(search_content, list):
                        for search_query in search_content:
                            if found_file.contains(search_query):
                                return found_file
                    elif isinstance(search_content, str):
                        if found_file.contains(search_content):
                            return found_file
                    log.debug("Skipping file '%s'. ", found_file)
                    log.debug("No line starts with: '%s'", search_content)
                    continue
        return None

    @staticmethod
    def get_temp_dir(*subfolders):
        """Create a temporary folder if needed and return it."""
        tempdir = path.join(tempfile.gettempdir(), PKG_NAME, *subfolders)
        try:
            makedirs(tempdir)
        except OSError:
            log.debug("Folder %s exists.", tempdir)
        return tempdir
