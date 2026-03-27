from __future__ import annotations

import shutil
from pathlib import Path

import typer
from rich.console import Console

from .loop import run_loop
from .planner import build_round_plan
from .runner import execute_plan
from .schemas import HistoryEntry, infer_run_root
from .storage import load_history, load_latest_evidence_state, load_plan, load_task, save_evidence_state, save_history, save_plan
from .summarizer import build_summary, save_summary
from .evidence import build_evidence_state
from .suggester import build_suggestions, render_suggestions
from .utils import round_plan_path, round_summary_path, round_suggestions_path

app = typer.Typer(help="Minimal autonomous research workflow for scientific ML.")
console = Console()
ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = ROOT / "examples"


def _round_mode_from_plan(plan) -> str:
    if not plan.experiments:
        return "unspecified"
    tag = plan.experiments[0].tag
    if tag.startswith("carryover-"):
        return tag.removeprefix("carryover-")
    if tag == "baseline":
        return "explore"
    return tag


def _metric_name(task_spec):
    return task_spec.reporting.sort_by or (task_spec.metrics.primary[0] if task_spec.metrics.primary else "score")


def _round_claim_label(task_spec, round_results):
    metric_name = _metric_name(task_spec)
    lower_is_better = task_spec.reporting.lower_is_better
    anchor = next((r for r in round_results if r.status == "ok" and r.experiment_id == "exp_001" and metric_name in r.metrics), None)
    completed = [r for r in round_results if r.status == "ok" and metric_name in r.metrics]
    if not completed or anchor is None:
        return "uncertain"
    best = sorted(completed, key=lambda r: r.metrics[metric_name], reverse=not lower_is_better)[0]
    improvement = anchor.metrics[metric_name] - best.metrics[metric_name] if lower_is_better else best.metrics[metric_name] - anchor.metrics[metric_name]
    if improvement > 0.01:
        return "supported"
    if improvement > 0:
        return "observed"
    return "uncertain"


def _format_branch_card_status(card: dict) -> str:
    segments = [
        f"taxonomy={card['evidence_status']}",
        f"completed_members={card.get('completed_members', 0)}",
        f"incomplete_members={card.get('incomplete_members', 0)}",
    ]
    if card.get("evidence_gaps"):
        segments.append(f"gaps={', '.join(card['evidence_gaps'])}")
    if card.get("missing_seeds"):
        segments.append(f"missing_seeds={', '.join(str(seed) for seed in card['missing_seeds'])}")
    if card.get("missing_regimes"):
        segments.append(f"missing_regimes={', '.join(card['missing_regimes'])}")
    coverage_guidance = card.get("coverage_guidance") or {}
    fixed_axes = coverage_guidance.get("recommended_fixed_axes") or {}
    if coverage_guidance.get("target_missing_seeds"):
        segments.append("target_missing_seeds=" + ", ".join(str(seed) for seed in coverage_guidance["target_missing_seeds"]))
    if coverage_guidance.get("target_missing_regimes"):
        segments.append("target_missing_regimes=" + ", ".join(coverage_guidance["target_missing_regimes"]))
    if fixed_axes.get("seed"):
        segments.append("fixed_seed=" + ", ".join(str(seed) for seed in fixed_axes["seed"]))
    if fixed_axes.get("evaluation_regime"):
        segments.append("fixed_regime=" + ", ".join(fixed_axes["evaluation_regime"]))
    return ", ".join(segments)


@app.command()
def init(example: str = typer.Option(..., help="Example name under examples/"), output: Path = typer.Option(..., help="Output run directory.")):
    source = EXAMPLES_DIR / example
    if not source.exists():
        raise typer.BadParameter(f"Example not found: {example}")
    if output.exists() and any(output.iterdir()):
        raise typer.BadParameter(f"Output directory already exists and is not empty: {output}")
    shutil.copytree(source, output, dirs_exist_ok=True)
    (output / "history.json").write_text('{\n  "task_name": "' + example + '",\n  "entries": []\n}\n', encoding="utf-8")
    console.print(f"Initialized run directory: [green]{output}[/green]")


@app.command()
def plan(task: Path = typer.Option(..., help="Path to task.yaml"), preview: bool = typer.Option(False, "--preview", help="Preview the next round plan without saving it.")):
    task_spec = load_task(task)
    run_root = infer_run_root(task)
    history = load_history(run_root, task_name=task_spec.name)
    round_plan = build_round_plan(task_spec, history)
    round_mode = _round_mode_from_plan(round_plan)
    if preview:
        console.print(f"Preview for round {round_plan.round_index} (mode={round_mode}):")
        for branch in round_plan.branches:
            console.print(f"- {branch.id}: {branch.tag} :: runs={branch.planned_evidence_runs} :: {branch.notes[0] if branch.notes else ''}")
        for exp in round_plan.experiments:
            console.print(f"  - {exp.id}: {exp.tag} [{exp.branch_id}] :: {exp.notes[0] if exp.notes else ''}")
        return
    path = round_plan_path(run_root, round_plan.round_index)
    save_plan(path, round_plan)
    console.print(f"Saved round plan to [green]{path}[/green]")
    console.print(f"Round mode: {round_mode}")
    for branch in round_plan.branches:
        console.print(f"- {branch.id}: {branch.tag} ({branch.planned_evidence_runs} evidence run(s))")
    for exp in round_plan.experiments:
        console.print(f"  - {exp.id}: {exp.tag} [{exp.branch_id}]")


@app.command()
def run(
    task: Path = typer.Option(None, help="Path to task.yaml"),
    plan_path: Path = typer.Option(None, "--plan", help="Path to round plan yaml"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show which plan would be executed without running experiments."),
):
    if task is None and plan_path is None:
        raise typer.BadParameter("Provide --task or --plan")
    if task is None:
        raise typer.BadParameter("A task file is required so the task spec can be loaded")
    task_spec = load_task(task)
    run_root = infer_run_root(task)
    history = load_history(run_root, task_name=task_spec.name)
    if plan_path is None:
        plan_path = round_plan_path(run_root, len(history.entries) + 1)
    if plan_path.exists():
        round_plan = load_plan(plan_path)
    else:
        round_plan = build_round_plan(task_spec, history)
    round_mode = _round_mode_from_plan(round_plan)
    if dry_run:
        console.print(f"Dry run for round {round_plan.round_index} (mode={round_mode}):")
        for branch in round_plan.branches:
            console.print(f"- {branch.id}: {branch.tag} -> canonical={branch.canonical_config} -> evidence_runs={branch.planned_evidence_runs}")
        for exp in round_plan.experiments:
            console.print(f"  - {exp.id}: {exp.tag} [{exp.branch_id}] -> {exp.config}")
        return
    results = execute_plan(task_spec, round_plan, run_root, resume=True)
    evidence_state = build_evidence_state(task_spec, [r for entry in history.entries for r in entry.experiments] + results)
    save_evidence_state(run_root, round_plan.round_index, evidence_state)
    history.entries.append(HistoryEntry(round_index=round_plan.round_index, plan_path=str(plan_path), experiments=results))
    save_history(run_root, history)
    resumed = sum(1 for r in results if r.provenance is not None and r.provenance.resumed)
    console.print(f"Executed {len(results)} experiment(s) for round {round_plan.round_index} in mode={round_mode} (resumed={resumed}).")


@app.command()
def summarize(run: Path = typer.Option(..., help="Run directory"), round_index: int | None = typer.Option(None, "--round")):
    task_path = run / "task.yaml"
    task_spec = load_task(task_path)
    history = load_history(run, task_name=task_spec.name)
    if not history.entries:
        raise typer.BadParameter("No history available to summarize")
    entry = history.entries[-1] if round_index is None else next(e for e in history.entries if e.round_index == round_index)
    historical_results = [r for e in history.entries if e.round_index < entry.round_index for r in e.experiments]
    plan = load_plan(Path(entry.plan_path)) if Path(entry.plan_path).exists() else None
    round_mode = _round_mode_from_plan(plan) if plan is not None else "unspecified"
    summary = build_summary(task_spec, entry.round_index, entry.experiments, historical_results=historical_results, round_mode=round_mode)
    path = round_summary_path(run, entry.round_index)
    save_summary(path, summary)
    entry.summary_path = str(path)
    save_history(run, history)
    console.print(f"Saved summary to [green]{path}[/green]")


@app.command()
def suggest(run: Path = typer.Option(..., help="Run directory"), round_index: int | None = typer.Option(None, "--round")):
    task_path = run / "task.yaml"
    task_spec = load_task(task_path)
    history = load_history(run, task_name=task_spec.name)
    if not history.entries:
        raise typer.BadParameter("No history available to suggest from")
    entry = history.entries[-1] if round_index is None else next(e for e in history.entries if e.round_index == round_index)
    historical_results = [r for e in history.entries if e.round_index < entry.round_index for r in e.experiments]
    suggestion = build_suggestions(task_spec, entry.experiments, historical_results=historical_results)
    path = round_suggestions_path(run, entry.round_index)
    path.write_text(render_suggestions(suggestion, entry.round_index), encoding="utf-8")
    entry.suggestion_path = str(path)
    save_history(run, history)
    console.print(f"Saved suggestions to [green]{path}[/green]")


@app.command()
def status(run: Path = typer.Option(..., help="Run directory")):
    task_path = run / "task.yaml"
    task_spec = load_task(task_path)
    history = load_history(run, task_name=task_spec.name)
    console.print(f"Task: [bold]{task_spec.name}[/bold]")
    console.print(f"Rounds completed: {len(history.entries)} / {task_spec.budget.max_rounds}")
    console.print(f"Budget: branches/round={task_spec.budget.max_branches_per_round}, evidence-runs/branch={task_spec.budget.max_evidence_runs_per_branch}, max-runs/round={task_spec.budget.max_runs_per_round}")
    console.print(f"Seeds: {task_spec.seeds if task_spec.seeds else 'none'}")
    console.print(
        f"Evaluation regimes: {', '.join(regime.name for regime in task_spec.evaluation_regimes) if task_spec.evaluation_regimes else 'default'}"
    )
    if not history.entries:
        console.print("No completed rounds yet.")
        return

    metric_name = _metric_name(task_spec)
    lower_is_better = task_spec.reporting.lower_is_better
    all_results = []
    trend_lines = []
    claim_lines = []
    branch_counter = {}
    baseline = task_spec.planner.baseline
    for entry in history.entries:
        round_results = [r for r in entry.experiments if r.status == "ok" and metric_name in r.metrics]
        all_results.extend(round_results)
        for result in round_results:
            changed = sorted(key for key, value in result.config.items() if baseline.get(key) != value)
            branch = "+".join(changed) if changed else "baseline"
            branch_counter[branch] = branch_counter.get(branch, 0) + 1
        if round_results:
            best_round = sorted(round_results, key=lambda r: r.metrics[metric_name], reverse=not lower_is_better)[0]
            plan = load_plan(Path(entry.plan_path)) if Path(entry.plan_path).exists() else None
            mode = _round_mode_from_plan(plan) if plan is not None else "unspecified"
            trend_lines.append(f"round {entry.round_index} [{mode}]: {best_round.experiment_id} -> {best_round.metrics[metric_name]}")
            claim_lines.append(f"round {entry.round_index}: {_round_claim_label(task_spec, round_results)}")

    if all_results:
        best = sorted(all_results, key=lambda r: r.metrics[metric_name], reverse=not lower_is_better)[0]
        console.print(f"Best so far: {best.experiment_id} (round {best.round_index}) -> {metric_name}={best.metrics[metric_name]}")
        console.print(f"Best config: {best.config}")

    if trend_lines:
        console.print("Per-round best trend:")
        for line in trend_lines:
            console.print(f"- {line}")
    if claim_lines:
        console.print("Claim trajectory:")
        for line in claim_lines:
            console.print(f"- {line}")
    if branch_counter:
        console.print("Branch evidence:")
        for branch, count in sorted(branch_counter.items(), key=lambda item: (-item[1], item[0])):
            console.print(f"- {branch}: {count} successful run(s)")

    latest = history.entries[-1]
    latest_plan = load_plan(Path(latest.plan_path)) if Path(latest.plan_path).exists() else None
    latest_mode = _round_mode_from_plan(latest_plan) if latest_plan is not None else "unspecified"
    console.print(f"Latest round: {latest.round_index} (mode={latest_mode})")
    latest_state = load_latest_evidence_state(run)
    if latest_state and latest_state.get("branch_cards"):
        console.print("Latest persisted evidence state:")
        for card in latest_state["branch_cards"][:3]:
            console.print(f"- {card['branch_label']}: {_format_branch_card_status(card)}")
    if latest.summary_path:
        console.print(f"Summary: {latest.summary_path}")
    if latest.suggestion_path:
        console.print(f"Suggestions: {latest.suggestion_path}")


@app.command()
def loop(task: Path = typer.Option(..., help="Path to task.yaml"), rounds: int = typer.Option(1, help="Number of rounds to run.")):
    run_loop(task, rounds, console=console)
    console.print("Loop finished.")


if __name__ == "__main__":
    app()
