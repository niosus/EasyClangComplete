"""This file defines a class for managing a thread pool with delayed execution.

Attributes:
    log (logging.Logger): Logger for current module.
"""
import logging
from concurrent import futures
from threading import Timer
from threading import RLock

log = logging.getLogger(__name__)


class ThreadJob:
    """A class for a job that can be submitted to ThreadPool.

    Attributes:
        name (str): Name of this job.
        callback (func): Function to use as callback.
        function (func): Function to run asyncronously.
        args (object[]): Sequence of additional arguments for `function`.
    """

    def __init__(self, name, callback, function, args):
        """Initialize a job.

        Args:
            name (str): Name of this job.
            callback (func): Function to use as callback.
            function (func): Function to run asyncronously.
            args (object[]): Sequence of additional arguments for `function`.
        """
        self.name = name
        self.callback = callback
        self.function = function
        self.args = args

    def __repr__(self):
        """Representation."""
        return "job: '{name}', args: ({args})".format(
            name=self.name, args=self.args)


class ThreadPool:
    """Thread pool that makes sure we don't get recurring jobs.

    Whenever a job is submitted to this pool, the pool waits for a specified
    amount of time before actually submitting the job to an async pool of
    threads. Therefore we avoid running similar jobs over and over again.
    """

    __lock = RLock()
    __jobs_to_run = {}

    def __init__(self, max_workers, run_delay=0.05):
        """Create a thread pool.

        Args:
            max_workers (int): Maximum number of parallel workers.
            run_delay (float, optional): Time of delay in seconds.
        """
        self.__timer = None
        self.__delay = run_delay
        self.__thread_pool = futures.ThreadPoolExecutor(
            max_workers=max_workers)

    def restart_timer(self):
        """Restart timer because there was a change in jobs."""
        if self.__timer:
            self.__timer.cancel()
        self.__timer = Timer(self.__delay, self.submit_jobs)
        self.__timer.start()

    def submit_jobs(self):
        """Submit jobs that survived the delay."""
        with ThreadPool.__lock:
            for job in ThreadPool.__jobs_to_run.values():
                log.debug("submitting job: %s", job)
                future = self.__thread_pool.submit(job.function, *job.args)
                future.add_done_callback(job.callback)
            ThreadPool.__jobs_to_run.clear()

    def new_job(self, job):
        """Add a new job to be submitted.

        Args:
            job (ThreadJob): A job to be run asyncronously.
        """
        with ThreadPool.__lock:
            ThreadPool.__jobs_to_run[job.name] = job
            self.restart_timer()
