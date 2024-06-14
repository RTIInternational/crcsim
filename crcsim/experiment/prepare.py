import json
import random
from enum import Enum, unique
from pathlib import Path
from typing import Callable, Dict, List, Optional, TypedDict

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
    #COLONOSCOPY = "Colonoscopy"
    FDNA = "FDNA"
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

    # Simple random screening compliance scenarios
    screening_compliance_rates = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    for compliance_rate in screening_compliance_rates:
        scenarios.extend(
            create_scenarios_per_test(
                transformers=[
                    transform_initial_compliance(compliance_rate),
                ],
                name_suffix=f"_screening_compliance_{compliance_rate * 100}",
            )
        )

    # Diagnostic compliance scenarios for 50% and 80% screening compliance rates
    diagnostic_compliance_rates = [0.5, 0.8]
    for screening_compliance_rate in [0.5, 0.8]:
        for diagnostic_compliance_rate in diagnostic_compliance_rates:
            scenarios.extend(
                create_scenarios_per_test(
                    transformers=[
                        transform_initial_compliance(screening_compliance_rate),
                        transform_diagnostic_compliance(diagnostic_compliance_rate),
            ],
            name_suffix=f"_{int(screening_compliance_rate * 100)}_screening_and_{int(diagnostic_compliance_rate * 100)}_diagnostic_compliance",
        )
    )

    # Diagnostic compliance scenarios for 100% screening compliance rate
    diagnostic_compliance_rates = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    for diagnostic_compliance_rate in diagnostic_compliance_rates:
        scenarios.extend(
            create_scenarios_per_test(
                transformers=[
                    transform_initial_compliance(1.0),
                    transform_diagnostic_compliance(diagnostic_compliance_rate),
            ],
            name_suffix=f"_diagnostic_compliance_{int(diagnostic_compliance_rate * 100)}",
        )
    )
    
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
