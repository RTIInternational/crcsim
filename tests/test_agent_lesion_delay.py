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


# When we first ported the crcsim model from AnyLogic to Python, this test module
# compared the lesion delay calculations against values from the AnyLogic model.
# We recalibrated the model since then (see exp-2022-calibration branch), which
# changed the lesion delay parameters. So the Py-AnyLogic comparison no longer
# holds. Instead, the expected values are now drawn from the recalibrated model.
# This is somewhat circular, since we're now comparing the recalibrated Python model
# against itself. However, it could still be useful to ensure that future changes
# don't introduce unexpected changes in lesion delay calculation. If the model is
# recalibrated again, the expected values in this test must be updated.
cases = [
    {"rand": 0.25, "risk": 1, "prev_time": 0, "expected": 52.90728289807124},
    {"rand": 0.75, "risk": 1, "prev_time": 0, "expected": None},
    {"rand": 0.25, "risk": 1.5, "prev_time": 0, "expected": 48.83940241505936},
    {"rand": 0.75, "risk": 1.5, "prev_time": 0, "expected": 84.92693097696306},
    {"rand": 0.25, "risk": 1, "prev_time": 42.765, "expected": 13.314891572288182},
    {"rand": 0.75, "risk": 1, "prev_time": 42.765, "expected": None},
    {"rand": 0.25, "risk": 1.5, "prev_time": 42.765, "expected": 9.565521932047488},
    {"rand": 0.75, "risk": 1.5, "prev_time": 42.765, "expected": 49.568749158781245},
]


@pytest.mark.parametrize("case", cases)
def test_delay(case, params):
    p = Person(
        id=None,
        race_ethnicity=None,
        sex=None,
        expected_lifespan=params["max_age"],
        params=params,
        scheduler=MockScheduler(time=case["prev_time"]),
        rng=MockRandom(value=case["rand"]),
        out=None,
    )
    p.lesion_risk_index = case["risk"]
    p.previous_lesion_onset_time = case["prev_time"]

    observed = p.compute_lesion_delay()

    if case["expected"] is None:
        assert observed is None
    else:
        assert observed == pytest.approx(case["expected"], abs=1e-12)
