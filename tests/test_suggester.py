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
    results = [
        ExperimentResult(experiment_id="exp_001", round_index=2, status="ok", metrics={"rel_l2": 0.2}, config={"model.width": 64}, run_dir="a"),
        ExperimentResult(experiment_id="exp_002", round_index=2, status="ok", metrics={"rel_l2": 0.1}, config={"model.width": 64, "model.depth": 3}, run_dir="b"),
        ExperimentResult(experiment_id="exp_003", round_index=2, status="ok", metrics={"rel_l2": 0.12}, config={"model.width": 64, "training.lr": 0.0005}, run_dir="c"),
    ]
    suggestion = build_suggestions(task, results)
    assert "round anchor" in suggestion.rationale
    assert "claim strength" in suggestion.rationale.lower()
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
    results = [
        ExperimentResult(experiment_id="exp_001", round_index=2, status="ok", metrics={"rel_l2": 0.1}, config={"model.width": 64}, run_dir="a"),
        ExperimentResult(experiment_id="exp_002", round_index=2, status="ok", metrics={"rel_l2": 0.1}, config={"model.width": 64, "model.depth": 3}, run_dir="b"),
    ]
    suggestion = build_suggestions(task, results)
    assert suggestion.next_action_type == "stop"
