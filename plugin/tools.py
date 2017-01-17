"""This module contains various tools

Attributes:
    log (logging): logger for this module
    OSX_CLANG_VERSION_DICT (dict): mapping from version number of OSX clang
        to the one of llvm clang.
        Taken from here: https://gist.github.com/yamaya/2924292
    PKG_NAME (str): this package name
"""
from os import path
from os import makedirs
from os import listdir

import sublime
import logging
import tempfile
import platform
import subprocess

import re

PKG_NAME = path.basename(path.dirname(path.dirname(__file__)))

OSX_CLANG_VERSION_DICT = {
    '4.2': '3.2',
    '5.0': '3.3',
    '5.1': '3.4',
    '6.0': '3.5',
    '6.1': '3.6',
    '7.0': '3.7',
    '7.3': '3.8',
    '8.0': '3.8'
}

log = logging.getLogger(__name__)


def singleton(class_):
    """Singleton class wrapper.

    Args:
      class_ (Class): Class to wrap.

    Returns:
      class_: unique instance of object.
    """
    instances = {}

    def getinstance(*args, **kwargs):
        """Get instance of a class."""
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]
    return getinstance


class SublBridge:
    """A small help class that bridges with sublime (maybe will grow).

    Attributes:
        NO_DEFAULT_COMPLETIONS (TYPE): Description
    """
    NO_DEFAULT_COMPLETIONS = sublime.INHIBIT_WORD_COMPLETIONS \
        | sublime.INHIBIT_EXPLICIT_COMPLETIONS

    @staticmethod
    def active_view_id():
        """Get the id of the active view.

        Returns:
            int: buffer id of the active view
        """
        return sublime.active_window().active_view().buffer_id()

    @staticmethod
    def cursor_pos(view, pos=None):
        """Get current cursor position.

        Args:
            view (sublime.View): current view
            pos (int, optional): given position. First selection by default.

        Returns:
            (row, col): tuple of row and col for cursor position
        """
        if not pos:
            pos = view.sel()
            if len(pos) < 1:
                # something is wrong
                return None
            # we care about the first position
            pos = pos[0].a
        (row, col) = view.rowcol(pos)
        row += 1
        col += 1
        return (row, col)

    @staticmethod
    def next_line(view):
        """Get next line as text.

        Args:
            view (sublime.View): current view

        Returns:
            str: text that the next line contains
        """
        (row, _) = SublBridge.cursor_pos(view)
        point_on_next_line = view.text_point(row, 0)
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
        if hide_default_completions:
            log.debug(" hiding default completions")
            return (completions, SublBridge.NO_DEFAULT_COMPLETIONS)
        else:
            log.debug(" adding clang completions to default ones")
            return completions

    @staticmethod
    def show_auto_complete(view):
        """Calling this function reopens completion popup.

        It therefore subsequently calls
        EasyClangComplete.on_query_completions(...)

        Args:
            view (sublime.View): view to open completion window in
        """
        log.debug(" reload completion tooltip")
        view.run_command('hide_auto_complete')
        view.run_command('auto_complete', {
            'disable_auto_insert': True,
            'api_completions_only': False,
            'next_competion_if_showing': False})


class PosStatus:
    """Enum class for position status.

    Attributes:
        COMPLETION_NEEDED (int): completion needed
        COMPLETION_NOT_NEEDED (int): completion not needed
        WRONG_TRIGGER (int): trigger is wrong
    """
    COMPLETION_NEEDED = 0
    COMPLETION_NOT_NEEDED = 1
    WRONG_TRIGGER = 2


class File:
    """Encapsulates a file."""
    __modification_cache = {}

    def __init__(self, file_path=None):
        """Initialize a new file and create it if needed.

        Args:
            file_path (str, optional): generate file object from this path
        """
        # intialize full path
        self.__full_path = None

        # fill the object if possible
        if not file_path or not path:
            # leave the object unitialized
            return
        self.__full_path = path.abspath(file_path)
        # initialize the file
        open(self.__full_path, 'a+').close()

    def full_path(self):
        """Get full path to file.

        Returns:
            str: full path
        """
        return self.__full_path

    def folder(self):
        """Get parent folder to the file.

        Returns:
            str: parent folder of a file
        """
        return path.dirname(self.__full_path)

    def loaded(self):
        """Check if the file is loaded."""
        if self.__full_path:
            return True
        return False

    @staticmethod
    def is_unchanged(file_path):
        """Check if file is unchanged since last access.

        Args:
            file_path (str): Path to a file.

        Returns:
            bool: True if unchanged, False otherwise.
        """
        if not file_path:
            return False
        actual_mod_time = path.getmtime(file_path)
        if file_path not in File.__modification_cache:
            log.debug(" never seen file '%s' before. Updating.", file_path)
            File.__modification_cache[file_path] = actual_mod_time
            return False
        cached_mod_time = File.__modification_cache[file_path]
        if actual_mod_time != cached_mod_time:
            File.__modification_cache[file_path] = actual_mod_time
            return False
        return True

    @staticmethod
    def canonical_path(input_path, folder=''):
        """Return a canonical path of the file.

        Args:
            input_path (str): path to convert.
            folder (str, optional): parent folder.

        Returns:
            str: canonical path
        """
        if not input_path:
            return None
        if not path.isabs(input_path):
            input_path = path.join(folder, input_path)
        return path.normcase(path.normpath(input_path))

    @staticmethod
    def update_mod_time(full_path):
        """Update modification time.

        Args:
            full_path (str): current full path to file.
        """
        log.debug(" updating modification time for file '%s'", full_path)
        mod_time = path.getmtime(full_path)
        File.__modification_cache[full_path] = mod_time

    @staticmethod
    def search(file_name, from_folder, to_folder, search_content=None):
        """Search for a file up the tree.

        Args:
            file_name (TYPE): Description
            from_folder (str): path to folder where we start the search
            to_folder (str): path to folder we should not go beyond
            search_content (None, optional): Description

        Returns:
            File: found file
        """
        # TODO(igor): should just take a SearchScope as input param
        log.debug(" searching '%s' from '%s' to '%s'",
                  file_name, from_folder, to_folder)
        current_folder = from_folder
        if not path.exists(current_folder):
            return File()
        one_past_stop_folder = path.dirname(to_folder)
        while current_folder != one_past_stop_folder:
            for file in listdir(current_folder):
                if file == file_name:
                    found_file = File(path.join(current_folder, file))
                    log.debug(" found '%s' file: %s",
                              file_name, found_file.full_path())
                    if search_content:
                        if File.contains(found_file.full_path(),
                                         search_content):
                            return found_file
                        else:
                            log.debug(" skipping file '%s'. ", found_file)
                            log.debug(" no line starts with: '%s'",
                                      search_content)
                            continue
                    # this is reached only if we don't search any content
                    return found_file
            if current_folder == path.dirname(current_folder):
                break
            current_folder = path.dirname(current_folder)
        return File()

    @staticmethod
    def contains(file_path, query):
        """Check if file contains a line.

        Args:
            file_path (str): path to file
            query (str): string to search

        Returns:
            bool: True if contains str, False if not
        """
        with open(file_path) as f:
            for line in f:
                if line.lower().startswith(query):
                    log.debug(" found needed line: '%s'", line)
                    return True
        return False


class SearchScope:
    """Encapsulation of a search scope for code cleanness."""
    from_folder = None
    to_folder = None

    def __init__(self, from_folder=None, to_folder=None):
        """Initialize the search scope.

        If any of the folders in None, set it to root

        Args:
            from_folder (str, optional): search from this folder
            to_folder (str, optional): search up to this folder
        """
        self.from_folder = from_folder
        self.to_folder = to_folder
        if not self.to_folder:
            self.to_folder = path.abspath('/')
        if not self.from_folder:
            self.from_folder = path.abspath('/')

    def valid(self):
        """Check if the search scope valid.

        Returns:
            bool: True if valid, False otherwise
        """
        if self.from_folder and self.to_folder:
            return True
        return False


class CompletionRequest(object):
    """A wrapper for completer request.

    Provides a way to identify a completer request and provide some information
    used when creating the request.
    """
    def __init__(self, view, trigger_position):
        """
        Initializes the object.

        Args:
            view (sublime.View): The view for which request is created.
            trigger_position(int): The position for which request was created.
        """
        self._view = view
        self._trigger_position = trigger_position

    def get_view(self):
        """Return the view for which completion was requested."""
        return self._view

    def get_trigger_position(self):
        """Get position of the trigger for which completion was requested."""
        return self._trigger_position

    def get_identifier(self):
        """Generate unique tuple for file and trigger position."""
        return (self._view.buffer_id(), self._trigger_position)

    def is_suitable_for_view(self, view):
        """Check if view is suitable for this completion request.

        Return True if specified view and its current position is deemed
        suitable for completions generated by this completion request. """
        if view != self._view:
            log.debug(" active view doesn't match completion view")
            return False
        # We accept both current position and position to the left of the
        # current word as valid as we don't know how much user already typed
        # after the trigger.
        current_position = view.sel()[0].a
        valid_positions = [current_position, view.word(current_position).a]
        if self._trigger_position not in valid_positions:
            log.debug(
                " view's trigger positions %s doesn't match completed trigger "
                "position %s" % (valid_positions, self._trigger_position))
            return False
        return True


class Tools:
    """Just a bunch of helpful tools.

    Attributes:
        HIDE_DEFAULT_COMPLETIONS: a value to return from `on_query_completions`
            Ensures nothing will be shown apart from the output of this plugin
        SHOW_DEFAULT_COMPLETIONS: `None` to return from `on_query_completions`.
            This guarantees that sublime text will show default completions.
        syntax_regex (regex): regex to parse syntax setting
        valid_extensions (list): list of valid extensions for auto-completion
        valid_syntax (list): list of valid syntaxes for this plugin

    """

    syntax_regex = re.compile("\/([^\/]+)\.(?:tmLanguage|sublime-syntax)")

    valid_extensions = [".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hxx"]

    C_SYNTAX = ["C", "C Improved", "C99"]
    CPP_SYNTAX = ["C++", "C++11"]
    valid_syntax = C_SYNTAX + CPP_SYNTAX

    SHOW_DEFAULT_COMPLETIONS = None
    HIDE_DEFAULT_COMPLETIONS = ([], sublime.INHIBIT_WORD_COMPLETIONS |
                                sublime.INHIBIT_EXPLICIT_COMPLETIONS)

    @staticmethod
    def get_temp_dir():
        """Create a temporary folder if needed and return it."""
        tempdir = path.join(tempfile.gettempdir(), PKG_NAME)
        if not path.exists(tempdir):
            makedirs(tempdir)
        return tempdir

    @staticmethod
    def get_view_lang(view):
        """Get language from view description.

        Args:
            view (sublime.View): Current view

        Returns:
            str: language, "C" or "C++"
        """
        syntax = Tools.get_view_syntax(view)
        if syntax in Tools.C_SYNTAX:
            return "C"
        if syntax in Tools.CPP_SYNTAX:
            return "C++"
        return None

    @staticmethod
    def get_view_syntax(view):
        """Get syntax from view description.

        Args:
            view (sublime.View): Current view

        Returns:
            str: syntax, e.g. "C", "C++"
        """
        try:
            syntax = re.findall(Tools.syntax_regex,
                                view.settings().get('syntax'))
            if len(syntax) > 0:
                return syntax[0]
        except TypeError as e:
            # if the view is killed while this is being run, an exception is
            # thrown. Let's dela with it gracefully.
            log.error(" error while getting current language: '%s'", e)
        return None

    @staticmethod
    def has_valid_syntax(view):
        """Check if syntax is valid for this plugin.

        Args:
            view (sublime.View): current view

        Returns:
            bool: True if valid, False otherwise
        """
        syntax = Tools.get_view_syntax(view)
        if syntax in Tools.valid_syntax:
            log.debug(" file has valid syntax: `%s`", syntax)
            return True
        log.debug(" file has unsupported syntax: `%s`", syntax)
        return False

    @staticmethod
    def is_valid_view(view):
        """Check whether the given view is one we can and want to handle.

        Args:
            view (sublime.View): view to check

        Returns:
            bool: True if we want to handle this view, False otherwise
        """
        if not view:
            return False
        if not view.file_name():
            return False
        if not Tools.has_valid_syntax(view):
            return False
        if view.is_scratch():
            return False
        if view.buffer_id() == 0:
            return False
        if not path.exists(view.file_name()):
            return False
        return True

    @staticmethod
    def has_valid_extension(view):
        """Test if the current file has a valid extension.

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
    def seconds_from_string(time_str):
        """Get int seconds from string.

        Args:
            time_str (str): string in format 'HH:MM:SS'

        Returns:
            int: seconds
        """
        h, m, s = time_str.split(":")
        return int(h) * 3600 + int(m) * 60 + int(s)

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
            log.debug(" trying to autocomplete digit, are we? Not allowed.")
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
                    log.debug(" matched trigger '%s'.", trigger)
                    return PosStatus.COMPLETION_NEEDED
                else:
                    log.debug(" wrong trigger '%s%s'.", prev_char, curr_char)
                    wrong_trigger_found = True
        if wrong_trigger_found:
            # no correct trigger found, but a wrong one fired instead
            log.debug(" wrong trigger fired")
            return PosStatus.WRONG_TRIGGER

        if settings.autocomplete_all:
            return PosStatus.COMPLETION_NEEDED

        # if nothing fired we don't need to do anything
        log.debug(" no completions needed")
        return PosStatus.COMPLETION_NOT_NEEDED

    @staticmethod
    def run_command(command, shell=True):
        """Run a generic command in a subprocess.

        Args:
            command (str): command to run

        Returns:
            str: raw command output
        """
        try:
            stdin = None
            startupinfo = None
            if isinstance(command, list):
                command = subprocess.list2cmdline(command)
                log.debug(" command: \n%s", command)
            if platform.system() == "Windows":
                # Don't let console window pop-up briefly.
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                stdin = subprocess.PIPE
            output = subprocess.check_output(command,
                                             stdin=stdin,
                                             stderr=subprocess.STDOUT,
                                             shell=shell,
                                             startupinfo=startupinfo)
            output_text = ''.join(map(chr, output))
        except subprocess.CalledProcessError as e:
            output_text = e.output.decode("utf-8")
            log.debug(" clang process finished with code: %s", e.returncode)
            log.debug(" clang process output: \n%s", output_text)
        return output_text

    @staticmethod
    def get_clang_version_str(clang_binary):
        """Get Clang version string from subprocess run of "clang_binary -v".

        Args:
            clang_binary (str): clang binary, e.g. "clang++-3.8"

        Returns:
            str: clang version number like: 3.8.0

        Raises: RuntimeError: There is an error while getting version. This is
            too important to continue. If this fails the plugin will not work
            at all.
        """
        check_version_cmd = clang_binary + " -v"
        log.info(" Getting version from command: `%s`", check_version_cmd)
        output_text = Tools.run_command(check_version_cmd, shell=True)

        # now we have the output, and can extract version from it
        version_regex = re.compile("\d\.\d\.*\d*")
        match = version_regex.search(output_text)
        if match:
            version_str = match.group()
            if version_str > "3.8" and platform.system() == "Darwin":
                # info from this table: https://gist.github.com/yamaya/2924292
                osx_version = version_str[:3]
                version_str = OSX_CLANG_VERSION_DICT[osx_version]
                info = {"platform": platform.system()}
                log.warning(
                    " OSX version %s reported. Reducing it to %s. Info: %s",
                    osx_version, version_str, info)
            log.info(" Found clang version: %s", version_str)
            return version_str
        else:
            raise RuntimeError(
                " Couldn't find clang version in clang version output.")

    @staticmethod
    def get_unique_str(init_string):
        """Generate md5 unique sting hash given init_string."""
        import hashlib
        return hashlib.md5(init_string.encode('utf-8')).hexdigest()

    @staticmethod
    def find_flag_idx(flags, prefix):
        """Find index of flag with given prefix in list.

        Returns: index of found flag or None if not found
        """
        for idx, flag in enumerate(flags):
            if flag.startswith(prefix):
                return idx
        return None
