"""This module contains class for libclang based completions.

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
from ..tools import Tools
from ..tools import SublBridge
from ..tools import PKG_NAME

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
    """Encapsulates completions based on libclang.

    Attributes:
        rlock (threading.Rlock): recursive mutex
        tu_module (cindex.TranslationUnit): module for proper cindex
        tu (cindex.TranslationUnit): current translation unit
    """
    name = "lib"
    rlock = RLock()

    def __init__(self, clang_binary, version_str):
        """Initialize the Completer from clang binary, reading its version.

        Picks an according cindex for the found version.

        Args:
            clang_binary (str): string for clang binary e.g. 'clang++-3.8'
            version_str (str): string for clang version e.g. '3.8.0'

        """
        super().__init__(clang_binary, version_str)

        # Create compiler options of specific variant of the compiler.
        self.compiler_variant = LibClangCompilerVariant()

        # init tu related variables
        with Completer.rlock:
            self.tu_module = None
            self.tu = None

            # slightly more complicated name retrieving to allow for more
            # complex version strings, e.g. 3.8.0
            cindex_module_name = Completer._cindex_for_version(
                self.version_str)

            if not cindex_module_name:
                log.critical(" No cindex module for clang version: %s",
                             self.version_str)
                return

            # import cindex bundled with this plugin. We cannot use the default
            # one because sublime uses python 3, but there are no python
            # bindings for python 3
            log.debug(" using bundled cindex: %s", cindex_module_name)
            cindex = importlib.import_module(cindex_module_name)

            # initialize ignore list to account for private methods etc.
            self.ignore_list = [cindex.CursorKind.DESTRUCTOR,
                                cindex.CursorKind.CLASS_DECL,
                                cindex.CursorKind.ENUM_CONSTANT_DECL]

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

            self.tu_module = cindex.TranslationUnit
            self.tu = None
            # check if we can build an index. If not, set valid to false
            try:
                cindex.Index.create()
                self.valid = True
            except Exception as e:
                log.error(" error: %s", e)
                self.valid = False

    def parse_tu(self, view):
        """Initialize the completer. Builds the view.

        Args:
            view (sublime.View): current view
        """
        # Return early if this is an invalid view.
        if not Tools.is_valid_view(view):
            return

        file_name = view.file_name()
        file_body = view.substr(sublime.Region(0, view.size()))

        # initialize unsaved files
        files = [(file_name, file_body)]

        # flags are loaded by base completer already
        log.debug(" clang flags are: %s", self.clang_flags)
        v_id = view.buffer_id()
        if v_id == 0:
            log.warning(" this is default id. View is closed. Abort!")
            return
        with Completer.rlock:
            try:
                TU = self.tu_module
                start = time.time()
                log.debug(" compilation started for view id: %s", v_id)
                trans_unit = TU.from_source(
                    filename=file_name,
                    args=self.clang_flags,
                    unsaved_files=files,
                    options=TU.PARSE_PRECOMPILED_PREAMBLE |
                    TU.PARSE_CACHE_COMPLETION_RESULTS)
                self.tu = trans_unit
                end = time.time()
                log.debug(" compilation done in %s seconds", end - start)
            except Exception as e:
                log.error(" error while compiling: %s", e)

    def complete(self, completion_request):
        """Called asynchronously to create a list of autocompletions.

        Using the current translation unit it queries libclang for the
        possible completions.

        """
        view = completion_request.get_view()
        file_body = view.substr(sublime.Region(0, view.size()))
        (row, col) = SublBridge.cursor_pos(
            view, completion_request.get_trigger_position())

        # unsaved files
        files = [(view.file_name(), file_body)]

        v_id = view.buffer_id()

        with Completer.rlock:
            # execute clang code completion
            start = time.time()
            log.debug(" started code complete for view %s", v_id)
            complete_obj = self.tu.codeComplete(
                view.file_name(),
                row, col,
                unsaved_files=files)
            end = time.time()
            log.debug(" code complete done in %s seconds", end - start)

        if complete_obj is None or len(complete_obj.results) == 0:
            completions = []
        else:
            point = completion_request.get_trigger_position()
            trigger = view.substr(point - 2) + view.substr(point - 1)
            if trigger != "::":
                excluded = self.ignore_list
            else:
                excluded = self.ignore_list[:-1]
            completions = Completer._parse_completions(complete_obj, excluded)
        log.debug(' completions: %s' % completions)
        return (completion_request, completions)

    def update(self, view, show_errors):
        """Reparse the translation unit.

        This speeds up completions significantly, so we perform this upon file
        save.

        Args:
            view (sublime.View): current view
            show_errors (bool): if true - highlight compile errors

        Returns:
            bool: reparsed successfully

        """
        v_id = view.buffer_id()
        log.debug(" view is %s", v_id)
        with Completer.rlock:
            if not self.tu:
                log.debug(" translation unit does not exist. Creating.")
                self.parse_tu(view)
            log.debug(" reparsing translation_unit for view %s", v_id)
            start = time.time()
            self.tu.reparse()
            end = time.time()
            log.debug(" reparsed in %s seconds", end - start)
            if show_errors:
                self.show_errors(view, self.tu.diagnostics)
            return True
        log.error(" no translation unit for view id %s", v_id)
        return False

    @staticmethod
    def _cindex_for_version(version):
        """Get cindex module name from version string.

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
    def _is_valid_result(completion_result, excluded_kinds):
        """Check if completion is valid.

           Remove excluded types and unaccessible members.

        Args:
            completion_result (): completion result from libclang
            excluded_kinds (list): list of CursorKind types that shouldn't be
                                   added to completion list

        Returns:
            boolean: True if completion should be added to completion list
        """
        if str(completion_result.string.availability) != "Available":
            return False
        try:
            if completion_result.kind in excluded_kinds:
                return False
        except ValueError as e:
            log.error(" error: %s", e)
        return True

    @staticmethod
    def _parse_completions(complete_results, excluded):
        """Create snippet-like structures from a list of completions.

        Args:
            complete_results (list): raw completions list
            excluded (list): list of excluded classes of completions

        Returns:
            list: updated completions
        """
        completions = []

        # sort results according to their clang based priority
        sorted_results = sorted(complete_results.results,
                                key=lambda x: x.string.priority)

        for c in sorted_results:
            if not Completer._is_valid_result(c, excluded):
                continue
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
