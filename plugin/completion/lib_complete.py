"""This module contains class for libclang based completions.

Attributes:
    cindex_dict (dict): dict of cindex entries for each version of clang
    log (logging.Logger): logger for this module
"""
import importlib
import sublime
import time
import logging
import html

from .base_complete import BaseCompleter
from .compiler_variant import LibClangCompilerVariant
from ..tools import Tools
from ..tools import SublBridge
from ..tools import PKG_NAME

from threading import RLock
from os import path

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
            self.default_ignore_list = [cindex.CursorKind.DESTRUCTOR]
            self.bigger_ignore_list = self.default_ignore_list +\
                [cindex.CursorKind.CLASS_DECL,
                 cindex.CursorKind.ENUM_CONSTANT_DECL]

            self.function_kinds_list = [cindex.CursorKind.FUNCTION_DECL,
                                        cindex.CursorKind.CXX_METHOD]

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
            start = time.time()
            try:
                TU = self.tu_module
                log.debug(" compilation started for view id: %s", v_id)
                if not file_name or not path.exists(file_name):
                    raise ValueError("file name does not exist anymore")
                trans_unit = TU.from_source(
                    filename=file_name,
                    args=self.clang_flags,
                    unsaved_files=files,
                    options=TU.PARSE_PRECOMPILED_PREAMBLE |
                    TU.PARSE_CACHE_COMPLETION_RESULTS |
                    TU.PARSE_INCLUDE_BRIEF_COMMENTS_IN_CODE_COMPLETION)
                self.tu = trans_unit
            except Exception as e:
                log.error(" error while compiling: %s", e)
            end = time.time()
            log.debug(" compilation done in %s seconds", end - start)

    def complete(self, completion_request):
        """Called asynchronously to create a list of autocompletions.

        Using the current translation unit it queries libclang for the
        possible completions.

        """
        view = completion_request.get_view()
        file_name = view.file_name()
        file_body = view.substr(sublime.Region(0, view.size()))
        (row, col) = SublBridge.cursor_pos(
            view, completion_request.get_trigger_position())

        # unsaved files
        files = [(file_name, file_body)]

        v_id = view.buffer_id()

        with Completer.rlock:
            # execute clang code completion
            start = time.time()
            log.debug(" started code complete for view %s", v_id)
            try:
                if not file_name or not path.exists(file_name):
                    raise ValueError("file name does not exist anymore")
                complete_obj = self.tu.codeComplete(
                    file_name,
                    row, col,
                    unsaved_files=files)
            except Exception as e:
                log.error(" error while completing view %s: %s", file_name, e)
                complete_obj = None
            end = time.time()
            log.debug(" code complete done in %s seconds", end - start)

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
        log.debug(' completions: %s' % completions)
        return (completion_request, completions)

    @staticmethod
    def location_from_type(clangType):
        """ Return location from type.

            Return proper location from type.
            Remove all inderactions like pointers etc.

        """
        cursor = clangType.get_declaration()
        if cursor and cursor.location and cursor.location.file:
            return cursor.location

        cursor = clangType.get_pointee().get_declaration()
        if cursor and cursor.location and cursor.location.file:
            return cursor.location

        return None

    @staticmethod
    def link_from_location(location, text):
        """Provide link to given cursor.

            Transforms SourceLocation object into html string

        """
        result = ""
        if location and location.file and location.file.name:
            result += "<a href=\""
            result += location.file.name
            result += ":"
            result += str(location.line)
            result += ":"
            result += str(location.column)
            result += "\">" + text + "</a>"
        else:
            result += text
        return result

    def build_info_details(self, cursor):
        """Provide information about given cursor.

        Builds detailed information about cursor.

        """
        result = ""
        if cursor.result_type.spelling:
            result += self.link_from_location(
                        self.location_from_type(cursor.result_type),
                        html.escape(cursor.result_type.spelling))
        elif cursor.type.spelling:
            result += self.link_from_location(
                        self.location_from_type(cursor.type),
                        html.escape(cursor.type.spelling))

        result += ' '

        if cursor.location:
            result += self.link_from_location(cursor.location,
                                              html.escape(cursor.spelling))
        else:
            result += html.escape(cursor.spelling)

        args = []
        for arg in cursor.get_arguments():
            if arg.spelling:
                args.append(arg.type.spelling + ' ' + arg.spelling)
            else:
                args.append(arg.type.spelling + ' ')

        if cursor.kind in self.function_kinds_list:
            result += '('
            if len(args):
                result += html.escape(', '.join(args))
            result += ')'

        if cursor.is_static_method():
            result = "static " + result
        if cursor.is_const_method():
            result += " const"

        if cursor.brief_comment:
            result += "<br><br><b>"
            result += cursor.brief_comment + "</b>"

        return result

    def info(self, tooltip_request):
        """Provide information about object in given location.

        Using the current translation unit it queries libclang for available
        information about cursor.

        """
        with Completer.rlock:
            if not self.tu:
                return (tooltip_request, "")
            view = tooltip_request.get_view()
            (row, col) = SublBridge.cursor_pos(
                view, tooltip_request.get_trigger_position())

            cur = self.tu.cursor.from_location(self.tu, self.tu.get_location(
                view.file_name(), (row, col)))
            result = ""
            if (cur and cur.kind.is_declaration() == False and
                cur.referenced and cur.referenced.kind.is_declaration()):
                result = self.build_info_details(cur.referenced)

        return (tooltip_request, result)

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
            # fix issue #191 - avoid crashing when renaming file
            if not self.tu or not self.tu.cursor.location.file:
                log.debug(" translation unit does not exist. Creating.")
                self.parse_tu(view)
            log.debug(" reparsing translation_unit for view %s", v_id)
            if not self.tu:
                log.error(" translation unit is not available. Not reparsing.")
                return False
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
            trigger = ''
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
