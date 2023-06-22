import csv
import logging
import random

import fire

from crcsim.agent import Person, RaceEthnicity, Sex
from crcsim.output import Output
from crcsim.parameters import load_params
from crcsim.scheduler import Scheduler


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
        for i, p in enumerate(cohort):
            if npeople is not None and i >= npeople:
                break

            scheduler = Scheduler()

            person = Person(
                id=p["id"],
                sex=Sex(p["sex"]),
                race_ethnicity=RaceEthnicity(p["race_ethnicity"]),
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
