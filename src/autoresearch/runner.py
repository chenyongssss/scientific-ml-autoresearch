from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .schemas import ArtifactStatus, ExperimentResult, ProvenanceRecord, RoundPlan, ScientificCheckResult, TaskSpec
from .storage import dump_yaml
from .utils import nest_dict


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_payload(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _format_command(template: str, config_path: Path, run_dir: Path, check_name: str | None = None, output_path: Path | None = None) -> str:
    return template.format(
        config_path=str(config_path),
        run_dir=str(run_dir),
        check_name=check_name or "",
        output_path=str(output_path) if output_path is not None else "",
    )


def _run_command(command: str, cwd: Path, log_path: Path) -> subprocess.CompletedProcess:
    with log_path.open("w", encoding="utf-8") as handle:
        return subprocess.run(command, cwd=cwd, shell=True, stdout=handle, stderr=subprocess.STDOUT, text=True)


def _evaluate_constraints(task: TaskSpec, metrics: dict) -> list[ScientificCheckResult]:
    checks: list[ScientificCheckResult] = []
    for constraint in task.constraints:
        if constraint.metric is None or constraint.threshold is None:
            checks.append(
                ScientificCheckResult(
                    name=constraint.name,
                    kind="constraint",
                    status="pending",
                    details="Named constraint only; add metric + threshold to evaluate automatically.",
                )
            )
            continue
        value = metrics.get(constraint.metric)
        if value is None:
            checks.append(
                ScientificCheckResult(
                    name=constraint.name,
                    kind="constraint",
                    status="missing",
                    metric=constraint.metric,
                    threshold=constraint.threshold,
                    direction=constraint.direction,
                    details="Constraint metric was not found in metrics.json.",
                )
            )
            continue
        passed = value <= constraint.threshold if constraint.direction == "lower_is_better" else value >= constraint.threshold
        checks.append(
            ScientificCheckResult(
                name=constraint.name,
                kind="constraint",
                status="passed" if passed else "failed",
                metric=constraint.metric,
                value=value,
                threshold=constraint.threshold,
                direction=constraint.direction,
                details="Constraint evaluated from primary metrics.",
            )
        )
    return checks


def _run_robustness_checks(task: TaskSpec, workspace: Path, config_path: Path, exp_dir: Path, skip_if_complete: bool) -> tuple[list[ScientificCheckResult], list[str]]:
    checks: list[ScientificCheckResult] = []
    artifact_paths: list[str] = []
    for check in task.robustness_checks:
        if not check.eval_command:
            checks.append(
                ScientificCheckResult(
                    name=check.name,
                    kind="robustness",
                    status="pending",
                    details="Robustness check declared but no eval_command was provided.",
                )
            )
            continue

        output_file = check.output_file or f"robustness_{check.name}.json"
        output_path = exp_dir / output_file
        log_path = exp_dir / f"robustness_{check.name}.log"
        if skip_if_complete and output_path.exists():
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            artifact_paths.extend([str(output_path), str(log_path)])
            status = payload.get("status", "passed")
            metrics = payload.get("metrics", payload if isinstance(payload, dict) else {})
            details = payload.get("details", "Robustness evaluation completed.") if isinstance(payload, dict) else "Robustness evaluation completed."
            checks.append(
                ScientificCheckResult(
                    name=check.name,
                    kind="robustness",
                    status=status if status in {"passed", "failed", "pending", "missing", "error"} else "passed",
                    details=details,
                    metrics=metrics if isinstance(metrics, dict) else {},
                    artifact_path=str(output_path),
                )
            )
            continue

        command = _format_command(check.eval_command, config_path, exp_dir, check_name=check.name, output_path=output_path)
        proc = _run_command(command, cwd=workspace, log_path=log_path)
        artifact_paths.append(str(log_path))
        if proc.returncode != 0:
            checks.append(
                ScientificCheckResult(
                    name=check.name,
                    kind="robustness",
                    status="error",
                    details=f"Robustness eval command failed with exit code {proc.returncode}.",
                    artifact_path=str(log_path),
                )
            )
            continue
        if not output_path.exists():
            checks.append(
                ScientificCheckResult(
                    name=check.name,
                    kind="robustness",
                    status="missing",
                    details="Robustness eval finished but did not produce the declared output file.",
                    artifact_path=str(log_path),
                )
            )
            continue

        payload = json.loads(output_path.read_text(encoding="utf-8"))
        artifact_paths.append(str(output_path))
        status = payload.get("status", "passed")
        metrics = payload.get("metrics", payload if isinstance(payload, dict) else {})
        details = payload.get("details", "Robustness evaluation completed.") if isinstance(payload, dict) else "Robustness evaluation completed."
        checks.append(
            ScientificCheckResult(
                name=check.name,
                kind="robustness",
                status=status if status in {"passed", "failed", "pending", "missing", "error"} else "passed",
                details=details,
                metrics=metrics if isinstance(metrics, dict) else {},
                artifact_path=str(output_path),
            )
        )
    return checks, artifact_paths


def _artifact_status(metrics_path: Path, scientific_checks: list[ScientificCheckResult], task: TaskSpec, metrics: dict | None = None) -> ArtifactStatus:
    metrics_present = metrics_path.exists()
    metrics = metrics or {}
    robustness_checks = [check for check in scientific_checks if check.kind == "robustness"]
    scientific_checks_complete = metrics_present and all(check.status not in {"missing", "error"} for check in scientific_checks)
    robustness_complete = (not task.robustness_checks) or all(check.status not in {"pending", "missing", "error"} for check in robustness_checks)
    required_metric = task.reporting.sort_by if task.reporting.sort_by and task.reporting.sort_by != "score" else (task.metrics.primary[0] if task.metrics.primary else None)
    required_metric_present = True if required_metric is None else (required_metric in metrics)
    artifact_valid = metrics_present and required_metric_present and scientific_checks_complete and robustness_complete
    return ArtifactStatus(
        metrics_present=metrics_present,
        scientific_checks_complete=scientific_checks_complete,
        robustness_complete=robustness_complete,
        artifact_valid=artifact_valid,
    )


def execute_plan(task: TaskSpec, plan: RoundPlan, run_root: Path, resume: bool = True) -> list[ExperimentResult]:
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
        provenance_path = exp_dir / "provenance.json"

        train_cmd = _format_command(task.commands.train, config_path, exp_dir)
        eval_cmd = _format_command(task.commands.eval, config_path, exp_dir)

        resumed = False
        train_rerun = False
        eval_rerun = False
        robustness_only = False
        status = "ok"
        error = None
        artifact_paths = [str(config_path)]

        prior_provenance = None
        if provenance_path.exists():
            try:
                prior_provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
            except Exception:
                prior_provenance = None

        can_resume_metrics = resume and metrics_path.exists()
        if can_resume_metrics:
            resumed = True
            robustness_only = bool(task.robustness_checks)
        else:
            train_proc = _run_command(train_cmd, cwd=workspace, log_path=train_log)
            artifact_paths.append(str(train_log))
            train_rerun = True
            if train_proc.returncode != 0:
                status = "failed"
                error = f"train failed with exit code {train_proc.returncode}"

            if status == "ok":
                eval_proc = _run_command(eval_cmd, cwd=workspace, log_path=eval_log)
                artifact_paths.append(str(eval_log))
                eval_rerun = True
                if eval_proc.returncode != 0:
                    status = "failed"
                    error = f"eval failed with exit code {eval_proc.returncode}"

        metrics = {}
        if metrics_path.exists():
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            artifact_paths.append(str(metrics_path))

        scientific_checks = _evaluate_constraints(task, metrics)
        if status == "ok":
            robustness_checks, robustness_artifacts = _run_robustness_checks(
                task,
                workspace=workspace,
                config_path=config_path,
                exp_dir=exp_dir,
                skip_if_complete=resumed and not robustness_only,
            )
            scientific_checks.extend(robustness_checks)
            artifact_paths.extend(robustness_artifacts)
        elif task.robustness_checks:
            for check in task.robustness_checks:
                scientific_checks.append(
                    ScientificCheckResult(
                        name=check.name,
                        kind="robustness",
                        status="pending",
                        details="Skipped because the main experiment did not finish successfully.",
                    )
                )

        artifact_status = _artifact_status(metrics_path, scientific_checks, task, metrics)
        if resumed and not artifact_status.artifact_valid and not train_rerun and not eval_rerun:
            train_proc = _run_command(train_cmd, cwd=workspace, log_path=train_log)
            artifact_paths.append(str(train_log))
            train_rerun = True
            if train_proc.returncode != 0:
                status = "failed"
                error = f"train failed with exit code {train_proc.returncode}"
            else:
                eval_proc = _run_command(eval_cmd, cwd=workspace, log_path=eval_log)
                artifact_paths.append(str(eval_log))
                eval_rerun = True
                if eval_proc.returncode != 0:
                    status = "failed"
                    error = f"eval failed with exit code {eval_proc.returncode}"
                else:
                    metrics = json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.exists() else {}
                    scientific_checks = _evaluate_constraints(task, metrics)
                    robustness_checks, robustness_artifacts = _run_robustness_checks(
                        task,
                        workspace=workspace,
                        config_path=config_path,
                        exp_dir=exp_dir,
                        skip_if_complete=False,
                    )
                    scientific_checks.extend(robustness_checks)
                    artifact_paths.extend(robustness_artifacts)
                    artifact_status = _artifact_status(metrics_path, scientific_checks, task, metrics)
                    resumed = False
                    robustness_only = False

        provenance = ProvenanceRecord(
            task_name=task.name,
            branch_id=exp.branch_id,
            round_index=plan.round_index,
            config_path=str(config_path),
            train_command=train_cmd,
            eval_command=eval_cmd,
            resumed=resumed,
            metrics_path=str(metrics_path) if metrics_path.exists() else None,
            artifact_paths=artifact_paths,
        )
        canonical_branch_config = {k: v for k, v in exp.config.items() if k not in {'seed', 'evaluation_regime', 'regime', 'eval.regime', 'data.regime'}}
        provenance_payload = provenance.model_dump()
        provenance_payload.update(
            {
                "timestamp_utc": _utc_now(),
                "config_hash": _hash_payload(exp.config),
                "branch_hash": _hash_payload({"branch_id": exp.branch_id, "config": canonical_branch_config}),
                "train_rerun": train_rerun,
                "eval_rerun": eval_rerun,
                "robustness_only": robustness_only,
                "prior_provenance_present": prior_provenance is not None,
            }
        )
        provenance_path.write_text(json.dumps(provenance_payload, indent=2), encoding="utf-8")
        if str(provenance_path) not in artifact_paths:
            artifact_paths.append(str(provenance_path))
            provenance.artifact_paths = artifact_paths

        results.append(
            ExperimentResult(
                experiment_id=exp.id,
                round_index=plan.round_index,
                status=status,
                metrics=metrics,
                config=exp.config,
                run_dir=str(exp_dir),
                scientific_checks=scientific_checks,
                branch_id=exp.branch_id,
                provenance=provenance,
                artifact_status=artifact_status,
                error=error,
            )
        )

    return results
