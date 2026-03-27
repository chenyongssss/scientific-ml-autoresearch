from autoresearch.planner import build_round_plan
from autoresearch.schemas import ExperimentResult, History, HistoryEntry, TaskSpec


def test_planner_targets_missing_seed_using_observed_regime():
    task = TaskSpec(
        name="demo",
        workspace=".",
        commands={"train": "x", "eval": "y"},
        metrics={"primary": ["rel_l2"]},
        planner={"baseline": {"model.width": 32}},
        search_space={"model.width": [32, 64]},
        budget={"max_runs_per_round": 2, "max_rounds": 3, "max_branches_per_round": 1, "max_evidence_runs_per_branch": 1},
        reporting={"sort_by": "rel_l2", "lower_is_better": True},
        seeds=[0, 1],
        evaluation_regimes=[{"name": "default"}, {"name": "harder"}],
    )
    history = History(
        task_name="demo",
        entries=[
            HistoryEntry(
                round_index=1,
                plan_path="round_01_plan.yaml",
                experiments=[
                    ExperimentResult(
                        experiment_id="exp_001",
                        round_index=1,
                        status="ok",
                        metrics={"rel_l2": 0.1},
                        config={"model.width": 64, "seed": 0, "evaluation_regime": "default"},
                        run_dir="a",
                    ),
                    ExperimentResult(
                        experiment_id="exp_002",
                        round_index=1,
                        status="ok",
                        metrics={"rel_l2": 0.09},
                        config={"model.width": 64, "seed": 0, "evaluation_regime": "harder"},
                        run_dir="b",
                    ),
                ],
            )
        ],
    )

    plan = build_round_plan(task, history)

    assert plan.branches
    assert plan.experiments[0].config["seed"] == 1
    assert plan.experiments[0].config["evaluation_regime"] in {"default", "harder"}
    assert any("target missing seeds: 1" in note for note in plan.branches[0].notes)


def test_planner_targets_missing_regime_using_observed_seed():
    task = TaskSpec(
        name="demo",
        workspace=".",
        commands={"train": "x", "eval": "y"},
        metrics={"primary": ["rel_l2"]},
        planner={"baseline": {"model.width": 32}},
        search_space={"model.width": [32, 64]},
        budget={"max_runs_per_round": 2, "max_rounds": 3, "max_branches_per_round": 1, "max_evidence_runs_per_branch": 1},
        reporting={"sort_by": "rel_l2", "lower_is_better": True},
        seeds=[0, 1],
        evaluation_regimes=[{"name": "default"}, {"name": "harder"}],
    )
    history = History(
        task_name="demo",
        entries=[
            HistoryEntry(
                round_index=1,
                plan_path="round_01_plan.yaml",
                experiments=[
                    ExperimentResult(
                        experiment_id="exp_001",
                        round_index=1,
                        status="ok",
                        metrics={"rel_l2": 0.1},
                        config={"model.width": 64, "seed": 0, "evaluation_regime": "default"},
                        run_dir="a",
                    ),
                    ExperimentResult(
                        experiment_id="exp_002",
                        round_index=1,
                        status="ok",
                        metrics={"rel_l2": 0.09},
                        config={"model.width": 64, "seed": 1, "evaluation_regime": "default"},
                        run_dir="b",
                    ),
                ],
            )
        ],
    )

    plan = build_round_plan(task, history)

    assert plan.branches
    assert plan.experiments[0].config["evaluation_regime"] == "harder"
    assert plan.experiments[0].config["seed"] in {0, 1}
    assert any("target missing regimes: harder" in note for note in plan.branches[0].notes)
