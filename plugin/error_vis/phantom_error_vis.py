"""Module for compile error visualization.

Attributes:
    log (logging): this module logger
"""
import logging
import sublime
from os import path

from ..tools import SublBridge
from .popup_error_vis import PopupErrorVis

log = logging.getLogger(__name__)


class PhantomErrorVis(PopupErrorVis):
    """A class for compile error visualization with phantoms.

    Attributes:
        phantom_sets (dict): dictionary of phantom sets for view ids
    """

    phantom_sets = {}

    def show_phantoms(self, view):
        """Show phantoms for compilation errors.

        Args:
            view (sublime.View): current view
        """
        view.erase_phantoms(PopupErrorVis._TAG)
        if view.buffer_id() not in self.phantom_sets:
            phantom_set = sublime.PhantomSet(view, PopupErrorVis._TAG)
            self.phantom_sets[view.buffer_id()] = phantom_set
        else:
            phantom_set = self.phantom_sets[view.buffer_id()]
        phantoms = []
        current_error_dict = self.err_regions[view.buffer_id()]
        for err in current_error_dict:
            errors_dict = current_error_dict[err]
            errors_html = PhantomErrorVis._as_phantom_html(errors_dict)
            pt = view.text_point(err - 1, 1)
            phantoms.append(sublime.Phantom(
                sublime.Region(pt, view.line(pt).b),
                errors_html,
                sublime.LAYOUT_BELOW,
                on_navigate=self._on_phantom_navigate))
        phantom_set.update(phantoms)

    def show_errors(self, view):
        """Show current error regions as phantoms.

        We rely on the parent to generate highlights and will just add the
        phantoms on top of them.

        Args:
            view (sublime.View): Current view
        """
        super().show_errors(view)
        self.show_phantoms(view)

    def show_popup_if_needed(self, view, row):
        """We override an implementation from popup class here with empty one.

        Args:
            view (sublime.View): current view
            row (int): number of row
        """
        log.debug(" not showing popup as we use phantoms")

    def clear(self, view):
        """Clear errors from dict for view.

        Args:
            view (sublime.View): current view
        """
        super().clear(view)
        SublBridge.erase_phantoms(PopupErrorVis._TAG)

    @staticmethod
    def _on_phantom_navigate(self):
        """Close all phantoms in active view."""
        SublBridge.erase_phantoms(PopupErrorVis._TAG)

    @staticmethod
    def _as_phantom_html(errors_dict):
        """Get error as html for phantom.

        Args:
            errors_dict (dict): Current error
        """
        import cgi
        from string import Template
        html_file_name = "error_phantom.html"
        errors_html = ""
        first_error_processed = False
        for entry in errors_dict:
            processed_error = cgi.escape(entry['error'])
            processed_error = processed_error.replace(' ', '&nbsp;')
            if first_error_processed:
                processed_error = '<br>' + processed_error
            errors_html += processed_error
            first_error_processed = True
        # add error to html template
        html_file_path = path.join(
            PopupErrorVis._PATH_TO_HTML_FOLDER, html_file_name)
        errors_html_mask = Template(
            open(html_file_path, encoding='utf8').read())
        return errors_html_mask.substitute(content=errors_html)
