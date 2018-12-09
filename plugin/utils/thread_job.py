"""Class that defined a job to be run in a thread pool.

Attributes:
    log (logging.Logger): Logger for current module.
"""
import logging


log = logging.getLogger("ECC")


class ThreadJob:
    """A class for a job that can be submitted to ThreadPool.

    Attributes:
        name (str): Name of this job.
        callback (func): Function to use as callback.
        function (func): Function to run asynchronously.
        args (object[]): Sequence of additional arguments for `function`.
    """

    UPDATE_TAG = "update"
    CLEAR_TAG = "clear"
    COMPLETE_TAG = "complete"
    COMPLETE_INCLUDES_TAG = "complete_includes"
    INFO_TAG = "info"

    def __init__(self, name, callback, function, args):
        """Initialize a job.

        Args:
            name (str): Name of this job.
            callback (func): Function to use as callback.
            function (func): Function to run asynchronously.
            args (object[]): Sequence of additional arguments for `function`.
            future (future): A future that tracks the execution of this job.
        """
        self.name = name
        self.callback = callback
        self.function = function
        self.args = args
        self.future = None

    def __is_high_priority(self):
        """Check if job is high priority."""
        is_update = self.name == ThreadJob.UPDATE_TAG
        is_clear = self.name == ThreadJob.CLEAR_TAG
        return is_update or is_clear

    def __repr__(self):
        """Representation."""
        return "job: '{name}'".format(name=self.name)

    def overrides(self, other):
        """Define if one job overrides another."""
        if self.is_same_type_as(other):
            return True
        if self.__is_high_priority() and not other.__is_high_priority():
            return True
        return False

    def is_same_type_as(self, other):
        """Define if these are the same type of jobs."""
        return self.name == other.name
