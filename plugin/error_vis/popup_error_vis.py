"""Module for compile error visualization.

Attributes:
    log (logging): this module logger
"""
import logging
import sublime
from os import path

from ..completion.compiler_variant import LibClangCompilerVariant
from ..settings.settings_storage import SettingsStorage
from ..utils.subl.row_col import ZeroIndexedRowCol
from .popups import Popup

log = logging.getLogger("ECC")

PATH_TO_ICON = "Packages/EasyClangComplete/pics/icons/{icon}"

MIN_ERROR_SEVERITY = 3


class PopupErrorVis:
    """A class for compile error visualization with popups.

    Attributes:
        err_regions (dict): dictionary of error regions for view ids
    """

    _TAG_ERRORS = "easy_clang_complete_errors"
    _TAG_WARNINGS = "easy_clang_complete_warnings"
    _ERROR_SCOPE = "undefined"
    _WARNING_SCOPE = "undefined"

    def __init__(self, settings):
        """Initialize error visualization.

        Args:
            mark_gutter (bool): add a mark to the gutter for error regions
        """
        gutter_style = settings.gutter_style
        mark_style = settings.linter_mark_style
        self.settings = settings

        self.err_regions = {}
        if gutter_style == SettingsStorage.GUTTER_COLOR_STYLE:
            self.gutter_mark_error = PATH_TO_ICON.format(
                icon="error.png")
            self.gutter_mark_warning = PATH_TO_ICON.format(
                icon="warning.png")
        elif gutter_style == SettingsStorage.GUTTER_MONO_STYLE:
            self.gutter_mark_error = PATH_TO_ICON.format(
                icon="error_mono.png")
            self.gutter_mark_warning = PATH_TO_ICON.format(
                icon="warning_mono.png")
        elif gutter_style == SettingsStorage.GUTTER_DOT_STYLE:
            self.gutter_mark_error = PATH_TO_ICON.format(
                icon="error_dot.png")
            self.gutter_mark_warning = PATH_TO_ICON.format(
                icon="warning_dot.png")
        else:
            log.error("Unknown option for gutter_style: %s", gutter_style)
            self.gutter_mark_error = ""
            self.gutter_mark_warning = ""

        if mark_style == SettingsStorage.MARK_STYLE_OUTLINE:
            self.draw_flags = sublime.DRAW_EMPTY | sublime.DRAW_NO_FILL
        elif mark_style == SettingsStorage.MARK_STYLE_FILL:
            self.draw_flags = 0
        elif mark_style == SettingsStorage.MARK_STYLE_SOLID_UNDERLINE:
            self.draw_flags = sublime.DRAW_NO_FILL | \
                sublime.DRAW_NO_OUTLINE | sublime.DRAW_SOLID_UNDERLINE
        elif mark_style == SettingsStorage.MARK_STYLE_STIPPLED_UNDERLINE:
            self.draw_flags = sublime.DRAW_NO_FILL | \
                sublime.DRAW_NO_OUTLINE | sublime.DRAW_STIPPLED_UNDERLINE
        elif mark_style == SettingsStorage.MARK_STYLE_SQUIGGLY_UNDERLINE:
            self.draw_flags = sublime.DRAW_NO_FILL | \
                sublime.DRAW_NO_OUTLINE | sublime.DRAW_SQUIGGLY_UNDERLINE
        else:
            self.draw_flags = sublime.HIDDEN

    def generate(self, view, errors):
        """Generate a dictionary that stores all errors.

        The errors are stored along with their positions and descriptions.
        Needed to show these errors on the screen.

        Args:
            view (sublime.View): current view
            errors (list): list of parsed errors (dict objects)
        """
        view_id = view.buffer_id()
        if view_id == 0:
            log.error("Trying to show error on invalid view. Abort.")
            return
        log.debug("Generating error regions for view %s", view_id)
        # first clear old regions
        if view_id in self.err_regions:
            log.debug("Removing old error regions")
            del self.err_regions[view_id]
        # create an empty region dict for view id
        self.err_regions[view_id] = {}

        # If the view is closed while this is running, there will be
        # errors. We want to handle them gracefully.
        try:
            for error in errors:
                self.add_error(view, error)
            log.debug("%s error regions ready", len(self.err_regions))
        except (AttributeError, KeyError, TypeError) as e:
            log.error("View was closed -> cannot generate error vis in it")
            log.info("Original exception: '%s'", repr(e))

    def add_error(self, view, error_dict):
        """Put new compile error in the dictionary of errors.

        Args:
            view (sublime.View): current view
            error_dict (dict): current error dict {row, col, file, region}
        """
        logging.debug("Adding error %s", error_dict)
        error_source_file = path.basename(error_dict['file'])
        if error_source_file == path.basename(view.file_name()):
            row_col = ZeroIndexedRowCol(error_dict['row'], error_dict['col'])
            point = row_col.as_1d_location(view)
            error_dict['region'] = view.word(point)
            if row_col.row in self.err_regions[view.buffer_id()]:
                self.err_regions[view.buffer_id()][row_col.row] += [error_dict]
            else:
                self.err_regions[view.buffer_id()][row_col.row] = [error_dict]

    def show_errors(self, view):
        """Show current error regions.

        Args:
            view (sublime.View): Current view
        """
        if view.buffer_id() not in self.err_regions:
            # view has no errors for it
            return
        current_error_dict = self.err_regions[view.buffer_id()]
        error_regions, warning_regions = PopupErrorVis._as_region_list(
            current_error_dict)
        log.debug("Showing error regions: %s", error_regions)
        log.debug("Showing warning regions: %s", warning_regions)
        view.add_regions(
            key=PopupErrorVis._TAG_ERRORS,
            regions=error_regions,
            scope=PopupErrorVis._ERROR_SCOPE,
            icon=self.gutter_mark_error,
            flags=self.draw_flags)
        view.add_regions(
            key=PopupErrorVis._TAG_WARNINGS,
            regions=warning_regions,
            scope=PopupErrorVis._WARNING_SCOPE,
            icon=self.gutter_mark_warning,
            flags=self.draw_flags)

    def erase_regions(self, view):
        """Erase error regions for view.

        Args:
            view (sublime.View): erase regions for view
        """
        if view.buffer_id() not in self.err_regions:
            # view has no errors for it
            return
        log.debug("Erasing error regions for view %s", view.buffer_id())
        view.erase_regions(PopupErrorVis._TAG_ERRORS)
        view.erase_regions(PopupErrorVis._TAG_WARNINGS)

    def show_popup_if_needed(self, view, row):
        """Show a popup if it is needed in this row.

        Args:
            view (sublime.View): current view
            row (int): number of row
        """
        if view.buffer_id() not in self.err_regions:
            return

        current_err_region_dict = self.err_regions[view.buffer_id()]
        if row in current_err_region_dict:
            errors_dict = current_err_region_dict[row]
            max_severity, error_list = PopupErrorVis._as_msg_list(errors_dict)
            text_to_show = PopupErrorVis.__to_md(error_list)
            if max_severity < MIN_ERROR_SEVERITY:
                popup = Popup.warning(text_to_show, self.settings)
            else:
                popup = Popup.error(text_to_show, self.settings)
            popup.show(view)
        else:
            log.debug("No error regions for row: %s", row)

    def clear(self, view):
        """Clear errors from dict for view.

        Args:
            view (sublime.View): current view
        """
        if view.buffer_id() not in self.err_regions:
            # no errors for this view
            return
        view.hide_popup()
        self.erase_regions(view)
        del self.err_regions[view.buffer_id()]

    @staticmethod
    def _as_msg_list(errors_dicts):
        """Return errors as list.

        Args:
            errors_dicts (dict[]): A list of error dicts
        """
        error_list = []
        max_severity = 0
        for entry in errors_dicts:
            error_list.append(entry['error'])
            if LibClangCompilerVariant.SEVERITY_TAG in entry:
                severity = entry[LibClangCompilerVariant.SEVERITY_TAG]
                if severity > max_severity:
                    max_severity = severity
        return max_severity, error_list

    @staticmethod
    def _as_region_list(err_regions_dict):
        """Make a list from error region dict.

        Args:
            err_regions_dict (dict): dict of error regions for current view

        Returns:
            list(Region): list of regions to show on sublime view
        """
        errors = []
        warnings = []
        for errors_list in err_regions_dict.values():
            for entry in errors_list:
                severity = MIN_ERROR_SEVERITY
                if LibClangCompilerVariant.SEVERITY_TAG in entry:
                    severity = entry[LibClangCompilerVariant.SEVERITY_TAG]
                if severity < MIN_ERROR_SEVERITY:
                    warnings.append(entry['region'])
                else:
                    errors.append(entry['region'])
        return errors, warnings

    @staticmethod
    def __to_md(error_list):
        """Convert an error dict to markdown string."""
        if len(error_list) > 1:
            # Make it a markdown list.
            text_to_show = '\n- '.join(error_list)
            text_to_show = '- ' + text_to_show
        else:
            text_to_show = error_list[0]
        return text_to_show
