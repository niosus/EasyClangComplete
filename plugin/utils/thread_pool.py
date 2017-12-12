"""Define a class for managing a thread pool with delayed execution.

Attributes:
    log (logging.Logger): Logger for current module.
"""
import time
import logging
from concurrent import futures
from threading import Lock
from threading import Thread

from ..tools import singleton

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
        """Define if one job is higher priority than the other."""
        if self.is_same_type_as(other):
            return True
        if self.__is_high_priority() and not other.__is_high_priority():
            return True
        return False

    def is_same_type_as(self, other):
        """Define if these are the same type of jobs."""
        return self.name == other.name


@singleton
class ThreadPool:
    """Thread pool that makes sure we don't get recurring jobs.

    Whenever a job is submitted we check if there is already a job like this
    running. If it is, we try to cancel the previous job. We are only able to
    cancel this job if it has not started yet.

    Example:

    active:     ['update', 'info'] and 'update' is running.
    incoming:   'update' and then another 'update'.

    We will try to cancel the first 'update' and will fail as it is running. We
    still cancel the 'info' job as it has less priority (no need to get info if
    the translation unit is not up to date). We add a new 'update' to the list.
    Now there are two 'update' jobs, one running, one pending. Adding another
    'update' job will replace the pending update job.
    """

    def __init__(self, max_workers=1):
        """Create a thread pool.

        Args:
            max_workers (int): Maximum number of parallel workers.
        """
        self.__thread_pool = futures.ThreadPoolExecutor(
            max_workers=max_workers)

        self.__lock = Lock()
        self.__progress_lock = Lock()

        self.__show_animation = False

        self.__progress_update_delay = 0.1
        self.__progress_idle_delay = 0.3

        # All the jobs that are currently active are stored here.
        self.__active_jobs = []

        # start animation thread
        self.__progress_status = None
        self.__progress_thread = Thread(target=self.__animate_progress,
                                        daemon=True).start()

    @property
    def progress_status(self):
        """Return current progress status."""
        return self.__progress_status

    @progress_status.setter
    def progress_status(self, val):
        """Set progress status instance."""
        with self.__progress_lock:
            self.__progress_status = val

    def new_job(self, job):
        """Add a new job to be submitted to a thread pool.

        Args:
            job (ThreadJob): A job to be run asynchronously.
        """
        # Cancel all the jobs with the same name that are already running.
        # Iterating over a list is atomic in python, so we should be safe.
        for active_job in self.__active_jobs:
            if job.overrides(active_job):
                if active_job.future.cancel():
                    log.debug("Canceled job: '%s'", job)
                else:
                    log.debug("Cannot cancel job: '%s'", active_job)
        # Submit a new job to the pool.
        future = self.__thread_pool.submit(job.function, *job.args)
        future.add_done_callback(job.callback)
        future.add_done_callback(self.__on_job_done)
        job.future = future  # Set the future for this job.
        with self.__lock:
            self.__active_jobs.append(job)
            self.__show_animation = True

    def __on_job_done(self, future):
        """Call this when the job is done or cancelled."""
        # We want to clear the old list and alter the positions of elements.
        # This is a potentially dangerous operation, so protect it by a mutex.
        with self.__lock:
            self.__active_jobs[:] = [
                job for job in self.__active_jobs if not job.future.done()]
            if len(self.__active_jobs) < 1:
                self.__show_animation = False

    def __animate_progress(self):
        """Change the status message, mostly used to animate progress."""
        while True:
            sleep_time = self.__progress_idle_delay
            with self.__progress_lock:
                if not self.__progress_status:
                    sleep_time = self.__progress_idle_delay
                elif self.__show_animation:
                    self.__progress_status.show_next_message()
                    sleep_time = self.__progress_update_delay
                else:
                    self.__progress_status.show_ready_message()
                    sleep_time = self.__progress_idle_delay
            # Allow some time for progress status to be updated.
            time.sleep(sleep_time)
