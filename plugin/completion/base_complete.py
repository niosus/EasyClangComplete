"""Contains base class for completers.

Attributes:
    log (logging.Logger): logger for this module

"""
import logging

from .. import error_vis
from ..tools import Tools

log = logging.getLogger(__name__)


class BaseCompleter:
    """A base class for clang based completions.

    Attributes:
        completions (list): current list of completions
        error_vis (plugin.CompileErrors): object of compile errors class
        compiler_variant (CompilerVariant): compiler specific options
        valid (bool): is completer valid
        version_str (str): version string of format "3.4.0"
    """
    name = "base"
    version_str = None
    error_vis = None
    compiler_variant = None

    valid = False

    def __init__(self, clang_binary, version_str):
        """Initialize the BaseCompleter.

        Args:
            clang_binary (str): string for clang binary e.g. 'clang-3.6++'

        Raises:
            RuntimeError: if clang not defined we throw an error

        """
        # check if clang binary is defined
        if not clang_binary:
            raise RuntimeError("clang binary not defined")

        self.version_str = version_str
        # initialize error visualization
        self.error_vis = error_vis.CompileErrors()

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
        if not Tools.is_valid_view(view):
            log.error(" cannot show errors. View became invalid!")
            return
        self.error_vis.generate(view, errors)
        self.error_vis.show_regions(view)
