"""Cluster H end-to-end (PYRAMID Stones 38 + 40 cross-model real, in toy mode).

Three test surfaces:

1. **Cross-model gate logic** (no API). Synthetic Scoreboards seeded with
   per-variant rows; verify `evaluate_proposal_cross_model` promotes when
   ≥2 variants confirm, returns L2 when only 1 confirms, returns None on
   no-variants / empty domain.

2. **Re-validation cycles** (no API). Build L3 + L2 artifacts via the
   gate; mutate the Scoreboard; verify `revalidate(...)` correctly
   demotes (L3 → L2), promotes (L2 → L3), and retires (L2 after
   MAX_L2_CYCLES) per the architecture in PYRAMID Stone 40.

3. **Population live API smoke** (auto-skipif no key). Build the
   `DEFAULT_VARIANTS` population (3 agents: 2 Haiku + 1 Sonnet, different
   prompts), feed each the same emission stream, verify all three return
   well-formed forecasts with distinct `agent_id` values.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import pytest

from fingym.agents.contract import TradeAction
from fingym.evaluator.scoreboard import Scoreboard, ScoreboardRow
from fingym.memory.population import build_population
from fingym.memory.promotion import (
    Proposal,
    evaluate_proposal_cross_model,
)
from fingym.memory.revalidation import (
    MAX_L2_CYCLES,
    RevalidationReport,
    revalidate,
    should_revalidate,
)
from fingym.memory.storage import (
    load_probationary_skills,
    load_promoted_skills,
    save_probationary_skill,
    save_promoted_skill,
)
from fingym.toys.synthetic_market import Emission, return_to_bucket

# ---------------------------------------------------------------------------
# Synthetic Scoreboard builders (no API)
# ---------------------------------------------------------------------------


def _make_row(
    *,
    agent_id: str,
    signal_class_id: str,
    brier: float,
    horizon: int = 1,
    realized_return: float = 0.0,
) -> ScoreboardRow:
    trade = TradeAction(
        expression_type="equity-long",
        underlying="TOY",
        direction="long",
        size=1,
        notional=1_000.0,
    )
    return ScoreboardRow(
        agent_id=agent_id,
        signal_class_id=signal_class_id,
        horizon=horizon,
        decision_time=datetime(2026, 5, 18),
        forecast_distribution={},
        calibrated_forecast={},
        calibrated_expected_return=0.0,
        calibrated_expected_utility=0.0,
        tradable_edge_score=0.0,
        kelly_fraction_applied=0.0,
        final_action=trade,
        realized_return=realized_return,
        realized_bucket=return_to_bucket(realized_return),
        brier=brier,
        log_score=0.5,
        realized_edge=0.0,
    )


def _scoreboard_with_per_variant_tag_brier(
    tag: str,
    *,
    variant_tag_brier: dict[str, float],
    variant_other_brier: dict[str, float],
    rows_under_tag: int = 12,
    rows_under_other: int = 30,
) -> Scoreboard:
    """Build a Scoreboard where each variant has its OWN mean Brier under
    the proposed tag and under everything else. Used to engineer scenarios
    where a specified subset of variants pass check 1."""
    sb = Scoreboard()
    for variant_id, tag_brier in variant_tag_brier.items():
        for _ in range(rows_under_tag):
            sb.append(_make_row(agent_id=variant_id, signal_class_id=tag, brier=tag_brier))
    for variant_id, other_brier in variant_other_brier.items():
        for _ in range(rows_under_other):
            sb.append(
                _make_row(
                    agent_id=variant_id,
                    signal_class_id="other_tag",
                    brier=other_brier,
                )
            )
    return sb


# ---------------------------------------------------------------------------
# Cross-model gate logic
# ---------------------------------------------------------------------------


def test_cross_model_promotes_when_two_of_three_variants_confirm() -> None:
    """A and C have low tag-Brier vs high overall; B has tag-Brier matching
    overall. 2 of 3 confirm → L3 promotion."""
    sb = _scoreboard_with_per_variant_tag_brier(
        tag="growing_revenues",
        variant_tag_brier={
            "haiku_default": 0.10,
            "haiku_value_investor": 0.30,
            "sonnet_default": 0.12,
        },
        variant_other_brier={
            "haiku_default": 0.50,
            "haiku_value_investor": 0.30,
            "sonnet_default": 0.50,
        },
    )
    proposal = Proposal(
        content="growing revenues predict upside",
        signal_class_id="growing_revenues",
        horizons=(1, 3),
    )
    artifact = evaluate_proposal_cross_model(proposal, sb)
    assert artifact is not None
    assert artifact.tier == "L3"
    assert artifact.promotion_check_results is not None
    assert artifact.promotion_check_results.cross_model_regression.passed is True
    confirmed = artifact.promotion_check_results.cross_model_regression.models_validated
    assert set(confirmed) == {"haiku_default", "sonnet_default"}


def test_cross_model_returns_l2_when_only_one_variant_confirms() -> None:
    """Only haiku_default has low tag-Brier; B and C don't. 1 of 3 confirm
    → L2 (probationary), not L3."""
    sb = _scoreboard_with_per_variant_tag_brier(
        tag="growing_revenues",
        variant_tag_brier={
            "haiku_default": 0.10,
            "haiku_value_investor": 0.30,
            "sonnet_default": 0.30,
        },
        variant_other_brier={
            "haiku_default": 0.50,
            "haiku_value_investor": 0.30,
            "sonnet_default": 0.30,
        },
    )
    proposal = Proposal(
        content="growing revenues predict upside",
        signal_class_id="growing_revenues",
        horizons=(1,),
    )
    artifact = evaluate_proposal_cross_model(proposal, sb)
    assert artifact is not None
    assert artifact.tier == "L2"
    # L2 artifacts don't carry full promotion_check_results
    assert artifact.promotion_check_results is None
    assert artifact.promoted_at is None


def test_cross_model_rejects_when_no_variant_confirms() -> None:
    """No variant has improvement: gate returns None."""
    sb = _scoreboard_with_per_variant_tag_brier(
        tag="random_tag",
        variant_tag_brier={
            "haiku_default": 0.30,
            "haiku_value_investor": 0.30,
            "sonnet_default": 0.30,
        },
        variant_other_brier={
            "haiku_default": 0.30,
            "haiku_value_investor": 0.30,
            "sonnet_default": 0.30,
        },
    )
    proposal = Proposal(content="anything", signal_class_id="random_tag", horizons=(1,))
    assert evaluate_proposal_cross_model(proposal, sb) is None


def test_cross_model_rejects_when_check_4_fails() -> None:
    """Empty signal_class_id fails check 4."""
    sb = _scoreboard_with_per_variant_tag_brier(
        tag="growing_revenues",
        variant_tag_brier={
            "haiku_default": 0.10,
            "haiku_value_investor": 0.10,
            "sonnet_default": 0.10,
        },
        variant_other_brier={
            "haiku_default": 0.50,
            "haiku_value_investor": 0.50,
            "sonnet_default": 0.50,
        },
    )
    proposal = Proposal(content="anything", signal_class_id="", horizons=(1,))
    assert evaluate_proposal_cross_model(proposal, sb) is None


def test_cross_model_min_variants_passing_is_operator_tunable() -> None:
    """Setting min_variants_passing=3 (full unanimity) is stricter than
    default 2; a 2-of-3 result then yields L2 instead of L3."""
    sb = _scoreboard_with_per_variant_tag_brier(
        tag="growing_revenues",
        variant_tag_brier={
            "haiku_default": 0.10,
            "haiku_value_investor": 0.30,
            "sonnet_default": 0.10,
        },
        variant_other_brier={
            "haiku_default": 0.50,
            "haiku_value_investor": 0.30,
            "sonnet_default": 0.50,
        },
    )
    proposal = Proposal(
        content="growing revenues predict upside",
        signal_class_id="growing_revenues",
        horizons=(1,),
    )
    # Default: 2-of-3 → L3
    default_result = evaluate_proposal_cross_model(proposal, sb)
    assert default_result is not None and default_result.tier == "L3"
    # Stricter: 3-of-3 required → 2 confirm, falls to L2
    strict_result = evaluate_proposal_cross_model(proposal, sb, min_variants_passing=3)
    assert strict_result is not None and strict_result.tier == "L2"


# ---------------------------------------------------------------------------
# Re-validation cycles
# ---------------------------------------------------------------------------


def test_should_revalidate_threshold() -> None:
    assert should_revalidate(0) is False
    assert should_revalidate(49) is False
    assert should_revalidate(50) is True
    assert should_revalidate(200) is True
    # Custom interval
    assert should_revalidate(10, interval_rows=10) is True
    assert should_revalidate(9, interval_rows=10) is False


def test_revalidate_demotes_l3_when_variants_disagree(tmp_path: Path) -> None:
    """An L3 skill is promoted under a Scoreboard where 2 variants agree.
    The Scoreboard changes (one of the confirming variants now has flat
    Brier). Re-validation demotes the skill to L2."""
    l3_dir = tmp_path / "promoted"
    l2_dir = tmp_path / "probationary"

    # Initial Scoreboard: 2 variants confirm `growing_revenues`
    initial_sb = _scoreboard_with_per_variant_tag_brier(
        tag="growing_revenues",
        variant_tag_brier={
            "haiku_default": 0.10,
            "haiku_value_investor": 0.30,
            "sonnet_default": 0.10,
        },
        variant_other_brier={
            "haiku_default": 0.50,
            "haiku_value_investor": 0.30,
            "sonnet_default": 0.50,
        },
    )
    proposal = Proposal(
        content="growing revenues predict upside",
        signal_class_id="growing_revenues",
        horizons=(1,),
    )
    artifact = evaluate_proposal_cross_model(proposal, initial_sb)
    assert artifact is not None and artifact.tier == "L3"
    save_promoted_skill(artifact, l3_dir)

    # New Scoreboard state: only haiku_default still confirms
    later_sb = _scoreboard_with_per_variant_tag_brier(
        tag="growing_revenues",
        variant_tag_brier={
            "haiku_default": 0.10,
            "haiku_value_investor": 0.30,
            "sonnet_default": 0.30,
        },
        variant_other_brier={
            "haiku_default": 0.50,
            "haiku_value_investor": 0.30,
            "sonnet_default": 0.30,
        },
    )
    report: RevalidationReport = revalidate(later_sb, l3_dir=l3_dir, l2_dir=l2_dir)

    assert report.demoted_l3_to_l2 == [artifact.id]
    # File moved from L3 → L2
    assert load_promoted_skills(l3_dir) == []
    demoted_l2 = load_probationary_skills(l2_dir)
    assert len(demoted_l2) == 1
    assert demoted_l2[0].id == artifact.id
    assert demoted_l2[0].tier == "L2"
    # Audit trail records the demotion
    actions = [e.action for e in demoted_l2[0].audit_trail]
    assert "demoted" in actions


def test_revalidate_promotes_l2_when_new_evidence_tips_a_second_variant(
    tmp_path: Path,
) -> None:
    """An L2 (probationary) skill from a 1-of-3 cross-model result. The
    Scoreboard changes to where 2 of 3 variants now confirm. Re-validation
    promotes L2 → L3."""
    l3_dir = tmp_path / "promoted"
    l2_dir = tmp_path / "probationary"

    # Initial: only haiku_default supports growing_revenues
    initial_sb = _scoreboard_with_per_variant_tag_brier(
        tag="growing_revenues",
        variant_tag_brier={
            "haiku_default": 0.10,
            "haiku_value_investor": 0.30,
            "sonnet_default": 0.30,
        },
        variant_other_brier={
            "haiku_default": 0.50,
            "haiku_value_investor": 0.30,
            "sonnet_default": 0.30,
        },
    )
    proposal = Proposal(
        content="growing revenues predict upside",
        signal_class_id="growing_revenues",
        horizons=(1,),
    )
    l2_artifact = evaluate_proposal_cross_model(proposal, initial_sb)
    assert l2_artifact is not None and l2_artifact.tier == "L2"
    save_probationary_skill(l2_artifact, l2_dir)

    # New Scoreboard: now sonnet_default also confirms
    later_sb = _scoreboard_with_per_variant_tag_brier(
        tag="growing_revenues",
        variant_tag_brier={
            "haiku_default": 0.10,
            "haiku_value_investor": 0.30,
            "sonnet_default": 0.10,
        },
        variant_other_brier={
            "haiku_default": 0.50,
            "haiku_value_investor": 0.30,
            "sonnet_default": 0.50,
        },
    )
    report = revalidate(later_sb, l3_dir=l3_dir, l2_dir=l2_dir)

    assert report.promoted_l2_to_l3 == [l2_artifact.id]
    # File moved L2 → L3
    assert load_probationary_skills(l2_dir) == []
    promoted = load_promoted_skills(l3_dir)
    assert len(promoted) == 1
    assert promoted[0].id == l2_artifact.id
    assert promoted[0].tier == "L3"
    # promotion_check_results now populated with real check 2
    assert promoted[0].promotion_check_results is not None
    assert promoted[0].promotion_check_results.cross_model_regression.passed is True
    actions = [e.action for e in promoted[0].audit_trail]
    assert "promoted" in actions


def test_revalidate_retires_l2_after_max_cycles(tmp_path: Path) -> None:
    """An L2 skill that never gathers cross-model support should be
    retired after MAX_L2_CYCLES re-validation cycles."""
    l3_dir = tmp_path / "promoted"
    l2_dir = tmp_path / "probationary"

    # Permanently-stuck Scoreboard: only 1 variant ever confirms
    stuck_sb = _scoreboard_with_per_variant_tag_brier(
        tag="stuck_tag",
        variant_tag_brier={
            "haiku_default": 0.10,
            "haiku_value_investor": 0.30,
            "sonnet_default": 0.30,
        },
        variant_other_brier={
            "haiku_default": 0.50,
            "haiku_value_investor": 0.30,
            "sonnet_default": 0.30,
        },
    )
    proposal = Proposal(content="stuck pattern", signal_class_id="stuck_tag", horizons=(1,))
    l2_artifact = evaluate_proposal_cross_model(proposal, stuck_sb)
    assert l2_artifact is not None and l2_artifact.tier == "L2"
    save_probationary_skill(l2_artifact, l2_dir)

    # Run MAX_L2_CYCLES re-validations against the same Scoreboard.
    for _ in range(MAX_L2_CYCLES):
        revalidate(stuck_sb, l3_dir=l3_dir, l2_dir=l2_dir)

    # The L2 artifact should now be retired.
    remaining = load_probationary_skills(l2_dir)
    assert len(remaining) == 1
    retired = remaining[0]
    last_audit = retired.audit_trail[-1]
    assert last_audit.action == "retired"


# ---------------------------------------------------------------------------
# Population live API smoke (skipif no key)
# ---------------------------------------------------------------------------


_SKIP_IF_NO_KEY = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set; skipping live API tests.",
)


@_SKIP_IF_NO_KEY
def test_default_population_builds_three_distinct_agents() -> None:
    """build_population(DEFAULT_VARIANTS) produces 3 LlmAgents with
    distinct names matching the variant configurations."""
    population = build_population()
    assert len(population) == 3
    names = [agent.name for agent in population]
    assert names == ["haiku_default", "haiku_value_investor", "sonnet_default"]


@_SKIP_IF_NO_KEY
def test_population_all_variants_return_wellformed_forecasts() -> None:
    """Feed each variant the same emission stream; verify each emits a
    well-formed forecast (sums to 1; non-empty signal_class_id). This
    fires 3 API calls (Haiku x2, Sonnet x1) ~ $0.01 total cost."""
    population = build_population()
    stream: list[Emission] = ["strong", "strong", "mixed", "strong", "weak"]
    for agent in population:
        for e in stream:
            agent.observe(e)

    for agent in population:
        forecast = agent.forecast
        assert abs(sum(forecast.values()) - 1.0) < 1e-6
        assert all(0.0 <= p <= 1.0 for p in forecast.values())
        assert agent.signal_class_id != "llm_unset"
        assert agent.signal_class_id.strip() != ""
