"""State-machine compliance tests (ADR-0008, Phase 7).

Every legal transition is reachable and every illegal transition raises,
including the ``processing -> pending`` retry edge added for worker
re-delivery.
"""

from __future__ import annotations

import pytest
from app.domain.analysis import (
    ALLOWED_TRANSITIONS,
    Analysis,
    AnalysisStatus,
    InvalidStatusTransitionError,
)

# Expected legal transitions, mirrored from the domain contract so the
# matrix below asserts the machine never drifts from its spec.
LEGAL: dict[AnalysisStatus, set[AnalysisStatus]] = {
    AnalysisStatus.PENDING: {AnalysisStatus.PROCESSING, AnalysisStatus.FAILED},
    AnalysisStatus.PROCESSING: {
        AnalysisStatus.COMPLETED,
        AnalysisStatus.FAILED,
        AnalysisStatus.PENDING,
    },
    AnalysisStatus.COMPLETED: set(),
    AnalysisStatus.FAILED: set(),
}


def test_transition_matrix_matches_spec() -> None:
    """The exported transition table equals the documented spec."""
    assert ALLOWED_TRANSITIONS == LEGAL


def test_every_transition_is_enforced() -> None:
    """Legal transitions succeed; illegal ones raise (full matrix)."""
    for source in AnalysisStatus:
        for target in AnalysisStatus:
            analysis = Analysis(status=source)
            if target in LEGAL[source]:
                moved = analysis.transition_to(
                    target, failure_reason="r" if target is AnalysisStatus.FAILED else None
                )
                assert moved.status is target
            else:
                with pytest.raises(InvalidStatusTransitionError):
                    analysis.transition_to(target, failure_reason="r")


def test_terminal_states_are_immutable() -> None:
    """Neither COMPLETED nor FAILED can ever leave its state."""
    for terminal in (AnalysisStatus.COMPLETED, AnalysisStatus.FAILED):
        analysis = Analysis(status=terminal)
        for target in AnalysisStatus:
            if target is not terminal:
                with pytest.raises(InvalidStatusTransitionError):
                    analysis.transition_to(
                        target,
                        failure_reason="r" if target is AnalysisStatus.FAILED else None,
                    )


def test_failed_requires_reason() -> None:
    """Entering FAILED without a structured reason is rejected."""
    with pytest.raises(InvalidStatusTransitionError):
        Analysis(status=AnalysisStatus.PENDING).transition_to(AnalysisStatus.FAILED)


def test_retry_edge_clears_terminal_fields() -> None:
    """processing -> pending (worker retry) resets timestamps and reasons."""
    analysis = Analysis(content="text")
    processing = analysis.transition_to(AnalysisStatus.PROCESSING)
    requeued = processing.transition_to(AnalysisStatus.PENDING)

    assert requeued.status is AnalysisStatus.PENDING
    assert requeued.completed_at is None
    assert requeued.failure_reason is None
    # The persisted input survives the round trip for re-processing.
    assert requeued.content == "text"


def test_pending_cannot_be_requeued() -> None:
    """pending -> pending is not a legal retry edge."""
    with pytest.raises(InvalidStatusTransitionError):
        Analysis(status=AnalysisStatus.PENDING).transition_to(AnalysisStatus.PENDING)
