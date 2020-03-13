"""Represent different ways to work with row and column in views."""


class ZeroIndexedRowCol():
    """A cursor position as 0-indexed row and column."""

    def __init__(self, row, col):
        """Initialize from row and column as seen in file (start with 1)."""
        self._row = row
        self._col = col

    @property
    def row(self):
        """Return row."""
        return self._row

    @property
    def col(self):
        """Return col."""
        return self._col

    def as_1d_location(self, view):
        """Return the cursor position as 1d location in a view."""
        return view.text_point(self._row, self._col)

    @staticmethod
    def from_one_indexed(one_indexed_row_col):
        """Convert 1-indexed row column into the 0-indexed representation."""
        return ZeroIndexedRowCol(one_indexed_row_col._row - 1,
                                 one_indexed_row_col._col - 1)

    @staticmethod
    def from_1d_location(view, pos):
        """Get row and column from a 1d location in a view."""
        if pos is None:
            return ZeroIndexedRowCol.from_current_cursor_pos(view)
        row, col = view.rowcol(pos)
        return ZeroIndexedRowCol(row, col)

    @classmethod
    def from_current_cursor_pos(cls, view):
        """Generate row and columg from current cursor position in view."""
        pos = view.sel()
        if pos is None or len(pos) < 1:
            # something is wrong
            return None
        # We care about the first position only.
        pos = pos[0].a
        return cls.from_1d_location(view, pos)

    def as_tuple(self):
        """Return as tuple."""
        return (self._row, self._col)


class OneIndexedRowCol():
    """Stores a cursor position."""

    def __init__(self, row, col):
        """Initialize from a zero-indexed row and column."""
        self._row = row
        self._col = col

    @staticmethod
    def from_zero_indexed(zero_indexed_row_col):
        """Convert 0-indexed row column into the 1-indexed representation."""
        return ZeroIndexedRowCol(zero_indexed_row_col._row + 1,
                                 zero_indexed_row_col._col + 1)

    @property
    def row(self):
        """Return row."""
        return self._row

    @property
    def col(self):
        """Return col."""
        return self._col

    def as_tuple(self):
        """Return as tuple."""
        return (self._row, self._col)
