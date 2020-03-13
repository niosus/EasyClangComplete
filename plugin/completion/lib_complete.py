"""Contains class for libclang based completions.

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
from ..utils.clang_utils import ClangUtils
from ..utils.subl.subl_bridge import SublBridge
from ..utils.subl.row_col import ZeroIndexedRowCol
from ..utils.subl.row_col import OneIndexedRowCol
from ..error_vis.popups import Popup

from threading import RLock
from os import path

log = logging.getLogger("ECC")

# Triggers that should show types.
GLOBAL_TRIGGERS = [":", "\t", " "]
# All symbols that can be part of a valid trigger.
ALLOWED_TRIGGER_SYMBOLS = [":", " ", "\t", ".", "-", ">"]


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
            cindex_module_name = ClangUtils.get_cindex_module_for_version(
                self.version_str)

            if not cindex_module_name:
                log.critical("No cindex module for clang version: %s",
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
                libclang_dir, libclang_file = ClangUtils.find_libclang(
                    settings.clang_binary,
                    settings.libclang_path,
                    settings.clang_version)
                if libclang_dir:
                    self.cindex.Config.set_library_file(libclang_file)
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
        if not SublBridge.is_valid_view(view):
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
        row_col = ZeroIndexedRowCol.from_1d_location(
            view, completion_request.get_trigger_position())
        file_row_col = OneIndexedRowCol.from_zero_indexed(row_col)

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
                    file_row_col.row, file_row_col.col,
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
            log.debug("Current trigger: '%s'", trigger)
            # We clean trigger from all symbols that cannot be part of one.
            sanitized_trigger = ''.join(
                [c for c in trigger if c in ALLOWED_TRIGGER_SYMBOLS])
            log.debug("Current sanitized_trigger: '%s'", sanitized_trigger)
            if sanitized_trigger not in GLOBAL_TRIGGERS:
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
        objc_types = [
            self.cindex.CursorKind.OBJC_MESSAGE_EXPR,
            self.cindex.CursorKind.OBJC_CLASS_METHOD_DECL,
            self.cindex.CursorKind.OBJC_INSTANCE_METHOD_DECL,
            self.cindex.CursorKind.OBJC_CATEGORY_DECL,
            self.cindex.CursorKind.OBJC_INTERFACE_DECL,
            self.cindex.CursorKind.OBJC_PROTOCOL_DECL,
            self.cindex.CursorKind.OBJC_CATEGORY_IMPL_DECL,
            self.cindex.CursorKind.OBJC_IMPLEMENTATION_DECL,
            self.cindex.CursorKind.OBJC_CLASS_REF,
            self.cindex.CursorKind.OBJC_PROTOCOL_REF,
        ]
        empty_info = (tooltip_request, None)
        with Completer.rlock:
            if not self.tu:
                return empty_info
            view = tooltip_request.get_view()
            row_col = ZeroIndexedRowCol.from_1d_location(
                view, tooltip_request.get_trigger_position())
            file_row_col = OneIndexedRowCol.from_zero_indexed(row_col)

            cursor = self.tu.cursor.from_location(
                self.tu,
                self.tu.get_location(
                    view.file_name(), (file_row_col.row, file_row_col.col)))
            if not cursor:
                return empty_info
            if cursor.kind in objc_types:
                info_popup = Popup.info_objc(cursor, self.cindex, settings)
                return tooltip_request, info_popup
            if cursor.referenced:
                info_popup = Popup.info(
                    cursor.referenced, self.cindex, settings)
                return tooltip_request, info_popup
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

            # Prepare unsaved files.
            file_name = view.file_name()
            file_body = view.substr(sublime.Region(0, view.size()))
            unsaved_files = [(file_name, file_body)]

            start = time.time()
            self.tu.reparse(unsaved_files=unsaved_files)
            end = time.time()
            log.debug("reparsed in %s seconds", end - start)
            # Store and potentially show errors to the user.
            self.save_errors(self.tu.diagnostics)  # Store for the future.
            if settings.show_errors:
                self.show_errors(view)
            return True
        log.error("no translation unit for view id %s", v_id)
        return False

    def get_declaration_location(self, view, row_col):
        """Get location of declaration from given location in file."""
        file_row_col = OneIndexedRowCol.from_zero_indexed(row_col)
        with Completer.rlock:
            if not self.tu:
                return None
            cursor = self.tu.cursor.from_location(
                self.tu, self.tu.get_location(view.file_name(),
                                              file_row_col.as_tuple()))
            ref_new = None
            if cursor and cursor.referenced:
                ref = cursor.referenced
                if cursor.kind.is_declaration():
                    ref_new = ref.get_definition()
                return (ref_new or ref).location
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
