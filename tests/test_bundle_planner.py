from autoresearch.planner import build_round_plan
from autoresearch.schemas import History, TaskSpec


def test_first_round_expands_seed_and_regime_bundle():
    task = TaskSpec(
        name="demo",
        workspace=".",
        commands={"train": "x", "eval": "y"},
        search_space={"model.width": [32, 64]},
        planner={"baseline": {"model.width": 32}},
        budget={"max_runs_per_round": 4, "max_rounds": 3, "max_branches_per_round": 2, "max_evidence_runs_per_branch": 2},
        seeds=[0, 1],
        evaluation_regimes=[{"name": "default"}, {"name": "harder"}],
    )
    plan = build_round_plan(task, History(task_name="demo"))
    assert len(plan.experiments) == 4
    assert all("seed" in exp.config for exp in plan.experiments)
    assert all("evaluation_regime" in exp.config for exp in plan.experiments)
    assert plan.experiments[0].tag == "baseline"
    assert any(exp.tag.endswith("-evidence") for exp in plan.experiments[1:])


def test_second_round_anchor_keeps_canonical_best_and_expands_bundle():
    task = TaskSpec(
        name="demo",
        workspace=".",
        commands={"train": "x", "eval": "y"},
        metrics={"primary": ["rel_l2"]},
        search_space={"model.width": [32, 64], "training.lr": [0.001, 0.0005]},
        planner={"baseline": {"model.width": 32, "training.lr": 0.001}},
        budget={"max_runs_per_round": 3, "max_rounds": 3, "max_branches_per_round": 2, "max_evidence_runs_per_branch": 2},
        reporting={"sort_by": "rel_l2", "lower_is_better": True},
        seeds=[0, 1],
    )
    history = History.model_validate(
        {
            "task_name": "demo",
            "entries": [
                {
                    "round_index": 1,
                    "plan_path": "round_01_plan.yaml",
                    "experiments": [
                        {
                            "experiment_id": "exp_001",
                            "round_index": 1,
                            "status": "ok",
                            "metrics": {"rel_l2": 0.1},
                            "config": {"model.width": 64, "training.lr": 0.001, "seed": 1},
                            "run_dir": "a",
                        }
                    ],
                }
            ],
        }
    )
    plan = build_round_plan(task, history)
    assert plan.experiments[0].config["model.width"] == 64
    assert "seed" in plan.experiments[0].config
    assert len(plan.experiments) >= 2
