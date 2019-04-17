"""Defines all search scopes used in this project."""
from os import path

ROOT_PATH = path.abspath('/')


class TreeSearchScope:
    """Encapsulation of a search scope to search up the tree."""

    def __init__(self,
                 from_folder=ROOT_PATH,
                 to_folder=ROOT_PATH):
        """Initialize the search scope."""
        self.from_folder = from_folder
        self.to_folder = to_folder

    @property
    def from_folder(self):
        """Get the starting folder."""
        return self._from_folder

    @from_folder.setter
    def from_folder(self, folder):
        """Set the last folder in search."""
        self._from_folder = folder
        self._current_folder = self._from_folder

    @property
    def to_folder(self):
        """Get the end of search folder."""
        return self._to_folder

    @to_folder.setter
    def to_folder(self, folder):
        """Set the last folder in search."""
        self._to_folder = folder
        self._one_past_last = path.dirname(self._to_folder)

    def __bool__(self):
        """Check if the search scope is empty."""
        return self.from_folder != ROOT_PATH

    def __iter__(self):
        """Make this an iterator."""
        self._current_folder = self._from_folder
        return self

    def __next__(self):
        """Get next folder to search in."""
        current_folder = self._current_folder
        self._current_folder = path.dirname(self._current_folder)
        scope_end_reached = current_folder == self._one_past_last
        root_reached = current_folder == self._current_folder
        if root_reached or scope_end_reached:
            raise StopIteration
        else:
            return current_folder

    def __repr__(self):
        """Return search scope as a printable string."""
        return 'SearchScope: from_folder: {}, to_folder: {}'.format(
            self._from_folder, self._to_folder)


class ListSearchScope:
    """Encapsulation of a search scope to search in a list."""

    def __init__(self, paths=[]):
        """Initialize the search scope."""
        self.folders = paths

    @property
    def folders(self):
        """Get the starting folder."""
        return self._folders

    @folders.setter
    def folders(self, paths):
        """Set the folders."""
        self._folders = [f for f in paths if path.isdir(f)]
        self._iter = iter(self._folders)

    def __bool__(self):
        """Check if the search scope is not empty."""
        return len(self._folders) > 0

    def __iter__(self):
        """Make this an iterator."""
        self._iter = iter(self._folders)
        return self._iter

    def __next__(self):
        """Get next folder to search in."""
        return next(self._iter)

    def __repr__(self):
        """Return search scope as a printable string."""
        return 'SearchScope: folders: {}'.format(self._folders)
