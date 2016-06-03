"""This moducle contains various tools

Attributes:
    log (TYPE): Description
    PKG_NAME (str): this package name
    OSX_CLANG_VERSION_DICT (dict): mapping from version number of OSX clang
        to the one of llvm clang.
        Taken from here: https://gist.github.com/yamaya/2924292
"""
import os.path as path
import logging
import re

PKG_NAME = path.basename(path.dirname(path.dirname(__file__)))

OSX_CLANG_VERSION_DICT = {
    '4.2':'3.2',
    '5.0':'3.3',
    '5.1':'3.4',
    '6.0':'3.5',
    '6.1':'3.6',
    '7.0':'3.7',
    '7.3':'3.8'
}

log = logging.getLogger(__name__)

class SublBridge:
    """A small help class that bridges with sublime (maybe will grow)
    """

    @staticmethod
    def cursor_pos(view):
        """Get current cursor position. Returns position of the first cursor if
        multiple are present

        Args:
            view (sublime.View): current view

        Returns:
            (row, col): tuple of row and col for cursor position
        """
        pos = view.sel()
        if len(pos) < 1:
            # something is wrong
            return None
        (row, col) = view.rowcol(pos[0].a)
        row += 1
        col += 1
        return (row, col)

    @staticmethod
    def next_line(view):
        """Get next line as text

        Args:
            view (sublime.View): current view

        Returns:
            str: text that the next line contains
        """
        (row, _) = SublBridge.cursor_pos(view)
        point_on_next_line = view.text_point(row, 0)
        line = view.line(point_on_next_line)
        return view.substr(line)

class Tools:
    """just a bunch of helpful tools to unclutter main file

    Attributes:
        syntax_regex (regex): regex to parse syntax setting
        valid_extensions (list): list of valid extentions for autocompletion
    """

    syntax_regex = re.compile("\/([^\/]+)\.(?:tmLanguage|sublime-syntax)")

    valid_extensions = [".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hxx"]

    @staticmethod
    def get_view_syntax(view):
        """Get syntax from view description

        Args:
            view (sublime.View): Current view

        Returns:
            str: syntax, e.g. "C", "C++"
        """
        syntax = re.findall(Tools.syntax_regex,
                            view.settings().get('syntax'))
        if len(syntax) > 0:
            return syntax[0]
        return None

    @staticmethod
    def has_valid_syntax(view):
        """Check if syntax is valid for this plugin

        Args:
            view (sublime.View): current view

        Returns:
            bool: True if valid, False otherwise
        """
        syntax = Tools.get_view_syntax(view)
        if syntax in ["C", "C++"]:
            log.debug(" file has valid syntax: `%s`", syntax)
            return True
        return False

    @staticmethod
    def is_valid_view(view):
        """
        Check whether the given view is one we can and want to handle.

        Args:
            view (sublime.View): view to check

        Returns:
            bool: True if we want to handle this view, False otherwise
        """

        return Tools.has_valid_syntax(view) and view.file_name()

    @staticmethod
    def has_valid_extension(view):
        """Test if the current file has a valid extension

        Args:
            view (sublime.View): current view

        Returns:
            bool: extension is valid
        """
        if not view or not view.file_name():
            return False
        (_, ext) = path.splitext(view.file_name())
        if ext in Tools.valid_extensions:
            return True
        return False

    @staticmethod
    def needs_autocompletion(point, view, settings):
        """Check if the cursor focuses a valid trigger

        Args:
            point (int): position of the cursor in the file as defined by subl
            view (sublime.View): current view
            settings (TYPE): Description

        Returns:
            bool: trigger is valid
        """
        trigger_length = 1

        current_char = view.substr(point - trigger_length)

        if current_char == '>':
            trigger_length = 2
            if view.substr(point - trigger_length) != '-':
                return False
        if current_char == ':':
            trigger_length = 2
            if view.substr(point - trigger_length) != ':':
                return False

        word_on_the_left = view.substr(view.word(point - trigger_length))
        if word_on_the_left.isdigit():
            # don't autocomplete digits
            return False

        for trigger in settings.triggers:
            if current_char in trigger:
                return True

        if settings.complete_all \
                and (current_char.isalpha() or current_char == '_'):
            return True

        return False
