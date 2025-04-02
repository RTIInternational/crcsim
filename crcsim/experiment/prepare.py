import json
import random
from enum import Enum, unique
from pathlib import Path
from typing import Callable, Dict, List, Optional, TypedDict, cast

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


class ScenarioVariation(TypedDict):
    name: str
    freq: int


@unique
class ConditionalComplianceParam(Enum):
    PREV_COMPLIANT = "compliance_rate_given_prev_compliant"
    NOT_PREV_COMPLIANT = "compliance_rate_given_not_prev_compliant"


@unique
class Test(Enum):
    FIT = "FIT"
    # COLONOSCOPY = "Colonoscopy"
    # FDNA = "FDNA"
    # BLOOD = "Blood"


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


def transform_initial_compliance(rate) -> Callable:
    def transform(params):
        params["initial_compliance_rate"] = rate

    return transform


def transform_diagnostic_compliance(rate) -> Callable:
    def transform(params):
        params["diagnostic_compliance_rate"] = rate

    return transform


def transform_conditional_compliance_rates(
    param: ConditionalComplianceParam, rates: List[float]
) -> Callable:
    """
    Replaces a conditional compliance parameter with a new set of rates.
    """

    def transform(params):
        for test in params["tests"].keys():
            params["tests"][test][param.value] = rates

    return transform


def transform_routine_freq(test: Test, freq: int) -> Callable:
    def transform(params):
        params["tests"][test.value]["routine_freq"] = freq

    return transform


def transform_routine_proportion(test: Test, proportion: float) -> Callable:
    def transform(params):
        params["tests"][test.value]["proportion"] = proportion

    return transform


def transform_test_cost(test: Test, cost: int) -> Callable:
    def transform(params):
        params["tests"][test.value]["cost"] = cost

    return transform


def transform_routine_ages(test: Test, start_age: int, end_age: int) -> Callable:
    def transform(params):
        params["tests"][test.value]["routine_start"] = start_age
        params["tests"][test.value]["routine_end"] = end_age

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


def transform_use_conditional_compliance(enabled: bool) -> Callable:
    def transform(params):
        params["use_conditional_compliance"] = enabled

    return transform


def create_scenarios() -> List[Scenario]:
    scenarios = []

    # No screening baseline scenario
    no_screening = (
        Scenario(name="no_screening", params=get_default_params())
        .transform(transform_fit_only())
        .transform(transform_routine_proportion(Test.FIT, 1.0))
        .transform(transform_routine_ages(Test.FIT, -1, -1))
    )
    scenarios.append(no_screening)

    # Full compliance baseline
    full_compliance = (
        Scenario(name="full_compliance", params=get_default_params())
        .transform(transform_fit_only())
        .transform(transform_routine_proportion(Test.FIT, 1.0))
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
    scenarios.append(full_compliance)

    # 3a. Fifty percent same agent scenario (same 50% of people always screen)
    fifty_same = (
        Scenario(name="fifty_percent_same_agent", params=get_default_params())
        .transform(transform_fit_only())
        .transform(transform_routine_proportion(Test.FIT, 1.0))
        .transform(transform_initial_compliance(0.5))
        .transform(transform_use_conditional_compliance(True))
        .transform(
            transform_conditional_compliance_rates(
                ConditionalComplianceParam.PREV_COMPLIANT, [float(1.0)] * 31
            )
        )
        .transform(
            transform_conditional_compliance_rates(
                ConditionalComplianceParam.NOT_PREV_COMPLIANT, [float(0.0)] * 31
            )
        )
    )
    scenarios.append(fifty_same)

    # 3b. Fifty percent random scenario (pure random, no conditional compliance)
    fifty_random = (
        Scenario(name="fifty_percent_random", params=get_default_params())
        .transform(transform_fit_only())
        .transform(transform_routine_proportion(Test.FIT, 1.0))
        .transform(transform_initial_compliance(0.5))
        .transform(transform_use_conditional_compliance(False))
        .transform(
            transform_conditional_compliance_rates(
                ConditionalComplianceParam.PREV_COMPLIANT, [float(0.5)] * 31
            )
        )
        .transform(
            transform_conditional_compliance_rates(
                ConditionalComplianceParam.NOT_PREV_COMPLIANT, [float(0.5)] * 31
            )
        )
    )
    scenarios.append(fifty_random)

    # 4. Delayed compliance scenarios
    delayed_scenarios = {
        "delayed_65": {
            "start_age": 65,
            "rates": [0.0] * 20 + [1.0] * 11,  # 0% 45-64, 100% 65-75
        },
        "delayed_55": {
            "start_age": 55,
            "rates": [0.0] * 10 + [1.0] * 21,  # 0% 45-54, 100% 55-75
        },
    }

    for name, config in delayed_scenarios.items():
        rates: List[float] = cast(List[float], config["rates"])  # Cast to List[float]
        scenario = (
            Scenario(name=name, params=get_default_params())
            .transform(transform_fit_only())
            .transform(transform_routine_proportion(Test.FIT, 1.0))
            .transform(transform_initial_compliance(0.0))
            .transform(
                transform_conditional_compliance_rates(
                    ConditionalComplianceParam.PREV_COMPLIANT, rates
                )
            )
            .transform(
                transform_conditional_compliance_rates(
                    ConditionalComplianceParam.NOT_PREV_COMPLIANT, rates
                )
            )
        )
        scenarios.append(scenario)

    # 5. Age-specific compliance scenarios
    age_specific_high_rates: List[float] = (
        [0.50] * 10
        + [0.75] * 10  # 50% for ages 45-54
        + [0.50] * 11  # 75% for ages 55-64  # 50% for ages 65-75
    )
    age_specific_high = (
        Scenario(name="age_specific_high", params=get_default_params())
        .transform(transform_fit_only())
        .transform(transform_routine_proportion(Test.FIT, 1.0))
        .transform(transform_initial_compliance(0.5))
        .transform(
            transform_conditional_compliance_rates(
                ConditionalComplianceParam.PREV_COMPLIANT, age_specific_high_rates
            )
        )
        .transform(
            transform_conditional_compliance_rates(
                ConditionalComplianceParam.NOT_PREV_COMPLIANT, age_specific_high_rates
            )
        )
    )
    scenarios.append(age_specific_high)

    # Age-specific low compliance scenario
    age_specific_low_rates: List[float] = (
        [0.25] * 10
        + [0.50] * 10  # 25% for ages 45-54
        + [0.25] * 11  # 50% for ages 55-64
        + [0.25] * 11  # 25% for ages 65-75
    )
    age_specific_low = (
        Scenario(name="age_specific_low", params=get_default_params())
        .transform(transform_fit_only())
        .transform(transform_routine_proportion(Test.FIT, 1.0))
        .transform(transform_initial_compliance(0.25))
        .transform(
            transform_conditional_compliance_rates(
                ConditionalComplianceParam.PREV_COMPLIANT, age_specific_low_rates
            )
        )
        .transform(
            transform_conditional_compliance_rates(
                ConditionalComplianceParam.NOT_PREV_COMPLIANT, age_specific_low_rates
            )
        )
    )
    scenarios.append(age_specific_low)

    # 6. Random intervals with conditional compliance
    fixed_rates = {"fifty_percent": 0.5, "twenty_percent": 0.2}

    for name, rate in fixed_rates.items():
        rates = [rate] * 31  # Same rate for all 31 years (ages 45-75)
        scenario = (
            Scenario(name=name, params=get_default_params())
            .transform(transform_fit_only())
            .transform(transform_routine_proportion(Test.FIT, 1.0))
            .transform(transform_initial_compliance(rate))
            .transform(transform_use_conditional_compliance(True))
            .transform(
                transform_conditional_compliance_rates(
                    ConditionalComplianceParam.PREV_COMPLIANT, rates
                )
            )
            .transform(
                transform_conditional_compliance_rates(
                    ConditionalComplianceParam.NOT_PREV_COMPLIANT, rates
                )
            )
        )
        scenarios.append(scenario)

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
