class Flag:
    """ utility class for storing possibly separated flag """

    __prefix = None
    __body = None

    def __init__(self, part_1, part_2=None):
        if part_2:
            self.__prefix = part_1
            self.__body = part_2
        else:
            self.__body = part_1

    def prefix():
        return __prefix

    def body():
        return __body

    def as_list(self):
        if self.__prefix:
            return [self.__prefix] + [self.__body]
        return [self.__body]

    def __str__(self):
        if self.__prefix:
            return self.__prefix + " " + self.__body
        return self.__body

    def __hash__(self):
        if self.__prefix:
            return hash(self.__prefix) + hash(self.__body)
        return hash(self.__body)
