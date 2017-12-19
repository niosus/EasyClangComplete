"""Parse a macro from cindex."""


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
        self._body = ''
        if location and location.file and location.file.name:
            with open(location.file.name, 'r', encoding='utf-8',
                      errors='ignore') as f:
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
                macro_line = macro_line[end_args_index + 1:]

        self._body = macro_line.strip()
        while self._body.endswith("\\"):
            macro_line_number += 1
            line = macro_file_lines[macro_line_number - 1].rstrip()
            self._body += "\n" + line

    @property
    def args_string(self):
        """Get arguments string.

        Examples:
            '#define MACRO()' would return '()'
            '#define MACRO(x, y)' would return '(x, y)'
            '#define MACRO' would return ''
        """
        return self._args_string

    @property
    def body_string(self):
        """Get macro body string."""
        return self._body
