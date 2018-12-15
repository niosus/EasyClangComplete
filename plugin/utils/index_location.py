"""Class that mimics cursor.location for dealing with index locations."""

from os import path


class IndexLocation:
    """Location of a file that mimics Cursor.location."""

    class File:
        """Help class to mimic Cursor.file."""

        def __init__(self, name):
            """Initialize file name."""
            # 'name' is a bad name for a variable, but we need it to be this way
            # to conform with cursor.location.
            self.name = name
            self.extension = path.splitext(name)[1]
            self.short_name = path.basename(name)

    def __init__(self, filename, line, column):
        """Initialize new location."""
        self.file = IndexLocation.File(filename)
        self.line = line
        self.column = column
