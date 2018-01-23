"""Host a class that controls the way we interact with quick pannel."""

import logging
import sublime

log = logging.getLogger("ECC")

ENTRY_TEMPLATE = "{type}: {error}"


class QuickPanelHandler(object):
    """Handle the quick panel."""

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
            if error_dict['severity'] < 3:
                error_type = 'WARNING'
            contents.append(
                [
                    ENTRY_TEMPLATE.format(type=error_type,
                                          error=error_dict['error']),
                    error_dict['file']
                ])
        return contents

    def on_done(self, idx):
        """Pick this error to navigate to a file."""
        log.debug("Picked idx: %s", idx)
        if idx < 0:
            return
        picked_entry = self.errors[idx]
        file_str = "{file}:{row}:{col}".format(file=picked_entry['file'],
                                               row=picked_entry['row'],
                                               col=picked_entry['col'])
        self.view.window().open_file(file_str, sublime.ENCODED_POSITION)

    def on_highlighted(self, idx):
        """Peek into a file upon highlighting the error from it."""
        log.debug("Navigated to idx: %s", idx)
        pass
