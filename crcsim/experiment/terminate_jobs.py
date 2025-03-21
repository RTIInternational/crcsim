import boto3


def terminate_all_jobs():
    batch = boto3.client("batch")

    # Get all jobs in RUNNING or SUBMITTED state
    response = batch.list_jobs(
        jobQueue="crcsim", jobStatus="RUNNING"  # your job queue name
    )
    running_jobs = response["jobSummaryList"]

    response = batch.list_jobs(jobQueue="crcsim", jobStatus="RUNNABLE")
    runnable_jobs = response["jobSummaryList"]

    response = batch.list_jobs(jobQueue="crcsim", jobStatus="SUBMITTED")
    submitted_jobs = response["jobSummaryList"]

    # Terminate each job
    for job in running_jobs + submitted_jobs + runnable_jobs:
        job_id = job["jobId"]
        print(f"Terminating job {job_id}")
        batch.terminate_job(jobId=job_id, reason="Manual termination")


if __name__ == "__main__":
    terminate_all_jobs()
