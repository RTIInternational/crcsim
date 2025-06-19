import json
import logging
import random
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from crcsim.agent import (
    Person,
    PersonDiseaseMessage,
    PersonTestingMessage,
    PersonTreatmentMessage,
)
from crcsim.output import Output
from crcsim.parameters import StepFunction, load_params
from crcsim.scheduler import Scheduler


def test_testing_year_misalignment():
    """
    Asserts that misaligned testing years in routine_testing_year and a single test's
    routine start or end raises an error.
    """
    # We load parameters.json here instead of using the params fixture because
    # load_params has already been run in the fixture, which creates additional
    # parameters of StepFunction type, and those are not JSON serializable.
    with open("parameters.json", "r") as f:
        params = json.load(f)
        params["tests"]["Colonoscopy"]["routine_end"] = 85
        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir) / "parameters.json"
            with open(tmp_path, "w") as f:
                json.dump(params, f)
            with pytest.raises(
                ValueError,
                match="routine_end for Colonoscopy does not equal the last year",
            ):
                load_params(tmp_path)


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
    # or surveillance testing. In the PersonForTests class, we ensure that the person
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


class PersonForTests(Person):
    """
    Overrides or adds to the Person class in two ways that are crucial to these tests:

    1. Overrides the start method to ensure that the person never has CRC and lives to
       100, so they always complete the full course of routine testing.
    2. Adds a simulate method to simulate one PersonForTests at a time without running
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
        # never having a lesion.

    def simulate(self):
        """
        Simplified version of the simulation loop used in crcsim.__main__.
        Enables us to simulate one PersonForTests at a time without running the
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


@pytest.mark.parametrize(
    "case",
    [
        # Switches to FIT at age 51, but they shouldn't get a FIT test until age 60
        # because they had a colonoscopy at age 50.
        {
            "routine_test_by_year": ["Colonoscopy"] + ["FIT"] * 25,
            "expected_colonoscopies": 1,
            "expected_fits": 16,
        },
        # Switches to FIT at age 60, and they should get a FIT test that year,
        # because the last colonoscopy was at age 50.
        {
            "routine_test_by_year": ["Colonoscopy"] * 10 + ["FIT"] * 16,
            "expected_colonoscopies": 1,
            "expected_fits": 16,
        },
        # Gets a FIT test every year from age 50 to 59, then a colonoscopy at age 60
        # and 70. They will be due for a third colonoscopy at age 80, but routine
        # testing ends at age 75.
        {
            "routine_test_by_year": ["FIT"] * 10 + ["Colonoscopy"] * 16,
            "expected_colonoscopies": 2,
            "expected_fits": 10,
        },
        # Gets a FIT test every year from age 50 to 54, then a colonoscopy at age 55,
        # then a FIT test every year from age 65 to 75 (in total, one colonoscopy and
        # 16 FIT tests)
        {
            "routine_test_by_year": ["FIT"] * 5 + ["Colonoscopy"] * 1 + ["FIT"] * 20,
            "expected_colonoscopies": 1,
            "expected_fits": 16,
        },
    ],
)
def test_switching_scenario(params, case):
    """
    Asserts that the routine_test_by_year sequences parametrized in the test cases
    result in the expected number of colonoscopies and FIT tests.
    """
    params_ = deepcopy(params)
    params_["variable_routine_test"] = StepFunction(
        params["routine_testing_year"], case["routine_test_by_year"]
    )

    p = PersonForTests(
        id=None,
        sex=None,
        race_ethnicity=None,
        expected_lifespan=None,
        params=params_,
        scheduler=None,
        rng=None,
        out=None,
    )
    p.start()
    p.simulate()

    tests = [row for row in p.out.rows if row["record_type"] == "test_performed"]
    colonoscopies = [test for test in tests if test["test_name"] == "Colonoscopy"]
    fits = [test for test in tests if test["test_name"] == "FIT"]
    assert len(colonoscopies) == case["expected_colonoscopies"]
    assert len(fits) == case["expected_fits"]
