""" Encapsulates set augmented list with unique stored values """


class UniqueList:
    """ A list that guarantees unique insertion. """

    __values_set = set()
    __values = list()

    def __init__(self):
        """ init empty list """
        self.__values = list()
        self.__values_set = set()

    def __init__(self, other):
        """ init with another iterable """
        for value in other:
            self.append(value)

    def append(self, value):
        """ Append a single value
        Args:
            value: input value
        """
        if value not in self.__values_set:
            self.__values.append(value)
            self.__values_set.add(value)

    def clear(self):
        """ Clear the list """
        self.__values = list()
        self.__values_set = set()

    def __add__(self, other):
        """ Append another iterable
        Args:
            other (iterable): some other iterable container
        Returns:
            UniqueList: new list with appended elements
        """
        for value in other:
            self.append(value)
        return self

    def __iter__(self):
        """ make iterable """
        return iter(self.__values)

    def __str__(self):
        """ make convertable to str """
        return str(self.__values)
