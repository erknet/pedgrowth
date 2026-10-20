"""Provider-neutral pediatric growth calculation engine."""

# Independently installed providers contribute pedgrowth.data.<provider> portions.
# pedgrowth itself remains a regular package with a stable top-level API.
from pkgutil import extend_path as _extend_path

__path__ = _extend_path(__path__, __name__)


from .architecture import (
    AgeDefinition,
    AgeType,
    AgeUnit,
    CoordinateType,
    GrowthResult,
    Indicator,
    ReferencePlan,
    ResolvedReference,
    TableDomain,
)
from .extra_tables import CsvGrowthTable, TableDefinition
from .plans import GrowthPlan
from .policies import InterpolationPolicy, MeasurementPosition, ReferenceStandard
from .provenance import ReferenceProvenance, bundled_references
from .pygrowup import GrowthChartsCalculator
from .registry import (
    ReferenceBatchCandidate,
    ReferenceCandidate,
    ReferenceProvider,
    ReferenceRegistry,
    available_plans,
    available_providers,
    create_plan,
    registry,
)
from .tables import Sex, TableType

__version__ = "1.0.0"


def get_version(short: bool = False) -> str:
    return __version__


__all__ = [
    "GrowthChartsCalculator",
    "Indicator",
    "CoordinateType",
    "TableDomain",
    "AgeDefinition",
    "AgeType",
    "AgeUnit",
    "GrowthPlan",
    "ReferencePlan",
    "ResolvedReference",
    "GrowthResult",
    "ReferenceProvenance",
    "bundled_references",
    "Sex",
    "TableType",
    "ReferenceStandard",
    "InterpolationPolicy",
    "MeasurementPosition",
    "TableDefinition",
    "CsvGrowthTable",
    "ReferenceProvider",
    "ReferenceCandidate",
    "ReferenceBatchCandidate",
    "ReferenceRegistry",
    "registry",
    "available_providers",
    "available_plans",
    "create_plan",
    "get_version",
    "__version__",
]
