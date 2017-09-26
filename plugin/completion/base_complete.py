"""Contains base class for completers.

Attributes:
    log (logging.Logger): logger for this module

"""
import logging

from ..tools import Tools

log = logging.getLogger("ECC")


class BaseCompleter:
    """A base class for clang based completions.

    Attributes:
        compiler_variant (CompilerVariant): compiler specific options
        valid (bool): is completer valid
        version_str (str): version string of format "3.4.0"
        error_vis (obj): an object of error visualizer
    """
    name = "base"

    valid = False

    def __init__(self, settings, error_vis):
        """Initialize the BaseCompleter.

        Args:
            settings (SettingsStorage): an object that stores current settings
            error_vis (ErrorVis): an object of error visualizer

        Raises:
            RuntimeError: if clang not defined we throw an error

        """
        # check if clang binary is defined
        if not settings.clang_binary:
            raise RuntimeError("clang binary not defined")

        self.compiler_variant = None
        self.version_str = settings.clang_version
        self.clang_binary = settings.clang_binary
        # initialize error visualization
        self.error_vis = error_vis

    def complete(self, completion_request):
        """Function to generate completions. See children for implementation.

        Args:
            completion_request (ActionRequest): request object

        Raises:
            NotImplementedError: Guarantees we do not call this abstract method
        """
        raise NotImplementedError("calling abstract method")

    def info(self, tooltip_request):
        """Provide information about object in given location.

        Using the current translation unit it queries libclang for available
        information about cursor.

        Args:
            tooltip_request (tools.ActionRequest): A request for action
                from the plugin.

        Raises:
            NotImplementedError: Guarantees we do not call this abstract method
        """
        raise NotImplementedError("calling abstract method")

    def update(self, view, settings):
        """Update the completer for this view.

        This can increase consequent completion speeds or is needed to just
        show errors.

        Args:
            view (sublime.View): this view
            settings: all plugin settings

        Raises:
            NotImplementedError: Guarantees we do not call this abstract method
        """
        raise NotImplementedError("calling abstract method")

    def get_reference(self, view):
        """Get location to declaration/definition from given location.

        Args:
            view (sublime.View): current view

        Returns:
            Location: location to declaration/definition
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
            log.error("cannot show errors. View became invalid!")
            return
        self.error_vis.generate(view, errors)
        self.error_vis.show_errors(view)
