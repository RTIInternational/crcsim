import json
from pathlib import Path
from typing import Dict

import fire


def combine_tests_in_params(
    params: Dict, test1: str, test2: str, how: str = "serial"
) -> Dict:
    """
    Combines two tests in the parameters dictionary and adds the combined test.
    Returns: The modified parameters dictionary
    """
    if test1 not in params["tests"]:
        raise ValueError(f"Test '{test1}' not found in parameters")
    if test2 not in params["tests"]:
        raise ValueError(f"Test '{test2}' not found in parameters")
    if how not in ["serial", "parallel"]:
        raise ValueError("how must be 'serial' or 'parallel'")

    t1 = params["tests"][test1]
    t2 = params["tests"][test2]
    combined = {}

    # Combine sensitivity and specificity for all relevant fields
    for key in [
        "sensitivity_polyp1",
        "sensitivity_polyp2",
        "sensitivity_polyp3",
        "sensitivity_cancer",
    ]:
        if how == "serial":
            combined[key] = t1[key] * t2[key]
        elif how == "parallel":
            combined[key] = 1 - (1 - t1[key]) * (1 - t2[key])

    if how == "serial":
        combined["specificity"] = t1["specificity"] * t2["specificity"]
    else:
        combined["specificity"] = 1 - (1 - t1["specificity"]) * (1 - t2["specificity"])

    # Combine cost and other fields
    combined["cost"] = t1.get("cost", 0) + t2.get("cost", 0)
    combined["proportion"] = 1.0  # Set to 1.0 to ensure it's selected
    combined["routine_start"] = min(
        t1.get("routine_start", 45), t2.get("routine_start", 45)
    )
    combined["routine_end"] = max(t1.get("routine_end", 75), t2.get("routine_end", 75))
    combined["routine_freq"] = min(t1.get("routine_freq", 1), t2.get("routine_freq", 1))
    combined["proportion_perforation"] = t1.get("proportion_perforation", 0) + t2.get(
        "proportion_perforation", 0
    )
    combined["cost_perforation"] = t1.get("cost_perforation", 0) + t2.get(
        "cost_perforation", 0
    )

    # For compliance, use the minimum for each year
    combined["compliance_rate_given_prev_compliant"] = [
        min(a, b)
        for a, b in zip(
            t1.get("compliance_rate_given_prev_compliant", [1.0] * 31),
            t2.get("compliance_rate_given_prev_compliant", [1.0] * 31),
        )
    ]
    combined["compliance_rate_given_not_prev_compliant"] = [
        min(a, b)
        for a, b in zip(
            t1.get("compliance_rate_given_not_prev_compliant", [0.0] * 31),
            t2.get("compliance_rate_given_not_prev_compliant", [0.0] * 31),
        )
    ]

    # Name for the new test
    new_test_name = f"{test1}_{test2}_{how}"
    params["tests"][new_test_name] = combined

    # Add to routine_tests if it exists
    if "routine_tests" in params:
        # Replace routine_tests with just the combined test
        params["routine_tests"] = [new_test_name]

    # Set proportion of all other tests to 0.0
    for test_name in params["tests"]:
        if test_name != new_test_name:
            params["tests"][test_name]["proportion"] = 0.0

    return params


def main(
    param_file: str,
    test_1: str,
    test_2: str,
    how: str = "serial",
    output_file: str | None = None,
) -> None:
    """
    Combine two tests in a parameters file and save the result.
    """
    param_path = Path(param_file)
    if not param_path.exists():
        raise FileNotFoundError(f"Parameters file not found: {param_file}")

    with open(param_path, "r") as f:
        params = json.load(f)

    # Combine the tests
    params = combine_tests_in_params(params, test_1, test_2, how)

    # Save the modified parameters
    output_path = Path(output_file) if output_file else param_path
    with open(output_path, "w") as f:
        json.dump(params, f, indent=2)

    new_test_name = f"{test_1}_{test_2}_{how}"
    print(f"Created combined test '{new_test_name}' in {output_path}")


if __name__ == "__main__":
    fire.Fire(main)
