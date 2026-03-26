from autoresearch.summarizer import build_summary
from autoresearch.schemas import ExperimentResult, ScientificCheckResult, TaskSpec


def test_summary_includes_anchor_delta():
    task = TaskSpec(
        name="demo",
        workspace=".",
        commands={"train": "x", "eval": "y"},
        metrics={"primary": ["rel_l2"], "secondary": []},
        planner={"baseline": {"model.width": 32}},
        reporting={"sort_by": "rel_l2", "lower_is_better": True},
        constraints=[{"name": "conservation", "metric": "conservation_error", "threshold": 0.001}],
        robustness_checks=[{"name": "shifted-grid", "eval_command": "python check.py --output {output_path}"}],
        seeds=[0, 1],
        evaluation_regimes=[{"name": "default"}, {"name": "harder"}],
    )
    historical = [
        ExperimentResult(experiment_id="exp_002", round_index=1, status="ok", metrics={"rel_l2": 0.11}, config={"model.width": 64}, run_dir="h"),
        ExperimentResult(experiment_id="exp_001", round_index=1, status="ok", metrics={"rel_l2": 0.2}, config={"model.width": 32}, run_dir="h2"),
    ]
    results = [
        ExperimentResult(
            experiment_id="exp_001",
            round_index=2,
            status="ok",
            metrics={"rel_l2": 0.2, "conservation_error": 0.002},
            config={"model.width": 64, "seed": 0, "evaluation_regime": "default"},
            run_dir="a",
            scientific_checks=[ScientificCheckResult(name="conservation", kind="constraint", status="failed", metric="conservation_error", value=0.002, threshold=0.001)],
        ),
        ExperimentResult(
            experiment_id="exp_002",
            round_index=2,
            status="ok",
            metrics={"rel_l2": 0.1, "conservation_error": 0.0005},
            config={"model.width": 64, "seed": 1, "evaluation_regime": "harder"},
            run_dir="b",
            scientific_checks=[
                ScientificCheckResult(name="conservation", kind="constraint", status="passed", metric="conservation_error", value=0.0005, threshold=0.001),
                ScientificCheckResult(name="shifted-grid", kind="robustness", status="passed", metrics={"rel_l2_shifted": 0.11}),
            ],
        ),
        ExperimentResult(experiment_id="exp_003", round_index=2, status="ok", metrics={"rel_l2": 0.12}, config={"model.width": 32, "seed": 0, "evaluation_regime": "default"}, run_dir="c"),
    ]
    summary = build_summary(task, 2, results, historical_results=historical, round_mode="validate")
    assert "Delta vs anchor" in summary
    assert "Compared with the round anchor" in summary
    assert "Round mode: validate" in summary
    assert "Claim strength" in summary
    assert "Claim taxonomy" in summary
    assert "Positive rounds so far" in summary
    assert "Historical evidence" in summary
    assert "Claim trajectory" in summary
    assert "Branch evidence" in summary
    assert "Aggregated branch evidence" in summary
    assert "Evidence status" in summary
    assert "Scientific checks passed" in summary
    assert "Per-experiment scientific check details" in summary
    assert "constraint:conservation -> passed" in summary
