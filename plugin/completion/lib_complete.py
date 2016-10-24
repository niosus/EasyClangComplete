"""This module contains class for libclang based completions

Attributes:
    cindex_dict (dict): dict of cindex entries for each version of clang
    log (logging.Logger): logger for this module
"""
import importlib
import sublime
import time
import logging

from .base_complete import BaseCompleter
from .compiler_variant import LibClangCompilerVariant
from .. import error_vis
from ..tools import Tools
from ..tools import SublBridge
from ..tools import PKG_NAME
from ..utils.stamped_tu import StampedTu

from threading import Timer
from threading import RLock


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
        TUs (dict(utils.StampledTu)): dictionary of timestamped translation
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

        # initialize cindex
        if self.version_str in cindex_dict:
            # import cindex bundled with this plugin. We cannot use the default
            # one because sublime uses python 3, but there are no python
            # bindings for python 3
            log.debug(
                " using bundled cindex: %s", cindex_dict[self.version_str])
            cindex = importlib.import_module(cindex_dict[self.version_str])
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

        """
        if view_id not in self.TUs:
            log.error(" no tu for view id: %s, so not removing", view_id)
            return
        log.debug(" removing translation unit for view id: %s", view_id)
        del self.TUs[view_id]

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

    def init(self, view, settings):
        """Initialize the completer. Builds the view.

        Args:
            view (sublime.View): current view
            settings (Settings): plugin settings

        """
        # Return early if this is an invalid view.
        if not Tools.is_valid_view(view):
            return

        # call initializer from the super class
        super(Completer, self).init(view, settings)

        file_name = view.file_name()
        file_body = view.substr(sublime.Region(0, view.size()))

        # initialize unsaved files
        files = [(file_name, file_body)]

        # init needed variables from settings
        clang_flags = []

        # set std_flag
        std_flag = None
        current_lang = Tools.get_view_syntax(view)
        if current_lang != 'C':
            std_flag = settings.std_flag_cpp
        else:
            std_flag = settings.std_flag_c

        # if we use project-specific settings we ignore everything else
        if settings.project_specific_settings:
            log.info(" overriding all flags by project ones")
            project_flags = settings.get_project_clang_flags()
            if project_flags:
                clang_flags.append(std_flag)
                clang_flags += project_flags
            else:
                log.error(" there are no project-specific settings.")
                log.info(" falling back to using plugin settings.")
        if len(clang_flags) < 2:
            # add std flag to all flags
            clang_flags.append(std_flag)
            # this means that project specific settings are either not used or
            # invalid, so we still need to initialize from settings

            # init includes to start with from settings
            includes = settings.populate_include_dirs(view)

            for include in includes:
                clang_flags.append('-I' + include)

            if settings.search_clang_complete and self.flags_manager:
                log.debug(" flags_manager loaded")
                custom_flags = self.flags_manager.get_flags(
                    separate_includes=False)
                clang_flags += custom_flags

        # now we have the flags and can continue initializing the TU
        if Tools.get_view_syntax(view) != "C":
            # treat this as c++ even if it is a header
            log.debug(" This is a C++ file. Adding `-x c++` to flags")
            clang_flags = ['-x'] + ['c++'] + clang_flags
        log.debug(" clang flags are: %s", clang_flags)
        v_id = view.buffer_id()
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

    def complete(self, view, cursor_pos, show_errors):
        """ This function is called asynchronously to create a list of
        autocompletions. Using the current translation unit it queries libclang
        for the possible completions. It also shows compile errors if needed.

        Args:
            view (sublime.View): current view
            cursor_pos (int): sublime provided poistion of the cursor
            show_errors (bool): controls if we need to show errors
        """
        file_body = view.substr(sublime.Region(0, view.size()))
        (row, col) = SublBridge.cursor_pos(view, cursor_pos)

        # unsaved files
        files = [(view.file_name(), file_body)]

        v_id = view.buffer_id()

        # do nothing if there in no translation_unit present
        with self.rlock:
            if v_id not in self.TUs:
                log.error(" cannot complete. No TU for view %s", v_id)
                return None
        # execute clang code completion
        with self.rlock:
            start = time.time()
            log.debug(" started code complete for view %s", v_id)
            complete_obj = self.TUs[v_id].tu().codeComplete(
                view.file_name(),
                row, col,
                unsaved_files=files)
            end = time.time()
            log.debug(" code complete done in %s seconds", end - start)

        if complete_obj is None or len(complete_obj.results) == 0:
            self.completions = []
        else:
            self.completions = Completer._parse_completions(complete_obj)
        log.debug(' completions: %s' % self.completions)
        self.async_completions_ready = True
        if len(self.completions) > 0:
            Completer._reload_completions(view)
        else:
            log.debug(" no completions")

        if show_errors:
            with self.rlock:
                self.show_errors(
                    view, self.TUs[v_id].tu().diagnostics)

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
