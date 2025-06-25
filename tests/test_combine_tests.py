import unittest

from crcsim.combine_tests import combine_tests_in_params
from crcsim.enums import TestCombiningMethod


class TestCombineTestsInParams(unittest.TestCase):
    def setUp(self):
        self.params = {
            "tests": {
                "TestA": {
                    "sensitivity_polyp1": 0.8,
                    "sensitivity_polyp2": 0.7,
                    "sensitivity_polyp3": 0.6,
                    "sensitivity_cancer": 0.5,
                    "specificity": 0.9,
                    "cost": 100,
                    "proportion": 0.5,
                    "routine_start": 1,
                    "routine_end": 10,
                    "routine_freq": 2,
                    "proportion_perforation": 0,
                    "cost_perforation": 0,
                    "compliance_rate_given_prev_compliant": [
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                    ],
                    "compliance_rate_given_not_prev_compliant": [
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                    ],
                },
                "TestB": {
                    "sensitivity_polyp1": 0.7,
                    "sensitivity_polyp2": 0.6,
                    "sensitivity_polyp3": 0.5,
                    "sensitivity_cancer": 0.4,
                    "specificity": 0.85,
                    "cost": 150,
                    "proportion": 0.5,
                    "routine_start": 2,
                    "routine_end": 20,
                    "routine_freq": 3,
                    "proportion_perforation": 0,
                    "cost_perforation": 0,
                    "compliance_rate_given_prev_compliant": [
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                        1.0,
                    ],
                    "compliance_rate_given_not_prev_compliant": [
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                    ],
                },
            },
            "routine_tests": ["TestA", "TestB"],
        }

    def test_serial_combination(self):
        combined_params = combine_tests_in_params(
            self.params, "TestA", "TestB", how=TestCombiningMethod.SERIAL
        )
        new_test_name = "TestA_TestB_serial"
        assert new_test_name in combined_params["tests"]
        assert new_test_name in combined_params["routine_tests"]
        combined_test_data = combined_params["tests"][new_test_name]
        assert abs(combined_test_data["sensitivity_polyp1"] - 0.56) < 1e-7
        assert abs(combined_test_data["specificity"] - 0.985) < 1e-7

    def test_parallel_combination(self):
        combined_params = combine_tests_in_params(
            self.params, "TestA", "TestB", how=TestCombiningMethod.PARALLEL
        )
        new_test_name = "TestA_TestB_parallel"
        assert new_test_name in combined_params["tests"]
        assert new_test_name in combined_params["routine_tests"]
        combined_test_data = combined_params["tests"][new_test_name]
        assert abs(combined_test_data["sensitivity_polyp1"] - 0.94) < 1e-7
        assert abs(combined_test_data["specificity"] - 0.765) < 1e-7

    def test_cost_combination(self):
        combined_params = combine_tests_in_params(
            self.params, "TestA", "TestB", how=TestCombiningMethod.SERIAL
        )
        new_test_name = "TestA_TestB_serial"
        combined_test_data = combined_params["tests"][new_test_name]
        assert combined_test_data["cost"] == 250

    def test_proportion_combination(self):
        combined_params = combine_tests_in_params(
            self.params, "TestA", "TestB", how=TestCombiningMethod.SERIAL
        )
        new_test_name = "TestA_TestB_serial"
        combined_test_data = combined_params["tests"][new_test_name]
        assert combined_test_data["proportion"] == 1.0


if __name__ == "__main__":
    unittest.main()
