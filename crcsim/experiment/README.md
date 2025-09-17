# Experiment: Test 100% and 80% Diagnostic Compliance for FQHCs

This branch tests 80% and 100% compliance for FQHCs 1-8 with differing screening uptake and low and extra low costs for Stage III and Stage IV inital treatment.

## Results

The results for the 100% diagnostic compliance match a previous run from April 2025. The results differ between 80% and 100% compliance.

## Experiment Workflow

`crcsim` experiments are managed as branches. We never merge experiment branches into main. Instead, each experiment branch has all relevant files in the `crcsim/experiment` directory, and is kept as a separate branch for historical record.

To create a new experiment, follow these steps:

1. **Make a branch with the `exp-*` prefix**. Sometimes, if a new experiment is tightly coupled to an existing experiment, it may make more sense to branch off another experiment branch. But in general, branching from this template should be the default.
1. Edit files as described below to define the new experiment.
1. Update this README to describe the experiment in detail.
1. Open a **Draft** pull request and follow the steps in the pull request template. A few specific callouts:
    - Don't run the experiment until the pull request reviewer has approved.
    - Make sure to revisit the README after you've run the experiment and add a detailed summary of results.
    - **Don't merge the experiment branch into `main`**. Instead, close the Draft PR with an informative comment once the experiment has been completed.

## Scenarios

`crcsim` experiments consist of a set of scenarios. Each scenario is defined by its own parameter file. The scenarios are chosen to test a certain hypothesis.

For example, this template includes a few basic scenarios: 0%, 50% and 100% screening compliance for Colonoscopies and FIT tests. Production experiments typically include more complex scenario sets to test real-world hypotheses.

Typically, an experiment's unique logic is defined by the `prepare.py` script. This script transforms a set of base parameters to create each scenario.

The rest of the steps - running the simulation with `simulate.py` and analyzing it with `summarize.py` - are mostly consistent between experiments. However, those files do need a few tweaks too, as described in the next section.

## Defining new experiments

To use this code as the basis for a new experiment, you should edit the following:

- [./prepare.py](./prepare.py) - Change the scenarios to run and the associated parameter transformations.
- [./simulate.py](./simulate.py) - Change the AWS batch objects and parameters.
- [./run_iteration.sh](./run_iteration.sh) - Change the s3 bucket name, or if the experiment is substantially different, the series of commands each run entails.
- [./summarize.py](./summarize.py) - You may want to change the derived variables that are added to the model results.
- [./parameters.json](./parameters.json) - You may want to edit the base parameter values.

## Running the experiment on AWS

### Test runs

If you want to conduct a test run of the experiment, consider reducing the number of iterations in Step 3 and/or using a smaller population size in Step 5. You could also comment out some FQHCs in the `initial_compliance` dict in the `create_scenarios` function in `prepare.py`.
### 1. Setup

1. Clone this repo to your local machine
1. Set your working directory to `./simulator/crcsim/experiment`
1. Create and activate a Python 3.11 virtual environment
1. Install dependencies with `pip install -r requirements.txt`

### 2. (Optional) Build and Push Image

Unless you've made changes to files that will affect simulation runs, this step is not necessary, since the `crcsim` image has already been uploaded to ECR. If you've changed anything in `run_iteration.sh`, `requirements.txt`, etc., you will need to rebuild and push the image.

Run `bash deploy_to_aws.sh` to run a series of commands which build the image locally from the Dockerfile in this repo and push it to ECR.

### 3. Prepare the Experiment Files

The script `prepare.py` prepares the `scenarios/` directory, the parameter files that define each scenario, and the `seeds.txt` file that defines the seeds used for multiple iterations of each scenario. 

Running this script with all default arguments will replicate the seed and number of iterations of this experiment's original run. You can vary the seed by editing the script, and you can vary the number of iterations with a command line argument, e.g. `prepare.py --n=10`. 

### 4. Upload the Experiment Files to S3

The subdirectories and files in `scenarios/` must be uploaded to AWS S3 for the Docker containers running Batch jobs to access them. *(Note: it would be possible to avoid this step because `scenarios/` is in the build context, but we chose to rely on S3 so the Docker image does not have to be rebuilt every time `prepare.py` is run.)*

To upload the files to S3, run
```
aws s3 cp ./scenarios s3://crcsim-exp-fqhc-diagnostic-compliance-comparison/scenarios --recursive
```
*(Another note: this manual step is necessary because `boto3` does not include functionality to upload a directory to S3 recursively. Future experiments could improve this workflow by writing a function to upload the directory recursively in `prepare.py`. Or submit a patch to resolve https://github.com/boto/boto3/issues/358)*

### 5. Launch the Jobs

The script `simulate.py` uses boto3 to launch jobs in AWS Batch. It relies on the structure of `scenarios/` generated by `prepare.py` to determine the jobs to launch and their parameters.

By default, each run uses a population size of 100,000 as with other experiments/batches. You can us the `n_people` argument to vary this parameter. For example, launch the jobs with a population size of 1,000 with the command `python simulate.py --n_people=1000`.

After launching, you can view job status and CloudWatch logs for individual jobs in the Batch console.

### 6. Check for Errors

Check the Batch console to see if any of the jobs failed. It is normal for a handful to fail due to Spot availability. Check the logs if you're concerned. If more than a few jobs failed, you may have a more serious issue. Use the CloudWatch logs to diagnose.

If you have only a few failed jobs and the reason looks innocuous, the easiest solution is to rerun the jobs manually via the Batch console.

### 6. Analyze the Results

Once all jobs have completed, run `summarize.py` to analyze the combined results of the model runs. This script uses pandas and s3fs to read and write files directly from S3 without saving them to your local machine. Like `simulate.py`, `summarize.py` relies on the structure of `scenarios/` to determine the files it fetches from S3.

This step generates `summary/` and its contents:
- `combined.csv` has one row per model run
- `summarized.xlsx` includes summary statistics for each scenario. Scenarios are separated into three sheets, one for each sensitivity test.

## AWS Architecture

The architecture relies on four AWS services - Batch, CloudWatch, Elastic Container Registry (ECR), and S3. The role of each service is as follows.

- Batch: high-level interface to launch Elastic Container Service (ECS) jobs
- CloudWatch: logging service to view logs for Batch jobs
- ECR: store Docker container used to run jobs
- S3: store output files generated by jobs 

Most of the AWS architecture was built via the AWS Console. As such, there is not a script available to replicate the setup steps. This section outlines those steps.

**Important:** all AWS resources should be tagged following CDS protocols. For this project, all resources were tagged as follows.

- project-name: crcsim
- project-number: 0216648.001.001
- responsible-person: apreiss@rti.org

### S3

We used the S3 console to create the `crcsim-exp-fqhc-diagnostic-compliance-comparison` bucket to store output files generated by simulation jobs.

### IAM

We used the IAM console to create the `crcsim-s3-access` IAM role. This IAM role has the `AmazonS3FullAccess` policy attached, which allows a service with this role to read and write to S3. 

### Batch

We created the following Batch objects:

- Compute environment: `crcsim` using the FARGATE_SPOT provisioning model
- Job queue: `crcsim`
- Job definition: `crcsim`. Executes the following command in the `crcsim:latest` image. 
```
["./run_iteration.sh","Ref::npeople","Ref::iteration","Ref::seed","Ref::scenario"]
```
- Important job definition properties:
    - The `Ref::<name>` placeholders in the command define parameters. We vary these parameters across jobs.
    - Job role ARN allows us to add the `crcsim-s3-access` IAM role which gives jobs access to S3.
    - Enabling tag propagation passes the job's tags on to the underlying ECS resources. This is important to ensure costs are billed to the project.

Note that most of these resources were named `crcsim` rather than something like `crcsim-exp-template`. We expect that we will be able to use the same objects across experiments, since their structure is not specific to this experiment.
### CloudWatch

AWS Batch automatically sends log streams from jobs to AWS CloudWatch. Some logging info is viewable from within Batch by opening a job. However, the added detail of the complete logs may be useful, particularly for debugging. To view Batch logs in CloudWatch:
1. Navigate to the [CloudWatch console](https://console.aws.amazon.com/cloudwatch/)
1. Open `Log groups` and the `/aws/batch/job` log group
1. Find the log stream for the job of interest.

### ECR

Pushing the Docker image to ECR is the only step of the architecture setup that was NOT completed via the AWS Console. The script `deploy_to_aws.sh` contains all commands necessary to build the `crcsim` Docker image and upload it to ECR.
