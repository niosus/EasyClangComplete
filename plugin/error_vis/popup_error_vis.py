"""Module for compile error visualization.

Attributes:
    log (logging): this module logger
"""
import logging
import sublime
from os import path

from ..completion.compiler_variant import LibClangCompilerVariant
from ..settings.settings_storage import SettingsStorage
from ..popups.popups import Popup
from ..popups.popups import PopupStyle

log = logging.getLogger("ECC")

PATH_TO_HTML_FOLDER = path.join(
    path.dirname(path.dirname(__file__)), 'html')

PATH_TO_ICON = "Packages/EasyClangComplete/pics/icons/{icon}"


class PopupErrorVis:
    """A class for compile error visualization with popups.

    Attributes:
        err_regions (dict): dictionary of error regions for view ids
    """
    _TAG = "easy_clang_complete_errors"
    _ERROR_FLAGS = sublime.DRAW_EMPTY | sublime.DRAW_NO_FILL
    _ERROR_SCOPE = "invalid.illegal"

    def __init__(self, gutter_style=None):
        """Initialize error visualization.

        Args:
            mark_gutter (bool): add a mark to the gutter for error regions
        """
        self.err_regions = {}
        if gutter_style == SettingsStorage.GUTTER_COLOR_STYLE:
            self.gutter_mark = PATH_TO_ICON.format(icon="error_color.png")
        elif gutter_style == SettingsStorage.GUTTER_MONO_STYLE:
            self.gutter_mark = PATH_TO_ICON.format(icon="error_mono.png")
        else:
            self.gutter_mark = ""

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
            log.error("trying to show error on invalid view. Abort.")
            return
        log.debug("generating error regions for view %s", view_id)
        # first clear old regions
        if view_id in self.err_regions:
            log.debug("removing old error regions")
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
            log.error("view was closed -> cannot generate error vis in it")
            log.info("original exception: '%s'", repr(e))

    def add_error(self, view, error_dict):
        """Put new compile error in the dictionary of errors.

        Args:
            view (sublime.View): current view
            error_dict (dict): current error dict {row, col, file, region}
        """
        logging.debug(" adding error %s", error_dict)
        error_source_file = path.basename(error_dict['file'])
        if error_source_file == path.basename(view.file_name()):
            row = int(error_dict['row'])
            col = int(error_dict['col'])
            point = view.text_point(row - 1, col - 1)
            error_dict['region'] = view.word(point)
            if row in self.err_regions[view.buffer_id()]:
                self.err_regions[view.buffer_id()][row] += [error_dict]
            else:
                self.err_regions[view.buffer_id()][row] = [error_dict]

    def show_errors(self, view):
        """Show current error regions.

        Args:
            view (sublime.View): Current view
        """
        if view.buffer_id() not in self.err_regions:
            # view has no errors for it
            return
        current_error_dict = self.err_regions[view.buffer_id()]
        regions = PopupErrorVis._as_region_list(current_error_dict)
        log.debug("showing error regions: %s", regions)
        view.add_regions(
            PopupErrorVis._TAG,
            regions,
            PopupErrorVis._ERROR_SCOPE,
            self.gutter_mark,
            PopupErrorVis._ERROR_FLAGS)

    def erase_regions(self, view):
        """Erase error regions for view.

        Args:
            view (sublime.View): erase regions for view
        """
        if view.buffer_id() not in self.err_regions:
            # view has no errors for it
            return
        log.debug("erasing error regions for view %s", view.buffer_id())
        view.erase_regions(PopupErrorVis._TAG)

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
            max_severity, error_list = PopupErrorVis._as_list(errors_dict)

            text_to_show = '\n'.join(error_list)
            popup = None
            if max_severity > 2:
                popup = Popup.error(text_to_show)
            else:
                popup = Popup.warning(text_to_show)
            popup.show(view)
        else:
            log.debug("no error regions for row: %s", row)

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
    def _as_list(errors_dict):
        """Show error as html.

        Args:
            errors_dict (dict): Current error
        """
        error_list = []
        max_severity = 0
        for entry in errors_dict:
            error_list.append(entry['error'])
            if LibClangCompilerVariant.SEVERITY_TAG in entry:
                severity = entry[LibClangCompilerVariant.SEVERITY_TAG]
                if severity > max_severity:
                    max_severity = severity
        # add error to html template
        return max_severity, error_list

    @staticmethod
    def _as_region_list(err_regions_dict):
        """Make a list from error region dict.

        Args:
            err_regions_dict (dict): dict of error regions for current view

        Returns:
            list(Region): list of regions to show on sublime view
        """
        region_list = []
        for errors_list in err_regions_dict.values():
            for error in errors_list:
                region_list.append(error['region'])
        return region_list
