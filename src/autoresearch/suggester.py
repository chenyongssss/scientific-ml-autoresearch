from __future__ import annotations

from .schemas import ExperimentResult, Suggestion, TaskSpec


def _changed_keys(config: dict, baseline: dict) -> list[str]:
    return [key for key, value in config.items() if baseline.get(key) != value]


def _metric_name(task: TaskSpec) -> str:
    return task.reporting.sort_by or (task.metrics.primary[0] if task.metrics.primary else "score")


def _sorted_completed(task: TaskSpec, results: list[ExperimentResult]) -> list[ExperimentResult]:
    metric_name = _metric_name(task)
    lower_is_better = task.reporting.lower_is_better
    completed = [r for r in results if r.status == "ok" and metric_name in r.metrics]
    return sorted(completed, key=lambda r: r.metrics[metric_name], reverse=not lower_is_better)


def _anchor_result(results: list[ExperimentResult], metric_name: str) -> ExperimentResult | None:
    return next((r for r in results if r.status == "ok" and r.experiment_id == "exp_001" and metric_name in r.metrics), None)


def _round_improvement(task: TaskSpec, results: list[ExperimentResult]) -> float | None:
    metric_name = _metric_name(task)
    lower_is_better = task.reporting.lower_is_better
    completed = _sorted_completed(task, results)
    anchor = _anchor_result(results, metric_name)
    if not completed or anchor is None:
        return None
    best = completed[0]
    return anchor.metrics[metric_name] - best.metrics[metric_name] if lower_is_better else best.metrics[metric_name] - anchor.metrics[metric_name]


def _historical_evidence(task: TaskSpec, historical_results: list[ExperimentResult], current_results: list[ExperimentResult]) -> dict:
    metric_name = _metric_name(task)
    lower_is_better = task.reporting.lower_is_better
    grouped: dict[int, list[ExperimentResult]] = {}
    for result in historical_results + current_results:
        grouped.setdefault(result.round_index, []).append(result)
    positive_rounds = 0
    non_improving_rounds = 0
    for round_index, round_results in grouped.items():
        completed = [r for r in round_results if r.status == "ok" and metric_name in r.metrics]
        anchor = _anchor_result(round_results, metric_name)
        if not completed or anchor is None:
            continue
        best = sorted(completed, key=lambda r: r.metrics[metric_name], reverse=not lower_is_better)[0]
        improvement = anchor.metrics[metric_name] - best.metrics[metric_name] if lower_is_better else best.metrics[metric_name] - anchor.metrics[metric_name]
        if improvement > 1e-6:
            positive_rounds += 1
        else:
            non_improving_rounds += 1
    return {"positive_rounds": positive_rounds, "non_improving_rounds": non_improving_rounds}


def _claim_strength(task: TaskSpec, results: list[ExperimentResult], historical_results: list[ExperimentResult]) -> str:
    metric_name = _metric_name(task)
    lower_is_better = task.reporting.lower_is_better
    completed = _sorted_completed(task, results)
    anchor = _anchor_result(results, metric_name)
    if not completed or anchor is None:
        return "uncertain"
    best = completed[0]
    improvement = anchor.metrics[metric_name] - best.metrics[metric_name] if lower_is_better else best.metrics[metric_name] - anchor.metrics[metric_name]
    evidence = _historical_evidence(task, historical_results, results)
    positive_rounds = evidence["positive_rounds"]
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


def build_suggestions(task: TaskSpec, results: list[ExperimentResult], historical_results: list[ExperimentResult] | None = None) -> Suggestion:
    historical_results = historical_results or []
    metric_name = _metric_name(task)
    lower_is_better = task.reporting.lower_is_better
    baseline = task.planner.baseline
    completed = _sorted_completed(task, results)

    if not completed:
        return Suggestion(
            title="No reliable next step yet",
            rationale="The current round did not produce valid metrics for comparison.",
            next_action_type="stop",
            actions=[
                "Fix failed runs before planning another round.",
                "Verify metric output paths and command templates.",
            ],
        )

    best = completed[0]
    anchor = _anchor_result(results, metric_name)
    changed = _changed_keys(best.config, baseline)
    primary_change = changed[0] if changed else "the current baseline configuration"
    improvement = _round_improvement(task, results)
    claim_strength = _claim_strength(task, results, historical_results)
    evidence = _historical_evidence(task, historical_results, results)

    rationale_parts = [f"{best.experiment_id} currently performs best on `{metric_name}`."]
    actions = [f"Repeat {best.experiment_id} with another seed to check stability."]
    next_action_type = "validate"

    if anchor is not None and best.experiment_id != anchor.experiment_id:
        gain = anchor.metrics[metric_name] - best.metrics[metric_name] if lower_is_better else best.metrics[metric_name] - anchor.metrics[metric_name]
        rationale_parts.append(
            f"Relative to the round anchor `{anchor.experiment_id}`, the improvement is `{gain:.6f}`."
        )
        actions.append("Validate whether the gain over anchor survives a slightly harder evaluation setting.")
        if gain > 0.01:
            next_action_type = "exploit"
    else:
        rationale_parts.append("The current anchor is still the best candidate, so more exploratory evidence is needed.")
        actions.append("Try one additional nearby exploration before committing to this branch.")
        next_action_type = "explore"

    if changed:
        actions.append(f"Run a local ablation around `{primary_change}` to isolate its effect.")
        if len(changed) == 1 and next_action_type != "exploit":
            next_action_type = "ablate"
    else:
        actions.append("Try one targeted single-parameter change around the baseline.")
        next_action_type = "explore"

    if len(changed) >= 2:
        actions.append("Test whether the combined changes still help when applied one at a time.")
        if next_action_type != "exploit":
            next_action_type = "ablate"

    if len(completed) >= 2:
        second = completed[1]
        gap = second.metrics[metric_name] - best.metrics[metric_name] if lower_is_better else best.metrics[metric_name] - second.metrics[metric_name]
        rationale_parts.append(f"The gap between the best and second-best run is `{gap:.6f}`.")
        if abs(gap) < 1e-8:
            actions.append("Because the top runs are tied, prefer the simpler configuration or run another discriminating evaluation.")
            next_action_type = "validate"

    rationale_parts.append(f"Current claim strength is `{claim_strength}`.")
    rationale_parts.append(f"Historical positive rounds: {evidence['positive_rounds']}; non-improving rounds: {evidence['non_improving_rounds']}.")
    if claim_strength == "needs-validation":
        actions.append("Do not treat this as a robust conclusion yet; prioritize explicit validation next.")
        next_action_type = "validate"
    elif claim_strength == "uncertain":
        actions.append("Treat the current result as exploratory only; avoid making strong claims.")
        next_action_type = "stop" if improvement is not None and improvement <= 1e-6 else "explore"
    elif claim_strength == "supported" and evidence["positive_rounds"] >= 2:
        actions.append("Historical evidence is accumulating; continue only with validation or targeted refinement, not broad exploration.")
        if next_action_type == "explore":
            next_action_type = "validate"

    if task.constraints:
        constraint_text = ", ".join(task.constraints[:3])
        actions.append(f"Check whether the current best configuration still respects the task constraints: {constraint_text}.")

    if task.robustness_checks:
        robustness_names = ", ".join(check.name for check in task.robustness_checks[:2])
        actions.append(f"Run the listed robustness checks on the best configuration: {robustness_names}.")
        if next_action_type == "exploit":
            next_action_type = "validate"

    if improvement is not None and improvement <= 1e-6:
        rationale_parts.append("This round did not produce a meaningful improvement over the anchor.")
        actions.append("Pause aggressive exploration and either stop here or switch to validation-only checks.")
        next_action_type = "stop"
    elif evidence["non_improving_rounds"] >= 2 and claim_strength != "supported":
        actions.append("Multiple rounds have failed to improve meaningfully; strongly consider stopping or narrowing to validation only.")
        next_action_type = "stop"

    if task.evaluation_regimes:
        regime_names = ", ".join(regime.name for regime in task.evaluation_regimes[:2])
        actions.append(f"Check the current best configuration on the named evaluation regimes: {regime_names}.")
    else:
        actions.append("Add one slightly harder evaluation setting before making broader claims.")

    return Suggestion(
        title="Suggested next round",
        rationale=" ".join(rationale_parts),
        next_action_type=next_action_type,
        actions=actions,
    )


def render_suggestions(suggestion: Suggestion, round_index: int) -> str:
    lines = [
        f"# Suggestions After Round {round_index}",
        "",
        f"## {suggestion.title}",
        suggestion.rationale,
        "",
        "## Recommended next action type",
        f"`{suggestion.next_action_type}`",
        "",
        "## Recommended next experiments",
    ]
    for idx, action in enumerate(suggestion.actions, start=1):
        lines.append(f"{idx}. {action}")
    return "\n".join(lines) + "\n"
