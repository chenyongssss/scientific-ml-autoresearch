from autoresearch.schemas import TaskSpec


def test_task_spec_supports_seeds_and_regimes():
    task = TaskSpec(
        name="demo",
        workspace=".",
        commands={"train": "x", "eval": "y"},
        seeds=[0, 1],
        evaluation_regimes=[{"name": "default", "description": "baseline regime"}],
        constraints=[
            {"name": "conservation", "metric": "conservation_error", "threshold": 0.001, "direction": "lower_is_better"}
        ],
        robustness_checks=[{"name": "ood-grid", "description": "shifted grid"}],
    )
    assert task.seeds == [0, 1]
    assert task.evaluation_regimes[0].name == "default"
    assert task.constraints[0].name == "conservation"
    assert task.constraints[0].metric == "conservation_error"
    assert task.robustness_checks[0].name == "ood-grid"


def test_task_spec_accepts_legacy_string_constraints():
    task = TaskSpec(
        name="demo",
        workspace=".",
        commands={"train": "x", "eval": "y"},
        constraints=["conservation", "positivity"],
    )
    assert [constraint.name for constraint in task.constraints] == ["conservation", "positivity"]
    assert task.constraints[0].metric is None
