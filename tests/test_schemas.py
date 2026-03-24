from autoresearch.schemas import TaskSpec


def test_task_spec_minimal():
    task = TaskSpec(name="demo", workspace=".", commands={"train": "x", "eval": "y"})
    assert task.name == "demo"
    assert task.workspace == "."
