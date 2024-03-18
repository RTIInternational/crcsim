import pytest
import random
from copy import deepcopy

from crcsim.agent import Person
from crcsim.parameters import load_params
from crcsim.scheduler import Scheduler


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

    ...


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

    ...


def test_fit_then_colonoscopy_then_fit(params, test_switching_scenarios):
    """
    Asserts that the fit_then_colonoscopy_then_fit test switching scenario results in
    five FIT tests, one colonoscopy, then ten FIT tests for a person with 100% compliance.
    In this scenario, the person should get a FIT test every year from age 50 to 54, then a
    colonoscopy at age 55, then a FIT test every year from age 56 to 75.
    """
    params_fit_then_colonoscopy = deepcopy(params)
    params_fit_then_colonoscopy["routine_test_by_year"] = test_switching_scenarios[
        "fit_then_colonoscopy_then_fit"
    ]

    ...
