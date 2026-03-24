from __future__ import annotations

from .schemas import ExperimentSpec, ExperimentResult, History, RoundPlan, TaskSpec


def next_round_index(history: History) -> int:
    return len(history.entries) + 1


def _metric_name(task: TaskSpec) -> str:
    return task.reporting.sort_by or (task.metrics.primary[0] if task.metrics.primary else "score")


def _best_previous_result(task: TaskSpec, history: History) -> ExperimentResult | None:
    metric_name = _metric_name(task)
    lower_is_better = task.reporting.lower_is_better
    completed = []
    for entry in history.entries:
        for result in entry.experiments:
            if result.status == "ok" and metric_name in result.metrics:
                completed.append(result)
    if not completed:
        return None
    return sorted(completed, key=lambda r: r.metrics[metric_name], reverse=not lower_is_better)[0]


def _round_best_result(task: TaskSpec, history: History) -> ExperimentResult | None:
    if not history.entries:
        return None
    metric_name = _metric_name(task)
    lower_is_better = task.reporting.lower_is_better
    latest = history.entries[-1]
    completed = [r for r in latest.experiments if r.status == "ok" and metric_name in r.metrics]
    if not completed:
        return None
    return sorted(completed, key=lambda r: r.metrics[metric_name], reverse=not lower_is_better)[0]


def _changed_keys(config: dict, reference: dict) -> list[str]:
    return [key for key, value in config.items() if reference.get(key) != value]


def _score_gap(task: TaskSpec, history: History) -> float | None:
    if not history.entries:
        return None
    metric_name = _metric_name(task)
    lower_is_better = task.reporting.lower_is_better
    latest = history.entries[-1]
    completed = [r for r in latest.experiments if r.status == "ok" and metric_name in r.metrics]
    if len(completed) < 2:
        return None
    ranked = sorted(completed, key=lambda r: r.metrics[metric_name], reverse=not lower_is_better)
    best = ranked[0].metrics[metric_name]
    second = ranked[1].metrics[metric_name]
    return second - best if lower_is_better else best - second


def _choose_round_mode(task: TaskSpec, history: History, anchor: dict) -> str:
    if not history.entries:
        return "explore"
    planner_baseline = dict(task.planner.baseline)
    changed = _changed_keys(anchor, planner_baseline)
    gap = _score_gap(task, history)
    if len(changed) >= 2:
        return "ablate"
    if gap is not None and abs(gap) < 1e-8:
        return "validate"
    if changed:
        return "exploit"
    return "explore"


def _add_experiment(
    experiments: list[ExperimentSpec],
    seen: set[tuple],
    round_index: int,
    config: dict,
    tag: str,
    notes: list[str],
    max_runs: int,
) -> None:
    frozen = tuple(sorted(config.items()))
    if frozen in seen or len(experiments) >= max_runs:
        return
    seen.add(frozen)
    experiments.append(
        ExperimentSpec(
            id=f"exp_{len(experiments)+1:03d}",
            round_index=round_index,
            config=config,
            tag=tag,
            notes=notes,
        )
    )


def build_round_plan(task: TaskSpec, history: History) -> RoundPlan:
    round_index = next_round_index(history)
    max_runs = task.budget.max_runs_per_round
    planner_baseline = dict(task.planner.baseline)
    best_previous = _best_previous_result(task, history)
    round_best = _round_best_result(task, history)
    anchor = dict(best_previous.config) if best_previous is not None else dict(planner_baseline)
    mode = _choose_round_mode(task, history, anchor)

    experiments: list[ExperimentSpec] = []
    seen: set[tuple] = set()

    anchor_note = "planner baseline" if best_previous is None else f"best previous configuration; mode={mode}"
    _add_experiment(
        experiments,
        seen,
        round_index,
        anchor,
        "baseline" if round_index == 1 else f"carryover-{mode}",
        [anchor_note],
        max_runs,
    )

    if round_index == 1:
        for key, values in task.search_space.items():
            for value in values:
                if value == planner_baseline.get(key):
                    continue
                config = dict(planner_baseline)
                config[key] = value
                _add_experiment(
                    experiments,
                    seen,
                    round_index,
                    config,
                    "explore",
                    [f"single-parameter variation around {key}"],
                    max_runs,
                )
                break

        if len(experiments) < max_runs:
            combo = dict(planner_baseline)
            changed = []
            for key, values in task.search_space.items():
                alt = next((v for v in values if v != planner_baseline.get(key)), None)
                if alt is not None:
                    combo[key] = alt
                    changed.append(key)
                if len(changed) == 2:
                    break
            if len(changed) >= 2:
                _add_experiment(
                    experiments,
                    seen,
                    round_index,
                    combo,
                    "explore",
                    [f"simple combination candidate over {', '.join(changed)}"],
                    max_runs,
                )
        return RoundPlan(task_name=task.name, round_index=round_index, experiments=experiments[:max_runs])

    changed_from_baseline = _changed_keys(anchor, planner_baseline)

    if mode in {"exploit", "ablate"}:
        for key in changed_from_baseline:
            config = dict(anchor)
            config[key] = planner_baseline.get(key)
            _add_experiment(
                experiments,
                seen,
                round_index,
                config,
                "ablate",
                [f"ablate {key} back to baseline"],
                max_runs,
            )

    if mode in {"exploit", "explore"} and len(experiments) < max_runs:
        for key, values in task.search_space.items():
            if key in changed_from_baseline:
                continue
            alt = next((v for v in values if v != anchor.get(key)), None)
            if alt is None:
                continue
            config = dict(anchor)
            config[key] = alt
            _add_experiment(
                experiments,
                seen,
                round_index,
                config,
                "explore",
                [f"local exploration on {key}"],
                max_runs,
            )
            if len(experiments) >= max_runs:
                break

    if mode == "validate" and len(experiments) < max_runs:
        for key in changed_from_baseline[:1]:
            config = dict(anchor)
            config[key] = planner_baseline.get(key)
            _add_experiment(
                experiments,
                seen,
                round_index,
                config,
                "validate",
                [f"validate whether gain persists after reverting {key}"],
                max_runs,
            )
        if task.evaluation_regimes and len(experiments) < max_runs:
            validation_config = dict(anchor)
            _add_experiment(
                experiments,
                seen,
                round_index,
                validation_config,
                "validate",
                [f"check named regimes: {', '.join(regime.name for regime in task.evaluation_regimes[:2])}"],
                max_runs,
            )

    if mode == "ablate" and len(experiments) < max_runs and changed_from_baseline:
        config = dict(anchor)
        for key in changed_from_baseline[:2]:
            config[key] = planner_baseline.get(key)
        _add_experiment(
            experiments,
            seen,
            round_index,
            config,
            "ablate",
            ["test whether combined gains persist when reverting key changes"],
            max_runs,
        )

    if mode == "exploit" and len(experiments) < max_runs and round_best is not None:
        for key in changed_from_baseline[:1]:
            config = dict(anchor)
            config[key] = round_best.config.get(key, config[key])
            _add_experiment(
                experiments,
                seen,
                round_index,
                config,
                "exploit",
                [f"keep current best branch and refine around {key}"],
                max_runs,
            )

    return RoundPlan(task_name=task.name, round_index=round_index, experiments=experiments[:max_runs])
