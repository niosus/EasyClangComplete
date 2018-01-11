"""Module for compile error visualization.

Attributes:
    log (logging): this module logger
"""
import logging
import sublime
import mdpopups

from ..tools import SublBridge
from ..tools import Tools
from .popup_error_vis import PopupErrorVis

log = logging.getLogger("ECC")


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
        mdpopups.erase_phantoms(view, PopupErrorVis._TAG)
        if view.buffer_id() not in self.phantom_sets:
            phantom_set = mdpopups.PhantomSet(view, PopupErrorVis._TAG)
            self.phantom_sets[view.buffer_id()] = phantom_set
        else:
            phantom_set = self.phantom_sets[view.buffer_id()]
        phantoms = []
        current_error_dict = self.err_regions[view.buffer_id()]
        for err in current_error_dict:
            errors_dict = current_error_dict[err]
            max_severity, error_list = PopupErrorVis._as_list(errors_dict)
            text_to_show = Tools.to_md(error_list)
            pt = view.text_point(err - 1, 1)
            phantoms.append(mdpopups.Phantom(
                region=sublime.Region(pt, view.line(pt).b),
                content=text_to_show,
                layout=sublime.LAYOUT_BELOW,
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
        log.debug("not showing popup as we use phantoms")

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
