from autoresearch.schemas import TaskSpec


def test_task_spec_supports_seeds_and_regimes():
    task = TaskSpec(
        name="demo",
        workspace=".",
        commands={"train": "x", "eval": "y"},
        seeds=[0, 1],
        evaluation_regimes=[{"name": "default", "description": "baseline regime"}],
        constraints=["conservation"],
        robustness_checks=[{"name": "ood-grid", "description": "shifted grid"}],
    )
    assert task.seeds == [0, 1]
    assert task.evaluation_regimes[0].name == "default"
    assert task.constraints == ["conservation"]
    assert task.robustness_checks[0].name == "ood-grid"
