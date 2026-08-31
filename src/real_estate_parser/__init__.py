"""Public library surface for the real estate parser."""

from real_estate_parser.fixture_source_batch import load_fixture_source_batch
from real_estate_parser.source_batch import (
    ContractIssue,
    InputLocation,
    MissingSourceField,
    SourceBatchLoadFailure,
    SourceBatchLoadResult,
    SourceBatchLoadSuccess,
    ValidatedSourceBatch,
    ValidatedSourceField,
    ValidatedSourceListing,
)

__version__ = "0.1.0"

__all__ = [
    "ContractIssue",
    "InputLocation",
    "MissingSourceField",
    "SourceBatchLoadFailure",
    "SourceBatchLoadResult",
    "SourceBatchLoadSuccess",
    "ValidatedSourceBatch",
    "ValidatedSourceField",
    "ValidatedSourceListing",
    "__version__",
    "load_fixture_source_batch",
]
