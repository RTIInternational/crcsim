import json
import random
from enum import Enum, unique
from pathlib import Path
from typing import Callable, Dict, List, Optional

import fire

SEED: int = 49865106
NUM_ITERATIONS: int = 100


class Scenario:
    def __init__(self, name: str, params: Dict):
        self.name = name
        self.params = params

    def transform(self, transformer: Callable) -> "Scenario":
        transformer(self.params)
        return self


@unique
class Test(Enum):
    FIT = "FIT"
    COLONOSCOPY = "Colonoscopy"


@unique
class IRR(Enum):
    irr = 1.19


@unique
class ConditionalComplianceParam(Enum):
    PREV_COMPLIANT = "compliance_rate_given_prev_compliant"
    NOT_PREV_COMPLIANT = "compliance_rate_given_not_prev_compliant"


def prepare_experiment_dir(
    scenarios: List[Scenario],
    num_iterations: int,
    rng: random.Random,
) -> None:
    """
    Create a directory hierarchy and the supporting files needed for running
    the experiment.

    A directory named `./scenarios` will be created. Inside this directory, one
    subdirectory per scenario will be created. Within each scenario subdirectory,
    a parameters input file named "params.json" will be created.

    In addition, a text file of seeds (seeds.txt) will be created in the ./scenarios
    directory. This file will contain a random seed for each iteration. For example,
    if num_iterations=100, seeds.txt will contain 100 seeds, one per row.

    For example, suppose `num_iterations=2`, and there are three scenarios named
    "base", "intervention1", and "intervention2". Then the resulting directory
    hierarchy would look like this:

        scenarios/
            base/
                params.json
            intervention1/
                params.json
            intervention2/
                params.json
            seeds.txt (will contain 2 lines, one seed per line)
    """

    scenarios_dir = Path("./scenarios")
    if scenarios_dir.exists():
        prompt = "Scenarios directory already exists. Do you want to continue? [y/n] "
        if input(prompt) != "y":
            print("Cancelling scenario directory preparation.")
            return

    for scenario in scenarios:
        scenario_dir = scenarios_dir / scenario.name
        scenario_dir.mkdir(exist_ok=True, parents=True)

        scenario_params_file = scenario_dir / "params.json"
        with open(scenario_params_file, mode="w") as f:
            json.dump(obj=scenario.params, fp=f, indent=2)

    seeds = [rng.randint(1, 2**31 - 1) for _ in range(num_iterations)]
    seeds_file = scenarios_dir / "seeds.txt"
    with open(seeds_file, mode="w") as f:
        for seed in seeds:
            f.write(str(seed))
            f.write("\n")


def get_default_params() -> Dict:
    with open("parameters.json") as f:
        params = json.load(f)
    return params


def transform_initial_compliance(rate: float) -> Callable:
    def transform(params):
        params["initial_compliance_rate"] = rate

    return transform


def transform_diagnostic_compliance(rate: float) -> Callable:
    def transform(params):
        params["diagnostic_compliance_rate"] = rate

    return transform


def transform_treatment_cost(stage: str, phase: str, cost: float) -> Callable:
    def transform(params):
        params[f"cost_treatment_stage{stage}_{phase}"] = cost

    return transform


def transform_routine_ages(test: Test, start_age: int, end_age: int) -> Callable:
    def transform(params):
        params["tests"][test.value]["routine_start"] = start_age
        params["tests"][test.value]["routine_end"] = end_age

    return transform


def transform_test_cost(test: Test, cost: int) -> Callable:
    def transform(params):
        params["tests"][test.value]["cost"] = cost

    return transform


def transform_routine_proportion(test: Test, proportion: float) -> Callable:
    def transform(params):
        params["tests"][test.value]["proportion"] = proportion

    return transform


def transform_fit_only() -> Callable:
    """Transform parameters to use FIT tests only."""

    def transform(params):
        # Set FIT as the only test
        params["routine_testing_year"] = list(range(45, 76))  # Ages 45-75
        params["variable_routine_test"] = ["FIT"] * 31  # FIT for all years

        # Disable other tests by setting their routine ages outside valid range
        for test_name in params["tests"]:
            if test_name != "FIT":
                params["tests"][test_name]["routine_start"] = -1
                params["tests"][test_name]["routine_end"] = -1
            else:
                params["tests"]["FIT"]["routine_start"] = 45
                params["tests"]["FIT"]["routine_end"] = 75

    return transform


def transform_colonoscopy_only() -> Callable:
    """Transform parameters to use Colonoscopy tests only."""

    def transform(params):
        # Set FIT as the only test
        params["routine_testing_year"] = list(range(45, 76))  # Ages 45-75
        params["variable_routine_test"] = ["Colonoscopy"] * 31  # FIT for all years

        # Disable other tests by setting their routine ages outside valid range
        for test_name in params["tests"]:
            if test_name != "Colonoscopy":
                params["tests"][test_name]["routine_start"] = -1
                params["tests"][test_name]["routine_end"] = -1
            else:
                params["tests"]["Colonoscopy"]["routine_start"] = 45
                params["tests"]["Colonoscopy"]["routine_end"] = 75

    return transform


def transform_conditional_compliance_rates(
    param: ConditionalComplianceParam, rates: List[float]
) -> Callable:
    """
    Replaces a conditional compliance parameter with a new set of rates.
    """

    def transform(params):
        for test in params["tests"]:
            params["tests"][test][param.value] = rates

    return transform


def transform_lesion_risk_alpha(IRR: float) -> Callable:
    def transform(params):
        params["lesion_risk_alpha"] = params["lesion_risk_alpha"] * IRR

    return transform


def create_scenarios() -> List:
    # For each health center, define the initial compliance rate in the baseline
    # scenario and the implementation scenario and vary diagnostic compliance.

    compliance_rates = {
        "NC": {
            "initial": (0.097, 0.300),
            "diagnostic": (0.444, 0.688),
        },
        # other items
    }

    costs = {
        "public": {
            "FIT": 22,
            "Colonoscopy": 912,
        },
        #'Patient-Public": {"FIT": 44, "Colonoscopy": 1437,}
    }

    scenarios = []

    for site, rates in compliance_rates.items():
        for cost_category, test_costs in costs.items():
            FIT_cost = test_costs["FIT"]
            Col_cost = test_costs["Colonoscopy"]
            baseline = (
                Scenario(
                    name=f"{site}_{cost_category}_baseline",
                    params=get_default_params(),
                )
                .transform(transform_initial_compliance(rates["initial"][0]))
                .transform(transform_diagnostic_compliance(rates["diagnostic"][0]))
                .transform(transform_test_cost(Test.FIT, FIT_cost))
                .transform(transform_test_cost(Test.COLONOSCOPY, Col_cost))
                .transform(transform_lesion_risk_alpha(IRR.irr.value))
            )
            scenarios.append(baseline)

            implementation = (
                Scenario(
                    name=f"{site}_{cost_category}_implementation",
                    params=get_default_params(),
                )
                .transform(transform_initial_compliance(rates["initial"][1]))
                .transform(transform_diagnostic_compliance(rates["diagnostic"][1]))
                .transform(transform_test_cost(Test.FIT, FIT_cost))
                .transform(transform_test_cost(Test.COLONOSCOPY, Col_cost))
                .transform(transform_lesion_risk_alpha(IRR.irr.value))
            )
            scenarios.append(implementation)

    # No screening baseline scenario
    no_screening = (
        Scenario(name="no_screening", params=get_default_params())
        .transform(transform_fit_only())
        .transform(transform_routine_proportion(Test.FIT, 1.0))
        .transform(transform_routine_ages(Test.FIT, -1, -1))
    )
    scenarios.append(no_screening)

    # Full FIT compliance baseline
    full_FIT_compliance = (
        Scenario(name="full_FIT_compliance", params=get_default_params())
        .transform(transform_fit_only())
        .transform(transform_routine_proportion(Test.FIT, 1.0))
        .transform(transform_routine_proportion(Test.COLONOSCOPY, 0.0))
        .transform(transform_initial_compliance(1.0))
        .transform(
            transform_conditional_compliance_rates(
                ConditionalComplianceParam.PREV_COMPLIANT, [float(1.0)] * 31
            )
        )
        .transform(
            transform_conditional_compliance_rates(
                ConditionalComplianceParam.NOT_PREV_COMPLIANT, [float(1.0)] * 31
            )
        )
    )
    scenarios.append(full_FIT_compliance)

    # Full Colonoscopy compliance baseline
    full_Colonoscopy_compliance = (
        Scenario(name="full_Colonoscopy_compliance", params=get_default_params())
        .transform(transform_colonoscopy_only())
        .transform(transform_routine_proportion(Test.FIT, 0.0))
        .transform(transform_routine_proportion(Test.COLONOSCOPY, 1.0))
        .transform(transform_initial_compliance(1.0))
        .transform(
            transform_conditional_compliance_rates(
                ConditionalComplianceParam.PREV_COMPLIANT, [float(1.0)] * 31
            )
        )
        .transform(
            transform_conditional_compliance_rates(
                ConditionalComplianceParam.NOT_PREV_COMPLIANT, [float(1.0)] * 31
            )
        )
    )
    scenarios.append(full_Colonoscopy_compliance)

    return scenarios


def run(n: Optional[int] = None) -> None:
    if n is None:
        n = NUM_ITERATIONS
    rng = random.Random(SEED)
    prepare_experiment_dir(scenarios=create_scenarios(), num_iterations=n, rng=rng)


def main() -> None:
    fire.Fire(run)


if __name__ == "__main__":
    main()
