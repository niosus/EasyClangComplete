"""Test compilation database flags generation."""
import imp

from EasyClangComplete.tests.gui_test_wrapper import GuiTestWrapper
from EasyClangComplete.plugin.utils import quick_panel_handler
imp.reload(quick_panel_handler)

QuickPanelHandler = quick_panel_handler.QuickPanelHandler


class test_panel_handler(GuiTestWrapper):
    """Test unique list."""

    def test_init(self):
        """Test initialization."""
        self.set_up_view()
        errors = [{"hello": "world"}]
        panel_handler = QuickPanelHandler(self.view, errors)
        self.assertEqual(self.view, panel_handler.view)
        self.assertEqual(errors, panel_handler.errors)

    def test_items_to_show(self):
        """Test that the items are well formatted."""
        self.set_up_view()
        errors = [
            {
                "severity": 3,
                "error": "ERROR_MSG",
                "file": "error_file"
            },
            {
                "severity": 2,
                "error": "WARNING_MSG",
                "file": "warning_file"
            }
        ]
        panel_handler = QuickPanelHandler(self.view, errors)
        items_to_show = panel_handler.items_to_show()
        expected = [["ERROR: ERROR_MSG", "error_file"],
                    ["WARNING: WARNING_MSG", "warning_file"]]
        self.assertEqual(items_to_show, expected)

    def test_on_done(self):
        """Test that the items are well formatted."""
        self.set_up_view()
        errors = [
            {
                "severity": 3,
                "error": "ERROR_MSG",
                "file": "error_file",
                "row": 0,
                "col": 0
            },
        ]
        panel_handler = QuickPanelHandler(self.view, errors)
        self.assertIsNone(panel_handler.on_done(-1))
        self.assertIsNone(panel_handler.on_done(1))
        view = panel_handler.on_done(0)
        self.assertIsNotNone(view)
        view.set_scratch(True)
        view.window().focus_view(view)
        view.window().run_command("close_file")
