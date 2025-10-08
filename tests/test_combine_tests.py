import itertools
import json
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pytest

from crcsim.combine_tests import combine_tests_in_params, main

# Alias TestCombiningMethod to keep pytest from treating it as a test class
from crcsim.enums import TestCombiningMethod as TstCombiningMethod


@pytest.fixture(scope="module")
def base_params():
    """
    Minimal test parameters with two simple tests for combination testing.
    """
    return {
        "routine_tests": ["TestA", "TestB"],
        "tests": {
            "TestA": {
                "proportion": 1.0,
                "routine_start": 50,
                "routine_end": 75,
                "routine_freq": 1,
                "specificity": 0.90,
                "sensitivity_polyp1": 0.10,
                "sensitivity_polyp2": 0.20,
                "sensitivity_polyp3": 0.30,
                "sensitivity_cancer": 0.80,
                "cost": 100,
                "proportion_perforation": 0.001,
                "cost_perforation": 5000,
                "compliance_rate_given_prev_compliant": [1.0, 0.9, 0.8],
                "compliance_rate_given_not_prev_compliant": [0.5, 0.4, 0.3],
            },
            "TestB": {
                "proportion": 0.0,
                "routine_start": 45,
                "routine_end": 80,
                "routine_freq": 2,
                "specificity": 0.95,
                "sensitivity_polyp1": 0.15,
                "sensitivity_polyp2": 0.25,
                "sensitivity_polyp3": 0.40,
                "sensitivity_cancer": 0.70,
                "cost": 200,
                "proportion_perforation": 0.002,
                "cost_perforation": 3000,
                "compliance_rate_given_prev_compliant": [0.95, 0.85, 0.75],
                "compliance_rate_given_not_prev_compliant": [0.4, 0.3, 0.2],
            },
        },
    }


@pytest.fixture(scope="module")
def sens_spec_params():
    """
    List of sensitivity and specificity parameter names, reused in several tests.
    """
    return [
        "sensitivity_polyp1",
        "sensitivity_polyp2",
        "sensitivity_polyp3",
        "sensitivity_cancer",
        "specificity",
    ]


@pytest.mark.parametrize(
    "case",
    [
        {
            "method": TstCombiningMethod.PARALLEL,
            "expected_sensitivity_polyp1": 0.235,  # 1 - (1-0.10)*(1-0.15)
            "expected_sensitivity_polyp2": 0.40,  # 1 - (1-0.20)*(1-0.25)
            "expected_sensitivity_polyp3": 0.58,  # 1 - (1-0.30)*(1-0.40)
            "expected_sensitivity_cancer": 0.94,  # 1 - (1-0.80)*(1-0.70)
            "expected_specificity": 0.855,  # 0.90 * 0.95
        },
        {
            "method": TstCombiningMethod.SERIAL,
            "expected_sensitivity_polyp1": 0.015,  # 0.10 * 0.15
            "expected_sensitivity_polyp2": 0.05,  # 0.20 * 0.25
            "expected_sensitivity_polyp3": 0.12,  # 0.30 * 0.40
            "expected_sensitivity_cancer": 0.56,  # 0.80 * 0.70
            "expected_specificity": 0.995,  # 1 - (1-0.90)*(1-0.95)
        },
    ],
)
def test_sens_spec_combinations(base_params, case, sens_spec_params):
    """
    Test parallel and serial combinations with hand-calculated values.

    Parallel: either test being positive results in a positive result.
    - Combined sensitivity = 1 - (1 - sens1) * (1 - sens2)
    - Combined specificity = spec1 * spec2

    Serial: both tests must be positive for a positive result.
    - Combined sensitivity = sens1 * sens2
    - Combined specificity = 1 - (1 - spec1) * (1 - spec2)
    """
    params = deepcopy(base_params)
    result = combine_tests_in_params(params, "TestA", "TestB", case["method"])

    combined_test = result["tests"][f"TestA_TestB_{case['method'].value}"]

    for param in sens_spec_params:
        assert combined_test[param] == pytest.approx(case[f"expected_{param}"])


@pytest.mark.parametrize(
    "method", [TstCombiningMethod.PARALLEL, TstCombiningMethod.SERIAL]
)
def test_sens_spec_monotonicity(base_params, method, sens_spec_params):
    """
    Test that combined sensitivities and specificities follow expected monotonicity rules.

    Parallel:
    - Sensitivity: 1 - (1 - s1) * (1 - s2) should be >= max(s1, s2)
    - Specificity: spec1 * spec2 should be <= min(spec1, spec2)

    Serial:
    - Sensitivity: s1 * s2 should be <= min(s1, s2)
    - Specificity: 1 - (1 - spec1) * (1 - spec2) should be >= max(spec1, spec2)
    """
    params = deepcopy(base_params)

    # Test combinations across a range of sensitivity and specificity values
    test_values = np.arange(0.01, 1.0, 0.01)

    for val1, val2 in itertools.product(test_values, repeat=2):
        for param in sens_spec_params:
            params["tests"]["TestA"][param] = val1
            params["tests"]["TestB"][param] = val2

        result = combine_tests_in_params(params, "TestA", "TestB", method)

        combined_test = result["tests"][f"TestA_TestB_{method.value}"]

        for param in sens_spec_params:
            combined_value = combined_test[param]
            # Combined value should be <= min for specificity in parallel & sensitivity in serial,
            # or >= max for specificity in serial & sensitivity in parallel (see docstring)
            if (
                (param == "specificity") and (method == TstCombiningMethod.PARALLEL)
            ) or (("sensitivity" in param) and (method == TstCombiningMethod.SERIAL)):
                assert combined_value <= min(val1, val2)
            else:
                assert combined_value >= max(val1, val2)


@pytest.mark.parametrize(
    "case",
    [
        {
            "method": TstCombiningMethod.PARALLEL,
            "value": 1.0,
            "description": "perfect test in parallel combination yields perfect sensitivity",
        },
        {
            "method": TstCombiningMethod.SERIAL,
            "value": 0.0,
            "description": "useless test in serial combination yields zero sensitivity",
        },
    ],
)
def test_sens_spec_boundary_cases(base_params, case, sens_spec_params):
    """
    Test boundary cases for sensitivity combinations.

    - Perfect test (sensitivity=1.0) in parallel → perfect sensitivity
    - Useless test (sensitivity=0.0) in serial → zero sensitivity
    """
    params = deepcopy(base_params)

    for param in sens_spec_params:
        params["tests"]["TestA"][param] = case["value"]

    result = combine_tests_in_params(params, "TestA", "TestB", case["method"])
    combined_test = result["tests"][f"TestA_TestB_{case['method'].value}"]

    for param in sens_spec_params:
        if "sensitivity" in param:
            assert combined_test[param] == case["value"], case["description"]


@pytest.mark.parametrize(
    "method", [TstCombiningMethod.PARALLEL, TstCombiningMethod.SERIAL]
)
def test_parameter_additions(base_params, method):
    """
    Test that the combined test is properly added to the parameters dictionary.
    """
    params = deepcopy(base_params)
    result = combine_tests_in_params(params, "TestA", "TestB", method)

    test_name = f"TestA_TestB_{method.value}"

    # Combined test exists in tests dict
    assert test_name in result["tests"]

    # Combined test is added to routine_tests list
    assert test_name in result["routine_tests"]

    # Combined test not assigned to anyone by default
    assert result["tests"][test_name]["proportion"] == 0.0

    # Other test proportions are unchanged
    assert (
        result["tests"]["TestA"]["proportion"]
        == base_params["tests"]["TestA"]["proportion"]
    )
    assert (
        result["tests"]["TestB"]["proportion"]
        == base_params["tests"]["TestB"]["proportion"]
    )

    # All base tests params exist for combined test
    for param in base_params["tests"]["TestA"]:
        assert param in result["tests"][test_name]


@pytest.mark.parametrize(
    "method", [TstCombiningMethod.PARALLEL, TstCombiningMethod.SERIAL]
)
def test_other_combinations(base_params, method):
    """
    Tests logic of combinations other than sensitivity and specificity.

      - Combined costs are the sum of individual costs.
      - Combined perforation probability is the sum of individual probabilities.
      - Combined age range takes min start and max end.
      - Combined conditional compliance rates use element-wise minimum.
    """
    params = deepcopy(base_params)
    result = combine_tests_in_params(params, "TestA", "TestB", method)

    combined_test = result["tests"][f"TestA_TestB_{method.value}"]

    # Combined costs are the sum of individual costs
    assert (
        combined_test["cost"]
        == params["tests"]["TestA"]["cost"] + params["tests"]["TestB"]["cost"]
    )
    assert (
        combined_test["cost_perforation"]
        == params["tests"]["TestA"]["cost_perforation"]
        + params["tests"]["TestB"]["cost_perforation"]
    )

    # Perforation probability is the sum of individual probabilities
    assert (
        combined_test["proportion_perforation"]
        == params["tests"]["TestA"]["proportion_perforation"]
        + params["tests"]["TestB"]["proportion_perforation"]
    )

    # Start age should be min of base tests
    assert combined_test["routine_start"] == min(
        params["tests"]["TestA"]["routine_start"],
        params["tests"]["TestB"]["routine_start"],
    )

    # End age should be max of base tests
    assert combined_test["routine_end"] == max(
        params["tests"]["TestA"]["routine_end"], params["tests"]["TestB"]["routine_end"]
    )

    # Test frequency should be min of base tests
    assert combined_test["routine_freq"] == min(
        params["tests"]["TestA"]["routine_freq"],
        params["tests"]["TestB"]["routine_freq"],
    )

    # Conditional compliance rates use element-wise minimum.
    conditions = ["prev_compliant", "not_prev_compliant"]
    for condition in conditions:
        assert (
            combined_test[f"compliance_rate_given_{condition}"]
            == np.minimum(
                params["tests"]["TestA"][f"compliance_rate_given_{condition}"],
                params["tests"]["TestB"][f"compliance_rate_given_{condition}"],
            ).tolist()
        )


@pytest.mark.parametrize(
    "method", [TstCombiningMethod.PARALLEL, TstCombiningMethod.SERIAL]
)
def test_missing_test_raises_error(base_params, method):
    """
    Test that ValueError is raised when one of the passed tests doesn't exist.
    """
    with pytest.raises(
        ValueError, match="Test 'NonexistentTest' not found in parameters"
    ):
        combine_tests_in_params(base_params, "NonexistentTest", "TestB", method)

    with pytest.raises(
        ValueError, match="Test 'NonexistentTest' not found in parameters"
    ):
        combine_tests_in_params(base_params, "TestA", "NonexistentTest", method)


def test_param_file_not_found():
    """
    Test that main() raises FileNotFoundError when parameter file doesn't exist.
    """
    with pytest.raises(FileNotFoundError, match="Parameters file not found"):
        main("nonexistent_file.json", "TestA", "TestB")


def test_output_file(base_params):
    """
    Test that main() creates an output file with correct name.
    """
    with TemporaryDirectory() as tmp_dir:
        # Dump base params into input parameter file
        input_path = Path(tmp_dir) / "parameters.json"
        with open(input_path, "w") as f:
            json.dump(base_params, f)

        # Default output file: run main without specifying name
        # Check that output file exists and contains correct combined test
        main(str(input_path), "TestA", "TestB", "parallel")

        expected_output = (
            Path(tmp_dir) / "parameters_combined_TestA_TestB_parallel.json"
        )
        assert expected_output.exists()

        with open(expected_output, "r") as f:
            output_params = json.load(f)
            assert "TestA_TestB_parallel" in output_params["tests"]

        # Custom output filename, same checks as previous
        output_path = Path(tmp_dir) / "custom_output.json"
        main(str(input_path), "TestA", "TestB", "serial", str(output_path))

        assert output_path.exists()

        with open(output_path, "r") as f:
            output_params = json.load(f)
            assert "TestA_TestB_serial" in output_params["tests"]


def test_main_misuse(base_params):
    """
    Test that main() raises an error when invalid input file, output file, or combination
    method is used.
    """
    with TemporaryDirectory() as tmp_dir:
        input_path = Path(tmp_dir) / "parameters.json"
        with open(input_path, "w") as f:
            json.dump(base_params, f)

        # Invalid combination method
        with pytest.raises(ValueError, match="is not a valid TestCombiningMethod"):
            main(str(input_path), "TestA", "TestB", "Parallel")  # Case-sensitive

        # Invalid output path - directory doesn't exist
        # (Add this dir to your system if you want the test to fail!)
        invalid_output_path = Path(tmp_dir) / "super_fake_dir" / "output.json"
        with pytest.raises(FileNotFoundError):
            main(
                str(input_path), "TestA", "TestB", "parallel", str(invalid_output_path)
            )

        # Invalid input path - file doesn't exist
        nonexistent_input_path = Path(tmp_dir) / "there_is_no.json"
        with pytest.raises(FileNotFoundError, match="Parameters file not found"):
            main(str(nonexistent_input_path), "TestA", "TestB", "parallel")
