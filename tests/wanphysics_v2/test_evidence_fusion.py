import pytest

from pavg_critic.config import FusionConfig
from pavg_critic.evidence_fusion import CoverageAwareEvidenceFusion
from pavg_critic.schemas import (
    CriticReport,
    FrameState,
    TrackSequence,
    Violation,
)


def _build_dummy_report(
    physics_score: float = 0.9,
    confidence: float = 0.85,
    violations: tuple[Violation, ...] = (),
) -> CriticReport:
    return CriticReport(
        decision="physical",
        is_physical=True,
        physics_score=physics_score,
        confidence=confidence,
        coverage=1.0,
        violations=violations,
        graph_evaluation=None,
        node_results=(),
        score_breakdown={},
        diagnostics={},
        model_versions={},
        evidence_bundles=(),
    )


def _build_dummy_tracks(visible_frames: int = 3) -> tuple[TrackSequence, ...]:
    return (
        TrackSequence(
            track_id="1",
            object="ball",
            states=tuple(
                FrameState(
                    frame=i,
                    timestamp_sec=i * 0.1,
                    object="ball",
                    center=(5.0, float(5 + i)),
                    bbox=(0.0, 0.0, 10.0, 10.0),
                    visible=True,
                    confidence=1.0,
                )
                for i in range(visible_frames)
            ),
        ),
    )


def test_active_family_normalization_prevents_coverage_collapse():
    """Verify active-family normalization normalizes coverage against available families only.

    When only rules evidence is available (other families unconfigured/not applicable),
    the normalized coverage should equal the rules coverage itself, rather than being
    divided by the global 1.0 denominator and collapsing below acceptance thresholds.
    """
    fusion = CoverageAwareEvidenceFusion(
        FusionConfig(),
        enabled_rules=["fall_acceleration", "collision_rebound"],
    )
    report = _build_dummy_report(physics_score=0.9, confidence=0.85)
    tracks = _build_dummy_tracks(visible_frames=3)

    enriched = fusion.enrich(
        report,
        tracks=tracks,
        candidates=(),
        reviews={},
        checklist_summary=None,
        mechanics_summary=None,
    )

    # With 2 rules enabled out of 5 categories, fraction is 2/5 = 0.4.
    # Active family normalization ensures coverage reflects available families (0.4)
    # rather than being crushed to 0.4 * 0.2 = 0.08.
    assert enriched.coverage >= 0.40
    assert enriched.decision == "physical"
    assert enriched.physics_score == 0.9
    assert any(b.family == "rules" and b.status == "available" for b in enriched.evidence_bundles)


def test_hard_violation_forces_violation_decision():
    """Verify that concrete violation candidates force the final decision to 'violation'."""
    fusion = CoverageAwareEvidenceFusion(
        FusionConfig(),
        enabled_rules=["fall_acceleration"],
    )
    violation = Violation(
        object="ball",
        category="dynamics",
        start_frame=1,
        peak_frame=2,
        end_frame=2,
        critical_frames=(1, 2),
        reason="ball accelerated upward without external force",
        repair_instruction="ensure gravity points downward",
        evidence={},
    )
    report = _build_dummy_report(physics_score=0.4, confidence=0.85, violations=(violation,))
    tracks = _build_dummy_tracks(visible_frames=3)

    enriched = fusion.enrich(
        report,
        tracks=tracks,
        candidates=(),
        reviews={},
        checklist_summary=None,
        mechanics_summary=None,
    )

    assert enriched.decision == "violation"
    assert not enriched.is_physical
    assert enriched.physics_score == 0.4

