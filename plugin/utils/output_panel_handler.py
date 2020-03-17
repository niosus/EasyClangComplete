"""Handle everything related to the output panel."""
import sublime


class OutputPanelHandler():
    """Handle the output panel."""
    _PANEL_TAG = "ECC"

    @staticmethod
    def show(text):
        """Show the panel with text."""
        window = sublime.active_window()
        panel_view = window.find_output_panel(OutputPanelHandler._PANEL_TAG)
        if panel_view is None:
            panel_view = window.create_output_panel(
                OutputPanelHandler._PANEL_TAG)
        panel_view.run_command("insert", {"characters": text})
