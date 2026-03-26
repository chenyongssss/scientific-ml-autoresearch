from autoresearch.planner import build_round_plan
from autoresearch.schemas import History, TaskSpec


def test_two_level_budget_limits_branches_and_evidence_runs():
    task = TaskSpec(
        name="demo",
        workspace=".",
        commands={"train": "x", "eval": "y"},
        search_space={"model.width": [32, 64], "training.lr": [0.001, 0.0005]},
        planner={"baseline": {"model.width": 32, "training.lr": 0.001}},
        budget={
            "max_runs_per_round": 5,
            "max_rounds": 3,
            "max_branches_per_round": 2,
            "max_evidence_runs_per_branch": 2,
        },
        seeds=[0, 1, 2],
        evaluation_regimes=[{"name": "default"}, {"name": "harder"}],
    )
    plan = build_round_plan(task, History(task_name="demo"))
    assert len(plan.branches) <= 2
    assert len(plan.experiments) <= 5
    assert all(branch.planned_evidence_runs <= 2 for branch in plan.branches)


def test_round_plan_exposes_branch_metadata():
    task = TaskSpec(
        name="demo",
        workspace=".",
        commands={"train": "x", "eval": "y"},
        search_space={"model.width": [32, 64]},
        planner={"baseline": {"model.width": 32}},
        budget={"max_runs_per_round": 3, "max_rounds": 2, "max_branches_per_round": 2, "max_evidence_runs_per_branch": 2},
        seeds=[0, 1],
    )
    plan = build_round_plan(task, History(task_name="demo"))
    assert plan.branches
    assert plan.branches[0].evidence_members
    assert plan.experiments[0].branch_id == plan.branches[0].id
