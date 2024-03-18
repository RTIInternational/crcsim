import logging
import pytest
import random
from copy import deepcopy

from crcsim.agent import (
    Person,
    PersonDiseaseMessage,
    PersonTestingMessage,
    PersonTreatmentMessage,
)
from crcsim.parameters import load_params
from crcsim.scheduler import Scheduler
from crcsim.output import Output


class MockScheduler:
    def __init__(self, time):
        self.time = time


@pytest.fixture(scope="module")
def params():
    p = load_params("parameters.json")

    # All test scenarios use FIT and Colonoscopy with testing from age 50 to 75
    p["routine_testing_year"] = list(range(50, 76))
    p["tests"]["FIT"]["routine_start"] = 50
    p["tests"]["FIT"]["routine_end"] = 75
    p["tests"]["Colonoscopy"]["routine_start"] = 50
    p["tests"]["Colonoscopy"]["routine_end"] = 75

    # Default test switching scenario
    p["routine_test_by_year"] = ["Colonoscopy"] * 11 + ["FIT"] * 15

    return p


def test_parameter_alignment(params):
    params_missing_year = deepcopy(params)
    params_missing_year["routine_testing_year"].pop()
    with pytest.raises(ValueError):
        p = Person(
            id=None,
            race_ethnicity=None,
            sex=None,
            params=params_missing_year,
            scheduler=Scheduler(),
            rng=random.Random(1),
            out=None,
        )
        p.start()

    params_missing_test = deepcopy(params)
    params_missing_test["routine_test_by_year"].pop()
    with pytest.raises(ValueError):
        p = Person(
            id=None,
            race_ethnicity=None,
            sex=None,
            params=params_missing_test,
            scheduler=Scheduler(),
            rng=random.Random(1),
            out=None,
        )
        p.start()

    params_unsorted_year = deepcopy(params)
    params_unsorted_year["routine_testing_year"].reverse()
    with pytest.raises(ValueError):
        p = Person(
            id=None,
            race_ethnicity=None,
            sex=None,
            params=params_unsorted_year,
            scheduler=Scheduler(),
            rng=random.Random(1),
            out=None,
        )
        p.start()

    params_wrong_test_end = deepcopy(params)
    params_wrong_test_end["tests"]["Colonoscopy"]["routine_end"] = 85
    with pytest.raises(ValueError):
        p = Person(
            id=None,
            race_ethnicity=None,
            sex=None,
            params=params_wrong_test_end,
            scheduler=Scheduler(),
            rng=random.Random(1),
            out=None,
        )
        p.start()


@pytest.fixture(scope="module")
def test_switching_scenarios():
    return {
        "one_colonoscopy_then_fit_v1": ["Colonoscopy"] + ["FIT"] * 25,
        "one_colonoscopy_then_fit_v2": ["Colonoscopy"] * 10 + ["FIT"] * 16,
        "ten_fit_then_colonoscopy": ["FIT"] * 10 + ["Colonoscopy"] * 16,
        "fit_then_colonoscopy_then_fit": ["FIT"] * 5
        + ["Colonoscopy"] * 1
        + ["FIT"] * 20,
    }


class TestPerson(Person):
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
        # never having a lesion.

    def simulate(self):
        # Simplified version of the simulation loop used in crcsim.__main__
        while not self.scheduler.is_empty():
            event = self.scheduler.consume_next_event()
            if not event.enabled:
                continue
            if event.message == "end_simulation":
                logging.debug("[scheduler] ending simulation \n")
                break
            handler = event.handler
            handler(event.message)


def test_one_colonoscopy_equivalence(params, test_switching_scenarios):
    """
    Asserts that the one_colonoscopy_then_fit_v1 and one_colonoscopy_then_fit_v2
    test switching scenarios both result in one colonoscopy and 15 FIT tests for
    a person with 100% compliance. This tests whether the logic in
    crcsim.agent.Person.do_tests, which requires the person to be due for *every*
    routine test, works in the test switching context.
    """
    params_one_colonoscopy_v1 = deepcopy(params)
    params_one_colonoscopy_v1["routine_test_by_year"] = test_switching_scenarios[
        "one_colonoscopy_then_fit_v1"
    ]

    params_one_colonoscopy_v2 = deepcopy(params)
    params_one_colonoscopy_v2["routine_test_by_year"] = test_switching_scenarios[
        "one_colonoscopy_then_fit_v2"
    ]

    p1 = TestPerson(
        id=1,
        # Sex and race_ethnicity are irrelevant to this test but we need to choose an
        # arbitrary value for the simulation to run.
        sex="female",
        race_ethnicity="black_non_hispanic",
        params=params_one_colonoscopy_v1,
        scheduler=Scheduler(),
        rng=random.Random(1),
        out=Output(),
    )
    p1.start()
    p1.simulate()

    p2 = TestPerson(
        id=2,
        sex="female",
        race_ethnicity="black_non_hispanic",
        params=params_one_colonoscopy_v1,
        scheduler=Scheduler(),
        rng=random.Random(1),
        out=Output(),
    )
    p2.start()
    p2.simulate()

    # Assert that both people have one colonoscopy and 15 FIT tests
    for person in [p1, p2]:
        tests = [
            row for row in person.out.rows if row["record_type"] == "test_performed"
        ]
        colonoscopies = [test for test in tests if test["test_name"] == "Colonoscopy"]
        fits = [test for test in tests if test["test_name"] == "FIT"]
        assert len(colonoscopies) == 1
        assert len(fits) == 15


def test_ten_fit_then_colonoscopy(params, test_switching_scenarios):
    """
    Asserts that the ten_fit_then_colonoscopy test switching scenario results in
    ten FIT tests and two colonoscopies for a person with 100% compliance. In this
    scenario, the person should get a FIT test every year from age 50 to 59, then a
    colonoscopy at age 60 and 70. They will be due for a third colonoscopy at age 80,
    but routine testing ends at age 75.
    """
    params_ten_fit = deepcopy(params)
    params_ten_fit["routine_test_by_year"] = test_switching_scenarios[
        "ten_fit_then_colonoscopy"
    ]

    p = TestPerson(
        id=None,
        sex="female",
        race_ethnicity="black_non_hispanic",
        params=params_ten_fit,
        scheduler=Scheduler(),
        rng=random.Random(1),
        out=Output(),
    )
    p.start()
    p.simulate()

    tests = [row for row in p.out.rows if row["record_type"] == "test_performed"]
    colonoscopies = [test for test in tests if test["test_name"] == "Colonoscopy"]
    fits = [test for test in tests if test["test_name"] == "FIT"]
    assert len(colonoscopies) == 2
    assert len(fits) == 10


def test_fit_then_colonoscopy_then_fit(params, test_switching_scenarios):
    """
    Asserts that the fit_then_colonoscopy_then_fit test switching scenario results in
    five FIT tests, one colonoscopy, then ten FIT tests for a person with 100% compliance.
    In this scenario, the person should get a FIT test every year from age 50 to 54, then a
    colonoscopy at age 55, then a FIT test every year from age 66 to 75 (in total, one
    colonoscopy and 15 FIT tests).
    """
    params_fit_then_colonoscopy = deepcopy(params)
    params_fit_then_colonoscopy["routine_test_by_year"] = test_switching_scenarios[
        "fit_then_colonoscopy_then_fit"
    ]

    p = TestPerson(
        id=None,
        sex="female",
        race_ethnicity="black_non_hispanic",
        params=params_fit_then_colonoscopy,
        scheduler=Scheduler(),
        rng=random.Random(1),
        out=Output(),
    )
    p.start()
    p.simulate()

    tests = [row for row in p.out.rows if row["record_type"] == "test_performed"]
    colonoscopies = [test for test in tests if test["test_name"] == "Colonoscopy"]
    fits = [test for test in tests if test["test_name"] == "FIT"]
    assert len(colonoscopies) == 1
    assert len(fits) == 15
