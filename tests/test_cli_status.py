from pathlib import Path

import yaml
from typer.testing import CliRunner

from autoresearch.cli import app
from autoresearch.schemas import ExperimentResult, History, HistoryEntry
from autoresearch.storage import save_evidence_state, save_history


runner = CliRunner()


def test_status_surfaces_evidence_gaps_and_missing_axes(tmp_path: Path):
    task_payload = {
        "name": "demo",
        "workspace": ".",
        "commands": {"train": "x", "eval": "y"},
        "metrics": {"primary": ["rel_l2"], "secondary": []},
        "planner": {"baseline": {"model.width": 32}},
        "reporting": {"sort_by": "rel_l2", "lower_is_better": True},
        "budget": {"max_runs_per_round": 4, "max_rounds": 3},
        "seeds": [0, 1],
        "evaluation_regimes": [{"name": "default"}, {"name": "harder"}],
    }
    task_path = tmp_path / "task.yaml"
    task_path.write_text(yaml.safe_dump(task_payload, sort_keys=False), encoding="utf-8")

    save_history(
        tmp_path,
        History(
            task_name="demo",
            entries=[
                HistoryEntry(
                    round_index=1,
                    plan_path=str(tmp_path / "round_01_plan.yaml"),
                    experiments=[
                        ExperimentResult(
                            experiment_id="exp_001",
                            round_index=1,
                            status="ok",
                            metrics={"rel_l2": 0.1},
                            config={"model.width": 64, "seed": 0, "evaluation_regime": "default"},
                            run_dir="run_001",
                        )
                    ],
                )
            ],
        ),
    )
    save_evidence_state(
        tmp_path,
        1,
        {
            "branch_cards": [
                {
                    "branch_label": "model.width=64",
                    "evidence_status": "observed",
                    "completed_members": 1,
                    "incomplete_members": 1,
                    "evidence_gaps": ["seed-coverage", "regime-coverage"],
                    "missing_seeds": [1],
                    "missing_regimes": ["harder"],
                    "coverage_guidance": {
                        "target_missing_seeds": [1],
                        "target_missing_regimes": ["harder"],
                        "recommended_fixed_axes": {"seed": [0], "evaluation_regime": ["default"]},
                    },
                }
            ]
        },
    )

    result = runner.invoke(app, ["status", "--run", str(tmp_path)])

    assert result.exit_code == 0
    assert "Latest persisted evidence state:" in result.stdout
    assert "gaps=seed-coverage, regime-coverage" in result.stdout
    assert "missing_seeds=1" in result.stdout
    assert "missing_regimes=harder" in result.stdout
    assert "target_missing_seeds=1" in result.stdout
    assert "target_missing_regimes=harder" in result.stdout
    assert "fixed_seed=0" in result.stdout
    assert "fixed_regime=default" in result.stdout
