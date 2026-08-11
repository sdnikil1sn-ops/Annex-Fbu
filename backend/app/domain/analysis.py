"""Analysis aggregate — the core domain entity of the analysis pipeline.

The state machine follows ADR-0008:

    pending -> processing -> completed | failed

Transitions are validated here in the domain layer, so no caller can move an
analysis into an illegal state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class AnalysisInputType(StrEnum):
    """The kind of content submitted for analysis."""

    TEXT = "text"
    URL = "url"
    IMAGE = "image"


class AnalysisStatus(StrEnum):
    """Lifecycle states of an analysis (ADR-0008)."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# Legal transitions of the analysis state machine.
ALLOWED_TRANSITIONS: dict[AnalysisStatus, set[AnalysisStatus]] = {
    AnalysisStatus.PENDING: {AnalysisStatus.PROCESSING, AnalysisStatus.FAILED},
    AnalysisStatus.PROCESSING: {AnalysisStatus.COMPLETED, AnalysisStatus.FAILED},
    AnalysisStatus.COMPLETED: set(),
    AnalysisStatus.FAILED: set(),
}


class InvalidStatusTransitionError(Exception):
    """Raised when an analysis is moved into an illegal state."""


def _utcnow() -> datetime:
    """Return the current UTC time (timezone-aware)."""
    return datetime.now(UTC)


@dataclass(frozen=True)
class Analysis:
    """Domain entity representing one analysis request.

    Attributes:
        analysis_id: Surrogate key, generated server-side.
        user_id: Owner; None for anonymous requests.
        input_type: What was submitted (text, url, or image).
        status: Current state-machine state.
        locale: Analysis language code.
        failure_reason: Structured error code when status is FAILED.
        created_at: Submission timestamp (UTC).
        completed_at: Terminal-state timestamp (UTC), None until terminal.
    """

    analysis_id: UUID = field(default_factory=uuid4)
    user_id: UUID | None = None
    input_type: AnalysisInputType = AnalysisInputType.TEXT
    status: AnalysisStatus = AnalysisStatus.PENDING
    locale: str = "en"
    failure_reason: str | None = None
    created_at: datetime = field(default_factory=_utcnow)
    completed_at: datetime | None = None

    def transition_to(
        self, new_status: AnalysisStatus, failure_reason: str | None = None
    ) -> Analysis:
        """Return a copy of this analysis moved to ``new_status``.

        Args:
            new_status: The target state.
            failure_reason: Structured error code; required when failing.

        Returns:
            A new Analysis instance in the target state.

        Raises:
            InvalidStatusTransitionError: If the transition is illegal or the
                failure reason is missing for the failed state.
        """
        if new_status not in ALLOWED_TRANSITIONS[self.status]:
            raise InvalidStatusTransitionError(
                f"illegal transition {self.status.value!r} -> {new_status.value!r}"
            )
        if new_status is AnalysisStatus.FAILED and not failure_reason:
            raise InvalidStatusTransitionError(
                "failure_reason is required when entering the failed state"
            )

        completed_at = (
            _utcnow() if new_status in {AnalysisStatus.COMPLETED, AnalysisStatus.FAILED} else None
        )
        return Analysis(
            analysis_id=self.analysis_id,
            user_id=self.user_id,
            input_type=self.input_type,
            status=new_status,
            locale=self.locale,
            failure_reason=failure_reason if new_status is AnalysisStatus.FAILED else None,
            created_at=self.created_at,
            completed_at=completed_at,
        )
