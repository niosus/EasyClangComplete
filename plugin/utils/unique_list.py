"""Encapsulates set augmented list with unique stored values."""


class UniqueList:
    """A list that guarantees unique insertion."""

    def __init__(self, other=None):
        """Init with another iterable if it is present."""
        self.__values = list()
        self.__values_set = set()
        if not other:
            return
        for value in other:
            self.append(value)

    def append(self, value):
        """Append a single value.

        Args:
            value: input value
        """
        if value not in self.__values_set:
            self.__values.append(value)
            self.__values_set.add(value)

    def as_list(self):
        """Return an ordinary python list."""
        return self.__values

    def clear(self):
        """Clear the list."""
        self.__values = list()
        self.__values_set = set()

    def __add__(self, other):
        """Append another iterable.

        Args:
            other (iterable): some other iterable container
        Returns:
            UniqueList: new list with appended elements
        """
        for value in other:
            self.append(value)
        return self

    def __iter__(self):
        """Make iterable."""
        return iter(self.__values)

    def __str__(self):
        """Make convertable to str."""
        return str(self.__values)
