from __future__ import annotations

from collections import Counter
from pathlib import Path

from .evidence import aggregate_branch_evidence, branch_label as evidence_branch_label, claim_taxonomy_from_cards
from .schemas import ExperimentResult, TaskSpec


def _format_config_changes(config: dict, baseline: dict) -> str:
    changes = []
    for key, value in config.items():
        if baseline.get(key) != value:
            changes.append(f"{key}={value}")
    return ", ".join(changes) if changes else "baseline"


def _branch_label(config: dict, baseline: dict) -> str:
    return evidence_branch_label(config, baseline)


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


def _round_improvement(results: list[ExperimentResult], metric_name: str, lower_is_better: bool) -> float | None:
    completed = [r for r in results if r.status == "ok" and metric_name in r.metrics]
    anchor = _anchor_result(results)
    if not completed or anchor is None:
        return None
    best = sorted(completed, key=lambda r: _metric_value(r, metric_name, lower_is_better), reverse=not lower_is_better)[0]
    return anchor.metrics[metric_name] - best.metrics[metric_name] if lower_is_better else best.metrics[metric_name] - anchor.metrics[metric_name]


def _historical_evidence(task: TaskSpec, historical_results: list[ExperimentResult], current_results: list[ExperimentResult]) -> dict:
    metric_name = task.reporting.sort_by or (task.metrics.primary[0] if task.metrics.primary else "score")
    lower_is_better = task.reporting.lower_is_better
    baseline = task.planner.baseline
    all_rounds: dict[int, list[ExperimentResult]] = {}
    branch_counter: Counter[str] = Counter()
    for result in historical_results + current_results:
        all_rounds.setdefault(result.round_index, []).append(result)
        if result.status == "ok" and metric_name in result.metrics:
            branch_counter[_branch_label(result.config, baseline)] += 1

    positive_rounds = 0
    non_improving_rounds = 0
    trajectory = []
    claim_trajectory = []
    for round_index in sorted(all_rounds):
        round_results = all_rounds[round_index]
        improvement = _round_improvement(round_results, metric_name, lower_is_better)
        if improvement is not None and improvement > 1e-6:
            positive_rounds += 1
        elif improvement is not None:
            non_improving_rounds += 1
        best_round = _best_result(round_results, metric_name, lower_is_better)
        if best_round is not None:
            trajectory.append((round_index, best_round.metrics[metric_name], _branch_label(best_round.config, baseline)))
            cards = aggregate_branch_evidence(task, round_results)
            claim_trajectory.append((round_index, claim_taxonomy_from_cards(cards)))

    return {
        "positive_rounds": positive_rounds,
        "non_improving_rounds": non_improving_rounds,
        "trajectory": trajectory,
        "claim_trajectory": claim_trajectory,
        "branch_counter": dict(branch_counter),
    }


def _check_counts(results: list[ExperimentResult]) -> dict[str, int]:
    counts = {"passed": 0, "failed": 0, "pending": 0, "missing": 0, "error": 0}
    for result in results:
        for check in result.scientific_checks:
            counts[check.status] = counts.get(check.status, 0) + 1
    return counts


def _required_constraints_satisfied(result: ExperimentResult, task: TaskSpec) -> bool:
    required_names = {constraint.name for constraint in task.constraints if constraint.required and constraint.metric is not None}
    if not required_names:
        return True
    status_by_name = {check.name: check.status for check in result.scientific_checks if check.kind == "constraint"}
    return all(status_by_name.get(name) == "passed" for name in required_names)


def _claim_strength(task: TaskSpec, results: list[ExperimentResult], historical_results: list[ExperimentResult], metric_name: str, lower_is_better: bool) -> str:
    completed = [r for r in results if r.status == "ok" and metric_name in r.metrics]
    anchor = _anchor_result(results)
    if not completed or anchor is None:
        return "uncertain"
    improvement = _round_improvement(results, metric_name, lower_is_better) or 0.0
    evidence = _historical_evidence(task, historical_results, results)
    positive_rounds = evidence["positive_rounds"]
    failed_required_constraints = any(not _required_constraints_satisfied(result, task) for result in completed)
    any_robustness_failed = any(check.kind == "robustness" and check.status in {"failed", "error"} for result in completed for check in result.scientific_checks)
    if failed_required_constraints or any_robustness_failed:
        return "needs-validation"
    if task.robustness_checks or task.constraints:
        if improvement > 0.01 and positive_rounds >= 2 and len(completed) >= 3:
            return "supported"
        if improvement > 0:
            return "needs-validation"
        return "uncertain"
    if improvement > 0.01 and positive_rounds >= 2:
        return "supported"
    if improvement > 0:
        return "observed"
    return "uncertain"


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
    evidence = _historical_evidence(task, historical_results, results)
    claim_strength = _claim_strength(task, results, historical_results, metric_name, lower_is_better)
    check_counts = _check_counts(results)
    branch_cards = aggregate_branch_evidence(task, results)
    best_card = branch_cards[0] if branch_cards else None

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
        f"- Constraints: {', '.join(constraint.name for constraint in task.constraints) if task.constraints else 'none'}",
        f"- Robustness checks: {', '.join(check.name for check in task.robustness_checks) if task.robustness_checks else 'none'}",
        f"- Round mode: {round_mode or 'unspecified'}",
        f"- Claim strength: {claim_strength}",
        f"- Claim taxonomy: {claim_taxonomy_from_cards(branch_cards)}",
        f"- Positive rounds so far: {evidence['positive_rounds']}",
        f"- Non-improving rounds so far: {evidence['non_improving_rounds']}",
        f"- Scientific checks passed: {check_counts['passed']}",
        f"- Scientific checks failed: {check_counts['failed']}",
        f"- Scientific checks pending/missing/error: {check_counts['pending'] + check_counts['missing'] + check_counts['error']}",
        "",
        "## Results",
        "",
        "| Rank | Exp ID | Changes vs baseline | Status | Primary Metric | Delta vs baseline | Delta vs anchor | Secondary Metrics | Scientific checks | Notes |",
        "|---:|---|---|---|---:|---:|---:|---|---|---|",
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
        scientific_check_text = ", ".join(f"{check.name}:{check.status}" for check in result.scientific_checks) if result.scientific_checks else "-"
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
            f"| {rank_text} | {result.experiment_id} | {changes} | {result.status} | {primary_value} | {delta_baseline_text} | {delta_anchor_text} | {secondary_text} | {scientific_check_text} | {note} |"
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

    lines.extend(["", "## Aggregated branch evidence"])
    if best_card is not None:
        lines.append(
            f"Best branch by aggregated evidence: `{best_card['branch_label']}` with mean `{metric_name}={best_card['mean']:.6f}` and std `{best_card['std']:.6f}` across {best_card['count']} run(s)."
        )
    if branch_cards:
        lines.append("")
        lines.append("| Branch | Mean | Std | Best | Runs | Seeds | Regimes | Constraint pass rate | Robustness pass rate | Evidence status |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---|")
        for card in branch_cards:
            constraint_rate = "-" if card["constraint_pass_rate"] is None else f"{card['constraint_pass_rate']:.2f}"
            robustness_rate = "-" if card["robustness_pass_rate"] is None else f"{card['robustness_pass_rate']:.2f}"
            lines.append(
                f"| {card['branch_label']} | {card['mean']:.6f} | {card['std']:.6f} | {float(card['best']):.6f} | {card['count']} | {card['seed_count']} | {card['regime_count']} | {constraint_rate} | {robustness_rate} | {card['evidence_status']} |"
            )
    else:
        lines.append("No aggregated branch evidence is available yet.")

    lines.extend(["", "## Best So Far"])
    if best_so_far is not None:
        lines.append(
            f"Across all completed rounds, the best run so far is `{best_so_far.experiment_id}` from round `{best_so_far.round_index}` with `{metric_name}={best_so_far.metrics.get(metric_name)}`."
        )
        lines.append(f"Best-so-far config snapshot: `{_format_config_changes(best_so_far.config, baseline_config)}`.")
    else:
        lines.append("No best-so-far record is available yet.")

    lines.extend(["", "## Claim assessment"])
    lines.append(f"- Observed: the current round produced measurable outcomes for `{metric_name}` across {len(completed)} completed run(s).")
    lines.append(f"- Taxonomy: the best current branch is classified as `{claim_taxonomy_from_cards(branch_cards)}` under aggregated evidence.")
    if claim_strength == "supported":
        lines.append("- Supported: the current improvement has now repeated strongly enough across rounds to be treated as a working result under the present checks.")
    elif claim_strength == "observed":
        lines.append("- Supported: a positive effect was observed, but the evidence is still narrow and mostly local to this round.")
    elif claim_strength == "needs-validation":
        lines.append("- Supported: there is a promising effect, but scientific checks still contain failed, missing, or incomplete evidence, so the result needs explicit validation.")
    else:
        lines.append("- Supported: no strong supported claim should be made yet.")
    lines.append("- Uncertain: generalization beyond the tested settings remains unresolved unless additional validation is run.")
    if evidence["positive_rounds"] >= 2:
        lines.append("- Historical evidence: at least two rounds have shown positive movement relative to their anchors.")
    else:
        lines.append("- Historical evidence: repeated positive evidence has not yet accumulated across rounds.")
    if task.robustness_checks or task.evaluation_regimes or task.constraints:
        lines.append("- Next validation needed: run or complete the named scientific checks before treating the improvement as robust.")
    else:
        lines.append("- Next validation needed: add at least one harder or shifted evaluation before making broader claims.")

    lines.extend(["", "## Claim trajectory"])
    if evidence["claim_trajectory"]:
        for round_idx, label in evidence["claim_trajectory"]:
            lines.append(f"- round {round_idx}: {label}")
    else:
        lines.append("- No claim trajectory is available yet.")

    lines.extend(["", "## Branch evidence"])
    if evidence["branch_counter"]:
        for branch, count in sorted(evidence["branch_counter"].items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"- {branch}: seen in {count} successful run(s)")
    else:
        lines.append("- No successful branch evidence is available yet.")

    lines.extend(["", "## Ranking"])
    if ranked:
        for idx, result in enumerate(ranked, start=1):
            lines.append(f"{idx}. `{result.experiment_id}` — `{metric_name}={result.metrics.get(metric_name)}` — {_format_config_changes(result.config, baseline_config)}")
    else:
        lines.append("No successful runs to rank.")

    lines.extend(["", "## Scientific checks"])
    if task.constraints:
        for constraint in task.constraints:
            if constraint.metric is not None and constraint.threshold is not None:
                lines.append(
                    f"- Constraint `{constraint.name}`: metric `{constraint.metric}` should be {constraint.direction.replace('_', ' ')} `{constraint.threshold}`."
                )
            else:
                lines.append(f"- Constraint `{constraint.name}`: named only, not yet executable.")
    else:
        lines.append("- No named scientific constraints were provided in the task.")
    if task.robustness_checks:
        for check in task.robustness_checks:
            if check.eval_command:
                lines.append(f"- Robustness `{check.name}`: executable hook configured.")
            else:
                lines.append(f"- Robustness `{check.name}`: reminder only; no eval command configured yet.")
    else:
        lines.append("- No explicit robustness hooks were provided in the task.")

    lines.extend(["", "## Per-experiment scientific check details"])
    detail_lines = 0
    for result in results:
        if not result.scientific_checks:
            continue
        lines.append(f"- `{result.experiment_id}`")
        detail_lines += 1
        for check in result.scientific_checks:
            summary = f"  - {check.kind}:{check.name} -> {check.status}"
            if check.metric is not None:
                summary += f" ({check.metric}={check.value}, threshold={check.threshold})"
            elif check.metrics:
                summary += f" (metrics={check.metrics})"
            if check.details:
                summary += f" — {check.details}"
            lines.append(summary)
    if detail_lines == 0:
        lines.append("- No per-experiment scientific check details are available yet.")

    lines.extend(["", "## Observations"])
    if round_mode is not None:
        lines.append(f"- This round was planned in `{round_mode}` mode.")
    if anchor_result is not None:
        lines.append(f"- The round anchor is `{anchor_result.experiment_id}` with changes: {_format_config_changes(anchor_result.config, baseline_config)}.")
    if best is not None:
        lines.append(f"- The current best run is `{best.experiment_id}` with changes: {_format_config_changes(best.config, baseline_config)}.")
    if best_card is not None:
        lines.append(
            f"- Aggregated evidence currently favors branch `{best_card['branch_label']}` with status `{best_card['evidence_status']}` over {best_card['count']} run(s)."
        )
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
    if check_counts["failed"] > 0 or check_counts["error"] > 0:
        lines.append("- At least one scientific check failed or errored; do not overclaim the current best metric.")
    elif check_counts["pending"] > 0 or check_counts["missing"] > 0:
        lines.append("- Some scientific checks are still pending or missing; evidence quality is incomplete.")

    return "\n".join(lines) + "\n"


def save_summary(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
