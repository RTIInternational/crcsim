import csv
import math
from copy import deepcopy

import fire
import numpy as np
import pandas as pd

from crcsim.agent import (
    LesionMessage,
    LesionState,
    PersonDiseaseMessage,
    PersonDiseaseState,
    TestingRole,
    TreatmentRole,
)
from crcsim.parameters import load_params


class Analysis:
    def __init__(self, params, raw_output_file: str):
        self.raw_output = pd.read_csv(raw_output_file)
        self.params = params

        # This option supresses numpy runtime warnings for division by NaN during
        # population rate calcuation. Divison by NaN happens often in those calculations,
        # but numpy handles it in a way that does not affect the results, so these
        # warning messages are unncessary.
        np.seterr(invalid="ignore")

    def summarize(self):
        """
        Takes raw output from a single model run and calculates summary values for the
        model run. Values are added to a dict which can be written as a row in the
        replication output file.
        """
        replication_output_row = {}

        # Number of individuals in the population
        disease_state_changes = self.raw_output[
            self.raw_output.record_type.eq("disease_state_change")
        ]
        inits = disease_state_changes[
            disease_state_changes.old_state.eq(str(PersonDiseaseState.UNINITIALIZED))
        ]
        n_individuals = len(inits.index)
        replication_output_row["n"] = n_individuals

        # Number of individuals who were undiagnosed and unscreened at age 40
        deaths = disease_state_changes[
            disease_state_changes.new_state.eq(str(PersonDiseaseState.DEAD))
        ]
        deaths_after_40 = deaths[deaths.time.ge(40)]
        indivs_screened_before_40 = self.raw_output[
            self.raw_output.record_type.eq("test_performed")
            & self.raw_output.role.isin(
                [str(TestingRole.ROUTINE), str(TestingRole.DIAGNOSTIC)]
            )
            & self.raw_output.time.lt(40)
        ].person_id
        indivs_diagnosed_before_40 = disease_state_changes[
            disease_state_changes.new_state.isin(
                [
                    str(PersonDiseaseState.CLINICAL_STAGE1),
                    str(PersonDiseaseState.CLINICAL_STAGE2),
                    str(PersonDiseaseState.CLINICAL_STAGE3),
                    str(PersonDiseaseState.CLINICAL_STAGE4),
                ]
            )
            & disease_state_changes.time.lt(40)
        ].person_id
        indivs_to_exclude = set(indivs_screened_before_40).union(
            set(indivs_diagnosed_before_40)
        )
        unscreened_undiagnosed_40yo_deaths = deaths_after_40[
            ~deaths_after_40.person_id.isin(indivs_to_exclude)
        ]
        unscreened_undiagnosed_40yos = unscreened_undiagnosed_40yo_deaths.person_id
        n_unscreened_undiagnosed_40yos = len(unscreened_undiagnosed_40yos)
        replication_output_row[
            "n_unscreened_undiagnosed_40yos"
        ] = n_unscreened_undiagnosed_40yos
        thousands_of_40yos = n_unscreened_undiagnosed_40yos / 1_000

        # Number of times an individual entered the polyp state
        polyp_onsets = disease_state_changes[
            disease_state_changes.message.eq(str(PersonDiseaseMessage.POLYP_ONSET))
        ]
        replication_output_row["polyp"] = len(polyp_onsets.index)
        # per 1k undiagnosed and unscreened 40-year-olds
        polyp_onsets_over_40 = polyp_onsets[
            polyp_onsets.time.ge(40)
            & polyp_onsets.person_id.isin(unscreened_undiagnosed_40yos)
        ]
        replication_output_row["polyp_per_1k_40yo"] = (
            len(polyp_onsets_over_40.index) / thousands_of_40yos
        )

        # Number of times an individual contracted CRC
        crc_onsets = disease_state_changes[
            disease_state_changes.message.eq(
                str(PersonDiseaseMessage.PRECLINICAL_ONSET)
            )
        ]
        replication_output_row["crc"] = len(crc_onsets.index)
        # per 1k undiagnosed and unscreened 40-year-olds
        crc_onsets_over_40 = crc_onsets[
            crc_onsets.time.ge(40)
            & crc_onsets.person_id.isin(unscreened_undiagnosed_40yos)
        ]
        replication_output_row["crc_per_1k_40yo"] = (
            len(crc_onsets_over_40.index) / thousands_of_40yos
        )

        # Number of times an individual was diagnosed withi clinically-detected CRC
        clinical_onsets = disease_state_changes[
            disease_state_changes.message.eq(str(PersonDiseaseMessage.CLINICAL_ONSET))
        ]
        replication_output_row["clin_crc"] = len(clinical_onsets.index)
        # per 1k undiagnosed and unscreened 40-year-olds
        clinical_onsets_over_40 = clinical_onsets[
            clinical_onsets.time.ge(40)
            & clinical_onsets.person_id.isin(unscreened_undiagnosed_40yos)
        ]
        replication_output_row["clin_crc_per_1k_40yo"] = (
            len(clinical_onsets_over_40.index) / thousands_of_40yos
        )

        # Number of inviduals who died from CRC
        crc_deaths = disease_state_changes[
            disease_state_changes.message.eq(str(PersonDiseaseMessage.CRC_DEATH))
        ]
        n_crc_deaths = len(crc_deaths.index)
        replication_output_row["deadcrc"] = n_crc_deaths
        # per 1k undiagnosed and unscreened 40-year-olds
        crc_deaths_over_40 = crc_deaths[
            crc_deaths.time.ge(40)
            & crc_deaths.person_id.isin(unscreened_undiagnosed_40yos)
        ]
        replication_output_row["deadcrc_per_1k_40yo"] = (
            len(crc_deaths_over_40.index) / thousands_of_40yos
        )

        # Mean expected lifespan among all individuals
        expected_lifespans = self.raw_output[self.raw_output.record_type.eq("lifespan")]
        replication_output_row["lifeexp"] = np.mean(expected_lifespans.time)
        # among those undiagnosed and unscreened at 40
        expected_lifespans_over_40 = expected_lifespans[
            expected_lifespans.person_id.isin(unscreened_undiagnosed_40yos)
        ]
        replication_output_row["lifeexp_if_unscreened_undiagnosed_at_40"] = np.mean(
            expected_lifespans_over_40.time
        )

        # Mean discounted expected lifespan among all individuals
        discounted_expected_lifespans = self.discount_ages(expected_lifespans.time)
        replication_output_row["discounted_lifeexp"] = np.mean(
            discounted_expected_lifespans
        )
        # among those undiagnosed and unscreened at 40
        discounted_expected_lifespans_over_40 = self.discount_ages(
            expected_lifespans_over_40.time
        )
        replication_output_row[
            "discounted_lifeexp_if_unscreened_undiagnosed_at_40"
        ] = np.mean(discounted_expected_lifespans_over_40)

        # Mean observed lifespan among all individuals
        replication_output_row["lifeobs"] = np.mean(deaths.time)
        # among those undiagnosed and unscreened at 40
        replication_output_row["lifeobs_if_unscreened_undiagnosed_at_40"] = np.mean(
            unscreened_undiagnosed_40yo_deaths.time
        )

        # Mean discounted observed lifespan among all individuals
        discounted_lifespans = self.discount_ages(deaths.time)
        replication_output_row["discounted_lifeobs"] = np.mean(discounted_lifespans)
        # among those undiagnosed and unscreened at 40
        discounted_lifespans_over_40 = self.discount_ages(
            unscreened_undiagnosed_40yo_deaths.time
        )
        replication_output_row[
            "discounted_lifeobs_if_unscreened_undiagnosed_at_40"
        ] = np.mean(discounted_lifespans_over_40)

        # Mean number of life years lost to CRC among all individuals
        replication_output_row["lifelost"] = (
            replication_output_row["lifeexp"] - replication_output_row["lifeobs"]
        )
        # per 1k undiagnosed and unscreened 40-year-olds
        replication_output_row["lifelost_per_1k_40yo"] = (
            replication_output_row["lifeexp_if_unscreened_undiagnosed_at_40"]
            - replication_output_row["lifeobs_if_unscreened_undiagnosed_at_40"]
        ) * 1_000

        # Mean number of discounted life years lost to CRC among all individuals
        replication_output_row["discounted_lifelost"] = (
            replication_output_row["discounted_lifeexp"]
            - replication_output_row["discounted_lifeobs"]
        )
        # per 1k undiagnosed and unscreened 40-year-olds
        replication_output_row["discounted_lifelost_per_1k_40yo"] = (
            replication_output_row["discounted_lifeexp_if_unscreened_undiagnosed_at_40"]
            - replication_output_row[
                "discounted_lifeobs_if_unscreened_undiagnosed_at_40"
            ]
        ) * 1_000

        # Mean number of cancer-free life years among all individuals
        # Not building this one for now, since it's complicated and Sujha doesn't
        # use it.
        #
        # Eventually, the algorithm could be:
        # Loop through disease state events. At each event, check it if changes person's
        # cancer state. If person becomes cancerous, add years from previous change to a
        # counter. If they become cancer-free, add discounted years.

        # Look up costs for all procedures that contribute to screening costs, then
        # combine into a screening costs dataframe that we'll use to calculate mean cost
        # per person for all testing types.
        tests = deepcopy(
            self.raw_output[self.raw_output.record_type.eq("test_performed")]
        )
        unique_tests = tests.test_name.unique()
        cost_lookup = {}
        for t in unique_tests:
            cost = self.params["tests"][t]["cost"]
            cost_lookup[t] = cost
        tests["cost"] = tests.test_name.map(cost_lookup)

        pathologies = deepcopy(
            self.raw_output[self.raw_output.record_type.eq("pathology")]
        )
        pathologies["cost"] = self.params["cost_polyp_pathology"]

        polypectomies = deepcopy(
            self.raw_output[self.raw_output.record_type.eq("polypectomy")]
        )
        polypectomies["cost"] = self.params["cost_polypectomy"]

        perforations = deepcopy(
            self.raw_output[self.raw_output.record_type.eq("perforation")]
        )
        perforation_unique_tests = perforations.test_name.unique()
        perforation_cost_lookup = {}
        for t in perforation_unique_tests:
            cost = self.params["tests"][t]["cost_perforation"]
            perforation_cost_lookup[t] = cost
        perforations["cost"] = perforations.test_name.map(perforation_cost_lookup)

        screening_costs = pd.concat([tests, pathologies, polypectomies, perforations])

        screening_costs["discounted_cost"] = np.where(
            screening_costs["time"] <= self.params["cost_discount_age"],
            screening_costs["cost"],
            screening_costs["cost"]
            * (
                (1 - self.params["cost_discount_rate"])
                ** (screening_costs["time"] - self.params["cost_discount_age"])
            ),
        )
        # among those undiagnosed and unscreened at 40
        screening_costs_over_40 = screening_costs[
            screening_costs.time.gt(40)
            & screening_costs.person_id.isin(unscreened_undiagnosed_40yos)
        ]

        # Mean routine screening costs and discounted routine screening costs
        # among all individuals and per thousand unscreened and undiagnosed 40-year-olds
        replication_output_row["cost_routine"] = get_screening_cost(
            screening_costs, TestingRole.ROUTINE, n_individuals, discount=False
        )
        replication_output_row["discounted_cost_routine"] = get_screening_cost(
            screening_costs, TestingRole.ROUTINE, n_individuals, discount=True
        )
        replication_output_row["cost_routine_per_1k_40yo"] = (
            get_screening_cost(
                screening_costs_over_40,
                TestingRole.ROUTINE,
                n_unscreened_undiagnosed_40yos,
                discount=False,
            )
            * 1_000
        )
        replication_output_row["discounted_cost_routine_per_1k_40yo"] = (
            get_screening_cost(
                screening_costs_over_40,
                TestingRole.ROUTINE,
                n_unscreened_undiagnosed_40yos,
                discount=True,
            )
            * 1_000
        )

        # Mean diagnostic screening costs and discounted diagnostic screening costs
        # among all individuals and per thousand unscreened and undiagnosed 40-year-olds
        replication_output_row["cost_diagnostic"] = get_screening_cost(
            screening_costs, TestingRole.DIAGNOSTIC, n_individuals, discount=False
        )
        replication_output_row["discounted_cost_diagnostic"] = get_screening_cost(
            screening_costs, TestingRole.DIAGNOSTIC, n_individuals, discount=True
        )
        replication_output_row["cost_diagnostic_per_1k_40yo"] = (
            get_screening_cost(
                screening_costs_over_40,
                TestingRole.DIAGNOSTIC,
                n_unscreened_undiagnosed_40yos,
                discount=False,
            )
            * 1_000
        )
        replication_output_row["discounted_cost_diagnostic_per_1k_40yo"] = (
            get_screening_cost(
                screening_costs_over_40,
                TestingRole.DIAGNOSTIC,
                n_unscreened_undiagnosed_40yos,
                discount=True,
            )
            * 1_000
        )

        # Mean surveillance screening costs and discounted surveillance screening costs
        # among all individuals and per thousand unscreened and undiagnosed 40-year-olds
        replication_output_row["cost_surveillance"] = get_screening_cost(
            screening_costs, TestingRole.SURVEILLANCE, n_individuals, discount=False
        )
        replication_output_row["discounted_cost_surveillance"] = get_screening_cost(
            screening_costs, TestingRole.SURVEILLANCE, n_individuals, discount=True
        )
        replication_output_row["cost_surveillance_per_1k_40yo"] = (
            get_screening_cost(
                screening_costs_over_40,
                TestingRole.SURVEILLANCE,
                n_unscreened_undiagnosed_40yos,
                discount=False,
            )
            * 1_000
        )
        replication_output_row["discounted_cost_surveillance_per_1k_40yo"] = (
            get_screening_cost(
                screening_costs_over_40,
                TestingRole.SURVEILLANCE,
                n_unscreened_undiagnosed_40yos,
                discount=True,
            )
            * 1_000
        )

        # Mean treatment costs and discounted treatment costs among all individuals
        treatments = deepcopy(
            self.raw_output[self.raw_output.record_type.eq("treatment")]
        )
        treatments["cost_lookup"] = (
            "cost_treatment_stage"
            + treatments.stage.astype(int).astype(str)
            + "_"
            + treatments.role.str.lower()
        )
        treatments["cost"] = treatments.cost_lookup.map(self.params)
        treatments["discounted_cost"] = np.where(
            treatments["time"] <= self.params["cost_discount_age"],
            treatments["cost"],
            treatments["cost"]
            * (
                (1 - self.params["cost_discount_rate"])
                ** (treatments["time"] - self.params["cost_discount_age"])
            ),
        )
        # among those undiagnosed and unscreened at 40
        treatments_over_40 = treatments[
            treatments.time.gt(40)
            & treatments.person_id.isin(unscreened_undiagnosed_40yos)
        ]
        for phase in [
            str(TreatmentRole.INITIAL),
            str(TreatmentRole.ONGOING),
            str(TreatmentRole.TERMINAL),
        ]:
            treatments_in_phase = treatments[treatments.role.eq(phase)]
            mean_cost_treatment = treatments_in_phase.cost.sum() / n_individuals
            mean_discounted_cost_treatment = (
                treatments_in_phase.discounted_cost.sum() / n_individuals
            )
            replication_output_row[
                f"cost_treatment_{phase.lower()}"
            ] = mean_cost_treatment
            replication_output_row[
                f"discounted_cost_treatment_{phase.lower()}"
            ] = mean_discounted_cost_treatment
            # per 1k undiagnosed and unscreened 40-year-olds
            treatments_in_phase_over_40 = treatments_over_40[
                treatments_over_40.role.eq(phase)
            ]
            mean_cost_treatment_over_40 = (
                treatments_in_phase_over_40.cost.sum() / n_unscreened_undiagnosed_40yos
            )
            mean_discounted_cost_treatment_over_40 = (
                treatments_in_phase_over_40.discounted_cost.sum()
                / n_unscreened_undiagnosed_40yos
            )
            replication_output_row[f"cost_treatment_{phase.lower()}_per_1k_40yo"] = (
                mean_cost_treatment_over_40 * 1_000
            )
            replication_output_row[
                f"discounted_cost_treatment_{phase.lower()}_per_1k_40yo"
            ] = (mean_discounted_cost_treatment_over_40 * 1_000)

        # Risk reduction costs
        # Omitted from Python port since this deals with colectomies

        # Value of life years among all individuals
        # See mean number of cancer-free life years among all individuals

        # Proportion of individuals who developed at least one polyp
        #
        # When we drop duplicates by person, keep the last polyp onset for each person.
        # We'll use this later to calculate time between polyp formation and CRC onset.
        indivs_developed_polyp = polyp_onsets.drop_duplicates(
            subset="person_id", keep="last"
        )
        n_indivs_developed_polyp = len(indivs_developed_polyp.index)
        replication_output_row["prob_polyp"] = n_indivs_developed_polyp / n_individuals

        # Number of times each test was adopted for routine screening
        routine_tests_chosen = self.raw_output[
            self.raw_output.record_type.eq("test_chosen") & self.raw_output.time.eq(0)
        ]
        for rt in self.params["routine_tests"]:
            rt_chosen = routine_tests_chosen[routine_tests_chosen.test_name.eq(rt)]
            replication_output_row[f"{rt}_adopted"] = len(rt_chosen.index)

        # Number of years each routine test was used
        # (if test variable routine test was enabled in the simulation)
        if self.params["use_variable_routine_test"]:
            rt_years = self.raw_output[
                self.raw_output.record_type.eq("test_chosen")
                & self.raw_output.time.gt(0)
            ]
            rt_years_grouped = rt_years.groupby(["test_name"]).agg(
                count=("time", "count")
            )
            for ix, row in rt_years_grouped.iterrows():
                replication_output_row[f"{ix}_available_as_routine"] = row["count"]

        # Number of times each test was performed for routine screening
        # and number of times per thousand unscreened and undiagnosed 40-year-olds
        routine_tests = tests[tests.role.eq(str(TestingRole.ROUTINE))]
        routine_tests_over_40 = routine_tests[
            routine_tests.time.gt(40)
            & routine_tests.person_id.isin(unscreened_undiagnosed_40yos)
        ]
        for rt in self.params["routine_tests"]:
            rt_performed = routine_tests[routine_tests.test_name.eq(rt)]
            replication_output_row[f"{rt}_performed_routine"] = len(rt_performed.index)
            rt_performed_over_40 = routine_tests_over_40[
                routine_tests_over_40.test_name.eq(rt)
            ]
            replication_output_row[f"{rt}_performed_routine_per_1k_40yo"] = (
                len(rt_performed_over_40.index) / thousands_of_40yos
            )

        # Number of times each test was performed for diagnostic screening
        # and number of times per thousand unscreened and undiagnosed 40-year-olds
        diagnostic_tests = tests[tests.role.eq(str(TestingRole.DIAGNOSTIC))]
        diagnostic_tests_over_40 = diagnostic_tests[
            diagnostic_tests.time.gt(40)
            & diagnostic_tests.person_id.isin(unscreened_undiagnosed_40yos)
        ]
        for test in self.params["tests"]:
            test_performed_diagnostic = diagnostic_tests[
                diagnostic_tests.test_name.eq(test)
            ]
            replication_output_row[f"{test}_performed_diagnostic"] = len(
                test_performed_diagnostic.index
            )
            test_performed_diagnostic_over_40 = diagnostic_tests_over_40[
                diagnostic_tests_over_40.test_name.eq(test)
            ]
            replication_output_row[f"{test}_performed_diagnostic_per_1k_40yo"] = (
                len(test_performed_diagnostic_over_40.index) / thousands_of_40yos
            )

        # Number of times each test was performed for surveillance screening
        # and number of times per thousand unscreened and undiagnosed 40-year-olds
        surveillance_tests = tests[tests.role.eq(str(TestingRole.SURVEILLANCE))]
        surveillance_tests_over_40 = surveillance_tests[
            surveillance_tests.time.gt(40)
            & surveillance_tests.person_id.isin(unscreened_undiagnosed_40yos)
        ]
        for test in self.params["tests"]:
            test_performed_surveillance = surveillance_tests[
                surveillance_tests.test_name.eq(test)
            ]
            replication_output_row[f"{test}_performed_surveillance"] = len(
                test_performed_surveillance.index
            )
            test_performed_surveillance_over_40 = surveillance_tests_over_40[
                surveillance_tests_over_40.test_name.eq(test)
            ]
            replication_output_row[f"{test}_performed_surveillance_per_1k_40yo"] = (
                len(test_performed_surveillance_over_40.index) / thousands_of_40yos
            )

        # Number of times people were noncompliant with each test for routine screening
        noncompliance = self.raw_output[self.raw_output.record_type.eq("noncompliance")]
        noncompliance_routine = noncompliance[
            noncompliance.role.eq(str(TestingRole.ROUTINE))
        ]
        for test in self.params["tests"]:
            test_noncompliant_routine = noncompliance_routine[
                noncompliance_routine.test_name.eq(test)
            ]
            replication_output_row[f"{test}_noncompliant_routine"] = len(
                test_noncompliant_routine.index
            )

        # Number of times people were noncompliant with each test for routine screening at age 50
        noncompliance_routine_50 = noncompliance_routine[
            noncompliance_routine["time"] == 50
        ]
        for test in self.params["tests"]:
            test_noncompliant_routine_50 = noncompliance_routine_50[
                noncompliance_routine_50.test_name.eq(test)
            ]
            replication_output_row[f"{test}_noncompliant_routine_50"] = len(
                test_noncompliant_routine_50.index
            )

        # Number of times people were noncompliant with each test for diagnostic screening
        noncompliance_diagnostic = noncompliance[
            noncompliance.role.eq(str(TestingRole.DIAGNOSTIC))
        ]
        for test in self.params["tests"]:
            test_noncompliant_diagnostic = noncompliance_diagnostic[
                noncompliance_diagnostic.test_name.eq(test)
            ]
            replication_output_row[f"{test}_noncompliant_diagnostic"] = len(
                test_noncompliant_diagnostic.index
            )

        # Number of times people were noncompliant with each test for surveillance screening
        noncompliance_surveillance = noncompliance[
            noncompliance.role.eq(str(TestingRole.SURVEILLANCE))
        ]
        for test in self.params["tests"]:
            test_noncompliant_surveillance = noncompliance_surveillance[
                noncompliance_surveillance.test_name.eq(test)
            ]
            replication_output_row[f"{test}_noncompliant_surveillance"] = len(
                test_noncompliant_surveillance.index
            )

        # Number of perforations by routine test and number of perforations by routine
        # test per thousand unscreened and undiagnosed 40-year-olds
        perforations_over_40 = perforations[
            perforations.time.gt(40)
            & perforations.person_id.isin(unscreened_undiagnosed_40yos)
        ]
        for rt in self.params["routine_tests"]:
            perforations_after_rt = perforations[perforations.routine_test.eq(rt)]
            replication_output_row[f"{rt}_perforations"] = len(
                perforations_after_rt.index
            )
            perforations_over_40_after_rt = perforations_over_40[
                perforations_over_40.routine_test.eq(rt)
            ]
            replication_output_row[f"{rt}_perforations_per_1k_40yo"] = (
                len(perforations_over_40_after_rt.index) / thousands_of_40yos
            )

        # Number of test fatalities by routine test and number of test fatalities by
        # routine test per thousand unscreened and undiagnosed 40-year-olds
        test_fatalities = disease_state_changes[
            disease_state_changes.message.eq(
                str(PersonDiseaseMessage.POLYPECTOMY_DEATH)
            )
        ]
        test_fatalities_over_40 = test_fatalities[
            test_fatalities.time.gt(40)
            & test_fatalities.person_id.isin(unscreened_undiagnosed_40yos)
        ]
        for rt in self.params["routine_tests"]:
            test_fatalities_after_rt = test_fatalities[
                test_fatalities.routine_test.eq(rt)
            ]
            replication_output_row[f"{rt}_test_fatalities"] = len(
                test_fatalities_after_rt.index
            )
            test_fatalities_over_40_after_rt = test_fatalities_over_40[
                test_fatalities_over_40.routine_test.eq(rt)
            ]
            replication_output_row[f"{rt}_test_fatalities_per_1k_40yo"] = (
                len(test_fatalities_over_40_after_rt.index) / thousands_of_40yos
            )

        # Proportion of individuals who contracted CRC
        indivs_contracted_crc = crc_onsets.drop_duplicates(subset="person_id")
        n_indivs_contracted_crc = len(indivs_contracted_crc.index)
        replication_output_row["prob_crc"] = n_indivs_contracted_crc / n_individuals

        # Of individuals who developed at least one polyp, proportion who contracted CRC
        crc_given_polyp = indivs_developed_polyp.merge(
            indivs_contracted_crc, how="inner", on="person_id"
        )
        replication_output_row["prob_crc_given_polyp"] = possible_zero_division(
            len(crc_given_polyp.index), n_indivs_developed_polyp
        )

        # Of individuals who never developed a polyp, proportion who contracted CRC
        #
        # Commented out for now, since this is no longer possible in the Python port of
        # the model. Enable if we ever add this functionality back.
        #
        # set_crc_given_no_polyp = set(indivs_contracted_crc.person_id).difference(
        #     set(indivs_developed_polyp.person_id)
        # )
        # crc_given_no_polyp = indivs_contracted_crc[
        #     indivs_contracted_crc.person_id.isin(set_crc_given_no_polyp)
        # ]
        # replication_output_row["prob_crc_given_no_polyp"] = possible_zero_division(
        #     len(crc_given_no_polyp.index), (n_individuals - n_indivs_developed_polyp)
        # )

        # Of individuals who contracted CRC, proportion who died from CRC
        crc_death_given_crc = indivs_contracted_crc.merge(
            crc_deaths, how="inner", on="person_id"
        )
        replication_output_row["prob_dead_crc_given_crc"] = possible_zero_division(
            len(crc_death_given_crc.index), n_indivs_contracted_crc
        )

        # Of all individuals, proportion who died from CRC
        replication_output_row["prob_dead_crc"] = n_crc_deaths / n_individuals

        # Of all lesions that developed into CRC, proportion that were medium-sized
        # polyps immediately prior to becoming cancerous.
        lesion_state_changes = self.raw_output[
            self.raw_output.record_type.eq("lesion_state_change")
        ]
        lesions_becoming_cancerous = lesion_state_changes[
            lesion_state_changes.message.eq(str(LesionMessage.BECOME_CANCER))
        ]
        cancer_from_med_polyp = lesions_becoming_cancerous[
            lesions_becoming_cancerous.old_state.eq(str(LesionState.MEDIUM_POLYP))
        ]
        replication_output_row["prob_crc_from_medium_polyp"] = possible_zero_division(
            len(cancer_from_med_polyp.index), len(lesions_becoming_cancerous.index)
        )

        # Of all lesions that developed into CRC, proportion that were large-sized
        # polyps immediately prior to becoming cancerous.
        cancer_from_large_polyp = lesions_becoming_cancerous[
            lesions_becoming_cancerous.old_state.eq(str(LesionState.LARGE_POLYP))
        ]
        replication_output_row["prob_crc_from_large_polyp"] = possible_zero_division(
            len(cancer_from_large_polyp.index), len(lesions_becoming_cancerous.index)
        )

        # Among all instances of an individual contracting CRC that developed from a
        # polyp, mean time between the initial formation of the polyp and the onset
        # of CRC.
        polyp_to_pre = indivs_contracted_crc.merge(
            indivs_developed_polyp,
            how="inner",
            on="person_id",
            suffixes=["_cancer", "_polyp_formation"],
        )
        polyp_to_pre["time_polyp_to_pre"] = (
            polyp_to_pre["time_cancer"] - polyp_to_pre["time_polyp_formation"]
        )
        replication_output_row[
            "time_polyp_to_pre"
        ] = polyp_to_pre.time_polyp_to_pre.mean()

        # Among all instances of an individual being clinically diagnosed with CRC,
        # mean time between the onset of CRC and the diagnosis of CRC.
        clinical_detections = disease_state_changes[
            disease_state_changes.message.eq(str(PersonDiseaseMessage.CLINICAL_ONSET))
        ]
        pre_to_clin = clinical_detections.merge(
            indivs_contracted_crc,
            how="inner",
            on="person_id",
            suffixes=["_detection", "_onset"],
        )
        pre_to_clin["time_pre_to_clin"] = (
            pre_to_clin["time_detection"] - pre_to_clin["time_onset"]
        )
        replication_output_row["time_pre_to_clin"] = pre_to_clin.time_pre_to_clin.mean()

        # Proportion of CRC clinical detections in each stage
        stage_counts = clinical_detections.new_state.value_counts()
        stage_counts.index = stage_counts.index.str.replace("CLINICAL_", "").str.lower()
        onset_distrib = stage_counts / len(clinical_detections)
        for stage, value in onset_distrib.items():
            replication_output_row[f"crc_onset_proportion_{stage}"] = value

        # Among all individuals who died from CRC, mean time between the onset of CRC
        # and death.
        pre_to_dead = crc_deaths.merge(
            indivs_contracted_crc,
            how="inner",
            on="person_id",
            suffixes=["_death", "_onset"],
        )
        pre_to_dead["time_pre_to_dead"] = (
            pre_to_dead["time_death"] - pre_to_dead["time_onset"]
        )
        replication_output_row["time_pre_to_dead"] = pre_to_dead.time_pre_to_dead.mean()

        # Among all individuals who died from CRC after being clinically diagnosed with
        # CRC, mean time between the diagnosis of CRC and death.
        clin_to_dead = clinical_detections.merge(
            crc_deaths, how="inner", on="person_id", suffixes=["_clin", "_dead"]
        )
        clin_to_dead["time_clin_to_dead"] = (
            clin_to_dead["time_dead"] - clin_to_dead["time_clin"]
        )
        replication_output_row[
            "time_clin_to_dead"
        ] = clin_to_dead.time_clin_to_dead.mean()

        # Calculate population rates
        status_arrays = self.compute_status_arrays()
        pop_rates = self.compute_pop_rates(status_arrays)
        replication_output_row.update(pop_rates)

        return replication_output_row

    def discount_ages(self, ages_to_discount: pd.Series):
        """
        Takes a Series of ages and returns a Series of discounted ages according to
        the age at which discounting should begin and the discount rate in the model
        parameters.
        """
        discount_age = self.params["lifespan_discount_age"]

        def discount(age: float):
            """
            Discounts a single age.
            """
            # np.arange does not include stop value, hence the +1
            years_to_discount = np.arange(1, math.floor(age) - discount_age + 1)
            rate = np.repeat(
                1 - self.params["lifespan_discount_rate"], len(years_to_discount)
            )
            discounted_years = np.power(rate, years_to_discount)
            partial_year = (age - math.floor(age)) * (
                1 - self.params["lifespan_discount_rate"]
            ) ** (math.ceil(age) - discount_age)
            discounted_age = discount_age + np.sum(discounted_years) + partial_year
            return discounted_age

        discounted_ages = [
            discount(age) if age > discount_age else age for age in ages_to_discount
        ]
        return discounted_ages

    def compute_status_arrays(self):
        """
        Uses disease state changes from raw output to calculate an array for each
        person in the population showing their yearly status on variables used to
        calculate population polyp prevalence, CRC incidence, 5-year survival, and
        CRC mortality rates.
        """
        # We only need disease state changes to calculate these variables.
        output = self.raw_output[self.raw_output.record_type.eq("disease_state_change")]

        # We'll use this a lot
        max_age = self.params["max_age"]

        # Initialize an empty list of person statuses. We'll add an array of
        # statuses by year for each person in the population.
        status_arrays = []

        # Loop through people in the population
        for p in output.person_id.unique():
            person_output = output[output.person_id.eq(p)]

            # Generate annual indicator variables for each variable we will use
            # to calculate population rates. Each variable is calculated as a 1d
            # array. Later we will add these together to get the population totals by year.
            #
            # First, calculate whether the person was alive each year.
            death = person_output[
                person_output.new_state.eq(str(PersonDiseaseState.DEAD))
            ]
            if len(death) == 0:
                raise ValueError(f"Unexpected: no death event for person {p}")
            elif len(death) > 1:
                raise ValueError(
                    f"Unexpected: more than one death event for person {p}"
                )
            else:
                death_age = int(death.time.iloc[0])

            alive = np.arange(max_age + 1)
            alive = np.where(alive > death_age, 0, 1)

            # Calculate whether the person died of CRC each year.
            crc_death = np.repeat(0, max_age + 1)
            if death.message.item() == str(PersonDiseaseMessage.CRC_DEATH):
                crc_death[death_age] = 1

            # Calculate whether the person had a polyp each year. A person is
            # considered to have a polyp at a particular age if, at any point
            # during that year, the person had a lesion that was either a polyp
            # or a cancer.
            #
            # The disease states that entail moving out of polyp and non-polyp
            # states are HEALTHY, SMALL_POLYP, and DEAD. For each state change, we
            # calculate the number of years that the state is active. The number of
            # years each state is active is defined as the time of the next state
            # change minus the time of the current state change.
            polyp_changes = person_output[
                person_output.new_state.isin(
                    [
                        str(PersonDiseaseState.HEALTHY),
                        str(PersonDiseaseState.SMALL_POLYP),
                        str(PersonDiseaseState.DEAD),
                    ]
                )
            ]
            polyp_changes_time_round = np.where(
                polyp_changes.new_state.eq(str(PersonDiseaseState.DEAD)),
                np.ceil(polyp_changes.time),
                np.floor(polyp_changes.time),
            )

            # This adjustment is necessary to count the person as having a polyp on any
            # years they transition from polyp to non-polyp. These transitions occur as a
            # reult of testing, and therefore always occur on integer years.
            #
            # For example, consider a person who develops their first polyp at age 48.7. The
            # polyp is detected and removed at the person's first routine test at age 50.
            #
            # The AnyLogic model counts that person as having had a polyp at age 50.
            #
            # Without this adjustment, this model does not. The transition to a polyp state at
            # time 48.7 is rounded down to 48 via np.floor. The transition back to a non-polyp
            # state due to testing is at time 50. The difference, added to polyp_changes_years
            # via np.diff, is 50 - 48 = 2. This leads to two years where the person is counted
            # as having had a polyp: 48 and 49.
            #
            # This adjustment simply adds a year to the time of every transition from polyp
            # to non-polyp due to testing. To continue the example, the difference becomes
            # 51 - 48 = 3, so the person is counted as having had a polyp for three years:
            # 48, 49, and 50.
            polyp_changes_time_round[
                polyp_changes.new_state.eq(str(PersonDiseaseState.HEALTHY))
                & polyp_changes.old_state.ne(str(PersonDiseaseState.UNINITIALIZED))
            ] += 1

            polyp_changes_years = np.diff(polyp_changes_time_round, append=np.nan)

            # After making the adjustment above, this step is necessary to handle cases
            # where a person transitioned to healthy and then back to polyp in the same
            # year.
            #
            # To continue the example above, assume the person develops another polyp at age 50.4.
            #
            # The transition back to polyp state is rounded down to time 50 via np.floor.
            # Since we adjusted the transition to non-polyp from 50 to 51, this leads to a
            # value of 50 - 51 = -1 in polyp_changes_years. This causes an error in the
            # had_polyp.extend section due to passing a negative number of repeats to np.repeat.
            #
            # We resolve this issue by replacing negative values in polyp_changes_years with 0.
            #
            # This leads to one final complication. The person's time in polyp state after
            # age 50.4 was calculated as 50 - <time of next transition>. However, we've already
            # counted the person as having had a polyp at age 50 due to the adjustment, so year
            # 50 is effectively added to had_polyp twice, and the person's time in polyp state
            # after age 50.4 is one year longer than it should be.
            #
            # We resolve this issue by subtracting a year from all values in polyp_changes_years
            # that immediately follow a negative value.
            for index, year in enumerate(polyp_changes_years):
                if year < 0:
                    polyp_changes_years[index] = 0
                    polyp_changes_years[index + 1] -= 1

            had_polyp = []

            for index, new_state in enumerate(polyp_changes["new_state"]):
                if new_state == str(PersonDiseaseState.HEALTHY):
                    had_polyp.extend(np.repeat(0, polyp_changes_years[index]))
                elif new_state == str(PersonDiseaseState.SMALL_POLYP):
                    had_polyp.extend(np.repeat(1, polyp_changes_years[index]))

            had_polyp[len(had_polyp) : max_age + 1] = np.repeat(
                0, max_age + 1 - len(had_polyp)
            )
            had_polyp = np.array(had_polyp)

            # Calculate whether the person had clinical CRC onset each year.
            # Generate an overall CRC incidence array, as well as one per cancer stage.
            #
            # For people who experienced clinical CRC onset, calculate whether they were
            # alive five years later for five-year survival rate.
            clinical_detection = person_output[
                person_output.message.eq(str(PersonDiseaseMessage.CLINICAL_ONSET))
            ]
            clinical_detection.reset_index(drop=True, inplace=True)

            clinical_onset = np.repeat(0, max_age + 1)
            clinical_onset_stage1 = np.repeat(0, max_age + 1)
            clinical_onset_stage2 = np.repeat(0, max_age + 1)
            clinical_onset_stage3 = np.repeat(0, max_age + 1)
            clinical_onset_stage4 = np.repeat(0, max_age + 1)
            five_year_survival = np.repeat(0, max_age + 1)
            five_year_survival_stage1 = np.repeat(0, max_age + 1)
            five_year_survival_stage2 = np.repeat(0, max_age + 1)
            five_year_survival_stage3 = np.repeat(0, max_age + 1)
            five_year_survival_stage4 = np.repeat(0, max_age + 1)

            if len(clinical_detection) > 0:
                if len(clinical_detection) > 1:
                    raise ValueError(
                        f"Unexpected: more than one clinical onset event for person {p}"
                    )
                # Clinical onset overall
                clinical_detection_age = int(clinical_detection.time.iloc[0])
                clinical_onset[clinical_detection_age] = 1
                # Five-year survival overall
                clinical_detection_age_decimal = float(clinical_detection.time.iloc[0])
                death_age_decimal = float(death.time.iloc[0])
                crc_onset_to_death = death_age_decimal - clinical_detection_age_decimal
                if crc_onset_to_death > 5:
                    five_year_survival[clinical_detection_age] = 1
                # Both by stage
                if clinical_detection.new_state.iat[0] == str(
                    PersonDiseaseState.CLINICAL_STAGE1
                ):
                    clinical_onset_stage1[clinical_detection_age] = 1
                    if crc_onset_to_death > 5:
                        five_year_survival_stage1[clinical_detection_age] = 1
                elif clinical_detection.new_state.iat[0] == str(
                    PersonDiseaseState.CLINICAL_STAGE2
                ):
                    clinical_onset_stage2[clinical_detection_age] = 1
                    if crc_onset_to_death > 5:
                        five_year_survival_stage2[clinical_detection_age] = 1
                elif clinical_detection.new_state.iat[0] == str(
                    PersonDiseaseState.CLINICAL_STAGE3
                ):
                    clinical_onset_stage3[clinical_detection_age] = 1
                    if crc_onset_to_death > 5:
                        five_year_survival_stage3[clinical_detection_age] = 1
                elif clinical_detection.new_state.iat[0] == str(
                    PersonDiseaseState.CLINICAL_STAGE4
                ):
                    clinical_onset_stage4[clinical_detection_age] = 1
                    if crc_onset_to_death > 5:
                        five_year_survival_stage4[clinical_detection_age] = 1

            # Combine 1d arrays as columns into a 2d array
            person_statuses = np.stack(
                [
                    alive,
                    crc_death,
                    had_polyp,
                    clinical_onset,
                    clinical_onset_stage1,
                    clinical_onset_stage2,
                    clinical_onset_stage3,
                    clinical_onset_stage4,
                    five_year_survival,
                    five_year_survival_stage1,
                    five_year_survival_stage2,
                    five_year_survival_stage3,
                    five_year_survival_stage4,
                ],
                axis=1,
            )
            status_arrays.append(person_statuses)
        return status_arrays

    def compute_pop_rates(self, status_arrays: list):
        """
        Takes a list of person status arrays generated by compute_status_arrays
        and uses them to calculate the population polyp prevalence, CRC incidence,
        5-year survival, and CRC mortality rates.
        """
        # Sum all of the person status arrays to get an array of counts of the number of
        # people in each status for each year.
        status_array: np.ndarray = sum(status_arrays)

        # Convert to DataFrame so we can index by column name
        statuses = pd.DataFrame(
            status_array,
            columns=[
                "alive",
                "crc_death",
                "had_polyp",
                "clinical_onset",
                "clinical_onset_stage1",
                "clinical_onset_stage2",
                "clinical_onset_stage3",
                "clinical_onset_stage4",
                "five_year_survival",
                "five_year_survival_stage1",
                "five_year_survival_stage2",
                "five_year_survival_stage3",
                "five_year_survival_stage4",
            ],
        )

        # First, calculate the age-adjusted rates.
        #
        # Divide the columns containing rate numerators by the shared denominator (the
        # number of people alive that year) to generate crude rates. The crude rate is
        # the observed rate in the population.
        crude_crc_mortality_rates = statuses.crc_death / statuses.alive
        crude_polyp_prevalence_rates = statuses.had_polyp / statuses.alive
        crude_crc_incidence_rates = statuses.clinical_onset / statuses.alive
        crude_crc_incidence_rates_stage1 = (
            statuses.clinical_onset_stage1 / statuses.alive
        )
        crude_crc_incidence_rates_stage2 = (
            statuses.clinical_onset_stage2 / statuses.alive
        )
        crude_crc_incidence_rates_stage3 = (
            statuses.clinical_onset_stage3 / statuses.alive
        )
        crude_crc_incidence_rates_stage4 = (
            statuses.clinical_onset_stage4 / statuses.alive
        )

        # Generate age-adjusted rates as the product of the crude rate and the age's
        # proportion in the target population.
        age_adusted_crc_mortality_rates = (
            crude_crc_mortality_rates * self.params["us_age_distribution_rates"]
        )
        age_adusted_polyp_prevalence_rates = (
            crude_polyp_prevalence_rates * self.params["us_age_distribution_rates"]
        )
        age_adusted_crc_incidence_rates = (
            crude_crc_incidence_rates * self.params["us_age_distribution_rates"]
        )
        age_adusted_crc_incidence_rates_stage1 = (
            crude_crc_incidence_rates_stage1 * self.params["us_age_distribution_rates"]
        )
        age_adusted_crc_incidence_rates_stage2 = (
            crude_crc_incidence_rates_stage2 * self.params["us_age_distribution_rates"]
        )
        age_adusted_crc_incidence_rates_stage3 = (
            crude_crc_incidence_rates_stage3 * self.params["us_age_distribution_rates"]
        )
        age_adusted_crc_incidence_rates_stage4 = (
            crude_crc_incidence_rates_stage4 * self.params["us_age_distribution_rates"]
        )

        # Sum the annual age-adjusted rates for the overall age-adjusted rate.
        crc_mortality_rate = age_adusted_crc_mortality_rates.sum()
        polyp_prevalence_rate = age_adusted_polyp_prevalence_rates.sum()
        crc_incidence_rate = age_adusted_crc_incidence_rates.sum()
        crc_incidence_stage1_rate = age_adusted_crc_incidence_rates_stage1.sum()
        crc_incidence_stage2_rate = age_adusted_crc_incidence_rates_stage2.sum()
        crc_incidence_stage3_rate = age_adusted_crc_incidence_rates_stage3.sum()
        crc_incidence_stage4_rate = age_adusted_crc_incidence_rates_stage4.sum()

        # Calculate five-year survival rates using column totals, since these don't need
        # to be age-adjusted.
        crc_survival_rate = (
            statuses.five_year_survival.sum() / statuses.clinical_onset.sum()
        )
        crc_survival_stage1_rate = (
            statuses.five_year_survival_stage1.sum()
            / statuses.clinical_onset_stage1.sum()
        )
        crc_survival_stage2_rate = (
            statuses.five_year_survival_stage2.sum()
            / statuses.clinical_onset_stage2.sum()
        )
        crc_survival_stage3_rate = (
            statuses.five_year_survival_stage3.sum()
            / statuses.clinical_onset_stage3.sum()
        )
        crc_survival_stage4_rate = (
            statuses.five_year_survival_stage4.sum()
            / statuses.clinical_onset_stage4.sum()
        )

        # Calculate five-year survival rates by age group. These will be used for CRC
        # mortality calibration to the age ranges provided in
        # https://ascopubs.org/doi/abs/10.1200/JCO.2018.36.4_suppl.587
        crc_survival_rate_20_64 = (
            statuses.five_year_survival.iloc[20:65].sum()
            / statuses.clinical_onset.iloc[20:65].sum()
        )
        crc_survival_stage1_rate_20_64 = (
            statuses.five_year_survival_stage1.iloc[20:65].sum()
            / statuses.clinical_onset_stage1.iloc[20:65].sum()
        )
        crc_survival_stage2_rate_20_64 = (
            statuses.five_year_survival_stage2.iloc[20:65].sum()
            / statuses.clinical_onset_stage2.iloc[20:65].sum()
        )
        crc_survival_stage3_rate_20_64 = (
            statuses.five_year_survival_stage3.iloc[20:65].sum()
            / statuses.clinical_onset_stage3.iloc[20:65].sum()
        )
        crc_survival_stage4_rate_20_64 = (
            statuses.five_year_survival_stage4.iloc[20:65].sum()
            / statuses.clinical_onset_stage4.iloc[20:65].sum()
        )
        crc_survival_rate_65_100 = (
            statuses.five_year_survival.iloc[65:].sum()
            / statuses.clinical_onset.iloc[65:].sum()
        )
        crc_survival_stage1_rate_65_100 = (
            statuses.five_year_survival_stage1.iloc[65:].sum()
            / statuses.clinical_onset_stage1.iloc[65:].sum()
        )
        crc_survival_stage2_rate_65_100 = (
            statuses.five_year_survival_stage2.iloc[65:].sum()
            / statuses.clinical_onset_stage2.iloc[65:].sum()
        )
        crc_survival_stage3_rate_65_100 = (
            statuses.five_year_survival_stage3.iloc[65:].sum()
            / statuses.clinical_onset_stage3.iloc[65:].sum()
        )
        crc_survival_stage4_rate_65_100 = (
            statuses.five_year_survival_stage4.iloc[65:].sum()
            / statuses.clinical_onset_stage4.iloc[65:].sum()
        )

        # Return all the rates as a dictionary. Output the age-adjusted rates per
        # 100,000 people, because that's how the external sources generally express them.
        rates = {
            "crc_mortality_rate": crc_mortality_rate * 100_000,
            "polyp_prevalence_rate": polyp_prevalence_rate * 100_000,
            "crc_incidence_rate": crc_incidence_rate * 100_000,
            "crc_incidence_stage1_rate": crc_incidence_stage1_rate * 100_000,
            "crc_incidence_stage2_rate": crc_incidence_stage2_rate * 100_000,
            "crc_incidence_stage3_rate": crc_incidence_stage3_rate * 100_000,
            "crc_incidence_stage4_rate": crc_incidence_stage4_rate * 100_000,
            "crc_survival_rate": crc_survival_rate,
            "crc_survival_stage1_rate": crc_survival_stage1_rate,
            "crc_survival_stage2_rate": crc_survival_stage2_rate,
            "crc_survival_stage3_rate": crc_survival_stage3_rate,
            "crc_survival_stage4_rate": crc_survival_stage4_rate,
            "crc_survival_rate_20_64": crc_survival_rate_20_64,
            "crc_survival_stage1_rate_20_64": crc_survival_stage1_rate_20_64,
            "crc_survival_stage2_rate_20_64": crc_survival_stage2_rate_20_64,
            "crc_survival_stage3_rate_20_64": crc_survival_stage3_rate_20_64,
            "crc_survival_stage4_rate_20_64": crc_survival_stage4_rate_20_64,
            "crc_survival_rate_65_100": crc_survival_rate_65_100,
            "crc_survival_stage1_rate_65_100": crc_survival_stage1_rate_65_100,
            "crc_survival_stage2_rate_65_100": crc_survival_stage2_rate_65_100,
            "crc_survival_stage3_rate_65_100": crc_survival_stage3_rate_65_100,
            "crc_survival_stage4_rate_65_100": crc_survival_stage4_rate_65_100,
        }
        # Some rates with zero denominators return NaN. Change those to zero.
        for key, value in rates.items():
            if np.isnan(value):
                rates[key] = 0

        # Add crude polyp prevalence rates by year for comparison to USPSTF
        for i, rate in enumerate(crude_polyp_prevalence_rates):
            rates[f"polyp_prevalence_rate_{i}"] = rate

        # Add age-range-specific age-adjusted incidence rates. These will be used for
        # CRC incidence calibration to the age ranges available via SEER*Explorer.
        def age_range_adjust(
            incidence_rates: pd.Series,
            age_distribution_rates: list,
            start_age: int,
            end_age: int,
        ):
            """
            Age-adjusts incidence rates for a given age range. Age adjustment is conducted
            for the given age range only. In other words, this function multiplies each year's
            incidence rate by the proportion of the population IN THE AGE RANGE which is of
            that age, rather than the proportion of the TOTAL population which is of that age.
            """
            rate_range = incidence_rates[start_age : end_age + 1]
            age_range = age_distribution_rates[start_age : end_age + 1]
            age_total = sum(age_range)
            age_pct_of_range = [i / age_total for i in age_range]
            age_adjusted_rates = rate_range.mul(age_pct_of_range)
            return age_adjusted_rates.sum() * 100_000

        rates["crc_incidence_15_39"] = age_range_adjust(
            crude_crc_incidence_rates, self.params["us_age_distribution_rates"], 15, 39
        )
        rates["crc_incidence_40_64"] = age_range_adjust(
            crude_crc_incidence_rates, self.params["us_age_distribution_rates"], 40, 64
        )
        rates["crc_incidence_65_74"] = age_range_adjust(
            crude_crc_incidence_rates, self.params["us_age_distribution_rates"], 65, 74
        )
        rates["crc_incidence_75_100"] = age_range_adjust(
            crude_crc_incidence_rates, self.params["us_age_distribution_rates"], 75, 100
        )

        return rates


def write_results(results: dict, analysis_file: str):
    fieldnames = results.keys()
    with open(analysis_file, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(results)


def possible_zero_division(numerator, denominator):
    return numerator / denominator if denominator != 0 else 0


def get_screening_cost(
    screening_cost_df: pd.DataFrame, role: TestingRole, denominator: int, discount: bool
):
    filtered_costs = screening_cost_df[screening_cost_df.role.eq(str(role))]
    if discount:
        mean_cost = filtered_costs.discounted_cost.sum() / denominator
    else:
        mean_cost = filtered_costs.cost.sum() / denominator
    return mean_cost


def run(
    params_file="parameters.json",
    outfile="output.csv",
    analysis_file="results.csv",
):
    params = load_params(params_file)

    analysis = Analysis(params=params, raw_output_file=outfile)
    results = analysis.summarize()
    write_results(results, analysis_file)


def main():
    fire.Fire(run)


if __name__ == "__main__":
    main()
