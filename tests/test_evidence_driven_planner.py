from autoresearch.planner import build_round_plan
from autoresearch.schemas import ExperimentResult, History, HistoryEntry, ScientificCheckResult, TaskSpec


def test_planner_prioritizes_evidence_gap_validation():
    task = TaskSpec(
        name="demo",
        workspace=".",
        commands={"train": "x", "eval": "y"},
        metrics={"primary": ["rel_l2"]},
        search_space={"model.width": [32, 64], "training.lr": [0.001, 0.0005]},
        planner={"baseline": {"model.width": 32, "training.lr": 0.001}},
        budget={"max_runs_per_round": 4, "max_rounds": 3, "max_branches_per_round": 2, "max_evidence_runs_per_branch": 2},
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
                        config={"model.width": 64, "training.lr": 0.001, "seed": 0, "evaluation_regime": "default"},
                        run_dir="a",
                        scientific_checks=[ScientificCheckResult(name="shifted-grid", kind="robustness", status="pending")],
                    )
                ],
            )
        ],
    )
    plan = build_round_plan(task, history)
    assert plan.branches
    assert all(branch.tag == "validate" for branch in plan.branches)
    assert any(note.startswith("gap_focus=") for branch in plan.branches for note in branch.notes)
