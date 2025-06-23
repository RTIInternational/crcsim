# Exploring and calculating demographic-specific survival rates

This experiment does not follow the typical `crcsim` experiment template. We aren't simulating scenarios here. Instead, this is a notebook-based exploration of how we might incorporate demographic-specific survival rates in the model. 

[survival_rate_adjustment.ipynb](crcsim/experiment/survival_rate_adjustment.ipynb) contains initial exploration of the possibility. It begins by establishing that our relevant parameters (the means of our time-to-death distributions) can be calculated directly from survival rates. It then explores several nuances to the calculation. It's thoroughly documented with markdown cells. 

[compute_variable_survival_rates.ipynb](crcsim/experiment/compute_variable_survival_rates.ipynb) implements the calculation approach that we decided on from the previous notebook. It ingests our standard parameters from the 2022 calibration (`crcsim/experiment/parameters.json`) and outputs two modifications:
- `crcsim/experiment/parameters_relative_survival.json` replaces the calibrated `mean_duration_clin*_dead` parameters with values calculated directly.
- `crcsim/experiment/parameters_by_demog.json` adds:
    - Demographic-specific `mean_duration_clin*_dead` parameters
    - Demographic-specific death rate parameters, added manually (with help from Claude) from the 2021 CDC life tables in `crcsim/experiment/survival_rate_adjustment_files`

## Handling demographic-specific survival rates in the model

This branch also contains changes to `crcsim` to simulate demographic-specific survival. 

The model already assigns a `RaceEthnicity` and `Sex` to each agent, based on the cohort file used in the simulation. This was already used to choose the appropriate death rate parameters for calculating each agent's expected lifespan.

Key changes:
- `./parameters.json` is a copy of `crcsim/experiment/parameters_by_demog.json`
- Minor edits to `crcsim.parameters` to handle the addition of death rates for hispanic males and females
- Substantial edits to `crcsim.agent` to use the appropriate clin-to-dead parameters
- Minor edits to other modules to handle these changes, including the addition of a `crcsim.enums` module to avoid circular imports
- Added tests

Because this branch diverged from `main` long ago, and because it includes a bunch of experiment files that we don't want to merge into `main`, we'll make a separate branch to cherry-pick this feature implementation and merge it.
