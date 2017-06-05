"""Test delayed thread pool."""
import imp
import time
from unittest import TestCase

import EasyClangComplete.plugin.utils.thread_pool

imp.reload(EasyClangComplete.plugin.utils.thread_pool)

ThreadPool = EasyClangComplete.plugin.utils.thread_pool.ThreadPool
ThreadJob = EasyClangComplete.plugin.utils.thread_pool.ThreadJob


def run_me(succeed):
    """A simple function to run asyncronously."""
    return succeed


class test_thread_pool(TestCase):
    """Test thread pool."""

    def callback_func(self, future):
        """Simple callback function to store result."""
        self.last_result = future.result()

    def override_func(self, future):
        """Simple callback function to store overridable result."""
        self.override_result = future.result()

    def test_single_job(self):
        """Test single job."""
        job = ThreadJob(name="test_job",
                        callback=self.callback_func,
                        function=run_me,
                        args=[True])
        pool = ThreadPool(max_workers=4)
        pool.new_job(job)
        time.sleep(0.2)
        self.assertTrue(self.last_result)

    def test_fail_job(self):
        """Test fail job."""
        job = ThreadJob(name="test_job",
                        callback=self.callback_func,
                        function=run_me,
                        args=[False])
        pool = ThreadPool(max_workers=4)
        pool.new_job(job)
        time.sleep(0.2)
        self.assertFalse(self.last_result)

    def test_override_job(self):
        """Test overriding job.

        The first job should be overridden by the next one.
        """
        job_good = ThreadJob(name="test_job",
                             callback=self.override_func,
                             function=run_me,
                             args=[True])
        job_bad = ThreadJob(name="test_job",
                            callback=self.override_func,
                            function=run_me,
                            args=[False])
        pool = ThreadPool(max_workers=4)
        pool.new_job(job_bad)
        pool.new_job(job_good)
        time.sleep(0.2)
        self.assertTrue(self.override_result)
