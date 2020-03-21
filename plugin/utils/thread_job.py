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

    UPDATE_TAG = "Updating translation unit"
    CLEAR_TAG = "Clearing"
    COMPLETE_TAG = "Completing"
    COMPLETE_INCLUDES_TAG = "Competing includes"
    GENERATE_DB_TAG = "Generating compilation database"
    INFO_TAG = "Showing info"

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
        return self.name in [ThreadJob.UPDATE_TAG,
                             ThreadJob.CLEAR_TAG,
                             ThreadJob.GENERATE_DB_TAG]

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
