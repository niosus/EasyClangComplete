"""Contains base class for completers.

Attributes:
    log (logging.Logger): logger for this module

"""
import logging

from os import path

from .compiler_variant import CompilerVariant

from .. import error_vis

from ..tools import SearchScope
from ..tools import Tools

from ..flags_sources.cmake_file import CMakeFile
from ..flags_sources.compilation_db import CompilationDb
from ..flags_sources.flags_file import FlagsFile
from ..flags_sources.flags_source import FlagsSource
from ..utils.unique_list import UniqueList
from ..utils.flag import Flag


log = logging.getLogger(__name__)


class BaseCompleter:
    """A base class for clang based completions.

    Attributes:
        completions (list): current list of completions
        error_vis (plugin.CompileErrors): object of compile errors class
        compiler_variant (CompilerVariant): compiler specific options
        valid (bool): is completer valid
        version_str (str): version string of format "3.4" for clang v. 3.4
    """
    version_str = None
    error_vis = None
    compiler_variant = None

    valid = False

    def __init__(self, clang_binary):
        """Initialize the BaseCompleter.

        Args:
            clang_binary (str): string for clang binary e.g. 'clang-3.6++'

        Raises:
            RuntimeError: if clang not defined we throw an error

        """
        # check if clang binary is defined
        if not clang_binary:
            raise RuntimeError("clang binary not defined")

        # run the cmd to get the proper version of the installed clang
        self.version_str = Tools.get_clang_version_str(clang_binary)
        # initialize error visualization
        self.error_vis = error_vis.CompileErrors()

    def needs_init(self, view):
        """Check if the completer needs init.

        Args:
            view (sublime.View): current view

        Returns:
            bool: True if init needed, False if not
        """
        # TODO(igor): what if flag source has changed? Do we even need it now?
        if self.exists_for_view(view.buffer_id()):
            log.debug(" view %s, already has a completer", view.buffer_id())
            return False
        log.debug(" need to init view '%s'", view.buffer_id())
        return True

    def remove(self, view_id):
        """Call when completion for this view is not needed anymore.

        For actual implementation see children of this class.
        Args:
            view_id (sublime.View): current view

        Raises:
            NotImplementedError: Guarantees we do not call this abstract method
        """
        raise NotImplementedError("calling abstract method")

    def exists_for_view(self, view_id):
        """Check if completer for this view is initialized.

        For real implementation see children.

        Args:
            view_id (int): view id

        Raises:
            NotImplementedError: Guarantees we do not call this abstract method
        """
        raise NotImplementedError("calling abstract method")

    def init_for_view(self, view, settings):
        """Initialize the completer for this view.

        For real implementation see children.

        Args:
            view (sublime.View): current view
            settings (Settings): plugin settings

        """
        # initialize default flags (init_flags list needs to be copied).
        initial_flags = UniqueList(CompilerVariant.init_flags)
        current_lang = Tools.get_view_syntax(view)
        if current_lang == 'C' or current_lang == 'C99':
            lang_flags = settings.c_flags
        else:
            lang_flags = settings.cpp_flags

        initial_flags += Flag.tokenize_list(lang_flags)

        include_prefixes = self.compiler_variant.include_prefixes
        home_folder = path.expanduser('~')
        initial_flags += FlagsSource.parse_flags(home_folder,
                                                 settings.common_flags,
                                                 include_prefixes)
        # get other flags from some flag source
        current_flags = BaseCompleter.get_flags_from_source(
            view, settings, include_prefixes)
        all_flags = initial_flags + current_flags
        self.clang_flags = []
        for flag in all_flags:
            self.clang_flags += flag.as_list()

    @staticmethod
    def get_flags_from_source(view, settings, include_prefixes):
        """Get flags from a flag source picked in settings.

        Args:
            view (View): Current view.
            settings (SettingsStorage): Current settings.
            include_prefixes (str[]): Valid include prefixes.

        Returns:
            str[]: Flags for this view.
        """
        prefix_paths = settings.cmake_prefix_paths
        if prefix_paths is None:
            prefix_paths = []
        current_dir = path.dirname(view.file_name())
        search_scope = SearchScope(
            from_folder=current_dir,
            to_folder=settings.project_folder)
        for source in settings.flags_sources:
            if source == "cmake":
                flag_source = CMakeFile(include_prefixes, prefix_paths)
            elif source == "compilation_db":
                flag_source = CompilationDb(include_prefixes)
            elif source == "clang_complete_file":
                flag_source = FlagsFile(include_prefixes)
            # try to get flags
            flags = flag_source.get_flags(view.file_name(), search_scope)
            if flags:
                # don't load anything more if we have flags
                log.debug(" flags generated with '%s' source.", source)
                return flags
        return []

    def complete(self, completion_request):
        """Function to generate completions. See children for implementation.

        Args:
            completion_request (CompletionRequest): request object

        Raises:
            NotImplementedError: Guarantees we do not call this abstract method
        """
        raise NotImplementedError("calling abstract method")

    def update(self, view, show_errors):
        """Update the completer for this view.

        This can increase consequent completion speeds or is needed to just
        show errors.

        Args:
            view (sublime.View): this view
            show_errors (bool): controls if we show errors

        Raises:
            NotImplementedError: Guarantees we do not call this abstract method
        """
        raise NotImplementedError("calling abstract method")

    def show_errors(self, view, output):
        """Show current complie errors.

        Args:
            view (sublime.View): Current view
            output (object): opaque output to be parsed by compiler variant
        """
        errors = self.compiler_variant.errors_from_output(output)
        self.error_vis.generate(view, errors)
        self.error_vis.show_regions(view)
