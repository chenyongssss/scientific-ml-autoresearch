from pathlib import Path

from autoresearch.runner import execute_plan
from autoresearch.schemas import RoundPlan, TaskSpec


def test_runner_passes_seed_and_regime_into_config_file(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    (workspace / "train.py").write_text(
        """
import argparse, json, yaml
from pathlib import Path
parser = argparse.ArgumentParser()
parser.add_argument('--config', required=True)
parser.add_argument('--output-dir', required=True)
args = parser.parse_args()
config = yaml.safe_load(Path(args.config).read_text())
out = Path(args.output_dir)
out.mkdir(parents=True, exist_ok=True)
(out / 'train_artifact.json').write_text(json.dumps({'rel_l2': 0.1, 'seed_seen': config.get('seed'), 'regime_seen': config.get('evaluation_regime')}))
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

    task = TaskSpec(
        name="demo",
        workspace=str(workspace),
        commands={
            "train": "python train.py --config {config_path} --output-dir {run_dir}",
            "eval": "python eval.py --run-dir {run_dir}",
        },
    )
    plan = RoundPlan(
        task_name="demo",
        round_index=1,
        experiments=[
            {"id": "exp_001", "round_index": 1, "config": {"seed": 7, "evaluation_regime": "harder"}}
        ],
    )
    results = execute_plan(task, plan, tmp_path)
    assert results[0].metrics["seed_seen"] == 7
    assert results[0].metrics["regime_seen"] == "harder"
