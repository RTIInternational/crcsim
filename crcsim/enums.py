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


@unique
class TestCombiningMethod(str, Enum):
    SERIAL = "serial"
    PARALLEL = "parallel"
