# CRCsim PR Template

## Description
<!-- Provide a brief description of the changes in this PR -->

## PR Type
<!-- Mark the appropriate option with an [x] (no spaces around the x) -->
- [ ] Feature (intended to merge)
- [ ] Experiment (not intended to merge)

<!-- If this is an experiment PR, delete the following section and complete the experiment-specific sections of this template. -->
<!-- If this is a feature PR, complete the following section and delete the experiment-specific sections. -->

## Feature checklist
<!-- Make sure all items are checked before submitting the PR -->
- [ ] I have written tests for all new functionality
- [ ] All tests pass
- [ ] I have conducted a successful integration test (eg, run an experiment to test new functionality, or run the model locally without errors)
- [ ] All new functionality is documented thoroughly (informative comments, docstrings, README updates if appropriate)

## Experiment review checklist
<!-- Make sure all items are checked before submitting the PR -->
- [ ] This experiment branch has the `exp-` prefix
- [ ] This experiment uses the appropriate `crcsim` commit hash (typically, the latest commit in the `main` branch). This ensures that the experiment uses the latest version of the model.
- [ ] This experiment uses the correct baseline `parameters.json` file
    - [ ] Correct screening start and end ages for the experiment
    - [ ] Latest values of all calibrated parameters
    - [ ] All necessary tests and latest test parameters
    - [ ] Latest cost parameters
- [ ] My `prepare.py` script applies incidence rate ratio (IRR) adjustment if appropriate for this experiment
- [ ] I have run `prepare.py` and:
    - [ ] Confirmed that all scenarios necessary for this experiment were created
    - [ ] Confirmed that no extraneous scenarios are in the `scenarios/` directory (eg, uncommitted local changes from a previous experiment)
    - [ ] Spot-checked a sample of scenario parameter files to ensure that my scenario creation logic works as expected
- [ ] I have updated `crcsim/experiment/README.md` with detailed information about the experiment's goals, scenarios, and corresponding AWS objects
- [ ] I am opening this PR as a **Draft** PR

## Experiment review process
<!-- No checkboxes here, because this happens after you submit the PR -->
*All experiments must follow each step of this review process.*
1. Contributor checks all items in experiment review checklist
1. Contributor opens **Draft PR** and tags a collaborator to review
1. Reviewer conducts a thorough review, including pulling experiment branch, running `prepare.py`, and spot-checking scenarios
1. Contributor and reviewer address any issues identified during review
1. Reviewer explicitly approves PR
1. Contributor builds image and pushes to ECR, copies experiment files to S3, and runs experiment
1. Contributor analyzes experiment (eg `crcsim/experiment/summarize.py`)
1. Contributor pushes results summary, so we have documentation of detailed results (eg `crcsim/experiment/summary/summarized.xlsx`)
1. Contributor updates experiment README with a detailed summary of results
1. Contributor closes this PR with an informative comment (eg, brief summary of results)

**Note that experiment PRs are never merged into `main`!** The PR is closed, and the experiment is maintained as a separate branch. That's why we keep all experiment PRs as drafts.