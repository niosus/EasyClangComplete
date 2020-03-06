"""Test tools.

Attributes:
    easy_clang_complete (module): this plugin module
    SublBridge (SublBridge): class for subl bridge
"""
import imp

from os import path

from EasyClangComplete.tests.gui_test_wrapper import GuiTestWrapper
from EasyClangComplete.plugin.utils import action_request
from EasyClangComplete.plugin.utils import subl_bridge

imp.reload(action_request)
imp.reload(subl_bridge)

ActionRequest = action_request.ActionRequest
CursorPosition = subl_bridge.CursorPosition


class test_action_request(GuiTestWrapper):
    """Test other things."""

    def test_setup_view(self):
        """Test that setup view correctly sets up the view."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        self.check_view(file_name)

    def test_round_trip(self):
        """Test that we can create another location from rowcol of the view."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        query_pos = CursorPosition(row=5, col=9)
        self.set_up_view(file_path=file_name, cursor_position=query_pos)
        self.assertEqual(self.get_row(query_pos.row), "  void foo(double a);")
        (row, col) = self.view.rowcol(query_pos.location(self.view))
        equal_pos = CursorPosition(row=row + 1, col=col + 1)
        self.assertEqual(equal_pos.row, query_pos.row)
        self.assertEqual(equal_pos.col, query_pos.col)
        self.assertEqual(equal_pos.location(self.view),
                         query_pos.location(self.view))

    def test_create(self):
        """Test creation."""
        self.set_up_view()
        expected_trigger_position = 42
        action_request = ActionRequest(self.view, expected_trigger_position)
        self.assertEqual(expected_trigger_position,
                         action_request.get_trigger_position())
        self.assertEqual(self.view.buffer_id(),
                         action_request.get_view().buffer_id())
        expected_identifier = (self.view.buffer_id(), expected_trigger_position)
        self.assertEqual(expected_identifier, action_request.get_identifier())

    def test_suitable(self):
        """Test that we detect if the view is suitable."""
        file_path = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        query_pos = CursorPosition(row=5, col=9)
        self.set_up_view(file_path=file_path, cursor_position=query_pos)
        self.assertEqual(self.get_row(query_pos.row), "  void foo(double a);")
        trigger_position = self.view.text_point(query_pos.row, query_pos.col)
        current_word = self.view.substr(self.view.word(trigger_position))
        self.assertEqual(current_word, "foo")

        action_request = ActionRequest(self.view, trigger_position)
        self.assertTrue(action_request.is_suitable_for_view(self.view))

    def test_not_suitable_location(self):
        """Test that we detect if the view is suitable."""
        file_path = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        query_pos = CursorPosition(row=5, col=9)
        self.set_up_view(file_path=file_path, cursor_position=query_pos)
        self.assertEqual(self.get_row(query_pos.row), "  void foo(double a);")
        trigger_position = self.view.text_point(query_pos.row, query_pos.col)
        current_word = self.view.substr(self.view.word(trigger_position))
        self.assertEqual(current_word, "foo")

        wrong_trigger_position = 42
        action_request = ActionRequest(self.view, wrong_trigger_position)
        self.assertFalse(action_request.is_suitable_for_view(self.view))

    def test_not_suitable_view(self):
        """Test that we detect if the view is suitable."""
        self.set_up_view()

        default_trigger_position = 0
        action_request = ActionRequest(self.view, default_trigger_position)
        self.assertTrue(action_request.is_suitable_for_view(self.view))

        self.tearDown()
        self.setUp()
        self.set_up_view()
        self.assertFalse(action_request.is_suitable_for_view(self.view))
