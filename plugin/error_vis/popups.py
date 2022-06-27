"""Incapsulate popup creation."""

import string
import sublime
import mdpopups
import markupsafe
import logging
import re

from ..utils.macro_parser import MacroParser
from ..utils.index_location import IndexLocation

POPUP_CSS_FILE = "Packages/EasyClangComplete/plugin/error_vis/popup.css"

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

DECLARATION_TEMPLATE = """## Declaration:
{type_declaration}
"""

INDEX_REFERENCES_TEMPLATE = \
    """### References: <small><small>(from sublime index)</small></small>

{references}
"""

OPEN_FILES_REFERENCES_TEMPLATE = \
    """### References: <small><small>(from open files)</small></small>

{references}
"""

BRIEF_DOC_TEMPLATE = """### Brief documentation:
{content}
"""

FULL_DOC_TEMPLATE = """### Detailed documentation:
{content}
"""

BODY_TEMPLATE = """### Body:
{content}
"""


class Popup:
    """Incapsulate popup creation."""

    WRAPPER_CLASS = "ECC"

    def __init__(self, max_dimensions):
        """Initialize basic needs.

        'max_dimensions' is a tuple of (maximum_width, maximum_height) in
        pixels."""
        self.CSS = sublime.load_resource(POPUP_CSS_FILE)
        self.max_width, self.max_height = max_dimensions

    @staticmethod
    def error(text, settings):
        """Initialize a new error popup."""
        popup = Popup((
            settings.popup_maximum_width, settings.popup_maximum_height
        ))
        popup.__popup_type = 'panel-error "ECC: Error"'
        popup.__text = markupsafe.escape(text)
        return popup

    @staticmethod
    def warning(text, settings):
        """Initialize a new warning popup."""
        popup = Popup((
            settings.popup_maximum_width, settings.popup_maximum_height
        ))
        popup.__popup_type = 'panel-warning "ECC: Warning"'
        popup.__text = markupsafe.escape(text)
        return popup

    @staticmethod
    def info(cursor, cindex, settings):
        """Initialize a new warning popup."""
        popup = Popup((
            settings.popup_maximum_width, settings.popup_maximum_height
        ))
        popup.__popup_type = 'panel-info "ECC: Info"'

        macro_parser = None
        if cursor.kind == cindex.CursorKind.MACRO_DEFINITION:
            macro_parser = MacroParser(cursor.spelling, cursor.location)

        if not isinstance(settings.popup_sections, list):
            log.error("Bad config value: \"popup_sections\" " +
                      "should be a list of strings")
        elif len(settings.popup_sections) == 0:
            log.error("Bad config value: \"popup_sections\" " +
                      "setting should have at least one element")
        else:
            popup.__text = ""
            for i in settings.popup_sections:
                if not isinstance(i, str):
                    log.error("Bad config value: \"popup_sections\" " +
                              "should be a list containing only strings")
                elif re.match(r'[Dd]eclaration', i):
                    popup.__text += Popup.info_section_declaration(
                        cursor, cindex, settings, macro_parser)
                elif re.match(r'[Rr]eferences', i):
                    popup.__text += Popup.info_section_references(
                        cursor, cindex, settings, macro_parser)
                elif re.match(r'[Dd]ocumentation', i):
                    popup.__text += Popup.info_section_documentation(
                        cursor, cindex, settings, macro_parser)
                elif re.match(r'([Bb]ody|[Ss]ource)', i):
                    popup.__text += Popup.info_section_body(
                        cursor, cindex, settings, macro_parser)
                else:
                    log.error("Bad config value: \"popup_sections\" " +
                              "has unknown value: \"" + i + "\"")

        return popup

    @staticmethod
    def info_section_declaration(cursor, cindex, settings, macro_parser):
        """Generate the info text for the declaration."""
        is_function = cursor.kind in [
            cindex.CursorKind.FUNCTION_DECL,
            cindex.CursorKind.CXX_METHOD,
            cindex.CursorKind.CONSTRUCTOR,
            cindex.CursorKind.DESTRUCTOR,
            cindex.CursorKind.CONVERSION_FUNCTION,
            cindex.CursorKind.FUNCTION_TEMPLATE
        ]
        declaration_text = ''
        if macro_parser is not None:
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
                declaration_text += Popup._declaration_for_type(result_type,
                                                                cindex)
                declaration_text += " "
        # Link to declaration of item under cursor
        if cursor.location:
            declaration_text += Popup.link_from_location(cursor.location,
                                                         cursor.spelling)
        else:
            declaration_text += cursor.spelling
        # Macro/function/method arguments
        args_string = None
        if macro_parser is not None:
            # cursor.get_arguments() doesn't give us anything for macros,
            # so we have to parse those ourselves
            args_string = macro_parser.args_string
        else:
            args = []
            for arg in cursor.get_arguments():
                arg_type_decl = Popup._declaration_for_type(arg.type,
                                                            cindex)
                if arg.spelling:
                    args.append(arg_type_decl + " " + arg.spelling)
                else:
                    args.append(arg_type_decl)
            if is_function:
                is_variadic = False
                if (cursor.type is not None):
                    is_variadic = cursor.type.is_function_variadic()
                if is_variadic:
                    args.append("...")
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
        return DECLARATION_TEMPLATE.format(
            type_declaration=markupsafe.escape(declaration_text))

    @staticmethod
    def info_section_references(cursor, cindex, settings, macro_parser):
        """Generate the info text for the declaration."""
        window = sublime.active_window()
        spelling = cursor.spelling
        if not settings.show_index_references:
            return ""

        def lookup(lookup_function, spelling):
            index = lookup_function(spelling)
            references = []
            for location_tuple in index:
                location = IndexLocation(filename=location_tuple[0],
                                         line=location_tuple[2][0],
                                         column=location_tuple[2][1])
                references.append(
                    "{reference}: `{file}:{line}:{col}`".format(
                        reference=Popup.link_from_location(location, spelling),
                        file=location.file.short_name,
                        line=location.line,
                        col=location.column))
            return markupsafe.escape("\n - ".join(references))

        index_references = lookup(window.lookup_symbol_in_index, spelling)
        usage_references = lookup(window.lookup_symbol_in_open_files, spelling)
        output_text = ""
        if index_references:
            output_text += INDEX_REFERENCES_TEMPLATE.format(
                references=" - " + index_references)
        if usage_references:
            output_text += OPEN_FILES_REFERENCES_TEMPLATE.format(
                references=" - " + usage_references)
        return output_text

    @staticmethod
    def info_section_documentation(cursor, cindex, settings, macro_parser):
        """Generate text for documentation comment(s), if any."""
        documentation_text = ""
        has_comment = None
        if macro_parser is not None:
            has_comment = macro_parser.doc_string
        else:
            has_comment = cursor.raw_comment
        if has_comment:
            if settings.show_doc_as_markdown:
                # Doxygen comment: single-line brief description
                charset_comment = '/' + '*' + '!' + string.whitespace
                brief_comment = has_comment.split("\n")[0]
                brief_comment = brief_comment.lstrip(charset_comment)
                if len(brief_comment) > 0:
                    brief_comment = Popup.doxygen_comment(brief_comment)
                    documentation_text += BRIEF_DOC_TEMPLATE.format(
                        content=brief_comment)
                # Doxygen comment: multi-line detailed description
                mdcomment = Popup.cleanup_comment(has_comment)
                if len(mdcomment) > 0:
                    mdcomment = Popup.doxygen_comment(mdcomment)
                    # Only add this if there is a Doxygen comment.
                    documentation_text += FULL_DOC_TEMPLATE.format(
                        content=mdcomment)
            else:
                # Doxygen comment: single-line brief description
                if cursor.brief_comment:
                    documentation_text += BRIEF_DOC_TEMPLATE.format(
                        content=CODE_TEMPLATE.format(code=cursor.brief_comment,
                                                     lang=""))
                # Doxygen comment: multi-line detailed description
                if cursor.raw_comment:
                    clean_comment = Popup.cleanup_comment(has_comment).strip()
                    if clean_comment:
                        # Only add this if there is a Doxygen comment.
                        documentation_text += FULL_DOC_TEMPLATE.format(
                            content=CODE_TEMPLATE.format(code=clean_comment,
                                                         lang=""))
        log.debug("Processed comment:\n" + documentation_text)
        return documentation_text

    @staticmethod
    def info_section_body(cursor, cindex, settings, macro_parser):
        """Generate info text for the "body" section."""
        is_type_decl = cursor.kind in [
            cindex.CursorKind.STRUCT_DECL,
            cindex.CursorKind.UNION_DECL,
            cindex.CursorKind.CLASS_DECL,
            cindex.CursorKind.ENUM_DECL,
            cindex.CursorKind.TYPEDEF_DECL,
            cindex.CursorKind.TYPE_ALIAS_DECL,
            cindex.CursorKind.TYPE_REF
        ]
        is_function = cursor.kind in [
            cindex.CursorKind.FUNCTION_DECL,
            cindex.CursorKind.CXX_METHOD,
            cindex.CursorKind.CONSTRUCTOR,
            cindex.CursorKind.DESTRUCTOR,
            cindex.CursorKind.CONVERSION_FUNCTION,
            cindex.CursorKind.FUNCTION_TEMPLATE
        ]
        body_cursor = None
        if is_type_decl:
            body_cursor = cursor
        elif cursor.kind == cindex.CursorKind.CLASS_TEMPLATE:
            body_cursor = cursor.get_definition()
        body = ""
        # Show macro body
        if macro_parser is not None:
            body += "#define "
            body += cursor.spelling
            if (len(macro_parser.args_string) > 0):
                body += macro_parser.args_string
            else:
                body += " "
            body += macro_parser.body_string
        # Show function declaration
        elif settings.show_type_body and is_function:
            body += cursor.result_type.spelling
            body += " "
            body += cursor.spelling
            args = []
            for arg in cursor.get_arguments():
                if arg.spelling:
                    args.append(arg.type.spelling + " " + arg.spelling)
                else:
                    args.append(arg.type.spelling)
            if cursor.type is not None and cursor.type.is_function_variadic():
                args.append("...")
            body += '('
            if len(args):
                body += ', '.join(args)
            body += ');'
            body = Popup.prettify_body(body)
        # Show type declaration
        elif settings.show_type_body and body_cursor and body_cursor.extent:
            body = Popup.get_text_by_extent(body_cursor.extent)
            body = Popup.prettify_body(body)

        # Format into code block with syntax highlighting
        if len(body) > 0:
            return BODY_TEMPLATE.format(
                content=CODE_TEMPLATE.format(lang="c++", code=body))
        else:
            return ""

    def info_objc(cursor, cindex, settings):
        """Provide information about Objective C cursors."""
        popup = Popup((
            settings.popup_maximum_width, settings.popup_maximum_height
        ))
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

    @staticmethod
    def _declaration_for_type(clang_type,
                              cindex,
                              default_spelling=None):
        """Get declaration for a cindex.Type.

        Includes a hyperlink to the type's definition, and, if type
        has template parameters, to the the definitions of each
        template paremeter's type too.
        """
        if clang_type.kind == cindex.TypeKind.POINTER:
            pointee_type = clang_type.get_pointee()
            pointee_text = Popup._declaration_for_type(pointee_type, cindex)
            return pointee_text + ' \\*'
        if clang_type.kind == cindex.TypeKind.LVALUEREFERENCE:
            referee_type = clang_type.get_pointee()
            referee_text = Popup._declaration_for_type(referee_type, cindex)
            return referee_text + ' &'
        if clang_type.spelling is None or clang_type.spelling == "":
            # This happens, for example, when using an integer literal as
            # a template parameter, e.g. in 'std::array<Foo, 5> fooArray;',
            # when hovering over fooArray, we iterate through
            # fooArray's template arguments, but the argument for '5' has
            # None for spelling.
            # We show a default spelling here.
            return default_spelling

        num_template_args = clang_type.get_num_template_arguments()
        declaration_text = ''
        if num_template_args < 1:
            # Just link to the type
            log.debug('Number of template args is too low.')
            declaration_text += Popup.link_from_location(
                Popup.location_from_type(clang_type),
                clang_type.spelling,
                trailing_space=False)
            return declaration_text

        def parse_template_type_spelling(clang_type_spelling):
            type_name = clang_type_spelling.split('<')[0]
            args_match = re.search(r'<(.*)>', clang_type_spelling)
            if not args_match:
                log.debug('Cannot find template arguments in spelling.')
                return None, None
            arg_list = []
            args_str = args_match.group(1)
            regex = re.compile(r"(<[^<>]*>)")
            all_changes = []
            num_changes = 100
            # Remove parameters within template brackets: <...> until there are
            # no left. This is going to be the actual type we want to split at
            # this step.
            # For example: "<int, A<int, float>>" will become ["int", "AX"]
            # It's ok to have wrong names here as they will be dealt with later.
            while num_changes > 0:
                all_changes.append(args_str)
                args_str, num_changes = re.subn(regex, r'X', args_str)
            arg_list += all_changes[-1].split(',')
            return type_name, arg_list

        # Link-ify the class and all the class's template parameters.
        # e.g. 'link to std::shared_ptr'<'link to Foo'>
        type_name, arg_list = parse_template_type_spelling(clang_type.spelling)
        if not type_name or len(arg_list) != num_template_args:
            log.debug('Wrong number of template args: len(%s) vs %s',
                      arg_list, num_template_args)
            declaration_text += Popup.link_from_location(
                Popup.location_from_type(clang_type),
                clang_type.spelling,
                trailing_space=False)
            return declaration_text

        declaration_text += Popup.link_from_location(
            Popup.location_from_type(clang_type),
            type_name,
            trailing_space=False)
        declaration_text += '<'
        for arg_index in range(num_template_args):
            templ_type = clang_type.get_template_argument_type(arg_index)
            declaration_text += Popup._declaration_for_type(
                templ_type,
                cindex,
                default_spelling=arg_list[arg_index].strip())
            if arg_index + 1 < num_template_args:
                declaration_text += ", "
        declaration_text += '>'
        return declaration_text

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

        lines = raw_comment.split('\n')
        chars_to_strip = '/' + '*' + '!' + string.whitespace
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
    def doxygen_comment(mdcomment):
        """Transform cleaned doxygen comment to valid markdown."""
        result = mdcomment
        index = mdcomment.find("@param")
        if (index >= 0):
            result = result[:index] + "\n**Parameters**:\n" + result[index:]
        doc_replace = [
            [r'@param\s+([_a-zA-Z0-9.]+)\s*', "- `\\1`: "],
            [r'@(retval|returns?)\b\s*',   "\n**Returns**:\n"],
            [r'@(exception|throws?)\b\s*', "\n**Exceptions**:\n"],
            [r'@(sa|see(also)?)\b\s*',     "\n**See also**:\n"],
            [r'@f\$', "`"],
            [r'@[{}]', ""],
        ]
        for replace in doc_replace:
            result = re.sub(replace[0], replace[1], result)
        window = sublime.active_window()

        def _make_doxygen_hyperlink(match):
            spelling = match.group(1)
            if len(spelling) == 0:
                return spelling
            symbol = window.lookup_symbol_in_index(spelling)
            if len(symbol) == 0:
                return spelling
            location_tuple = symbol[0]
            location = IndexLocation(filename=location_tuple[0],
                                     line=location_tuple[2][0],
                                     column=location_tuple[2][1])
            link = Popup.link_from_location(location, spelling,
                                            trailing_space=False)
            return link
        result = re.sub(r'\b([_a-zA-Z0-9]+)(?=\(\))',
                        _make_doxygen_hyperlink, result)
        result = re.sub(r'#([_a-zA-Z0-9]+)\b',
                        _make_doxygen_hyperlink, result)
        return result

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
        from os import path
        if location and location.file and location.file.name:
            result += "[" + text + "]"
            result += "(" + path.realpath(location.file.name)
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
