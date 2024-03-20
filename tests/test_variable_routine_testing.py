import json
import logging
import pytest
import random
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

from crcsim.agent import (
    Person,
    PersonDiseaseMessage,
    PersonTestingMessage,
    PersonTreatmentMessage,
)
from crcsim.parameters import load_params, StepFunction
from crcsim.scheduler import Scheduler
from crcsim.output import Output


@pytest.fixture(scope="module")
def params():
    """
    Default parameters. Some tests use these as-is; others override some values
    to test specific scenarios. These are also the current values in parameters.json,
    but we specify them here so that any future changes to parameters.json don't
    affect these tests.
    """
    p = load_params("parameters.json")

    # All test scenarios use FIT and Colonoscopy with testing from age 50 to 75.
    p["routine_testing_year"] = list(range(50, 76))
    p["tests"]["FIT"]["routine_start"] = 50
    p["tests"]["FIT"]["routine_end"] = 75
    p["tests"]["Colonoscopy"]["routine_start"] = 50
    p["tests"]["Colonoscopy"]["routine_end"] = 75

    # All test scenarios use 100% compliance.
    p["initial_compliance_rate"] = 1.0
    p["tests"]["FIT"]["compliance_rate_given_prev_compliant"] = [1.0] * 26
    p["tests"]["Colonoscopy"]["compliance_rate_given_prev_compliant"] = [1.0] * 26

    # We don't want any false positives for these tests, because we rely on each
    # person completing a normal course of routine testing without any diagnostic
    # or surveillance testing. In the TestPerson class, we ensure that the person
    # never has CRC; here we ensure that no routine test returns a false positive
    # and causes a diagnostic test.
    p["tests"]["FIT"]["specificity"] = 1
    p["tests"]["Colonoscopy"]["specificity"] = 1

    # Default test switching scenario. We directly specify variable_routine_test,
    # which is normally computed from the parameters routine_testing_year and
    # routine_test_by_year in load_params. We have to specify if directly here
    # because we've already called load_params, so if we just change
    # routine_testing_year and routine_test_by_year, variable_routine_test won't
    # be recomputed, and it is the parameter which ultimately determines test
    # switching behavior.
    p["variable_routine_test"] = StepFunction(
        p["routine_testing_year"], ["Colonoscopy"] * 11 + ["FIT"] * 15
    )

    return p


@pytest.fixture(scope="module")
def test_switching_scenarios(params):
    """
    These test switching scenarios are used to override the default params for some
    tests.
    """
    routine_testing_year = params["routine_testing_year"]
    return {
        "one_colonoscopy_then_fit_v1": StepFunction(
            routine_testing_year, ["Colonoscopy"] + ["FIT"] * 25
        ),
        "one_colonoscopy_then_fit_v2": StepFunction(
            routine_testing_year, ["Colonoscopy"] * 10 + ["FIT"] * 16
        ),
        "ten_fit_then_colonoscopy": StepFunction(
            routine_testing_year, ["FIT"] * 10 + ["Colonoscopy"] * 16
        ),
        "fit_then_colonoscopy_then_fit": StepFunction(
            routine_testing_year, ["FIT"] * 5 + ["Colonoscopy"] * 1 + ["FIT"] * 20
        ),
    }


class TestPerson(Person):
    """
    Overrides or adds to the Person class in two ways that are crucial to these tests:

    1. Overrides the start method to ensure that the person never has CRC and lives to
       100, so they always complete the full course of routine testing.
    2. Adds a simulate method to simulate one TestPerson at a time without running
       the main simulation on a cohort of people.

    Also, for convenience, assigns attributes directly in __init__ so we don't have
    to pass them at instantiation.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scheduler = Scheduler()
        self.rng = random.Random(1)
        # Output class requires a file name, but we don't write to disk in these tests,
        # so we give it a dummy file name.
        self.out = Output(file_name="unused")
        # Sex and race_ethnicity are irrelevant to this test but we need to choose an
        # arbitrary value for the simulation to run.
        self.sex = ("female",)
        self.race_ethnicity = ("black_non_hispanic",)

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
        """
        Simplified version of the simulation loop used in crcsim.__main__.
        Enables us to simulate one TestPerson at a time without running the
        main simulation on a cohort of people.
        """
        while not self.scheduler.is_empty():
            event = self.scheduler.consume_next_event()
            if not event.enabled:
                continue
            if event.message == "end_simulation":
                logging.debug("[scheduler] ending simulation \n")
                break
            handler = event.handler
            handler(event.message)


def test_testing_year_misalignment(params):
    """
    Asserts that misaligned testing years in routine_testing_year and a single test's
    routine start or end raises an error.
    """
    with open("parameters.json", "r") as f:
        params = json.load(f)
        params["tests"]["Colonoscopy"]["routine_end"] = 85
        with TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / "parameters.json"
            with open(tmp_path, "w") as f:
                json.dump(params, f)
                with pytest.raises(ValueError):
                    load_params(tmp_path)


def test_one_colonoscopy_equivalence(params, test_switching_scenarios):
    """
    Asserts that the one_colonoscopy_then_fit_v1 and one_colonoscopy_then_fit_v2
    test switching scenarios both result in one colonoscopy and 16 FIT tests for
    a person with 100% compliance. This tests whether the logic in
    crcsim.agent.Person.do_tests, which requires the person to be due for *every*
    routine test, works in the test switching context. P1 switches to FIT at age
    51, but they shouldn't get a FIT test until age 60 because they had a
    colonoscopy at age 50. P2 switches to FIT at age 60, and they should get a FIT
    test that year.
    """
    params_one_colonoscopy_v1 = deepcopy(params)
    params_one_colonoscopy_v1["variable_routine_test"] = test_switching_scenarios[
        "one_colonoscopy_then_fit_v1"
    ]

    params_one_colonoscopy_v2 = deepcopy(params)
    params_one_colonoscopy_v2["variable_routine_test"] = test_switching_scenarios[
        "one_colonoscopy_then_fit_v2"
    ]

    p1 = TestPerson(
        id=1,
        sex=None,
        race_ethnicity=None,
        params=params_one_colonoscopy_v1,
        scheduler=None,
        rng=None,
        out=None,
    )
    p1.start()
    p1.simulate()

    p2 = TestPerson(
        id=2,
        sex=None,
        race_ethnicity=None,
        params=params_one_colonoscopy_v1,
        scheduler=None,
        rng=None,
        out=None,
    )
    p2.start()
    p2.simulate()

    # Assert that both people have one colonoscopy and 16 FIT tests
    for person in [p1, p2]:
        tests = [
            row for row in person.out.rows if row["record_type"] == "test_performed"
        ]
        colonoscopies = [test for test in tests if test["test_name"] == "Colonoscopy"]
        fits = [test for test in tests if test["test_name"] == "FIT"]
        assert len(colonoscopies) == 1
        assert len(fits) == 16


def test_ten_fit_then_colonoscopy(params, test_switching_scenarios):
    """
    Asserts that the ten_fit_then_colonoscopy test switching scenario results in
    ten FIT tests and two colonoscopies for a person with 100% compliance. In this
    scenario, the person should get a FIT test every year from age 50 to 59, then a
    colonoscopy at age 60 and 70. They will be due for a third colonoscopy at age 80,
    but routine testing ends at age 75.
    """
    params_ten_fit = deepcopy(params)
    params_ten_fit["variable_routine_test"] = test_switching_scenarios[
        "ten_fit_then_colonoscopy"
    ]

    p = TestPerson(
        id=None,
        sex=None,
        race_ethnicity=None,
        params=params_ten_fit,
        scheduler=None,
        rng=None,
        out=None,
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
    five FIT tests, one colonoscopy, then 11 FIT tests for a person with 100% compliance.
    In this scenario, the person should get a FIT test every year from age 50 to 54, then a
    colonoscopy at age 55, then a FIT test every year from age 65 to 75 (in total, one
    colonoscopy and 16 FIT tests).
    """
    params_fit_then_colonoscopy = deepcopy(params)
    params_fit_then_colonoscopy["variable_routine_test"] = test_switching_scenarios[
        "fit_then_colonoscopy_then_fit"
    ]

    p = TestPerson(
        id=None,
        sex=None,
        race_ethnicity=None,
        params=params_fit_then_colonoscopy,
        scheduler=None,
        rng=None,
        out=None,
    )
    p.start()
    p.simulate()

    tests = [row for row in p.out.rows if row["record_type"] == "test_performed"]
    colonoscopies = [test for test in tests if test["test_name"] == "Colonoscopy"]
    fits = [test for test in tests if test["test_name"] == "FIT"]
    assert len(colonoscopies) == 1
    assert len(fits) == 16
