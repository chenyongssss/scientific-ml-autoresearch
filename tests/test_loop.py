from autoresearch.suggester import build_suggestions
from autoresearch.schemas import ExperimentResult, TaskSpec


def test_suggestion_generation():
    task = TaskSpec(
        name="demo",
        workspace=".",
        commands={"train": "x", "eval": "y"},
        metrics={"primary": ["rel_l2"]},
        reporting={"sort_by": "rel_l2", "lower_is_better": True},
    )
    results = [
        ExperimentResult(experiment_id="exp_001", round_index=1, status="ok", metrics={"rel_l2": 0.2}, run_dir="a"),
        ExperimentResult(experiment_id="exp_002", round_index=1, status="ok", metrics={"rel_l2": 0.1}, run_dir="b"),
    ]
    suggestion = build_suggestions(task, results)
    assert "exp_002" in suggestion.rationale
