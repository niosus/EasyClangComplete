"""Incapsulate popup creation."""

import sublime
import mdpopups
import markupsafe
import logging

from ..utils.macro_parser import MacroParser

POPUP_CSS_FILE = "Packages/EasyClangComplete/plugin/popups/popup.css"

log = logging.getLogger("ECC")

MD_TEMPLATE = """\
---
allow_code_wrap: true
---
!!! {type}
    {contents}
"""

CODE_TEMPLATE = """```{lang}
{code}
```"""

DECLARATION_TEMPLATE = """## Declaration: ##
{type_declaration}
"""

BRIEF_DOC_TEMPLATE = """### Brief documentation: ###
{content}
"""

FULL_DOC_TEMPLATE = """### Full doxygen comment: ###
{content}
"""

BODY_TEMPLATE = """### Body: ###
{content}
"""


def log_location(location, name):
    """Log info about a cindex.SourceLocation."""
    if location is None:
        log.debug("%s: none" % name)
        return
    log.debug("%s" % str(location))
    file_name = "none"
    if location.file and location.file.name:
        file_name = location.file.name
    log.debug("%s: file: %s" % (name, file_name))
    log.debug("%s: line: %u" % (name, location.line))
    log.debug("%s: col: %u" % (name, location.column))


def log_type(clang_type, name):
    """Log info about a cindex.Type."""
    if clang_type is None:
        log.debug("%s: none" % name)
        return
    log.debug("%s" % str(clang_type))
    log.debug("%s.kind: %s" % (name, clang_type.kind))
    log_location(Popup.location_from_type(clang_type), "%s.location" % name)
    log.debug("%s.spelling: %s" % (name, clang_type.spelling or "none"))
    num_template_arguments = clang_type.get_num_template_arguments()
    log.debug("%s.get_num_template_arguments(): %i" % (
        name, num_template_arguments))
    if num_template_arguments != -1:
        for arg_index in range(num_template_arguments):
            templ_type = clang_type.get_template_argument_type(arg_index)
            log.debug("%s.template_argument[%i].spelling: %s" % (
                name, arg_index, templ_type.spelling))
            log_location(Popup.location_from_type(templ_type),
                         "%s.template_argument[%i].location" % (
                         name, arg_index))
    log.debug("%s.get_declaration().get_num_template_arguments(): %i" % (
        name,
        clang_type.get_declaration().get_num_template_arguments()))
    log.debug("%s.get_declaration().spelling: %s" % (
        name,
        clang_type.get_declaration().spelling))


def log_cursor(cursor, name):
    """Log info about a cindex.Cursor."""
    if cursor is None:
        log.debug("%s: none" % name)
        return
    log.debug("%s.kind: %s" % (name, cursor.kind))
    log.debug("%s.spelling: %s" % (name, cursor.spelling or "none"))
    log.debug("%s.displayname: %s" % (name, cursor.displayname or "none"))
    log.debug("%s.get_usr(): %s" % (name, cursor.get_usr() or "none"))
    log.debug("%s.is_definition(): %s" % (name, cursor.is_definition()))
    # I've never seen this 'num_template_args' be anything other than -1.
    num_template_args = cursor.get_num_template_arguments()
    log.debug("%s.get_num_template_arguments(): %i" % (name, num_template_args))
    log_type(cursor.type, "%s.type" % name)
    log_type(cursor.result_type, "%s.result_type" % name)
    log_location(cursor.location, "%s.location" % name)
    log.debug("%s.extent: %r" % (name, cursor.extent or "none"))


def log_extent(extent, name):
    """Log info about a cindex.SourceRange."""
    if extent is None:
        log.debug("%s: none" % name)
        return
    if extent and extent.start and extent.start.file:
        log.debug("%s.start.file.name: %s" % (name, extent.start.file.name))
        log.debug("%s.start.line: %i" % (name, extent.start.line))
        log.debug("%s.end.file.name: %s" % (name, extent.end.file.name))
        log.debug("%s.start.end.line: %i" % (name, extent.end.line))
    else:
        log.debug("%s.start.file.name: none" % name)
        log.debug("%s.start.line: none" % name)
        log.debug("%s.end.file.name: none" % name)
        log.debug("%s.start.end.line: none" % name)


class Popup:
    """Incapsulate popup creation."""

    WRAPPER_CLASS = "ECC"

    def __init__(self, max_dimensions):
        """ Initialize basic needs. 'max_dimensions' is a tuple of
        (maximum_width, maximum_height) in pixels.
        """
        self.CSS = sublime.load_resource(POPUP_CSS_FILE)
        self.max_width, self.max_height = max_dimensions

    @staticmethod
    def error(text, settings):
        """Initialize a new error popup."""
        popup = Popup((settings.popup_maximum_width, settings.popup_maximum_height))
        popup.__popup_type = 'panel-error "ECC: Error"'
        popup.__text = markupsafe.escape(text)
        return popup

    @staticmethod
    def warning(text, settings):
        """Initialize a new warning popup."""
        popup = Popup((settings.popup_maximum_width, settings.popup_maximum_height))
        popup.__popup_type = 'panel-warning "ECC: Warning"'
        popup.__text = markupsafe.escape(text)
        return popup

    @staticmethod
    def declaration_for_type(clang_type, cindex, expand_template_types):
        """Get declaration for a cindex.Type.

        Includes a hyperlink to the type's definition, and, if type
        has template parameters, to the the definitions of each
        template paremeter's type too.
        """
        if clang_type.kind == cindex.TypeKind.POINTER:
            pointee_type = clang_type.get_pointee()
            pointee_text = Popup.declaration_for_type(pointee_type, cindex,
                                                      expand_template_types)
            return pointee_text + ' \\*'
        if clang_type.kind == cindex.TypeKind.LVALUEREFERENCE:
            referee_type = clang_type.get_pointee()
            referee_text = Popup.declaration_for_type(referee_type, cindex,
                                                      expand_template_types)
            return referee_text + ' &'
        if clang_type.spelling is None or clang_type.spelling == "":
            # This happens, for example, when using an integer literal as
            # a template parameter, e.g. in 'std::array<Foo, 5> fooArray;',
            # when hovering over fooArray, we iterate through
            # fooArray's template arguments, but the argument for '5' has
            # None for spelling.
            # For now, just show a placeholder 'unknown' message because
            # we can't easily determine what to show here.
            # @todo: In the future, we could find a way to parse this and
            # correctly show '5' instead of 'unknown'.
            # cursor.spelling for 'fooArray' is the text 'std::array<Foo, 5>'.
            # We generally ignore cursor.spelling here because iterating
            # through template types lets us put a hyperlink to Foo's
            # definition. With more effort, we could parse the '5' out of
            # cursor.spelling and insert that here.
            return "*ECC: unknown*"  # in italics

        num_template_args = clang_type.get_num_template_arguments()
        declaration_text = ''
        if not expand_template_types or num_template_args <= 0:
            # Just link to the type
            declaration_text += Popup.link_from_location(
                Popup.location_from_type(clang_type),
                clang_type.spelling,
                trailing_space=False)
        else:
            # Link-ify the class and all the class's template parameters.
            # e.g. 'link to std::shared_ptr'<'link to Foo'>
            spelling_without_template = clang_type.spelling.split('<')[0]
            declaration_text += Popup.link_from_location(
                Popup.location_from_type(clang_type),
                spelling_without_template,
                trailing_space=False)
            declaration_text += '<'
            for arg_index in range(num_template_args):
                templ_type = clang_type.get_template_argument_type(arg_index)
                declaration_text += Popup.declaration_for_type(
                    templ_type,
                    cindex,
                    expand_template_types)
                if arg_index + 1 != num_template_args:
                    declaration_text += ", "
            declaration_text += '>'
        return declaration_text

    @staticmethod
    def info(cursor, cindex, settings):
        """Initialize a new warning popup."""
        popup = Popup((settings.popup_maximum_width, settings.popup_maximum_height))
        popup.__popup_type = 'panel-info "ECC: Info"'
        is_type_decl = cursor.kind in [
            cindex.CursorKind.STRUCT_DECL,
            cindex.CursorKind.UNION_DECL,
            cindex.CursorKind.CLASS_DECL,
            cindex.CursorKind.ENUM_DECL,
            cindex.CursorKind.TYPEDEF_DECL,
            cindex.CursorKind.TYPE_ALIAS_DECL,
            cindex.CursorKind.TYPE_REF
        ]
        is_macro = cursor.kind == cindex.CursorKind.MACRO_DEFINITION
        is_class_template = cursor.kind == cindex.CursorKind.CLASS_TEMPLATE

        # Show the return type of the function/method if applicable,
        # macros just show that they are a macro.
        macro_parser = None
        body_cursor = None
        if is_type_decl:
            body_cursor = cursor
        elif is_class_template:
            body_cursor = cursor.get_definition()

        # Initialize the text the declaration.
        declaration_text = ''
        if is_macro:
            macro_parser = MacroParser(cursor.spelling, cursor.location)
            declaration_text += r'\#define '
        else:
            if cursor.result_type.spelling:
                result_type = cursor.result_type
            elif cursor.type.spelling:
                result_type = cursor.type
            else:
                result_type = None
            if cursor.is_static_method():
                declaration_text += "static "
            result_type_not_none = result_type is not None
            if result_type_not_none and cursor.spelling != cursor.type.spelling:
                # Don't show duplicates if the user focuses type, not variable
                declaration_text += Popup.declaration_for_type(
                    result_type,
                    cindex,
                    settings.expand_template_types)
                declaration_text += " "
        # Link to declaration of item under cursor
        if cursor.location:
            declaration_text += Popup.link_from_location(cursor.location,
                                                         cursor.spelling)
        else:
            declaration_text += cursor.spelling
        # Macro/function/method arguments
        args_string = None
        if is_macro:
            # cursor.get_arguments() doesn't give us anything for macros,
            # so we have to parse those ourselves
            args_string = macro_parser.args_string
        else:
            args = []
            for arg in cursor.get_arguments():
                arg_type_decl = Popup.declaration_for_type(
                    arg.type,
                    cindex,
                    settings.expand_template_types)
                if arg.spelling:
                    args.append(arg_type_decl + " " + arg.spelling)
                else:
                    args.append(arg_type_decl)
            if cursor.kind in [cindex.CursorKind.FUNCTION_DECL,
                               cindex.CursorKind.CXX_METHOD,
                               cindex.CursorKind.CONSTRUCTOR,
                               cindex.CursorKind.DESTRUCTOR,
                               cindex.CursorKind.CONVERSION_FUNCTION,
                               cindex.CursorKind.FUNCTION_TEMPLATE]:
                args_string = '('
                if len(args):
                    args_string += ', '.join(args)
                args_string += ')'
        if args_string:
            declaration_text += args_string
        # Show value for enum
        if cursor.kind == cindex.CursorKind.ENUM_CONSTANT_DECL:
            declaration_text += " = " + str(cursor.enum_value)
            declaration_text += "(" + hex(cursor.enum_value) + ")"
        # Method modifiers
        if cursor.is_const_method():
            declaration_text += " const"
        # Save declaration text.
        popup.__text = DECLARATION_TEMPLATE.format(
            type_declaration=markupsafe.escape(declaration_text))
        # Doxygen comments
        if cursor.brief_comment:
            popup.__text += BRIEF_DOC_TEMPLATE.format(
                content=CODE_TEMPLATE.format(lang="",
                                             code=cursor.brief_comment))
        if cursor.raw_comment:
            clean_comment = Popup.cleanup_comment(cursor.raw_comment).strip()
            print(clean_comment)
            if clean_comment:
                # Only add this if there is a Doxygen comment.
                popup.__text += FULL_DOC_TEMPLATE.format(
                    content=CODE_TEMPLATE.format(lang="", code=clean_comment))
        # Show macro body
        if is_macro:
            popup.__text += BODY_TEMPLATE.format(
                content=CODE_TEMPLATE.format(lang="c++",
                                             code=macro_parser.body_string))
        # Show type declaration
        if settings.show_type_body and body_cursor and body_cursor.extent:
            body = Popup.get_text_by_extent(body_cursor.extent)
            body = Popup.prettify_body(body)
            popup.__text += BODY_TEMPLATE.format(
                content=CODE_TEMPLATE.format(lang="c++", code=body))
        return popup

    def as_markdown(self):
        """Represent all the text as markdown."""
        tabbed_text = "\n    ".join(self.__text.split('\n')).strip()
        return MD_TEMPLATE.format(type=self.__popup_type,
                                  contents=tabbed_text)

    def show(self, view, location=-1, on_navigate=None):
        """Show this popup."""
        mdpopups.show_popup(view, self.as_markdown(),
                            max_width=self.max_width,
                            max_height=self.max_height,
                            wrapper_class=Popup.WRAPPER_CLASS,
                            css=self.CSS,
                            flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY,
                            location=location,
                            on_navigate=on_navigate)

    @staticmethod
    def cleanup_comment(raw_comment):
        """Cleanup raw doxygen comment."""
        def pop_prepending_empty_lines(lines):
            first_non_empty_line_idx = 0
            for line in lines:
                if line == '':
                    first_non_empty_line_idx += 1
                else:
                    break
            return lines[first_non_empty_line_idx:]

        import string
        lines = raw_comment.split('\n')
        chars_to_strip = '/' + '*' + string.whitespace
        lines = [line.lstrip(chars_to_strip) for line in lines]
        lines = pop_prepending_empty_lines(lines)
        clean_lines = []
        is_brief_comment = True
        for line in lines:
            if line == '' and is_brief_comment:
                # Skip lines that belong to brief comment.
                is_brief_comment = False
                continue
            if is_brief_comment:
                continue
            clean_lines.append(line)
        return '\n'.join(clean_lines)

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
    def link_from_location(location, text, trailing_space=True):
        """Provide link to given cursor.

        Transforms SourceLocation object into markdown string.

        Args:
            location (Cursor.location): Current location.
            text (str): Text to be added as info.
            trailing_space (bool): Whether to add a trailing space
                For C/C++ method & argument names, this would normally be true,
                but ObjC methods/arguments are usually presented without
                this space.
        """
        result = ""
        if location and location.file and location.file.name:
            result += "[" + text + "]"
            result += "(" + location.file.name
            result += ":" + str(location.line)
            result += ":" + str(location.column)
            result += ")"
        else:
            result += text
        if trailing_space:
            result += " "
        return result

    @staticmethod
    def get_text_by_extent(extent):
        """Load lines of code in range, pointed by extent.

        Args:
            extent (Cursor.extent): Ranges of source file.
        """
        if extent.start.file.name != extent.end.file.name:
            return None

        with open(extent.start.file.name, 'r', encoding='utf-8',
                  errors='ignore') as f:
            lines = f.readlines()
            return "".join(lines[extent.start.line - 1:extent.end.line])

    @staticmethod
    def prettify_body(body):
        """Format some declaration body for viewing.

        Args:
            body (str): Body text.
        """
        # remove any global indentation
        import textwrap
        body = textwrap.dedent(body)

        return body

    def info_objc(cursor, cindex, settings):
        """Provide information about Objective C cursors."""
        popup = Popup((settings.popup_maximum_width, settings.popup_maximum_height))
        popup.__popup_type = 'panel-info "ECC: Info"'
        is_message = cursor.kind in [
            cindex.CursorKind.OBJC_MESSAGE_EXPR,
        ]
        is_method_decl = cursor.kind in [
            cindex.CursorKind.OBJC_CLASS_METHOD_DECL,
            cindex.CursorKind.OBJC_INSTANCE_METHOD_DECL,
        ]
        is_type_decl = cursor.kind in [
            cindex.CursorKind.OBJC_CATEGORY_DECL,
            cindex.CursorKind.OBJC_INTERFACE_DECL,
            cindex.CursorKind.OBJC_PROTOCOL_DECL,
        ]
        is_type_impl = cursor.kind in [
            cindex.CursorKind.OBJC_CATEGORY_IMPL_DECL,
            cindex.CursorKind.OBJC_IMPLEMENTATION_DECL,
        ]
        is_type_ref = cursor.kind in [
            cindex.CursorKind.OBJC_CLASS_REF,
            cindex.CursorKind.OBJC_PROTOCOL_REF,
        ]
        comment_cursor = None
        type_body_cursor = None
        method_cursor = None
        return_type = None
        location_cursor = None
        if is_message:
            location_cursor = cursor
            comment_cursor = cursor.referenced
            method_cursor = cursor.referenced
            return_type = cursor.type
        elif is_method_decl:
            location_cursor = cursor
            comment_cursor = cursor.referenced
            method_cursor = cursor.referenced
            return_type = cursor.result_type
        elif is_type_decl:
            location_cursor = cursor
            comment_cursor = cursor
            type_body_cursor = cursor
        elif is_type_impl:
            location_cursor = cursor.canonical
            comment_cursor = cursor.canonical
            type_body_cursor = cursor.canonical
        elif is_type_ref:
            location_cursor = cursor
            comment_cursor = cursor.referenced
            type_body_cursor = cursor.referenced
            location_cursor = cursor.referenced
        else:
            assert False, "Unexpected type"

        declaration_text = ""
        if method_cursor:
            # <+ or ->(<return type>)
            method_kind = method_cursor.kind
            if method_kind == cindex.CursorKind.OBJC_INSTANCE_METHOD_DECL:
                declaration_text += "-("
            elif method_kind == cindex.CursorKind.OBJC_CLASS_METHOD_DECL:
                declaration_text += "+("
            declaration_text += Popup.link_from_location(
                Popup.location_from_type(return_type),
                return_type.spelling or "",
                trailing_space=False)
            declaration_text += ')'

            # <method name>
            method_and_params = method_cursor.spelling.split(':')
            method_name = method_and_params[0]
            if method_cursor.location:
                declaration_text += Popup.link_from_location(
                    method_cursor.location,
                    method_name,
                    trailing_space=False)
            else:
                declaration_text += method_cursor.spelling

            # <args if they exist>
            method_params_index = 1
            for arg in method_cursor.get_arguments():
                arg_type_location = Popup.location_from_type(arg.type)
                arg_type_link = Popup.link_from_location(arg_type_location,
                                                         arg.type.spelling,
                                                         trailing_space=False)
                declaration_text += ":(" + arg_type_link + ")"
                if arg.spelling:
                    declaration_text += arg.spelling + " "
                declaration_text += method_and_params[method_params_index]
                method_params_index += 1
        else:
            if location_cursor.location:
                declaration_text += Popup.link_from_location(
                    location_cursor.location,
                    location_cursor.spelling)
            else:
                declaration_text += location_cursor.spelling
        popup.__text = DECLARATION_TEMPLATE.format(
            type_declaration=markupsafe.escape(declaration_text))

        if comment_cursor and comment_cursor.brief_comment:
            popup.__text += BRIEF_DOC_TEMPLATE.format(
                content=CODE_TEMPLATE.format(lang="",
                                             code=comment_cursor.brief_comment))
        if comment_cursor and comment_cursor.raw_comment:
            clean_comment = Popup.cleanup_comment(comment_cursor.raw_comment)
            clean_comment = clean_comment.strip()
            if clean_comment:
                # Only add this if there is a Doxygen comment.
                popup.__text += FULL_DOC_TEMPLATE.format(
                    content=CODE_TEMPLATE.format(lang="", code=clean_comment))

        # Show type declaration
        if type_body_cursor:
            if settings.show_type_body and type_body_cursor.extent:
                body = Popup.get_text_by_extent(type_body_cursor.extent)
                popup.__text += BODY_TEMPLATE.format(
                    content=CODE_TEMPLATE.format(
                        lang="objective-c++",
                        code=body))
        return popup
