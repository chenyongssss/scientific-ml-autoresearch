from __future__ import annotations

from .schemas import ExperimentSpec, ExperimentResult, History, RoundPlan, TaskSpec


def next_round_index(history: History) -> int:
    return len(history.entries) + 1


def _best_previous_result(task: TaskSpec, history: History) -> ExperimentResult | None:
    metric_name = task.reporting.sort_by or (task.metrics.primary[0] if task.metrics.primary else "score")
    lower_is_better = task.reporting.lower_is_better
    completed = []
    for entry in history.entries:
        for result in entry.experiments:
            if result.status == "ok" and metric_name in result.metrics:
                completed.append(result)
    if not completed:
        return None
    return sorted(completed, key=lambda r: r.metrics[metric_name], reverse=not lower_is_better)[0]


def _changed_keys(config: dict, reference: dict) -> list[str]:
    return [key for key, value in config.items() if reference.get(key) != value]


def _add_experiment(experiments: list[ExperimentSpec], seen: set[tuple], round_index: int, config: dict, tag: str, notes: list[str], max_runs: int) -> None:
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
    anchor = dict(best_previous.config) if best_previous is not None else dict(planner_baseline)

    experiments: list[ExperimentSpec] = []
    seen: set[tuple] = set()

    _add_experiment(
        experiments,
        seen,
        round_index,
        anchor,
        "baseline" if round_index == 1 else "carryover-best",
        ["best previous configuration" if best_previous is not None else "planner baseline"],
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
                    "variation",
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
                    "combination",
                    [f"simple combination candidate over {', '.join(changed)}"],
                    max_runs,
                )
    else:
        changed_from_baseline = _changed_keys(anchor, planner_baseline)

        for key in changed_from_baseline:
            config = dict(anchor)
            config[key] = planner_baseline.get(key)
            _add_experiment(
                experiments,
                seen,
                round_index,
                config,
                "ablation",
                [f"ablate {key} back to baseline"],
                max_runs,
            )

        if len(experiments) < max_runs:
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
                    "exploration",
                    [f"local exploration on {key}"],
                    max_runs,
                )
                if len(experiments) >= max_runs:
                    break

        if len(experiments) < max_runs and changed_from_baseline:
            config = dict(anchor)
            for key in changed_from_baseline[:2]:
                config[key] = planner_baseline.get(key)
            _add_experiment(
                experiments,
                seen,
                round_index,
                config,
                "combined-ablation",
                ["test whether combined gains persist when reverting key changes"],
                max_runs,
            )

    return RoundPlan(task_name=task.name, round_index=round_index, experiments=experiments[:max_runs])
