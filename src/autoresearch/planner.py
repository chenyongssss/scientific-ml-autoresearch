from __future__ import annotations

from .evidence import build_evidence_state, config_without_evidence_axes, detect_evidence_gaps
from .schemas import BranchPlan, ExperimentSpec, ExperimentResult, History, RoundPlan, TaskSpec
from .storage import load_latest_evidence_state


GAP_PRIORITY = {
    "failed-checks": 0,
    "constraint-failures": 1,
    "robustness-failures": 2,
    "partial-bundle": 3,
    "pending-checks": 4,
    "regime-coverage": 5,
    "seed-coverage": 6,
    "replication": 7,
    "ablation": 8,
}


def next_round_index(history: History) -> int:
    return len(history.entries) + 1


def _metric_name(task: TaskSpec) -> str:
    if task.reporting.sort_by and task.reporting.sort_by != "score":
        return task.reporting.sort_by
    if task.metrics.primary:
        return task.metrics.primary[0]
    return task.reporting.sort_by or "score"


def _canonical_config(config: dict) -> dict:
    return config_without_evidence_axes(config)


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
    canonical = _canonical_config(config)
    return [key for key, value in canonical.items() if reference.get(key) != value]


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


def _evidence_axes(task: TaskSpec, gap_focus: str | None, max_evidence_runs_per_branch: int) -> list[dict]:
    seeds = task.seeds or [None]
    regimes = [regime.name for regime in task.evaluation_regimes] or [None]
    axes = []
    for seed in seeds:
        for regime in regimes:
            entry = {}
            if seed is not None:
                entry["seed"] = seed
            if regime is not None:
                entry["evaluation_regime"] = regime
            axes.append(entry)
    axes = axes or [{}]

    if gap_focus == "seed-coverage":
        axes = sorted(axes, key=lambda item: (item.get("seed") is None, item.get("seed"), item.get("evaluation_regime") or ""))
    elif gap_focus == "regime-coverage":
        axes = sorted(axes, key=lambda item: (item.get("evaluation_regime") is None, item.get("evaluation_regime") or "", item.get("seed")))
    return axes[:max_evidence_runs_per_branch]


def _highest_priority_gap(gaps: list[str]) -> str | None:
    if not gaps:
        return None
    return sorted(gaps, key=lambda gap: GAP_PRIORITY.get(gap, 999))[0]


def _add_branch_bundle(
    plan: RoundPlan,
    seen: set[tuple],
    canonical_config: dict,
    tag: str,
    notes: list[str],
    task: TaskSpec,
    gap_focus: str | None = None,
    preferred_axes: list[dict] | None = None,
) -> None:
    max_branches = task.budget.max_branches_per_round or task.budget.max_runs_per_round
    max_evidence = task.budget.max_evidence_runs_per_branch or 1
    max_total_runs = task.budget.max_runs_per_round
    frozen_canonical = tuple(sorted(_canonical_config(canonical_config).items()))
    if frozen_canonical in seen:
        return
    if len(plan.branches) >= max_branches:
        return
    if len(plan.experiments) >= max_total_runs:
        return

    seen.add(frozen_canonical)
    branch_id = f"branch_{len(plan.branches)+1:03d}"
    branch = BranchPlan(
        id=branch_id,
        round_index=plan.round_index,
        canonical_config=_canonical_config(canonical_config),
        tag=tag,
        notes=notes + ([f"gap_focus={gap_focus}"] if gap_focus else []),
    )

    axes_pool = preferred_axes[:max_evidence] if preferred_axes else _evidence_axes(task, gap_focus, max_evidence)
    for idx, axis in enumerate(axes_pool):
        if len(plan.experiments) >= max_total_runs:
            break
        config = {**branch.canonical_config, **axis}
        evidence_bits = []
        if "seed" in config:
            evidence_bits.append(f"seed={config['seed']}")
        if "evaluation_regime" in config:
            evidence_bits.append(f"regime={config['evaluation_regime']}")
        member_notes = list(branch.notes)
        if evidence_bits:
            member_notes.append("evidence bundle member: " + ", ".join(evidence_bits))
        exp_id = f"exp_{len(plan.experiments)+1:03d}"
        branch.evidence_members.append(exp_id)
        plan.experiments.append(
            ExperimentSpec(
                id=exp_id,
                round_index=plan.round_index,
                config=config,
                tag=tag if idx == 0 else f"{tag}-evidence",
                notes=member_notes,
                branch_id=branch_id,
            )
        )

    branch.planned_evidence_runs = len(branch.evidence_members)
    if branch.evidence_members:
        plan.branches.append(branch)


def _historical_branch_cards(task: TaskSpec, history: History) -> list[dict]:
    all_results = [result for entry in history.entries for result in entry.experiments]
    return build_evidence_state(task, all_results)["branch_cards"]


def _branch_cards_with_source(task: TaskSpec, history: History) -> tuple[list[dict], str]:
    if not history.entries:
        return [], "none"
    latest_entry = history.entries[-1]
    run_root = None
    try:
        run_root = __import__("pathlib").Path(latest_entry.plan_path).resolve().parent
    except Exception:
        run_root = None
    if run_root is not None:
        state = load_latest_evidence_state(run_root)
        if state and isinstance(state.get("branch_cards"), list):
            return state["branch_cards"], "persisted"
    return _historical_branch_cards(task, history), "history"


def _missing_member_axes(card: dict) -> list[dict]:
    completed_axes = {tuple(sorted((member.get("axes") or {}).items())) for member in card.get("member_completion", []) if member.get("artifact_valid")}
    expected = []
    for member in card.get("member_completion", []):
        axis = member.get("axes") or {}
        if tuple(sorted(axis.items())) not in completed_axes:
            expected.append(axis)
    return expected


def _plan_from_evidence_gaps(task: TaskSpec, history: History, plan: RoundPlan, seen: set[tuple]) -> bool:
    cards, source = _branch_cards_with_source(task, history)
    if not cards:
        return False

    max_branches = task.budget.max_branches_per_round or task.budget.max_runs_per_round
    actionable = []
    for card in cards:
        gaps = card.get("evidence_gaps") or detect_evidence_gaps(task, card)
        allowed = {"failed-checks", "constraint-failures", "robustness-failures", "pending-checks", "seed-coverage", "regime-coverage"}
        if source == "persisted":
            allowed.add("partial-bundle")
        prioritized = [gap for gap in gaps if gap in allowed]
        if not prioritized:
            continue
        actionable.append((card, _highest_priority_gap(prioritized)))

    if not actionable:
        return False

    for card, gap_focus in actionable[:max_branches]:
        canonical = dict(card["canonical_config"])
        preferred_axes = _missing_member_axes(card) if (source == "persisted" and gap_focus == "partial-bundle") else None
        tag = "validate"
        notes = [f"address evidence gap: {gap_focus}", f"source={source}-evidence-state"]
        _add_branch_bundle(plan, seen, canonical, tag, notes, task, gap_focus=gap_focus, preferred_axes=preferred_axes)
        if len(plan.branches) >= max_branches or len(plan.experiments) >= task.budget.max_runs_per_round:
            break
    return bool(plan.branches)


def build_round_plan(task: TaskSpec, history: History) -> RoundPlan:
    round_index = next_round_index(history)
    planner_baseline = dict(task.planner.baseline)
    best_previous = _best_previous_result(task, history)
    round_best = _round_best_result(task, history)
    anchor = _canonical_config(best_previous.config) if best_previous is not None else dict(planner_baseline)
    mode = _choose_round_mode(task, history, anchor)

    plan = RoundPlan(task_name=task.name, round_index=round_index, experiments=[], branches=[])
    seen: set[tuple] = set()

    if history.entries and _plan_from_evidence_gaps(task, history, plan, seen):
        return plan

    anchor_note = "planner baseline" if best_previous is None else f"best previous configuration; mode={mode}"
    _add_branch_bundle(
        plan,
        seen,
        anchor,
        "baseline" if round_index == 1 else f"carryover-{mode}",
        [anchor_note],
        task,
    )

    if round_index == 1:
        for key, values in task.search_space.items():
            for value in values:
                if value == planner_baseline.get(key):
                    continue
                config = dict(planner_baseline)
                config[key] = value
                _add_branch_bundle(
                    plan,
                    seen,
                    config,
                    "explore",
                    [f"single-parameter variation around {key}"],
                    task,
                )
                break

        if len(plan.branches) < (task.budget.max_branches_per_round or task.budget.max_runs_per_round):
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
                _add_branch_bundle(
                    plan,
                    seen,
                    combo,
                    "explore",
                    [f"simple combination candidate over {', '.join(changed)}"],
                    task,
                )
        return plan

    changed_from_baseline = _changed_keys(anchor, planner_baseline)

    if mode in {"exploit", "ablate"}:
        for key in changed_from_baseline:
            config = dict(anchor)
            config[key] = planner_baseline.get(key)
            _add_branch_bundle(
                plan,
                seen,
                config,
                "ablate",
                [f"ablate {key} back to baseline"],
                task,
                gap_focus="ablation",
            )

    if mode in {"exploit", "explore"}:
        for key, values in task.search_space.items():
            if key in changed_from_baseline:
                continue
            alt = next((v for v in values if v != anchor.get(key)), None)
            if alt is None:
                continue
            config = dict(anchor)
            config[key] = alt
            _add_branch_bundle(
                plan,
                seen,
                config,
                "explore",
                [f"local exploration on {key}"],
                task,
            )
            if len(plan.branches) >= (task.budget.max_branches_per_round or task.budget.max_runs_per_round):
                break

    if mode == "validate":
        for key in changed_from_baseline[:1]:
            config = dict(anchor)
            config[key] = planner_baseline.get(key)
            _add_branch_bundle(
                plan,
                seen,
                config,
                "validate",
                [f"validate whether gain persists after reverting {key}"],
                task,
                gap_focus="ablation",
            )
        if task.evaluation_regimes:
            validation_config = dict(anchor)
            _add_branch_bundle(
                plan,
                seen,
                validation_config,
                "validate",
                [f"check named regimes: {', '.join(regime.name for regime in task.evaluation_regimes[:2])}"],
                task,
                gap_focus="regime-coverage",
            )

    if mode == "ablate" and changed_from_baseline:
        config = dict(anchor)
        for key in changed_from_baseline[:2]:
            config[key] = planner_baseline.get(key)
        _add_branch_bundle(
            plan,
            seen,
            config,
            "ablate",
            ["test whether combined gains persist when reverting key changes"],
            task,
            gap_focus="ablation",
        )

    if mode == "exploit" and round_best is not None:
        for key in changed_from_baseline[:1]:
            config = dict(anchor)
            config[key] = round_best.config.get(key, config[key])
            _add_branch_bundle(
                plan,
                seen,
                config,
                "exploit",
                [f"keep current best branch and refine around {key}"],
                task,
            )

    return plan
