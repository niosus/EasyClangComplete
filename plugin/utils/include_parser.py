"""Find all includes."""
import os
import logging
from os import path

import sublime

from ..utils import thread_job

log = logging.getLogger("ECC")

FILE_TAG = "[file]   "
FOLDER_TAG = "[folder] "


class IncludeCompleter():
    """Handle the include completion in the quick panel."""

    MATCHING_CHAR = {
        '<': '>',
        '"': '"'
    }

    def __init__(self, view, opening_char, thread_pool):
        """Initialize the object."""
        self.view = view
        self.opening_char = opening_char
        self.thread_pool = thread_pool
        self.folders_and_headers = None
        self.max_lines_per_item = 1
        self.full_include_path = None

    def start_completion(self, initial_folders):
        """Start completing includes."""
        job = thread_job.ThreadJob(
            name=thread_job.ThreadJob.COMPLETE_INCLUDES_TAG,
            function=IncludeCompleter.__get_all_headers,
            callback=self.__on_folders_loaded,
            args=[initial_folders, False])
        self.thread_pool.new_job(job)

    def __on_folders_loaded(self, future):
        if future.done() and not future.cancelled():
            self.folders_and_headers = [
                [tag, name, list(paths)]
                for (tag, name), paths in future.result().items()]
            self.max_lines_per_item = max([len(paths)
                                           for paths in future.result().values()])
            self.view.window().show_quick_panel(
                self.items_to_show(),
                self.on_done,
                sublime.MONOSPACE_FONT,
                start_idx=0)
        else:
            log.debug("could not update config -> cancelled")

    def items_to_show(self):
        """Present include_folders as list of lists."""
        if not self.folders_and_headers:
            return []
        contents = []
        for tag, name, paths in self.folders_and_headers:
            padding = self.max_lines_per_item - len(paths)
            contents.append([tag + name] + paths + [''] * padding)
        return contents

    def on_done(self, idx):
        """Pick this error to navigate to a file."""
        if not self.folders_and_headers:
            log.debug("No folders to show for includes yet.")
            return None
        log.debug("Picked idx: %s", idx)
        if idx < 0 or idx >= len(self.folders_and_headers):
            return None
        tag, name, paths = self.folders_and_headers[idx]
        if not self.full_include_path:
            self.full_include_path = ''
        self.full_include_path = path.join(self.full_include_path, name)
        if tag == FOLDER_TAG:
            self.start_completion(paths)
            return None
        return self.view.run_command(
            "insert",
            {"characters": "{opening_char}{path}{closing_char}".format(
                opening_char=self.opening_char,
                path=self.full_include_path,
                closing_char=IncludeCompleter.MATCHING_CHAR[self.opening_char])})

    @staticmethod
    def __get_all_headers(folders, force_unix_includes):
        """Parse all the folders and return all headers."""
        def to_platform_specific_paths(folders):
            """We might want to have back slashes intead of slashes."""
            for idx, folder in enumerate(folders):
                folders[idx] = path.normpath(folder)
            return folders

        matches = {}
        if force_unix_includes:
            folders = to_platform_specific_paths(folders)
        for folder in folders:
            if not path.exists(folder) or not path.isdir(folder):
                continue
            log.debug("Going through: %s", folder)
            for name in os.listdir(folder):
                full_path = path.realpath(path.join(folder, name))
                if path.isdir(full_path):
                    key = (FOLDER_TAG, name)
                    if key not in matches:
                        matches[key] = set([full_path])
                    else:
                        matches[key].add(full_path)
                    continue
                _, ext = path.splitext(name)
                if not ext or ext.startswith(".h"):
                    key = (FILE_TAG, name)
                    if key not in matches:
                        matches[key] = set([full_path])
                    else:
                        matches[key].add(full_path)
                    continue
        log.debug("Includes completion list size: %s", len(matches))
        return matches
