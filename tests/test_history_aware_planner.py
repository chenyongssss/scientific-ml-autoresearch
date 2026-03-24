from autoresearch.planner import build_round_plan
from autoresearch.schemas import ExperimentResult, History, HistoryEntry, TaskSpec


def test_second_round_uses_best_previous_config():
    task = TaskSpec(
        name="demo",
        workspace=".",
        commands={"train": "x", "eval": "y"},
        metrics={"primary": ["rel_l2"]},
        search_space={"model.width": [32, 64], "training.lr": [0.001, 0.0005]},
        planner={"baseline": {"model.width": 32, "training.lr": 0.001}},
        budget={"max_runs_per_round": 4, "max_rounds": 3},
        reporting={"sort_by": "rel_l2", "lower_is_better": True},
    )
    history = History(
        task_name="demo",
        entries=[
            HistoryEntry(
                round_index=1,
                plan_path="round_01_plan.yaml",
                experiments=[
                    ExperimentResult(experiment_id="exp_001", round_index=1, status="ok", metrics={"rel_l2": 0.2}, config={"model.width": 32, "training.lr": 0.001}, run_dir="a"),
                    ExperimentResult(experiment_id="exp_002", round_index=1, status="ok", metrics={"rel_l2": 0.1}, config={"model.width": 64, "training.lr": 0.001}, run_dir="b"),
                ],
            )
        ],
    )
    plan = build_round_plan(task, history)
    assert plan.round_index == 2
    assert plan.experiments[0].config["model.width"] == 64


def test_second_round_contains_ablation_of_best_change():
    task = TaskSpec(
        name="demo",
        workspace=".",
        commands={"train": "x", "eval": "y"},
        metrics={"primary": ["rel_l2"]},
        search_space={"model.width": [32, 64], "training.lr": [0.001, 0.0005]},
        planner={"baseline": {"model.width": 32, "training.lr": 0.001}},
        budget={"max_runs_per_round": 4, "max_rounds": 3},
        reporting={"sort_by": "rel_l2", "lower_is_better": True},
    )
    history = History(
        task_name="demo",
        entries=[
            HistoryEntry(
                round_index=1,
                plan_path="round_01_plan.yaml",
                experiments=[
                    ExperimentResult(experiment_id="exp_002", round_index=1, status="ok", metrics={"rel_l2": 0.1}, config={"model.width": 64, "training.lr": 0.001}, run_dir="b"),
                ],
            )
        ],
    )
    plan = build_round_plan(task, history)
    tags = [exp.tag for exp in plan.experiments]
    assert "ablation" in tags
    ablation = next(exp for exp in plan.experiments if exp.tag == "ablation")
    assert ablation.config["model.width"] == 32
