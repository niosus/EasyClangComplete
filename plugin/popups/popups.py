"""Incapsulate popup creation."""

import sublime
import mdpopups
import logging

from ..utils.macro_parser import MacroParser

POPUP_MD_FILE = "Packages/EasyClangComplete/plugin/popups/popup.md"
POPUP_CSS_FILE = "Packages/EasyClangComplete/plugin/popups/popup.css"

log = logging.getLogger("ECC")

CODE_TEMPLATE = """```{lang}
{code}
```
"""


class PopupStyle:
    """Enum with possible popup styles."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Popup:
    """Incapsulate popup creation."""

    WRAPPER_CLASS = "ECC"
    MAX_POPUP_WIDTH = 1800

    def __init__(self):
        """Initialize basic needs."""
        self.CSS = sublime.load_resource(POPUP_CSS_FILE)
        self.MD_TEMPLATE = sublime.load_resource(POPUP_MD_FILE)

    @staticmethod
    def error(text):
        """Initialize a new error popup."""
        popup = Popup()
        popup.__popup_type = 'panel-error "ECC: Error"'
        popup.__text = CODE_TEMPLATE.format(lang='', code=text)
        return popup

    @staticmethod
    def warning(text):
        """Initialize a new warning popup."""
        popup = Popup()
        popup.__popup_type = 'panel-warning "ECC: Warning"'
        popup.__text = CODE_TEMPLATE.format(lang='', code=text)
        return popup

    @staticmethod
    def info(cursor, cindex, settings):
        """Initialize a new warning popup."""
        popup = Popup()
        popup.__popup_type = 'panel-info "ECC: Info"'

        type_decl = [
            cindex.CursorKind.STRUCT_DECL,
            cindex.CursorKind.UNION_DECL,
            cindex.CursorKind.CLASS_DECL,
            cindex.CursorKind.ENUM_DECL,
            cindex.CursorKind.TYPEDEF_DECL,
            cindex.CursorKind.CLASS_TEMPLATE,
            cindex.CursorKind.TYPE_ALIAS_DECL,
            cindex.CursorKind.TYPE_REF
        ]

        popup.__text += '## Declaration: ##\n'

        # Show the return type of the function/method if applicable,
        # macros just show that they are a macro.
        macro_parser = None
        is_macro = cursor.kind == cindex.CursorKind.MACRO_DEFINITION
        is_type = cursor.kind in type_decl
        if is_macro:
            macro_parser = MacroParser(cursor.spelling, cursor.location)
            popup.__text += '#define '
        else:
            if cursor.result_type.spelling:
                result_type = cursor.result_type
            elif cursor.type.spelling:
                result_type = cursor.type
            else:
                result_type = None
                log.warning("No spelling for type provided in info.")
                return ""

            if cursor.is_static_method():
                popup.__text += "static "

            if cursor.spelling != cursor.type.spelling:
                # Don't show duplicates if the user focuses type, not variable
                popup.__text += Popup.link_from_location(
                    Popup.location_from_type(result_type),
                    result_type.spelling)

        # Link to declaration of item under cursor
        if cursor.location:
            popup.__text += Popup.link_from_location(cursor.location,
                                                     cursor.spelling)
        else:
            popup.__text += cursor.spelling

        # Macro/function/method arguments
        args_string = None
        if is_macro:
            # cursor.get_arguments() doesn't give us anything for macros,
            # so we have to parse those ourselves
            args_string = macro_parser.args_string
        else:
            args = []
            for arg in cursor.get_arguments():
                if arg.spelling:
                    args.append(arg.type.spelling + ' ' + arg.spelling)
                else:
                    args.append(arg.type.spelling + ' ')
            if cursor.kind in [cindex.CursorKind.FUNCTION_DECL,
                               cindex.CursorKind.CXX_METHOD]:
                args_string = '('
                if len(args):
                    args_string += ', '.join(args)
                args_string += ')'
        if args_string:
            popup.__text += args_string

        # Show value for enum
        if cursor.kind == cindex.CursorKind.ENUM_CONSTANT_DECL:
            popup.__text += " = " + str(cursor.enum_value)
            popup.__text += "(" + hex(cursor.enum_value) + ")"

        # Method modifiers
        if cursor.is_const_method():
            popup.__text += " const"

        # Show macro body
        if is_macro:
            popup.__text += CODE_TEMPLATE.format(
                lang="c++", code=macro_parser.body_string)

        # Show type declaration
        if settings.show_type_body and is_type and cursor.extent:
            body = Popup.get_text_by_extent(cursor.extent)
            popup.__text += CODE_TEMPLATE.format(lang="c++", code=body)

        # Doxygen comments
        if cursor.brief_comment:
            popup.__text += "## Brief documentation: ##\n"
            popup.__text += CODE_TEMPLATE.format(lang="",
                                                 code=cursor.brief_comment)

        if cursor.raw_comment:
            popup.__text += "## Full doxygen comment: ##\n"
            popup.__text += CODE_TEMPLATE.format(lang="",
                                                 code=cursor.raw_comment)

        return popup


    def show(self, view):
        """Show this popup."""

        contents = self.MD_TEMPLATE.format(type=self.__popup_type,
                                           code_style=self.__code_style,
                                           content=self.__text)
        mdpopups.show_popup(view, contents,
                            max_width=Popup.MAX_POPUP_WIDTH,
                            wrapper_class=Popup.WRAPPER_CLASS,
                            css=self.CSS)

    @staticmethod
    def location_from_type(clang_type):
        """Return location from type.

        Return proper location from type.
        Remove all inderactions like pointers etc.

        Args:
            clang_type (cindex.Type): clang type.

        """
        cursor = clang_type.get_declaration()
        if cursor and cursor.location and cursor.location.file:
            return cursor.location

        cursor = clang_type.get_pointee().get_declaration()
        if cursor and cursor.location and cursor.location.file:
            return cursor.location

        return None

    @staticmethod
    def link_from_location(location, text):
        """Provide link to given cursor.

        Transforms SourceLocation object into html string.

        Args:
            location (Cursor.location): Current location.
            text (str): Text to be added as info.
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
