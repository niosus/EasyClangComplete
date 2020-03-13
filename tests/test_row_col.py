"""Tests for classes incapsulating row and column positions."""
import imp
from os import path

from EasyClangComplete.plugin.utils.subl import row_col
from EasyClangComplete.tests.gui_test_wrapper import GuiTestWrapper

imp.reload(row_col)

ZeroIndexedRowCol = row_col.ZeroIndexedRowCol
OneIndexedRowCol = row_col.OneIndexedRowCol


class TestRowCol(GuiTestWrapper):
    """Test getting flags from CMakeLists.txt."""

    def test_setup_view(self):
        """Test that setup view correctly sets up the view."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        self.check_view(file_name)

    def test_init(self):
        """Initialization test."""
        pos = ZeroIndexedRowCol(4, 2)
        self.assertEquals(pos.row, 4)
        self.assertEquals(pos.col, 2)
        self.assertEquals((4, 2), pos.as_tuple())

    def test_init_from_one_indexed(self):
        """Initialization test from 1-indexed row and column."""
        pos = ZeroIndexedRowCol.from_one_indexed(OneIndexedRowCol(4, 2))
        self.assertEquals(pos.row, 3)
        self.assertEquals(pos.col, 1)
        self.assertEquals((3, 1), pos.as_tuple())

    def test_init_from_zero_indexed(self):
        """Initialization test from 0-indexed row and column."""
        pos = OneIndexedRowCol.from_zero_indexed(ZeroIndexedRowCol(4, 2))
        self.assertEquals(pos.row, 5)
        self.assertEquals(pos.col, 3)
        self.assertEquals((5, 3), pos.as_tuple())

    def test_location(self):
        """Location is valid."""
        file_name = path.join(path.dirname(__file__),
                              'test_files',
                              'test.cpp')
        self.set_up_view(file_name)
        pos = ZeroIndexedRowCol(4, 2)
        self.assertEquals(pos.row, 4)
        self.assertEquals(pos.col, 2)
        location = pos.as_1d_location(self.view)
        pos_from_location = ZeroIndexedRowCol.from_1d_location(
            self.view, location)
        self.assertEquals(pos.row, pos_from_location.row)
        self.assertEquals(pos.col, pos_from_location.col)

        default_location = ZeroIndexedRowCol.from_1d_location(self.view, None)
        self.assertEquals(0, default_location.row)
        self.assertEquals(0, default_location.col)
