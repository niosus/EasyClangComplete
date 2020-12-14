"""Host a class that controls the way we interact with quick pannel."""

import logging
import sublime

from ..error_vis.popup_error_vis import MIN_ERROR_SEVERITY

log = logging.getLogger("ECC")


class ErrorQuickPanelHandler():
    """Handle the quick panel."""

    ENTRY_TEMPLATE = "{type}: {error}"

    def __init__(self, view, errors):
        """Initialize the object.

        Args:
            view (sublime.View): Current view.
            errors (list(dict)): A list of error dicts.
        """
        self.view = view
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

    def show(self, window):
        """Show the quick panel."""
        start_idx = 0
        window.show_quick_panel(
            self.items_to_show(),
            self.on_done,
            sublime.MONOSPACE_FONT,
            start_idx)
