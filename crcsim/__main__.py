import csv
import logging
import random

import fire

from crcsim.agent import Person, RaceEthnicity, Sex
from crcsim.output import Output
from crcsim.parameters import load_params
from crcsim.scheduler import Scheduler


def compute_lifespan(rng: random.Random, params: dict, cohort_row: dict) -> float:
    """
    Return a randomly-computed lifespan based on the death rate parameters.
    """

    rand = rng.random()
    cum_prob_survive = 1.0
    cum_prob_death = 0.0
    sex = Sex(cohort_row["sex"])
    race_ethnicity = RaceEthnicity(cohort_row["race_ethnicity"])

    # Find the appropriate death rate table. We don't have separate tables
    # for all combinations of sex and race_ethnicity, so we'll need to do
    # some imperfect combining of categories.
    if sex == Sex.FEMALE:
        if race_ethnicity == RaceEthnicity.WHITE_NON_HISPANIC:
            death_rate = params["death_rate_white_female"]
        elif race_ethnicity in (
            RaceEthnicity.HISPANIC,
            RaceEthnicity.BLACK_NON_HISPANIC,
            RaceEthnicity.OTHER_NON_HISPANIC,
        ):
            death_rate = params["death_rate_black_female"]
        else:
            raise ValueError(f"Unexpected race/ethnicity value: {race_ethnicity}")
    elif sex in (Sex.MALE, Sex.OTHER):
        if race_ethnicity == RaceEthnicity.WHITE_NON_HISPANIC:
            death_rate = params["death_rate_white_male"]
        elif race_ethnicity in (
            RaceEthnicity.HISPANIC,
            RaceEthnicity.BLACK_NON_HISPANIC,
            RaceEthnicity.OTHER_NON_HISPANIC,
        ):
            death_rate = params["death_rate_black_male"]
        else:
            raise ValueError(f"Unexpected race/ethnicity value: {race_ethnicity}")
    else:
        raise ValueError(f"Unexpected sex value: {sex}")

    # Move through the death table, searching for the age at which the
    # person's cumulative probability of death exceeds the random number we
    # generated. This is the age when the person will die.
    found_lifespan = False

    for i in range(params["max_age"] + 1):
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
        lifespan = params["max_age"]

    # Just in case, cap the lifespan at the max age.
    if lifespan > params["max_age"]:
        lifespan = params["max_age"]

    return lifespan


def run(
    seed=None,
    npeople=None,
    params_file="parameters.json",
    outfile="./output.csv",
    cohort_file="cohort.csv",
    debug=False,
):
    if debug:
        logging.basicConfig(format="%(message)s", level=logging.DEBUG)

    rng = random.Random(seed)

    params = load_params(params_file)

    out = Output(outfile)
    out.open()

    with open(cohort_file, mode="r") as input:
        cohort = csv.DictReader(input)

        # Draw expected lifespans for everyone in the cohort prior to starting
        # simulations. This is necessary to ensure that expected lifespans are
        # always the same for a given seed. If we drew lifespans during the cohort
        # loop, the state of the random number generator at the time of drawing each
        # lifespan would be affected by the number of draws that occurred while
        # simulating the previous persons, which is affected by parameters other
        # than the seed.
        expected_lifespans = [compute_lifespan(rng, params, p) for p in cohort]

        for i, p in enumerate(cohort):
            if npeople is not None and i >= npeople:
                break

            scheduler = Scheduler()

            person = Person(
                id=p["id"],
                sex=Sex(p["sex"]),
                race_ethnicity=RaceEthnicity(p["race_ethnicity"]),
                expected_lifespan=expected_lifespans[i],
                params=params,
                scheduler=scheduler,
                rng=rng,
                out=out,
            )
            person.start()

            while not scheduler.is_empty():
                event = scheduler.consume_next_event()
                if not event.enabled:
                    continue
                if event.message == "end_simulation":
                    logging.debug("[scheduler] ending simulation \n")
                    break
                handler = event.handler
                if debug:
                    # For performance reasons, don't call logging.debug() unless
                    # debugging is enabled. Constructing the string argument takes a
                    # surprisingly large portion of the overall script runtime.
                    logging.debug(
                        f"[scheduler] send event '{str(event.message)}' at time {scheduler.time}"
                    )
                handler(event.message)

            # To keep our memory usage low, commit the saved data to the output
            # file after simulating each person instead of waiting until
            # simulating all people.
            out.commit()

    out.close()


# Define main as a separate function so that it can be reached from a console script in setup.py.
# Set main to call run() in order to use Fire.
def main():
    fire.Fire(run)


if __name__ == "__main__":
    main()
