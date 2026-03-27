from __future__ import annotations

from .evidence import aggregate_branch_evidence, claim_taxonomy_from_cards
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


def _scientific_check_summary(results: list[ExperimentResult]) -> dict[str, int]:
    counts = {"passed": 0, "failed": 0, "pending": 0, "missing": 0, "error": 0}
    for result in results:
        for check in result.scientific_checks:
            counts[check.status] = counts.get(check.status, 0) + 1
    return counts


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
    counts = _scientific_check_summary(results)
    if counts["failed"] > 0 or counts["error"] > 0:
        return "needs-validation"
    if task.robustness_checks or task.constraints:
        if improvement > 0.01 and positive_rounds >= 2 and len(completed) >= 3 and counts["pending"] == 0 and counts["missing"] == 0:
            return "supported"
        if improvement > 0:
            return "needs-validation"
        return "uncertain"
    if improvement > 0.01 and positive_rounds >= 2:
        return "supported"
    if improvement > 0:
        return "observed"
    return "uncertain"


def _targeted_validation_hint(task: TaskSpec, best_card: dict | None) -> str | None:
    if best_card is None:
        return None
    coverage_guidance = best_card.get("coverage_guidance") or {}
    missing_seeds = coverage_guidance.get("target_missing_seeds") or best_card.get("missing_seeds") or []
    missing_regimes = coverage_guidance.get("target_missing_regimes") or best_card.get("missing_regimes") or []
    fixed_axes = coverage_guidance.get("recommended_fixed_axes") or {}
    observed_seeds = fixed_axes.get("seed") or best_card.get("seeds") or task.seeds or []
    observed_regimes = fixed_axes.get("evaluation_regime") or best_card.get("regimes") or [regime.name for regime in task.evaluation_regimes] or []

    if missing_seeds:
        regime_hint = ""
        if observed_regimes:
            regime_hint = f" while keeping the evaluation regime fixed to one of: {', '.join(observed_regimes)}"
        return f"Target the missing seeds next: {', '.join(str(seed) for seed in missing_seeds)}{regime_hint}."
    if missing_regimes:
        seed_hint = ""
        if observed_seeds:
            seed_hint = f" while keeping the seed fixed to one of: {', '.join(str(seed) for seed in observed_seeds)}"
        return f"Target the missing regimes next: {', '.join(missing_regimes)}{seed_hint}."
    return None


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
    check_counts = _scientific_check_summary(results)
    branch_cards = aggregate_branch_evidence(task, results)
    best_card = branch_cards[0] if branch_cards else None
    taxonomy = claim_taxonomy_from_cards(branch_cards)

    rationale_parts = [f"{best.experiment_id} currently performs best on `{metric_name}`."]
    if best_card is not None:
        rationale_parts.append(
            f"Aggregated branch evidence currently favors `{best_card['branch_label']}` with mean `{metric_name}={best_card['mean']:.6f}`, std `{best_card['std']:.6f}`, and taxonomy `{taxonomy}` over {best_card['count']} run(s)."
        )
        if best_card.get("evidence_gaps"):
            rationale_parts.append(f"Open evidence gaps for the leading branch: {', '.join(best_card['evidence_gaps'])}.")
        targeted_hint = _targeted_validation_hint(task, best_card)
        if targeted_hint is not None:
            rationale_parts.append(targeted_hint)
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
    rationale_parts.append(f"Current claim taxonomy is `{taxonomy}`.")
    rationale_parts.append(f"Historical positive rounds: {evidence['positive_rounds']}; non-improving rounds: {evidence['non_improving_rounds']}.")
    rationale_parts.append(
        f"Scientific check counts: passed={check_counts['passed']}, failed={check_counts['failed']}, pending/missing/error={check_counts['pending'] + check_counts['missing'] + check_counts['error']}."
    )
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

    if taxonomy == "observed":
        actions.append("This branch has only been observed locally; add another seed or regime before treating it as stable.")
        next_action_type = "validate"
    elif taxonomy == "promising":
        actions.append("This branch looks promising, but pending checks block a stronger claim; finish the missing evidence first.")
        next_action_type = "validate"
    elif taxonomy == "unsupported":
        actions.append("The current best-looking branch is unsupported under aggregated evidence; debug failed checks or abandon the branch.")
        next_action_type = "stop" if check_counts["failed"] > 0 else "validate"

    if best_card is not None and "partial-bundle" in best_card.get("evidence_gaps", []):
        actions.append("Complete the missing bundle members for the leading branch before comparing it against new branches.")
        next_action_type = "validate"
    if best_card is not None and "replication" in best_card.get("evidence_gaps", []):
        actions.append("The leading branch still lacks replication; add another evidence member before escalating any claim.")
        next_action_type = "validate"

    if best_card is not None and best_card["seed_count"] < max(1, len(task.seeds)):
        missing_seed_text = f" Missing seeds: {', '.join(str(seed) for seed in best_card.get('missing_seeds', []))}." if best_card.get("missing_seeds") else ""
        fixed_regime_text = f" Keep the evaluation regime fixed to one of: {', '.join(best_card.get('regimes', []))}." if best_card.get("regimes") else ""
        actions.append("Increase seed coverage for the leading branch so the evidence card is not dominated by single-seed luck." + missing_seed_text + fixed_regime_text)
        next_action_type = "validate"
    if task.evaluation_regimes and best_card is not None and best_card["regime_count"] < len(task.evaluation_regimes):
        missing_regime_text = f" Remaining regimes: {', '.join(best_card.get('missing_regimes', []))}." if best_card.get("missing_regimes") else ""
        fixed_seed_text = f" Keep the seed fixed to one of: {', '.join(str(seed) for seed in best_card.get('seeds', []))}." if best_card.get("seeds") else ""
        actions.append("Evaluate the leading branch across the remaining named regimes before another exploit step." + missing_regime_text + fixed_seed_text)
        next_action_type = "validate"

    if check_counts["failed"] > 0 or check_counts["error"] > 0:
        actions.append("At least one scientific check failed or errored; debug those checks before expanding the search.")
        next_action_type = "validate"
    elif check_counts["pending"] > 0 or check_counts["missing"] > 0:
        actions.append("Complete the pending scientific checks before treating the current winner as a credible result.")
        next_action_type = "validate"

    if task.constraints:
        executable_constraints = [c for c in task.constraints if c.metric is not None]
        if executable_constraints:
            actions.append(
                "Promote only configurations that satisfy the executable constraints: "
                + ", ".join(c.name for c in executable_constraints[:3])
                + "."
            )
        else:
            actions.append("Convert the named constraints into metric-threshold checks so they can gate claims automatically.")

    if task.robustness_checks:
        executable_checks = [check.name for check in task.robustness_checks if check.eval_command]
        if executable_checks:
            actions.append(f"Run the listed robustness checks on the best configuration: {', '.join(executable_checks[:2])}.")
        else:
            actions.append("Turn the named robustness checks into executable eval hooks before another exploit round.")
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
