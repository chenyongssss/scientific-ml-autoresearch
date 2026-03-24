from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .schemas import ExperimentResult, RoundPlan, TaskSpec
from .storage import dump_yaml
from .utils import nest_dict


def _format_command(template: str, config_path: Path, run_dir: Path) -> str:
    return template.format(config_path=str(config_path), run_dir=str(run_dir))


def execute_plan(task: TaskSpec, plan: RoundPlan, run_root: Path) -> list[ExperimentResult]:
    workspace = (run_root / task.workspace).resolve() if not Path(task.workspace).is_absolute() else Path(task.workspace)
    if not workspace.exists():
        workspace = (run_root.parent / task.workspace).resolve()

    round_dir = run_root / f"round_{plan.round_index:02d}"
    round_dir.mkdir(parents=True, exist_ok=True)
    results: list[ExperimentResult] = []

    for exp in plan.experiments:
        exp_dir = round_dir / exp.id
        exp_dir.mkdir(parents=True, exist_ok=True)
        config_path = exp_dir / "config.yaml"
        dump_yaml(config_path, nest_dict(exp.config))

        train_log = exp_dir / "train.log"
        eval_log = exp_dir / "eval.log"
        metrics_path = exp_dir / "metrics.json"

        train_cmd = _format_command(task.commands.train, config_path, exp_dir)
        eval_cmd = _format_command(task.commands.eval, config_path, exp_dir)

        status = "ok"
        error = None

        with train_log.open("w", encoding="utf-8") as train_handle:
            train_proc = subprocess.run(train_cmd, cwd=workspace, shell=True, stdout=train_handle, stderr=subprocess.STDOUT, text=True)
        if train_proc.returncode != 0:
            status = "failed"
            error = f"train failed with exit code {train_proc.returncode}"

        if status == "ok":
            with eval_log.open("w", encoding="utf-8") as eval_handle:
                eval_proc = subprocess.run(eval_cmd, cwd=workspace, shell=True, stdout=eval_handle, stderr=subprocess.STDOUT, text=True)
            if eval_proc.returncode != 0:
                status = "failed"
                error = f"eval failed with exit code {eval_proc.returncode}"

        metrics = {}
        if metrics_path.exists():
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))

        results.append(
            ExperimentResult(
                experiment_id=exp.id,
                round_index=plan.round_index,
                status=status,
                metrics=metrics,
                config=exp.config,
                run_dir=str(exp_dir),
                error=error,
            )
        )

    return results
