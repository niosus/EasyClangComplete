"""Bridge to sublime functionality."""

import sublime
import logging
import re

from .row_col import ZeroIndexedRowCol

_log = logging.getLogger("ECC")


class SublBridge:
    """A small help class that bridges with sublime (maybe will grow)."""

    NO_DEFAULT_COMPLETIONS = sublime.INHIBIT_WORD_COMPLETIONS \
        | sublime.INHIBIT_EXPLICIT_COMPLETIONS

    SHOW_DEFAULT_COMPLETIONS = None
    HIDE_DEFAULT_COMPLETIONS = ([], sublime.INHIBIT_WORD_COMPLETIONS |
                                sublime.INHIBIT_EXPLICIT_COMPLETIONS)

    @staticmethod
    def set_status(message):
        """Set status message for the current view."""
        view = SublBridge.active_view()
        view.set_status("000_ECC", message)

    @staticmethod
    def erase_status():
        """Erase status message for the current view."""
        view = SublBridge.active_view()
        if not view:
            # do nothing if there is no view
            return
        view.erase_status("000_ECC")

    @staticmethod
    def erase_phantoms(tag):
        """Erase phantoms for the current view."""
        SublBridge.active_view().erase_phantoms(tag)

    @staticmethod
    def active_view():
        """Get the active view.

        Returns:
            View: Active view
        """
        return sublime.active_window().active_view()

    @staticmethod
    def active_view_id():
        """Get the id of the active view.

        Returns:
            int: buffer id of the active view
        """
        return SublBridge.active_view().buffer_id()

    @staticmethod
    def get_line(view, pos=None):
        """Get next line as text.

        Args:
            view (sublime.View): current view

        Returns:
            str: text that the next line contains
        """
        row_col = ZeroIndexedRowCol.from_1d_location(view, pos)
        point_on_line = view.text_point(row_col.row, 0)
        line = view.line(point_on_line)
        return view.substr(line)

    @staticmethod
    def next_line(view):
        """Get next line as text.

        Args:
            view (sublime.View): current view

        Returns:
            str: text that the next line contains
        """
        row_col = ZeroIndexedRowCol.from_current_cursor_pos(view)
        point_on_next_line = view.text_point(row_col.row + 1, 0)
        line = view.line(point_on_next_line)
        return view.substr(line)

    @staticmethod
    def format_completions(completions, hide_default_completions):
        """Get completions. Manage hiding default ones.

        Args:
            hide_default_completions (bool): True if we hide default ones

        Returns:
            tuple: (completions, flags)
        """
        if completions and hide_default_completions:
            _log.debug("Hiding default completions")
            return (completions, SublBridge.NO_DEFAULT_COMPLETIONS)
        else:
            _log.debug("Adding clang completions to default ones")
            return completions

    @staticmethod
    def show_auto_complete(view):
        """Reopen completion popup.

        It therefore subsequently calls
        EasyClangComplete.on_query_completions(...)

        Args:
            view (sublime.View): view to open completion window in
        """
        _log.debug("reload completion tooltip")
        view.run_command('hide_auto_complete')
        view.run_command('auto_complete', {
            'disable_auto_insert': True,
            'api_completions_only': False,
            'next_competion_if_showing': False})

    @staticmethod
    def show_error_dialog(message):
        """Show an error message dialog."""
        sublime.error_message("EasyClangComplete:\n\n" + message)

    SYNTAX_REGEX = re.compile(r"\/([^\/]+)\.(?:tmLanguage|sublime-syntax)")

    LANG_TAG = "lang"
    SYNTAXES_TAG = "syntaxes"

    LANG_C_TAG = "C"
    LANG_CPP_TAG = "CPP"
    LANG_OBJECTIVE_C_TAG = "OBJECTIVE_C"
    LANG_OBJECTIVE_CPP_TAG = "OBJECTIVE_CPP"
    LANG_TAGS = [LANG_C_TAG, LANG_CPP_TAG,
                 LANG_OBJECTIVE_C_TAG, LANG_OBJECTIVE_CPP_TAG]

    LANG_NAMES = {
        LANG_C_TAG: 'c',
        LANG_CPP_TAG: 'c++',
        LANG_OBJECTIVE_CPP_TAG: 'objective-c++',
        LANG_OBJECTIVE_C_TAG: 'objective-c'
    }

    @staticmethod
    def get_view_lang(view, settings_storage):
        """Get language from view description.

        Args:
            view (sublime.View): Current view
            settings_storage (SettingsStorage): ECC settings for the view

        Returns:
            str: language, one of LANG_TAGS or None if nothing matched
        """
        syntax = SublBridge.get_view_syntax(view)
        for lang_tag, syntaxes in settings_storage.valid_lang_syntaxes.items():
            if syntax in syntaxes and lang_tag in SublBridge.LANG_NAMES:
                return lang_tag, SublBridge.LANG_NAMES[lang_tag]
        _log.debug("ECC does nothing for language syntax: '%s'", syntax)
        return None, None

    @staticmethod
    def get_view_syntax(view):
        """Get syntax from view description.

        Args:
            view (sublime.View): Current view

        Returns:
            str: syntax, e.g. "C", "C++"
        """
        try:
            syntax = re.findall(SublBridge.SYNTAX_REGEX,
                                view.settings().get('syntax'))
            if len(syntax) > 0:
                return syntax[0]
        except TypeError as e:
            # if the view is killed while this is being run, an exception is
            # thrown. Let's dela with it gracefully.
            _log.error("error while getting current language: '%s'", e)
        return None

    @staticmethod
    def has_valid_syntax(view, settings_storage):
        """Check if syntax is valid for this plugin.

        Args:
            view (sublime.View): current view
            settings_storage (SettingsStorage): ECC settings for this view

        Returns:
            bool: True if valid, False otherwise
        """
        lang_tag, lang = SublBridge.get_view_lang(view, settings_storage)
        if not lang:
            # We could not determine the language from syntax. Means the syntax
            # is not valid for us.
            return False
        return True

    @staticmethod
    def is_valid_view(view):
        """Check whether the given view is one we can and want to handle.

        Args:
            view (sublime.View): view to check

        Returns:
            bool: True if we want to handle this view, False otherwise
        """
        from os import path
        if not view:
            _log.debug("view is None")
            return False
        if not view.file_name():
            _log.debug("view file_name is None")
            return False
        if view.is_scratch():
            _log.debug("view is scratch view")
            return False
        if view.buffer_id() == 0:
            _log.debug("view buffer id is 0")
            return False
        if not path.exists(view.file_name()):
            _log.debug("view file_name does not exist in system")
            return False
        return True

    @staticmethod
    def get_pos_status(point, view, settings):
        """Check if the cursor focuses a valid trigger.

        Args:
            point (int): position of the cursor in the file as defined by subl
            view (sublime.View): current view
            settings (TYPE): Description

        Returns:
            PosStatus: statuf for this position
        """
        trigger_length = 1

        word_on_the_left = view.substr(view.word(point - trigger_length))
        if word_on_the_left.isdigit():
            # don't autocomplete digits
            _log.debug("trying to autocomplete digit, are we? Not allowed.")
            return PosStatus.WRONG_TRIGGER

        # slightly counterintuitive `view.substr` returns ONE character
        # to the right of given point.
        curr_char = view.substr(point - trigger_length)
        wrong_trigger_found = False
        for trigger in settings.triggers:
            # compare to the last char of a trigger
            if curr_char == trigger[-1]:
                trigger_length = len(trigger)
                prev_char = view.substr(point - trigger_length)
                if prev_char == trigger[0]:
                    _log.debug("matched trigger '%s'.", trigger)
                    return PosStatus.COMPLETION_NEEDED
                else:
                    _log.debug("wrong trigger '%s%s'.", prev_char, curr_char)
                    wrong_trigger_found = True
        if wrong_trigger_found:
            # no correct trigger found, but a wrong one fired instead
            _log.debug("wrong trigger fired")
            return PosStatus.WRONG_TRIGGER

        if settings.autocomplete_all:
            return PosStatus.COMPLETION_NEEDED

        this_line = SublBridge.get_line(view, point)
        if this_line.startswith('#include'):
            _log.debug("completing an include")
            return PosStatus.COMPLETE_INCLUDES
        # if nothing fired we don't need to do anything
        _log.debug("no completions needed")
        return PosStatus.COMPLETION_NOT_NEEDED


class PosStatus:
    """Enum class with values for completion status."""
    COMPLETION_NEEDED = 0
    COMPLETION_NOT_NEEDED = 1
    WRONG_TRIGGER = 2
    COMPLETE_INCLUDES = 3
