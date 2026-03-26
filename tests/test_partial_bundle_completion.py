from pathlib import Path

from autoresearch.planner import build_round_plan
from autoresearch.schemas import History, HistoryEntry, ExperimentResult, TaskSpec
from autoresearch.storage import save_evidence_state


def test_planner_prioritizes_partial_bundle_completion_from_persisted_state(tmp_path: Path):
    task = TaskSpec(
        name="demo",
        workspace=".",
        commands={"train": "x", "eval": "y"},
        metrics={"primary": ["rel_l2"]},
        planner={"baseline": {"model.width": 32}},
        search_space={"model.width": [32, 64]},
        budget={"max_runs_per_round": 3, "max_rounds": 3, "max_branches_per_round": 1, "max_evidence_runs_per_branch": 2},
        seeds=[0, 1],
    )
    run_root = tmp_path / "run"
    run_root.mkdir()
    history = History(
        task_name="demo",
        entries=[
            HistoryEntry(
                round_index=1,
                plan_path=str(run_root / "round_01_plan.yaml"),
                experiments=[
                    ExperimentResult(
                        experiment_id="exp_001",
                        round_index=1,
                        status="ok",
                        metrics={"rel_l2": 0.1},
                        config={"model.width": 64, "seed": 0},
                        run_dir="a",
                    )
                ],
            )
        ],
    )
    save_evidence_state(
        run_root,
        1,
        {
            "claim_taxonomy": "promising",
            "branch_cards": [
                {
                    "branch_label": "model.width",
                    "canonical_config": {"model.width": 64},
                    "seeds": [0, 1],
                    "regimes": [],
                    "evidence_status": "promising",
                    "completed_members": 1,
                    "incomplete_members": 1,
                    "member_completion": [
                        {"experiment_id": "exp_001", "axes": {"seed": 0}, "artifact_valid": True, "status": "ok"},
                        {"experiment_id": "missing_seed_1", "axes": {"seed": 1}, "artifact_valid": False, "status": "missing"},
                    ],
                    "evidence_gaps": ["partial-bundle", "seed-coverage"],
                }
            ],
        },
    )
    plan = build_round_plan(task, history)
    assert plan.branches
    assert plan.branches[0].tag == "validate"
    assert any(exp.config.get("seed") == 1 for exp in plan.experiments)
