from autoresearch.schemas import TaskSpec


def test_task_spec_minimal():
    task = TaskSpec(name="demo", workspace=".", commands={"train": "x", "eval": "y"})
    assert task.name == "demo"
    assert task.workspace == "."
    assert task.budget.max_branches_per_round == task.budget.max_runs_per_round
    assert task.budget.max_evidence_runs_per_branch == 1
