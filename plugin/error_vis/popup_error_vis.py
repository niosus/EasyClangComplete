"""Module for compile error visualization.

Attributes:
    log (logging): this module logger
"""
import logging
from os import path
from string import Template

from sublime import Region

from ..completion.compiler_variant import LibClangCompilerVariant

log = logging.getLogger(__name__)

PATH_TO_HTML_FOLDER = path.join(
    path.dirname(path.dirname(__file__)), 'html')

POPUP_ERROR_HTML_FILE = path.join(PATH_TO_HTML_FOLDER, "error_popup.html")
POPUP_WARNING_HTML_FILE = path.join(PATH_TO_HTML_FOLDER, "warning_popup.html")


class PopupErrorVis:
    """A class for compile error visualization with popups.

    Attributes:
        err_regions (dict): dictionary of error regions for view ids
    """
    _TAG = "easy_clang_complete_errors"
    _TAG_FIXIT = "easy_clang_complete_fixits"
    _MAX_POPUP_WIDTH = 1800

    ERROR_HTML_TEMPLATE = Template(
        open(POPUP_ERROR_HTML_FILE, encoding='utf8').read())
    WARNING_HTML_TEMPLATE = Template(
        open(POPUP_WARNING_HTML_FILE, encoding='utf8').read())

    def __init__(self):
        """Initialize error visualization."""
        self.err_regions = {}

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
            log.error(" trying to show error on invalid view. Abort.")
            return
        log.debug(" generating error regions for view %s", view_id)
        # first clear old regions
        if view_id in self.err_regions:
            log.debug(" removing old error regions")
            del self.err_regions[view_id]
        # create an empty region dict for view id
        self.err_regions[view_id] = {}

        # If the view is closed while this is running, there will be
        # errors. We want to handle them gracefully.
        try:
            for error in errors:
                self.add_error(view, error)
            log.debug(" %s error regions ready", len(self.err_regions))
        except (AttributeError, KeyError, TypeError) as e:
            log.error(" view was closed -> cannot generate error vis in it")
            log.info(" original exception: '%s'", repr(e))

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
        errors, fixits = PopupErrorVis._as_region_lists(current_error_dict)
        log.debug(" showing error regions: %s", errors)
        log.debug(" showing fixit regions: %s", fixits)
        view.add_regions(PopupErrorVis._TAG, errors, "code")
        view.add_regions(PopupErrorVis._TAG_FIXIT,
                         fixits,
                         "code",
                         'Packages/EasyClangComplete/icons/intentionBulb.png')

    def erase_regions(self, view):
        """Erase error regions for view.

        Args:
            view (sublime.View): erase regions for view
        """
        if view.buffer_id() not in self.err_regions:
            # view has no errors for it
            return
        log.debug(" erasing error regions for view %s", view.buffer_id())
        view.erase_regions(PopupErrorVis._TAG)
        view.erase_regions(PopupErrorVis._TAG_FIXIT)

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
            errors_html = PopupErrorVis._as_html(errors_dict)
            view.show_popup(errors_html, max_width=self._MAX_POPUP_WIDTH)
        else:
            log.debug(" no error regions for row: %s", row)

    def get_fixits_for_location(self, view, row):
        """Get list of FixIts for all errors in given row.

        Args:
            view (sublime.View): current view
            row (int): number of row
        Returns:
            List[Dict[...]] List of FixIt dicts
            Format {'region': tuple of two text points,
                    'value': fixit replacement value}
        """
        if view.buffer_id() not in self.err_regions:
            return
        current_err_region_dict = self.err_regions[view.buffer_id()]

        if row in current_err_region_dict:
            fixits = []
            for error in current_err_region_dict[row]:
                if 'fixits' not in error:
                    continue
                points = []
                for fixit in error['fixits']:
                    points.append(((view.text_point(fixit['start']['row'] - 1,
                                                    fixit['start']['col'] - 1),
                                    view.text_point(fixit['end']['row'] - 1,
                                                    fixit['end']['col'] - 1)),
                                   fixit['value']))
                regions, values = zip(*sorted(points))
                replacement = [values[0]]
                for i in range(1, len(points)):
                    replacement.append(view.substr(Region(regions[i - 1][1],
                                                          regions[i][0])))
                    replacement.append(values[i])
                fixits.append({'region': (regions[0][0], regions[-1][1]),
                               'value': ''.join(replacement)})
            if fixits:
                return fixits
            else:
                log.debug(" no fixits for row: %s", row)
        else:
            log.debug(" no error regions for row: %s", row)

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
    def _as_html(errors_dict):
        """Show error as html.

        Args:
            errors_dict (dict): Current error
        """
        import cgi
        errors_html_mask = PopupErrorVis.WARNING_HTML_TEMPLATE
        errors_html = ""
        for entry in errors_dict:
            processed_error = cgi.escape(entry['error'])
            # Add non-breaking space to prevent popup from getting a newline
            # after every word
            processed_error = processed_error.replace(' ', '&nbsp;')
            if LibClangCompilerVariant.SEVERITY_TAG in entry:
                severity = entry[LibClangCompilerVariant.SEVERITY_TAG]
                if severity > 2:
                    errors_html_mask = PopupErrorVis.ERROR_HTML_TEMPLATE
            errors_html += "<div>" + processed_error + "</div>"
        # add error to html template
        return errors_html_mask.substitute(content=errors_html)

    @staticmethod
    def _as_region_lists(err_regions_dict):
        """Make lists of errors and fixits regions from error region dict.

        Args:
            err_regions_dict (dict): dict of error regions for current view

        Returns:
            (list(Region),
             list(Region)): two lists of regions to show on sublime view
        """
        region_list = []
        fixit_list = []
        for errors_list in err_regions_dict.values():
            for error in errors_list:
                if 'fixits' in error:
                    fixit_list.append(error['region'])
                else:
                    region_list.append(error['region'])
        return region_list, fixit_list
