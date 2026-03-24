from __future__ import annotations

from pathlib import Path

from rich.console import Console

from .planner import build_round_plan
from .runner import execute_plan
from .storage import load_history, load_task, save_history, save_plan
from .summarizer import build_summary, save_summary
from .suggester import build_suggestions, render_suggestions
from .schemas import HistoryEntry, infer_run_root
from .utils import round_plan_path, round_summary_path, round_suggestions_path


def run_loop(task_path: Path, rounds: int, console: Console | None = None) -> None:
    task = load_task(task_path)
    run_root = infer_run_root(task_path)
    history = load_history(run_root, task_name=task.name)

    remaining = min(rounds, task.budget.max_rounds - len(history.entries))
    for _ in range(max(remaining, 0)):
        plan = build_round_plan(task, history)
        plan_path = round_plan_path(run_root, plan.round_index)
        save_plan(plan_path, plan)
        if console:
            console.print(f"[bold]Round {plan.round_index}[/bold]: planned {len(plan.experiments)} experiment(s)")
            for exp in plan.experiments:
                note = exp.notes[0] if exp.notes else ""
                console.print(f"  - {exp.id}: {exp.tag} ({note})")

        results = execute_plan(task, plan, run_root)
        summary_path = round_summary_path(run_root, plan.round_index)
        summary_text = build_summary(task, plan.round_index, results)
        save_summary(summary_path, summary_text)

        suggestion = build_suggestions(task, results)
        suggestion_path = round_suggestions_path(run_root, plan.round_index)
        suggestion_path.write_text(render_suggestions(suggestion, plan.round_index), encoding="utf-8")

        history.entries.append(
            HistoryEntry(
                round_index=plan.round_index,
                plan_path=str(plan_path),
                summary_path=str(summary_path),
                suggestion_path=str(suggestion_path),
                experiments=results,
            )
        )
        save_history(run_root, history)

        if console:
            completed = sum(1 for r in results if r.status == "ok")
            failed = sum(1 for r in results if r.status == "failed")
            metric_name = task.reporting.sort_by or (task.metrics.primary[0] if task.metrics.primary else "score")
            successful = [r for r in results if r.status == "ok" and metric_name in r.metrics]
            if successful:
                lower_is_better = task.reporting.lower_is_better
                best = sorted(successful, key=lambda r: r.metrics[metric_name], reverse=not lower_is_better)[0]
                console.print(
                    f"[green]Round {plan.round_index} done[/green]: completed={completed}, failed={failed}, best={best.experiment_id}, {metric_name}={best.metrics[metric_name]}"
                )
            else:
                console.print(f"[yellow]Round {plan.round_index} done[/yellow]: completed={completed}, failed={failed}, no valid metric yet")
            console.print(f"  summary: {summary_path}")
            console.print(f"  suggestions: {suggestion_path}")
