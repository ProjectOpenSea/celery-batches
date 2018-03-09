# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from time import sleep

from celery import signals

from .tasks import add, cumadd, Results


class SignalCounter(object):
    def __init__(self, expected_calls):
        self.calls = 0
        self.expected_calls = expected_calls

    def __call__(self, *args, **kwargs):
        self.calls += 1

    def assert_calls(self):
        assert self.calls == self.expected_calls


def test_flush_interval(celery_worker):
    """The batch runs after the flush interval has elapsed."""
    add.delay(1)

    # The flush interval is 1 second, this is longer.
    sleep(2)

    assert Results().get() == 1


def test_flush_calls(celery_worker):
    """The batch runs after two calls."""
    add.delay(1)
    add.delay(3)

    # Yield control to the other thread. (This needs to be shorter than the
    # flush interval.)
    sleep(1)

    assert Results().get() == 4


def test_result(celery_worker):
    result_1 = cumadd.delay(1)
    result_2 = cumadd.delay(2)

    # Yield control to the other thread. (This needs to be shorter than the
    # flush interval.)
    sleep(1)

    assert result_1.get(timeout=3) == 1
    assert result_2.get(timeout=3) == 3


def test_signals(celery_app, celery_worker):
    """The batch runs after two calls."""
    # Configure a SignalCounter for each task signal.
    checks = (
        # Each task request gets published separately.
        (signals.before_task_publish, 2),
        (signals.after_task_publish, 2),
        # The task only runs a single time.
        (signals.task_prerun, 1),
        (signals.task_postrun, 1),
        # Other task signals are not implemented.
        (signals.task_retry, 0),
        (signals.task_success, 0),
        (signals.task_failure, 0),
        (signals.task_revoked, 0),
        (signals.task_unknown, 0),
        (signals.task_rejected, 0),
    )
    signal_counters = []
    for sig, expected_count in checks:
        counter = SignalCounter(expected_count)
        sig.connect(counter)
        signal_counters.append(counter)

    add.delay(1)
    add.delay(3)

    # Yield control to the other thread. (This needs to be shorter than the
    # flush interval.)
    sleep(1)

    # Should still have the correct result.
    assert Results().get() == 4

    for counter in signal_counters:
        counter.assert_calls()


# TODO
# * Test acking
