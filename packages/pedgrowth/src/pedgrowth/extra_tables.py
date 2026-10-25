"""Declarative, data-only external growth-reference tables.

Custom reference *data* do not require Python subclasses, dynamic imports,
or extending the registry. To change calculation algorithms, implement a
trusted GrowthTable subclass and use the existing override_tables interface.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from .provenance import ReferenceProvenance
from .tables.lms import LMS
from .tables.sex import Sex
from .tables.table import LMSTable, TableType


@dataclass(frozen=True, slots=True)
class TableDefinition:
    """External normalized CSV for an existing anthropometric indicator.

    Sex=None means the file contains both M and F partitions (CDC format).
    Sex.Male / Sex.Female indicate a single partition with a blank sex
    column (WHO format). Definitions are prioritized before default tables.
    """

    name: str
    indicator: TableType
    source: Path
    sex: Sex | None = None
    extended_bmi: bool = False
    reference_version: str = "user-supplied"
    source_url: str | None = None
    standard_name: str = "custom"

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", self.name):
            raise ValueError("Reference table name must be an alphanumeric identifier")
        if not isinstance(self.indicator, TableType):
            raise TypeError("indicator must be a TableType")
        if not isinstance(self.source, Path):
            raise TypeError("source must be a pathlib.Path")
        if self.sex is not None and not isinstance(self.sex, Sex):
            raise TypeError("sex must be Sex.Male or Sex.Female")
        if self.extended_bmi and self.indicator is not TableType.BodyMassIndexForAge:
            raise ValueError("Extended BMI coefficients require BMI-for-age indicator")


class CsvGrowthTable(LMSTable):
    """GrowthTable adapter for declarative local CSV reference data."""

    def __init__(self, definition: TableDefinition) -> None:
        self._definition = definition
        self._data_sha256: str | None = None
        super().__init__()
        self.override_sha256 = self._data_sha256

    def get_file_name(self) -> str:
        return self._definition.name

    def get_provenance(self) -> ReferenceProvenance:
        definition = self._definition
        return ReferenceProvenance(
            name=definition.name,
            standard=definition.standard_name,
            reference_version=definition.reference_version,
            source_url=definition.source_url,
            source_sha256=None,
            data_sha256=self._data_sha256 or "",
            snapshot_date=None,
            custom=True,
        )

    def get_table_type(self) -> TableType:
        return self._definition.indicator

    def get_table_sex(self) -> Sex | None:
        return self._definition.sex

    def get_col_index_sex(self) -> int | None:
        return 0 if self._definition.sex is None else None

    def get_col_index_sigma(self) -> int | None:
        return 5 if self._definition.extended_bmi else None

    def get_table(self) -> Mapping[Sex | None, Mapping[float, LMS]]:
        from .reference_data import read_override_csv

        table, digest = read_override_csv(self._definition.source)
        self._data_sha256 = digest
        return table
