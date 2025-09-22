from copy import deepcopy

import pytest
from conftest import BasePersonForTests

# Alias TestingRole to keep pytest from treating it as a test class
from crcsim.enums import PersonTestingMessage, PersonTestingState
from crcsim.enums import TestingRole as TstingRole
from crcsim.parameters import StepFunction, load_params


@pytest.fixture(scope="module")
def params():
    """
    Default parameters. Some tests use these as-is; others override some values
    to test specific scenarios. These are also the current values in parameters.json,
    but we specify them here so that any future changes to parameters.json don't
    affect these tests.
    """
    p = load_params("parameters.json")

    # All test scenarios use FIT and Colonoscopy with testing from age 50 to 75.
    p["routine_tests"] = ["FIT", "Colonoscopy"]
    p["diagnostic_test"] = "Colonoscopy"
    p["surveillance_test"] = "Colonoscopy"
    p["routine_testing_year"] = list(range(50, 76))
    p["tests"]["FIT"]["routine_start"] = 50
    p["tests"]["FIT"]["routine_end"] = 75
    p["tests"]["Colonoscopy"]["routine_start"] = 50
    p["tests"]["Colonoscopy"]["routine_end"] = 75

    # Start from perfect compliance so we can control when noncompliance occurs
    p["initial_compliance_rate"] = 1.0
    p["tests"]["FIT"]["compliance_rate_given_prev_compliant"] = [1.0] * 26
    p["tests"]["Colonoscopy"]["compliance_rate_given_prev_compliant"] = [1.0] * 26
    p["never_compliant_rate"] = 0.0
    p["diagnostic_compliance_rate"] = 1.0
    p["surveillance_compliance_rate"] = 1.0

    # We don't want any false positives for these tests, because we rely on each
    # person completing a normal course of routine testing without any diagnostic
    # or surveillance testing. In the PersonForTests class, we ensure that the person
    # never has CRC; here we ensure that no routine test returns a false positive
    # and causes a diagnostic test.
    p["tests"]["FIT"]["specificity"] = 1
    p["tests"]["Colonoscopy"]["specificity"] = 1

    # Most of the tests apply to separate routine and diagnostic tests (ie, not
    # Colonoscopy). So we assign everyone FIT in base params, and override in some tests.
    p["tests"]["Colonoscopy"]["proportion"] = 0.0
    p["tests"]["FIT"]["proportion"] = 1.0

    return p


class PersonForTests(BasePersonForTests):
    """
    Specialized PersonForTests for diagnostic noncompliance propagation testing.

    This class inherits from BasePersonForTests, which means the person never
    gets lesions. Therefore, we manually trigger state transitions to test the
    compliance logic without needing actual disease progression. This approach
    lets us isolate and test the noncompliance propagation mechanism.
    """

    def force_diagnostic_noncompliance(self):
        """
        Force the person to be noncompliant with the next diagnostic test.

        This mocks the compliance check to return False specifically for
        diagnostic tests (not routine-is-diagnostic), allowing us to test
        the propagation mechanism without relying on random compliance outcomes.
        """
        original_is_compliant = self.is_compliant

        def mock_is_compliant(test):
            if (
                self.testing_state == PersonTestingState.DIAGNOSTIC
                and not self.routine_is_diagnostic
            ):
                return False
            return original_is_compliant(test)

        self.is_compliant = mock_is_compliant

    def trigger_positive_screen(self):
        """
        Simulate a positive routine test that triggers diagnostic testing.

        Since BasePersonForTests never gets lesions, this simulates what would
        happen if a routine test had a false positive result, triggering the
        ROUTINE → DIAGNOSTIC state transition.
        """
        self.handle_testing_message(PersonTestingMessage.SCREEN_POSITIVE)

    def trigger_symptomatic_lesion(self):
        """
        Simulate becoming symptomatic, which triggers diagnostic testing.

        This simulates the scenario where someone develops symptoms (which would
        normally be caused by a lesion's timeout to exhibit symptoms), bypassing
        the normal compliance checks for diagnostic tests.
        """
        self.handle_testing_message(PersonTestingMessage.SYMPTOMATIC)

    def transition_diagnostic_to_routine(self):
        """
        Transition the person from the DIAGNOSTIC testing state back to ROUTINE.

        Accomplishing that by passing the NOT_COMPLIANT message (even if the person was compliant)
        is hacky, but it doesn't affect our testing logic, because that testing message only does
        two things:

        1. Sets the testing state back to ROUTINE
        2. Sets routine_is_diagnostic to False

        I.e., it does not record noncompliance anywhere.

        The other path from DIAGNOSTIC to ROUTINE is through NEGATIVE, SKIP_TESTING, and
        RETURN_TO_ROUTINE. That just accomplishes the same two things, plus additional
        complication from scheduling and disabling a timeout event. Plus it's more verbose.
        So here, we just go the simple path even though it may seem counterintuitive.
        """
        self.handle_testing_message(PersonTestingMessage.NOT_COMPLIANT)

        assert self.testing_state == PersonTestingState.ROUTINE


@pytest.mark.parametrize(
    "case",
    [
        # When feature is disabled, diagnostic noncompliance should not affect routine tests
        {
            "name": "feature_disabled",
            "propagate_diagnostic_noncompliance": False,
            "is_diagnostic_noncompliant": False,
        },
        # When feature is enabled and person is noncompliant with diagnostic, routine tests should
        # be affected
        {
            "name": "feature_enabled_noncompliant",
            "propagate_diagnostic_noncompliance": True,
            "is_diagnostic_noncompliant": True,
        },
        # When feature is enabled but person is compliant with diagnostic, routine tests should not
        # be affected
        {
            "name": "feature_enabled_compliant",
            "propagate_diagnostic_noncompliance": True,
            "is_diagnostic_noncompliant": False,
        },
    ],
)
def test_diagnostic_noncompliance_propagation(params, case):
    """
    Test basic propagation behavior of diagnostic noncompliance to routine tests.

    This test simulates the core workflow:
    1. Person starts in ROUTINE testing state
    2. Gets positive screen → DIAGNOSTIC state
    3. Takes diagnostic test (compliant or noncompliant based on test case)
    4. Returns to ROUTINE state
    5. Tests whether future routine compliance is affected by diagnostic noncompliance
    """
    params_ = deepcopy(params)
    params_["propagate_diagnostic_noncompliance"] = case[
        "propagate_diagnostic_noncompliance"
    ]

    person = PersonForTests(params=params_)

    if case["is_diagnostic_noncompliant"]:
        # Force noncompliance with diagnostic test to test propagation
        person.force_diagnostic_noncompliance()

    person.start()
    # Person always starts in ROUTINE testing state
    assert person.testing_state == PersonTestingState.ROUTINE

    # Trigger positive routine screen and transition to DIAGNOSTIC testing state
    person.trigger_positive_screen()
    assert person.testing_state == PersonTestingState.DIAGNOSTIC

    # Compliance with diagnostic test is 100% if not forced noncompliant
    # (enforced in params fixture) and is 0% if forced noncompliant.
    person.test_diagnostic()

    # Assert diagnostic_noncompliance flag was set correctly
    if case["is_diagnostic_noncompliant"]:
        assert person.diagnostic_noncompliant
    else:
        assert not person.diagnostic_noncompliant

    # Transition the person back to the ROUTINE testing state
    person.transition_diagnostic_to_routine()

    # Check if routine test compliance is affected by diagnostic noncompliance
    routine_compliant = person.is_compliant(person.routine_test)

    if case["is_diagnostic_noncompliant"]:
        assert not routine_compliant, (
            f"Expected routine noncompliance in {case['name']}"
        )
    else:
        assert routine_compliant, f"Expected routine compliance in {case['name']}"


def test_symptomatic_unaffected(params):
    """
    Test that diagnostic tests caused by lesions becoming symptomatic are unaffected by
    previous diagnostic noncompliance.

    This test verifies that the propagation feature only affects routine tests, not
    diagnostic tests triggered by symptoms, and not any surveillance tests that follow a
    positive, symptomatic diagnostic test.

    The workflow:
    1. Person becomes noncompliant with initial diagnostic test → sets diagnostic_noncompliant flag
    2. Returns to routine testing → routine tests are affected by propagation
    3. Becomes symptomatic → triggers new diagnostic test
    4. Symptomatic diagnostic test should be unaffected by the diagnostic noncompliance flag
    5. Diagnostic test finds cancer → DIAGNOSTIC → SURVEILLANCE state transition
    6. Surveillance compliance should be unaffected by the diagnostic noncompliance flag
    """
    params_ = deepcopy(params)
    params_["propagate_diagnostic_noncompliance"] = True
    params_["diagnostic_compliance_rate"] = 0.0

    person = PersonForTests(params=params_)
    person.start()

    # First diagnostic test - simulate positive screen followed by noncompliant diagnostic
    person.trigger_positive_screen()
    assert person.testing_state == PersonTestingState.DIAGNOSTIC
    person.test_diagnostic()
    assert person.diagnostic_noncompliant
    person.transition_diagnostic_to_routine()

    # Verify routine tests are affected by propagation
    assert not person.is_compliant(person.routine_test)

    # Trigger diagnostic test caused by becoming symptomatic, which should bypass
    # compliance checks entirely.
    person.trigger_symptomatic_lesion()
    assert person.testing_state == PersonTestingState.DIAGNOSTIC
    # Check that a diagnostic test was added to the person's output record.
    person.test_diagnostic(symptomatic=True)
    last_output = person.out.rows[-1]
    assert last_output["record_type"] == "test_performed"
    assert last_output["role"] == TstingRole.DIAGNOSTIC

    # Simulate positive diagnostic result (found cancer) leading to surveillance.
    person.handle_testing_message(PersonTestingMessage.POSITIVE_CANCER)
    assert person.testing_state == PersonTestingState.SURVEILLANCE

    # Surveillance compliance (set to 100% in params fixture) should be unaffected
    # by diagnostic noncompliance.
    assert person.is_compliant(person.surveillance_test)


def test_routine_is_diagnostic_unaffected(params):
    """
    Test that when a person's routine test and diagnostic test are the same,
    noncompliance with the test is not propagated.

    When the routine test is Colonoscopy, it is also the diagnostic test. The routine_test
    function handles this by skipping all testing logic and scheduling a ROUTINE_IS_DIAGNOSTIC
    message instead, which then invokes the diagnostic_test function. We keep track of whether
    routine is diagnostic in the diagnostic_test function, and only record person.diagnostic_noncompliant
    if the diagnostic test is not also routine. (Ie, it follows a separate positive routine test.)

    The workflow:
    1. Person is noncompliant with routine colonoscopy
    2. Returns to routine testing
    3. Person has another routine colonoscopy and should be compliant
    """
    params_ = deepcopy(params)
    params_["propagate_diagnostic_noncompliance"] = True
    # Assign colonoscopy as the routine test
    params_["tests"]["Colonoscopy"]["proportion"] = 1.0
    params_["tests"]["FIT"]["proportion"] = 0.0
    # This ensures that the person will be noncompliant with their first routine test
    # and compliant with the next one (absent any unwanted noncompliance propagation)
    params_["initial_compliance_rate"] = 1.0
    params_["tests"]["Colonoscopy"]["compliance_rate_given_not_prev_compliant"] = [
        1.0
    ] * 26

    person = PersonForTests(params=params_)
    person.start()

    # Start with a noncompliant routine colonoscopy
    person.handle_testing_message(PersonTestingMessage.ROUTINE_IS_DIAGNOSTIC)

    # Return to routine testing
    person.handle_testing_message(PersonTestingMessage.NOT_COMPLIANT)

    # Before we check another routine test, we need to set the person's age to avoid
    # an error. That's because all tests after the first one will use conditional compliance
    # logic, which throws an error if the person's age is outside of the routine testing
    # range.
    person.scheduler.time = 60

    # Next routine colonoscopy should be compliant
    person.handle_testing_message(PersonTestingMessage.ROUTINE_IS_DIAGNOSTIC)
    assert person.testing_state == PersonTestingState.DIAGNOSTIC
    assert person.routine_is_diagnostic

    # Check that a routine test was added to the person's output record.
    last_output = person.out.rows[-1]
    assert last_output["record_type"] == "test_performed"
    assert last_output["role"] == TstingRole.ROUTINE


def test_variable_routine_test_colonoscopy_first(params):
    """
    Test that noncompliance is propagated as expected when using variable routine tests.

    In this case, the person starts with a colonoscopy, then switches to FIT. If the person
    is noncompliant with the colonoscopy, it shouldn't lead to noncompliance with future
    FIT tests, for the reason described in `test_routine_is_diagnostic_unaffected`.

    The workflow:
    1. Person is assigned colonoscopy as their routine test from age 50 to 60, then FIT for
        the rest of their lifespan.
    2. Person is noncompliant with routine colonoscopy every year from ages 50 to 60.
    3. At age 61, person is due for routine FIT testing. They are compliant, ie,
        noncompliance with routine_is_diagnostic colonoscopies does not propagate.
    """
    params_ = deepcopy(params)
    params_["propagate_diagnostic_noncompliance"] = True
    params_["use_variable_routine_test"] = True
    params_["routine_test_by_year"] = ["Colonoscopy"] * 11 + ["FIT"] * 15
    params_["variable_routine_test"] = StepFunction(
        params_["routine_testing_year"], params_["routine_test_by_year"]
    )
    # Set noncompliance for colonoscopy routine tests
    params_["tests"]["Colonoscopy"]["compliance_rate_given_prev_compliant"] = [0.0] * 26
    params_["tests"]["FIT"]["compliance_rate_given_prev_compliant"] = [1.0] * 26

    person = PersonForTests(params=params_)
    person.start()

    # Test at age 50 - should be colonoscopy (routine-is-diagnostic)
    person.scheduler.time = 50
    person.handle_testing_message(PersonTestingMessage.ROUTINE_IS_DIAGNOSTIC)
    assert person.testing_state == PersonTestingState.DIAGNOSTIC
    assert person.routine_is_diagnostic

    # Routine-is-diagnostic noncompliance should NOT set diagnostic_noncompliant flag
    assert not person.diagnostic_noncompliant

    person.transition_diagnostic_to_routine()

    # Test at age 61 - should switch to FIT and be compliant
    person.scheduler.time = 61
    # We need to manually update the person's routine test to match their age. In the
    # simulation, this is done by `Person.handle_yearly_actions`, but that also kicks off
    # `Person.do_tests`, which we don't want here.
    person.routine_test = person.params["variable_routine_test"](person.scheduler.time)
    assert person.routine_test == "FIT"

    # FIT compliance should not be affected by previous colonoscopy noncompliance
    assert person.is_compliant(person.routine_test)


def test_variable_routine_test_fit_first(params):
    """
    Test that noncompliance is propagated as expected when using variable routine tests.

    In this case, the person starts with FIT tests, then switches to colonoscopy. If the
    person screens positive for FIT and is noncompliant with the diagnostic colonoscopy,
    they should be noncompliant for all future routine tests, both FIT and colonoscopy.

    The workflow:
    1. Person is assigned FIT as their routine test from age 50 to 60, then Colonoscopy for
        the rest of their lifespan.
    2. Person screens positive with a FIT test at age 50.
    3. Person is noncompliant with the diagnostic colonoscopy at age 50.
    4. Person is noncompliant for all future routine tests, including FIT tests from ages
       51 to 60, and colonoscopy tests from ages 61 and beyond. (For simplicity, we just
       test one year of noncompliance for each test type.)
    """
    params_ = deepcopy(params)
    params_["propagate_diagnostic_noncompliance"] = True
    params_["use_variable_routine_test"] = True
    params_["routine_test_by_year"] = ["FIT"] * 11 + ["Colonoscopy"] * 15
    params_["variable_routine_test"] = StepFunction(
        params_["routine_testing_year"], params_["routine_test_by_year"]
    )

    person = PersonForTests(params=params_)
    person.force_diagnostic_noncompliance()
    person.start()

    # Test at age 50 - person should automatically be assigned FIT as starting routine
    # test based on logic in `Person.choose_tests`
    person.scheduler.time = 50
    assert person.routine_test == "FIT"

    # Simulate positive FIT screen → diagnostic colonoscopy
    person.trigger_positive_screen()
    assert person.testing_state == PersonTestingState.DIAGNOSTIC
    assert not person.routine_is_diagnostic

    # Person is noncompliant with diagnostic colonoscopy
    person.test_diagnostic()
    assert person.diagnostic_noncompliant  # This SHOULD set the flag

    person.transition_diagnostic_to_routine()

    # Test at age 51 - still FIT, should be noncompliant due to propagation
    person.scheduler.time = 51
    # Now we have to update the person's routine test to match their age. In the simulation,
    # this is done by `Person.handle_yearly_actions`, but that also kicks off `Person.do_tests`,
    # which we don't want here.
    person.routine_test = person.params["variable_routine_test"](person.scheduler.time)
    assert person.routine_test == "FIT"

    fit_compliant = person.is_compliant(person.routine_test)
    assert not fit_compliant  # Should be noncompliant due to propagation

    # Test at age 61 - switches to colonoscopy, should still be noncompliant
    person.scheduler.time = 61
    person.routine_test = person.params["variable_routine_test"](
        61
    )  # Should be Colonoscopy
    assert person.routine_test == "Colonoscopy"

    # Test routine colonoscopy - this would be routine-is-diagnostic
    person.handle_testing_message(PersonTestingMessage.ROUTINE_IS_DIAGNOSTIC)
    assert person.testing_state == PersonTestingState.DIAGNOSTIC
    assert person.routine_is_diagnostic

    # Check that person was noncompliant with routine colonoscopy
    last_output = person.out.rows[-1]
    assert last_output["record_type"] == "noncompliance"
    assert last_output["role"] == TstingRole.ROUTINE
