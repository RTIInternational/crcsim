from itertools import chain
from pathlib import Path

import pandas as pd
import s3fs  # noqa: F401

S3_BUCKET_NAME = "crcsim-exp-consistent-lifespans"


def main() -> None:
    summary_dir = Path("./summary")
    summary_dir.mkdir(exist_ok=True, parents=True)
    combined = combine_run_results()
    combined.to_csv(summary_dir / "combined.csv", index=False)
    df = add_derived_variables(combined)
    summary, summary_subset = summarize_results(df)

    with pd.ExcelWriter(summary_dir / "summarized.xlsx", engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="All Columns", index=False)
        summary_subset.to_excel(writer, sheet_name="Select Columns", index=False)


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


def get_n_iterations() -> int:
    """
    Gets the length of ./scenarios/seeds.txt
    """
    with open(Path("./scenarios/seeds.txt")) as f:
        seeds = f.read().splitlines()
    return len(seeds)


def combine_run_results() -> pd.DataFrame:
    """
    Gather the final analysis results of every run and concatenate them into a
    single data frame.
    """

    scenarios = get_scenario_list()
    n_iterations = get_n_iterations()

    dfs = []

    for scenario in scenarios:
        for iteration in range(n_iterations):
            iteration_name = f"{iteration:03}"

            print(f"Fetching results for {scenario}, iteration {iteration_name}")

            df = pd.read_csv(
                f"s3://{S3_BUCKET_NAME}/scenarios/{scenario}/results_{iteration_name}.csv"
            )
            df["scenario"] = scenario
            df["iteration"] = iteration

            dfs.append(df)

    if len(dfs) == 0:
        raise RuntimeError("No simulation results files were found")

    return pd.concat(
        dfs, axis="index"
    ).copy()  # copy to address pandas fragmentation warning


def add_derived_variables(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add derived variables to the data frame.
    """

    df["cost_treatment"] = (
        df["cost_treatment_initial"]
        + df["cost_treatment_ongoing"]
        + df["cost_treatment_terminal"]
    )

    df["discounted_cost_treatment"] = (
        df["discounted_cost_treatment_initial"]
        + df["discounted_cost_treatment_ongoing"]
        + df["discounted_cost_treatment_terminal"]
    )

    df["cost_total"] = (
        df["cost_routine"]
        + df["cost_diagnostic"]
        + df["cost_surveillance"]
        + df["cost_treatment"]
    )

    df["discounted_cost_total"] = (
        df["discounted_cost_routine"]
        + df["discounted_cost_diagnostic"]
        + df["discounted_cost_surveillance"]
        + df["discounted_cost_treatment"]
    )

    return df


def summarize_results(df: pd.DataFrame) -> pd.DataFrame:
    """ Compute the mean and standard deviation of every analysis variable, by scenario. """
    groups = df.groupby("scenario")
    means = groups.mean()
    stds = groups.std()
    means.columns = [f"{c}_mean" for c in means.columns]
    stds.columns = [f"{c}_std" for c in stds.columns]
    interleaved_columns = chain.from_iterable(zip(means.columns, stds.columns))
    summary = pd.concat([means, stds], axis="columns")[interleaved_columns]
    summary = summary.reset_index()

    # Create a second sheet with select columns
    select_columns = ["scenario", 
        "Colonoscopy_performed_diagnostic_per_1k_40yo_mean", 
        "Colonoscopy_performed_surveillance_per_1k_40yo_mean",
        "FIT_performed_routine_per_1k_40yo_mean", 
        "clin_crc_per_1k_40yo_mean",
        "deadcrc_per_1k_40yo_mean", 
        "lifeobs_if_unscreened_undiagnosed_at_40_mean",
        "discounted_cost_routine_mean",
        "discounted_cost_diagnostic_mean",
        "discounted_cost_surveillance_mean",
        "discounted_cost_treatment_initial_mean",
        "discounted_cost_treatment_ongoing_mean",
        "discounted_cost_treatment_terminal_mean",
        "cost_routine_mean",
        "cost_diagnostic_mean",
        "cost_surveillance_mean",
        "cost_treatment_initial_mean",
        "cost_treatment_ongoing_mean",
        "cost_treatment_terminal_mean",
        "discounted_cost_routine_per_1k_40yo_mean",
        "discounted_cost_diagnostic_per_1k_40yo_mean",
        "discounted_cost_surveillance_per_1k_40yo_mean",
        "discounted_cost_treatment_initial_per_1k_40yo_mean",
        "discounted_cost_treatment_ongoing_per_1k_40yo_mean",
        "discounted_cost_treatment_terminal_per_1k_40yo_mean",
        "cost_routine_per_1k_40yo_mean",
        "cost_diagnostic_per_1k_40yo_mean",
        "cost_surveillance_per_1k_40yo_mean",
        "cost_treatment_initial_per_1k_40yo_mean",
        "cost_treatment_ongoing_per_1k_40yo_mean",
        "cost_treatment_terminal_per_1k_40yo_mean",
        "discounted_lifeobs_if_unscreened_undiagnosed_at_40_mean"]
    summary_subset = summary[select_columns]

    return summary, summary_subset


if __name__ == "__main__":
    main()
