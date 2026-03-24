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


def build_suggestions(task: TaskSpec, results: list[ExperimentResult]) -> Suggestion:
    metric_name = _metric_name(task)
    lower_is_better = task.reporting.lower_is_better
    baseline = task.planner.baseline
    completed = _sorted_completed(task, results)

    if not completed:
        return Suggestion(
            title="No reliable next step yet",
            rationale="The current round did not produce valid metrics for comparison.",
            actions=[
                "Fix failed runs before planning another round.",
                "Verify metric output paths and command templates.",
            ],
        )

    best = completed[0]
    anchor = next((r for r in results if r.status == "ok" and r.experiment_id == "exp_001" and metric_name in r.metrics), None)
    changed = _changed_keys(best.config, baseline)
    primary_change = changed[0] if changed else "the current baseline configuration"

    rationale_parts = [f"{best.experiment_id} currently performs best on `{metric_name}`."]
    actions = [f"Repeat {best.experiment_id} with another seed to check stability."]

    if anchor is not None and best.experiment_id != anchor.experiment_id:
        best_val = best.metrics[metric_name]
        anchor_val = anchor.metrics[metric_name]
        gain = anchor_val - best_val if lower_is_better else best_val - anchor_val
        rationale_parts.append(
            f"Relative to the round anchor `{anchor.experiment_id}`, the improvement is `{gain:.6f}`."
        )
        actions.append(f"Validate whether the gain over anchor survives a slightly harder evaluation setting.")
    else:
        rationale_parts.append("The current anchor is still the best candidate, so more exploratory evidence is needed.")
        actions.append("Try one additional nearby exploration before committing to this branch.")

    ablations = [r for r in results if r.status == "ok" and r.experiment_id != "exp_001" and "baseline" in _changed_keys(best.config, {})]
    if changed:
        actions.append(f"Run a local ablation around `{primary_change}` to isolate its effect.")
    else:
        actions.append("Try one targeted single-parameter change around the baseline.")

    if len(changed) >= 2:
        actions.append("Test whether the combined changes still help when applied one at a time.")

    if len(completed) >= 3:
        second = completed[1]
        second_val = second.metrics[metric_name]
        best_val = best.metrics[metric_name]
        gap = second_val - best_val if lower_is_better else best_val - second_val
        rationale_parts.append(f"The gap between the best and second-best run is `{gap:.6f}`.")
        if abs(gap) < 1e-8:
            actions.append("Because the top runs are tied, prefer the simpler configuration or run another discriminating evaluation.")

    actions.append("Add one slightly harder evaluation setting before making broader claims.")

    return Suggestion(
        title="Suggested next round",
        rationale=" ".join(rationale_parts),
        actions=actions,
    )


def render_suggestions(suggestion: Suggestion, round_index: int) -> str:
    lines = [
        f"# Suggestions After Round {round_index}",
        "",
        f"## {suggestion.title}",
        suggestion.rationale,
        "",
        "## Recommended next experiments",
    ]
    for idx, action in enumerate(suggestion.actions, start=1):
        lines.append(f"{idx}. {action}")
    return "\n".join(lines) + "\n"
