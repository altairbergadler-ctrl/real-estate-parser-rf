"""Consumer-owned publication persistence contracts from ADR 0010.

The records in this module describe exact reads, optimistic commits, replay,
and structural failures.  They deliberately contain no storage technology,
serialization, filesystem, network, or execution policy.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal, Protocol, runtime_checkable

from real_estate_parser.publication_duplicate_assessment_batches import (
    DuplicateCandidateAssessmentBatch,
    DuplicateCandidateAssessmentBatchIdentity,
)
from real_estate_parser.publication_duplicate_assessments import (
    AssessmentSupersession,
    DuplicateAssessmentIdentity,
    DuplicatePairAssessment,
    DuplicatePairManualReview,
    ManualReviewIdentity,
    ReviewReferenceCode,
)
from real_estate_parser.publication_duplicate_candidates import (
    DuplicateCandidateGenerationIdentity,
    DuplicateCandidateGenerationResult,
)
from real_estate_parser.publication_duplicate_quality import DuplicatePolicyControlSet
from real_estate_parser.publication_observation_batches import ObservationBatchAppendSuccess
from real_estate_parser.publication_observations import (
    AvailableObservation,
    ComparisonPolicyVersion,
    ObservationKey,
    PublicationObservation,
    PublicationObservationHistory,
    UnavailableObservation,
)
from real_estate_parser.source_batch import PublicationRef


def _reference_key(reference: PublicationRef) -> tuple[str, str]:
    return reference.source_id.value, reference.publication_id.value


def _observation_key(key: ObservationKey) -> tuple[str, str, object]:
    return (*_reference_key(key.reference), key.observed_at.value)


def _review_identity_key(identity: ManualReviewIdentity) -> tuple[str, int]:
    return identity.review_reference_code.value, identity.revision


def _generation_identity_key(
    identity: DuplicateCandidateGenerationIdentity,
) -> tuple[object, ...]:
    return (
        identity.candidate_policy_version.value,
        identity.bucket_pair_limit.value,
        tuple(_observation_key(key) for key in identity.canonical_input_keys),
    )


def _assessment_identity_key(identity: DuplicateAssessmentIdentity) -> tuple[object, ...]:
    return (
        *_reference_key(identity.pair.left),
        *_reference_key(identity.pair.right),
        identity.left_observation_key.observed_at.value,
        identity.right_observation_key.observed_at.value,
        identity.policy_version.value,
    )


@dataclass(frozen=True, slots=True, init=False)
class PersistenceRevision:
    """Opaque adapter-issued compare-and-commit token."""

    _value: int

    def __init__(self, value: int, *, _issuer: object) -> None:
        if _issuer is not _REVISION_ISSUER:
            raise TypeError("persistence revisions are issued only by adapters")
        if type(value) is not int or value < 1:
            raise ValueError("persistence revision value must be a positive integer")
        object.__setattr__(self, "_value", value)

    def __repr__(self) -> str:
        return "PersistenceRevision(<opaque>)"


_REVISION_ISSUER = object()


def _issue_persistence_revision(value: int, *, issuer: object) -> PersistenceRevision:
    """Issue a token for an adapter that holds the private module issuer.

    This function is not re-exported from the package surface.  Reference
    adapters pass the exact private issuer object obtained by the internal
    helper below; consumers cannot construct revisions from domain values.
    """

    if issuer is not _REVISION_ISSUER:
        raise TypeError("invalid persistence revision issuer")
    return PersistenceRevision(value, _issuer=_REVISION_ISSUER)


def _persistence_revision_issuer() -> object:
    """Return the private issuer to infrastructure code in this package."""

    return _REVISION_ISSUER


@dataclass(frozen=True, slots=True)
class ExpectAbsent:
    """Require a slot or head to be absent at commit time."""


@dataclass(frozen=True, slots=True)
class ExpectExact:
    """Require a slot or head to have the exact loaded revision."""

    revision: PersistenceRevision

    def __post_init__(self) -> None:
        if not isinstance(self.revision, PersistenceRevision):
            raise TypeError("exact expectation requires a persistence revision")


type ExpectedRevision = ExpectAbsent | ExpectExact


class CommitDisposition(StrEnum):
    """Whether a commit added content or replayed exact retained content."""

    COMMITTED = "COMMITTED"
    REPLAYED = "REPLAYED"


class PersistenceOperationFailureCode(StrEnum):
    """Operational failure that does not assert a domain conflict."""

    TEMPORARILY_UNAVAILABLE = "temporarily_unavailable"
    INTEGRITY_VIOLATION = "integrity_violation"
    OUTCOME_UNKNOWN = "outcome_unknown"


class PersistencePortName(StrEnum):
    OBSERVATION_HISTORY = "observation_history"
    DUPLICATE_GENERATION = "duplicate_generation"
    DUPLICATE_ASSESSMENT = "duplicate_assessment"
    MANUAL_REVIEW = "manual_review"
    DUPLICATE_QUALITY = "duplicate_quality"


class PersistenceOperationName(StrEnum):
    LOAD_HISTORIES = "load_histories"
    LOAD_OBSERVATIONS = "load_observations"
    COMMIT_HISTORIES = "commit_histories"
    LOAD_GENERATION = "load_generation"
    COMMIT_GENERATION = "commit_generation"
    LOAD_ASSESSMENT_BATCH = "load_assessment_batch"
    LOAD_PAIR_ASSESSMENT = "load_pair_assessment"
    COMMIT_ASSESSMENT_BATCH = "commit_assessment_batch"
    COMMIT_ASSESSMENT_SUPERSESSION = "commit_assessment_supersession"
    LOAD_MANUAL_REVIEW_CHAIN = "load_manual_review_chain"
    COMMIT_MANUAL_REVIEW = "commit_manual_review"
    LOAD_QUALITY_AUDIT = "load_quality_audit"
    COMMIT_QUALITY_AUDIT = "commit_quality_audit"


type PersistenceOperationIdentity = (
    PublicationRef
    | ObservationKey
    | DuplicateCandidateGenerationIdentity
    | DuplicateCandidateAssessmentBatchIdentity
    | DuplicateAssessmentIdentity
    | AssessmentSupersession
    | ReviewReferenceCode
    | ManualReviewIdentity
    | "QualityAuditIdentity"
)


@dataclass(frozen=True, slots=True)
class PersistenceOperationSubject:
    """Typed operational coordinate safe to expose to a consumer."""

    port: PersistencePortName
    operation: PersistenceOperationName
    identity: PersistenceOperationIdentity

    def __post_init__(self) -> None:
        if not isinstance(self.port, PersistencePortName):
            raise TypeError("operation subject requires a persistence port")
        if not isinstance(self.operation, PersistenceOperationName):
            raise TypeError("operation subject requires a persistence operation")
        if not isinstance(
            self.identity,
            (
                PublicationRef,
                ObservationKey,
                DuplicateCandidateGenerationIdentity,
                DuplicateCandidateAssessmentBatchIdentity,
                DuplicateAssessmentIdentity,
                AssessmentSupersession,
                ReviewReferenceCode,
                ManualReviewIdentity,
                QualityAuditIdentity,
            ),
        ):
            raise TypeError("operation subject requires a supported structural identity")


@dataclass(frozen=True, slots=True)
class PersistenceOperationFailure:
    """Typed operational failure with no partial successful state."""

    code: PersistenceOperationFailureCode
    subject: PersistenceOperationSubject

    def __post_init__(self) -> None:
        if not isinstance(self.code, PersistenceOperationFailureCode):
            raise TypeError("operation failure requires a supported code")
        if not isinstance(self.subject, PersistenceOperationSubject):
            raise TypeError("operation failure requires an operation subject")


@dataclass(frozen=True, slots=True)
class LoadObservationHistoriesRequest:
    references: tuple[PublicationRef, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.references, tuple):
            raise TypeError("history references must be a tuple")
        if not self.references:
            raise ValueError("history load requires a reference")
        if any(not isinstance(reference, PublicationRef) for reference in self.references):
            raise TypeError("history load contains an unsupported reference")
        if len(set(self.references)) != len(self.references):
            raise ValueError("history load references must be unique")
        if self.references != tuple(sorted(self.references, key=_reference_key)):
            raise ValueError("history load references must be canonical")


@dataclass(frozen=True, slots=True)
class LoadedHistoryEntry:
    reference: PublicationRef
    history: PublicationObservationHistory | None
    revision: PersistenceRevision | None

    def __post_init__(self) -> None:
        if not isinstance(self.reference, PublicationRef):
            raise TypeError("loaded history entry requires a publication reference")
        if (self.history is None) != (self.revision is None):
            raise ValueError("history and revision must be both present or both absent")
        if self.history is not None:
            if not isinstance(self.history, PublicationObservationHistory):
                raise TypeError("loaded history entry contains an unsupported history")
            if self.history.reference != self.reference:
                raise ValueError("loaded history entry reference does not match history")
            if not isinstance(self.revision, PersistenceRevision):
                raise TypeError("loaded history entry contains an unsupported revision")


@dataclass(frozen=True, slots=True)
class LoadObservationHistoriesSuccess:
    entries: tuple[LoadedHistoryEntry, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.entries, tuple):
            raise TypeError("loaded history entries must be a tuple")
        if not self.entries:
            raise ValueError("history load success requires an entry")
        if any(not isinstance(entry, LoadedHistoryEntry) for entry in self.entries):
            raise TypeError("history load success contains an unsupported entry")
        references = tuple(entry.reference for entry in self.entries)
        if len(set(references)) != len(references):
            raise ValueError("loaded history entries must be unique")
        if references != tuple(sorted(references, key=_reference_key)):
            raise ValueError("loaded history entries must be canonical")


type LoadObservationHistoriesOutcome = LoadObservationHistoriesSuccess | PersistenceOperationFailure


@dataclass(frozen=True, slots=True)
class LoadObservationsByKeyRequest:
    keys: tuple[ObservationKey, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.keys, tuple):
            raise TypeError("observation keys must be a tuple")
        if not self.keys:
            raise ValueError("observation load requires a key")
        if any(not isinstance(key, ObservationKey) for key in self.keys):
            raise TypeError("observation load contains an unsupported key")
        if len(set(self.keys)) != len(self.keys):
            raise ValueError("observation load keys must be unique")
        if self.keys != tuple(sorted(self.keys, key=_observation_key)):
            raise ValueError("observation load keys must be canonical")


@dataclass(frozen=True, slots=True)
class LoadObservationsByKeySuccess:
    observations: tuple[PublicationObservation, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.observations, tuple):
            raise TypeError("loaded observations must be a tuple")
        if not self.observations:
            raise ValueError("observation load success requires an observation")
        if any(
            not isinstance(observation, (AvailableObservation, UnavailableObservation))
            for observation in self.observations
        ):
            raise TypeError("observation load success contains an unsupported observation")
        keys = tuple(observation.key for observation in self.observations)
        if len(set(keys)) != len(keys):
            raise ValueError("loaded observations must have unique keys")
        if keys != tuple(sorted(keys, key=_observation_key)):
            raise ValueError("loaded observations must be canonical")


@dataclass(frozen=True, slots=True)
class ObservationHistoryCommitIdentity:
    comparison_policy_version: ComparisonPolicyVersion
    candidate_keys: tuple[ObservationKey, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.comparison_policy_version, ComparisonPolicyVersion):
            raise TypeError("history commit identity requires a comparison policy version")
        if not isinstance(self.candidate_keys, tuple):
            raise TypeError("history commit candidate keys must be a tuple")
        if not self.candidate_keys:
            raise ValueError("history commit identity requires a candidate key")
        if any(not isinstance(key, ObservationKey) for key in self.candidate_keys):
            raise TypeError("history commit identity contains an unsupported key")
        if len(set(self.candidate_keys)) != len(self.candidate_keys):
            raise ValueError("history commit candidate keys must be unique")
        if self.candidate_keys != tuple(sorted(self.candidate_keys, key=_observation_key)):
            raise ValueError("history commit candidate keys must be canonical")


@dataclass(frozen=True, slots=True)
class ExpectedHistoryHead:
    reference: PublicationRef
    expected_revision: ExpectedRevision

    def __post_init__(self) -> None:
        if not isinstance(self.reference, PublicationRef):
            raise TypeError("expected history head requires a publication reference")
        if not isinstance(self.expected_revision, (ExpectAbsent, ExpectExact)):
            raise TypeError("expected history head requires an explicit expectation")


@dataclass(frozen=True, slots=True)
class ObservationHistoryCommitRequest:
    identity: ObservationHistoryCommitIdentity
    expected_heads: tuple[ExpectedHistoryHead, ...]
    candidates: tuple[PublicationObservation, ...]
    prepared_result: ObservationBatchAppendSuccess

    def __post_init__(self) -> None:
        if not isinstance(self.identity, ObservationHistoryCommitIdentity):
            raise TypeError("history commit requires a commit identity")
        if not isinstance(self.expected_heads, tuple) or not self.expected_heads:
            raise ValueError("history commit requires expected heads as a non-empty tuple")
        if any(not isinstance(head, ExpectedHistoryHead) for head in self.expected_heads):
            raise TypeError("history commit contains an unsupported expected head")
        references = tuple(head.reference for head in self.expected_heads)
        if len(set(references)) != len(references):
            raise ValueError("history commit expected heads must be unique")
        if references != tuple(sorted(references, key=_reference_key)):
            raise ValueError("history commit expected heads must be canonical")
        if not isinstance(self.candidates, tuple) or not self.candidates:
            raise ValueError("history commit requires candidates as a non-empty tuple")
        if any(
            not isinstance(candidate, (AvailableObservation, UnavailableObservation))
            for candidate in self.candidates
        ):
            raise TypeError("history commit contains an unsupported candidate")
        keys = tuple(candidate.key for candidate in self.candidates)
        if keys != self.identity.candidate_keys:
            raise ValueError("history commit candidates do not match commit identity")
        if not isinstance(self.prepared_result, ObservationBatchAppendSuccess):
            raise TypeError("history commit requires a complete prepared success")
        if tuple(outcome.key for outcome in self.prepared_result.outcomes) != keys:
            raise ValueError("prepared outcomes do not match commit candidate keys")
        prepared_references = tuple(
            history.reference for history in self.prepared_result.histories.histories
        )
        if prepared_references != references:
            raise ValueError("prepared histories do not match expected heads")
        if set(key.reference for key in keys) != set(references):
            raise ValueError("history commit must expect every affected candidate reference")
        if any(
            history.comparison_policy_version != self.identity.comparison_policy_version
            for history in self.prepared_result.histories.histories
        ):
            raise ValueError("prepared history policy does not match commit identity")


@dataclass(frozen=True, slots=True)
class CommittedHistoryHead:
    reference: PublicationRef
    history: PublicationObservationHistory
    revision: PersistenceRevision

    def __post_init__(self) -> None:
        if not isinstance(self.reference, PublicationRef):
            raise TypeError("committed history head requires a publication reference")
        if not isinstance(self.history, PublicationObservationHistory):
            raise TypeError("committed history head requires a publication history")
        if self.history.reference != self.reference:
            raise ValueError("committed history head reference does not match history")
        if not isinstance(self.revision, PersistenceRevision):
            raise TypeError("committed history head requires a persistence revision")


@dataclass(frozen=True, slots=True)
class ObservationHistoryCommitSuccess:
    disposition: CommitDisposition
    heads: tuple[CommittedHistoryHead, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.disposition, CommitDisposition):
            raise TypeError("history commit success requires a disposition")
        if not isinstance(self.heads, tuple) or not self.heads:
            raise ValueError("history commit success requires committed heads")
        if any(not isinstance(head, CommittedHistoryHead) for head in self.heads):
            raise TypeError("history commit success contains an unsupported head")
        references = tuple(head.reference for head in self.heads)
        if references != tuple(sorted(references, key=_reference_key)):
            raise ValueError("committed history heads must be canonical")
        if len(set(references)) != len(references):
            raise ValueError("committed history heads must be unique")


class ObservationPersistenceConflictCode(StrEnum):
    COMMIT_IDENTITY_CONTENT_CONFLICT = "commit_identity_content_conflict"
    EXPECTED_REVISION_MISMATCH = "expected_revision_mismatch"
    PREPARED_HISTORY_MISMATCH = "prepared_history_mismatch"
    UNSUPPORTED_OUT_OF_ORDER_COMMIT = "unsupported_out_of_order_commit"
    OBSERVATION_NOT_FOUND = "observation_not_found"


@dataclass(frozen=True, slots=True)
class ObservationIdentityContentSubject:
    identity: ObservationHistoryCommitIdentity

    def __post_init__(self) -> None:
        if not isinstance(self.identity, ObservationHistoryCommitIdentity):
            raise TypeError("observation content subject requires a commit identity")


@dataclass(frozen=True, slots=True)
class ObservationExpectedRevisionSubject:
    reference: PublicationRef
    expected: ExpectedRevision
    actual: PersistenceRevision | None

    def __post_init__(self) -> None:
        if not isinstance(self.reference, PublicationRef):
            raise TypeError("observation revision subject requires a publication reference")
        if not isinstance(self.expected, (ExpectAbsent, ExpectExact)):
            raise TypeError("observation revision subject requires an explicit expectation")
        if self.actual is not None and not isinstance(self.actual, PersistenceRevision):
            raise TypeError("observation revision subject actual token is unsupported")


@dataclass(frozen=True, slots=True)
class ObservationPreparedHistorySubject:
    identity: ObservationHistoryCommitIdentity
    reference: PublicationRef

    def __post_init__(self) -> None:
        if not isinstance(self.identity, ObservationHistoryCommitIdentity):
            raise TypeError("prepared history subject requires a commit identity")
        if not isinstance(self.reference, PublicationRef):
            raise TypeError("prepared history subject requires a publication reference")


type ObservationPersistenceConflictSubject = (
    ObservationIdentityContentSubject
    | ObservationExpectedRevisionSubject
    | ObservationPreparedHistorySubject
    | ObservationKey
)


@dataclass(frozen=True, slots=True)
class ObservationPersistenceConflict:
    category: Literal["OBSERVATION_PERSISTENCE_CONFLICT"]
    code: ObservationPersistenceConflictCode
    subject: ObservationPersistenceConflictSubject

    def __post_init__(self) -> None:
        if self.category != "OBSERVATION_PERSISTENCE_CONFLICT":
            raise ValueError("invalid observation persistence conflict category")
        if not isinstance(self.code, ObservationPersistenceConflictCode):
            raise TypeError("unsupported observation persistence conflict code")
        identity_codes = {
            ObservationPersistenceConflictCode.UNSUPPORTED_OUT_OF_ORDER_COMMIT,
            ObservationPersistenceConflictCode.OBSERVATION_NOT_FOUND,
        }
        subject_matches = (
            (
                self.code is ObservationPersistenceConflictCode.COMMIT_IDENTITY_CONTENT_CONFLICT
                and isinstance(self.subject, ObservationIdentityContentSubject)
            )
            or (
                self.code is ObservationPersistenceConflictCode.EXPECTED_REVISION_MISMATCH
                and isinstance(self.subject, ObservationExpectedRevisionSubject)
            )
            or (
                self.code is ObservationPersistenceConflictCode.PREPARED_HISTORY_MISMATCH
                and isinstance(self.subject, ObservationPreparedHistorySubject)
            )
            or (self.code in identity_codes and isinstance(self.subject, ObservationKey))
        )
        if not subject_matches:
            raise TypeError("observation persistence conflict subject does not match code")


def _observation_conflict_key(conflict: ObservationPersistenceConflict) -> tuple[object, ...]:
    code_order = {
        code: position for position, code in enumerate(ObservationPersistenceConflictCode)
    }
    subject = conflict.subject
    if isinstance(subject, ObservationExpectedRevisionSubject):
        subject_key: tuple[object, ...] = _reference_key(subject.reference)
    elif isinstance(subject, ObservationPreparedHistorySubject):
        subject_key = _reference_key(subject.reference)
    elif isinstance(subject, ObservationKey):
        subject_key = _observation_key(subject)
    else:
        subject_key = tuple(_observation_key(key) for key in subject.identity.candidate_keys)
    return code_order[conflict.code], *subject_key, conflict.code.value


@dataclass(frozen=True, slots=True)
class ObservationHistoryCommitFailure:
    conflicts: tuple[ObservationPersistenceConflict, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.conflicts, tuple) or not self.conflicts:
            raise ValueError("history commit failure requires conflicts as a non-empty tuple")
        if any(not isinstance(item, ObservationPersistenceConflict) for item in self.conflicts):
            raise TypeError("history commit failure contains an unsupported conflict")
        canonical = tuple(sorted(set(self.conflicts), key=_observation_conflict_key))
        object.__setattr__(self, "conflicts", canonical)


type ObservationHistoryCommitOutcome = (
    ObservationHistoryCommitSuccess | ObservationHistoryCommitFailure | PersistenceOperationFailure
)
type LoadObservationsByKeyOutcome = (
    LoadObservationsByKeySuccess | ObservationHistoryCommitFailure | PersistenceOperationFailure
)


@dataclass(frozen=True, slots=True)
class LoadDuplicateGenerationRequest:
    identity: DuplicateCandidateGenerationIdentity

    def __post_init__(self) -> None:
        if not isinstance(self.identity, DuplicateCandidateGenerationIdentity):
            raise TypeError("generation load requires a generation identity")


@dataclass(frozen=True, slots=True)
class GenerationFound:
    result: DuplicateCandidateGenerationResult
    revision: PersistenceRevision

    def __post_init__(self) -> None:
        if not isinstance(self.result, DuplicateCandidateGenerationResult):
            raise TypeError("found generation requires a complete generation result")
        if not isinstance(self.revision, PersistenceRevision):
            raise TypeError("found generation requires a persistence revision")


@dataclass(frozen=True, slots=True)
class GenerationNotFound:
    """Exact generation identity is absent."""


type LoadedDuplicateGeneration = GenerationFound | GenerationNotFound | PersistenceOperationFailure


@dataclass(frozen=True, slots=True)
class CommitDuplicateGenerationRequest:
    expected_revision: ExpectedRevision
    result: DuplicateCandidateGenerationResult

    def __post_init__(self) -> None:
        if not isinstance(self.expected_revision, (ExpectAbsent, ExpectExact)):
            raise TypeError("generation commit requires an explicit expectation")
        if not isinstance(self.result, DuplicateCandidateGenerationResult):
            raise TypeError("generation commit requires a complete generation result")


@dataclass(frozen=True, slots=True)
class CommitDuplicateGenerationSuccess:
    disposition: CommitDisposition
    result: DuplicateCandidateGenerationResult
    revision: PersistenceRevision

    def __post_init__(self) -> None:
        if not isinstance(self.disposition, CommitDisposition):
            raise TypeError("generation commit success requires a disposition")
        if not isinstance(self.result, DuplicateCandidateGenerationResult):
            raise TypeError("generation commit success requires a complete result")
        if not isinstance(self.revision, PersistenceRevision):
            raise TypeError("generation commit success requires a persistence revision")


class DuplicateGenerationPersistenceConflictCode(StrEnum):
    GENERATION_IDENTITY_CONTENT_CONFLICT = "generation_identity_content_conflict"
    EXPECTED_REVISION_MISMATCH = "expected_revision_mismatch"


@dataclass(frozen=True, slots=True)
class GenerationIdentityContentSubject:
    identity: DuplicateCandidateGenerationIdentity

    def __post_init__(self) -> None:
        if not isinstance(self.identity, DuplicateCandidateGenerationIdentity):
            raise TypeError("generation content subject requires a generation identity")


@dataclass(frozen=True, slots=True)
class GenerationExpectedRevisionSubject:
    identity: DuplicateCandidateGenerationIdentity
    expected: ExpectedRevision
    actual: PersistenceRevision | None

    def __post_init__(self) -> None:
        if not isinstance(self.identity, DuplicateCandidateGenerationIdentity):
            raise TypeError("generation revision subject requires a generation identity")
        if not isinstance(self.expected, (ExpectAbsent, ExpectExact)):
            raise TypeError("generation revision subject requires an explicit expectation")
        if self.actual is not None and not isinstance(self.actual, PersistenceRevision):
            raise TypeError("generation revision subject actual token is unsupported")


type DuplicateGenerationPersistenceConflictSubject = (
    GenerationIdentityContentSubject | GenerationExpectedRevisionSubject
)


@dataclass(frozen=True, slots=True)
class DuplicateGenerationPersistenceConflict:
    category: Literal["DUPLICATE_GENERATION_PERSISTENCE_CONFLICT"]
    code: DuplicateGenerationPersistenceConflictCode
    subject: DuplicateGenerationPersistenceConflictSubject

    def __post_init__(self) -> None:
        if self.category != "DUPLICATE_GENERATION_PERSISTENCE_CONFLICT":
            raise ValueError("invalid generation persistence conflict category")
        if not isinstance(self.code, DuplicateGenerationPersistenceConflictCode):
            raise TypeError("unsupported generation persistence conflict code")
        expected_type = (
            GenerationIdentityContentSubject
            if self.code
            is DuplicateGenerationPersistenceConflictCode.GENERATION_IDENTITY_CONTENT_CONFLICT
            else GenerationExpectedRevisionSubject
        )
        if not isinstance(self.subject, expected_type):
            raise TypeError("generation persistence conflict subject does not match code")


@dataclass(frozen=True, slots=True)
class CommitDuplicateGenerationFailure:
    conflicts: tuple[DuplicateGenerationPersistenceConflict, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.conflicts, tuple) or not self.conflicts:
            raise ValueError("generation commit failure requires conflicts")
        if any(
            not isinstance(item, DuplicateGenerationPersistenceConflict) for item in self.conflicts
        ):
            raise TypeError("generation commit failure contains an unsupported conflict")
        order = {
            code: position
            for position, code in enumerate(DuplicateGenerationPersistenceConflictCode)
        }

        def conflict_key(
            item: DuplicateGenerationPersistenceConflict,
        ) -> tuple[object, ...]:
            return (
                order[item.code],
                *_generation_identity_key(item.subject.identity),
                item.code.value,
            )

        canonical = tuple(sorted(set(self.conflicts), key=conflict_key))
        object.__setattr__(self, "conflicts", canonical)


type CommitDuplicateGenerationOutcome = (
    CommitDuplicateGenerationSuccess
    | CommitDuplicateGenerationFailure
    | PersistenceOperationFailure
)


@dataclass(frozen=True, slots=True)
class LoadDuplicateAssessmentBatchRequest:
    identity: DuplicateCandidateAssessmentBatchIdentity

    def __post_init__(self) -> None:
        if not isinstance(self.identity, DuplicateCandidateAssessmentBatchIdentity):
            raise TypeError("assessment batch load requires a batch identity")


@dataclass(frozen=True, slots=True)
class AssessmentBatchFound:
    batch: DuplicateCandidateAssessmentBatch
    revision: PersistenceRevision

    def __post_init__(self) -> None:
        if not isinstance(self.batch, DuplicateCandidateAssessmentBatch):
            raise TypeError("found assessment batch requires a complete batch")
        if not isinstance(self.revision, PersistenceRevision):
            raise TypeError("found assessment batch requires a persistence revision")


@dataclass(frozen=True, slots=True)
class AssessmentBatchNotFound:
    """Exact assessment batch identity is absent."""


type LoadedDuplicateAssessmentBatch = (
    AssessmentBatchFound | AssessmentBatchNotFound | PersistenceOperationFailure
)


@dataclass(frozen=True, slots=True)
class LoadDuplicatePairAssessmentRequest:
    identity: DuplicateAssessmentIdentity

    def __post_init__(self) -> None:
        if not isinstance(self.identity, DuplicateAssessmentIdentity):
            raise TypeError("pair assessment load requires an assessment identity")


@dataclass(frozen=True, slots=True)
class PairAssessmentFound:
    assessment: DuplicatePairAssessment

    def __post_init__(self) -> None:
        if not isinstance(self.assessment, DuplicatePairAssessment):
            raise TypeError("found pair assessment requires a complete assessment")


@dataclass(frozen=True, slots=True)
class PairAssessmentNotFound:
    """Exact pair-assessment identity is absent."""


type LoadedDuplicatePairAssessment = (
    PairAssessmentFound | PairAssessmentNotFound | PersistenceOperationFailure
)


@dataclass(frozen=True, slots=True)
class CommitDuplicateAssessmentBatchRequest:
    expected_generation_revision: ExpectedRevision
    expected_batch_revision: ExpectedRevision
    batch: DuplicateCandidateAssessmentBatch

    def __post_init__(self) -> None:
        expectations = (self.expected_generation_revision, self.expected_batch_revision)
        if any(not isinstance(item, (ExpectAbsent, ExpectExact)) for item in expectations):
            raise TypeError("assessment commit requires explicit expectations")
        if not isinstance(self.batch, DuplicateCandidateAssessmentBatch):
            raise TypeError("assessment commit requires a complete batch")


@dataclass(frozen=True, slots=True)
class CommitDuplicateAssessmentBatchSuccess:
    disposition: CommitDisposition
    generation_revision: PersistenceRevision
    batch_revision: PersistenceRevision
    batch: DuplicateCandidateAssessmentBatch

    def __post_init__(self) -> None:
        if not isinstance(self.disposition, CommitDisposition):
            raise TypeError("assessment commit success requires a disposition")
        if not isinstance(self.generation_revision, PersistenceRevision):
            raise TypeError("assessment commit success requires a generation revision")
        if not isinstance(self.batch_revision, PersistenceRevision):
            raise TypeError("assessment commit success requires a batch revision")
        if not isinstance(self.batch, DuplicateCandidateAssessmentBatch):
            raise TypeError("assessment commit success requires a complete batch")


class DuplicateAssessmentPersistenceConflictCode(StrEnum):
    BATCH_IDENTITY_CONTENT_CONFLICT = "batch_identity_content_conflict"
    ITEM_IDENTITY_CONTENT_CONFLICT = "item_identity_content_conflict"
    GENERATION_DEPENDENCY_CONTENT_CONFLICT = "generation_dependency_content_conflict"
    EXPECTED_REVISION_MISMATCH = "expected_revision_mismatch"
    ASSESSMENT_SUPERSESSION_CONFLICT = "assessment_supersession_conflict"
    ASSESSMENT_DEPENDENCY_NOT_FOUND = "assessment_dependency_not_found"


@dataclass(frozen=True, slots=True)
class AssessmentBatchIdentityContentSubject:
    identity: DuplicateCandidateAssessmentBatchIdentity

    def __post_init__(self) -> None:
        if not isinstance(self.identity, DuplicateCandidateAssessmentBatchIdentity):
            raise TypeError("assessment batch content subject requires a batch identity")


@dataclass(frozen=True, slots=True)
class AssessmentItemIdentityContentSubject:
    identity: DuplicateAssessmentIdentity

    def __post_init__(self) -> None:
        if not isinstance(self.identity, DuplicateAssessmentIdentity):
            raise TypeError("assessment item content subject requires an assessment identity")


@dataclass(frozen=True, slots=True)
class AssessmentGenerationDependencySubject:
    identity: DuplicateCandidateGenerationIdentity

    def __post_init__(self) -> None:
        if not isinstance(self.identity, DuplicateCandidateGenerationIdentity):
            raise TypeError("assessment dependency subject requires a generation identity")


@dataclass(frozen=True, slots=True)
class AssessmentExpectedRevisionSubject:
    slot: Literal["generation", "batch"]
    identity: DuplicateCandidateGenerationIdentity | DuplicateCandidateAssessmentBatchIdentity
    expected: ExpectedRevision
    actual: PersistenceRevision | None

    def __post_init__(self) -> None:
        if self.slot not in ("generation", "batch"):
            raise ValueError("assessment revision subject has an unsupported slot")
        expected_identity_type = (
            DuplicateCandidateGenerationIdentity
            if self.slot == "generation"
            else DuplicateCandidateAssessmentBatchIdentity
        )
        if not isinstance(self.identity, expected_identity_type):
            raise TypeError("assessment revision subject identity does not match slot")
        if not isinstance(self.expected, (ExpectAbsent, ExpectExact)):
            raise TypeError("assessment revision subject requires an explicit expectation")
        if self.actual is not None and not isinstance(self.actual, PersistenceRevision):
            raise TypeError("assessment revision subject actual token is unsupported")


type DuplicateAssessmentPersistenceConflictSubject = (
    AssessmentBatchIdentityContentSubject
    | AssessmentItemIdentityContentSubject
    | AssessmentGenerationDependencySubject
    | AssessmentExpectedRevisionSubject
    | AssessmentSupersession
    | DuplicateAssessmentIdentity
)


@dataclass(frozen=True, slots=True)
class DuplicateAssessmentPersistenceConflict:
    category: Literal["DUPLICATE_ASSESSMENT_PERSISTENCE_CONFLICT"]
    code: DuplicateAssessmentPersistenceConflictCode
    subject: DuplicateAssessmentPersistenceConflictSubject

    def __post_init__(self) -> None:
        if self.category != "DUPLICATE_ASSESSMENT_PERSISTENCE_CONFLICT":
            raise ValueError("invalid assessment persistence conflict category")
        if not isinstance(self.code, DuplicateAssessmentPersistenceConflictCode):
            raise TypeError("unsupported assessment persistence conflict code")
        subject_matches = (
            (
                self.code
                is DuplicateAssessmentPersistenceConflictCode.BATCH_IDENTITY_CONTENT_CONFLICT
                and isinstance(self.subject, AssessmentBatchIdentityContentSubject)
            )
            or (
                self.code
                is DuplicateAssessmentPersistenceConflictCode.ITEM_IDENTITY_CONTENT_CONFLICT
                and isinstance(self.subject, AssessmentItemIdentityContentSubject)
            )
            or (
                self.code
                is DuplicateAssessmentPersistenceConflictCode.GENERATION_DEPENDENCY_CONTENT_CONFLICT
                and isinstance(self.subject, AssessmentGenerationDependencySubject)
            )
            or (
                self.code is DuplicateAssessmentPersistenceConflictCode.EXPECTED_REVISION_MISMATCH
                and isinstance(self.subject, AssessmentExpectedRevisionSubject)
            )
            or (
                self.code
                is DuplicateAssessmentPersistenceConflictCode.ASSESSMENT_SUPERSESSION_CONFLICT
                and isinstance(self.subject, AssessmentSupersession)
            )
            or (
                self.code
                is DuplicateAssessmentPersistenceConflictCode.ASSESSMENT_DEPENDENCY_NOT_FOUND
                and isinstance(self.subject, DuplicateAssessmentIdentity)
            )
        )
        if not subject_matches:
            raise TypeError("assessment persistence conflict subject does not match code")


def _assessment_conflict_key(
    conflict: DuplicateAssessmentPersistenceConflict,
) -> tuple[object, ...]:
    order = {
        code: position for position, code in enumerate(DuplicateAssessmentPersistenceConflictCode)
    }
    subject = conflict.subject
    if isinstance(subject, AssessmentExpectedRevisionSubject):
        identity_detail = (
            _generation_identity_key(subject.identity)
            if isinstance(subject.identity, DuplicateCandidateGenerationIdentity)
            else (
                *_generation_identity_key(subject.identity.generation_identity),
                subject.identity.assessment_policy_version.value,
            )
        )
        detail: tuple[object, ...] = (
            0 if subject.slot == "generation" else 1,
            *identity_detail,
        )
    elif isinstance(subject, AssessmentItemIdentityContentSubject):
        detail = _assessment_identity_key(subject.identity)
    elif isinstance(subject, DuplicateAssessmentIdentity):
        detail = _assessment_identity_key(subject)
    elif isinstance(subject, AssessmentSupersession):
        detail = (
            *_assessment_identity_key(subject.previous),
            *_assessment_identity_key(subject.replacement),
        )
    elif isinstance(subject, AssessmentBatchIdentityContentSubject):
        detail = (
            *_generation_identity_key(subject.identity.generation_identity),
            subject.identity.assessment_policy_version.value,
        )
    elif isinstance(subject, AssessmentGenerationDependencySubject):
        detail = _generation_identity_key(subject.identity)
    else:
        detail = ()
    return order[conflict.code], *detail, conflict.code.value


@dataclass(frozen=True, slots=True)
class CommitDuplicateAssessmentBatchFailure:
    conflicts: tuple[DuplicateAssessmentPersistenceConflict, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.conflicts, tuple) or not self.conflicts:
            raise ValueError("assessment commit failure requires conflicts")
        if any(
            not isinstance(item, DuplicateAssessmentPersistenceConflict) for item in self.conflicts
        ):
            raise TypeError("assessment commit failure contains an unsupported conflict")
        canonical = tuple(sorted(set(self.conflicts), key=_assessment_conflict_key))
        object.__setattr__(self, "conflicts", canonical)


type CommitDuplicateAssessmentBatchOutcome = (
    CommitDuplicateAssessmentBatchSuccess
    | CommitDuplicateAssessmentBatchFailure
    | PersistenceOperationFailure
)


@dataclass(frozen=True, slots=True)
class CommitAssessmentSupersessionRequest:
    link: AssessmentSupersession

    def __post_init__(self) -> None:
        if not isinstance(self.link, AssessmentSupersession):
            raise TypeError("assessment supersession commit requires a link")


@dataclass(frozen=True, slots=True)
class CommitAssessmentSupersessionSuccess:
    disposition: CommitDisposition
    link: AssessmentSupersession

    def __post_init__(self) -> None:
        if not isinstance(self.disposition, CommitDisposition):
            raise TypeError("assessment supersession success requires a disposition")
        if not isinstance(self.link, AssessmentSupersession):
            raise TypeError("assessment supersession success requires a link")


type CommitAssessmentSupersessionOutcome = (
    CommitAssessmentSupersessionSuccess
    | CommitDuplicateAssessmentBatchFailure
    | PersistenceOperationFailure
)


@dataclass(frozen=True, slots=True)
class LoadManualReviewChainRequest:
    review_reference_code: ReviewReferenceCode

    def __post_init__(self) -> None:
        if not isinstance(self.review_reference_code, ReviewReferenceCode):
            raise TypeError("manual review chain load requires a reference code")


@dataclass(frozen=True, slots=True)
class LoadManualReviewChainSuccess:
    revisions: tuple[DuplicatePairManualReview, ...]
    head: DuplicatePairManualReview | None
    head_revision: PersistenceRevision | None

    def __post_init__(self) -> None:
        if not isinstance(self.revisions, tuple):
            raise TypeError("manual review chain must be a tuple")
        if any(not isinstance(review, DuplicatePairManualReview) for review in self.revisions):
            raise TypeError("manual review chain contains an unsupported revision")
        identities = tuple(review.identity for review in self.revisions)
        if identities != tuple(sorted(identities, key=_review_identity_key)):
            raise ValueError("manual review chain must be canonical")
        if len(set(identities)) != len(identities):
            raise ValueError("manual review chain revisions must be unique")
        if self.revisions:
            reference_codes = {identity.review_reference_code for identity in identities}
            if len(reference_codes) != 1:
                raise ValueError("manual review chain must have one reference code")
            if tuple(identity.revision for identity in identities) != tuple(
                range(1, len(identities) + 1)
            ):
                raise ValueError("manual review chain revisions must be contiguous")
        if not self.revisions:
            if self.head is not None or self.head_revision is not None:
                raise ValueError("absent manual review chain cannot have a head")
        elif (
            self.head != self.revisions[-1]
            or not isinstance(self.head, DuplicatePairManualReview)
            or not isinstance(self.head_revision, PersistenceRevision)
        ):
            raise ValueError("manual review chain head must be its last revision")


type LoadManualReviewChainOutcome = LoadManualReviewChainSuccess | PersistenceOperationFailure


@dataclass(frozen=True, slots=True)
class CommitManualReviewRevisionRequest:
    expected_head_revision: ExpectedRevision
    review: DuplicatePairManualReview
    bound_assessment: DuplicatePairAssessment

    def __post_init__(self) -> None:
        if not isinstance(self.expected_head_revision, (ExpectAbsent, ExpectExact)):
            raise TypeError("manual review commit requires an explicit expectation")
        if not isinstance(self.review, DuplicatePairManualReview):
            raise TypeError("manual review commit requires a validated review")
        if not isinstance(self.bound_assessment, DuplicatePairAssessment):
            raise TypeError("manual review commit requires a bound assessment")


@dataclass(frozen=True, slots=True)
class CommitManualReviewRevisionSuccess:
    disposition: CommitDisposition
    review: DuplicatePairManualReview
    head_revision: PersistenceRevision

    def __post_init__(self) -> None:
        if not isinstance(self.disposition, CommitDisposition):
            raise TypeError("manual review commit success requires a disposition")
        if not isinstance(self.review, DuplicatePairManualReview):
            raise TypeError("manual review commit success requires a review")
        if not isinstance(self.head_revision, PersistenceRevision):
            raise TypeError("manual review commit success requires a head revision")


class ManualReviewPersistenceConflictCode(StrEnum):
    REVIEW_IDENTITY_CONTENT_CONFLICT = "review_identity_content_conflict"
    REVIEW_REVISION_MISMATCH = "review_revision_mismatch"
    REVIEW_REVISION_FORK = "review_revision_fork"
    REVIEW_ASSESSMENT_MISMATCH = "review_assessment_mismatch"
    EXPECTED_REVISION_MISMATCH = "expected_revision_mismatch"


@dataclass(frozen=True, slots=True)
class ManualReviewExpectedRevisionSubject:
    review_reference_code: ReviewReferenceCode
    expected: ExpectedRevision
    actual: PersistenceRevision | None

    def __post_init__(self) -> None:
        if not isinstance(self.review_reference_code, ReviewReferenceCode):
            raise TypeError("manual review revision subject requires a reference code")
        if not isinstance(self.expected, (ExpectAbsent, ExpectExact)):
            raise TypeError("manual review revision subject requires an explicit expectation")
        if self.actual is not None and not isinstance(self.actual, PersistenceRevision):
            raise TypeError("manual review revision subject actual token is unsupported")


@dataclass(frozen=True, slots=True)
class ManualReviewAssessmentSubject:
    review_identity: ManualReviewIdentity
    assessment_identity: DuplicateAssessmentIdentity

    def __post_init__(self) -> None:
        if not isinstance(self.review_identity, ManualReviewIdentity):
            raise TypeError("manual review assessment subject requires a review identity")
        if not isinstance(self.assessment_identity, DuplicateAssessmentIdentity):
            raise TypeError("manual review assessment subject requires an assessment identity")


type ManualReviewPersistenceConflictSubject = (
    ManualReviewIdentity | ManualReviewExpectedRevisionSubject | ManualReviewAssessmentSubject
)


@dataclass(frozen=True, slots=True)
class ManualReviewPersistenceConflict:
    category: Literal["MANUAL_REVIEW_PERSISTENCE_CONFLICT"]
    code: ManualReviewPersistenceConflictCode
    subject: ManualReviewPersistenceConflictSubject

    def __post_init__(self) -> None:
        if self.category != "MANUAL_REVIEW_PERSISTENCE_CONFLICT":
            raise ValueError("invalid manual review persistence conflict category")
        if not isinstance(self.code, ManualReviewPersistenceConflictCode):
            raise TypeError("unsupported manual review persistence conflict code")
        identity_codes = {
            ManualReviewPersistenceConflictCode.REVIEW_IDENTITY_CONTENT_CONFLICT,
            ManualReviewPersistenceConflictCode.REVIEW_REVISION_MISMATCH,
            ManualReviewPersistenceConflictCode.REVIEW_REVISION_FORK,
        }
        subject_matches = (
            (self.code in identity_codes and isinstance(self.subject, ManualReviewIdentity))
            or (
                self.code is ManualReviewPersistenceConflictCode.REVIEW_ASSESSMENT_MISMATCH
                and isinstance(self.subject, ManualReviewAssessmentSubject)
            )
            or (
                self.code is ManualReviewPersistenceConflictCode.EXPECTED_REVISION_MISMATCH
                and isinstance(self.subject, ManualReviewExpectedRevisionSubject)
            )
        )
        if not subject_matches:
            raise TypeError("manual review persistence conflict subject does not match code")


def _manual_review_conflict_key(
    conflict: ManualReviewPersistenceConflict,
) -> tuple[object, ...]:
    order = {code: position for position, code in enumerate(ManualReviewPersistenceConflictCode)}
    subject = conflict.subject
    if isinstance(subject, ManualReviewIdentity):
        detail = _review_identity_key(subject)
    elif isinstance(subject, ManualReviewExpectedRevisionSubject):
        detail = (subject.review_reference_code.value, 0)
    else:
        detail = _review_identity_key(subject.review_identity)
    return order[conflict.code], *detail, conflict.code.value


@dataclass(frozen=True, slots=True)
class CommitManualReviewRevisionFailure:
    conflicts: tuple[ManualReviewPersistenceConflict, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.conflicts, tuple) or not self.conflicts:
            raise ValueError("manual review commit failure requires conflicts")
        if any(not isinstance(item, ManualReviewPersistenceConflict) for item in self.conflicts):
            raise TypeError("manual review commit failure contains an unsupported conflict")
        canonical = tuple(sorted(set(self.conflicts), key=_manual_review_conflict_key))
        object.__setattr__(self, "conflicts", canonical)


type CommitManualReviewRevisionOutcome = (
    CommitManualReviewRevisionSuccess
    | CommitManualReviewRevisionFailure
    | PersistenceOperationFailure
)


@dataclass(frozen=True, slots=True)
class QualityAuditReferenceCode:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            raise TypeError("quality audit reference code must be a string")
        if not self.value or not self.value.isascii():
            raise ValueError("quality audit reference code must be non-empty ASCII")
        if any(not (character.isalnum() or character in "._:-") for character in self.value):
            raise ValueError("quality audit reference code contains an unsupported character")


@dataclass(frozen=True, slots=True)
class QualityAuditIdentity:
    reference_code: QualityAuditReferenceCode
    revision: int

    def __post_init__(self) -> None:
        if not isinstance(self.reference_code, QualityAuditReferenceCode):
            raise TypeError("quality audit identity requires a reference code")
        if type(self.revision) is not int or self.revision < 1:
            raise ValueError("quality audit revision must be a positive integer")


@dataclass(frozen=True, slots=True)
class DuplicateQualityAuditInput:
    identity: QualityAuditIdentity
    control_set: DuplicatePolicyControlSet
    generation_result: DuplicateCandidateGenerationResult | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.identity, QualityAuditIdentity):
            raise TypeError("quality audit input requires an identity")
        if not isinstance(self.control_set, DuplicatePolicyControlSet):
            raise TypeError("quality audit input requires a control set")
        if self.generation_result is not None and not isinstance(
            self.generation_result, DuplicateCandidateGenerationResult
        ):
            raise TypeError("quality audit generation must be a complete result")


@dataclass(frozen=True, slots=True)
class LoadDuplicateQualityAuditRequest:
    identity: QualityAuditIdentity

    def __post_init__(self) -> None:
        if not isinstance(self.identity, QualityAuditIdentity):
            raise TypeError("quality audit load requires an audit identity")


@dataclass(frozen=True, slots=True)
class QualityAuditFound:
    input: DuplicateQualityAuditInput
    head_revision: PersistenceRevision

    def __post_init__(self) -> None:
        if not isinstance(self.input, DuplicateQualityAuditInput):
            raise TypeError("found quality audit requires a complete input")
        if not isinstance(self.head_revision, PersistenceRevision):
            raise TypeError("found quality audit requires a persistence revision")


@dataclass(frozen=True, slots=True)
class QualityAuditNotFound:
    """Exact quality audit identity is absent."""


type LoadedDuplicateQualityAudit = (
    QualityAuditFound | QualityAuditNotFound | PersistenceOperationFailure
)


@dataclass(frozen=True, slots=True)
class CommitDuplicateQualityAuditRequest:
    expected_head_revision: ExpectedRevision
    input: DuplicateQualityAuditInput

    def __post_init__(self) -> None:
        if not isinstance(self.expected_head_revision, (ExpectAbsent, ExpectExact)):
            raise TypeError("quality audit commit requires an explicit expectation")
        if not isinstance(self.input, DuplicateQualityAuditInput):
            raise TypeError("quality audit commit requires a complete audit input")


@dataclass(frozen=True, slots=True)
class CommitDuplicateQualityAuditSuccess:
    disposition: CommitDisposition
    input: DuplicateQualityAuditInput
    head_revision: PersistenceRevision

    def __post_init__(self) -> None:
        if not isinstance(self.disposition, CommitDisposition):
            raise TypeError("quality audit commit success requires a disposition")
        if not isinstance(self.input, DuplicateQualityAuditInput):
            raise TypeError("quality audit commit success requires a complete input")
        if not isinstance(self.head_revision, PersistenceRevision):
            raise TypeError("quality audit commit success requires a head revision")


class DuplicateQualityPersistenceConflictCode(StrEnum):
    AUDIT_IDENTITY_CONTENT_CONFLICT = "audit_identity_content_conflict"
    AUDIT_REVISION_FORK = "audit_revision_fork"
    EXPECTED_REVISION_MISMATCH = "expected_revision_mismatch"


@dataclass(frozen=True, slots=True)
class QualityExpectedRevisionSubject:
    reference_code: QualityAuditReferenceCode
    expected: ExpectedRevision
    actual: PersistenceRevision | None

    def __post_init__(self) -> None:
        if not isinstance(self.reference_code, QualityAuditReferenceCode):
            raise TypeError("quality revision subject requires an audit reference code")
        if not isinstance(self.expected, (ExpectAbsent, ExpectExact)):
            raise TypeError("quality revision subject requires an explicit expectation")
        if self.actual is not None and not isinstance(self.actual, PersistenceRevision):
            raise TypeError("quality revision subject actual token is unsupported")


type DuplicateQualityPersistenceConflictSubject = (
    QualityAuditIdentity | QualityExpectedRevisionSubject
)


@dataclass(frozen=True, slots=True)
class DuplicateQualityPersistenceConflict:
    category: Literal["DUPLICATE_QUALITY_PERSISTENCE_CONFLICT"]
    code: DuplicateQualityPersistenceConflictCode
    subject: DuplicateQualityPersistenceConflictSubject

    def __post_init__(self) -> None:
        if self.category != "DUPLICATE_QUALITY_PERSISTENCE_CONFLICT":
            raise ValueError("invalid duplicate quality persistence conflict category")
        if not isinstance(self.code, DuplicateQualityPersistenceConflictCode):
            raise TypeError("unsupported duplicate quality persistence conflict code")
        expected_type = (
            QualityExpectedRevisionSubject
            if self.code is DuplicateQualityPersistenceConflictCode.EXPECTED_REVISION_MISMATCH
            else QualityAuditIdentity
        )
        if not isinstance(self.subject, expected_type):
            raise TypeError("quality persistence conflict subject does not match code")


@dataclass(frozen=True, slots=True)
class CommitDuplicateQualityAuditFailure:
    conflicts: tuple[DuplicateQualityPersistenceConflict, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.conflicts, tuple) or not self.conflicts:
            raise ValueError("quality audit commit failure requires conflicts")
        if any(
            not isinstance(item, DuplicateQualityPersistenceConflict) for item in self.conflicts
        ):
            raise TypeError("quality audit commit failure contains an unsupported conflict")
        order = {
            code: position for position, code in enumerate(DuplicateQualityPersistenceConflictCode)
        }

        def conflict_key(item: DuplicateQualityPersistenceConflict) -> tuple[object, ...]:
            subject = item.subject
            if isinstance(subject, QualityAuditIdentity):
                detail: tuple[object, ...] = (
                    subject.reference_code.value,
                    subject.revision,
                )
            else:
                detail = (subject.reference_code.value, 0)
            return order[item.code], *detail, item.code.value

        canonical = tuple(sorted(set(self.conflicts), key=conflict_key))
        object.__setattr__(self, "conflicts", canonical)


type CommitDuplicateQualityAuditOutcome = (
    CommitDuplicateQualityAuditSuccess
    | CommitDuplicateQualityAuditFailure
    | PersistenceOperationFailure
)


@runtime_checkable
class ObservationHistoryPort(Protocol):
    def load_histories(
        self, request: LoadObservationHistoriesRequest
    ) -> LoadObservationHistoriesOutcome: ...

    def load_observations_by_key(
        self, request: LoadObservationsByKeyRequest
    ) -> LoadObservationsByKeyOutcome: ...

    def commit_histories(
        self, request: ObservationHistoryCommitRequest
    ) -> ObservationHistoryCommitOutcome: ...


@runtime_checkable
class DuplicateGenerationArtifactPort(Protocol):
    def load_generation(
        self, request: LoadDuplicateGenerationRequest
    ) -> LoadedDuplicateGeneration: ...

    def commit_generation(
        self, request: CommitDuplicateGenerationRequest
    ) -> CommitDuplicateGenerationOutcome: ...


@runtime_checkable
class DuplicateAssessmentArtifactPort(Protocol):
    def load_assessment_batch(
        self, request: LoadDuplicateAssessmentBatchRequest
    ) -> LoadedDuplicateAssessmentBatch: ...

    def load_pair_assessment(
        self, request: LoadDuplicatePairAssessmentRequest
    ) -> LoadedDuplicatePairAssessment: ...

    def commit_assessment_batch(
        self, request: CommitDuplicateAssessmentBatchRequest
    ) -> CommitDuplicateAssessmentBatchOutcome: ...

    def commit_assessment_supersession(
        self, request: CommitAssessmentSupersessionRequest
    ) -> CommitAssessmentSupersessionOutcome: ...


@runtime_checkable
class ManualReviewRevisionPort(Protocol):
    def load_manual_review_chain(
        self, request: LoadManualReviewChainRequest
    ) -> LoadManualReviewChainOutcome: ...

    def commit_manual_review(
        self, request: CommitManualReviewRevisionRequest
    ) -> CommitManualReviewRevisionOutcome: ...


@runtime_checkable
class DuplicateQualityAuditPort(Protocol):
    def load_quality_audit(
        self, request: LoadDuplicateQualityAuditRequest
    ) -> LoadedDuplicateQualityAudit: ...

    def commit_quality_audit(
        self, request: CommitDuplicateQualityAuditRequest
    ) -> CommitDuplicateQualityAuditOutcome: ...
