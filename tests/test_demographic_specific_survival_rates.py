import random
from typing import Any

import pytest
from _pytest.python import Metafunc

from crcsim.agent import Lesion, Person, get_demographic
from crcsim.enums import LesionMessage, LesionState, RaceEthnicity, Sex
from crcsim.output import Output
from crcsim.parameters import load_params
from crcsim.scheduler import Event, Scheduler


@pytest.fixture
def params() -> dict[str, Any]:
    """Assumes parameters.json contains demographic-specific survival parameters."""
    return load_params("parameters.json")


@pytest.fixture
def output() -> Output:
    """Output is unused in these tests, but required to instantiate model objects."""
    return Output(file_name="unused")


def pytest_generate_tests(metafunc: Metafunc) -> None:
    """Various parametrizations related to demographics and stages. Using
    pytest_generate_tests instead of separate fixtures avoids repetition. The
    conditionals in this function determine which parametrizations are passed
    to which tests.

    See https://docs.pytest.org/en/stable/how-to/parametrize.html#basic-pytest-generate-tests-example
    """
    demographics: list[str] = [
        "black_female",
        "black_male",
        "hispanic_female",
        "hispanic_male",
        "white_female",
        "white_male",
    ]
    stages: list[int] = [1, 2, 3, 4]

    if "demographic_only" in metafunc.fixturenames:
        metafunc.parametrize("demographic_only", demographics)

    if "stage_only" in metafunc.fixturenames:
        metafunc.parametrize("stage_only", stages)

    if "demographic_stage_combo" in metafunc.fixturenames:
        # Create all combinations of demographics and stages
        combos: list[tuple[str, int]] = [
            (demo, stage) for demo in demographics for stage in stages
        ]
        metafunc.parametrize("demographic_stage_combo", combos)

    if "demographic_mapping_item" in metafunc.fixturenames:
        # Create test cases for each demographic mapping
        mappings: list[tuple[Sex, RaceEthnicity, str]] = [
            (Sex.FEMALE, RaceEthnicity.WHITE_NON_HISPANIC, "white_female"),
            (Sex.MALE, RaceEthnicity.WHITE_NON_HISPANIC, "white_male"),
            (Sex.FEMALE, RaceEthnicity.BLACK_NON_HISPANIC, "black_female"),
            (Sex.MALE, RaceEthnicity.BLACK_NON_HISPANIC, "black_male"),
            (Sex.FEMALE, RaceEthnicity.HISPANIC, "hispanic_female"),
            (Sex.MALE, RaceEthnicity.HISPANIC, "hispanic_male"),
            (Sex.FEMALE, RaceEthnicity.OTHER_NON_HISPANIC, "black_female"),
            (Sex.MALE, RaceEthnicity.OTHER_NON_HISPANIC, "black_male"),
            (Sex.OTHER, RaceEthnicity.WHITE_NON_HISPANIC, "white_male"),
        ]
        metafunc.parametrize("demographic_mapping_item", mappings)


def test_demo_string_mapping(
    demographic_mapping_item: tuple[Sex, RaceEthnicity, str],
) -> None:
    """Test that get_demographic correctly maps sex and race/ethnicity to parameter strings."""
    sex, race_ethnicity, expected = demographic_mapping_item
    result = get_demographic(sex, race_ethnicity)
    assert result == expected


def test_invalid_race_ethnicity_raises_error() -> None:
    """Invalid race/ethnicity values should raise ValueError."""
    with pytest.raises(ValueError, match="Unexpected race/ethnicity value"):
        get_demographic(Sex.FEMALE, "invalid_race")  # type: ignore


def test_invalid_sex_raises_error() -> None:
    """Invalid sex values should raise ValueError."""
    with pytest.raises(ValueError, match="Unexpected sex value"):
        get_demographic("invalid_sex", RaceEthnicity.WHITE_NON_HISPANIC)  # type: ignore


def test_person_demo_string_assignment(
    params: dict[str, Any],
    demographic_mapping_item: tuple[Sex, RaceEthnicity, str],
    output: Output,
) -> None:
    """Test that Person correctly assigns demographic based on sex and race_ethnicity."""
    sex, race_ethnicity, expected = demographic_mapping_item
    person = Person(
        id=1,
        sex=sex,
        race_ethnicity=race_ethnicity,
        expected_lifespan=params["max_age"],
        params=params,
        scheduler=Scheduler(),
        rng=random.Random(42),
        out=output,
    )
    person.start()
    assert person.demographic == expected


def test_mean_duration_clin_dead_parameters_exist(
    params: dict[str, Any], demographic_stage_combo: tuple[str, int]
) -> None:
    """Test that all demographic-specific survival parameters exist."""
    demographic, stage = demographic_stage_combo
    param_name = f"mean_duration_clin{stage}_dead_{demographic}"
    assert param_name in params, f"Missing parameter: {param_name}"


def test_death_rate_parameters_exist(
    params: dict[str, Any], demographic_only: str
) -> None:
    """Test that all emographic-specific death rate parameters exist."""
    demographic = demographic_only
    ages_param = f"death_rate_{demographic}_ages"
    rates_param = f"death_rate_{demographic}_rates"

    assert ages_param in params, f"Missing parameter: {ages_param}"
    assert rates_param in params, f"Missing parameter: {rates_param}"


def test_clin_to_dead_integration(
    demographic_mapping_item: tuple[Sex, RaceEthnicity, str],
    stage_only: int,
    params: dict[str, Any],
    output: Output,
) -> None:
    """Checks that simulated clin to death times for each demographic have similar
    means to the expected values in the parameters.
    """
    sex, race_ethnicity, expected = demographic_mapping_item
    stage = stage_only

    # Schedule many CRC deaths for each demographic to get a good sample size.
    n = 10_000

    # Use a unique but deterministic base seed for each demographic/stage combo to ensure
    # reproducibility while avoiding correlation between different test cases.
    # (Ie, we want the same set of n seeds per combo across test runs. But we don't
    # want the same set of n seeds for different combos.)
    demographic_seeds = {
        "black_female": 1000,
        "black_male": 2000,
        "hispanic_female": 3000,
        "hispanic_male": 4000,
        "white_female": 5000,
        "white_male": 6000,
    }
    base_seed = demographic_seeds[expected] + stage
    rng = random.Random(base_seed)
    seeds = [rng.randint(1, 2**31 - 1) for _ in range(n)]

    def schedule_crc_death(
        sex: Sex, race_ethnicity: RaceEthnicity, stage: int, seed: int
    ) -> float:
        """Helper function to set up Person and Lesion objects and schedule CRC death."""
        scheduler = Scheduler()

        rng = random.Random(seed)

        person = Person(
            id=1,
            sex=sex,
            race_ethnicity=race_ethnicity,
            expected_lifespan=params["max_age"],
            params=params,
            scheduler=scheduler,
            rng=rng,
            out=output,
        )
        person.start()

        lesion = Lesion(
            params=params,
            scheduler=scheduler,
            person=person,
            rng=rng,
            out=output,
        )
        # We need to add Lesion.symptoms_event to avoid an error when we schedule
        # death, but we don't use it for anything in this test, so we don't need to
        # pass actual values.
        lesion.symptoms_event = Event(message=None, time=None)  # type: ignore

        # LesionState is an IntEnum and is ordered by stage, so with integer stages,
        # adding stage - 1 to the PRECLINICAL_STAGE1 value gets the corresponding IntEnum
        # value. Eg, PRECLINICAL_STAGE1 = 4, so for stage 2, we want LesionState(5).
        lesion.state = LesionState(LesionState.PRECLINICAL_STAGE1 + stage - 1)

        # Death event is scheduled upon clinical detection
        lesion.handle_message(LesionMessage.CLINICAL_DETECTION)

        # Get the duration from clinical detection to death. The event contains the
        # death age, so we need to subtract the person's age at clinical detection to
        # get the duration.
        crc_death_age = lesion.transition_timeout_event.time  # type: ignore
        return crc_death_age - scheduler.time

    # Simulate clinical detection to death durations for each seed
    durations = [schedule_crc_death(sex, race_ethnicity, stage, seed) for seed in seeds]
    mean_duration = sum(durations) / n

    # Check that the mean duration is within 2.5% of the target mean duration.
    # This threshold was chosen heuristically, based on 10k runs per demographic/stage
    # combo. As n runs increases, the mean duration converges to the expected value.
    # For example, with 100k runs, the max relative error was 1.01%. But increasing n
    # runs makes the test suite slower.
    target_mean_duration = params[f"mean_duration_clin{stage}_dead_{expected}"]

    assert mean_duration == pytest.approx(target_mean_duration, rel=0.025)
