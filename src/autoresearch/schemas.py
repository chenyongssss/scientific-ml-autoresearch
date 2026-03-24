from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


class Commands(BaseModel):
    train: str
    eval: str


class MetricsSpec(BaseModel):
    primary: list[str] = Field(default_factory=list)
    secondary: list[str] = Field(default_factory=list)


class PlannerConfig(BaseModel):
    strategy: str = "heuristic"
    baseline: dict[str, Any] = Field(default_factory=dict)


class BudgetConfig(BaseModel):
    max_runs_per_round: int = 4
    max_rounds: int = 3


class ReportingConfig(BaseModel):
    sort_by: str = "score"
    lower_is_better: bool = True


class TaskSpec(BaseModel):
    name: str
    description: str = ""
    workspace: str
    commands: Commands
    metrics: MetricsSpec = Field(default_factory=MetricsSpec)
    search_space: dict[str, list[Any]] = Field(default_factory=dict)
    planner: PlannerConfig = Field(default_factory=PlannerConfig)
    budget: BudgetConfig = Field(default_factory=BudgetConfig)
    reporting: ReportingConfig = Field(default_factory=ReportingConfig)
    notes: list[str] = Field(default_factory=list)


class ExperimentSpec(BaseModel):
    id: str
    round_index: int
    config: dict[str, Any] = Field(default_factory=dict)
    tag: str = "candidate"
    notes: list[str] = Field(default_factory=list)


class RoundPlan(BaseModel):
    task_name: str
    round_index: int
    experiments: list[ExperimentSpec] = Field(default_factory=list)


class ExperimentResult(BaseModel):
    experiment_id: str
    round_index: int
    status: Literal["ok", "failed"]
    metrics: dict[str, Any] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)
    run_dir: str
    error: str | None = None


class HistoryEntry(BaseModel):
    round_index: int
    plan_path: str
    summary_path: str | None = None
    suggestion_path: str | None = None
    experiments: list[ExperimentResult] = Field(default_factory=list)


class History(BaseModel):
    task_name: str
    entries: list[HistoryEntry] = Field(default_factory=list)


class Suggestion(BaseModel):
    title: str
    rationale: str
    actions: list[str] = Field(default_factory=list)


def infer_run_root(task_path: Path) -> Path:
    return task_path.resolve().parent
