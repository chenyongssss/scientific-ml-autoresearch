from autoresearch.schemas import TaskSpec


def test_task_spec_supports_seeds_and_regimes():
    task = TaskSpec(
        name="demo",
        workspace=".",
        commands={"train": "x", "eval": "y"},
        seeds=[0, 1],
        evaluation_regimes=[{"name": "default", "description": "baseline regime"}],
    )
    assert task.seeds == [0, 1]
    assert task.evaluation_regimes[0].name == "default"
