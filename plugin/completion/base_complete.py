"""Contains base class for completers

Attributes:
    log (logging.Logger): logger for this module

"""
import re
import logging

from os import path

from .. import error_vis
from .. import tools

from .flags_manager import FlagsManager
from .flags_manager import SearchScope

log = logging.getLogger(__name__)

Tools = tools.Tools


class BaseCompleter:

    """A base class for clang based completions

    Attributes:
        completions (list): current list of completions
        error_vis (plugin.CompileErrors): object of compile errors class
        compiler_variant (CompilerVariant): compiler specific options
        flags_manager (FlagsManager): An object that manages all the flags and
            how to load them from disk to memory.
        valid (bool): is completer valid
        version_str (str): version string of format "3.4" for clang v. 3.4
    """
    version_str = None
    error_vis = None
    compiler_variant = None

    flags_manager = None

    valid = False

    def __init__(self, clang_binary):
        """Initialize the BaseCompleter

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
        """ Check if the completer needs init.

        Args:
            view (sublime.View): current view

        Returns:
            bool: True if init needed, False if not
        """
        # TODO: test this approach. Call it in main file
        if not self.flags_manager:
            log.debug(" flags handler not initialized. Do it.")
            return True
        if self.flags_manager.any_file_modified():
            log.debug(" .clang_complete or CMakeLists.txt were modified. "
                      "Need to reinit.")
            return True
        if self.exists_for_view(view.buffer_id()):
            log.debug(" view %s, already has a completer", view.buffer_id())
            return False
        log.debug(" need to init view '%s'", view.buffer_id())
        return True

    def remove(self, view_id):
        """
        Called when completion for this view is not needed anymore. For actual
        implementation see children of this class.

        Args:
            view_id (sublime.View): current view

        Raises:
            NotImplementedError: Guarantees we do not call this abstract method
        """
        raise NotImplementedError("calling abstract method")

    def exists_for_view(self, view_id):
        """
        Check if completer for this view is initialized and is ready to
        autocomplete. For real implementation see children.

        Args:
            view_id (int): view id

        Raises:
            NotImplementedError: Guarantees we do not call this abstract method
        """
        raise NotImplementedError("calling abstract method")

    def init_for_view(self, view, settings):
        """
        Initialize the completer for this view. For real implementation see
        children.

        Args:
            view (sublime.View): current view
            settings (Settings): plugin settings

        """
        current_dir = path.dirname(view.file_name())
        search_scope = SearchScope(
            from_folder=current_dir,
            to_folder=settings.project_folder)
        self.flags_manager = FlagsManager(
            view=view,
            settings=settings,
            compiler_variant=self.compiler_variant,
            search_scope=search_scope)
        log.debug(" flags_manager loaded")

    def complete(self, completion_request):
        """Function to generate completions. See children for implementation.

        Args:
            completion_request (CompletionRequest): request object

        Raises:
            NotImplementedError: Guarantees we do not call this abstract method
        """
        raise NotImplementedError("calling abstract method")

    def update(self, view, show_errors):
        """Update the completer for this view. This can increase consequent
        completion speeds or is needed to just show errors.

        Args:
            view (sublime.View): this view
            show_errors (bool): controls if we show errors

        Raises:
            NotImplementedError: Guarantees we do not call this abstract method
        """
        raise NotImplementedError("calling abstract method")

    def show_errors(self, view, output):
        """ Show current complie errors

        Args:
            view (sublime.View): Current view
            output (object): opaque output to be parsed by compiler variant
        """
        errors = self.compiler_variant.errors_from_output(output)
        self.error_vis.generate(view, errors)
        self.error_vis.show_regions(view)
