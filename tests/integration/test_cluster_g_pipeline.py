"""Cluster G end-to-end (PYRAMID Stones 39 + 40 in toy mode).

Tests the memory-loop architecture:

  LLM emits proposal -> promotion gate (checks 1 + 4) -> L3 YAML on disk
                                                              |
                                                              v
                                  next LlmAgent reads L3 at construction
                                  -> system prompt includes promoted skills

Three test surfaces:

1. Promotion gate logic (unit, no API): the gate promotes / rejects
   under the right conditions; promoted artifacts carry honest
   audit_trail and promotion_check_results (with checks 2 + 3 stubbed
   as passed=False).

2. Storage round-trip (unit, no API): YAML save/load preserves the
   full MemoryArtifact incl. nested check results; render_for_system_prompt
   formats correctly.

3. Full memory loop (integration, requires ANTHROPIC_API_KEY,
   auto-skipif): LLM emits proposal via propose_memory_item tool call;
   gate evaluates against a synthetic-populated scoreboard; promoted
   skill saved to a temp dir; next LlmAgent loads it from disk and
   includes it in the system prompt.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import pytest

from fingym.agents.contract import TradeAction
from fingym.evaluator.scoreboard import Scoreboard, ScoreboardRow
from fingym.llm.anthropic import AnthropicClient
from fingym.memory.promotion import (
    MIN_CALIBRATION_DELTA,
    MIN_HELD_OUT_ROWS,
    Proposal,
    evaluate_proposal,
)
from fingym.memory.schema import MemoryArtifact
from fingym.memory.storage import (
    load_promoted_skills,
    render_for_system_prompt,
    save_promoted_skill,
)
from fingym.toys.llm_agent import LlmAgent
from fingym.toys.synthetic_market import Emission, return_to_bucket

# ---------------------------------------------------------------------------
# Promotion gate logic (no API)
# ---------------------------------------------------------------------------


def _make_row(
    *,
    signal_class_id: str,
    brier: float,
    horizon: int = 1,
    realized_return: float = 0.0,
) -> ScoreboardRow:
    """Build a ScoreboardRow with the minimal fields the gate reads."""
    trade = TradeAction(
        expression_type="equity-long",
        underlying="TOY",
        direction="long",
        size=1,
        notional=1_000.0,
    )
    return ScoreboardRow(
        agent_id="bayesian",
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


def _build_scoreboard_with_good_tag_calibration() -> Scoreboard:
    """Build a scoreboard where signal_class_id='good_tag' has lower mean
    Brier (better calibration) than the overall mean. The promotion gate
    should pass check 1 for a proposal targeting 'good_tag'."""
    sb = Scoreboard()
    # 15 rows under 'good_tag' with low Brier (0.10)
    for _ in range(15):
        sb.append(_make_row(signal_class_id="good_tag", brier=0.10))
    # 30 rows under 'other_tag' with high Brier (0.50)
    for _ in range(30):
        sb.append(_make_row(signal_class_id="other_tag", brier=0.50))
    return sb


def test_evaluate_proposal_promotes_when_signal_class_better_calibrated() -> None:
    sb = _build_scoreboard_with_good_tag_calibration()
    proposal = Proposal(
        content="High-conviction streams in 'good_tag' show consistent edge.",
        signal_class_id="good_tag",
        horizons=(1, 3),
        proposed_by_agent="test_agent",
    )
    artifact = evaluate_proposal(proposal, sb)
    assert artifact is not None
    assert artifact.tier == "L3"
    assert artifact.content == proposal.content
    assert artifact.domain_of_validity.horizons == ["1", "3"]
    # Check 1 should be passed=True with positive calibration_delta
    assert artifact.promotion_check_results is not None
    assert artifact.promotion_check_results.held_out_replay.passed is True
    assert (
        artifact.promotion_check_results.held_out_replay.calibration_delta >= MIN_CALIBRATION_DELTA
    )
    # Check 4 (domain_of_validity_declared) passed
    assert artifact.promotion_check_results.domain_of_validity_declared is True


def test_evaluate_proposal_rejects_when_too_few_held_out_rows() -> None:
    """The proposal targets a tag with only 5 rows in the scoreboard; below
    MIN_HELD_OUT_ROWS=10, the gate has too little evidence. Reject."""
    sb = Scoreboard()
    for _ in range(MIN_HELD_OUT_ROWS - 5):
        sb.append(_make_row(signal_class_id="sparse_tag", brier=0.10))
    for _ in range(30):
        sb.append(_make_row(signal_class_id="other_tag", brier=0.50))
    proposal = Proposal(
        content="Pattern under sparse_tag.",
        signal_class_id="sparse_tag",
        horizons=(1,),
    )
    assert evaluate_proposal(proposal, sb) is None


def test_evaluate_proposal_rejects_when_signal_class_no_better_than_average() -> None:
    """A proposal under a tag whose Brier matches the overall mean
    yields calibration_delta < MIN_CALIBRATION_DELTA. Reject."""
    sb = Scoreboard()
    for _ in range(20):
        sb.append(_make_row(signal_class_id="mediocre_tag", brier=0.30))
    for _ in range(20):
        sb.append(_make_row(signal_class_id="other_tag", brier=0.30))
    proposal = Proposal(
        content="Insight under mediocre_tag.",
        signal_class_id="mediocre_tag",
        horizons=(1,),
    )
    assert evaluate_proposal(proposal, sb) is None


def test_evaluate_proposal_rejects_when_signal_class_id_empty() -> None:
    sb = _build_scoreboard_with_good_tag_calibration()
    proposal = Proposal(content="anything", signal_class_id="", horizons=(1,))
    assert evaluate_proposal(proposal, sb) is None


def test_evaluate_proposal_rejects_when_horizons_empty() -> None:
    sb = _build_scoreboard_with_good_tag_calibration()
    proposal = Proposal(content="anything", signal_class_id="good_tag", horizons=())
    assert evaluate_proposal(proposal, sb) is None


def test_promoted_artifact_audit_trail_has_proposed_and_promoted_entries() -> None:
    sb = _build_scoreboard_with_good_tag_calibration()
    proposal = Proposal(
        content="insight",
        signal_class_id="good_tag",
        horizons=(1,),
        proposed_by_agent="alice",
    )
    artifact = evaluate_proposal(proposal, sb, proposed_at_episode=42)
    assert artifact is not None
    actions = [e.action for e in artifact.audit_trail]
    assert actions == ["proposed", "promoted"]
    proposed_entry = artifact.audit_trail[0]
    assert proposed_entry.by == "alice"
    assert "Episode 42" in proposed_entry.reason


def test_promoted_artifact_checks_2_and_3_stubbed_as_not_validated() -> None:
    """Honest audit: the toy-mode gate marks checks 2 + 3 as
    passed=False with empty/zero fields. Real validation comes in
    Cluster H + Phase 2 NEW."""
    sb = _build_scoreboard_with_good_tag_calibration()
    proposal = Proposal(content="insight", signal_class_id="good_tag", horizons=(1,))
    artifact = evaluate_proposal(proposal, sb)
    assert artifact is not None
    assert artifact.promotion_check_results is not None
    assert artifact.promotion_check_results.cross_model_regression.passed is False
    assert artifact.promotion_check_results.cross_model_regression.models_validated == []
    assert artifact.promotion_check_results.survivorship_check.passed is False
    assert artifact.promotion_check_results.survivorship_check.delisted_sample_size == 0


# ---------------------------------------------------------------------------
# Storage round-trip (no API)
# ---------------------------------------------------------------------------


def test_save_and_load_promoted_skill_round_trip(tmp_path: Path) -> None:
    sb = _build_scoreboard_with_good_tag_calibration()
    proposal = Proposal(
        content="Streams of 5+ STRONG signals show edge at 3-6 month horizons.",
        signal_class_id="good_tag",  # matches the scoreboard so check 1 passes
        horizons=(3, 6),
        proposed_by_agent="alice",
    )
    artifact = evaluate_proposal(proposal, sb)
    assert artifact is not None
    save_promoted_skill(artifact, tmp_path)
    loaded = load_promoted_skills(tmp_path)
    assert len(loaded) == 1
    assert loaded[0].id == artifact.id
    assert loaded[0].content == artifact.content
    assert loaded[0].domain_of_validity.horizons == ["3", "6"]
    # Nested validators round-tripped correctly
    assert loaded[0].promotion_check_results is not None
    assert loaded[0].promotion_check_results.held_out_replay.passed is True


def test_load_promoted_skills_empty_directory_returns_empty(tmp_path: Path) -> None:
    assert load_promoted_skills(tmp_path) == []


def test_load_promoted_skills_missing_directory_returns_empty(tmp_path: Path) -> None:
    assert load_promoted_skills(tmp_path / "does_not_exist") == []


def test_render_for_system_prompt_empty_returns_empty_string() -> None:
    assert render_for_system_prompt([]) == ""


def test_render_for_system_prompt_includes_content_and_horizons(
    tmp_path: Path,
) -> None:
    sb = _build_scoreboard_with_good_tag_calibration()
    proposal = Proposal(
        content="Test content for prompt rendering.",
        signal_class_id="good_tag",
        horizons=(1, 3, 6),
    )
    artifact = evaluate_proposal(proposal, sb)
    assert artifact is not None
    text = render_for_system_prompt([artifact])
    assert "Promoted skills" in text
    assert "Test content for prompt rendering." in text
    assert "1, 3, 6" in text


def test_save_rejects_l2_artifact(tmp_path: Path) -> None:
    """save_promoted_skill is L3-only; passing an L2 artifact raises."""
    # Construct an L2 artifact manually (the gate only emits L3, so we
    # bypass it here to test the storage guard).
    from fingym.memory.schema import AuditEntry, DomainOfValidity

    l2 = MemoryArtifact(
        id="l2-test",
        tier="L2",
        content="probationary",
        domain_of_validity=DomainOfValidity(horizons=["1"]),
        derived_from=[],
        audit_trail=[
            AuditEntry(
                timestamp=datetime(2026, 5, 18),
                action="proposed",
                by="test",
                reason="probationary",
            )
        ],
    )
    with pytest.raises(ValueError, match="L3"):
        save_promoted_skill(l2, tmp_path)


# ---------------------------------------------------------------------------
# Live API integration (auto-skipif no key)
# ---------------------------------------------------------------------------


_SKIP_IF_NO_KEY = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set; skipping live API tests.",
)


@pytest.fixture(scope="module")
def anthropic_client() -> AnthropicClient:
    return AnthropicClient()


@_SKIP_IF_NO_KEY
def test_llm_agent_with_promoted_skills_runs_and_includes_them_in_context(
    anthropic_client: AnthropicClient, tmp_path: Path
) -> None:
    """An LlmAgent constructed with one promoted skill runs successfully
    (the system-prompt injection doesn't break the call). The skill text
    is in the rendered system prompt — we verify by checking promoted_skills."""
    # Build a synthetic L3 skill via the gate
    sb = _build_scoreboard_with_good_tag_calibration()
    proposal = Proposal(
        content="When 4+ of 6 signals are STRONG, expect positive realized return.",
        signal_class_id="good_tag",  # matches the scoreboard so the gate promotes
        horizons=(1,),
    )
    skill = evaluate_proposal(proposal, sb)
    assert skill is not None
    save_promoted_skill(skill, tmp_path)
    promoted = load_promoted_skills(tmp_path)
    assert len(promoted) == 1

    # Instantiate an LlmAgent with the promoted skill and run one forecast.
    agent = LlmAgent(anthropic_client, promoted_skills=promoted)
    stream: list[Emission] = ["strong", "strong", "strong", "strong", "mixed", "weak"]
    for e in stream:
        agent.observe(e)
    f = agent.forecast
    # Well-formed forecast
    assert abs(sum(f.values()) - 1.0) < 1e-6
    # Agent exposes its promoted skills
    assert len(agent.promoted_skills) == 1
    assert agent.promoted_skills[0].content == proposal.content


@_SKIP_IF_NO_KEY
def test_llm_agent_proposal_is_parsed_when_emitted(
    anthropic_client: AnthropicClient,
) -> None:
    """When the model decides to call propose_memory_item, the agent
    captures the proposal via .latest_proposal. The exact decision is
    model-dependent — this test verifies the plumbing, not the
    proposal frequency.

    We give the model a very strongly-patterned signal stream (all
    STRONG) and check that whatever it returns is well-formed. The
    proposal may be None on some calls — that's the model's choice
    and the test accepts it."""
    agent = LlmAgent(anthropic_client)
    stream: list[Emission] = ["strong"] * 8
    for e in stream:
        agent.observe(e)
    _ = agent.forecast  # triggers the LLM call
    proposal = agent.latest_proposal
    # Either the model proposed (in which case the proposal is well-formed)
    # or it didn't (in which case proposal is None). Both are valid.
    if proposal is not None:
        assert proposal.content.strip() != ""
        assert proposal.signal_class_id.strip() != ""
        assert len(proposal.horizons) > 0
