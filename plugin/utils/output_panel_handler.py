"""Handle everything related to the output panel."""
import sublime


class OutputPanelHandler():
    """Handle the output panel."""
    _PANEL_TAG = "ECC"

    @staticmethod
    def hide_panel():
        """Hide the output panel."""
        window = sublime.active_window()
        window.run_command(
            "hide_panel", {"panel": "output." + OutputPanelHandler._PANEL_TAG})

    @staticmethod
    def show(text):
        """Show the panel with text."""
        import time
        window = sublime.active_window()
        window.destroy_output_panel(OutputPanelHandler._PANEL_TAG)
        panel_view = window.create_output_panel(
            OutputPanelHandler._PANEL_TAG)
        while panel_view.is_loading():
            time.sleep(0.1)
        panel_view.run_command("select_all")
        panel_view.run_command("right_delete")

        settings = panel_view.settings()
        settings.set("tab_size", 0)
        settings.set("line_numbers", True)
        panel_view.run_command("insert", {"characters": text})
        panel_view.sel().clear()
        panel_view.show(panel_view.size())

        window.run_command(
            "show_panel", {"panel": "output." + OutputPanelHandler._PANEL_TAG})
        panel_view.set_read_only(True)
