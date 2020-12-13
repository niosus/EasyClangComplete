"""Host a class that controls the way we interact with quick pannel."""

import logging
from os import path

import sublime

from ..utils import thread_job
from ..utils import include_parser
from ..error_vis.popup_error_vis import MIN_ERROR_SEVERITY

log = logging.getLogger("ECC")


class QuickPanelHandler:
    """Handle the quick panel."""

    def __init__(self, view):
        """Initialize the object.

        Args:
            view (sublime.View): Current view.
            errors (list(dict)): A list of error dicts.
        """
        self.view = view

    def show(self, window):
        """Show the quick panel."""
        start_idx = 0
        window.show_quick_panel(
            self.items_to_show(),
            self.on_done,
            sublime.MONOSPACE_FONT,
            start_idx,
            self.on_highlighted)

    def items_to_show(self):
        """All items that are to be shown."""
        log.error("Abstract method is called!")

    def on_highlighted(self, idx):
        """Gets called when user navigates to a line."""
        log.debug("Navigated to idx: %s", idx)

    def on_done(self, idx):
        """Gets called once something is picked."""
        log.error("Abstract method is called!")


class IncludeCompleter():
    """Handle the quick panel."""

    MATCHING_CHAR = {
        '<': '>',
        '"': '"'
    }

    def __init__(self, view, edit, opening_char, thread_pool):
        """Initialize the object."""
        self.view = view
        self.edit = edit
        self.opening_char = opening_char
        self.thread_pool = thread_pool
        self.folders_and_headers = None
        self.full_include_path = None

    def start_completion(self, initial_folders):
        job = thread_job.ThreadJob(
            name=thread_job.ThreadJob.COMPLETE_INCLUDES_TAG,
            function=include_parser.get_all_headers,
            callback=self.__on_folders_loaded,
            args=[initial_folders, False])
        self.thread_pool.new_job(job)

    def __on_folders_loaded(self, future):
        if future.done() and not future.cancelled():
            self.folders_and_headers = future.result()
            self.show(self.view.window())
        else:
            log.debug("could not update config -> cancelled")

    def items_to_show(self):
        """Present include_folders as list of lists."""
        contents = []
        if not self.folders_and_headers:
            return contents
        for header_or_folder in self.folders_and_headers:
            contents.append(
                [
                    path.basename(header_or_folder),
                    header_or_folder
                ])
        return contents

    def on_highlighted(self, idx):
        """Gets called when user navigates to a line."""
        log.debug("Navigated to idx: %s", idx)

    def on_done(self, idx):
        """Pick this error to navigate to a file."""
        if not self.folders_and_headers:
            log.debug("No folders to show for includes yet.")
            return None
        log.debug("Picked idx: %s", idx)
        if idx < 0 or idx >= len(self.folders_and_headers):
            return None
        picked_file_or_folder = self.folders_and_headers[idx]
        if not self.full_include_path:
            self.full_include_path = ''
        self.full_include_path = path.join(
            self.full_include_path, path.basename(picked_file_or_folder))
        if path.isdir(picked_file_or_folder):
            self.start_completion([picked_file_or_folder])
            return None
        return self.view.run_command(
            "insert",
            {"characters": "{opening_char}{path}{closing_char}".format(
                opening_char=self.opening_char,
                path=self.full_include_path,
                closing_char=IncludeCompleter.MATCHING_CHAR[self.opening_char])})

        # self.view.insert(
        #     self.edit, self.view.sel()[0].begin(), self.full_include_path)

    def show(self, window):
        """Show the quick panel."""
        start_idx = 0
        window.show_quick_panel(
            self.items_to_show(),
            self.on_done,
            sublime.MONOSPACE_FONT,
            start_idx,
            self.on_highlighted)


class ErrorQuickPanelHandler(QuickPanelHandler):
    """Handle the quick panel."""

    ENTRY_TEMPLATE = "{type}: {error}"

    def __init__(self, view, errors):
        """Initialize the object.

        Args:
            view (sublime.View): Current view.
            errors (list(dict)): A list of error dicts.
        """
        super().__init__(view)
        self.errors = errors

    def items_to_show(self):
        """Present errors as list of lists."""
        contents = []
        for error_dict in self.errors:
            error_type = 'ERROR'
            if error_dict['severity'] < MIN_ERROR_SEVERITY:
                error_type = 'WARNING'
            contents.append(
                [
                    ErrorQuickPanelHandler.ENTRY_TEMPLATE.format(
                        type=error_type,
                        error=error_dict['error']),
                    error_dict['file']
                ])
        return contents

    def on_done(self, idx):
        """Pick this error to navigate to a file."""
        log.debug("Picked idx: %s", idx)
        if idx < 0 or idx >= len(self.errors):
            return None
        return self.view.window().open_file(self.__get_formatted_location(idx),
                                            sublime.ENCODED_POSITION)

    def __get_formatted_location(self, idx):
        picked_entry = self.errors[idx]
        return "{file}:{row}:{col}".format(file=picked_entry['file'],
                                           row=picked_entry['row'],
                                           col=picked_entry['col'])
