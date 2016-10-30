"""This module contains a class for clang binary based completion

Attributes:
    log (logging.Logger): logger for this module

Deleted Attributes:
    cindex_dict (dict): dict of cindex entries for each version of clang
"""
import re
import sublime
import time
import logging

from os import path

from .. import error_vis
from ..tools import Tools
from ..tools import SublBridge
from .base_complete import BaseCompleter
from .compiler_variant import ClangCompilerVariant
from .compiler_variant import ClangClCompilerVariant

log = logging.getLogger(__name__)
log.debug(" reloading module")


class Completer(BaseCompleter):

    """Encapsulates completions based on the output from clang_binary

    Attributes:

        clang_binary (str): e.g. "clang++" or "clang++-3.6"
        flags_dict (dict): compilation flags lists for each view
        std_flag (TYPE): std flag, e.g. "std=c++11"

        completions (list): current completions
        compl_regex (regex): regex to parse raw completion for name and content
        compl_content_regex (regex): regex to parse the content of the
        completion opts_regex (regex): regex to detect optional parameters
        triggers

        group_params (str): string for a group to capture function parameters
        group_types (str): string for a group to capture type names
        group_opts (str): string for a group to capture optional parameters

        PARAM_CHARS (str): chars allowed to be part of function or type
        PARAM_TAG (str): function params tag for convenience
        TYPE_TAG (str): type name tag for convenience

    """
    clang_binary = None

    flags_dict = {}
    std_flag = None

    PARAM_TAG = "param"
    TYPE_TAG = "type"
    PARAM_CHARS = "\w\s\*\&\<\>:,\(\)\$\{\}!"
    TYPE_CHARS = "\w\s\*\&\<\>:,\(\)\$\{\}\[\]!"
    group_params = "(?P<{param_tag}>[{param_chars}]+)".format(
        param_chars=PARAM_CHARS,
        param_tag=PARAM_TAG)
    group_types = "(?P<{type_tag}>[{type_chars}]+)".format(
        type_tag=TYPE_TAG,
        type_chars=TYPE_CHARS)

    compl_str_mask = "{complete_flag}={file}:{row}:{col} {file}"

    completion_mask = "{binary} {init} {std} {complete_at} {flags}"
    update_mask = "{binary} {init} {std} {file} {flags}"

    compl_regex = re.compile("COMPLETION:\s(?P<name>.*)\s:\s(?P<content>.*)")
    compl_content_regex = re.compile(
        "\<#{group_params}#\>|\[#{group_types}#\]".format(
            group_params=group_params, group_types=group_types))

    opts_regex = re.compile("{#|#}")

    def __init__(self, clang_binary):
        """Initialize the Completer

        Args:
            clang_binary (str): string for clang binary e.g. 'clang-3.6++'

        """
        # init common completer interface
        super(Completer, self).__init__(clang_binary)
        Completer.clang_binary = clang_binary

        # Create compiler options of specific variant of the compiler.
        filename = path.splitext(path.basename(clang_binary))[0]
        if filename.startswith('clang-cl'):
            self.compiler_variant = ClangClCompilerVariant()
        else:
            self.compiler_variant = ClangCompilerVariant()

    def remove(self, view_id):
        """remove compile flags for view

        Args:
            view_id (int): current view id
        """
        if view_id in self.flags_dict:
            self.flags_dict[view_id] = []

    def exists_for_view(self, view_id):
        """check if compile flags exist for view id

        Args:
            view_id (int): current view id

        Returns:
            bool: compile flags exist for this view
        """
        if self.flags_dict.get(view_id) is None:
            log.debug(" no build flags for view: %s", view_id)
            return False
        if len(self.flags_dict[view_id]) > 0:
            return True
        return False

    def init(self, view, settings):
        """Initialize the completer

        Args:
            view (sublime.View): current view
            settings (Settings): plugin settings

        """

        # Return early if this is an invalid view.
        if not Tools.is_valid_view(view):
            return

        # init procedure from super class
        super(Completer, self).init(view, settings)

        # init current flags empty
        self.flags_dict[view.buffer_id()] = None
        clang_flags = None

        # set std_flag
        current_lang = Tools.get_view_syntax(view)
        if current_lang != 'C':
            self.std_flag = settings.std_flag_cpp
        else:
            self.std_flag = settings.std_flag_c

        clang_flags = []

        # init includes to start with from settings
        includes = settings.populate_include_dirs(view)

        for include in includes:
            clang_flags.append('-I "{}"'.format(include))

        if settings.search_clang_complete_file and self.flags_manager:
            log.debug(" flags_manager loaded")
            custom_flags = self.flags_manager.get_flags(
                separate_includes=True)
            clang_flags += custom_flags

        # let's print the flags just to be sure
        self.flags_dict[view.buffer_id()] = clang_flags
        log.debug(" clang flags are: %s", self.flags_dict[view.buffer_id()])

    def complete(self, view, cursor_pos, current_job_id):
        """ This function is called asynchronously to create a list of
        autocompletions. It builds up a clang command that is then executed
        as a subprocess. The output is parsed for completions """
        if not view.buffer_id() in self.flags_dict:
            log.error(" cannot complete view: %s", view.buffer_id())
            return (None, None)
        start = time.time()
        output_text = self.run_clang_command(view, "complete", cursor_pos)
        raw_complete = output_text.splitlines()
        end = time.time()
        log.debug(" code complete done in %s seconds", end - start)

        completions = Completer._parse_completions(raw_complete)
        log.debug(' completions: %s' % completions)
        return (current_job_id, completions)

    def update(self, view, show_errors):
        """update build for current view

        Args:
            view (sublime.View): this view
            show_errors (TYPE): do we need to show errors? If not this is a
                dummy function as we gain nothing from building it with binary.

        """
        if view.buffer_id() not in self.flags_dict:
            log.error(
                " Cannot update view %s. No build flags.", view.buffer_id())
            return False

        if not show_errors:
            # in this class there is no need to rebuild the file. It brings no
            # benefits. We only want to do it if we need to show errors.
            return False

        start = time.time()
        output_text = self.run_clang_command(view, "update")
        end = time.time()
        log.debug(" rebuilding done in %s seconds", end - start)

        if show_errors:
            self.show_errors(view, output_text)

    def run_clang_command(self, view, task_type, cursor_pos=0):
        """
        Construct and run clang command based on task

        Args:
            view (sublime.View): current view
            task_type (str): one of: {"complete", "update"}
            cursor_pos (int, optional): cursor position (used in completion)

        Returns:
            str: Output from command
        """
        file_body = view.substr(sublime.Region(0, view.size()))

        tempdir = Tools.get_temp_dir()
        temp_file_name = path.join(tempdir, path.basename(view.file_name()))
        with open(temp_file_name, "w", encoding='utf-8') as tmp_file:
            tmp_file.write(file_body)

        flags = self.flags_dict[view.buffer_id()]
        if task_type == "update":
            # we construct command for update task
            complete_cmd = Completer.update_mask.format(
                binary=Completer.clang_binary,
                init=" ".join(self.compiler_variant.init_flags),
                std=self.std_flag,
                file=temp_file_name,
                flags=" ".join(flags))
        elif task_type == "complete":
            # we construct command for complete task
            (row, col) = SublBridge.cursor_pos(view, cursor_pos)
            complete_at_str = Completer.compl_str_mask.format(
                complete_flag="-Xclang -code-completion-at",
                file=temp_file_name, row=row, col=col)
            complete_cmd = Completer.completion_mask.format(
                binary=Completer.clang_binary,
                init=" ".join(self.compiler_variant.init_flags),
                std=self.std_flag,
                complete_at=complete_at_str,
                flags=" ".join(flags))
        else:
            log.critical(" unknown type of cmd command wanted.")
            return None
        # now run this command
        log.debug(" clang command: \n%s", complete_cmd)

        return Tools.run_command(complete_cmd)

    @staticmethod
    def _parse_completions(complete_results):
        """Create snippet-like structures from a list of completions

        Args:
            complete_results (list): raw completions list

        Returns:
            list: updated completions
        """
        class Parser:

            """Help class to parse completions with regex

            Attributes:
                place_holders (int): number of place holders in use
            """

            def __init__(self):
                self.place_holders = 0

            def tokenize_params(self, match):
                """Create tockens from a match. Used as part or re.sub function

                Args:
                    match (re.match): current match

                Returns:
                    str: current match, wrapped in snippet
                """
                dict_match = match.groupdict()
                if dict_match[Completer.PARAM_TAG]:
                    self.place_holders += 1
                    return "${{{count}:{text}}}".format(
                        count=self.place_holders,
                        text=dict_match[Completer.PARAM_TAG])
                return ''

            @staticmethod
            def make_pretty(match):
                """Process raw match and remove ugly placeholders. Needed to
                have a human readable text for each completion.

                Args:
                    match (re.match): current completion

                Returns:
                    str: match stripped from unneeded placeholders
                """
                dict_match = match.groupdict()
                if dict_match[Completer.PARAM_TAG]:
                    return dict_match[Completer.PARAM_TAG]
                if dict_match[Completer.TYPE_TAG]:
                    return dict_match[Completer.TYPE_TAG] + ' '
                return ''

        completions = []
        for completion in complete_results:
            pos_search = Completer.compl_regex.search(completion)
            if not pos_search:
                log.debug(
                    " completion '%s' did not match pattern '%s'",
                    completion, Completer.compl_regex.pattern)
                continue
            comp_dict = pos_search.groupdict()
            # log.debug("completions parsed: %s", comp_dict)
            trigger = comp_dict['name']
            parser = Parser()
            # remove optional parameters triggers
            comp_dict['content'] = re.sub(
                Completer.opts_regex, '', comp_dict['content'])
            # tokenize parameters
            contents = re.sub(Completer.compl_content_regex,
                              parser.tokenize_params,
                              comp_dict['content'])
            # make the hint look pretty
            hint = re.sub(Completer.compl_content_regex,
                          Parser.make_pretty,
                          comp_dict['content'])
            completions.append([trigger + "\t" + hint, contents])
        return completions
