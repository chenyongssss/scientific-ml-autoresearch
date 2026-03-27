from autoresearch.evidence import aggregate_branch_evidence, detect_evidence_gaps
from autoresearch.schemas import ExperimentResult, ScientificCheckResult, TaskSpec


def test_detect_evidence_gaps_identifies_missing_seed_and_regime_coverage():
    task = TaskSpec(
        name="demo",
        workspace=".",
        commands={"train": "x", "eval": "y"},
        metrics={"primary": ["rel_l2"]},
        planner={"baseline": {"model.width": 32}},
        seeds=[0, 1],
        evaluation_regimes=[{"name": "default"}, {"name": "harder"}],
    )
    results = [
        ExperimentResult(
            experiment_id="exp_001",
            round_index=1,
            status="ok",
            metrics={"rel_l2": 0.1},
            config={"model.width": 64, "seed": 0, "evaluation_regime": "default"},
            run_dir="a",
            scientific_checks=[ScientificCheckResult(name="shifted-grid", kind="robustness", status="pending")],
        )
    ]
    card = aggregate_branch_evidence(task, results)[0]
    gaps = detect_evidence_gaps(task, card)
    assert "seed-coverage" in gaps
    assert "regime-coverage" in gaps
    assert "pending-checks" in gaps
    assert "replication" in gaps
    assert card["missing_seeds"] == [1]
    assert card["missing_regimes"] == ["harder"]
    assert card["coverage_guidance"]["target_missing_seeds"] == [1]
    assert card["coverage_guidance"]["target_missing_regimes"] == ["harder"]
    assert card["coverage_guidance"]["recommended_fixed_axes"]["evaluation_regime"] == ["default"]
    assert card["coverage_guidance"]["recommended_fixed_axes"]["seed"] == [0]



def test_detect_evidence_gaps_flags_missing_axis_annotations():
    task = TaskSpec(
        name="demo",
        workspace=".",
        commands={"train": "x", "eval": "y"},
        metrics={"primary": ["rel_l2"]},
        planner={"baseline": {"model.width": 32}},
        seeds=[0, 1],
        evaluation_regimes=[{"name": "default"}, {"name": "harder"}],
    )
    results = [
        ExperimentResult(
            experiment_id="exp_001",
            round_index=1,
            status="ok",
            metrics={"rel_l2": 0.1},
            config={"model.width": 64},
            run_dir="a",
        )
    ]
    card = aggregate_branch_evidence(task, results)[0]
    gaps = detect_evidence_gaps(task, card)
    assert "seed-coverage" in gaps
    assert "regime-coverage" in gaps
    assert card["missing_seeds"] == [0, 1]
    assert card["missing_regimes"] == ["default", "harder"]
    assert card["coverage_guidance"]["target_missing_seeds"] == [0, 1]
    assert card["coverage_guidance"]["target_missing_regimes"] == ["default", "harder"]
    assert card["coverage_guidance"]["recommended_fixed_axes"] == {}
