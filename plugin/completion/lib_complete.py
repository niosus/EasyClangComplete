"""This module contains class for libclang based completions

Attributes:
    cindex_dict (dict): dict of cindex entries for each version of clang
    log (logging.Logger): logger for this module
"""
import importlib
import sublime
import time
import logging
import copy

from .base_complete import BaseCompleter
from .compiler_variant import LibClangCompilerVariant
from .. import error_vis
from ..tools import Tools
from ..tools import SublBridge
from ..tools import PKG_NAME
from ..utils.stamped_tu import StampedTu

from threading import Timer
from threading import RLock

from ..plugin_settings import Settings

log = logging.getLogger(__name__)
log.debug(" reloading module")

cindex_dict = {
    '3.2': PKG_NAME + ".clang.cindex32",
    '3.3': PKG_NAME + ".clang.cindex33",
    '3.4': PKG_NAME + ".clang.cindex34",
    '3.5': PKG_NAME + ".clang.cindex35",
    '3.6': PKG_NAME + ".clang.cindex36",
    '3.7': PKG_NAME + ".clang.cindex37",
    '3.8': PKG_NAME + ".clang.cindex38",
    '3.9': PKG_NAME + ".clang.cindex39"
}

clang_utils_module_name = PKG_NAME + ".clang.utils"


class Completer(BaseCompleter):

    """Encapsulates completions based on libclang

    Attributes:
        rlock (threading.Rlock): recursive mutex
        timer (threading.Timer): timer object to schedule tu removal
        max_tu_age (int): maximum translation unit age in seconds
        timer_period (int): period of timer in seconds
        tu_module (cindex.TranslationUnit): module for proper cindex
        TUs (dict(utils.StampedTu)): dictionary of timestamped translation
            units for each view id
    """
    rlock = RLock()

    tu_module = None

    TUs = {}

    timer = None
    max_tu_age = None
    timer_period = 60  # seconds

    def __init__(self, clang_binary):
        """Initialize the Completer from clang binary, reading its version.
        Picks an according cindex for the found version.

        Args:
            clang_binary (str): string for clang binary e.g. 'clang++-3.8'

        """
        super(Completer, self).__init__(clang_binary)

        # slightly more complicated name retrieving to allow for more complex
        # version strings, e.g. 3.8.0
        cindex_module_name = Completer._cindex_for_version(self.version_str)

        if cindex_module_name:
            # import cindex bundled with this plugin. We cannot use the default
            # one because sublime uses python 3, but there are no python
            # bindings for python 3
            log.debug(
                " using bundled cindex: %s", cindex_module_name)
            cindex = importlib.import_module(cindex_module_name)
            # load clang helper class
            clang_utils = importlib.import_module(clang_utils_module_name)
            ClangUtils = clang_utils.ClangUtils
            # If we haven't already initialized the clang Python bindings, try
            # to figure out the path libclang.
            if not cindex.Config.loaded:
                # This will return something like /.../lib/clang/3.x.0
                libclang_dir = ClangUtils.find_libclang_dir(clang_binary)
                if libclang_dir:
                    cindex.Config.set_library_path(libclang_dir)

            Completer.tu_module = cindex.TranslationUnit
            # check if we can build an index. If not, set valid to false
            try:
                cindex.Index.create()
                self.valid = True
            except Exception as e:
                log.error(" error: %s", e)
                self.valid = False

        # Create compiler options of specific variant of the compiler.
        self.compiler_variant = LibClangCompilerVariant()

    def remove(self, view_id):
        """Remove tu for this view. Happens when we don't need it anymore.

        Args:
            view_id (int): view id

        Returns: view id
        """
        with self.rlock:
            if view_id not in self.TUs:
                log.error(" no tu for view id: %s, so not removing", view_id)
                return
            log.debug(" removing translation unit for view id: %s", view_id)
            del self.TUs[view_id]
            return view_id

    def exists_for_view(self, view_id):
        """find if there is a completer for the view

        Args:
            view_id (int): current view id

        Returns:
            bool: has completer
        """
        with self.rlock:
            if view_id in self.TUs:
                self.TUs[view_id].touch()
                return True
            return False

    def init_for_view(self, view, settings):
        """Initialize the completer. Builds the view.

        Args:
            view (sublime.View): current view
            settings (Settings): plugin settings

        """
        # Return early if this is an invalid view.
        if not Tools.is_valid_view(view):
            return

        # call initializer from the super class
        super(Completer, self).init_for_view(view, settings)

        file_name = view.file_name()
        file_body = view.substr(sublime.Region(0, view.size()))

        # initialize unsaved files
        files = [(file_name, file_body)]

        # get flags from manager
        clang_flags = self.flags_manager.get_flags()

        log.debug(" clang flags are: %s", clang_flags)
        v_id = view.buffer_id()
        if v_id == 0:
            log.warning(" this is default id. View is closed. Abort!")
            return
        with self.rlock:
            try:
                TU = Completer.tu_module
                start = time.time()
                log.debug(" compilation started for view id: %s", v_id)
                trans_unit = TU.from_source(
                    filename=file_name,
                    args=clang_flags,
                    unsaved_files=files,
                    options=TU.PARSE_PRECOMPILED_PREAMBLE |
                    TU.PARSE_CACHE_COMPLETION_RESULTS)
                self.TUs[v_id] = StampedTu(trans_unit)
                end = time.time()
                log.debug(" compilation done in %s seconds", end - start)
            except Exception as e:
                log.error(" error while compiling: %s", e)
            if settings.errors_on_save:
                self.show_errors(view, self.TUs[v_id].tu().diagnostics)

        # start timer if it is not set yet
        self.max_tu_age = settings.max_tu_age
        if not self.timer:
            self.timer = Timer(Completer.timer_period, self.__remove_old_TUs)
            self.timer.start()

    def complete(self, completion_request):
        """ This function is called asynchronously to create a list of
        autocompletions. Using the current translation unit it queries libclang
        for the possible completions.

        """
        view = completion_request.get_view()
        file_body = view.substr(sublime.Region(0, view.size()))
        (row, col) = SublBridge.cursor_pos(
            view, completion_request.get_trigger_position())

        # unsaved files
        files = [(view.file_name(), file_body)]

        v_id = view.buffer_id()

        with self.rlock:
            # do nothing if there in no translation_unit present
            if v_id not in self.TUs:
                log.error(" cannot complete. No TU for view %s", v_id)
                return (None, None)
            # execute clang code completion
            start = time.time()
            log.debug(" started code complete for view %s", v_id)
            complete_obj = self.TUs[v_id].tu().codeComplete(
                view.file_name(),
                row, col,
                unsaved_files=files)
            end = time.time()
            log.debug(" code complete done in %s seconds", end - start)

        if complete_obj is None or len(complete_obj.results) == 0:
            completions = []
        else:
            completions = Completer._parse_completions(complete_obj)
        log.debug(' completions: %s' % completions)

        # Copy content to clipboard or new window
        settings = Settings()
        if settings.copy_to_clipboard:
            res = copy.deepcopy(completions)
            res = [row[0] for row in completions]
            res = '\n'.join(sorted([row[row.rindex("\t") + 1:] for row in res]))

            # Clipboard
            # sublime.set_clipboard(res)

            # New window
            win = sublime.active_window()
            v = None

            if hasattr(self, "id_view"):
                for vv in win.views():
                    if vv.id() == self.id_view:
                        v = vv

            if v is None:
                v = win.new_file()
                v.set_name("EasyClangAutocompletions")
                v.set_scratch(True)
                self.id_view = v.id()

            v.run_command('select_all')
            v.run_command('right_delete')
            v.run_command('append', {'characters': res})

        return (completion_request, completions)

    def update(self, view, show_errors):
        """Reparse the translation unit. This speeds up completions
        significantly, so we perform this upon file save.

        Args:
            view (sublime.View): current view
            show_errors (bool): if true - highlight compile errors

        Returns:
            bool: reparsed successfully

        """
        v_id = view.buffer_id()
        log.debug(" view is %s", v_id)
        if v_id in self.TUs:
            with self.rlock:
                log.debug(" reparsing translation_unit for view %s", v_id)
                start = time.time()
                self.TUs[v_id].tu().reparse()
                end = time.time()
                log.debug(" reparsed in %s seconds", end - start)
                if show_errors:
                    self.show_errors(view, self.TUs[v_id].tu().diagnostics)
                return True
        log.error(" no translation unit for view id %s", v_id)
        return False

    def __remove_old_TUs(self):
        """ Remove old translation units and restart timer """
        # first restart timer
        self.timer.cancel()
        self.timer = Timer(Completer.timer_period, self.__remove_old_TUs)
        self.timer.start()

        # now do some work if needed
        if not self.max_tu_age:
            return

        log.debug(" removing TUs older than: %s secs.", self.max_tu_age)
        with self.rlock:
            old_TUs = []
            for key, tu in self.TUs.items():
                if tu.is_older_than(self.max_tu_age):
                    old_TUs.append(key)
            current_id = SublBridge.active_view_id()
            if len(old_TUs) < 1:
                log.debug(" no old TUs.")
                return
            for key in old_TUs:
                if key == current_id:
                    # don't delete the tu if this view is focused
                    log.debug(" TU for view %s is old but active: [skip]", key)
                    continue
                log.debug(" TU for view %s is old [delete]", key)
                del self.TUs[key]

    @staticmethod
    def _cindex_for_version(version):
        """ Get cindex module name from version string.

        Args:
            version (str): version string, such as "3.8" or "3.8.0"

        Returns:
            str: cindex module name
        """
        for version_str in cindex_dict.keys():
            if version.startswith(version_str):
                return cindex_dict[version_str]
        return None

    @staticmethod
    def _parse_completions(complete_results):
        """Create snippet-like structures from a list of completions

        Args:
            complete_results (list): raw completions list

        Returns:
            list: updated completions
        """
        completions = []
        for c in complete_results.results:
            hint = ''
            contents = ''
            place_holders = 1
            for chunk in c.string:
                if not chunk:
                    continue
                if not chunk.spelling:
                    continue
                hint += chunk.spelling
                if chunk.isKindTypedText():
                    trigger = chunk.spelling
                if chunk.isKindResultType():
                    hint += ' '
                    continue
                if chunk.isKindOptional():
                    continue
                if chunk.isKindInformative():
                    continue
                if chunk.isKindPlaceHolder():
                    contents += ('${' + str(place_holders) + ':' +
                                 chunk.spelling + '}')
                    place_holders += 1
                else:
                    contents += chunk.spelling
            completions.append([trigger + "\t" + hint, contents])
        return completions
