from pathlib import Path

from autoresearch.runner import execute_plan
from autoresearch.schemas import RoundPlan, TaskSpec


def test_runner_executes_constraints_and_robustness_checks(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    (workspace / "train.py").write_text(
        """
import argparse, json
from pathlib import Path
parser = argparse.ArgumentParser()
parser.add_argument('--config', required=True)
parser.add_argument('--output-dir', required=True)
args = parser.parse_args()
out = Path(args.output_dir)
out.mkdir(parents=True, exist_ok=True)
(out / 'train_artifact.json').write_text(json.dumps({'rel_l2': 0.1, 'conservation_error': 0.0005}))
""".strip(),
        encoding="utf-8",
    )
    (workspace / "eval.py").write_text(
        """
import argparse, json
from pathlib import Path
parser = argparse.ArgumentParser()
parser.add_argument('--run-dir', required=True)
args = parser.parse_args()
run_dir = Path(args.run_dir)
(run_dir / 'metrics.json').write_text((run_dir / 'train_artifact.json').read_text())
""".strip(),
        encoding="utf-8",
    )
    (workspace / "robust.py").write_text(
        """
import argparse, json
from pathlib import Path
parser = argparse.ArgumentParser()
parser.add_argument('--run-dir', required=True)
parser.add_argument('--output', required=True)
args = parser.parse_args()
out = Path(args.output)
out.write_text(json.dumps({'status': 'passed', 'metrics': {'rel_l2_shifted': 0.12}, 'details': 'ok'}))
""".strip(),
        encoding="utf-8",
    )

    task = TaskSpec(
        name="demo",
        workspace=str(workspace),
        commands={
            "train": "python train.py --config {config_path} --output-dir {run_dir}",
            "eval": "python eval.py --run-dir {run_dir}",
        },
        constraints=[{"name": "conservation", "metric": "conservation_error", "threshold": 0.001}],
        robustness_checks=[
            {"name": "shifted-grid", "eval_command": "python robust.py --run-dir {run_dir} --output {output_path}", "output_file": "shifted.json"}
        ],
    )
    plan = RoundPlan(task_name="demo", round_index=1, experiments=[{"id": "exp_001", "round_index": 1, "config": {}}])

    results = execute_plan(task, plan, tmp_path)
    assert len(results) == 1
    result = results[0]
    assert result.status == "ok"
    assert any(check.name == "conservation" and check.status == "passed" for check in result.scientific_checks)
    assert any(check.name == "shifted-grid" and check.status == "passed" for check in result.scientific_checks)
    assert result.provenance is not None
    assert result.artifact_status.metrics_present is True
    assert result.artifact_status.artifact_valid is True


def test_runner_can_resume_completed_experiment(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "train.py").write_text("raise SystemExit(99)", encoding="utf-8")
    (workspace / "eval.py").write_text("raise SystemExit(99)", encoding="utf-8")

    exp_dir = tmp_path / "round_01" / "exp_001"
    exp_dir.mkdir(parents=True, exist_ok=True)
    (exp_dir / "metrics.json").write_text('{"rel_l2": 0.2}', encoding="utf-8")

    task = TaskSpec(
        name="demo",
        workspace=str(workspace),
        commands={
            "train": "python train.py --config {config_path} --output-dir {run_dir}",
            "eval": "python eval.py --run-dir {run_dir}",
        },
        metrics={"primary": ["rel_l2"]},
        reporting={"sort_by": "rel_l2", "lower_is_better": True},
    )
    plan = RoundPlan(task_name="demo", round_index=1, experiments=[{"id": "exp_001", "round_index": 1, "config": {}}])

    results = execute_plan(task, plan, tmp_path, resume=True)
    assert results[0].status == "ok"
    assert results[0].provenance is not None and results[0].provenance.resumed is True
