from datetime import datetime
from typing import Dict, List

import boto3
from botocore.config import Config
from fire import Fire

from crcsim.experiment.simulate import get_seed_list


def get_failed_jobs(
    start_date: str, job_queue: str, batch_client: boto3.client
) -> List[Dict[str, str]]:
    """
    Checks the given AWS Batch job queue for failed jobs created after the given
    start date. Returns the senario and iteration for each failed job.
    """
    start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
    # convert to milliseconds to match the timestamp format returned by list_jobs
    start_timestamp = int(start_datetime.timestamp() * 1_000)

    failed_jobs = batch_client.list_jobs(jobQueue=job_queue, jobStatus="FAILED")[
        "jobSummaryList"
    ]

    failed_jobs_in_range = [
        job for job in failed_jobs if job["createdAt"] >= start_timestamp
    ]

    failed_job_names = [job["jobName"].rsplit("_", 1) for job in failed_jobs_in_range]

    return [{"scenario": name[0], "iteration": name[1]} for name in failed_job_names]


def main(
    start_date: str,
    n_people: int = 100_000,
    job_queue: str = "crcsim",
    job_definition: str = "crcsim:3",
):
    my_config = Config(region_name="us-east-2")
    batch = boto3.client("batch", config=my_config)

    failed_job_params = get_failed_jobs(start_date, job_queue, batch)

    seeds = get_seed_list()

    for params in failed_job_params:
        iteration = params["iteration"]
        iteration_number = int(iteration)
        seed = seeds[iteration_number]
        scenario = params["scenario"]
        job_name = f"clone_{scenario}_{iteration}"
        parameters = {
            "npeople": str(n_people),
            "iteration": iteration,
            "seed": seed,
            "scenario": scenario,
        }

        job = batch.submit_job(
            jobName=job_name,
            jobQueue=job_queue,
            jobDefinition=job_definition,
            parameters=parameters,
        )
        print(
            f"Cloning iteration {iteration} for scenario {scenario}, Job ID {job['jobId']}"
        )


if __name__ == "__main__":
    Fire(main)
