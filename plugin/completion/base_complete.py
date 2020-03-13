"""Contains base class for completers.

Attributes:
    log (logging.Logger): logger for this module

"""
import logging

from ..utils.subl.subl_bridge import SublBridge

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
        # Store the latest errors here
        self.latest_errors = None

    def complete(self, completion_request):
        """Generate completions. See children for implementation.

        Args:
            completion_request (ActionRequest): request object

        Raises:
            NotImplementedError: Guarantees we do not call this abstract method
        """
        raise NotImplementedError("calling abstract method")

    def info(self, tooltip_request, settings):
        """Provide information about object in given location.

        Using the current translation unit it queries libclang for available
        information about cursor.

        Args:
            tooltip_request (tools.ActionRequest): A request for action
                from the plugin.
            settings: All plugin settings.

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

    def get_declaration_location(self, view, row_col):
        """Get location of declaration from given location in file.

        Args:
            view (sublime.View): current view.
            row_col (ZeroBasedRowCol): location of the cursor.

        Returns:
            Location: location of declaration
        """
        raise NotImplementedError("calling abstract method")

    def save_errors(self, output):
        """Generate and store the errors.

        Args:
            output (object): opaque output to be parsed by compiler variant
        """
        self.latest_errors = self.compiler_variant.errors_from_output(output)

    def show_errors(self, view):
        """Show current complie errors.

        Args:
            view (sublime.View): Current view
        """
        if not SublBridge.is_valid_view(view):
            log.error("cannot show errors. View became invalid!")
            return
        self.error_vis.generate(view, self.latest_errors)
        self.error_vis.show_errors(view)
