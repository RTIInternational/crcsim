import json
import random
from pathlib import Path
from typing import Callable, Dict, List, Optional
from copy import copy

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


def transform_treatment_cost(stage: str, phase: str, value: int) -> Callable:
    def transform(params):
        params[f"cost_treatment_stage{stage}_{phase}"] = value

    return transform


# TODO: add transform function to handle lowered repeat compliance
def transform_repeat_Compliance(rate) -> Callable:
    def transform(params):
        params["lowered_repeat_compliance"] = rate

    return transform

# TODO: add transform function to handle lowered diagnostic compliance

def transform_Compliance_with_diagnostic_colonoscopy(rate) -> Callable:
    def transform(params):
        params["diagnostic_compliance_rate"] = rate

    return transform

def create_scenarios() -> List:
    # For each health center, define the initial compliance rate in the baseline
    # scenario and the implementation scenario.
    initial_compliance = {
        "fqhc1": (0.522, 0.593),
        "fqhc2": (0.154, 0.421),
        "fqhc3": (0.519, 0.615),
        "fqhc4": (0.278, 0.374),
        "fqhc5": (0.383, 0.572),
        "fqhc6": (0.211, 0.392),
        "fqhc7": (0.257, 0.354),
        "fqhc8": (0.190, 0.390),
    }
    low_initial_stage_3_treatment_cost = 67_300
    low_initial_stage_4_treatment_cost = 97_931
    diagnostic_compliance_rate= 1.0
    lower_repeat_compliance=0.0
    scenarios = []

    for fqhc, rates in initial_compliance.items():
        baseline = Scenario(
            name=f"{fqhc}_baseline", params=get_default_params()
        ).transform(transform_initial_compliance(rates[0]))
        scenarios.append(baseline)

        implementation = Scenario(
            name=f"{fqhc}_implementation", params=get_default_params()
        ).transform(transform_initial_compliance(rates[1]))
        scenarios.append(implementation)

        # TODO: Sensitivity Analysis 1.  Lower repeat compliance (note that the baseline runs stay the same)
        baseline_lower_repeat_compliance = copy(baseline)
        baseline_lower_repeat_compliance.name = f"{fqhc}_baseline_Lower_repeat_compliance"
        scenarios.append(baseline_lower_repeat_compliance)
        implementation_lower_repeat_compliance = copy(implementation)
        implementation_lower_repeat_compliance.transform(
            transform_repeat_Compliance(lower_repeat_compliance)
        )
        implementation_lower_repeat_compliance.name = f"{fqhc}_implementation_Lower_repeat_compliance"
        scenarios.append(implementation_lower_repeat_compliance)

        # Sensitivity analysis 2. Lower cost for stage III and stage IV initial phase
        baseline_low_cost = copy(baseline)
        baseline_low_cost.transform(
            transform_treatment_cost("3", "initial", low_initial_stage_3_treatment_cost)
        ).transform(
            transform_treatment_cost("4", "initial", low_initial_stage_4_treatment_cost)
        )
        baseline_low_cost.name = f"{fqhc}_baseline_low_initial_treat_cost"
        scenarios.append(baseline_low_cost)

        implementation_low_cost = copy(implementation)
        implementation_low_cost.transform(
            transform_treatment_cost("3", "initial", low_initial_stage_3_treatment_cost)
        ).transform(
            transform_treatment_cost("4", "initial", low_initial_stage_4_treatment_cost)
        )
        implementation_low_cost.name = f"{fqhc}_implementation_low_initial_treat_cost"
        scenarios.append(implementation_low_cost)

        # TODO: Sensitivity analysis 3. Lower compliance with diagnostic colonoscopy
        baseline_lower_compliance = copy(baseline)
        baseline_lower_compliance.transform(
            transform_Compliance_with_diagnostic_colonoscopy(diagnostic_compliance_rate)
        )
        baseline_lower_compliance.name = f"{fqhc}_baseline_Lower_compliance_with_diagnostic_colonoscopy"
        scenarios.append(baseline_lower_compliance)

        implementation_lower_compliance = copy(implementation)
        implementation_lower_compliance.transform(
            transform_Compliance_with_diagnostic_colonoscopy(diagnostic_compliance_rate)
        )
        implementation_lower_compliance.name = f"{fqhc}_implementation_Lower_compliance_with_diagnostic_colonoscopy"
        scenarios.append(implementation_lower_compliance)

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
