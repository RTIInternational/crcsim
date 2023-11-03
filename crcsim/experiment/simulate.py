from pathlib import Path

import boto3
import fire


def get_scenario_list() -> list:
    """
    Search the scenarios directory for all parameter files. Add name of each
    parent folder to scenario list. Assumes scenario directory has the structure
    generated by prepare.py:

        scenarios/
            scenario_1/
                params.json
            scenario_2/
                params.json
    """
    scenarios = []

    for results_file in Path("./scenarios").glob("*/params.json"):
        scenarios.append(results_file.parent.name)

    return scenarios


def get_seed_list() -> list:
    """
    Generate a list of integer seeds from ./scenarios/seeds.txt. Assumes seeds.txt has
    one seed per line.
    """
    with open(Path("./scenarios/seeds.txt")) as f:
        seeds = f.read().splitlines()
    return seeds


def run(
    n_people: int = 100_000,
    job_queue: str = "crcsim",
    job_definition: str = "crcsim:3",
):
    scenarios = get_scenario_list()
    seeds = get_seed_list()

    batch = boto3.client("batch")

    for scenario in scenarios:
        for iteration, seed in enumerate(seeds):
            iteration_name = f"{iteration:03}"

            job = batch.submit_job(
                jobName=scenario + f"_{iteration_name}",
                jobQueue=job_queue,
                jobDefinition=job_definition,
                parameters={
                    "npeople": str(n_people),
                    "iteration": iteration_name,
                    "seed": seed,
                    "scenario": scenario,
                },
            )
            print(
                f"Submitting iteration {iteration_name} for scenario {scenario}, Job ID {job['jobId']}"
            )


def main():
    fire.Fire(run)


if __name__ == "__main__":
    test = ""
    main()
