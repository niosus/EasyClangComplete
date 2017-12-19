"""This module contains class for libclang based completions.

Attributes:
    cindex_dict (dict): dict of cindex entries for each version of clang.
    clang_utils_module_name (str): Name of the module for clang tools.
    log (logging.Logger): logger for this module.
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
from ..clang.utils import ClangUtils
from ..settings.settings_storage import SettingsStorage

from threading import RLock
from os import path

log = logging.getLogger("ECC")

cindex_dict = {
    '3.2': PKG_NAME + ".plugin.clang.cindex32",
    '3.3': PKG_NAME + ".plugin.clang.cindex33",
    '3.4': PKG_NAME + ".plugin.clang.cindex34",
    '3.5': PKG_NAME + ".plugin.clang.cindex35",
    '3.6': PKG_NAME + ".plugin.clang.cindex36",
    '3.7': PKG_NAME + ".plugin.clang.cindex37",
    '3.8': PKG_NAME + ".plugin.clang.cindex38",
    '3.9': PKG_NAME + ".plugin.clang.cindex39",
    '4.0': PKG_NAME + ".plugin.clang.cindex40",
    '5.0': PKG_NAME + ".plugin.clang.cindex50",
    '6.0': PKG_NAME + ".plugin.clang.cindex50",  # FIXME
}


class Completer(BaseCompleter):
    """Encapsulates completions based on libclang.

    Attributes:
        default_ignore_list (str[]): base list of cursor kinds to ignore
        bigger_ignore_list (str[]): extended list of cursor kinds to ignore.
            This list is used when completion is triggered with `::`.
        compiler_variant: Compiler variant currently in use.
        cindex (module): clang cindex.py module for the correct version
        rlock (threading.Rlock): recursive mutex
        tu (cindex.TranslationUnit): current translation unit
        valid (bool): Will be False if we fail to build proper clang index.
    """
    name = "lib"
    rlock = RLock()

    def __init__(self, settings, error_vis):
        """Initialize the Completer from clang binary, reading its version.

        Picks an according cindex for the found version.

        Args:
            settings (SettingStorage): object that stores current settings
            error_vis (ErrorVis): an object of error visualizer

        """
        super().__init__(settings, error_vis)

        # Create compiler options of specific variant of the compiler.
        self.compiler_variant = LibClangCompilerVariant()

        # init tu related variables
        with Completer.rlock:
            self.tu = None
            self.cindex = None

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
            log.debug("using bundled cindex: %s", cindex_module_name)
            self.cindex = importlib.import_module(cindex_module_name)

            # initialize ignore list to account for private methods etc.
            self.default_ignore_list = [self.cindex.CursorKind.DESTRUCTOR]
            self.bigger_ignore_list = self.default_ignore_list +\
                [self.cindex.CursorKind.CLASS_DECL,
                 self.cindex.CursorKind.ENUM_CONSTANT_DECL]

            # If we haven't already initialized the clang Python bindings, try
            # to figure out the path libclang.
            if not self.cindex.Config.loaded:
                # This will return something like /.../lib/clang/3.x.0
                libclang_dir = ClangUtils.find_libclang_dir(
                    settings.clang_binary,
                    settings.libclang_path,
                    settings.clang_version)
                if libclang_dir:
                    self.cindex.Config.set_library_path(libclang_dir)

            # check if we can build an index. If not, set valid to false
            try:
                self.cindex.Index.create()
                self.valid = True
            except Exception as e:
                log.error("error: %s", e)
                self.valid = False

    def parse_tu(self, view, settings):
        """Initialize the completer. Builds the view.

        Args:
            view (sublime.View): current view

        Raises:
            ValueError: if file name does not exist - throw exception.
        """
        # Return early if this is an invalid view.
        if not Tools.is_valid_view(view):
            return

        file_name = view.file_name()
        file_body = view.substr(sublime.Region(0, view.size()))

        unsaved_files = [(file_name, file_body)]

        # flags are loaded by base completer already
        log.debug("clang flags are: %s", self.clang_flags)
        v_id = view.buffer_id()
        if v_id == 0:
            log.warning(" this is default id. View is closed. Abort!")
            return
        with Completer.rlock:
            start = time.time()
            try:
                TU = self.cindex.TranslationUnit
                log.debug("compilation started for view id: %s", v_id)
                if not file_name or not path.exists(file_name):
                    raise ValueError("file name does not exist anymore")

                parse_options = \
                    (TU.PARSE_PRECOMPILED_PREAMBLE |
                     TU.PARSE_DETAILED_PROCESSING_RECORD |
                     TU.PARSE_INCLUDE_BRIEF_COMMENTS_IN_CODE_COMPLETION)
                if settings.use_libclang_caching:
                    parse_options |= TU.PARSE_CACHE_COMPLETION_RESULTS

                trans_unit = TU.from_source(
                    filename=file_name,
                    args=self.clang_flags,
                    unsaved_files=unsaved_files,
                    options=parse_options)
                self.tu = trans_unit
                self.save_errors(self.tu.diagnostics)  # Store for the future.
            except Exception as e:
                log.error("error while compiling: %s", e)
            end = time.time()
            log.debug("compilation done in %s seconds", end - start)

    def complete(self, completion_request):
        """Create a list of autocompletions. Called asynchronously.

        Using the current translation unit it queries libclang for the
        possible completions.

        Args:
            completion_request (tools.ActionRequest): completion request
                holding information about the view and needed location.

        Raises:
            ValueError: if file name does not exist - throw exception.

        """
        view = completion_request.get_view()
        file_name = view.file_name()
        file_body = view.substr(sublime.Region(0, view.size()))
        (row, col) = SublBridge.cursor_pos(
            view, completion_request.get_trigger_position())

        # unsaved files
        unsaved_files = [(file_name, file_body)]

        v_id = view.buffer_id()

        with Completer.rlock:
            # execute clang code completion
            start = time.time()
            log.debug("started code complete for view %s", v_id)
            try:
                if not file_name or not path.exists(file_name):
                    raise ValueError("file name does not exist anymore")
                if int(self.version_str[0]) > 3:
                    log.debug("using newer version of clang: %s",
                              self.version_str)
                    # It is important to set this option for clang 4.0 as
                    # there is an assert in ASTUnit.cpp that checks if this
                    # flag corresponds to the one that was used for building
                    # the translation unit. As we use it to create the unit,
                    # we need it here too. See issue #230.
                    include_brief_comments = True
                else:
                    log.debug("using older version of clang: %s",
                              self.version_str)
                    # To avoid breaking compatibility with old versions of
                    # clang, where the assert is different, we make sure to
                    # pass False if the version is older. See issue #245.
                    include_brief_comments = False
                complete_obj = self.tu.codeComplete(
                    file_name,
                    row, col,
                    unsaved_files=unsaved_files,
                    include_macros=True,
                    include_brief_comments=include_brief_comments)
            except Exception as e:
                log.error("error while completing view %s: %s", file_name, e)
                complete_obj = None
            end = time.time()
            log.debug("code complete done in %s seconds", end - start)

        if complete_obj is None or len(complete_obj.results) == 0:
            completions = []
        else:
            point = completion_request.get_trigger_position()
            trigger = view.substr(point - 2) + view.substr(point - 1)
            if trigger != "::":
                excluded = self.bigger_ignore_list
            else:
                excluded = self.default_ignore_list
            completions = Completer._parse_completions(complete_obj, excluded)
        log.debug('completions: %s' % completions)
        return (completion_request, completions)

    def info(self, tooltip_request, settings):
        """Provide information about object in given location.

        Using the current translation unit it queries libclang for available
        information about cursor.

        Args:
            tooltip_request (tools.ActionRequest): A request for action
                from the plugin.
            settings: All plugin settings.

        Returns:
            (tools.ActionRequest, str): completion request along with the
                info details read from the translation unit.

        """
        empty_info = (tooltip_request, None)
        with Completer.rlock:
            if not self.tu:
                return empty_info
            view = tooltip_request.get_view()
            (row, col) = SublBridge.cursor_pos(
                view, tooltip_request.get_trigger_position())

            cursor = self.tu.cursor.from_location(
                self.tu, self.tu.get_location(view.file_name(), (row, col)))
            if not cursor:
                return empty_info
            if cursor.kind == self.cindex.CursorKind.OBJC_MESSAGE_EXPR:
                info_details = ClangUtils.build_objc_message_info_details(
                    cursor)
                return (tooltip_request, info_details)
            if cursor.referenced:
                info_details = ClangUtils.build_info_details(
                    cursor.referenced, self.cindex, settings)
                return (tooltip_request, info_details)
            return empty_info

    def update(self, view, settings):
        """Reparse the translation unit.

        This speeds up completions significantly, so we perform this upon file
        save.

        Args:
            view (sublime.View): current view
            settings: ECC settings

        Returns:
            bool: reparsed successfully

        """
        v_id = view.buffer_id()
        log.debug("view is %s", v_id)
        with Completer.rlock:
            if not self.tu:
                log.debug("translation unit does not exist. Creating.")
                self.parse_tu(view, settings)
            if not self.tu:
                log.critical(" cannot create translation unit. Abort.")
                return False
            if isinstance(self.tu.cursor.displayname, bytes):
                # it is bytes, convert!
                log.debug("converting bytes '%s' into str",
                          self.tu.cursor.displayname)
                displayname = self.tu.cursor.displayname.decode('utf-8')
            else:
                # it is a normal string, no conversion needed
                displayname = self.tu.cursor.displayname
            if displayname != view.file_name():
                # In case the file was renamed, the translation unit still has
                # the old name in it and crashes the plugin host. We need to
                # completely recreate a translation unit if the filename has
                # changed. Addressed in issue #191.
                log.debug("translation unit file does not match view one")
                log.debug("names: '%s' vs '%s'",
                          displayname, view.file_name())
                log.debug("recreate translation unit completely")
                self.parse_tu(view, settings)
            log.debug("reparsing translation_unit for view %s", v_id)
            if not self.tu:
                log.error("translation unit is not available. Not reparsing.")
                return False
            start = time.time()
            self.tu.reparse()
            end = time.time()
            log.debug("reparsed in %s seconds", end - start)
            # Store and potentially show errors to the user.
            self.save_errors(self.tu.diagnostics)  # Store for the future.
            if settings.errors_style != SettingsStorage.NONE_STYLE:
                self.show_errors(view)
            return True
        log.error("no translation unit for view id %s", v_id)
        return False

    def get_declaration_location(self, view, row, col):
        """Get location of declaration from given location in file.

        Args:
            view (sublime.View): current view
            row (int): cursor row
            col (int): cursor col

        Returns:
            Location: location of declaration

        """
        with Completer.rlock:
            if not self.tu:
                return None
            cursor = self.tu.cursor.from_location(
                self.tu, self.tu.get_location(view.file_name(), (row, col)))
            ref_new = None
            if cursor and cursor.referenced:
                ref = cursor.referenced
                if cursor.kind.is_declaration():
                    ref_new = ref.get_definition()
                return (ref_new or ref).location
            return None

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
            completion_result: completion result from libclang
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
            log.error("error: %s", e)
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
            trigger = ''
            place_holders = 1
            for chunk in c.string:
                if not chunk:
                    continue
                if not chunk.spelling:
                    continue
                hint += chunk.spelling
                if chunk.isKindTypedText():
                    trigger += chunk.spelling
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
