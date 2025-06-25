import pytest

from crcsim.combine_tests import combine_tests_in_params
from crcsim.enums import TestCombiningMethod


class TestCombineTests:
    """Focused test suite for essential test combination functionality."""

    @pytest.fixture
    def sample_params(self):
        """Simple test parameters for testing."""
        return {
            "tests": {
                "test_a": {
                    "sensitivity_polyp1": 0.8,
                    "sensitivity_polyp2": 0.7,
                    "sensitivity_polyp3": 0.6,
                    "sensitivity_cancer": 0.9,
                    "specificity": 0.95,
                    "cost": 100,
                    "proportion": 0.5,
                    "routine_start": 50,
                    "routine_end": 75,
                    "routine_freq": 10,
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
                "test_b": {
                    "sensitivity_polyp1": 0.9,
                    "sensitivity_polyp2": 0.8,
                    "sensitivity_polyp3": 0.7,
                    "sensitivity_cancer": 0.85,
                    "specificity": 0.9,
                    "cost": 150,
                    "proportion": 0.5,
                    "routine_start": 45,
                    "routine_end": 80,
                    "routine_freq": 5,
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
            "routine_tests": ["test_a", "test_b"],
        }

    def test_parallel_sensitivity_and_specificity(self, sample_params):
        """Test parallel combination calculations for sensitivity and specificity."""
        result = combine_tests_in_params(
            sample_params, "test_a", "test_b", TestCombiningMethod.PARALLEL
        )

        combined = result["tests"]["test_a_test_b_parallel"]

        # Parallel sensitivity: 1 - (1-sens1)*(1-sens2)
        assert combined["sensitivity_polyp1"] == pytest.approx(
            0.98
        )  # 1-(1-0.8)*(1-0.9)
        assert combined["sensitivity_cancer"] == pytest.approx(
            0.985
        )  # 1-(1-0.9)*(1-0.85)

        # Parallel specificity: spec1 * spec2
        assert combined["specificity"] == pytest.approx(0.855)  # 0.95 * 0.9

    def test_serial_sensitivity_and_specificity(self, sample_params):
        """Test serial combination calculations for sensitivity and specificity."""
        result = combine_tests_in_params(
            sample_params, "test_a", "test_b", TestCombiningMethod.SERIAL
        )

        combined = result["tests"]["test_a_test_b_serial"]

        # Serial sensitivity: sens1 * sens2
        assert combined["sensitivity_polyp1"] == pytest.approx(0.72)  # 0.8 * 0.9
        assert combined["sensitivity_cancer"] == pytest.approx(0.765)  # 0.9 * 0.85

        # Serial specificity: 1 - (1-spec1)*(1-spec2)
        assert combined["specificity"] == pytest.approx(0.995)  # 1-(1-0.95)*(1-0.9)

    def test_cost_calculations(self, sample_params):
        """Test that costs are properly combined."""
        result = combine_tests_in_params(
            sample_params, "test_a", "test_b", TestCombiningMethod.PARALLEL
        )

        combined = result["tests"]["test_a_test_b_parallel"]

        # Costs should be additive
        assert combined["cost"] == 250  # 100 + 150

    def test_combined_test_setup(self, sample_params):
        """Test that the combined test is properly configured."""
        result = combine_tests_in_params(
            sample_params, "test_a", "test_b", TestCombiningMethod.PARALLEL
        )

        # Combined test should be set to 100% proportion
        assert result["tests"]["test_a_test_b_parallel"]["proportion"] == 1.0

        # Original tests should be set to 0% proportion
        assert result["tests"]["test_a"]["proportion"] == 0.0
        assert result["tests"]["test_b"]["proportion"] == 0.0

        # Combined test should be in routine_tests
        assert "test_a_test_b_parallel" in result["routine_tests"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
