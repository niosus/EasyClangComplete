"""This file defines a class for managing a thread pool with delayed execution.

Attributes:
    log (logging.Logger): Logger for current module.
"""
import time
import logging
from concurrent import futures
from threading import Timer
from threading import RLock
from threading import Thread

log = logging.getLogger("ECC")


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
    __progress_lock = RLock()

    __jobs_to_run = {}
    __running_jobs_count = 0
    __show_animation = False

    __progress_update_delay = 0.1
    __progress_idle_delay = 0.3

    def __init__(self, max_workers, run_delay=0.1):
        """Create a thread pool.

        Args:
            max_workers (int): Maximum number of parallel workers.
            run_delay (float, optional): Time of delay in seconds.
        """
        self.__timer = None
        self.__delay = run_delay
        self.__thread_pool = futures.ThreadPoolExecutor(
            max_workers=max_workers)

        # start animation thread
        self.__progress_status = None
        self.__progress_thread = Thread(target=self.__animate_progress,
                                        daemon=True)
        self.__progress_thread.start()

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
        """Add a new job to be submitted.

        Args:
            job (ThreadJob): A job to be run asyncronously.
        """
        with ThreadPool.__lock:
            ThreadPool.__jobs_to_run[job.name] = job
            self.__restart_timer()

    def __restart_timer(self):
        """Restart timer because there was a change in jobs."""
        if self.__timer:
            self.__timer.cancel()
        self.__timer = Timer(self.__delay, self.__submit_jobs)
        self.__timer.start()

    def __submit_jobs(self):
        """Submit jobs that survived the delay."""
        with ThreadPool.__lock:
            for job in ThreadPool.__jobs_to_run.values():
                log.debug("submitting job: %s", job)
                future = self.__thread_pool.submit(job.function, *job.args)
                future.add_done_callback(job.callback)
                future.add_done_callback(self.__stop_progress_animation)
                self.__running_jobs_count += 1
            ThreadPool.__jobs_to_run.clear()
            log.debug("running %s jobs", self.__running_jobs_count)
            if self.__running_jobs_count > 0:
                self.__progress_status.showing = True
                self.__show_animation = True

    def __stop_progress_animation(self, future):
        """Stop progress animation thread if there are no running jobs."""
        with ThreadPool.__lock:
            self.__running_jobs_count -= 1
            log.debug("Jobs still running: %s", self.__running_jobs_count)
            if self.__running_jobs_count < 1:
                log.debug("Stopping progress animation.")
                self.__show_animation = False

    def __animate_progress(self):
        """Function that changes the status message, i.e animates progress."""
        while True:
            sleep_time = ThreadPool.__progress_idle_delay
            with self.__progress_lock:
                if not self.__progress_status:
                    sleep_time = ThreadPool.__progress_idle_delay
                elif self.__show_animation:
                    self.__progress_status.show_next_message()
                    sleep_time = ThreadPool.__progress_update_delay
                else:
                    self.__progress_status.show_ready_message()
                    sleep_time = ThreadPool.__progress_idle_delay
            # allow some time for progress status to be updated
            time.sleep(sleep_time)
