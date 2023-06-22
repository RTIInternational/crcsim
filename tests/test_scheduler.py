import pytest

from crcsim.scheduler import Scheduler


def test_init_time_0():
    """
    After initializing the scheduler, the time should be 0.
    """

    s = Scheduler()
    assert s.time == 0


def test_init_empty():
    """
    After initializing the scheduler, its queue should be empty.
    """

    s = Scheduler()
    assert s.is_empty()


def test_add_event_nonempty():
    """
    After adding an event, the queue should be nonempty.
    """

    s = Scheduler()
    s.add_event(message="test", delay=1)
    assert not s.is_empty()


def test_consume_when_empty():
    """
    Consuming an event when the queue is empty should raise an error.
    """

    s = Scheduler()
    with pytest.raises(IndexError):
        s.consume_next_event()


def test_added_event_is_consumed():
    """
    A consumed event should be identical to the one that was added.
    """

    s = Scheduler()
    added_event = s.add_event(message="test", delay=1)
    consumed_event = s.consume_next_event()
    assert added_event is consumed_event


def test_consume_event_time():
    """
    After consuming an event, the time should match the event's time.
    """

    s = Scheduler()
    s.add_event(message="test", delay=1)
    consumed_event = s.consume_next_event()
    assert s.time == consumed_event.time


@pytest.mark.parametrize("count", [1, 2])
def test_add_consume_empty(count):
    """
    Adding events and then consuming the same number of events should leave the
    queue empty.
    """

    s = Scheduler()
    for _ in range(count):
        s.add_event(message="test", delay=1)
    for _ in range(count):
        s.consume_next_event()
    assert s.is_empty()


def test_event_delay():
    """
    An event's time should equal the sum of the specified delay and the
    scheduler's time when the event was added.
    """

    s = Scheduler()
    s.add_event(message="test", delay=1)
    s.consume_next_event()
    added_event = s.add_event(message="test", delay=2)
    assert added_event.time == 3


def test_consume_correct_order():
    """
    If multiple events are added with different delays, the events should be
    consumed in the order of their delays, regardless of the order they were
    added.
    """

    s = Scheduler()
    event4 = s.add_event(message="test", delay=4)
    event2 = s.add_event(message="test", delay=2)
    event1 = s.add_event(message="test", delay=1)
    event3 = s.add_event(message="test", delay=3)

    for expected in [event1, event2, event3, event4]:
        observed = s.consume_next_event()
        assert observed is expected


def test_consume_ties_correct_order():
    """
    If two events have the same time, then the one added first should be
    consumed first.
    """

    s = Scheduler()
    event4 = s.add_event(message="test", delay=4)
    event2a = s.add_event(message="test", delay=2)
    event2b = s.add_event(message="test", delay=2)
    event3 = s.add_event(message="test", delay=3)

    for expected in [event2a, event2b, event3, event4]:
        observed = s.consume_next_event()
        assert observed is expected
