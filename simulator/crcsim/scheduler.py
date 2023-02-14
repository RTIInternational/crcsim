import logging


class Event:
    def __init__(self, message, time, handler=None):
        self.message = message
        self.time = time
        self.handler = handler
        self.enabled = True


class Scheduler:
    def __init__(self):
        self.queue = []
        self.time = 0
        self.debug = logging.getLogger().isEnabledFor(logging.DEBUG)

    def add_event(self, message, handler=None, delay=0):
        """
        Insert an event into the queue.

        A time is assigned to the event based on the current time and the
        event's delay. The queue is maintained in increasing order of event
        time.

        If the event's time matches an event already in the queue, then the
        event is inserted after the existing event.
        """

        new_event = Event(message=message, handler=handler, time=self.time + delay)
        for index, event in enumerate(self.queue):
            if new_event.time < event.time:
                self.queue.insert(index, new_event)
                break
        else:
            self.queue.append(new_event)

        if self.debug:
            # For performance reasons, don't call logging.debug() unless
            # debugging is enabled. Constructing the string argument takes a
            # surprisingly large portion of the overall script runtime.
            logging.debug(
                f"[scheduler] add event '{str(event.message)}' to queue at time {self.time} for firing at time {new_event.time}"
            )

        return new_event

    def consume_next_event(self):
        """
        Remove the first event from the queue, return it, and set the current time
        to that event's time.
        """

        if self.is_empty():
            raise IndexError("queue is empty")
        else:
            event = self.queue.pop(0)
            self.time = event.time
            return event

    def is_empty(self):
        return len(self.queue) == 0

    def remove_events(self, messages: list = []):
        self.queue = [event for event in self.queue if event.message not in messages]
        logging.debug(
            f"[scheduler] clearing events with messages {[str(m) for m in messages]} at time {self.time}"
        )
