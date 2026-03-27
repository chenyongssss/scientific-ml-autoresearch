from pathlib import Path

import yaml
from typer.testing import CliRunner

from autoresearch.cli import app
from autoresearch.evidence import build_evidence_state
from autoresearch.planner import build_round_plan
from autoresearch.schemas import ExperimentResult, History, HistoryEntry, TaskSpec
from autoresearch.storage import save_evidence_state, save_history
from autoresearch.summarizer import build_summary


runner = CliRunner()


def test_evidence_loop_surfaces_and_targets_missing_axes(tmp_path: Path):
    task_payload = {
        "name": "demo",
        "workspace": ".",
        "commands": {"train": "x", "eval": "y"},
        "metrics": {"primary": ["rel_l2"], "secondary": []},
        "search_space": {"model.width": [32, 64]},
        "planner": {"baseline": {"model.width": 32}},
        "budget": {"max_runs_per_round": 2, "max_rounds": 3, "max_branches_per_round": 1, "max_evidence_runs_per_branch": 1},
        "reporting": {"sort_by": "rel_l2", "lower_is_better": True},
        "seeds": [0, 1],
        "evaluation_regimes": [{"name": "default"}, {"name": "harder"}],
    }
    task_path = tmp_path / "task.yaml"
    task_path.write_text(yaml.safe_dump(task_payload, sort_keys=False), encoding="utf-8")
    task = TaskSpec(**task_payload)

    history = History(
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
                        metrics={"rel_l2": 0.10},
                        config={"model.width": 64, "seed": 0, "evaluation_regime": "default"},
                        run_dir="run_001",
                        artifact_status={"metrics_present": True, "scientific_checks_complete": True, "robustness_complete": True, "artifact_valid": True},
                    ),
                    ExperimentResult(
                        experiment_id="exp_002",
                        round_index=1,
                        status="ok",
                        metrics={"rel_l2": 0.09},
                        config={"model.width": 64, "seed": 1, "evaluation_regime": "default"},
                        run_dir="run_002",
                        artifact_status={"metrics_present": True, "scientific_checks_complete": True, "robustness_complete": True, "artifact_valid": True},
                    ),
                ],
            )
        ],
    )
    save_history(tmp_path, history)

    evidence_state = build_evidence_state(task, history.entries[0].experiments)
    save_evidence_state(tmp_path, 1, evidence_state)

    summary = build_summary(task, 1, history.entries[0].experiments)
    assert "Current evidence gaps for the leading branch:" in summary
    assert "regime-coverage" in summary
    assert "Missing regimes for the leading branch: `harder`." in summary

    plan = build_round_plan(task, history)
    assert plan.branches
    assert plan.branches[0].tag == "validate"
    assert any(note.startswith("gap_focus=") for note in plan.branches[0].notes)
    assert plan.experiments[0].config["evaluation_regime"] == "harder"
    assert plan.experiments[0].config["seed"] in {0, 1}

    result = runner.invoke(app, ["status", "--run", str(tmp_path)])
    assert result.exit_code == 0
    assert "Latest persisted evidence state:" in result.stdout
    assert "gaps=regime-coverage" in result.stdout
    assert "missing_regimes=harder" in result.stdout
