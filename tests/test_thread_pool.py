"""Test delayed thread pool."""
import time
from unittest import TestCase

import EasyClangComplete.plugin.utils.singleton_thread_pool
import EasyClangComplete.plugin.utils.thread_job

ThreadPool = EasyClangComplete.plugin.utils.singleton_thread_pool.ThreadPool
ThreadJob = EasyClangComplete.plugin.utils.thread_job.ThreadJob


def run_me(succeed):
    """Run this asyncronously."""
    time.sleep(0.1)
    return succeed


class TestContainer():
    """A test container to store results of the operation."""

    def __init__(self, cancelled, result):
        """Initialize this object."""
        self.cancelled = cancelled
        self.result = result

    def on_job_done(self, future):
        """Call this when the job is done."""
        if future.cancelled():
            self.cancelled = True
            self.result = False
            return
        self.result = future.result()


class test_thread_pool(TestCase):
    """Test thread pool."""

    def test_single_job(self):
        """Test single job."""
        test_container = TestContainer(False, False)
        job = ThreadJob(name="test_job",
                        callback=test_container.on_job_done,
                        function=run_me,
                        args=[True])
        pool = ThreadPool()
        pool.new_job(job)
        time.sleep(0.2)
        self.assertTrue(test_container.result)

    def test_fail_job(self):
        """Test fail job."""
        test_container = TestContainer(False, False)
        job = ThreadJob(name="test_job",
                        callback=test_container.on_job_done,
                        function=run_me,
                        args=[False])
        pool = ThreadPool()
        pool.new_job(job)
        time.sleep(0.2)
        self.assertFalse(test_container.result)

    def test_override_job(self):
        """Test overriding job.

        The first job should be overridden by the next one.
        """
        test_container = TestContainer(False, False)
        job_good = ThreadJob(name="test_job",
                             function=run_me,
                             callback=test_container.on_job_done,
                             args=[True])
        job_bad = ThreadJob(name="test_job",
                            function=run_me,
                            callback=test_container.on_job_done,
                            args=[False])
        pool = ThreadPool()
        pool.new_job(job_good)  # Initial.
        pool.new_job(job_bad)   # Cannot override as prev is running.
        pool.new_job(job_good)  # Overrides the previous one.
        time.sleep(0.3)
        self.assertTrue(test_container.result)
        self.assertTrue(test_container.cancelled)

    def test_no_override_job(self):
        """Test adding the same job while running another instance of it."""
        test_container = TestContainer(False, False)
        job_good = ThreadJob(name="test_job",
                             function=run_me,
                             callback=test_container.on_job_done,
                             args=[True])
        job_bad = ThreadJob(name="test_job",
                            function=run_me,
                            callback=test_container.on_job_done,
                            args=[False])
        pool = ThreadPool()
        pool.new_job(job_good)  # Initial.
        time.sleep(0.05)
        self.assertFalse(test_container.result)
        pool.new_job(job_bad)   # Cannot override as prev is running.
        time.sleep(0.1)
        self.assertTrue(test_container.result)
        self.assertFalse(test_container.cancelled)
