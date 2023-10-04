import json
import random
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


def transform_FIT_routine_ages(age: int) -> Callable:
    def transform(params):
        for p in ["routine_start", "routine_end"]:
            params["tests"]["FIT"][p] = age

    return transform


def transform_routine_test_proportion(test: str, proportion: float) -> Callable:
    def transform(params):
        params["tests"][test]["proportion"] = proportion

    return transform


def create_scenarios() -> List:
    scenarios = []

    # No screening
    #
    # Start and end ages are enforced by skipping testing logic if simulation time is
    # less than routine_start or greater than routine end. Setting both to -1 ensures
    # that simulation time will always be greater than routine end, so no routine
    # testing will ever be performed.
    no_screening = Scenario(name="no_screening", params=get_default_params()).transform(
        transform_FIT_routine_ages(-1)
    )
    scenarios.append(no_screening)

    # 100% routine test proportions
    # Default parameters are already 100% FIT, so all we need to do there is adjust
    # compliance.
    all_fit = Scenario(name="all_FIT", params=get_default_params()).transform(
        transform_initial_compliance(1.0)
    )
    scenarios.append(all_fit)

    all_colonoscopy = Scenario(
        name="all_colonoscopy", params=get_default_params()
    ).transform(transform_initial_compliance(1.0))
    all_colonoscopy.transform(transform_routine_test_proportion("FIT", 0.0))
    all_colonoscopy.transform(transform_routine_test_proportion("Colonoscopy", 1.0))
    scenarios.append(all_colonoscopy)

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
