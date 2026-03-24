from autoresearch.summarizer import build_summary
from autoresearch.schemas import ExperimentResult, TaskSpec


def test_summary_includes_anchor_delta():
    task = TaskSpec(
        name="demo",
        workspace=".",
        commands={"train": "x", "eval": "y"},
        metrics={"primary": ["rel_l2"], "secondary": []},
        planner={"baseline": {"model.width": 32}},
        reporting={"sort_by": "rel_l2", "lower_is_better": True},
        constraints=["conservation"],
    )
    historical = [
        ExperimentResult(experiment_id="exp_002", round_index=1, status="ok", metrics={"rel_l2": 0.11}, config={"model.width": 64}, run_dir="h"),
        ExperimentResult(experiment_id="exp_001", round_index=1, status="ok", metrics={"rel_l2": 0.2}, config={"model.width": 32}, run_dir="h2"),
    ]
    results = [
        ExperimentResult(experiment_id="exp_001", round_index=2, status="ok", metrics={"rel_l2": 0.2}, config={"model.width": 64}, run_dir="a"),
        ExperimentResult(experiment_id="exp_002", round_index=2, status="ok", metrics={"rel_l2": 0.1}, config={"model.width": 32}, run_dir="b"),
        ExperimentResult(experiment_id="exp_003", round_index=2, status="ok", metrics={"rel_l2": 0.12}, config={"model.width": 64, "model.depth": 3}, run_dir="c"),
    ]
    summary = build_summary(task, 2, results, historical_results=historical, round_mode="validate")
    assert "Delta vs anchor" in summary
    assert "Compared with the round anchor" in summary
    assert "Round mode: validate" in summary
    assert "Claim strength" in summary
    assert "Claim assessment" in summary
    assert "Positive rounds so far" in summary
    assert "Historical evidence" in summary
    assert "Claim trajectory" in summary
    assert "Branch evidence" in summary
