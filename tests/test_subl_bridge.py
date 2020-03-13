"""Test tools.

Attributes:
    easy_clang_complete (module): this plugin module
    SublBridge (SublBridge): class for subl bridge
"""
import imp
from os import path

from EasyClangComplete.plugin.settings import settings_manager
from EasyClangComplete.plugin.utils.subl import subl_bridge

from EasyClangComplete.tests.gui_test_wrapper import GuiTestWrapper


imp.reload(settings_manager)
imp.reload(subl_bridge)

SettingsManager = settings_manager.SettingsManager

SublBridge = subl_bridge.SublBridge
PosStatus = subl_bridge.PosStatus


class test_tools_command(GuiTestWrapper):
    """Test sublime commands."""

    def set_text(self, string):
        """Set text to a view.

        Args:
            string (str): some string to set
        """
        self.view.run_command("insert", {"characters": string})

    def move(self, dist, forward=True):
        """Move the cursor by distance.

        Args:
            dist (int): pixels to move
            forward (bool, optional): forward or backward in the file

        """
        for _ in range(dist):
            self.view.run_command("move",
                                  {"by": "characters", "forward": forward})

    def test_next_line(self):
        """Test returning next line."""
        self.set_up_view()
        self.set_text("hello\nworld!")
        self.move(10, forward=False)
        next_line = SublBridge.next_line(self.view)
        self.assertEqual(next_line, "world!")

    def test_wrong_triggers(self):
        """Test that we don't complete on numbers and wrong triggers."""
        self.set_up_view(path.join(path.dirname(__file__),
                                   'test_files',
                                   'test_wrong_triggers.cpp'))
        # Load the completions.
        manager = SettingsManager()
        settings = manager.user_settings()

        # Check the current cursor position is completable.
        self.assertEqual(self.get_row(2), "  a > 2.")

        # check that '>' does not trigger completions
        pos = self.view.text_point(2, 5)
        current_word = self.view.substr(self.view.word(pos))
        self.assertEqual(current_word, "> ")
        status = SublBridge.get_pos_status(pos, self.view, settings)

        # Verify that we got the expected completions back.
        self.assertEqual(status, PosStatus.WRONG_TRIGGER)

        # check that 'a' does not trigger completions
        pos = self.view.text_point(2, 3)
        current_word = self.view.substr(self.view.word(pos))
        self.assertEqual(current_word, "a")

        status = SublBridge.get_pos_status(pos, self.view, settings)

        # Verify that we got the expected completions back.
        self.assertEqual(status, PosStatus.COMPLETION_NOT_NEEDED)

        # check that '2.' does not trigger completions
        pos = self.view.text_point(2, 8)
        current_word = self.view.substr(self.view.word(pos))
        self.assertEqual(current_word, ".\n")

        status = SublBridge.get_pos_status(pos, self.view, settings)

        # Verify that we got the expected completions back.
        self.assertEqual(status, PosStatus.WRONG_TRIGGER)
