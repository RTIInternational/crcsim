import random

import pytest

from crcsim.agent import Lesion, Person
from crcsim.enums import (
    LesionMessage,
    LesionState,
    PersonDiseaseMessage,
    PersonDiseaseState,
    PersonTestingMessage,
    PersonTestingState,
    PersonTreatmentMessage,
    PersonTreatmentState,
    RaceEthnicity,
    Sex,
)
from crcsim.output import Output
from crcsim.parameters import load_params
from crcsim.scheduler import Scheduler

# The purpose of this testing module is to verify that statecharts move into the
# expected state given the current state and a message.
#
# A test case should be included for every message that is explicitly handled in
# the statechart logic. If you discover one that is missing, please add it.
#
# Test cases shouldn't _necessarily_ be included for messages that are silently
# ignored (implying that the statechart does nothing and stays in the same
# state). Some may be included in potentially tricky situations, such as
# ignoring the POLYP_ONSET message when in the Person's POLYP_SMALL state.
#
# The test cases are defined with a lot of tedious code, but the concept of each
# is fairly simple:
#
#   1. Put the statechart into a given current state.
#   2. Send a message to the statechart.
#   3. Verify that the statechart has moved into the expected state.
#
# The first step of putting the statechart into a given current state seems like
# it could be as trivial as something like this:
#
#   person.disease_state = PersonDiseaseState.PRECLINICAL_STAGE2  # noqa: ERA001
#
# However, this approach doesn't work in all cases, because it bypasses the code
# that runs as the statechart transitions through the previous states, and
# important variables may be assigned during those transitions. Instead, we need
# to specify a sequence of messages that takes the statechart from the initial
# state up through the desired current state. Therefore, our test cases are
# defined with the following attributes:
#
#   - message_history: sequence of messages that takes the statechart from
#     the initial state up through the desired current state
#   - current: desired current state, which will be reached via message_history
#   - message: message to send as part of the test
#   - end: expected state after the statechart handles the message
#
# We could have simplified the test case by omitting the `current` attribute and
# appending `message` to `message_history`. However, we separated it out this
# way because we think explicitly naming the current state makes it easier to
# understand the test.
#
# So far this message-history approach has worked, but it's conceivable that
# we'll introduce cross-statechart dependencies in the future, in which case
# this approach may not be sufficient. For example, suppose the logic for
# transitioning out of a given treatment state makes assumptions about the
# current disease state. Our test case definitions for the treatment state don't
# do anything to set up the disease statechart, so we might encounter errors.
# Setting up multiple statecharts for each test case would introduce more
# complexity, and it might reach a point where the value of these tests doesn't
# warrant their complexity. That tradeoff already seems borderline as it is.


@pytest.fixture(scope="module")
def params():
    return load_params("parameters.json")


@pytest.fixture(scope="module")
def out():
    return Output("/dev/null")


@pytest.fixture(scope="module")
def scheduler():
    return Scheduler()


@pytest.fixture(scope="module")
def rng():
    return random.Random()


@pytest.fixture
def person(params, scheduler, rng, out):
    person = Person(
        id=0,
        sex=Sex.MALE,
        race_ethnicity=RaceEthnicity.HISPANIC,
        expected_lifespan=params["max_age"],
        params=params,
        scheduler=scheduler,
        rng=rng,
        out=out,
    )
    person.start()
    return person


@pytest.fixture
def lesion(params, scheduler, person, rng, out):
    return Lesion(params=params, scheduler=scheduler, person=person, rng=rng, out=out)


@pytest.mark.parametrize(
    "case",
    [
        # polyp size progression
        {
            "message_history": [],
            "start": PersonDiseaseState.HEALTHY,
            "message": PersonDiseaseMessage.POLYP_ONSET,
            "end": PersonDiseaseState.SMALL_POLYP,
        },
        {
            "message_history": [PersonDiseaseMessage.POLYP_ONSET],
            "start": PersonDiseaseState.SMALL_POLYP,
            "message": PersonDiseaseMessage.POLYP_MEDIUM_ONSET,
            "end": PersonDiseaseState.MEDIUM_POLYP,
        },
        {
            "message_history": [
                PersonDiseaseMessage.POLYP_ONSET,
                PersonDiseaseMessage.POLYP_MEDIUM_ONSET,
            ],
            "start": PersonDiseaseState.MEDIUM_POLYP,
            "message": PersonDiseaseMessage.POLYP_LARGE_ONSET,
            "end": PersonDiseaseState.LARGE_POLYP,
        },
        # Polyp size doesn't increase if the onset message is for an equal or
        # smaller sized polyp.
        {
            "message_history": [PersonDiseaseMessage.POLYP_ONSET],
            "start": PersonDiseaseState.SMALL_POLYP,
            "message": PersonDiseaseMessage.POLYP_ONSET,
            "end": PersonDiseaseState.SMALL_POLYP,
        },
        {
            "message_history": [
                PersonDiseaseMessage.POLYP_ONSET,
                PersonDiseaseMessage.POLYP_MEDIUM_ONSET,
            ],
            "start": PersonDiseaseState.MEDIUM_POLYP,
            "message": PersonDiseaseMessage.POLYP_ONSET,
            "end": PersonDiseaseState.MEDIUM_POLYP,
        },
        {
            "message_history": [
                PersonDiseaseMessage.POLYP_ONSET,
                PersonDiseaseMessage.POLYP_MEDIUM_ONSET,
            ],
            "start": PersonDiseaseState.MEDIUM_POLYP,
            "message": PersonDiseaseMessage.POLYP_MEDIUM_ONSET,
            "end": PersonDiseaseState.MEDIUM_POLYP,
        },
        # all polyps removed
        {
            "message_history": [PersonDiseaseMessage.POLYP_ONSET],
            "start": PersonDiseaseState.SMALL_POLYP,
            "message": PersonDiseaseMessage.ALL_POLYPS_REMOVED,
            "end": PersonDiseaseState.HEALTHY,
        },
        {
            "message_history": [
                PersonDiseaseMessage.POLYP_ONSET,
                PersonDiseaseMessage.POLYP_MEDIUM_ONSET,
            ],
            "start": PersonDiseaseState.MEDIUM_POLYP,
            "message": PersonDiseaseMessage.ALL_POLYPS_REMOVED,
            "end": PersonDiseaseState.HEALTHY,
        },
        {
            "message_history": [
                PersonDiseaseMessage.POLYP_ONSET,
                PersonDiseaseMessage.POLYP_MEDIUM_ONSET,
                PersonDiseaseMessage.POLYP_LARGE_ONSET,
            ],
            "start": PersonDiseaseState.LARGE_POLYP,
            "message": PersonDiseaseMessage.ALL_POLYPS_REMOVED,
            "end": PersonDiseaseState.HEALTHY,
        },
        # transitions from polyp to preclinical cancer
        #
        # Note that the small => preclinical transition is omitted here because it
        # isn't handled by the code. A lesion can't go from small polyp to
        # preclinical cancer, so we didn't include a case for that transition in the
        # person, either.
        {
            "message_history": [
                PersonDiseaseMessage.POLYP_ONSET,
                PersonDiseaseMessage.POLYP_MEDIUM_ONSET,
            ],
            "start": PersonDiseaseState.MEDIUM_POLYP,
            "message": PersonDiseaseMessage.PRECLINICAL_ONSET,
            "end": PersonDiseaseState.PRECLINICAL_STAGE1,
        },
        {
            "message_history": [
                PersonDiseaseMessage.POLYP_ONSET,
                PersonDiseaseMessage.POLYP_MEDIUM_ONSET,
                PersonDiseaseMessage.POLYP_LARGE_ONSET,
            ],
            "start": PersonDiseaseState.LARGE_POLYP,
            "message": PersonDiseaseMessage.PRECLINICAL_ONSET,
            "end": PersonDiseaseState.PRECLINICAL_STAGE1,
        },
        # preclinical cancer progression
        {
            "message_history": [
                PersonDiseaseMessage.POLYP_ONSET,
                PersonDiseaseMessage.POLYP_MEDIUM_ONSET,
                PersonDiseaseMessage.PRECLINICAL_ONSET,
            ],
            "start": PersonDiseaseState.PRECLINICAL_STAGE1,
            "message": PersonDiseaseMessage.PRE2_ONSET,
            "end": PersonDiseaseState.PRECLINICAL_STAGE2,
        },
        {
            "message_history": [
                PersonDiseaseMessage.POLYP_ONSET,
                PersonDiseaseMessage.POLYP_MEDIUM_ONSET,
                PersonDiseaseMessage.PRECLINICAL_ONSET,
                PersonDiseaseMessage.PRE2_ONSET,
            ],
            "start": PersonDiseaseState.PRECLINICAL_STAGE2,
            "message": PersonDiseaseMessage.PRE3_ONSET,
            "end": PersonDiseaseState.PRECLINICAL_STAGE3,
        },
        {
            "message_history": [
                PersonDiseaseMessage.POLYP_ONSET,
                PersonDiseaseMessage.POLYP_MEDIUM_ONSET,
                PersonDiseaseMessage.PRECLINICAL_ONSET,
                PersonDiseaseMessage.PRE2_ONSET,
                PersonDiseaseMessage.PRE3_ONSET,
            ],
            "start": PersonDiseaseState.PRECLINICAL_STAGE3,
            "message": PersonDiseaseMessage.PRE3_ONSET,
            "end": PersonDiseaseState.PRECLINICAL_STAGE3,
        },
        # clinical cancer detection
        {
            "message_history": [
                PersonDiseaseMessage.POLYP_ONSET,
                PersonDiseaseMessage.POLYP_MEDIUM_ONSET,
                PersonDiseaseMessage.PRECLINICAL_ONSET,
            ],
            "start": PersonDiseaseState.PRECLINICAL_STAGE1,
            "message": PersonDiseaseMessage.CLINICAL_ONSET,
            "end": PersonDiseaseState.CLINICAL_STAGE1,
        },
        {
            "message_history": [
                PersonDiseaseMessage.POLYP_ONSET,
                PersonDiseaseMessage.POLYP_MEDIUM_ONSET,
                PersonDiseaseMessage.PRECLINICAL_ONSET,
                PersonDiseaseMessage.PRE2_ONSET,
            ],
            "start": PersonDiseaseState.PRECLINICAL_STAGE2,
            "message": PersonDiseaseMessage.CLINICAL_ONSET,
            "end": PersonDiseaseState.CLINICAL_STAGE2,
        },
        {
            "message_history": [
                PersonDiseaseMessage.POLYP_ONSET,
                PersonDiseaseMessage.POLYP_MEDIUM_ONSET,
                PersonDiseaseMessage.PRECLINICAL_ONSET,
                PersonDiseaseMessage.PRE2_ONSET,
                PersonDiseaseMessage.PRE3_ONSET,
            ],
            "start": PersonDiseaseState.PRECLINICAL_STAGE3,
            "message": PersonDiseaseMessage.CLINICAL_ONSET,
            "end": PersonDiseaseState.CLINICAL_STAGE3,
        },
        {
            "message_history": [
                PersonDiseaseMessage.POLYP_ONSET,
                PersonDiseaseMessage.POLYP_MEDIUM_ONSET,
                PersonDiseaseMessage.PRECLINICAL_ONSET,
                PersonDiseaseMessage.PRE2_ONSET,
                PersonDiseaseMessage.PRE3_ONSET,
                PersonDiseaseMessage.PRE4_ONSET,
            ],
            "start": PersonDiseaseState.PRECLINICAL_STAGE4,
            "message": PersonDiseaseMessage.CLINICAL_ONSET,
            "end": PersonDiseaseState.CLINICAL_STAGE4,
        },
        # CRC death
        {
            "message_history": [
                PersonDiseaseMessage.POLYP_ONSET,
                PersonDiseaseMessage.POLYP_MEDIUM_ONSET,
                PersonDiseaseMessage.PRECLINICAL_ONSET,
                PersonDiseaseMessage.CLINICAL_ONSET,
            ],
            "start": PersonDiseaseState.CLINICAL_STAGE1,
            "message": PersonDiseaseMessage.CRC_DEATH,
            "end": PersonDiseaseState.DEAD,
        },
        {
            "message_history": [
                PersonDiseaseMessage.POLYP_ONSET,
                PersonDiseaseMessage.POLYP_MEDIUM_ONSET,
                PersonDiseaseMessage.PRECLINICAL_ONSET,
                PersonDiseaseMessage.PRE2_ONSET,
                PersonDiseaseMessage.CLINICAL_ONSET,
            ],
            "start": PersonDiseaseState.CLINICAL_STAGE2,
            "message": PersonDiseaseMessage.CRC_DEATH,
            "end": PersonDiseaseState.DEAD,
        },
        {
            "message_history": [
                PersonDiseaseMessage.POLYP_ONSET,
                PersonDiseaseMessage.POLYP_MEDIUM_ONSET,
                PersonDiseaseMessage.PRECLINICAL_ONSET,
                PersonDiseaseMessage.PRE2_ONSET,
                PersonDiseaseMessage.PRE3_ONSET,
                PersonDiseaseMessage.CLINICAL_ONSET,
            ],
            "start": PersonDiseaseState.CLINICAL_STAGE3,
            "message": PersonDiseaseMessage.CRC_DEATH,
            "end": PersonDiseaseState.DEAD,
        },
        {
            "message_history": [
                PersonDiseaseMessage.POLYP_ONSET,
                PersonDiseaseMessage.POLYP_MEDIUM_ONSET,
                PersonDiseaseMessage.PRECLINICAL_ONSET,
                PersonDiseaseMessage.PRE2_ONSET,
                PersonDiseaseMessage.PRE3_ONSET,
                PersonDiseaseMessage.PRE4_ONSET,
                PersonDiseaseMessage.CLINICAL_ONSET,
            ],
            "start": PersonDiseaseState.CLINICAL_STAGE4,
            "message": PersonDiseaseMessage.CRC_DEATH,
            "end": PersonDiseaseState.DEAD,
        },
        # death from other causes
        {
            "message_history": [],
            "start": PersonDiseaseState.HEALTHY,
            "message": PersonDiseaseMessage.OTHER_DEATH,
            "end": PersonDiseaseState.DEAD,
        },
        {
            "message_history": [PersonDiseaseMessage.POLYP_ONSET],
            "start": PersonDiseaseState.SMALL_POLYP,
            "message": PersonDiseaseMessage.OTHER_DEATH,
            "end": PersonDiseaseState.DEAD,
        },
        {
            "message_history": [
                PersonDiseaseMessage.POLYP_ONSET,
                PersonDiseaseMessage.POLYP_MEDIUM_ONSET,
            ],
            "start": PersonDiseaseState.MEDIUM_POLYP,
            "message": PersonDiseaseMessage.OTHER_DEATH,
            "end": PersonDiseaseState.DEAD,
        },
        {
            "message_history": [
                PersonDiseaseMessage.POLYP_ONSET,
                PersonDiseaseMessage.POLYP_MEDIUM_ONSET,
                PersonDiseaseMessage.POLYP_LARGE_ONSET,
            ],
            "start": PersonDiseaseState.LARGE_POLYP,
            "message": PersonDiseaseMessage.OTHER_DEATH,
            "end": PersonDiseaseState.DEAD,
        },
        {
            "message_history": [
                PersonDiseaseMessage.POLYP_ONSET,
                PersonDiseaseMessage.POLYP_MEDIUM_ONSET,
                PersonDiseaseMessage.PRECLINICAL_ONSET,
            ],
            "start": PersonDiseaseState.PRECLINICAL_STAGE1,
            "message": PersonDiseaseMessage.OTHER_DEATH,
            "end": PersonDiseaseState.DEAD,
        },
        {
            "message_history": [
                PersonDiseaseMessage.POLYP_ONSET,
                PersonDiseaseMessage.POLYP_MEDIUM_ONSET,
                PersonDiseaseMessage.PRECLINICAL_ONSET,
                PersonDiseaseMessage.PRE2_ONSET,
            ],
            "start": PersonDiseaseState.PRECLINICAL_STAGE2,
            "message": PersonDiseaseMessage.OTHER_DEATH,
            "end": PersonDiseaseState.DEAD,
        },
        {
            "message_history": [
                PersonDiseaseMessage.POLYP_ONSET,
                PersonDiseaseMessage.POLYP_MEDIUM_ONSET,
                PersonDiseaseMessage.PRECLINICAL_ONSET,
                PersonDiseaseMessage.PRE2_ONSET,
                PersonDiseaseMessage.PRE3_ONSET,
            ],
            "start": PersonDiseaseState.PRECLINICAL_STAGE3,
            "message": PersonDiseaseMessage.OTHER_DEATH,
            "end": PersonDiseaseState.DEAD,
        },
        {
            "message_history": [
                PersonDiseaseMessage.POLYP_ONSET,
                PersonDiseaseMessage.POLYP_MEDIUM_ONSET,
                PersonDiseaseMessage.PRECLINICAL_ONSET,
                PersonDiseaseMessage.PRE2_ONSET,
                PersonDiseaseMessage.PRE3_ONSET,
                PersonDiseaseMessage.PRE4_ONSET,
            ],
            "start": PersonDiseaseState.PRECLINICAL_STAGE4,
            "message": PersonDiseaseMessage.OTHER_DEATH,
            "end": PersonDiseaseState.DEAD,
        },
        {
            "message_history": [
                PersonDiseaseMessage.POLYP_ONSET,
                PersonDiseaseMessage.POLYP_MEDIUM_ONSET,
                PersonDiseaseMessage.PRECLINICAL_ONSET,
                PersonDiseaseMessage.CLINICAL_ONSET,
            ],
            "start": PersonDiseaseState.CLINICAL_STAGE1,
            "message": PersonDiseaseMessage.OTHER_DEATH,
            "end": PersonDiseaseState.DEAD,
        },
        {
            "message_history": [
                PersonDiseaseMessage.POLYP_ONSET,
                PersonDiseaseMessage.POLYP_MEDIUM_ONSET,
                PersonDiseaseMessage.PRECLINICAL_ONSET,
                PersonDiseaseMessage.PRE2_ONSET,
                PersonDiseaseMessage.CLINICAL_ONSET,
            ],
            "start": PersonDiseaseState.CLINICAL_STAGE2,
            "message": PersonDiseaseMessage.OTHER_DEATH,
            "end": PersonDiseaseState.DEAD,
        },
        {
            "message_history": [
                PersonDiseaseMessage.POLYP_ONSET,
                PersonDiseaseMessage.POLYP_MEDIUM_ONSET,
                PersonDiseaseMessage.PRECLINICAL_ONSET,
                PersonDiseaseMessage.PRE2_ONSET,
                PersonDiseaseMessage.PRE3_ONSET,
                PersonDiseaseMessage.CLINICAL_ONSET,
            ],
            "start": PersonDiseaseState.CLINICAL_STAGE3,
            "message": PersonDiseaseMessage.OTHER_DEATH,
            "end": PersonDiseaseState.DEAD,
        },
        {
            "message_history": [
                PersonDiseaseMessage.POLYP_ONSET,
                PersonDiseaseMessage.POLYP_MEDIUM_ONSET,
                PersonDiseaseMessage.PRECLINICAL_ONSET,
                PersonDiseaseMessage.PRE2_ONSET,
                PersonDiseaseMessage.PRE3_ONSET,
                PersonDiseaseMessage.PRE4_ONSET,
                PersonDiseaseMessage.CLINICAL_ONSET,
            ],
            "start": PersonDiseaseState.CLINICAL_STAGE4,
            "message": PersonDiseaseMessage.OTHER_DEATH,
            "end": PersonDiseaseState.DEAD,
        },
    ],
)
def test_person_disease_transitions(case, person):
    person.start()
    for message in case["message_history"]:
        person.handle_disease_message(message)
    assert person.disease_state == case["start"]
    person.handle_disease_message(case["message"])
    assert person.disease_state == case["end"]


@pytest.mark.parametrize(
    "case",
    [
        # transitions out of ROUTINE
        {
            "message_history": [],
            "start": PersonTestingState.ROUTINE,
            "message": PersonTestingMessage.SYMPTOMATIC,
            "end": PersonTestingState.DIAGNOSTIC,
        },
        {
            "message_history": [],
            "start": PersonTestingState.ROUTINE,
            "message": PersonTestingMessage.SCREEN_POSITIVE,
            "end": PersonTestingState.DIAGNOSTIC,
        },
        {
            "message_history": [],
            "start": PersonTestingState.ROUTINE,
            "message": PersonTestingMessage.ROUTINE_IS_DIAGNOSTIC,
            "end": PersonTestingState.DIAGNOSTIC,
        },
        # transitions out of DIAGNOSTIC
        {
            "message_history": [PersonTestingMessage.SCREEN_POSITIVE],
            "start": PersonTestingState.DIAGNOSTIC,
            "message": PersonTestingMessage.NEGATIVE,
            "end": PersonTestingState.SKIP_TESTING,
        },
        {
            "message_history": [PersonTestingMessage.SCREEN_POSITIVE],
            "start": PersonTestingState.DIAGNOSTIC,
            "message": PersonTestingMessage.NOT_COMPLIANT,
            "end": PersonTestingState.ROUTINE,
        },
        {
            "message_history": [PersonTestingMessage.SCREEN_POSITIVE],
            "start": PersonTestingState.DIAGNOSTIC,
            "message": PersonTestingMessage.POSITIVE_POLYP,
            "end": PersonTestingState.SURVEILLANCE,
        },
        {
            "message_history": [PersonTestingMessage.SCREEN_POSITIVE],
            "start": PersonTestingState.DIAGNOSTIC,
            "message": PersonTestingMessage.POSITIVE_CANCER,
            "end": PersonTestingState.SURVEILLANCE,
        },
        # transitions out of SKIP_TESTING
        {
            "message_history": [
                PersonTestingMessage.SCREEN_POSITIVE,
                PersonTestingMessage.NEGATIVE,
            ],
            "start": PersonTestingState.SKIP_TESTING,
            "message": PersonTestingMessage.RETURN_TO_ROUTINE,
            "end": PersonTestingState.ROUTINE,
        },
        {
            "message_history": [
                PersonTestingMessage.SCREEN_POSITIVE,
                PersonTestingMessage.NEGATIVE,
            ],
            "start": PersonTestingState.SKIP_TESTING,
            "message": PersonTestingMessage.SYMPTOMATIC,
            "end": PersonTestingState.DIAGNOSTIC,
        },
        # transitions while in SURVEILLANCE
        {
            "message_history": [
                PersonTestingMessage.SCREEN_POSITIVE,
                PersonTestingMessage.POSITIVE_POLYP,
            ],
            "start": PersonTestingState.SURVEILLANCE,
            "message": PersonTestingMessage.SYMPTOMATIC,
            "end": PersonTestingState.SURVEILLANCE,
        },
        {
            "message_history": [
                PersonTestingMessage.SCREEN_POSITIVE,
                PersonTestingMessage.POSITIVE_POLYP,
            ],
            "start": PersonTestingState.SURVEILLANCE,
            "message": PersonTestingMessage.NOT_COMPLIANT,
            "end": PersonTestingState.SURVEILLANCE,
        },
        {
            "message_history": [
                PersonTestingMessage.SCREEN_POSITIVE,
                PersonTestingMessage.POSITIVE_POLYP,
            ],
            "start": PersonTestingState.SURVEILLANCE,
            "message": PersonTestingMessage.NEGATIVE,
            "end": PersonTestingState.SURVEILLANCE,
        },
        {
            "message_history": [
                PersonTestingMessage.SCREEN_POSITIVE,
                PersonTestingMessage.POSITIVE_POLYP,
            ],
            "start": PersonTestingState.SURVEILLANCE,
            "message": PersonTestingMessage.POSITIVE_POLYP,
            "end": PersonTestingState.SURVEILLANCE,
        },
        {
            "message_history": [
                PersonTestingMessage.SCREEN_POSITIVE,
                PersonTestingMessage.POSITIVE_POLYP,
            ],
            "start": PersonTestingState.SURVEILLANCE,
            "message": PersonTestingMessage.POSITIVE_CANCER,
            "end": PersonTestingState.SURVEILLANCE,
        },
    ],
)
def test_person_testing_transitions(case, person):
    person.start()
    for message in case["message_history"]:
        person.handle_testing_message(message)
    assert person.testing_state == case["start"]
    person.handle_testing_message(case["message"])
    assert person.testing_state == case["end"]


@pytest.mark.parametrize(
    "case",
    [
        {
            "message_history": [],
            "start": PersonTreatmentState.NO_TREATMENT,
            "message": PersonTreatmentMessage.START_TREATMENT,
            "end": PersonTreatmentState.TREATMENT,
        },
        {
            "message_history": [PersonTreatmentMessage.START_TREATMENT],
            "start": PersonTreatmentState.TREATMENT,
            "message": PersonTreatmentMessage.START_TREATMENT,
            "end": PersonTreatmentState.TREATMENT,
        },
    ],
)
def test_person_treatment_transitions(case, person):
    person.start()
    for message in case["message_history"]:
        person.handle_treatment_message(message)
    assert person.treatment_state == case["start"]
    person.handle_treatment_message(case["message"])
    assert person.treatment_state == case["end"]


@pytest.mark.parametrize(
    "case",
    [
        # polyp size progression
        {
            "message_history": [],
            "start": LesionState.SMALL_POLYP,
            "message": LesionMessage.PROGRESS_POLYP_STAGE,
            "end": LesionState.MEDIUM_POLYP,
        },
        {
            "message_history": [LesionMessage.PROGRESS_POLYP_STAGE],
            "start": LesionState.MEDIUM_POLYP,
            "message": LesionMessage.PROGRESS_POLYP_STAGE,
            "end": LesionState.LARGE_POLYP,
        },
        # polyp removal after clinical detection
        {
            "message_history": [],
            "start": LesionState.SMALL_POLYP,
            "message": LesionMessage.CLINICAL_DETECTION,
            "end": LesionState.REMOVED,
        },
        {
            "message_history": [LesionMessage.PROGRESS_POLYP_STAGE],
            "start": LesionState.MEDIUM_POLYP,
            "message": LesionMessage.CLINICAL_DETECTION,
            "end": LesionState.REMOVED,
        },
        {
            "message_history": [
                LesionMessage.PROGRESS_POLYP_STAGE,
                LesionMessage.PROGRESS_POLYP_STAGE,
            ],
            "start": LesionState.LARGE_POLYP,
            "message": LesionMessage.CLINICAL_DETECTION,
            "end": LesionState.REMOVED,
        },
        # transitions from polyp to preclinical cancer
        {
            "message_history": [LesionMessage.PROGRESS_POLYP_STAGE],
            "start": LesionState.MEDIUM_POLYP,
            "message": LesionMessage.BECOME_CANCER,
            "end": LesionState.PRECLINICAL_STAGE1,
        },
        {
            "message_history": [
                LesionMessage.PROGRESS_POLYP_STAGE,
                LesionMessage.PROGRESS_POLYP_STAGE,
            ],
            "start": LesionState.LARGE_POLYP,
            "message": LesionMessage.BECOME_CANCER,
            "end": LesionState.PRECLINICAL_STAGE1,
        },
        # pre-clinical cancer progression
        {
            "message_history": [
                LesionMessage.PROGRESS_POLYP_STAGE,
                LesionMessage.BECOME_CANCER,
            ],
            "start": LesionState.PRECLINICAL_STAGE1,
            "message": LesionMessage.PROGRESS_CANCER_STAGE,
            "end": LesionState.PRECLINICAL_STAGE2,
        },
        {
            "message_history": [
                LesionMessage.PROGRESS_POLYP_STAGE,
                LesionMessage.BECOME_CANCER,
                LesionMessage.PROGRESS_CANCER_STAGE,
            ],
            "start": LesionState.PRECLINICAL_STAGE2,
            "message": LesionMessage.PROGRESS_CANCER_STAGE,
            "end": LesionState.PRECLINICAL_STAGE3,
        },
        {
            "message_history": [
                LesionMessage.PROGRESS_POLYP_STAGE,
                LesionMessage.BECOME_CANCER,
                LesionMessage.PROGRESS_CANCER_STAGE,
                LesionMessage.PROGRESS_CANCER_STAGE,
            ],
            "start": LesionState.PRECLINICAL_STAGE3,
            "message": LesionMessage.PROGRESS_CANCER_STAGE,
            "end": LesionState.PRECLINICAL_STAGE4,
        },
        # clinical cancer detection
        {
            "message_history": [
                LesionMessage.PROGRESS_POLYP_STAGE,
                LesionMessage.BECOME_CANCER,
            ],
            "start": LesionState.PRECLINICAL_STAGE1,
            "message": LesionMessage.CLINICAL_DETECTION,
            "end": LesionState.CLINICAL_STAGE1,
        },
        {
            "message_history": [
                LesionMessage.PROGRESS_POLYP_STAGE,
                LesionMessage.BECOME_CANCER,
                LesionMessage.PROGRESS_CANCER_STAGE,
            ],
            "start": LesionState.PRECLINICAL_STAGE2,
            "message": LesionMessage.CLINICAL_DETECTION,
            "end": LesionState.CLINICAL_STAGE2,
        },
        {
            "message_history": [
                LesionMessage.PROGRESS_POLYP_STAGE,
                LesionMessage.BECOME_CANCER,
                LesionMessage.PROGRESS_CANCER_STAGE,
                LesionMessage.PROGRESS_CANCER_STAGE,
            ],
            "start": LesionState.PRECLINICAL_STAGE3,
            "message": LesionMessage.CLINICAL_DETECTION,
            "end": LesionState.CLINICAL_STAGE3,
        },
        {
            "message_history": [
                LesionMessage.PROGRESS_POLYP_STAGE,
                LesionMessage.BECOME_CANCER,
                LesionMessage.PROGRESS_CANCER_STAGE,
                LesionMessage.PROGRESS_CANCER_STAGE,
                LesionMessage.PROGRESS_CANCER_STAGE,
            ],
            "start": LesionState.PRECLINICAL_STAGE4,
            "message": LesionMessage.CLINICAL_DETECTION,
            "end": LesionState.CLINICAL_STAGE4,
        },
        # CRC death
        {
            "message_history": [
                LesionMessage.PROGRESS_POLYP_STAGE,
                LesionMessage.BECOME_CANCER,
                LesionMessage.CLINICAL_DETECTION,
            ],
            "start": LesionState.CLINICAL_STAGE1,
            "message": LesionMessage.KILL_PERSON,
            "end": LesionState.DEAD,
        },
        {
            "message_history": [
                LesionMessage.PROGRESS_POLYP_STAGE,
                LesionMessage.BECOME_CANCER,
                LesionMessage.PROGRESS_CANCER_STAGE,
                LesionMessage.CLINICAL_DETECTION,
            ],
            "start": LesionState.CLINICAL_STAGE2,
            "message": LesionMessage.KILL_PERSON,
            "end": LesionState.DEAD,
        },
        {
            "message_history": [
                LesionMessage.PROGRESS_POLYP_STAGE,
                LesionMessage.BECOME_CANCER,
                LesionMessage.PROGRESS_CANCER_STAGE,
                LesionMessage.PROGRESS_CANCER_STAGE,
                LesionMessage.CLINICAL_DETECTION,
            ],
            "start": LesionState.CLINICAL_STAGE3,
            "message": LesionMessage.KILL_PERSON,
            "end": LesionState.DEAD,
        },
        {
            "message_history": [
                LesionMessage.PROGRESS_POLYP_STAGE,
                LesionMessage.BECOME_CANCER,
                LesionMessage.PROGRESS_CANCER_STAGE,
                LesionMessage.PROGRESS_CANCER_STAGE,
                LesionMessage.PROGRESS_CANCER_STAGE,
                LesionMessage.CLINICAL_DETECTION,
            ],
            "start": LesionState.CLINICAL_STAGE4,
            "message": LesionMessage.KILL_PERSON,
            "end": LesionState.DEAD,
        },
    ],
)
def test_lesion_transition(case, lesion):
    for message in case["message_history"]:
        lesion.handle_message(message)
    assert lesion.state == case["start"]
    lesion.handle_message(case["message"])
    assert lesion.state == case["end"]
