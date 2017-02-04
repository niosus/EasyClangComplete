import logging
from concurrent import futures
from threading import Timer
from threading import RLock

log = logging.getLogger(__name__)


class ThreadJob:
    """docstring for ThreadJob"""

    def __init__(self, name, callback, function, args):
        self.name = name
        self.callback = callback
        self.function = function
        self.args = args

    def __repr__(self):
        return "job: '{name}', args: ({args})".format(
            name=self.name, args=self.args)


class ThreadPool:
    """docstring for ThreadPool"""

    __lock = RLock()
    __jobs_to_run = {}

    def __init__(self, max_workers, run_delay=0.05):
        self.__timer = None
        self.__delay = run_delay
        self.__thread_pool = futures.ThreadPoolExecutor(
            max_workers=max_workers)

    def restart_timer(self):
        if self.__timer:
            self.__timer.cancel()
        self.__timer = Timer(self.__delay, self.submit_jobs)
        self.__timer.start()

    def submit_jobs(self):
        with ThreadPool.__lock:
            for job in ThreadPool.__jobs_to_run.values():
                log.debug("submitting job: %s", job)
                future = self.__thread_pool.submit(job.function, *job.args)
                future.add_done_callback(job.callback)

    def new_job(self, job):
        with ThreadPool.__lock:
            ThreadPool.__jobs_to_run[job.name] = job
            self.restart_timer()
