import pytest

from crcsim.agent import Person
from crcsim.parameters import load_params


class MockScheduler:
    def __init__(self, time):
        self.time = time


class MockRandom:
    def __init__(self, value):
        self.value = value

    def random(self):
        return self.value


@pytest.fixture(scope="module")
def params():
    return load_params("parameters.json")


# The expected values for these test cases were obtained using the AnyLogic
# model. (It doesn't provide these values in its output, and it doesn't provide
# a way to specify these inputs. Temporary, manual editing of the model was
# necessary to produce these.)
cases = [
    {"rand": 0.25, "risk": 1, "prev_time": 0, "expected": 59.90341968549087},
    {"rand": 0.75, "risk": 1, "prev_time": 0, "expected": None},
    {"rand": 0.25, "risk": 1.5, "prev_time": 0, "expected": 55.9078353458828},
    {"rand": 0.75, "risk": 1.5, "prev_time": 0, "expected": 92.65420370423578},
    {"rand": 0.25, "risk": 1, "prev_time": 42.765, "expected": 19.142669350065958},
    {"rand": 0.75, "risk": 1, "prev_time": 42.765, "expected": None},
    {"rand": 0.25, "risk": 1.5, "prev_time": 42.765, "expected": 15.385543679216134},
    {"rand": 0.75, "risk": 1.5, "prev_time": 42.765, "expected": 54.7823855224176},
]


@pytest.mark.parametrize("case", cases)
def test_delay(case, params):
    p = Person(
        id=None,
        race_ethnicity=None,
        sex=None,
        params=params,
        scheduler=MockScheduler(time=case["prev_time"]),
        rng=MockRandom(value=case["rand"]),
        out=None,
    )
    p.lesion_risk_index = case["risk"]
    p.previous_lesion_onset_time = case["prev_time"]
    p.expected_lifespan = params["max_age"]

    observed = p.compute_lesion_delay()

    if case["expected"] is None:
        assert observed is None
    else:
        assert observed == pytest.approx(case["expected"], abs=1e-12)
