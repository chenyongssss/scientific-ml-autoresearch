from autoresearch.suggester import build_suggestions
from autoresearch.schemas import ExperimentResult, TaskSpec


def test_suggestions_reference_anchor_gain():
    task = TaskSpec(
        name="demo",
        workspace=".",
        commands={"train": "x", "eval": "y"},
        metrics={"primary": ["rel_l2"]},
        planner={"baseline": {"model.width": 32}},
        reporting={"sort_by": "rel_l2", "lower_is_better": True},
        constraints=["conservation"],
        robustness_checks=[{"name": "shifted-grid"}],
    )
    historical = [
        ExperimentResult(experiment_id="exp_001", round_index=1, status="ok", metrics={"rel_l2": 0.2}, config={"model.width": 32}, run_dir="h1"),
        ExperimentResult(experiment_id="exp_002", round_index=1, status="ok", metrics={"rel_l2": 0.1}, config={"model.width": 64}, run_dir="h2"),
    ]
    results = [
        ExperimentResult(experiment_id="exp_001", round_index=2, status="ok", metrics={"rel_l2": 0.2}, config={"model.width": 64}, run_dir="a"),
        ExperimentResult(experiment_id="exp_002", round_index=2, status="ok", metrics={"rel_l2": 0.1}, config={"model.width": 64, "model.depth": 3}, run_dir="b"),
        ExperimentResult(experiment_id="exp_003", round_index=2, status="ok", metrics={"rel_l2": 0.12}, config={"model.width": 64, "training.lr": 0.0005}, run_dir="c"),
    ]
    suggestion = build_suggestions(task, results, historical_results=historical)
    assert "round anchor" in suggestion.rationale
    assert "claim strength" in suggestion.rationale.lower()
    assert "Historical positive rounds" in suggestion.rationale
    assert any("robustness checks" in action for action in suggestion.actions)


def test_suggestions_can_trigger_stop_when_no_improvement():
    task = TaskSpec(
        name="demo",
        workspace=".",
        commands={"train": "x", "eval": "y"},
        metrics={"primary": ["rel_l2"]},
        planner={"baseline": {"model.width": 32}},
        reporting={"sort_by": "rel_l2", "lower_is_better": True},
    )
    historical = [
        ExperimentResult(experiment_id="exp_001", round_index=1, status="ok", metrics={"rel_l2": 0.1}, config={"model.width": 64}, run_dir="h1"),
        ExperimentResult(experiment_id="exp_002", round_index=1, status="ok", metrics={"rel_l2": 0.1}, config={"model.width": 64, "model.depth": 3}, run_dir="h2"),
    ]
    results = [
        ExperimentResult(experiment_id="exp_001", round_index=2, status="ok", metrics={"rel_l2": 0.1}, config={"model.width": 64}, run_dir="a"),
        ExperimentResult(experiment_id="exp_002", round_index=2, status="ok", metrics={"rel_l2": 0.1}, config={"model.width": 64, "model.depth": 3}, run_dir="b"),
    ]
    suggestion = build_suggestions(task, results, historical_results=historical)
    assert suggestion.next_action_type == "stop"
