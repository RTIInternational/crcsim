import json
import random
from copy import deepcopy
from enum import Enum, unique
from pathlib import Path
from typing import Callable, Dict, List, Optional

import fire

SEED: int = 49865106
NUM_ITERATIONS: int = 100


@unique
class Test(Enum):
    FIT = "FIT"
    COLONOSCOPY = "Colonoscopy"


@unique
class ConditionalComplianceParam(Enum):
    PREV_COMPLIANT = "compliance_rate_given_prev_compliant"
    NOT_PREV_COMPLIANT = "compliance_rate_given_not_prev_compliant"


class Scenario:
    def __init__(self, name: str, params: Dict):
        self.name = name
        self.params = params

    def transform(self, transformer: Callable) -> "Scenario":
        transformer(self.params)
        return self


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


def transform_lesion_risk_alpha(IRR: float) -> Callable:
    def transform(params):
        params["lesion_risk_alpha"] = params["lesion_risk_alpha"] * IRR

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


def transform_routine_ages(test: Test, start_age: int, end_age: int) -> Callable:
    def transform(params):
        params["tests"][test.value]["routine_start"] = start_age
        params["tests"][test.value]["routine_end"] = end_age

    return transform


def transform_routine_proportion(test: Test, proportion: float) -> Callable:
    def transform(params):
        params["tests"][test.value]["proportion"] = proportion

    return transform


def create_scenarios() -> List:
    # For each health center, define the initial compliance rate in the baseline
    # scenario and the implementation scenario and vary diagnostic compliance.
    initial_compliance = {
        "fqhc1": (0.522, 0.593),
        "fqhc2": (0.154, 0.421),
        "fqhc3": (0.519, 0.568),
        "fqhc4": (0.278, 0.374),
        "fqhc5": (0.383, 0.572),
        "fqhc6": (0.211, 0.392),
        "fqhc7": (0.257, 0.354),
        "fqhc8": (0.190, 0.390),
    }
    low_initial_stage_3_treatment_cost = 67_300
    low_initial_stage_4_treatment_cost = 97_931
    extra_low_initial_stage_3_treatment_cost = 50_000
    extra_low_initial_stage_4_treatment_cost = 80_000

    diagnostic_compliance_rates = {
        "100Compliance": 1.0,
        "80Compliance": 0.8,
    }
    scenarios = []

    for fqhc, sreening_rates in initial_compliance.items():
        for compliance, diagnostic_rate in diagnostic_compliance_rates.items():
            baseline = (
                Scenario(
                    name=f"{fqhc}_{compliance}_baseline", params=get_default_params()
                )
                .transform(transform_initial_compliance(sreening_rates[0]))
                .transform(transform_diagnostic_compliance(diagnostic_rate))
            )
            scenarios.append(baseline)

            implementation = (
                Scenario(
                    name=f"{fqhc}_{compliance}_implementation",
                    params=get_default_params(),
                )
                .transform(transform_initial_compliance(sreening_rates[1]))
                .transform(transform_diagnostic_compliance(diagnostic_rate))
            )
            scenarios.append(implementation)

            # Sensitivity analysis 2. Lower cost for stage III and stage IV initial phase
            baseline_low_cost = deepcopy(baseline)
            baseline_low_cost.transform(
                transform_treatment_cost(
                    "3", "initial", low_initial_stage_3_treatment_cost
                )
            ).transform(
                transform_treatment_cost(
                    "4", "initial", low_initial_stage_4_treatment_cost
                )
            )
            baseline_low_cost.name = (
                f"{fqhc}_{compliance}_baseline_low_initial_treat_cost"
            )
            scenarios.append(baseline_low_cost)

            implementation_low_cost = deepcopy(implementation)
            implementation_low_cost.transform(
                transform_treatment_cost(
                    "3", "initial", low_initial_stage_3_treatment_cost
                )
            ).transform(
                transform_treatment_cost(
                    "4", "initial", low_initial_stage_4_treatment_cost
                )
            )
            implementation_low_cost.name = (
                f"{fqhc}_{compliance}_implementation_low_initial_treat_cost"
            )
            scenarios.append(implementation_low_cost)

            # Sensitivity analysis 2a. Extra low cost for stage III and stage IV initial phase
            baseline_extra_low_cost = deepcopy(baseline)
            baseline_extra_low_cost.transform(
                transform_treatment_cost(
                    "3", "initial", extra_low_initial_stage_3_treatment_cost
                )
            ).transform(
                transform_treatment_cost(
                    "4", "initial", extra_low_initial_stage_4_treatment_cost
                )
            )
            baseline_extra_low_cost.name = (
                f"{fqhc}_{compliance}_baseline_extra_low_initial_treat_cost"
            )
            scenarios.append(baseline_extra_low_cost)

            implementation_extra_low_cost = deepcopy(implementation)
            implementation_extra_low_cost.transform(
                transform_treatment_cost(
                    "3", "initial", extra_low_initial_stage_3_treatment_cost
                )
            ).transform(
                transform_treatment_cost(
                    "4", "initial", extra_low_initial_stage_4_treatment_cost
                )
            )
            implementation_extra_low_cost.name = (
                f"{fqhc}_{compliance}_implementation_extra_low_initial_treat_cost"
            )
            scenarios.append(implementation_extra_low_cost)

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
