import json
import random
from enum import Enum, unique
from pathlib import Path
from typing import Callable, Dict, List, Optional, TypedDict

import fire
from combine_tests import combine_tests_in_params

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
    COLONOSCOPY = "Colonoscopy"
    FDNA = "FDNA"
    EMERGENT_STOOL = "Emergent_stool"
    BLOOD = "Blood"


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


def transform_combine_tests(test1: Test, test2: Test, how: str) -> Callable:
    def transform(params):
        combine_tests_in_params(params, test1.value, test2.value, how)

        # Double-check that only the combined test is in routine_tests
        combined_test_name = f"{test1.value}_{test2.value}_{how}"
        params["routine_tests"] = [combined_test_name]

        # Double-check that only the combined test has proportion > 0
        for test_name in params["tests"]:
            if test_name == combined_test_name:
                params["tests"][test_name]["proportion"] = 1.0
            else:
                params["tests"][test_name]["proportion"] = 0.0

    return transform


def create_scenarios() -> List[Scenario]:
    scenarios = []

    def create_scenarios_per_test(
        transformers: List[Callable], name_suffix: str
    ) -> List[Scenario]:
        """
        This experiment consists of several blocks of scenarios. Each block consists
        of the same set of routine tests. The blocks differ in compliance rates and/or
        screening costs. This function creates a scenario for each test in a block to
        avoid repeating this code for each block.
        """
        scenarios: List[Scenario] = []

        for test in Test:
            scenario = Scenario(
                name=test.value + name_suffix, params=get_default_params()
            ).transform(transform_routine_proportion(test, 1.0))
            scenarios.append(scenario)

        # In addition to the default params for each test, we also want a few extra
        # scenarios with variations on the routine frequency.
        variations: Dict[Test, ScenarioVariation] = {
            Test.FDNA: {"name": "FDNA_annual", "freq": 1},
            Test.EMERGENT_STOOL: {"name": "Emergent_stool_3y", "freq": 3},
            Test.BLOOD: {"name": "Blood_annual", "freq": 1},
        }

        for test, variation in variations.items():
            scenario = (
                Scenario(
                    name=variation["name"] + name_suffix,
                    params=get_default_params(),
                )
                .transform(transform_routine_proportion(test, 1.0))
                .transform(transform_routine_freq(test, variation["freq"]))
            )
            scenarios.append(scenario)

        for transformer in transformers:
            scenarios = [s.transform(transformer) for s in scenarios]

        return scenarios

    # No screening
    no_screening = (
        Scenario(name="no_screening", params=get_default_params())
        .transform(transform_routine_proportion(Test.FIT, 1.0))
        .transform(transform_routine_ages(Test.FIT, -1, -1))
    )
    scenarios.append(no_screening)

    # 100% compliance
    scenarios.extend(
        create_scenarios_per_test(
            transformers=[transform_initial_compliance(1.0)],
            name_suffix="_100_compliance",
        )
    )

    """#  repeat for 80, 50, and 30% compliance
    scenarios.extend(
        create_scenarios_per_test(
            transformers=[
                transform_initial_compliance(0.80),
            ],
            name_suffix="_80_compliance",
        )
    )
    scenarios.extend(
        create_scenarios_per_test(
            transformers=[
                transform_initial_compliance(0.50),
            ],
            name_suffix="_50_compliance",
        )
    )
    scenarios.extend(
        create_scenarios_per_test(
            transformers=[
                transform_initial_compliance(0.30),
            ],
            name_suffix="_30_compliance",
        )
    )

    # 100% to 40% descending compliance
    rates = [1.0] * 10 + [0.7] * 10 + [0.4] * 10 + [0.0]
    scenarios.extend(
        create_scenarios_per_test(
            transformers=[
                transform_initial_compliance(1.0),
                transform_conditional_compliance_rates(
                    ConditionalComplianceParam.PREV_COMPLIANT, rates
                ),
            ],
            name_suffix="_100_to_40_compliance",
        )
    )

    #  100% screening and 50% diagnostic compliance.
    scenarios.extend(
        create_scenarios_per_test(
            transformers=[
                transform_initial_compliance(1.0),
                transform_diagnostic_compliance(0.5),
            ],
            name_suffix="_100_screening_and_50_diagnostic_compliance",
        )
    )

    #  100% screening and low screening cost.
    scenarios.extend(
        create_scenarios_per_test(
            transformers=[
                transform_initial_compliance(1.0),
                transform_test_cost(Test.EMERGENT_STOOL, 300),
                transform_test_cost(Test.BLOOD, 600),
                transform_test_cost(Test.FDNA, 300),
                transform_test_cost(Test.COLONOSCOPY, 700),
                transform_test_cost(Test.FIT, 20),
            ],
            name_suffix="_100_screening_and_low_screening_cost",
        )
    )
    # 100% screening and high screening cost.
    scenarios.extend(
        create_scenarios_per_test(
            transformers=[
                transform_initial_compliance(1.0),
                transform_test_cost(Test.EMERGENT_STOOL, 1000),
                transform_test_cost(Test.BLOOD, 1200),
                transform_test_cost(Test.FDNA, 681),
                transform_test_cost(Test.COLONOSCOPY, 1193),
                transform_test_cost(Test.FIT, 22),
            ],
            name_suffix="_100_screening_and_high_screening_cost",
        )
    )"""

    # Add combined test scenarios
    combined_test_scenarios = []

    # Define combinations to test
    test_combinations = [
        (Test.FIT, Test.BLOOD, "serial"),
        (Test.FIT, Test.BLOOD, "parallel"),
    ]

    for test1, test2, how in test_combinations:
        suffix = f"_{test1.value}_{test2.value}_{how}"

        # Create scenario with 100% compliance
        scenario = (
            Scenario(
                name=f"combined{suffix}_100_compliance", params=get_default_params()
            )
            .transform(transform_combine_tests(test1, test2, how))
            .transform(transform_initial_compliance(1.0))
        )
        combined_test_scenarios.append(scenario)

        # Create scenario with 80% compliance
        scenario = (
            Scenario(
                name=f"combined{suffix}_80_compliance", params=get_default_params()
            )
            .transform(transform_combine_tests(test1, test2, how))
            .transform(transform_initial_compliance(0.8))
        )
        combined_test_scenarios.append(scenario)

    scenarios.extend(combined_test_scenarios)

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
