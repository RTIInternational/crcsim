import json
import random
from pathlib import Path
from typing import Callable, Dict, List, Optional
from copy import deepcopy

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

def transform_repeat_compliance(rate: float, test: str) -> Callable:
    def transform(params):
        params[f"{test}_compliance_rate"] = rate

    return transform


def transform_delayed_onset_compliance(age_ranges, compliance_rates, test) -> Callable:
    def transform(params):
        params["delayed_onset_compliance"] = {
            "age_ranges": age_ranges,
            "compliance_rates": compliance_rates,
            "test": test
        }
    return transform

def transform_random_compliance(test: str) -> Callable:
    def transform(params):
        params["random_compliance"] = {
            "test": test
        }
        initial_compliance_rate = random.uniform(0.5, 0.9)
        params["tests"][test]["initial_compliance_rate"] = initial_compliance_rate
        for year in range(1, 10):
            conditional_compliance_rate = random.uniform(0.5, 0.9)
            params["tests"][test][f"compliance_rate_year_{year}"] = conditional_compliance_rate

    return transform
def transform_test_frequency(test: str, frequency: int) -> Callable:
    def transform(params):
        params["tests"][test]["frequency_years"] = frequency
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
    low_diagnostic_compliance_rate = 0.525
    lower_repeat_compliance = 0.8
    low_surveillance_freq_mild = 10
    low_surveillance_freq_severe = 2
    low_surveillance_end_age = 80
    start_age = 50
    end_age = 75
    scenarios = []

    fifty_percent_compliance = {year: 0.5 for year in range(start_age, end_age + 1)}
    twenty_percent_compliance = {year: 0.2 for year in range(start_age, end_age + 1)}

    for fqhc, rates in initial_compliance.items():
        baseline = Scenario(
            name=f"{fqhc}_baseline", params=get_default_params()
        ).transform(transform_initial_compliance(rates[0]))
        scenarios.append(baseline)

        implementation = Scenario(
            name=f"{fqhc}_implementation", params=get_default_params()
        ).transform(transform_initial_compliance(rates[1]))
        scenarios.append(implementation)

        # Scenarios: 100% FIT compliance
        implementation_100_compliance = deepcopy(implementation)
        implementation_100_compliance.transform(
            transform_repeat_compliance(1.0, "FIT")
        )
        implementation_100_compliance.name = f"{fqhc}_implementation_100_compliance"
        scenarios.append(implementation_100_compliance)

        # Scenarios: 0% FIT Compliance
        implementation_0_compliance = deepcopy(implementation)
        implementation_0_compliance.transform(
            transform_repeat_compliance(0.0, "FIT")
        )
        implementation_0_compliance.name = f"{fqhc}_implementation_0_FIT_compliance"
        scenarios.append(implementation_0_compliance)

        # Scenarios: Delayed Onset Scenarios 50 to 64
        delayed_onset_50_64 = deepcopy(implementation)
        delayed_onset_50_64.transform(
            transform_delayed_onset_compliance(
                age_ranges=[(50, 64), (65, 75)],
                compliance_rates=[0.0, 1.0],
                test="FIT"
            )
        )
        delayed_onset_50_64.name = f"{fqhc}_delayed_onset_50_64"
        scenarios.append(delayed_onset_50_64)

        # Scenarios: Delayed Onset Scenarios 50 to 59
        delayed_onset_50_59 = deepcopy(implementation)
        delayed_onset_50_59.transform(
            transform_delayed_onset_compliance(
                age_ranges=[(50, 59), (60, 75)],
                compliance_rates=[0.0, 1.0],
                test="FIT"
            )
        )
        delayed_onset_50_59.name = f"{fqhc}_delayed_onset_50_59"
        scenarios.append(delayed_onset_50_59)

        # Scenario for every other year testing
        one_year_testing = deepcopy(implementation)
        one_year_testing.transform(
            transform_test_frequency("FIT", 2)
        )
        one_year_testing.name = f"{fqhc}_one_year_testing"
        scenarios.append(one_year_testing)

        # Scenario for every five years testing
        five_years_testing = deepcopy(implementation)
        five_years_testing.transform(
            transform_test_frequency("FIT", 5) 
        )
        five_years_testing.name = f"{fqhc}_five_years_testing"
        scenarios.append(five_years_testing)
        # Scenario with 50% compliance every year
        random_50_compliance = deepcopy(implementation)
        random_50_compliance.transform(
            transform_random_compliance("FIT", fifty_percent_compliance)
        )
        random_50_compliance.name = f"{fqhc}_random_50_compliance"
        scenarios.append(random_50_compliance)

        # Scenario with 20% compliance every year
        random_20_compliance = deepcopy(implementation)
        random_20_compliance.transform(
            transform_random_compliance("FIT", twenty_percent_compliance)
        )
        random_20_compliance.name = f"{fqhc}_random_20_compliance"
        scenarios.append(random_20_compliance)

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
