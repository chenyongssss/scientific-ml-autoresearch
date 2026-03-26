from pathlib import Path

from autoresearch.runner import execute_plan
from autoresearch.schemas import RoundPlan, TaskSpec


def test_resume_recovers_invalid_artifact_by_rerunning(tmp_path: Path):
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
(out / 'train_artifact.json').write_text(json.dumps({'rel_l2': 0.05}))
""".strip(),
        encoding="utf-8",
    )
    (workspace / "eval.py").write_text(
        """
import argparse
from pathlib import Path
parser = argparse.ArgumentParser()
parser.add_argument('--run-dir', required=True)
args = parser.parse_args()
run_dir = Path(args.run_dir)
(run_dir / 'metrics.json').write_text((run_dir / 'train_artifact.json').read_text())
""".strip(),
        encoding="utf-8",
    )

    exp_dir = tmp_path / "round_01" / "exp_001"
    exp_dir.mkdir(parents=True, exist_ok=True)
    (exp_dir / "metrics.json").write_text("{}", encoding="utf-8")

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
    assert results[0].metrics["rel_l2"] == 0.05
    assert results[0].artifact_status.artifact_valid is True
