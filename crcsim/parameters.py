import bisect
import json
from typing import List


class StepFunction:
    def __init__(self, x: List[float], y: List[float]):
        """
        Create a step function that maps each element of x to the corresponding
        element of y.

        x and y must have the same length, and the x values must be sorted in
        increasing order.
        """

        if len(x) != len(y):
            raise ValueError(f"Lengths of x and y don't match: {len(x)} != {len(y)}")
        if sorted(x) != x:
            raise ValueError("x isn't sorted in increasing order")

        self.x = x
        self.y = y

    def __call__(self, value: float) -> float:
        """
        Evaluate the step function at the given value.

        If the given value isn't one of the function's defined x values, the
        step function interpolates by finding the next lowest value that is one
        of the defined x values, returning its corresponding y value.

        If the given value is smaller than the smallest of function's defined x
        values, then an exception is raised.
        """

        i = bisect.bisect_right(self.x, value) - 1
        if i < 0:
            raise ValueError(f"{value} is smaller than the smallest defined x value")
        return self.y[i]


def load_params(file):
    """
    Load the parameters from a JSON file.
    """

    with open(file) as f:
        params = json.load(f)

    params["value_life_year"] = StepFunction(
        x=params["value_life_year_ages"],
        y=params["value_life_year_dollars"],
    )

    params["lesion_incidence"] = StepFunction(
        x=params["lesion_incidence_ages"],
        y=params["lesion_incidence_rates"],
    )

    for sex in ("male", "female"):
        for race in ("black", "white"):
            params[f"death_rate_{race}_{sex}"] = StepFunction(
                x=params[f"death_rate_{race}_{sex}_ages"],
                y=params[f"death_rate_{race}_{sex}_rates"],
            )

    if params["use_variable_routine_test"]:
        params["variable_routine_test"] = StepFunction(
            x=params["routine_testing_year"], y=params["routine_test_by_year"]
        )
        for test_name, test_params in params["tests"].items():
            # Indexing 0 and -1 here safely returns the min and max testing years,
            # because initializing the StepFunction raises an error if the testing
            # years are not sorted in increasing order.
            if test_params["routine_start"] != params["routine_testing_year"][0]:
                raise ValueError(
                    f"routine_start for {test_name} does not equal the first year"
                    " of routine testing specified in routine_testing_year."
                )
            if test_params["routine_end"] != params["routine_testing_year"][-1]:
                raise ValueError(
                    f"routine_end for {test_name} does not equal the last year"
                    " of routine testing specified in routine_testing_year."
                )

    return params
