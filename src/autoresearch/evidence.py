from __future__ import annotations

from collections import defaultdict
from math import sqrt
from typing import Any

from .schemas import ExperimentResult, TaskSpec


EVIDENCE_AXIS_KEYS = {"seed", "evaluation_regime", "regime", "eval.regime", "data.regime"}


def metric_name(task: TaskSpec) -> str:
    if task.reporting.sort_by and task.reporting.sort_by != "score":
        return task.reporting.sort_by
    if task.metrics.primary:
        return task.metrics.primary[0]
    return task.reporting.sort_by or "score"


def config_without_evidence_axes(config: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in config.items() if key not in EVIDENCE_AXIS_KEYS}


def evidence_axes(config: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in config.items() if key in EVIDENCE_AXIS_KEYS}


def branch_label(config: dict[str, Any], baseline: dict[str, Any]) -> str:
    changed = sorted(key for key, value in config.items() if baseline.get(key) != value)
    return "+".join(changed) if changed else "baseline"


def branch_key(config: dict[str, Any]) -> tuple:
    canonical = config_without_evidence_axes(config)
    return tuple(sorted(canonical.items()))


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _std(values: list[float]) -> float:
    if len(values) <= 1:
        return 0.0
    mu = _mean(values)
    return sqrt(sum((value - mu) ** 2 for value in values) / len(values))


def expected_seed_count(task: TaskSpec) -> int:
    return len(task.seeds)


def expected_regime_count(task: TaskSpec) -> int:
    return len(task.evaluation_regimes)


def aggregate_branch_evidence(task: TaskSpec, results: list[ExperimentResult]) -> list[dict[str, Any]]:
    name = metric_name(task)
    lower_is_better = task.reporting.lower_is_better
    baseline = task.planner.baseline
    grouped: dict[tuple, list[ExperimentResult]] = defaultdict(list)
    for result in results:
        if result.status != "ok" or name not in result.metrics:
            continue
        grouped[branch_key(result.config)].append(result)

    cards: list[dict[str, Any]] = []
    for key, group in grouped.items():
        metric_values = [float(result.metrics[name]) for result in group]
        best_result = sorted(group, key=lambda result: result.metrics[name], reverse=not lower_is_better)[0]
        seeds = sorted({result.config.get("seed") for result in group if result.config.get("seed") is not None})
        regimes = sorted({result.config.get("evaluation_regime") or result.config.get("regime") for result in group if (result.config.get("evaluation_regime") or result.config.get("regime")) is not None})
        total_constraints = 0
        passed_constraints = 0
        total_robustness = 0
        passed_robustness = 0
        pending_or_missing = 0
        failed_or_error = 0
        completion = []
        for result in group:
            member_state = {
                "experiment_id": result.experiment_id,
                "branch_id": result.branch_id,
                "axes": evidence_axes(result.config),
                "status": result.status,
                "artifact_valid": result.artifact_status.artifact_valid,
            }
            completion.append(member_state)
            for check in result.scientific_checks:
                if check.kind == "constraint":
                    total_constraints += 1
                    if check.status == "passed":
                        passed_constraints += 1
                if check.kind == "robustness":
                    total_robustness += 1
                    if check.status == "passed":
                        passed_robustness += 1
                if check.status in {"pending", "missing"}:
                    pending_or_missing += 1
                if check.status in {"failed", "error"}:
                    failed_or_error += 1

        completed_members = sum(1 for member in completion if member["status"] == "ok" and member["artifact_valid"])
        incomplete_members = len(completion) - completed_members

        if failed_or_error > 0:
            evidence_status = "unsupported"
        elif pending_or_missing > 0:
            evidence_status = "promising"
        elif len(group) >= 2:
            evidence_status = "validated"
        else:
            evidence_status = "observed"

        card = {
            "branch_key": key,
            "branch_label": branch_label(config_without_evidence_axes(best_result.config), baseline),
            "canonical_config": config_without_evidence_axes(best_result.config),
            "count": len(group),
            "seed_count": len(seeds),
            "regime_count": len(regimes),
            "seeds": seeds,
            "regimes": regimes,
            "metric_name": name,
            "mean": _mean(metric_values),
            "std": _std(metric_values),
            "best": best_result.metrics[name],
            "best_experiment_id": best_result.experiment_id,
            "constraint_pass_rate": (passed_constraints / total_constraints) if total_constraints else None,
            "robustness_pass_rate": (passed_robustness / total_robustness) if total_robustness else None,
            "pending_or_missing": pending_or_missing,
            "failed_or_error": failed_or_error,
            "evidence_status": evidence_status,
            "completed_members": completed_members,
            "incomplete_members": incomplete_members,
            "member_completion": completion,
        }
        card["evidence_gaps"] = detect_evidence_gaps(task, card)
        cards.append(card)

    return sorted(cards, key=lambda card: card["mean"], reverse=not lower_is_better)


def detect_evidence_gaps(task: TaskSpec, card: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    if expected_seed_count(task) > 0 and card.get("seed_count", 0) > 0 and card.get("seed_count", 0) < expected_seed_count(task):
        gaps.append("seed-coverage")
    if expected_regime_count(task) > 0 and card.get("regime_count", 0) > 0 and card.get("regime_count", 0) < expected_regime_count(task):
        gaps.append("regime-coverage")
    if card.get("pending_or_missing", 0) > 0:
        gaps.append("pending-checks")
    if card.get("failed_or_error", 0) > 0:
        gaps.append("failed-checks")
    if card.get("constraint_pass_rate") is not None and card["constraint_pass_rate"] < 1.0:
        gaps.append("constraint-failures")
    if card.get("robustness_pass_rate") is not None and card["robustness_pass_rate"] < 1.0:
        gaps.append("robustness-failures")
    if card.get("incomplete_members", 0) > 0:
        gaps.append("partial-bundle")
    if card.get("count", 0) <= 1:
        gaps.append("replication")
    if len(config_without_evidence_axes(card.get("canonical_config", {}))) > len(task.planner.baseline):
        gaps.append("ablation")
    return gaps


def build_evidence_state(task: TaskSpec, results: list[ExperimentResult]) -> dict[str, Any]:
    cards = aggregate_branch_evidence(task, results)
    best = cards[0] if cards else None
    return {
        "branch_cards": cards,
        "best_branch": best,
        "claim_taxonomy": claim_taxonomy_from_cards(cards),
    }


def claim_taxonomy_from_cards(cards: list[dict[str, Any]]) -> str:
    if not cards:
        return "unsupported"
    best = cards[0]
    return best["evidence_status"]
