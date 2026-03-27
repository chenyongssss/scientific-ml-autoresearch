from autoresearch.evidence import build_evidence_state
from autoresearch.schemas import ExperimentResult, TaskSpec


def test_evidence_state_exposes_structured_coverage_guidance():
    task = TaskSpec(
        name="demo",
        workspace=".",
        commands={"train": "x", "eval": "y"},
        metrics={"primary": ["rel_l2"]},
        planner={"baseline": {"model.width": 32}},
        reporting={"sort_by": "rel_l2", "lower_is_better": True},
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
        ),
        ExperimentResult(
            experiment_id="exp_002",
            round_index=1,
            status="ok",
            metrics={"rel_l2": 0.09},
            config={"model.width": 64, "seed": 1, "evaluation_regime": "default"},
            run_dir="b",
        ),
    ]

    state = build_evidence_state(task, results)
    card = state["best_branch"]

    assert card["coverage_guidance"]["target_missing_seeds"] == []
    assert card["coverage_guidance"]["target_missing_regimes"] == ["harder"]
    assert card["coverage_guidance"]["recommended_fixed_axes"]["seed"] == [0, 1]
