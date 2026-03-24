from __future__ import annotations

from pathlib import Path

from .schemas import ExperimentResult, TaskSpec


def _format_config_changes(config: dict, baseline: dict) -> str:
    changes = []
    for key, value in config.items():
        if baseline.get(key) != value:
            changes.append(f"{key}={value}")
    return ", ".join(changes) if changes else "baseline"


def _metric_value(result: ExperimentResult, metric_name: str, lower_is_better: bool):
    value = result.metrics.get(metric_name)
    if value is None:
        return float("inf") if lower_is_better else float("-inf")
    return value


def _anchor_result(results: list[ExperimentResult]) -> ExperimentResult | None:
    for result in results:
        if result.status == "ok" and result.experiment_id == "exp_001":
            return result
    return None


def _best_result(results: list[ExperimentResult], metric_name: str, lower_is_better: bool) -> ExperimentResult | None:
    completed = [r for r in results if r.status == "ok" and metric_name in r.metrics]
    if not completed:
        return None
    return sorted(completed, key=lambda r: _metric_value(r, metric_name, lower_is_better), reverse=not lower_is_better)[0]


def build_summary(
    task: TaskSpec,
    round_index: int,
    results: list[ExperimentResult],
    historical_results: list[ExperimentResult] | None = None,
    round_mode: str | None = None,
) -> str:
    metric_name = task.reporting.sort_by or (task.metrics.primary[0] if task.metrics.primary else "score")
    lower_is_better = task.reporting.lower_is_better
    baseline_config = task.planner.baseline
    historical_results = historical_results or []

    completed = [r for r in results if r.status == "ok"]
    failed = [r for r in results if r.status == "failed"]
    baseline_result = next((r for r in results if r.config == baseline_config and r.status == "ok"), None)
    anchor_result = _anchor_result(results)
    ranked = sorted(completed, key=lambda r: _metric_value(r, metric_name, lower_is_better), reverse=not lower_is_better)
    best = ranked[0] if ranked else None
    best_so_far = _best_result(historical_results + results, metric_name, lower_is_better)

    lines = [
        f"# Round {round_index} Summary",
        "",
        "## Task",
        task.name,
        "",
        "## Overview",
        f"- Round: {round_index}",
        f"- Experiments: {len(results)}",
        f"- Completed: {len(completed)}",
        f"- Failed: {len(failed)}",
        f"- Seeds configured: {task.seeds if task.seeds else 'none'}",
        f"- Evaluation regimes: {', '.join(regime.name for regime in task.evaluation_regimes) if task.evaluation_regimes else 'default'}",
        f"- Round mode: {round_mode or 'unspecified'}",
        "",
        "## Results",
        "",
        "| Rank | Exp ID | Changes vs baseline | Status | Primary Metric | Delta vs baseline | Delta vs anchor | Secondary Metrics | Notes |",
        "|---:|---|---|---|---:|---:|---:|---|---|",
    ]

    rank_lookup = {result.experiment_id: idx for idx, result in enumerate(ranked, start=1)}
    baseline_value = baseline_result.metrics.get(metric_name) if baseline_result is not None else None
    anchor_value = anchor_result.metrics.get(metric_name) if anchor_result is not None else None

    for result in results:
        primary_value = result.metrics.get(metric_name, "n/a")
        secondary_parts = []
        for key in task.metrics.secondary:
            if key in result.metrics:
                secondary_parts.append(f"{key}={result.metrics[key]}")
        secondary_text = ", ".join(secondary_parts) if secondary_parts else "-"
        note = result.error or ""
        changes = _format_config_changes(result.config, baseline_config)
        rank_text = str(rank_lookup.get(result.experiment_id, "-"))
        delta_baseline_text = "-"
        if baseline_value is not None and isinstance(primary_value, (int, float)):
            delta = baseline_value - primary_value if lower_is_better else primary_value - baseline_value
            delta_baseline_text = f"{delta:.6f}"
        delta_anchor_text = "-"
        if anchor_value is not None and isinstance(primary_value, (int, float)):
            delta = anchor_value - primary_value if lower_is_better else primary_value - anchor_value
            delta_anchor_text = f"{delta:.6f}"
        lines.append(
            f"| {rank_text} | {result.experiment_id} | {changes} | {result.status} | {primary_value} | {delta_baseline_text} | {delta_anchor_text} | {secondary_text} | {note} |"
        )

    lines.extend(["", "## Best Run"])
    if best is not None:
        lines.append(
            f"`{best.experiment_id}` achieved the best `{metric_name}` value in this round: `{best.metrics.get(metric_name)}`."
        )
        if baseline_result is not None and best.experiment_id != baseline_result.experiment_id:
            best_value = best.metrics.get(metric_name)
            if isinstance(best_value, (int, float)) and isinstance(baseline_value, (int, float)):
                delta = baseline_value - best_value if lower_is_better else best_value - baseline_value
                lines.append(f"Compared with baseline, the improvement on `{metric_name}` is `{delta:.6f}`.")
        if anchor_result is not None and best.experiment_id != anchor_result.experiment_id:
            best_value = best.metrics.get(metric_name)
            if isinstance(best_value, (int, float)) and isinstance(anchor_value, (int, float)):
                delta = anchor_value - best_value if lower_is_better else best_value - anchor_value
                lines.append(f"Compared with the round anchor, the improvement on `{metric_name}` is `{delta:.6f}`.")
        lines.append(f"Key config snapshot: `{_format_config_changes(best.config, baseline_config)}`.")
    else:
        lines.append("No successful runs were available for comparison.")

    lines.extend(["", "## Best So Far"])
    if best_so_far is not None:
        lines.append(
            f"Across all completed rounds, the best run so far is `{best_so_far.experiment_id}` from round `{best_so_far.round_index}` with `{metric_name}={best_so_far.metrics.get(metric_name)}`."
        )
        lines.append(f"Best-so-far config snapshot: `{_format_config_changes(best_so_far.config, baseline_config)}`.")
    else:
        lines.append("No best-so-far record is available yet.")

    lines.extend(["", "## Ranking"])
    if ranked:
        for idx, result in enumerate(ranked, start=1):
            lines.append(f"{idx}. `{result.experiment_id}` — `{metric_name}={result.metrics.get(metric_name)}` — {_format_config_changes(result.config, baseline_config)}")
    else:
        lines.append("No successful runs to rank.")

    lines.extend(["", "## Observations"])
    if round_mode is not None:
        lines.append(f"- This round was planned in `{round_mode}` mode.")
    if anchor_result is not None:
        lines.append(f"- The round anchor is `{anchor_result.experiment_id}` with changes: {_format_config_changes(anchor_result.config, baseline_config)}.")
    if best is not None:
        lines.append(f"- The current best run is `{best.experiment_id}` with changes: {_format_config_changes(best.config, baseline_config)}.")
    if best_so_far is not None and best is not None and best_so_far.experiment_id == best.experiment_id and best_so_far.round_index == best.round_index:
        lines.append("- This round produced the current best-so-far result.")
    if failed:
        lines.append(f"- {len(failed)} run(s) failed and should be checked before drawing conclusions.")
    else:
        lines.append("- No failed runs were observed in this round.")
    if len(completed) >= 2:
        lines.append("- At least two completed runs are available for local comparison.")
    if baseline_result is None:
        lines.append("- No successful baseline run was found, so relative improvement should be interpreted cautiously.")

    return "\n".join(lines) + "\n"


def save_summary(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
