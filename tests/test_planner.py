from autoresearch.planner import build_round_plan
from autoresearch.schemas import History, TaskSpec


def test_build_round_plan():
    task = TaskSpec(
        name="demo",
        workspace=".",
        commands={"train": "x", "eval": "y"},
        search_space={"model.width": [32, 64], "training.lr": [0.001, 0.0005]},
        planner={"baseline": {"model.width": 32, "training.lr": 0.001}},
        budget={"max_runs_per_round": 4, "max_rounds": 3},
    )
    plan = build_round_plan(task, History(task_name="demo"))
    assert plan.round_index == 1
    assert len(plan.experiments) >= 2
