import json
from enum import Enum, unique
from pathlib import Path

import fire


@unique
class TestCombiningMethod(str, Enum):
    SERIAL = "serial"
    PARALLEL = "parallel"


def combine_tests_in_params(
    params: dict,
    test1: str,
    test2: str,
    how: TestCombiningMethod = TestCombiningMethod.PARALLEL,
) -> dict:
    """
    Combines two tests in the parameters dictionary and adds the combined test.
    Returns: The modified parameters dictionary
    """
    if test1 not in params["tests"]:
        raise ValueError(f"Test '{test1}' not found in parameters")
    if test2 not in params["tests"]:
        raise ValueError(f"Test '{test2}' not found in parameters")

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
        if how == TestCombiningMethod.SERIAL:
            # In serial testing, both tests must be positive for a positive result
            # Therefore, the combined sensitivity is the product of individual sensitivities
            # This reduces sensitivity (more false negatives) but increases specificity (fewer false positives)
            combined[key] = t1[key] * t2[key]
        else:
            # In parallel testing, either test being positive results in a positive result
            # The probability of a negative result is (1-sens1)*(1-sens2)
            # Therefore, the combined sensitivity is 1 - [(1-sens1)*(1-sens2)]
            # This increases sensitivity (fewer false negatives) but decreases specificity (more false positives)
            combined[key] = 1 - (1 - t1[key]) * (1 - t2[key])

    if how == TestCombiningMethod.SERIAL:
        # In serial testing, both tests must be positive for a positive result
        # For a false positive, both tests must give false positives
        # Therefore, the combined specificity is higher than either individual test
        combined["specificity"] = 1 - (1 - t1["specificity"]) * (1 - t2["specificity"])
    else:
        # In parallel testing, either test being positive results in a positive result
        # For a true negative, both tests must give true negatives
        # Therefore, the combined specificity is lower than either individual test
        combined["specificity"] = t1["specificity"] * t2["specificity"]

    # Combine cost and other fields
    combined["cost"] = t1["cost"] + t2["cost"]
    combined["proportion"] = 1.0  # Set to 1.0 to ensure it's selected
    combined["routine_start"] = min(t1["routine_start"], t2["routine_start"])
    combined["routine_end"] = max(t1["routine_end"], t2["routine_end"])
    combined["routine_freq"] = min(t1["routine_freq"], t2["routine_freq"])
    combined["proportion_perforation"] = (
        t1["proportion_perforation"] + t2["proportion_perforation"]
    )
    combined["cost_perforation"] = t1["cost_perforation"] + t2["cost_perforation"]

    # For compliance, use the minimum for each year
    combined["compliance_rate_given_prev_compliant"] = [
        min(a, b)
        for a, b in zip(
            t1["compliance_rate_given_prev_compliant"],
            t2["compliance_rate_given_prev_compliant"],
        )
    ]
    combined["compliance_rate_given_not_prev_compliant"] = [
        min(a, b)
        for a, b in zip(
            t1["compliance_rate_given_not_prev_compliant"],
            t2["compliance_rate_given_not_prev_compliant"],
        )
    ]

    # Name for the new test
    new_test_name = f"{test1}_{test2}_{how}"

    # Add the combined test to routine_tests if not already present
    if new_test_name not in params["routine_tests"]:
        params["routine_tests"].append(new_test_name)

    # Set proportion of all other tests to 0.0
    for test_name in params["tests"]:
        params["tests"][test_name]["proportion"] = 0.0

    # Now add the combined test to the tests dictionary
    params["tests"][new_test_name] = combined

    # By default, we'll assign everyone the combined test
    params["tests"][new_test_name]["proportion"] = 1.0
   

    return params


def main(
    param_file: str,
    test_1: str,
    test_2: str,
    how: str = TestCombiningMethod.PARALLEL.value,
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

    # Convert string to enum
    how_enum = TestCombiningMethod(how)

    # Combine the tests
    params = combine_tests_in_params(params, test_1, test_2, how_enum)

    # Generate default output filename if not provided
    if output_file is None:
        # Create a default output filename based on the input filename
        stem = param_path.stem
        output_file = f"{stem}_combined_{test_1}_{test_2}_{how}.json"
        output_path = param_path.parent / output_file
    else:
        output_path = Path(output_file)

    # Save the modified parameters
    with open(output_path, "w") as f:
        json.dump(params, f, indent=2)


if __name__ == "__main__":
    fire.Fire(main)
