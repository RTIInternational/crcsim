import bisect
import itertools
import math
from enum import Enum, IntEnum, unique


@unique
class PersonDiseaseState(IntEnum):
    UNINITIALIZED = 0
    HEALTHY = 1
    SMALL_POLYP = 2
    MEDIUM_POLYP = 3
    LARGE_POLYP = 4
    PRECLINICAL_STAGE1 = 5
    PRECLINICAL_STAGE2 = 6
    PRECLINICAL_STAGE3 = 7
    PRECLINICAL_STAGE4 = 8
    CLINICAL_STAGE1 = 9
    CLINICAL_STAGE2 = 10
    CLINICAL_STAGE3 = 11
    CLINICAL_STAGE4 = 12
    DEAD = 13

    def __str__(self):
        return self.name


@unique
class PersonDiseaseMessage(IntEnum):
    INIT = 0
    POLYP_ONSET = 1
    POLYP_MEDIUM_ONSET = 2
    POLYP_LARGE_ONSET = 3
    PRECLINICAL_ONSET = 4
    PRE2_ONSET = 5
    PRE3_ONSET = 6
    PRE4_ONSET = 7
    CLINICAL_ONSET = 8
    ALL_POLYPS_REMOVED = 9
    OTHER_DEATH = 10
    CRC_DEATH = 11
    POLYPECTOMY_DEATH = 12

    def __str__(self):
        return self.name


@unique
class PersonTestingState(IntEnum):
    UNINITIALIZED = 0
    ROUTINE = 1
    DIAGNOSTIC = 2
    SKIP_TESTING = 3
    SURVEILLANCE = 4
    NO_TESTING = 5

    def __str__(self):
        return self.name


@unique
class PersonTestingMessage(IntEnum):
    INIT = 0
    SYMPTOMATIC = 1
    SCREEN_POSITIVE = 2
    ROUTINE_IS_DIAGNOSTIC = 3
    NOT_COMPLIANT = 4
    RETURN_TO_ROUTINE = 5
    NEGATIVE = 6
    POSITIVE_POLYP = 7
    POSITIVE_CANCER = 8

    def __str__(self):
        return self.name


@unique
class PersonTreatmentState(IntEnum):
    UNINITIALIZED = 0
    NO_TREATMENT = 1
    TREATMENT = 2

    def __str__(self):
        return self.name


@unique
class PersonTreatmentMessage(IntEnum):
    INIT = 0
    START_TREATMENT = 1

    def __str__(self):
        return self.name


@unique
class LesionState(IntEnum):
    UNINITIALIZED = 0
    SMALL_POLYP = 1
    MEDIUM_POLYP = 2
    LARGE_POLYP = 3
    PRECLINICAL_STAGE1 = 4
    PRECLINICAL_STAGE2 = 5
    PRECLINICAL_STAGE3 = 6
    PRECLINICAL_STAGE4 = 7
    CLINICAL_STAGE1 = 8
    CLINICAL_STAGE2 = 9
    CLINICAL_STAGE3 = 10
    CLINICAL_STAGE4 = 11
    REMOVED = 12
    DEAD = 13

    def __str__(self):
        return self.name


@unique
class LesionMessage(IntEnum):
    INIT = 0
    PROGRESS_POLYP_STAGE = 1
    PROGRESS_CANCER_STAGE = 2
    CLINICAL_DETECTION = 3
    BECOME_CANCER = 4
    KILL_PERSON = 5

    def __str__(self):
        return self.name


@unique
class TestingRole(IntEnum):
    ROUTINE = 1
    DIAGNOSTIC = 2
    SURVEILLANCE = 3

    def __str__(self):
        return self.name


@unique
class TreatmentRole(IntEnum):
    INITIAL = 1
    ONGOING = 2
    TERMINAL = 3

    def __str__(self):
        return self.name


@unique
class RaceEthnicity(Enum):
    HISPANIC = "hispanic"
    WHITE_NON_HISPANIC = "white_non_hispanic"
    BLACK_NON_HISPANIC = "black_non_hispanic"
    OTHER_NON_HISPANIC = "other_non_hispanic"


@unique
class Sex(Enum):
    FEMALE = "female"
    MALE = "male"
    OTHER = "other"


class Person:
    def __init__(self, id, sex, race_ethnicity, params, scheduler, rng, out):
        self.id = id
        self.sex = sex
        self.race_ethnicity = race_ethnicity
        self.params = params
        self.scheduler = scheduler
        self.rng = rng
        self.out = out

        self.expected_lifespan = None

        self.lesions = []
        self.lesion_risk_index = None
        self.previous_lesion_onset_time = 0

        # testing attributes
        self.routine_test = None
        self.diagnostic_test = None
        self.surveillance_test = None
        self.routine_is_diagnostic = False
        self.never_compliant = False
        self.routine_compliance_history = []
        self.previous_test_small = {}
        self.previous_test_medium = {}
        self.previous_test_large = {}
        self.previous_test_age = {}

        # treatment attributes
        self.previous_treatment_initiation_age = None
        self.num_ongoing_treatments = None
        self.num_surveillance_tests_since_positive = None
        self.num_ongoing_treatments = 0
        self.ongoing_treatment_event = None
        self.stage_at_detection = None

        self.disease_state = PersonDiseaseState.UNINITIALIZED
        self.testing_state = PersonTestingState.UNINITIALIZED
        self.treatment_state = PersonTreatmentState.UNINITIALIZED

        self.testing_transition_timeout_event = None

    def start(self):
        self.never_compliant = self.rng.random() < self.params["never_compliant_rate"]
        self.choose_tests()

        self.handle_disease_message(PersonDiseaseMessage.INIT)
        self.handle_testing_message(PersonTestingMessage.INIT)
        self.handle_treatment_message(PersonTreatmentMessage.INIT)

        self.scheduler.add_event(
            message="Conduct yearly actions",
            delay=1,
            handler=self.handle_yearly_actions,
        )

        self.start_life_timer()

        self.lesion_risk_index = self.rng.gammavariate(
            alpha=self.params["lesion_risk_alpha"],
            beta=self.params["lesion_risk_beta"],
        )

        lesion_delay = self.compute_lesion_delay()
        if lesion_delay is not None:
            self.scheduler.add_event(
                message="Create lesion",
                delay=lesion_delay,
                handler=self.handle_lesion_creation,
            )

    def handle_disease_message(self, message):
        if self.disease_state == PersonDiseaseState.UNINITIALIZED:
            if message == PersonDiseaseMessage.INIT:
                self.disease_state = PersonDiseaseState.HEALTHY
                self.write_state_change(
                    message,
                    PersonDiseaseState.UNINITIALIZED,
                    PersonDiseaseState.HEALTHY,
                )
            else:
                raise ValueError(
                    f"Received unexpected message {message} in disease state {self.disease_state}"
                )
        elif self.disease_state == PersonDiseaseState.HEALTHY:
            if message == PersonDiseaseMessage.POLYP_ONSET:
                self.disease_state = PersonDiseaseState.SMALL_POLYP
                self.write_state_change(
                    message, PersonDiseaseState.HEALTHY, PersonDiseaseState.SMALL_POLYP
                )
            elif message in [
                PersonDiseaseMessage.OTHER_DEATH,
                PersonDiseaseMessage.POLYPECTOMY_DEATH,
            ]:
                self.disease_state = PersonDiseaseState.DEAD
                self.write_state_change(
                    message, PersonDiseaseState.HEALTHY, PersonDiseaseState.DEAD
                )
                self.scheduler.add_event(message="end_simulation")
            else:
                pass
        elif self.disease_state == PersonDiseaseState.SMALL_POLYP:
            if message == PersonDiseaseMessage.ALL_POLYPS_REMOVED:
                self.disease_state = PersonDiseaseState.HEALTHY
                self.write_state_change(
                    message, PersonDiseaseState.SMALL_POLYP, PersonDiseaseState.HEALTHY
                )
            elif message == PersonDiseaseMessage.POLYP_MEDIUM_ONSET:
                self.disease_state = PersonDiseaseState.MEDIUM_POLYP
                self.write_state_change(
                    message,
                    PersonDiseaseState.SMALL_POLYP,
                    PersonDiseaseState.MEDIUM_POLYP,
                )
            elif message in [
                PersonDiseaseMessage.OTHER_DEATH,
                PersonDiseaseMessage.POLYPECTOMY_DEATH,
            ]:
                self.disease_state = PersonDiseaseState.DEAD
                self.write_state_change(
                    message, PersonDiseaseState.SMALL_POLYP, PersonDiseaseState.DEAD
                )
                self.scheduler.add_event(message="end_simulation")
            else:
                pass
        elif self.disease_state == PersonDiseaseState.MEDIUM_POLYP:
            if message == PersonDiseaseMessage.ALL_POLYPS_REMOVED:
                self.disease_state = PersonDiseaseState.HEALTHY
                self.write_state_change(
                    message, PersonDiseaseState.MEDIUM_POLYP, PersonDiseaseState.HEALTHY
                )
            elif message == PersonDiseaseMessage.POLYP_LARGE_ONSET:
                self.disease_state = PersonDiseaseState.LARGE_POLYP
                self.write_state_change(
                    message,
                    PersonDiseaseState.MEDIUM_POLYP,
                    PersonDiseaseState.LARGE_POLYP,
                )
            elif message == PersonDiseaseMessage.PRECLINICAL_ONSET:
                self.disease_state = PersonDiseaseState.PRECLINICAL_STAGE1
                self.write_state_change(
                    message,
                    PersonDiseaseState.MEDIUM_POLYP,
                    PersonDiseaseState.PRECLINICAL_STAGE1,
                )
            elif message in [
                PersonDiseaseMessage.OTHER_DEATH,
                PersonDiseaseMessage.POLYPECTOMY_DEATH,
            ]:
                self.disease_state = PersonDiseaseState.DEAD
                self.write_state_change(
                    message, PersonDiseaseState.MEDIUM_POLYP, PersonDiseaseState.DEAD
                )
                self.scheduler.add_event(message="end_simulation")
            else:
                pass
        elif self.disease_state == PersonDiseaseState.LARGE_POLYP:
            if message == PersonDiseaseMessage.ALL_POLYPS_REMOVED:
                self.disease_state = PersonDiseaseState.HEALTHY
                self.write_state_change(
                    message, PersonDiseaseState.LARGE_POLYP, PersonDiseaseState.HEALTHY
                )
            elif message == PersonDiseaseMessage.PRECLINICAL_ONSET:
                self.disease_state = PersonDiseaseState.PRECLINICAL_STAGE1
                self.write_state_change(
                    message,
                    PersonDiseaseState.LARGE_POLYP,
                    PersonDiseaseState.PRECLINICAL_STAGE1,
                )
            elif message in [
                PersonDiseaseMessage.OTHER_DEATH,
                PersonDiseaseMessage.POLYPECTOMY_DEATH,
            ]:
                self.disease_state = PersonDiseaseState.DEAD
                self.write_state_change(
                    message, PersonDiseaseState.LARGE_POLYP, PersonDiseaseState.DEAD
                )
                self.scheduler.add_event(message="end_simulation")
            else:
                pass
        elif self.disease_state == PersonDiseaseState.PRECLINICAL_STAGE1:
            if message == PersonDiseaseMessage.PRE2_ONSET:
                self.disease_state = PersonDiseaseState.PRECLINICAL_STAGE2
                self.write_state_change(
                    message,
                    PersonDiseaseState.PRECLINICAL_STAGE1,
                    PersonDiseaseState.PRECLINICAL_STAGE2,
                )
            elif message == PersonDiseaseMessage.CLINICAL_ONSET:
                self.disease_state = PersonDiseaseState.CLINICAL_STAGE1
                self.write_state_change(
                    message,
                    PersonDiseaseState.PRECLINICAL_STAGE1,
                    PersonDiseaseState.CLINICAL_STAGE1,
                )
                self.stage_at_detection = 1
                # when one cancer is detected then all cancers are detected
                self.detect_other_cancers()
                # Begin treatment
                self.scheduler.add_event(
                    message=PersonTreatmentMessage.START_TREATMENT,
                    handler=self.handle_treatment_message,
                )
            elif message in [
                PersonDiseaseMessage.OTHER_DEATH,
                PersonDiseaseMessage.POLYPECTOMY_DEATH,
            ]:
                self.disease_state = PersonDiseaseState.DEAD
                self.write_state_change(
                    message,
                    PersonDiseaseState.PRECLINICAL_STAGE1,
                    PersonDiseaseState.DEAD,
                )
                self.scheduler.add_event(message="end_simulation")
            else:
                pass
        elif self.disease_state == PersonDiseaseState.PRECLINICAL_STAGE2:
            if message == PersonDiseaseMessage.PRE3_ONSET:
                self.disease_state = PersonDiseaseState.PRECLINICAL_STAGE3
                self.write_state_change(
                    message,
                    PersonDiseaseState.PRECLINICAL_STAGE2,
                    PersonDiseaseState.PRECLINICAL_STAGE3,
                )
            elif message == PersonDiseaseMessage.CLINICAL_ONSET:
                self.disease_state = PersonDiseaseState.CLINICAL_STAGE2
                self.write_state_change(
                    message,
                    PersonDiseaseState.PRECLINICAL_STAGE2,
                    PersonDiseaseState.CLINICAL_STAGE2,
                )
                self.stage_at_detection = 2
                # when one cancer is detected then all cancers are detected
                self.detect_other_cancers()
                # Begin treatment
                self.scheduler.add_event(
                    message=PersonTreatmentMessage.START_TREATMENT,
                    handler=self.handle_treatment_message,
                )
            elif message in [
                PersonDiseaseMessage.OTHER_DEATH,
                PersonDiseaseMessage.POLYPECTOMY_DEATH,
            ]:
                self.disease_state = PersonDiseaseState.DEAD
                self.write_state_change(
                    message,
                    PersonDiseaseState.PRECLINICAL_STAGE2,
                    PersonDiseaseState.DEAD,
                )
                self.scheduler.add_event(message="end_simulation")
            else:
                pass
        elif self.disease_state == PersonDiseaseState.PRECLINICAL_STAGE3:
            if message == PersonDiseaseMessage.PRE4_ONSET:
                self.disease_state = PersonDiseaseState.PRECLINICAL_STAGE4
                self.write_state_change(
                    message,
                    PersonDiseaseState.PRECLINICAL_STAGE3,
                    PersonDiseaseState.PRECLINICAL_STAGE4,
                )
            elif message == PersonDiseaseMessage.CLINICAL_ONSET:
                self.disease_state = PersonDiseaseState.CLINICAL_STAGE3
                self.write_state_change(
                    message,
                    PersonDiseaseState.PRECLINICAL_STAGE3,
                    PersonDiseaseState.CLINICAL_STAGE3,
                )
                self.stage_at_detection = 3
                # when one cancer is detected then all cancers are detected
                self.detect_other_cancers()
                # Begin treatment
                self.scheduler.add_event(
                    message=PersonTreatmentMessage.START_TREATMENT,
                    handler=self.handle_treatment_message,
                )
            elif message in [
                PersonDiseaseMessage.OTHER_DEATH,
                PersonDiseaseMessage.POLYPECTOMY_DEATH,
            ]:
                self.disease_state = PersonDiseaseState.DEAD
                self.write_state_change(
                    message,
                    PersonDiseaseState.PRECLINICAL_STAGE3,
                    PersonDiseaseState.DEAD,
                )
                self.scheduler.add_event(message="end_simulation")
            else:
                pass
        elif self.disease_state == PersonDiseaseState.PRECLINICAL_STAGE4:
            if message == PersonDiseaseMessage.CLINICAL_ONSET:
                self.disease_state = PersonDiseaseState.CLINICAL_STAGE4
                self.write_state_change(
                    message,
                    PersonDiseaseState.PRECLINICAL_STAGE4,
                    PersonDiseaseState.CLINICAL_STAGE4,
                )
                self.stage_at_detection = 4
                # when one cancer is detected then all cancers are detected
                self.detect_other_cancers()
                # Begin treatment
                self.scheduler.add_event(
                    message=PersonTreatmentMessage.START_TREATMENT,
                    handler=self.handle_treatment_message,
                )
            elif message in [
                PersonDiseaseMessage.OTHER_DEATH,
                PersonDiseaseMessage.POLYPECTOMY_DEATH,
            ]:
                self.disease_state = PersonDiseaseState.DEAD
                self.write_state_change(
                    message,
                    PersonDiseaseState.PRECLINICAL_STAGE4,
                    PersonDiseaseState.DEAD,
                )
                self.scheduler.add_event(message="end_simulation")
            else:
                pass
        elif self.disease_state == PersonDiseaseState.CLINICAL_STAGE1:
            if message in [
                PersonDiseaseMessage.OTHER_DEATH,
                PersonDiseaseMessage.POLYPECTOMY_DEATH,
            ]:
                self.disease_state = PersonDiseaseState.DEAD
                self.write_state_change(
                    message, PersonDiseaseState.CLINICAL_STAGE1, PersonDiseaseState.DEAD
                )
                self.scheduler.add_event(message="end_simulation")
            elif message == PersonDiseaseMessage.CRC_DEATH:
                self.disease_state = PersonDiseaseState.DEAD
                self.write_state_change(
                    message, PersonDiseaseState.CLINICAL_STAGE1, PersonDiseaseState.DEAD
                )
                self.scheduler.add_event(message="end_simulation")
                self.out.add_treatment(
                    person_id=self.id,
                    stage=self.stage_at_detection,
                    role=TreatmentRole.TERMINAL,
                    time=self.scheduler.time,
                )
            else:
                pass
        elif self.disease_state == PersonDiseaseState.CLINICAL_STAGE2:
            if message in [
                PersonDiseaseMessage.OTHER_DEATH,
                PersonDiseaseMessage.POLYPECTOMY_DEATH,
            ]:
                self.disease_state = PersonDiseaseState.DEAD
                self.write_state_change(
                    message, PersonDiseaseState.CLINICAL_STAGE2, PersonDiseaseState.DEAD
                )
                self.scheduler.add_event(message="end_simulation")
            elif message == PersonDiseaseMessage.CRC_DEATH:
                self.disease_state = PersonDiseaseState.DEAD
                self.write_state_change(
                    message, PersonDiseaseState.CLINICAL_STAGE2, PersonDiseaseState.DEAD
                )
                self.scheduler.add_event(message="end_simulation")
                self.out.add_treatment(
                    person_id=self.id,
                    stage=self.stage_at_detection,
                    role=TreatmentRole.TERMINAL,
                    time=self.scheduler.time,
                )
            else:
                pass
        elif self.disease_state == PersonDiseaseState.CLINICAL_STAGE3:
            if message in [
                PersonDiseaseMessage.OTHER_DEATH,
                PersonDiseaseMessage.POLYPECTOMY_DEATH,
            ]:
                self.disease_state = PersonDiseaseState.DEAD
                self.write_state_change(
                    message, PersonDiseaseState.CLINICAL_STAGE3, PersonDiseaseState.DEAD
                )
                self.scheduler.add_event(message="end_simulation")
            elif message == PersonDiseaseMessage.CRC_DEATH:
                self.disease_state = PersonDiseaseState.DEAD
                self.write_state_change(
                    message, PersonDiseaseState.CLINICAL_STAGE3, PersonDiseaseState.DEAD
                )
                self.scheduler.add_event(message="end_simulation")
                self.out.add_treatment(
                    person_id=self.id,
                    stage=self.stage_at_detection,
                    role=TreatmentRole.TERMINAL,
                    time=self.scheduler.time,
                )
            else:
                pass
        elif self.disease_state == PersonDiseaseState.CLINICAL_STAGE4:
            if message in [
                PersonDiseaseMessage.OTHER_DEATH,
                PersonDiseaseMessage.POLYPECTOMY_DEATH,
            ]:
                self.disease_state = PersonDiseaseState.DEAD
                self.write_state_change(
                    message, PersonDiseaseState.CLINICAL_STAGE4, PersonDiseaseState.DEAD
                )
                self.scheduler.add_event(message="end_simulation")
            elif message == PersonDiseaseMessage.CRC_DEATH:
                self.disease_state = PersonDiseaseState.DEAD
                self.write_state_change(
                    message, PersonDiseaseState.CLINICAL_STAGE4, PersonDiseaseState.DEAD
                )
                self.scheduler.add_event(message="end_simulation")
                self.out.add_treatment(
                    person_id=self.id,
                    stage=self.stage_at_detection,
                    role=TreatmentRole.TERMINAL,
                    time=self.scheduler.time,
                )
            else:
                pass
        elif self.disease_state == PersonDiseaseState.DEAD:
            pass
        else:
            raise ValueError(f"Unexpected disease state {self.disease_state}")

    def handle_testing_message(self, message):
        if self.testing_state == PersonTestingState.UNINITIALIZED:
            if message == PersonTestingMessage.INIT:
                self.testing_state = PersonTestingState.ROUTINE
            else:
                raise ValueError(
                    f"Received unexpected message {message} in testing state {self.testing_state}"
                )
        elif self.testing_state == PersonTestingState.ROUTINE:
            if message == PersonTestingMessage.SYMPTOMATIC:
                self.testing_state = PersonTestingState.DIAGNOSTIC
                self.test_diagnostic(symptomatic=True)
            elif message == PersonTestingMessage.SCREEN_POSITIVE:
                self.testing_state = PersonTestingState.DIAGNOSTIC
                self.test_diagnostic()
            elif message == PersonTestingMessage.ROUTINE_IS_DIAGNOSTIC:
                self.testing_state = PersonTestingState.DIAGNOSTIC
                self.routine_is_diagnostic = True
                self.test_diagnostic()
            else:
                pass
        elif self.testing_state == PersonTestingState.DIAGNOSTIC:
            if message == PersonTestingMessage.NEGATIVE:
                self.testing_state = PersonTestingState.SKIP_TESTING
                self.routine_is_diagnostic = False
                self.testing_transition_timeout_event = self.scheduler.add_event(
                    message=PersonTestingMessage.RETURN_TO_ROUTINE,
                    handler=self.handle_testing_message,
                    delay=self.params["duration_screen_skip_testing"],
                )
            elif message == PersonTestingMessage.NOT_COMPLIANT:
                self.testing_state = PersonTestingState.ROUTINE
                self.routine_is_diagnostic = False
            elif message == PersonTestingMessage.POSITIVE_POLYP:
                self.testing_state = PersonTestingState.SURVEILLANCE
                self.num_surveillance_tests_since_positive = 0
                self.routine_is_diagnostic = False
            elif message == PersonTestingMessage.POSITIVE_CANCER:
                self.testing_state = PersonTestingState.SURVEILLANCE
                self.num_surveillance_tests_since_positive = 0
                self.routine_is_diagnostic = False
            else:
                pass
        elif self.testing_state == PersonTestingState.SKIP_TESTING:
            if message == PersonTestingMessage.SYMPTOMATIC:
                # When exiting a state with a timeout transition, always disable the
                # timeout event to avoid acting on stale messages.
                self.testing_transition_timeout_event.enabled = False

                self.testing_state = PersonTestingState.DIAGNOSTIC
                self.test_diagnostic(symptomatic=True)
            elif message == PersonTestingMessage.RETURN_TO_ROUTINE:
                # When exiting a state with a timeout transition, always disable the
                # timeout event to avoid acting on stale messages.
                self.testing_transition_timeout_event.enabled = False

                self.testing_state = PersonTestingState.ROUTINE
            else:
                pass
        elif self.testing_state == PersonTestingState.SURVEILLANCE:
            if message == PersonTestingMessage.SYMPTOMATIC:
                self.testing_state = PersonTestingState.SURVEILLANCE
                self.test_surveillance(symptomatic=True)
            elif message == PersonTestingMessage.POSITIVE_POLYP:
                self.testing_state = PersonTestingState.SURVEILLANCE
                self.num_surveillance_tests_since_positive = 0
            elif message == PersonTestingMessage.POSITIVE_CANCER:
                self.testing_state = PersonTestingState.SURVEILLANCE
                self.num_surveillance_tests_since_positive = 0
                # Even if the person is in surveillance because they already have cancer,
                # we restart the treatment protocol when a new cancer is detected.
                self.scheduler.add_event(
                    message=PersonTreatmentMessage.START_TREATMENT,
                    handler=self.handle_treatment_message,
                )
            else:
                pass
        else:
            raise ValueError(f"Unexpected testing state {self.testing_state}")

    def handle_treatment_message(self, message):
        if self.treatment_state == PersonTreatmentState.UNINITIALIZED:
            if message == PersonTreatmentMessage.INIT:
                self.treatment_state = PersonTreatmentState.NO_TREATMENT
            else:
                raise ValueError(
                    f"Received unexpected message {message} in treatment state {self.treatment_state}"
                )
        elif self.treatment_state == PersonTreatmentState.NO_TREATMENT:
            if message == PersonTreatmentMessage.START_TREATMENT:
                self.treatment_state = PersonTreatmentState.TREATMENT
                self.out.add_treatment(
                    person_id=self.id,
                    stage=self.stage_at_detection,
                    role=TreatmentRole.INITIAL,
                    time=self.scheduler.time,
                )
                self.previous_treatment_initiation_age = int(self.scheduler.time)
                self.num_ongoing_treatments = 0
                self.ongoing_treatment_event = self.scheduler.add_event(
                    message="Ongoing treatment",
                    handler=self.handle_ongoing_treatment,
                    delay=1,
                )
            else:
                pass
        elif self.treatment_state == PersonTreatmentState.TREATMENT:
            if message == PersonTreatmentMessage.START_TREATMENT:
                # We're starting a new treatment series, so cancel any existing
                # one first.
                self.ongoing_treatment_event.enabled = False

                self.treatment_state = PersonTreatmentState.TREATMENT
                self.out.add_treatment(
                    person_id=self.id,
                    stage=self.stage_at_detection,
                    role=TreatmentRole.INITIAL,
                    time=self.scheduler.time,
                )
                self.previous_treatment_initiation_age = int(self.scheduler.time)
                self.num_ongoing_treatments = 0
                self.ongoing_treatment_event = self.scheduler.add_event(
                    message="Ongoing treatment",
                    handler=self.handle_ongoing_treatment,
                    delay=1,
                )
            else:
                pass
        else:
            raise ValueError(f"Unexpected treatment state {self.treatment_state}")

    def compute_lesion_delay(self):
        """
        Return the time delay between now and when the next lesion appears.

        The algorithm requires a few variables to be assigned before calling
        this method:
          - self.lesion_risk_index
          - self.previous_lesion_onset_time
          - self.expected_lifespan
        """

        # The algorithm is based on the lesion incidence curve and a random
        # number. The random number corresponds to an area under the curve (the
        # "target area"). Starting at the point on the curve where the previous
        # lesion appeared, we move forward until the area between the points
        # equals the target area. This new point is the time when the next lesion
        # appears.
        #
        # This function is based on the Erasmus MISCAN-COLON paper, Chapter 2,
        # Appendix A. The notation is mapped from the paper to this code as
        # follows:
        #
        #   R_i = self.lesion_risk_index
        #   a = next_onset_time
        #   a_0 = self.previous_lesion_onset_time
        #   h_i(a) = incidence(a)
        #   integral(h_i(x), x = a_0 to a) = target_area
        #   u = u
        #
        # The goal of this function is to find the value of a that satisfies the
        # equation:
        #
        #   u = 1 - exp[-H_i(a,a_0)]
        #
        # where
        #
        #   H_i(a,a_0) = R_i * integral(h_i(x), x = a_0 to a)

        incidence = self.params["lesion_incidence"]

        # Compute the target area. This equation was obtained by rearranging the
        # equations listed in the description at the beginning of this function.

        u = self.rng.random()
        target_area = -math.log(1 - u) / self.lesion_risk_index

        # Move along the incidence curve until the area between the previous
        # onset time and the current point equals the target area. That point
        # will be the next onset time. If we get to the end of the incidence
        # curve without reaching the target area, then the person doesn't
        # contract another lesion.
        #
        # Because our incidence curve is a step function, calculating the area
        # under the curve involves summing the areas of a series of boxes. The
        # boxes are defined by the steps in the function. The width of each box
        # is the distance between the start and end times for that step, and the
        # height of each box is the incidence at the start time. The first and
        # last boxes likely will represent only a partial step, because the
        # lesion onset times are unlikely to fall directly on step boundaries.

        cumulative_area = 0
        box_start_time = self.previous_lesion_onset_time

        while True:
            # The end time for this box is the next time defined in the incidence
            # step function.
            box_end_index = bisect.bisect_right(incidence.x, box_start_time)

            # If there are no more steps in the incidence curve, then we won't
            # be able to accumulate the target area. This means the person's
            # next lesion won't appear until after they're dead. In other words,
            # there won't be a next lesion. (This assumes that the incidence
            # curve extends far enough to cover their potential lifespan.)
            if box_end_index >= len(incidence.x):
                return None

            box_end_time = incidence.x[box_end_index]

            # Compute the area of this box, and add it to to the cumulative area.
            box_height = incidence(box_start_time)
            box_area = (box_end_time - box_start_time) * box_height
            cumulative_area += box_area

            # If the cumulative area has surpassed the target area, we know
            # next_onset_time is somewhere between start and end, and therefore
            # this is the last box we need to process.
            if cumulative_area >= target_area:
                # The box is likely too big, meaning the cumulative area is
                # larger than the target area. We must shrink the box by
                # lowering the end point such that the cumulative area matches
                # the target area exactly. The new end of the box is the time
                # when the next lesion occurs.
                excess_area = cumulative_area - target_area
                excess_width = excess_area / box_height
                next_onset_time = box_end_time - excess_width

                if next_onset_time <= self.expected_lifespan:
                    return next_onset_time - self.scheduler.time
                else:
                    # The next lesion won't appear until after the person is
                    # dead, so there won't be a next lesion.
                    return None

            # We haven't reached the target area yet, so prepare for the next
            # box.
            box_start_time = box_end_time

    def handle_lesion_creation(self, message="Create lesion"):
        self.lesions.append(
            Lesion(
                scheduler=self.scheduler,
                params=self.params,
                person=self,
                rng=self.rng,
                out=self.out,
            ),
        )

        self.previous_lesion_onset_time = self.scheduler.time

        lesion_delay = self.compute_lesion_delay()
        if lesion_delay is not None:
            self.scheduler.add_event(
                message=message,
                handler=self.handle_lesion_creation,
                delay=lesion_delay,
            )

    def write_state_change(self, message, old_state, new_state):
        self.out.add_disease_state_change(
            person_id=self.id,
            message=message,
            time=self.scheduler.time,
            old_state=old_state,
            new_state=new_state,
            routine_test=self.routine_test,
        )

    def detect_other_cancers(self):
        for lesion in self.lesions:
            if lesion.state in [
                LesionState.PRECLINICAL_STAGE1,
                LesionState.PRECLINICAL_STAGE2,
                LesionState.PRECLINICAL_STAGE3,
                LesionState.PRECLINICAL_STAGE4,
            ]:
                self.scheduler.add_event(
                    message=LesionMessage.CLINICAL_DETECTION,
                    handler=lesion.handle_message,
                )
            else:
                pass

    # skipping add_lesion as we are using wake_lesion_creator() instead

    def choose_tests(self):
        # There's a choice only for routine tests, but we assign diagnostic
        # and surveillance tests here as well to keep all in one place.
        self.diagnostic_test = self.params["diagnostic_test"]
        self.surveillance_test = self.params["surveillance_test"]

        if self.params["use_variable_routine_test"]:
            # If the simulation is using variable routine tests, then we do not pick
            # a single routine test for each person. Instead, we will refer to the
            # routine_testing_year and routine_test_by_year parameters to determine
            # which test to use each year. This allows a person to switch tests during
            # their lifetime. We still assign the routine_test attribute here to
            # avoid errors from yearly actions that expect a person to have a routine
            # test attribute.
            starting_test = self.params["routine_test_by_year"][0]
            self.routine_test = starting_test
            self.out.add_routine_test_chosen(
                person_id=self.id,
                test_name=starting_test,
                time=self.scheduler.time,
            )
            return

        # Choose the routine test based on proportions specified in
        # parameters file.
        #
        # First, create a dict containing the probability for each test.
        # Ensure that the sum of all test probabilities <= 1.
        distribution = {}
        direct_prob = 0

        for test in self.params["tests"]:
            proportion = self.params["tests"][test]["proportion"]
            direct_prob += proportion
            distribution[test] = proportion

        if direct_prob > 1:
            raise ValueError(f"Sum of test probabilities {direct_prob} > 1")

        # Randomly choose which routine test this person will take.
        # Start out with None - if the distribution sums to less than 1,
        # the person might not be assigned to any test.
        self.routine_test = None

        rand = self.rng.random()
        cumulative_distribution = 0

        for test, proportion in distribution.items():
            cumulative_distribution += proportion
            if rand < cumulative_distribution:
                self.routine_test = test
                self.out.add_routine_test_chosen(
                    person_id=self.id,
                    test_name=test,
                    time=self.scheduler.time,
                )
                break

    # skipping discount_age as it is used only for summary stats
    # will calculate in analysis script

    # exhibit_symptoms is a one-liner and can probably be included
    # as part of Lesion's symptoms timer

    def is_compliant(self, test: str):
        if test is None:
            return False
        if (
            self.testing_state == PersonTestingState.DIAGNOSTIC
            and not self.routine_is_diagnostic
        ):
            return self.rng.random() < self.params["diagnostic_compliance_rate"]
        elif self.testing_state == PersonTestingState.SURVEILLANCE:
            return self.rng.random() < self.params["surveillance_compliance_rate"]
        elif self.testing_state == PersonTestingState.ROUTINE or (
            self.testing_state == PersonTestingState.DIAGNOSTIC
            and self.routine_is_diagnostic
        ):
            # Determine routine testing compliance probability.
            # First, if the person is never compliant, set to zero.
            # If this is the first time the person has been eligible for a routine test
            # or if we are using unconditional compliance, use the rules for initial
            # compliance. Otherwise use the rules for conditional compliance.
            if self.never_compliant:
                compliance_prob = 0
            elif (
                self.params["use_conditional_compliance"] is True
                and len(self.routine_compliance_history) == 0
            ) or self.params["use_conditional_compliance"] is False:
                compliance_prob = self.params["initial_compliance_rate"]
                # The initial compliance rate parameter is intended to be a probability
                # based on the entire population. Here we adjust this population
                # probability to the conditional probability that the person is compliant
                # given that they are not "never compliant".
                if self.params["never_compliant_rate"] < 1:
                    compliance_prob = compliance_prob / (
                        1 - self.params["never_compliant_rate"]
                    )
                    # This adjustment may result in compliance probabilities > 1.
                    # If so, adjust to 1.
                    if compliance_prob > 1:
                        compliance_prob = 1
                else:
                    compliance_prob = 0
            else:
                # We are using conditional compliance and the person has been eligible
                # for routine testing before, so we use the rules for conditional
                # compliance. In the parameters file, conditional compliance probabilities
                # are specified for each age between the test's routine start and end age.
                # We select the person's compliance probability based on their age and
                # whether they were compliant the last time they were eligible.
                test_params = self.params["tests"][self.routine_test]
                testing_year = int(self.scheduler.time - test_params["routine_start"])
                if testing_year < 0 or testing_year > (
                    test_params["routine_end"] - test_params["routine_start"]
                ):
                    raise ValueError(
                        f"Unexpected age {self.scheduler.time} resulting in testing year {testing_year}"
                    )
                if self.routine_compliance_history[-1] is True:
                    compliance_prob = test_params[
                        "compliance_rate_given_prev_compliant"
                    ][testing_year]
                else:
                    compliance_prob = test_params[
                        "compliance_rate_given_not_prev_compliant"
                    ][testing_year]

            # Return a random indicator of whether the person complied.
            if self.rng.random() < compliance_prob:
                self.routine_compliance_history.append(True)
                return True
            else:
                self.routine_compliance_history.append(False)
                return False
        else:
            raise ValueError(f"Unexpected testing state {self.testing_state}")

    def is_false_positive(self, test: str):
        if test is None:
            return False
        else:
            fp = self.rng.random() < 1 - self.params["tests"][test]["specificity"]
            return fp

    # on_end_year is just a wrapper for update_value - not necessary as far as I can tell

    def compute_lifespan(self) -> float:
        """
        Return a randomly-computed lifespan based on the death rate parameters.
        """

        rand = self.rng.random()
        cum_prob_survive = 1.0
        cum_prob_death = 0.0

        # Find the appropriate death rate table. We don't have separate tables
        # for all combinations of sex and race_ethnicity, so we'll need to do
        # some imperfect combining of categories.
        if self.sex == Sex.FEMALE:
            if self.race_ethnicity == RaceEthnicity.WHITE_NON_HISPANIC:
                death_rate = self.params["death_rate_white_female"]
            elif self.race_ethnicity in (
                RaceEthnicity.HISPANIC,
                RaceEthnicity.BLACK_NON_HISPANIC,
                RaceEthnicity.OTHER_NON_HISPANIC,
            ):
                death_rate = self.params["death_rate_black_female"]
            else:
                raise ValueError(
                    f"Unexpected race/ethnicity value: {self.race_ethnicity}"
                )
        elif self.sex in (Sex.MALE, Sex.OTHER):
            if self.race_ethnicity == RaceEthnicity.WHITE_NON_HISPANIC:
                death_rate = self.params["death_rate_white_male"]
            elif self.race_ethnicity in (
                RaceEthnicity.HISPANIC,
                RaceEthnicity.BLACK_NON_HISPANIC,
                RaceEthnicity.OTHER_NON_HISPANIC,
            ):
                death_rate = self.params["death_rate_black_male"]
            else:
                raise ValueError(
                    f"Unexpected race/ethnicity value: {self.race_ethnicity}"
                )
        else:
            raise ValueError(f"Unexpected sex value: {self.sex}")

        # Move through the death table, searching for the age at which the
        # person's cumulative probability of death exceeds the random number we
        # generated. This is the age when the person will die.
        found_lifespan = False

        for i in range(self.params["max_age"] + 1):
            cond_prob_death = death_rate(i)
            prob_death = cond_prob_death * cum_prob_survive
            cum_prob_death += prob_death
            cum_prob_survive *= 1 - cond_prob_death
            if rand < cum_prob_death:
                # Calculate the lifespan as the current year plus the fraction that
                # the random number slips into the next year.
                lifespan = i + 1 - ((cum_prob_death - rand) / prob_death)
                found_lifespan = True
                break

        # If we went through the death table without finding a lifespan (this
        # can happen if the max age is less than the upper bound of the death
        # table, for example), set the lifespan to the max age.
        if not found_lifespan:
            lifespan = self.params["max_age"]

        # Just in case, cap the lifespan at the max age.
        if lifespan > self.params["max_age"]:
            lifespan = self.params["max_age"]

        return lifespan

    def start_life_timer(self):
        self.expected_lifespan = self.compute_lifespan()
        self.scheduler.add_event(
            message=PersonDiseaseMessage.OTHER_DEATH,
            handler=self.handle_disease_message,
            delay=self.expected_lifespan,
        )
        self.out.add_expected_lifespan(
            person_id=self.id,
            time=self.expected_lifespan,
        )

    def test_diagnostic(self, symptomatic: bool = False):
        if (
            self.testing_state == PersonTestingState.DIAGNOSTIC
            and self.disease_state
            not in [
                PersonDiseaseState.CLINICAL_STAGE1,
                PersonDiseaseState.CLINICAL_STAGE2,
                PersonDiseaseState.CLINICAL_STAGE3,
                PersonDiseaseState.CLINICAL_STAGE4,
                PersonDiseaseState.DEAD,
            ]
        ):
            role = (
                TestingRole.ROUTINE
                if self.routine_is_diagnostic
                else TestingRole.DIAGNOSTIC
            )
            if self.is_compliant(test=self.diagnostic_test) or symptomatic is True:
                test_params = self.params["tests"][self.diagnostic_test]

                self.out.add_test_performed(
                    person_id=self.id,
                    test_name=self.diagnostic_test,
                    role=role,
                    time=self.scheduler.time,
                )
                self.previous_test_age[self.diagnostic_test] = int(self.scheduler.time)

                num_detected_lesions = 0
                num_detected_polyps = 0
                num_detected_polyps_small = 0
                num_detected_polyps_medium = 0
                num_detected_polyps_large = 0
                num_detected_cancer = 0

                # We assume that a false positive leads to pathology and polypectomy.
                # We further assume that these procedures reveal the person has no polyps.
                # Therefore, we apply the cost of the procedures but report a negative
                # result. Pathology cost is designed to be applied per-polyp. Since
                # the person has no polyps, we apply cost as if they had one polyp.
                # Finally, we check if the polypectomy was lethal.
                if self.disease_state == PersonDiseaseState.HEALTHY:
                    if self.is_false_positive(test=self.diagnostic_test):
                        self.out.add_pathology(
                            person_id=self.id,
                            lesion_id=-1,
                            role=role,
                            time=self.scheduler.time,
                        )
                        self.out.add_polypectomy(
                            person_id=self.id,
                            role=role,
                            time=self.scheduler.time,
                        )
                        if (
                            self.rng.random()
                            < self.params["polypectomy_proportion_lethal"]
                        ):
                            self.scheduler.add_event(
                                message=PersonDiseaseMessage.POLYPECTOMY_DEATH,
                                handler=self.handle_disease_message,
                            )
                            return
                    self.scheduler.add_event(
                        message=PersonTestingMessage.NEGATIVE,
                        handler=self.handle_testing_message,
                    )
                else:
                    # Cycle through each lesion, doing the following for each:
                    # 1. Check whether the lesion is detected.
                    # 2. If detected, send a clinical detection message.
                    # 3. If detected, store the lesion's state in tracking variables.
                    for lesion in self.lesions:
                        if lesion.is_detected(test=self.diagnostic_test):
                            if lesion.state == LesionState.SMALL_POLYP:
                                num_detected_lesions += 1
                                num_detected_polyps += 1
                                num_detected_polyps_small += 1
                                # Pathology cost is per polyp, so we add within the loop
                                self.out.add_pathology(
                                    person_id=self.id,
                                    lesion_id=lesion.id,
                                    role=role,
                                    time=self.scheduler.time,
                                )
                            elif lesion.state == LesionState.MEDIUM_POLYP:
                                num_detected_lesions += 1
                                num_detected_polyps += 1
                                num_detected_polyps_medium += 1
                                self.out.add_pathology(
                                    person_id=self.id,
                                    lesion_id=lesion.id,
                                    role=role,
                                    time=self.scheduler.time,
                                )
                            elif lesion.state == LesionState.LARGE_POLYP:
                                num_detected_lesions += 1
                                num_detected_polyps += 1
                                num_detected_polyps_large += 1
                                self.out.add_pathology(
                                    person_id=self.id,
                                    lesion_id=lesion.id,
                                    role=role,
                                    time=self.scheduler.time,
                                )
                            elif lesion.state in [
                                LesionState.PRECLINICAL_STAGE1,
                                LesionState.PRECLINICAL_STAGE2,
                                LesionState.PRECLINICAL_STAGE3,
                                LesionState.PRECLINICAL_STAGE4,
                            ]:
                                num_detected_lesions += 1
                                num_detected_cancer += 1
                            else:
                                raise ValueError(
                                    f"Unexpected lesion state {lesion.state}"
                                )
                            self.scheduler.add_event(
                                message=LesionMessage.CLINICAL_DETECTION,
                                handler=lesion.handle_message,
                            )

                    # Check if any polyps were detected. If so, add cost of polypectomy.
                    # Polypectomy cost is added only once, not per polyp. This assumes
                    # clinical detection of a polyp always results in polypectomy. We
                    # also check if the polypectomy was lethal.
                    if num_detected_polyps > 0:
                        self.out.add_polypectomy(
                            person_id=self.id,
                            role=role,
                            time=self.scheduler.time,
                        )
                        if (
                            self.rng.random()
                            < self.params["polypectomy_proportion_lethal"]
                        ):
                            self.scheduler.add_event(
                                message=PersonDiseaseMessage.POLYPECTOMY_DEATH,
                                handler=self.handle_disease_message,
                            )
                            return

                    # Schedule an event based on the set of results. After checking
                    # for any elements in the vector, we go in descending order of
                    # "badness" because we want the fired event to represent the
                    # most developed lesion.
                    if num_detected_lesions == 0:
                        self.scheduler.add_event(
                            message=PersonTestingMessage.NEGATIVE,
                            handler=self.handle_testing_message,
                        )
                    elif num_detected_cancer > 0:
                        self.scheduler.add_event(
                            message=PersonTestingMessage.POSITIVE_CANCER,
                            handler=self.handle_testing_message,
                        )
                    elif num_detected_polyps > 0:
                        self.scheduler.add_event(
                            message=PersonTestingMessage.POSITIVE_POLYP,
                            handler=self.handle_testing_message,
                        )
                    else:
                        raise ValueError("Unexpected set of diagnostic test results")
                        # NOTE: did not copy negative test event here from AL as the
                        # ValueError will halt execution in Python.

                # Store number of polyps found by size. These counts influence how
                # soon the person needs to be retested.
                self.previous_test_small[
                    self.diagnostic_test
                ] = num_detected_polyps_small
                self.previous_test_medium[
                    self.diagnostic_test
                ] = num_detected_polyps_medium
                self.previous_test_large[
                    self.diagnostic_test
                ] = num_detected_polyps_large

                # check whether test resulted in perforation
                if self.rng.random() < test_params["proportion_perforation"]:
                    self.out.add_perforation(
                        person_id=self.id,
                        test_name=self.diagnostic_test,
                        role=role,
                        time=self.scheduler.time,
                        routine_test=self.routine_test,
                    )
            else:
                self.scheduler.add_event(
                    message=PersonTestingMessage.NOT_COMPLIANT,
                    handler=self.handle_testing_message,
                )
                self.out.add_noncompliance(
                    person_id=self.id,
                    test_name=self.diagnostic_test,
                    role=role,
                    time=self.scheduler.time,
                )

    def test_routine(self):
        if (
            self.testing_state == PersonTestingState.ROUTINE
            and self.disease_state
            not in [
                PersonDiseaseState.CLINICAL_STAGE1,
                PersonDiseaseState.CLINICAL_STAGE2,
                PersonDiseaseState.CLINICAL_STAGE3,
                PersonDiseaseState.CLINICAL_STAGE4,
                PersonDiseaseState.DEAD,
            ]
        ):
            # if the test used for routine screening is the same as for diagnostic,
            # go straight to the actions of the diagnostic test.
            if self.routine_test == self.diagnostic_test:
                self.scheduler.add_event(
                    message=PersonTestingMessage.ROUTINE_IS_DIAGNOSTIC,
                    handler=self.handle_testing_message,
                )
            else:
                if self.is_compliant(test=self.routine_test):
                    test_params = self.params["tests"][self.routine_test]

                    self.out.add_test_performed(
                        person_id=self.id,
                        test_name=self.routine_test,
                        role=TestingRole.ROUTINE,
                        time=self.scheduler.time,
                    )
                    self.previous_test_age[self.routine_test] = int(self.scheduler.time)

                    # if person is healthy, then positive result is false positive
                    if self.disease_state == PersonDiseaseState.HEALTHY:
                        if self.is_false_positive(test=self.routine_test):
                            self.scheduler.add_event(
                                message=PersonTestingMessage.SCREEN_POSITIVE,
                                handler=self.handle_testing_message,
                            )

                    # check each lesion for detection
                    elif self.disease_state in [
                        PersonDiseaseState.SMALL_POLYP,
                        PersonDiseaseState.MEDIUM_POLYP,
                        PersonDiseaseState.LARGE_POLYP,
                        PersonDiseaseState.PRECLINICAL_STAGE1,
                        PersonDiseaseState.PRECLINICAL_STAGE2,
                        PersonDiseaseState.PRECLINICAL_STAGE3,
                        PersonDiseaseState.PRECLINICAL_STAGE4,
                    ]:
                        for lesion in self.lesions:
                            if lesion.is_detected(test=self.routine_test):
                                self.scheduler.add_event(
                                    message=PersonTestingMessage.SCREEN_POSITIVE,
                                    handler=self.handle_testing_message,
                                )
                                # once we've found one, don't need to check the rest.
                                # positive/negative is all we need to know.
                                break

                    # check whether test resulted in perforation
                    if self.rng.random() < test_params["proportion_perforation"]:
                        self.out.add_perforation(
                            person_id=self.id,
                            test=self.routine_test,
                            role=TestingRole.ROUTINE,
                            time=self.scheduler.time,
                            routine_test=self.routine_test,
                        )
                else:
                    self.out.add_noncompliance(
                        person_id=self.id,
                        test_name=self.routine_test,
                        role=TestingRole.ROUTINE,
                        time=self.scheduler.time,
                    )

    def test_surveillance(self, symptomatic: bool = False):
        if (
            self.testing_state == PersonTestingState.SURVEILLANCE
            and self.disease_state != PersonDiseaseState.DEAD
        ):
            if self.is_compliant(test=self.surveillance_test) or symptomatic is True:
                test_params = self.params["tests"][self.surveillance_test]

                self.out.add_test_performed(
                    person_id=self.id,
                    test_name=self.surveillance_test,
                    role=TestingRole.SURVEILLANCE,
                    time=self.scheduler.time,
                )
                self.previous_test_age[self.surveillance_test] = int(
                    self.scheduler.time
                )
                self.num_surveillance_tests_since_positive += 1

                num_detected_lesions = 0
                num_detected_polyps = 0
                num_detected_polyps_small = 0
                num_detected_polyps_medium = 0
                num_detected_polyps_large = 0
                num_detected_cancer = 0

                # We assume that a false positive leads to pathology and polypectomy.
                # We further assume that these procedures reveal the person has no polyps.
                # Therefore, we apply the cost of the procedures but report a negative
                # result. Pathology cost is designed to be applied per-polpy. Since
                # the person has no polyps, we apply cost as if they had one polyp.
                # Finally, we check if the polypectomy was lethal.
                if self.disease_state == PersonDiseaseState.HEALTHY:
                    if self.is_false_positive(test=self.surveillance_test):
                        self.out.add_pathology(
                            person_id=self.id,
                            lesion_id=-1,
                            role=TestingRole.SURVEILLANCE,
                            time=self.scheduler.time,
                        )
                        self.out.add_polypectomy(
                            person_id=self.id,
                            role=TestingRole.SURVEILLANCE,
                            time=self.scheduler.time,
                        )
                        if (
                            self.rng.random()
                            < self.params["polypectomy_proportion_lethal"]
                        ):
                            self.scheduler.add_event(
                                message=PersonDiseaseMessage.POLYPECTOMY_DEATH,
                                handler=self.handle_disease_message,
                            )
                            return
                    self.scheduler.add_event(
                        message=PersonTestingMessage.NEGATIVE,
                        handler=self.handle_testing_message,
                    )
                else:
                    # Cycle through each lesion, doing the following for each:
                    # 1. Check whether the lesion is detected.
                    # 2. If detected, send a clinical detection message.
                    # 3. If detected, store the lesion's state in tracking variables.
                    for lesion in self.lesions:
                        if lesion.is_detected(test=self.surveillance_test):
                            if lesion.state == LesionState.SMALL_POLYP:
                                num_detected_lesions += 1
                                num_detected_polyps += 1
                                num_detected_polyps_small += 1
                                # Pathology cost is per polyp, so we add within the loop
                                self.out.add_pathology(
                                    person_id=self.id,
                                    lesion_id=lesion.id,
                                    role=TestingRole.SURVEILLANCE,
                                    time=self.scheduler.time,
                                )
                            elif lesion.state == LesionState.MEDIUM_POLYP:
                                num_detected_lesions += 1
                                num_detected_polyps += 1
                                num_detected_polyps_medium += 1
                                self.out.add_pathology(
                                    person_id=self.id,
                                    lesion_id=lesion.id,
                                    role=TestingRole.SURVEILLANCE,
                                    time=self.scheduler.time,
                                )
                            elif lesion.state == LesionState.LARGE_POLYP:
                                num_detected_lesions += 1
                                num_detected_polyps += 1
                                num_detected_polyps_large += 1
                                self.out.add_pathology(
                                    person_id=self.id,
                                    lesion_id=lesion.id,
                                    role=TestingRole.SURVEILLANCE,
                                    time=self.scheduler.time,
                                )
                            elif lesion.state in [
                                LesionState.PRECLINICAL_STAGE1,
                                LesionState.PRECLINICAL_STAGE2,
                                LesionState.PRECLINICAL_STAGE3,
                                LesionState.PRECLINICAL_STAGE4,
                            ]:
                                num_detected_lesions += 1
                                num_detected_cancer += 1
                            elif lesion.state in [
                                LesionState.CLINICAL_STAGE1,
                                LesionState.CLINICAL_STAGE2,
                                LesionState.CLINICAL_STAGE3,
                                LesionState.CLINICAL_STAGE4,
                            ]:
                                # We don't need to do anything about cancers that are already known.
                                pass
                            else:
                                raise ValueError(
                                    f"Unexpected lesion state {lesion.state}"
                                )
                            self.scheduler.add_event(
                                message=LesionMessage.CLINICAL_DETECTION,
                                handler=lesion.handle_message,
                            )

                    # Check if any polyps were detected. If so, add cost of polypectomy.
                    # Polypectomy cost is added only once, not per polyp. This assumes
                    # clinical detection of a polyp always results in polypectomy. We
                    # also check if the polypectomy was lethal.
                    if num_detected_polyps > 0:
                        self.out.add_polypectomy(
                            person_id=self.id,
                            role=TestingRole.SURVEILLANCE,
                            time=self.scheduler.time,
                        )
                        if (
                            self.rng.random()
                            < self.params["polypectomy_proportion_lethal"]
                        ):
                            self.scheduler.add_event(
                                message=PersonDiseaseMessage.POLYPECTOMY_DEATH,
                                handler=self.handle_disease_message,
                            )
                            return

                    # Schedule an event based on the set of results. After checking
                    # for any elements in the vector, we go in descending order of
                    # "badness" because we want the fired event to represent the
                    # most developed lesion.
                    if num_detected_lesions == 0:
                        self.scheduler.add_event(
                            message=PersonTestingMessage.NEGATIVE,
                            handler=self.handle_testing_message,
                        )
                    elif num_detected_cancer > 0:
                        self.scheduler.add_event(
                            message=PersonTestingMessage.POSITIVE_CANCER,
                            handler=self.handle_testing_message,
                        )
                    elif num_detected_polyps > 0:
                        self.scheduler.add_event(
                            message=PersonTestingMessage.POSITIVE_POLYP,
                            handler=self.handle_testing_message,
                        )
                    else:
                        raise ValueError("Unexpected set of surveillance test results")
                        # NOTE: did not copy negative test event here from AL as the
                        # ValueError will halt execution in Python.

                # Store number of polyps found by size. These counts influence how
                # soon the person needs to be retested.
                self.previous_test_small[
                    self.surveillance_test
                ] = num_detected_polyps_small
                self.previous_test_medium[
                    self.surveillance_test
                ] = num_detected_polyps_medium
                self.previous_test_large[
                    self.surveillance_test
                ] = num_detected_polyps_large

                # check whether test resulted in perforation
                if self.rng.random() < test_params["proportion_perforation"]:
                    self.out.add_perforation(
                        person_id=self.id,
                        test_name=self.surveillance_test,
                        role=TestingRole.SURVEILLANCE,
                        time=self.scheduler.time,
                        routine_test=self.routine_test,
                    )
            else:
                self.scheduler.add_event(
                    message=PersonTestingMessage.NOT_COMPLIANT,
                    handler=self.handle_testing_message,
                )
                self.out.add_noncompliance(
                    person_id=self.id,
                    test_name=self.surveillance_test,
                    role=TestingRole.SURVEILLANCE,
                    time=self.scheduler.time,
                )

    # skipping update_value as it is used only for summary stats

    # skipping stop_lesions as we accomplish that with the end_simulation message

    # omitting the 3 trace state functions as we are writing state changes instead

    # omitting learn_family_history_event and predicted_risk_change_event
    # since we are not implementing risk categories

    def handle_ongoing_treatment(self, message="Ongoing treatment"):
        self.num_ongoing_treatments += 1
        self.out.add_treatment(
            person_id=self.id,
            stage=self.stage_at_detection,
            role=TreatmentRole.ONGOING,
            time=self.scheduler.time,
        )

        if self.num_ongoing_treatments < self.params["max_ongoing_treatments"]:
            self.ongoing_treatment_event = self.scheduler.add_event(
                message=message,
                handler=self.handle_ongoing_treatment,
                delay=1,
            )

    def handle_yearly_actions(self, message="Conduct yearly actions"):
        if self.params["use_variable_routine_test"]:
            # If the simulation is using variable routine tests, then the parameters
            # specify a single routine test that every person in the simulation will
            # use for each testing year. This allows a person to switch tests during
            # their lifetime. In this case, we assign the routine test for each year
            # rather than choosing a single routine test at initiatilization.
            #
            # Note that indexing self.params["routine_testing_year"] will always
            # return the min/max testing year, because crcsim.parameters raises an
            # error if this parameter is not sorted in increasing order.
            if (
                self.scheduler.time >= self.params["routine_testing_year"][0]
                and self.scheduler.time <= self.params["routine_testing_year"][-1]
            ):
                self.routine_test = self.params["variable_routine_test"](
                    self.scheduler.time
                )
                self.out.add_routine_test_chosen(
                    person_id=self.id,
                    test_name=self.routine_test,
                    time=self.scheduler.time,
                )

        self.do_tests()

        self.scheduler.add_event(
            message=message,
            delay=1,
            handler=self.handle_yearly_actions,
        )

    def do_tests(self):
        # See if the person is due for their routine test. If so, give them the test.
        if self.testing_state == PersonTestingState.ROUTINE:
            test_params = self.params["tests"][self.routine_test]

            # Skip the test if the person is outside of the recommended age range.
            if (
                int(self.scheduler.time) < test_params["routine_start"]
                or int(self.scheduler.time) > test_params["routine_end"]
            ):
                return

            # Skip the test unless the person is due for *every* routine test available,
            # not just their routine test. For example, suppose the recommended testing
            # strategies are a colonoscopy every 10 years or an FOBT every two years,
            # and this person has chosen the FOBT strategy. One reason for skipping the
            # FOBT this year would be if they had an FOBT last year. Another reason would
            # be if they had a colonoscopy in the past 9 years.
            found_skip = False
            for test, age in self.previous_test_age.items():
                if test in self.params["routine_tests"]:
                    if age is not None:
                        if (int(self.scheduler.time) - age) < self.params["tests"][
                            test
                        ]["routine_freq"]:
                            found_skip = True
                            break
            if not found_skip:
                self.test_routine()

        # See if the person is due for their surveillance test. If so, give them the test.
        elif self.testing_state == PersonTestingState.SURVEILLANCE:
            # Skip the test if the person's age exceeds the upper bound on surveillance.
            if int(self.scheduler.time) > self.params["surveillance_end_age"]:
                return

            # To decide whether or not the person is eligible for a surveillance test
            # this year, we need to know how long it has been since their previous test
            # and the recommended test frequency. These are defined differently for
            # people in "regular" surveillance than for people in post-cancer
            # surveillance. Regular surveillance is for people who have had polyps
            # but not cancer.
            #
            # For regular surveillance:
            #   - The time since the previous test is computed using either a
            #     surveillance test or a diagnostic test, whichever is most recent.
            #   - The recommended test frequency depends on the results of their
            #     previous test and on their predicted risk category.
            # For post-cancer surveillance:
            #   - The time since the previous test is computed as the time since the
            #     most recent surveillance test or the time since treatment initiation,
            #     whichever is smaller.
            #   - The recommended test frequency depends on the number of
            #     surveillance tests they have already taken since treatment initiation.
            if self.treatment_state == PersonTreatmentState.NO_TREATMENT:
                # This case represents those who are in "regular" surveillance.
                #
                # First determine which test the person took most recently, diagnostic or
                # surveillance.
                #
                # Note that they may have never taken a surveillance test before, but they
                # must have taken a diagnostic test before reaching the Surveillance
                # state. Therefore, we don't have to handle the case of neither test
                # being taken.
                if self.diagnostic_test not in self.previous_test_age:
                    raise ValueError(
                        "Did not expect age at previous diagnostic test to be null"
                    )
                elif (
                    self.surveillance_test not in self.previous_test_age
                    or self.previous_test_age[self.surveillance_test]
                    < self.previous_test_age[self.diagnostic_test]
                ):
                    previous_test = self.diagnostic_test
                    previous_test_age = self.previous_test_age[self.diagnostic_test]
                else:
                    previous_test = self.surveillance_test
                    previous_test_age = self.previous_test_age[self.surveillance_test]

                # Next, find the results of the most recent test
                num_small = self.previous_test_small[previous_test]
                num_medium = self.previous_test_medium[previous_test]
                num_large = self.previous_test_large[previous_test]

                # Find the recommended surveillance test frequency for a person with
                # this polyp size distribution
                if (num_small + num_medium + num_large) == 0:
                    frequency = self.params["surveillance_freq_polyp_none"]
                elif (num_small + num_medium) <= 2 and num_large == 0:
                    frequency = self.params["surveillance_freq_polyp_mild"]
                elif (num_small + num_medium + num_large) <= 10:
                    frequency = self.params["surveillance_freq_polyp_moderate"]
                else:
                    frequency = self.params["surveillance_freq_polyp_severe"]

            else:
                # This case represents those who are in post-treatment surveillance
                previous_surveillance_age = self.previous_test_age[
                    self.surveillance_test
                ]

                if self.previous_treatment_initiation_age is None:
                    raise ValueError(
                        "Did not expect previous treatment initiation age to be null"
                    )
                if previous_surveillance_age is None:
                    previous_test_age = self.previous_treatment_initiation_age
                else:
                    previous_test_age = max(
                        previous_surveillance_age,
                        self.previous_treatment_initiation_age,
                    )

                if self.num_surveillance_tests_since_positive is None:
                    raise ValueError(
                        "Did not expect number of surveillance tests since positive to be null"
                    )
                if self.num_surveillance_tests_since_positive == 0:
                    frequency = self.params["surveillance_freq_cancer_first"]
                elif self.num_surveillance_tests_since_positive == 1:
                    frequency = self.params["surveillance_freq_cancer_second"]
                else:
                    frequency = self.params["surveillance_freq_cancer_rest"]

            # Now that we know the time since the previous test and the recommended
            # test frequency, we can determine eligibility for this year.
            if (int(self.scheduler.time) - previous_test_age) >= frequency:
                self.test_surveillance()


class Lesion:
    id_generator = itertools.count()

    def __init__(self, params, scheduler, person, rng, out):
        self.id = next(Lesion.id_generator)
        self.params = params
        self.scheduler = scheduler
        self.person = person
        self.rng = rng
        self.out = out

        self.transition_timeout_event = None
        self.symptoms_event = None

        self.state = LesionState.UNINITIALIZED
        self.handle_message(LesionMessage.INIT)

    def handle_message(self, message):
        if self.state == LesionState.UNINITIALIZED:
            if message == LesionMessage.INIT:
                self.state = LesionState.SMALL_POLYP
                self.write_state_change(
                    message, LesionState.UNINITIALIZED, LesionState.SMALL_POLYP
                )
                # update person disease state
                self.scheduler.add_event(
                    message=PersonDiseaseMessage.POLYP_ONSET,
                    handler=self.person.handle_disease_message,
                )
                # schedule timeout to progress to medium polyp
                self.transition_timeout_event = self.scheduler.add_event(
                    message=LesionMessage.PROGRESS_POLYP_STAGE,
                    handler=self.handle_message,
                    delay=self.rng.expovariate(
                        1 / self.params["mean_duration_polyp1_polyp2"]
                    ),
                )
            else:
                raise ValueError(
                    f"Received unexpected message {message} in Lesion state {self.state}"
                )
        elif self.state == LesionState.SMALL_POLYP:
            if message == LesionMessage.PROGRESS_POLYP_STAGE:
                # When exiting a state with a timeout transition, always disable the
                # timeout event to avoid acting on stale messages.
                self.transition_timeout_event.enabled = False

                self.state = LesionState.MEDIUM_POLYP
                self.write_state_change(
                    message, LesionState.SMALL_POLYP, LesionState.MEDIUM_POLYP
                )
                # update person disease state
                self.scheduler.add_event(
                    message=PersonDiseaseMessage.POLYP_MEDIUM_ONSET,
                    handler=self.person.handle_disease_message,
                )
                # schedule timeout to progress to large polyp or to
                # preclinical stage 1 - whichever comes first
                large_polyp_delay = self.rng.expovariate(
                    1 / self.params["mean_duration_polyp2_polyp3"]
                )
                pre1_delay = self.rng.expovariate(
                    1 / self.params["mean_duration_polyp2_pre"]
                )
                if large_polyp_delay < pre1_delay:
                    self.transition_timeout_event = self.scheduler.add_event(
                        message=LesionMessage.PROGRESS_POLYP_STAGE,
                        handler=self.handle_message,
                        delay=large_polyp_delay,
                    )
                else:
                    self.transition_timeout_event = self.scheduler.add_event(
                        message=LesionMessage.BECOME_CANCER,
                        handler=self.handle_message,
                        delay=pre1_delay,
                    )
            elif message == LesionMessage.CLINICAL_DETECTION:
                # When exiting a state with a timeout transition, always disable the
                # timeout event to avoid acting on stale messages.
                self.transition_timeout_event.enabled = False

                self.state = LesionState.REMOVED
                self.write_state_change(
                    message, LesionState.SMALL_POLYP, LesionState.REMOVED
                )
                # check if all of person's lesions are removed.
                # If so, update their disease state to healthy.
                all_polyps_removed = all(
                    lesion.state == LesionState.REMOVED
                    for lesion in self.person.lesions
                )
                if all_polyps_removed:
                    self.scheduler.add_event(
                        message=PersonDiseaseMessage.ALL_POLYPS_REMOVED,
                        handler=self.person.handle_disease_message,
                    )
            else:
                pass
        elif self.state == LesionState.MEDIUM_POLYP:
            if message == LesionMessage.PROGRESS_POLYP_STAGE:
                # When exiting a state with a timeout transition, always disable the
                # timeout event to avoid acting on stale messages.
                self.transition_timeout_event.enabled = False

                self.state = LesionState.LARGE_POLYP
                self.write_state_change(
                    message, LesionState.MEDIUM_POLYP, LesionState.LARGE_POLYP
                )
                # update person disease state
                self.scheduler.add_event(
                    message=PersonDiseaseMessage.POLYP_LARGE_ONSET,
                    handler=self.person.handle_disease_message,
                )
                # schedule timeout to progress to preclinical stage 1
                self.transition_timeout_event = self.scheduler.add_event(
                    message=LesionMessage.BECOME_CANCER,
                    handler=self.handle_message,
                    delay=self.rng.expovariate(
                        1 / self.params["mean_duration_polyp3_pre"]
                    ),
                )
            elif message == LesionMessage.BECOME_CANCER:
                # When exiting a state with a timeout transition, always disable the
                # timeout event to avoid acting on stale messages.
                self.transition_timeout_event.enabled = False

                self.state = LesionState.PRECLINICAL_STAGE1
                self.write_state_change(
                    message, LesionState.MEDIUM_POLYP, LesionState.PRECLINICAL_STAGE1
                )
                # update person disease state
                self.scheduler.add_event(
                    message=PersonDiseaseMessage.PRECLINICAL_ONSET,
                    handler=self.person.handle_disease_message,
                )
                # schedule timeout to progress to preclinical stage 2
                self.transition_timeout_event = self.scheduler.add_event(
                    message=LesionMessage.PROGRESS_CANCER_STAGE,
                    handler=self.handle_message,
                    delay=self.rng.expovariate(
                        1 / self.params["mean_duration_pre1_pre2"]
                    ),
                )
                # Schedule timeout to exhibit symptoms. Note that we schedule this event
                # independently of the cancer progression event above, as opposed to
                # deciding which will happen first and scheduling only that one. We need
                # to schedule both, because the symptoms event is sent to the Person
                # statechart and won't necessarily prompt a transition in the Lesion
                # statechart. If it doesn't, then we still want the progression event to
                # prompt a transition in the Lesion statechart, even if it comes later.
                self.symptoms_event = self.scheduler.add_event(
                    message=PersonTestingMessage.SYMPTOMATIC,
                    handler=self.person.handle_testing_message,
                    delay=self.rng.expovariate(
                        1 / self.params["mean_duration_pre1_clin1"]
                    ),
                )
            elif message == LesionMessage.CLINICAL_DETECTION:
                # When exiting a state with a timeout transition, always disable the
                # timeout event to avoid acting on stale messages.
                self.transition_timeout_event.enabled = False

                self.state = LesionState.REMOVED
                self.write_state_change(
                    message, LesionState.MEDIUM_POLYP, LesionState.REMOVED
                )
                # check if all of person's lesions are removed.
                # If so, update their disease state to healthy.
                all_polyps_removed = all(
                    lesion.state == LesionState.REMOVED
                    for lesion in self.person.lesions
                )
                if all_polyps_removed:
                    self.scheduler.add_event(
                        message=PersonDiseaseMessage.ALL_POLYPS_REMOVED,
                        handler=self.person.handle_disease_message,
                    )
            else:
                pass
        elif self.state == LesionState.LARGE_POLYP:
            if message == LesionMessage.BECOME_CANCER:
                # When exiting a state with a timeout transition, always disable the
                # timeout event to avoid acting on stale messages.
                self.transition_timeout_event.enabled = False

                self.state = LesionState.PRECLINICAL_STAGE1
                self.write_state_change(
                    message, LesionState.LARGE_POLYP, LesionState.PRECLINICAL_STAGE1
                )
                # update person disease state
                self.scheduler.add_event(
                    message=PersonDiseaseMessage.PRECLINICAL_ONSET,
                    handler=self.person.handle_disease_message,
                )
                # schedule timeout to progress to preclinical stage 2
                self.transition_timeout_event = self.scheduler.add_event(
                    message=LesionMessage.PROGRESS_CANCER_STAGE,
                    handler=self.handle_message,
                    delay=self.rng.expovariate(
                        1 / self.params["mean_duration_pre1_pre2"]
                    ),
                )
                # Schedule timeout to exhibit symptoms. See the discussion in the
                # MEDIUM_POLYP => PRECLINICAL_STAGE1 transition for why we schedule the
                # symptoms event in addition to the cancer progression event.
                self.symptoms_event = self.scheduler.add_event(
                    message=PersonTestingMessage.SYMPTOMATIC,
                    handler=self.person.handle_testing_message,
                    delay=self.rng.expovariate(
                        1 / self.params["mean_duration_pre1_clin1"]
                    ),
                )
            elif message == LesionMessage.CLINICAL_DETECTION:
                # When exiting a state with a timeout transition, always disable the
                # timeout event to avoid acting on stale messages.
                self.transition_timeout_event.enabled = False

                self.state = LesionState.REMOVED
                self.write_state_change(
                    message, LesionState.LARGE_POLYP, LesionState.REMOVED
                )
                # check if all of person's lesions are removed.
                # If so, update their disease state to healthy.
                all_polyps_removed = all(
                    lesion.state == LesionState.REMOVED
                    for lesion in self.person.lesions
                )
                if all_polyps_removed:
                    self.scheduler.add_event(
                        message=PersonDiseaseMessage.ALL_POLYPS_REMOVED,
                        handler=self.person.handle_disease_message,
                    )
            else:
                pass
        elif self.state == LesionState.PRECLINICAL_STAGE1:
            if message == LesionMessage.PROGRESS_CANCER_STAGE:
                # When exiting a state with a timeout transition, always disable the
                # timeout event to avoid acting on stale messages.
                self.transition_timeout_event.enabled = False
                self.symptoms_event.enabled = False

                self.state = LesionState.PRECLINICAL_STAGE2
                self.write_state_change(
                    message,
                    LesionState.PRECLINICAL_STAGE1,
                    LesionState.PRECLINICAL_STAGE2,
                )
                # update person disease state
                self.scheduler.add_event(
                    message=PersonDiseaseMessage.PRE2_ONSET,
                    handler=self.person.handle_disease_message,
                )
                # schedule timeout to progress to preclinical stage 3
                self.transition_timeout_event = self.scheduler.add_event(
                    message=LesionMessage.PROGRESS_CANCER_STAGE,
                    handler=self.handle_message,
                    delay=self.rng.expovariate(
                        1 / self.params["mean_duration_pre2_pre3"]
                    ),
                )
                # Schedule timeout to exhibit symptoms. See the discussion in the
                # MEDIUM_POLYP => PRECLINICAL_STAGE1 transition for why we schedule the
                # symptoms event in addition to the cancer progression event.
                self.symptoms_event = self.scheduler.add_event(
                    message=PersonTestingMessage.SYMPTOMATIC,
                    handler=self.person.handle_testing_message,
                    delay=self.rng.expovariate(
                        1 / self.params["mean_duration_pre2_clin2"]
                    ),
                )
            elif message == LesionMessage.CLINICAL_DETECTION:
                # When exiting a state with a timeout transition, always disable the
                # timeout event to avoid acting on stale messages.
                self.transition_timeout_event.enabled = False
                self.symptoms_event.enabled = False

                self.state = LesionState.CLINICAL_STAGE1
                self.write_state_change(
                    message, LesionState.PRECLINICAL_STAGE1, LesionState.CLINICAL_STAGE1
                )
                # update person disease state
                self.scheduler.add_event(
                    message=PersonDiseaseMessage.CLINICAL_ONSET,
                    handler=self.person.handle_disease_message,
                )
                # check if person will die of CRC and schedule timeout if so
                if self.rng.random() < self.params["proportion_survive_clin1"]:
                    pass
                else:
                    if self.params["mean_duration_clin1_dead"] != 0:
                        duration_clin_dead = self.rng.expovariate(
                            1 / self.params["mean_duration_clin1_dead"]
                        )
                    else:
                        duration_clin_dead = 0
                    self.transition_timeout_event = self.scheduler.add_event(
                        message=LesionMessage.KILL_PERSON,
                        handler=self.handle_message,
                        delay=duration_clin_dead,
                    )
            else:
                pass
        elif self.state == LesionState.PRECLINICAL_STAGE2:
            if message == LesionMessage.PROGRESS_CANCER_STAGE:
                # When exiting a state with a timeout transition, always disable the
                # timeout event to avoid acting on stale messages.
                self.transition_timeout_event.enabled = False
                self.symptoms_event.enabled = False

                self.state = LesionState.PRECLINICAL_STAGE3
                self.write_state_change(
                    message,
                    LesionState.PRECLINICAL_STAGE2,
                    LesionState.PRECLINICAL_STAGE3,
                )
                # update person disease state
                self.scheduler.add_event(
                    message=PersonDiseaseMessage.PRE3_ONSET,
                    handler=self.person.handle_disease_message,
                )
                # schedule timeout to progress to preclinical stage 4
                self.transition_timeout_event = self.scheduler.add_event(
                    message=LesionMessage.PROGRESS_CANCER_STAGE,
                    handler=self.handle_message,
                    delay=self.rng.expovariate(
                        1 / self.params["mean_duration_pre3_pre4"]
                    ),
                )
                # Schedule timeout to exhibit symptoms. See the discussion in the
                # MEDIUM_POLYP => PRECLINICAL_STAGE1 transition for why we schedule the
                # symptoms event in addition to the cancer progression event.
                self.symptoms_event = self.scheduler.add_event(
                    message=PersonTestingMessage.SYMPTOMATIC,
                    handler=self.person.handle_testing_message,
                    delay=self.rng.expovariate(
                        1 / self.params["mean_duration_pre3_clin3"]
                    ),
                )
            elif message == LesionMessage.CLINICAL_DETECTION:
                # When exiting a state with a timeout transition, always disable the
                # timeout event to avoid acting on stale messages.
                self.transition_timeout_event.enabled = False
                self.symptoms_event.enabled = False

                self.state = LesionState.CLINICAL_STAGE2
                self.write_state_change(
                    message, LesionState.PRECLINICAL_STAGE2, LesionState.CLINICAL_STAGE2
                )
                # update person disease state
                self.scheduler.add_event(
                    message=PersonDiseaseMessage.CLINICAL_ONSET,
                    handler=self.person.handle_disease_message,
                )
                # check if person will die of CRC and schedule timeout if so
                if self.rng.random() < self.params["proportion_survive_clin2"]:
                    pass
                else:
                    if self.params["mean_duration_clin2_dead"] != 0:
                        duration_clin_dead = self.rng.expovariate(
                            1 / self.params["mean_duration_clin2_dead"]
                        )
                    else:
                        duration_clin_dead = 0
                    self.transition_timeout_event = self.scheduler.add_event(
                        message=LesionMessage.KILL_PERSON,
                        handler=self.handle_message,
                        delay=duration_clin_dead,
                    )
            else:
                pass
        elif self.state == LesionState.PRECLINICAL_STAGE3:
            if message == LesionMessage.PROGRESS_CANCER_STAGE:
                # When exiting a state with a timeout transition, always disable the
                # timeout event to avoid acting on stale messages.
                self.transition_timeout_event.enabled = False
                self.symptoms_event.enabled = False

                self.state = LesionState.PRECLINICAL_STAGE4
                self.write_state_change(
                    message,
                    LesionState.PRECLINICAL_STAGE3,
                    LesionState.PRECLINICAL_STAGE4,
                )
                # update person disease state
                self.scheduler.add_event(
                    message=PersonDiseaseMessage.PRE4_ONSET,
                    handler=self.person.handle_disease_message,
                )
                # schedule timeout to exhibit symptoms
                self.symptoms_event = self.scheduler.add_event(
                    message=PersonTestingMessage.SYMPTOMATIC,
                    handler=self.person.handle_testing_message,
                    delay=self.rng.expovariate(
                        1 / self.params["mean_duration_pre4_clin4"]
                    ),
                )
            elif message == LesionMessage.CLINICAL_DETECTION:
                # When exiting a state with a timeout transition, always disable the
                # timeout event to avoid acting on stale messages.
                self.transition_timeout_event.enabled = False
                self.symptoms_event.enabled = False

                self.state = LesionState.CLINICAL_STAGE3
                self.write_state_change(
                    message, LesionState.PRECLINICAL_STAGE3, LesionState.CLINICAL_STAGE3
                )
                # update person disease state
                self.scheduler.add_event(
                    message=PersonDiseaseMessage.CLINICAL_ONSET,
                    handler=self.person.handle_disease_message,
                )
                # check if person will die of CRC and schedule timeout if so
                if self.rng.random() < self.params["proportion_survive_clin3"]:
                    pass
                else:
                    if self.params["mean_duration_clin3_dead"] != 0:
                        duration_clin_dead = self.rng.expovariate(
                            1 / self.params["mean_duration_clin3_dead"]
                        )
                    else:
                        duration_clin_dead = 0
                    self.transition_timeout_event = self.scheduler.add_event(
                        message=LesionMessage.KILL_PERSON,
                        handler=self.handle_message,
                        delay=duration_clin_dead,
                    )
            else:
                pass
        elif self.state == LesionState.PRECLINICAL_STAGE4:
            if message == LesionMessage.CLINICAL_DETECTION:
                # When exiting a state with a timeout transition, always disable the
                # timeout event to avoid acting on stale messages.
                self.symptoms_event.enabled = False

                self.state = LesionState.CLINICAL_STAGE4
                self.write_state_change(
                    message, LesionState.PRECLINICAL_STAGE4, LesionState.CLINICAL_STAGE4
                )
                # update person disease state
                self.scheduler.add_event(
                    message=PersonDiseaseMessage.CLINICAL_ONSET,
                    handler=self.person.handle_disease_message,
                )
                # check if person will die of CRC and schedule timeout if so
                if self.rng.random() < self.params["proportion_survive_clin4"]:
                    pass
                else:
                    if self.params["mean_duration_clin4_dead"] != 0:
                        duration_clin_dead = self.rng.expovariate(
                            1 / self.params["mean_duration_clin4_dead"]
                        )
                    else:
                        duration_clin_dead = 0
                    self.transition_timeout_event = self.scheduler.add_event(
                        message=LesionMessage.KILL_PERSON,
                        handler=self.handle_message,
                        delay=duration_clin_dead,
                    )
            else:
                pass
        elif self.state == LesionState.CLINICAL_STAGE1:
            if message == LesionMessage.KILL_PERSON:
                # When exiting a state with a timeout transition, always disable the
                # timeout event to avoid acting on stale messages.
                self.transition_timeout_event.enabled = False

                self.state = LesionState.DEAD
                self.write_state_change(
                    message, LesionState.CLINICAL_STAGE1, LesionState.DEAD
                )
                # update person disease state
                self.scheduler.add_event(
                    message=PersonDiseaseMessage.CRC_DEATH,
                    handler=self.person.handle_disease_message,
                )
            else:
                pass
        elif self.state == LesionState.CLINICAL_STAGE2:
            if message == LesionMessage.KILL_PERSON:
                # When exiting a state with a timeout transition, always disable the
                # timeout event to avoid acting on stale messages.
                self.transition_timeout_event.enabled = False

                self.state = LesionState.DEAD
                self.write_state_change(
                    message, LesionState.CLINICAL_STAGE2, LesionState.DEAD
                )
                # update person disease state
                self.scheduler.add_event(
                    message=PersonDiseaseMessage.CRC_DEATH,
                    handler=self.person.handle_disease_message,
                )
            else:
                pass
        elif self.state == LesionState.CLINICAL_STAGE3:
            if message == LesionMessage.KILL_PERSON:
                # When exiting a state with a timeout transition, always disable the
                # timeout event to avoid acting on stale messages.
                self.transition_timeout_event.enabled = False

                self.state = LesionState.DEAD
                self.write_state_change(
                    message, LesionState.CLINICAL_STAGE3, LesionState.DEAD
                )
                # update person disease state
                self.scheduler.add_event(
                    message=PersonDiseaseMessage.CRC_DEATH,
                    handler=self.person.handle_disease_message,
                )
            else:
                pass
        elif self.state == LesionState.CLINICAL_STAGE4:
            if message == LesionMessage.KILL_PERSON:
                # When exiting a state with a timeout transition, always disable the
                # timeout event to avoid acting on stale messages.
                self.transition_timeout_event.enabled = False

                self.state = LesionState.DEAD
                self.write_state_change(
                    message, LesionState.CLINICAL_STAGE4, LesionState.DEAD
                )
                # update person disease state
                self.scheduler.add_event(
                    message=PersonDiseaseMessage.CRC_DEATH,
                    handler=self.person.handle_disease_message,
                )
            else:
                pass
        elif self.state == LesionState.REMOVED:
            pass
        elif self.state == LesionState.DEAD:
            pass
        else:
            raise ValueError(f"Unexpected Lesion state {self.state}")

    def write_state_change(self, message, old_state, new_state):
        self.out.add_lesion_state_change(
            person_id=self.person.id,
            lesion_id=self.id,
            message=message,
            time=self.scheduler.time,
            old_state=old_state,
            new_state=new_state,
        )

    def is_detected(self, test: str):
        if test is None:
            return False

        test_params = self.params["tests"][test]

        # Determine which sensitivity parameter to used based on the current state
        # of the lesion and type of test. If the current state is not Polyp or
        # Preclinical Cacner, then immediately return.
        if self.state == LesionState.SMALL_POLYP:
            sensitivity = test_params["sensitivity_polyp1"]
        elif self.state == LesionState.MEDIUM_POLYP:
            sensitivity = test_params["sensitivity_polyp2"]
        elif self.state == LesionState.LARGE_POLYP:
            sensitivity = test_params["sensitivity_polyp3"]
        elif self.state in [
            LesionState.PRECLINICAL_STAGE1,
            LesionState.PRECLINICAL_STAGE2,
            LesionState.PRECLINICAL_STAGE3,
            LesionState.PRECLINICAL_STAGE4,
        ]:
            sensitivity = test_params["sensitivity_cancer"]
        elif self.state in [
            LesionState.CLINICAL_STAGE1,
            LesionState.CLINICAL_STAGE2,
            LesionState.CLINICAL_STAGE3,
            LesionState.CLINICAL_STAGE4,
        ]:
            return True
        elif self.state in [
            LesionState.REMOVED,
            LesionState.DEAD,
        ]:
            return False
        else:
            raise ValueError(f"Unexpected Lesion state {self.state}")

        # Sensitivity is the probability of a positive test result given the presence
        # of a lesion. Since we are doing this inside of a Lesion object, we know a
        # lesion is present. So we can view the sensitivity as the probability of a
        # positive test result.
        return self.rng.random() < sensitivity
