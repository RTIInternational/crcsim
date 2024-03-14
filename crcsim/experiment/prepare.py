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
class ConditionalComplianceParam(Enum):
    PREV_COMPLIANT = "compliance_rate_given_prev_compliant"
    NOT_PREV_COMPLIANT = "compliance_rate_given_not_prev_compliant"


@unique
class Test(Enum):
    FIT = "FIT"
    COLONOSCOPY = "Colonoscopy"


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


def transform_conditional_compliance_rates(
    test: Test, param: ConditionalComplianceParam, rates: List[float]
) -> Callable:
    """
    Replaces a conditional compliance parameter with a new set of rates.
    """

    def transform(params):
        params["tests"][test.value][param.value] = rates

    return transform


def transform_delayed_onset(test: Test, onset_age: int) -> Callable:
    """
    Transforms the necessary compliance parameters such that, for the given test,
    compliance is 0.0 for all years before the given age, and 1.0 for all years
    after the given age.
    """

    def transform(params):
        start_age = params["tests"][test.value]["routine_start"]
        # Testing years are inclusive, so add 1
        testing_years = params["tests"][test.value]["routine_end"] - start_age + 1

        # Initial compliance is 0
        params["initial_compliance_rate"] = 0.0

        # Then everyone remains noncompliant until the given age.
        compliance_rate_given_not_prev_compliant = [0.0] * testing_years
        onset_year = onset_age - start_age
        compliance_rate_given_not_prev_compliant[onset_year] = 1.0
        params["tests"][test.value][
            "compliance_rate_given_not_prev_compliant"
        ] = compliance_rate_given_not_prev_compliant

        # Then everyone remains compliant after the given age.
        # We can just set the compliance rate to 1.0 for all years, including those before
        # the onset age, because initial compliance is 0.0.
        compliance_rate_given_prev_compliant = [1.0] * testing_years
        params["tests"][test.value][
            "compliance_rate_given_prev_compliant"
        ] = compliance_rate_given_prev_compliant

    return transform


def transform_routine_freq(test: Test, freq: int) -> Callable:
    def transform(params):
        params["tests"][test.value]["routine_freq"] = freq

    return transform


def create_scenarios() -> List:

    scenarios = []

    # Scenarios: 100% FIT compliance
    always_compliant = Scenario(
        name="always_compliant", params=get_default_params()
    ).transform(transform_initial_compliance(1.0))
    scenarios.append(always_compliant)

    # Scenarios: 0% FIT Compliance
    never_compliant = Scenario(
        name="never_compliant", params=get_default_params()
    ).transform(transform_initial_compliance(0.0))
    scenarios.append(never_compliant)

    # Scenarios: Delayed Onset Until Age 60
    delayed_onset_60 = Scenario(
        name="delayed_onset_60", params=get_default_params()
    ).transform(transform_delayed_onset(Test.FIT, 60))
    scenarios.append(delayed_onset_60)

    # Scenarios: Delayed Onset Until Age 65
    delayed_onset_65 = Scenario(
        name="delayed_onset_65", params=get_default_params()
    ).transform(transform_delayed_onset(Test.FIT, 65))
    scenarios.append(delayed_onset_65)

    # Scenario for every other year testing
    every_two_years = Scenario(
        name="every_two_years", params=get_default_params()
    ).transform(transform_routine_freq(Test.FIT, 2))
    scenarios.append(every_two_years)

    # Scenario for every five years testing
    every_five_years = Scenario(
        name="every_five_years", params=get_default_params()
    ).transform(transform_routine_freq(Test.FIT, 5))
    scenarios.append(every_five_years)

    # Scenario with 50% compliance every year
    #
    # Shorthand to create conditional compliance arrays without specifying each year.
    # Conditional compliance arrays are length 26, one for each year of testing (50-75).
    fifty_percent_compliance_rates = [0.5] * 26

    fifty_percent_compliance = Scenario(
        name="fifty_percent_compliance", params=get_default_params()
    ).transform(
        transform_conditional_compliance_rates(
            Test.FIT,
            ConditionalComplianceParam.PREV_COMPLIANT,
            fifty_percent_compliance_rates,
        )
    )
    scenarios.append(fifty_percent_compliance)

    # Scenario with 20% compliance every year
    twenty_percent_compliance_rates = [0.2] * 26

    twenty_percent_compliance = Scenario(
        name="twenty_percent_compliance", params=get_default_params()
    ).transform(
        transform_conditional_compliance_rates(
            Test.FIT,
            ConditionalComplianceParam.PREV_COMPLIANT,
            twenty_percent_compliance_rates,
        )
    )
    scenarios.append(twenty_percent_compliance)

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
