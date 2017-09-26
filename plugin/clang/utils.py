"""Utilities for clang.

Attributes:
    log (logging.log): logger for this module
"""
import platform
import logging
import subprocess
import html

from os import path

log = logging.getLogger("ECC")


class MacroParser(object):
    """Parse info from macros.

    Clang doesn't provide much information for MACRO_DEFINITION cursors,
    so we have to parse this info ourselves.
    """

    def __init__(self, name, location):
        """Parse the macro with the given name from its location.

        Args:
            name (str): Macro's name.
            location (cindex.SourceLocation): Macro definition's location.
                Can be None for unittests that parse with text content
                directly instead of loading from file.

        Future improvement: if there are line continuation characters
            in a macro with parenthesis, continue parsing into the next line
            to find it and create a proper args string.
        """
        self._args_string = ''
        self._name = name
        if location and location.file and location.file.name:
            with open(location.file.name, 'r') as f:
                macro_file_lines = f.readlines()
                self._parse_macro_file_lines(macro_file_lines, location.line)

    def _parse_macro_file_lines(self, macro_file_lines, macro_line_number):
        """Parse a macro from lines of text containing the macro.

        Args:
            macro_file_lines (list[str]): lines of text containing the macro
            macro_line_number (int): line number (1-based) of the macro
               in macro_file_lines.
        """
        macro_line = macro_file_lines[macro_line_number - 1].strip()
        # strip leading '#<whitespace>define<whitespace><macro name>'
        macro_line = macro_line.lstrip('#').lstrip().lstrip('define')
        macro_line = macro_line.lstrip().lstrip(self._name)
        # macro that looks like a function, possibly with args
        if macro_line.startswith('('):
            end_args_index = macro_line.find(')')
            # There should always be a closing parenthesis, but check
            # just in case a) the code is malformed or b) the macro
            # definition is continued on the next line so we can't
            # find it on this line.
            if end_args_index != -1:
                # If extra spaces, e.g. "#define MACRO( x ,  y  , z )",
                # then flatten down to just "(x, y, z)"
                args_str = macro_line[1:end_args_index]
                args_str = ''.join(args_str.split())
                args_str = args_str.replace(',', ', ')
                self._args_string = '(' + args_str + ')'

    @property
    def args_string(self):
        """Get arguments string.

        Examples:
            '#define MACRO()' would return '()'
            '#define MACRO(x, y)' would return '(x, y)'
            '#define MACRO' would return ''
        """
        return self._args_string


class ClangUtils:
    """Utils to help handling libclang, e.g. searching for it.

    Attributes:
        libclang_name (str): name of the libclang library file
        linux_suffixes (list): suffixes for linux
        osx_suffixes (list): suffixes for osx
        windows_suffixes (list): suffixes for windows
    """
    libclang_name = None

    windows_suffixes = ['.dll', '.lib']
    linux_suffixes = ['.so', '.so.1']
    osx_suffixes = ['.dylib']

    suffixes = {
        'Windows': windows_suffixes,
        'Linux': linux_suffixes,
        'Darwin': osx_suffixes
    }

    # MSYS2 has `clang.dll` instead of `libclang.dll`
    possible_filenames = {
        'Windows': ['libclang', 'clang'],
        'Linux': ['libclang-$version', 'libclang'],
        'Darwin': ['libclang']
    }

    @staticmethod
    def dir_from_output(output):
        """Get library directory based on the output of clang.

        Args:
            output (str): raw output from clang

        Returns:
            str: path to folder with libclang
        """
        log.debug("real output: %s", output)
        if platform.system() == "Darwin":
            # [HACK] uh... I'm not sure why it happens like this...
            folder_to_search = path.join(output, '..', '..')
            log.debug("folder to search: %s", folder_to_search)
            return folder_to_search
        elif platform.system() == "Windows":
            log.debug("architecture: %s", platform.architecture())
            return path.normpath(output)
        elif platform.system() == "Linux":
            return path.normpath(path.dirname(output))
        return None

    @staticmethod
    def try_load_from_user_hint(libclang_path):
        """Load library hinted by the user.

        Args:
            libclang_path (str): full path to the libclang library file.

        Returns:
            str: folder of the libclang library or None if not found.
        """
        if path.exists(libclang_path):
            return path.dirname(libclang_path)

    @staticmethod
    def find_libclang_dir(clang_binary, libclang_path, version_str):
        """Find directory with libclang.

        Args:
            clang_binary (str): clang binary to call
            libclang_path (str): libclang path provided by user.
                Does not have to be valid.
            version_str(str): version of libclang to be used in format 3.8.0
        Returns:
            str: folder with libclang
        """
        stdin = None
        stderr = None
        log.debug("platform: %s", platform.architecture())
        log.debug("python version: %s", platform.python_version())
        current_system = platform.system()
        log.debug("we are on '%s'", platform.system())
        log.debug("user provided libclang_path: %s", libclang_path)
        # Get version string for help finding the proper libclang library on
        # Linux
        if libclang_path:
            # User thinks he knows better. Let him try his luck.
            libclang_dir = ClangUtils.try_load_from_user_hint(libclang_path)
            if libclang_dir:
                # It was found! No need to search any further!
                ClangUtils.libclang_name = path.basename(libclang_path)
                log.info("using user-provided libclang: '%s'", libclang_path)
                return libclang_dir
        # If the user hint did not work, we look for it normally
        if current_system == "Linux":
            # we only care about first two digits
            version_str = version_str[0:3]
        for suffix in ClangUtils.suffixes[current_system]:
            # pick a name for a file
            for name in ClangUtils.possible_filenames[current_system]:
                file = "{name}{suffix}".format(name=name, suffix=suffix)
                log.debug("searching for: '%s'", file)
                startupinfo = None
                # let's find the library
                if platform.system() == "Darwin":
                    # [HACK]: wtf??? why does it not find libclang.dylib?
                    get_library_path_cmd = [clang_binary, "-print-file-name="]
                elif platform.system() == "Windows":
                    get_library_path_cmd = [clang_binary, "-print-prog-name="]
                    # Don't let console window pop-up briefly.
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE
                    stdin = subprocess.PIPE
                    stderr = subprocess.PIPE
                elif platform.system() == "Linux":
                    file = file.replace("$version", version_str)
                    get_library_path_cmd = [
                        clang_binary, "-print-file-name={}".format(file)]
                output = subprocess.check_output(
                    get_library_path_cmd,
                    stdin=stdin,
                    stderr=stderr,
                    startupinfo=startupinfo).decode('utf8').strip()
                log.debug("libclang search output = '%s'", output)
                if output:
                    libclang_dir = ClangUtils.dir_from_output(output)
                    if path.isdir(libclang_dir):
                        full_libclang_path = path.join(libclang_dir, file)
                        if path.exists(full_libclang_path):
                            log.info("found libclang library file: '%s'",
                                     full_libclang_path)
                            ClangUtils.libclang_name = file
                            return libclang_dir
                log.warning(" clang could not find '%s'", file)
        # if we haven't found anything there is nothing to return
        log.error("no libclang found at all")
        return None

    @staticmethod
    def location_from_type(clangType):
        """Return location from type.

        Return proper location from type.
        Remove all inderactions like pointers etc.

        Args:
            clangType (cindex.Type): clang type.

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

    @staticmethod
    def build_info_details(cursor, cindex):
        """Provide information about given cursor.

        Builds detailed information about cursor.

        Args:
            cursor (Cursor): Current cursor.
            cindex (module): clang cindex.py module for the correct version

        """
        result = ""

        result += '<b>Declaration:</b><br>'

        # Show the return type of the function/method if applicable,
        # macros just show that they are a macro.
        macro_parser = None
        is_macro = cursor.kind == cindex.CursorKind.MACRO_DEFINITION
        if is_macro:
            macro_parser = MacroParser(cursor.spelling, cursor.location)
            result += '#define '
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
                result += "static "

            if cursor.spelling != cursor.type.spelling:
                # Don't show duplicates if the user focuses type, not variable
                result += ClangUtils.link_from_location(
                    ClangUtils.location_from_type(result_type),
                    html.escape(result_type.spelling))
                result += ' '

        # Link to declaration of item under cursor
        if cursor.location:
            result += ClangUtils.link_from_location(
                cursor.location,
                html.escape(cursor.spelling))
        else:
            result += html.escape(cursor.spelling)

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
                    args_string += html.escape(', '.join(args))
                args_string += ')'
        if args_string:
            result += args_string

        # Show value for enum
        if cursor.kind == cindex.CursorKind.ENUM_CONSTANT_DECL:
            result += " = " + str(cursor.enum_value)
            result += "(" + hex(cursor.enum_value) + ")"

        # Method modifiers
        if cursor.is_const_method():
            result += " const"

        # Doxygen comments
        if cursor.brief_comment:
            result += "<br><br><b>Brief documentation:</b><br>"
            result += "<div>" + cursor.brief_comment + "</div>"

        if cursor.raw_comment:
            html_raw_comment = ClangUtils.cleanup_comment(cursor.raw_comment)
            if len(html_raw_comment) > 0:
                result += "<br><b>Full Doxygen comment:</b>"
                result += "<br><div>" + html_raw_comment + "</div>"

        return result

    @staticmethod
    def build_objc_message_info_details(cursor):
        """Provide information about cursor to Objective C message expression.

        Builds detailed information about cursor when cursor is
        a CursorKind.OBJC_MESSAGE_EXPR. OBJC_MESSAGE_EXPR cursors
        behave very differently from other C/C++ cursors in that:
        - The return type we want to show in the tooltip
          is stored in the original 'cursor.type' from the cursor the user is
          hovering over; in C/C++ we only used 'cursor.referenced' but nothing
          else from the original cursor.
        - 'cursor.referenced' is still important, as it holds the name and args
          of the method being called in the message. But
          'cursor.referenced.spelling' comes in a different format then what
          For example, if we have this method declaration for 'bar':
            @interface Foo
              -(void)bar:(BOOL)b1 boolParam2:(BOOL):b2
            @end
          And later, we hover over the text calling bar():
            Foo* foo = [[Foo alloc] init];
            [foo bar:YES boolParam2:NO]; // <- Hover over 'bar' here
          Then we would see:
            cursor.kind = CursorKind.OBJC_INSTANCE_METHOD_DECL
            cursor.type.spelling = 'void'
            cursor.referenced.kind: CursorKind.OBJC_INSTANCE_METHOD_DECL
            cursor.referenced.spelling = 'bar:boolParam2:'
            cursor.referenced.arguments[0].type.spelling = 'BOOL'
            cursor.referenced.arguments[0].spelling = 'b1'
            cursor.referenced.arguments[1].spelling = 'BOOL'
            cursor.referenced.arguments[1].spelling = 'b2'
          Our goal is to make the tooltip match the method declaration:
            'void bar:(BOOL)b1 boolParam2:(BOOL):b2'
        - Objective C methods also don't need to worry about static/const

        Args:
            cursor (Cursor): Current cursor.
        """
        result = ""
        return_type = cursor.type
        result += ClangUtils.link_from_location(
            ClangUtils.location_from_type(return_type),
            html.escape(return_type.spelling))

        result += ' '

        method_cursor = cursor.referenced
        method_and_params = method_cursor.spelling.split(':')
        method_name = method_and_params[0]
        if method_cursor.location:
            result += ClangUtils.link_from_location(
                method_cursor.location,
                html.escape(method_name))
        else:
            result += html.escape(method_cursor.spelling)

        method_params_index = 1
        for arg in method_cursor.get_arguments():
            result += ":(" + arg.type.spelling + ")"
            if arg.spelling:
                result += arg.spelling + " "
            result += method_and_params[method_params_index]
            method_params_index += 1

        if method_cursor.brief_comment:
            result += "<br><br><b>"
            result += method_cursor.brief_comment + "</b>"

        return result

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
        return '<br>'.join(clean_lines)
