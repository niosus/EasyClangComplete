"""Test delayed thread pool."""
import time
from unittest import TestCase

import EasyClangComplete.plugin.utils.thread_pool
import EasyClangComplete.plugin.utils.thread_job

ThreadPool = EasyClangComplete.plugin.utils.thread_pool.ThreadPool
ThreadJob = EasyClangComplete.plugin.utils.thread_job.ThreadJob


def run_me(result):
    """Run this asyncronously."""
    time.sleep(0.2)
    return result


TIMEOUT = 5.0


class TestContainer():
    """A test container to store results of the operation."""

    def __init__(self):
        """Initialize this object."""
        self.futures = []

    def on_job_done(self, future):
        """Call this when the job is done."""
        self.futures.append(future)

    def wait_until_got_number_of_callbacks(self, number):
        """Wait until callback is called."""
        slept = 0.0
        time_step = 0.1
        while not len(self.futures) == number and slept < TIMEOUT:
            time.sleep(time_step)
            slept += time_step


class TestThreadPool(TestCase):
    """Test thread pool."""

    def test_single_job(self):
        """Test single job."""
        test_container = TestContainer()
        job = ThreadJob(name="test_job",
                        callback=test_container.on_job_done,
                        function=run_me,
                        args=[True])
        pool = ThreadPool()
        pool.new_job(job)
        test_container.wait_until_got_number_of_callbacks(1)
        self.assertGreater(len(test_container.futures), 0)
        self.assertFalse(test_container.futures[0].cancelled())
        self.assertTrue(test_container.futures[0].result())

    def test_override_job(self):
        """Test overriding job.

        The first job should be overridden by the next one.
        """
        test_container = TestContainer()
        job_1 = ThreadJob(name="test_job",
                          function=run_me,
                          callback=test_container.on_job_done,
                          args=["job_1"])
        job_2 = ThreadJob(name="test_job",
                          function=run_me,
                          callback=test_container.on_job_done,
                          args=["job_2"])
        job_3 = ThreadJob(name="test_job",
                          function=run_me,
                          callback=test_container.on_job_done,
                          args=["job_3"])
        pool = ThreadPool()
        pool.new_job(job_1)
        pool.new_job(job_2)
        pool.new_job(job_3)
        test_container.wait_until_got_number_of_callbacks(3)
        self.assertEqual(len(test_container.futures), 3)
        # Here is what happens. job_1 runs so cannot be cancelled by job_2, so
        # job_1 keeps running while job_2 is added to the queue. Then we add
        # job_3, which cancels job_2, which immediately calls it's callback,
        # thus the first future in the result is from job_2. Then job_1
        # eventually finishes. Then job_3 starts and finishes.
        self.assertTrue(test_container.futures[0].cancelled())
        self.assertFalse(test_container.futures[1].cancelled())
        self.assertEqual(test_container.futures[1].result(), "job_1")
        self.assertFalse(test_container.futures[2].cancelled())
        self.assertEqual(test_container.futures[2].result(), "job_3")
