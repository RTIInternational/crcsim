import csv
from typing import Any

from crcsim.agent import (
    LesionMessage,
    LesionState,
    PersonDiseaseMessage,
    PersonDiseaseState,
    TestingRole,
    TreatmentRole,
)


class Output:
    def __init__(self, file_name):
        """
        Create a new Output object designed to write data to a file with the given
        name.

        The object works by accumulating output data in memory via calls to its
        various `add_` methods, and then writing it to disk whenever its
        `commit` method is called.
        """

        self.file_name = file_name
        self.rows = []
        self.file_handle = None
        self.writer = None

    def open(self):
        """
        Open the output file for writing, overwriting the file if it already exists,
        and write the header row.

        Unlike Python's built-in `open()`, this isn't a context manager and
        therefore can't be used in a `with`-block. You should close it
        explicitly when you are done.
        """

        field_names = [
            "record_type",
            "person_id",
            "lesion_id",
            "time",
            "message",
            "old_state",
            "new_state",
            "test_name",
            "routine_test",
            "role",
            "stage",
        ]

        # We're opening the file twice here so that we can open it first in
        # write mode (to overwrite any existing file) and second in append mode
        # (to leave it open for appending throughout the simulation).

        with open(self.file_name, mode="w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=field_names)
            writer.writeheader()

        # \NOQA is to avoid context manager linting, becuase we intentionally want to
        # keep the file open for the lifetime of the simulation. We close it explicitly
        # with the close method.
        self.file_handle = open(self.file_name, mode="a", newline="")  # NOQA: SIM115
        self.writer = csv.DictWriter(self.file_handle, fieldnames=field_names)

    def commit(self):
        """
        Write the accumulated data to the output file, freeing it from memory.
        """

        self.writer.writerows(self.rows)
        self.rows = []

    def close(self):
        """
        Close the output file.
        """

        self.file_handle.close()

    def add_disease_state_change(
        self,
        person_id: Any,
        old_state: PersonDiseaseState,
        new_state: PersonDiseaseState,
        message: PersonDiseaseMessage,
        time: float,
        routine_test: str,
    ):
        self.rows.append(
            {
                "record_type": "disease_state_change",
                "person_id": person_id,
                "old_state": old_state,
                "new_state": new_state,
                "message": message,
                "time": time,
                "routine_test": routine_test,
            }
        )

    def add_lesion_state_change(
        self,
        person_id: Any,
        lesion_id: Any,
        old_state: LesionState,
        new_state: LesionState,
        message: LesionMessage,
        time: float,
    ):
        self.rows.append(
            {
                "record_type": "lesion_state_change",
                "person_id": person_id,
                "lesion_id": lesion_id,
                "old_state": old_state,
                "new_state": new_state,
                "message": message,
                "time": time,
            }
        )

    def add_noncompliance(
        self, person_id: Any, test_name: str, role: TestingRole, time: float
    ):
        self.rows.append(
            {
                "record_type": "noncompliance",
                "person_id": person_id,
                "test_name": test_name,
                "role": role,
                "time": time,
            }
        )

    def add_expected_lifespan(self, person_id: Any, time: float):
        self.rows.append(
            {"record_type": "lifespan", "person_id": person_id, "time": time}
        )

    def add_routine_test_chosen(self, person_id: Any, test_name: str, time: float):
        self.rows.append(
            {
                "record_type": "test_chosen",
                "person_id": person_id,
                "test_name": test_name,
                "role": TestingRole.ROUTINE,
                "time": time,
            }
        )

    def add_test_performed(
        self, person_id: Any, test_name: str, role: TestingRole, time: float
    ):
        self.rows.append(
            {
                "record_type": "test_performed",
                "person_id": person_id,
                "test_name": test_name,
                "role": role,
                "time": time,
            }
        )

    def add_perforation(
        self,
        person_id: Any,
        test_name: str,
        role: TestingRole,
        time: float,
        routine_test: str,
    ):
        self.rows.append(
            {
                "record_type": "perforation",
                "person_id": person_id,
                "test_name": test_name,
                "role": role,
                "time": time,
                "routine_test": routine_test,
            }
        )

    def add_polypectomy(self, person_id: Any, role: TestingRole, time: float):
        self.rows.append(
            {
                "record_type": "polypectomy",
                "person_id": person_id,
                "role": role,
                "time": time,
            }
        )

    def add_pathology(
        self, person_id: Any, lesion_id: Any, role: TestingRole, time: float
    ):
        self.rows.append(
            {
                "record_type": "pathology",
                "person_id": person_id,
                "lesion_id": lesion_id,
                "role": role,
                "time": time,
            }
        )

    def add_treatment(
        self, person_id: Any, stage: int, role: TreatmentRole, time: float
    ):
        self.rows.append(
            {
                "record_type": "treatment",
                "person_id": person_id,
                "stage": stage,
                "role": role,
                "time": time,
            }
        )
