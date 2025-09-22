import random

from crcsim.agent import Person
from crcsim.enums import (
    PersonDiseaseMessage,
    PersonTestingMessage,
    PersonTreatmentMessage,
)
from crcsim.output import Output
from crcsim.scheduler import Scheduler


class BasePersonForTests(Person):
    """
    Base class for testing Person behavior. Provides common functionality for tests
    that need to simulate individual people without running the full cohort simulation.

    Overrides or adds to the Person class in two ways that are crucial to tests:

    1. Overrides the start method to ensure that the person never has CRC and lives to
       100, so they always complete the full course of routine testing.
    2. Adds a simulate method to simulate one Person at a time without running
       the main simulation on a cohort of people.

    Also, for convenience, assigns unused Person attributes directly in __init__ so we
    don't have to pass them at instantiation.
    """

    def __init__(
        self,
        id=None,
        sex=None,
        race_ethnicity=None,
        expected_lifespan=None,
        params=None,
        scheduler=None,
        rng=None,
        out=None,
    ):
        super().__init__(
            id, sex, race_ethnicity, expected_lifespan, params, scheduler, rng, out
        )
        self.scheduler = Scheduler()
        self.rng = random.Random(1)
        # Output class requires a file name, but we don't write to disk in these tests,
        # so we give it a dummy file name.
        self.out = Output(file_name="unused")
        # Sex and race_ethnicity are irrelevant to most tests but we need to choose an
        # arbitrary value for the simulation to run.
        self.sex = "female"
        self.race_ethnicity = "black_non_hispanic"

    def start(self):
        self.choose_tests()

        self.handle_disease_message(PersonDiseaseMessage.INIT)
        self.handle_testing_message(PersonTestingMessage.INIT)
        self.handle_treatment_message(PersonTreatmentMessage.INIT)

        self.scheduler.add_event(
            message="Conduct yearly actions",
            delay=1,
            handler=self.handle_yearly_actions,
        )

        # Fix lifespan at 100 for testing instead of calling self.start_life_timer()
        self.expected_lifespan = 100
        self.scheduler.add_event(
            message=PersonDiseaseMessage.OTHER_DEATH,
            handler=self.handle_disease_message,
            delay=self.expected_lifespan,
        )
        self.out.add_expected_lifespan(
            person_id=self.id,
            time=self.expected_lifespan,
        )

        # Person.start has lesion delay functions here to add an event to the
        # scheduler for the person's first lesion. We don't want any lesions for the
        # test person, so that chunk is omitted here. Because the next lesion delay
        # is computed when a lesion onset is handled, this results in the person
        # never having a lesion. That gives us finer-grained control over what happens
        # during the test person's lifespan, making it easier to test specific scenarios.

    def simulate(self):
        """
        Simplified version of the simulation loop used in crcsim.__main__.
        Enables us to simulate one Person at a time without running the
        main simulation on a cohort of people.
        """
        while not self.scheduler.is_empty():
            event = self.scheduler.consume_next_event()
            if not event.enabled:
                continue
            if event.message == "end_simulation":
                break
            handler = event.handler
            handler(event.message)
