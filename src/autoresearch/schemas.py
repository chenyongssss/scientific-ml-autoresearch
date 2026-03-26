from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


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
    max_branches_per_round: int | None = None
    max_evidence_runs_per_branch: int | None = None

    @model_validator(mode="after")
    def fill_derived_budget_defaults(self):
        if self.max_branches_per_round is None:
            self.max_branches_per_round = self.max_runs_per_round
        if self.max_evidence_runs_per_branch is None:
            self.max_evidence_runs_per_branch = 1
        return self


class ReportingConfig(BaseModel):
    sort_by: str = "score"
    lower_is_better: bool = True


class EvaluationRegime(BaseModel):
    name: str
    description: str = ""


class ConstraintSpec(BaseModel):
    name: str
    description: str = ""
    metric: str | None = None
    threshold: float | None = None
    direction: Literal["lower_is_better", "higher_is_better"] = "lower_is_better"
    required: bool = True

    @model_validator(mode="after")
    def validate_threshold_bundle(self):
        if (self.metric is None) != (self.threshold is None):
            raise ValueError("constraint metric and threshold must be provided together")
        return self


class RobustnessCheck(BaseModel):
    name: str
    description: str = ""
    eval_command: str | None = None
    metrics: list[str] = Field(default_factory=list)
    output_file: str | None = None


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
    seeds: list[int] = Field(default_factory=list)
    evaluation_regimes: list[EvaluationRegime] = Field(default_factory=list)
    constraints: list[ConstraintSpec] = Field(default_factory=list)
    robustness_checks: list[RobustnessCheck] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_fields(cls, data: Any):
        if not isinstance(data, dict):
            return data
        data = dict(data)
        constraints = data.get("constraints", [])
        normalized_constraints = []
        for item in constraints:
            if isinstance(item, str):
                normalized_constraints.append({"name": item})
            else:
                normalized_constraints.append(item)
        data["constraints"] = normalized_constraints
        return data


class ExperimentSpec(BaseModel):
    id: str
    round_index: int
    config: dict[str, Any] = Field(default_factory=dict)
    tag: str = "candidate"
    notes: list[str] = Field(default_factory=list)
    branch_id: str | None = None


class ScientificCheckResult(BaseModel):
    name: str
    kind: Literal["constraint", "robustness"]
    status: Literal["passed", "failed", "pending", "missing", "error"]
    metric: str | None = None
    value: float | int | str | None = None
    threshold: float | None = None
    direction: Literal["lower_is_better", "higher_is_better"] | None = None
    details: str = ""
    metrics: dict[str, Any] = Field(default_factory=dict)
    artifact_path: str | None = None


class BranchPlan(BaseModel):
    id: str
    round_index: int
    canonical_config: dict[str, Any] = Field(default_factory=dict)
    tag: str = "candidate"
    notes: list[str] = Field(default_factory=list)
    planned_evidence_runs: int = 1
    evidence_members: list[str] = Field(default_factory=list)


class RoundPlan(BaseModel):
    task_name: str
    round_index: int
    experiments: list[ExperimentSpec] = Field(default_factory=list)
    branches: list[BranchPlan] = Field(default_factory=list)


class ProvenanceRecord(BaseModel):
    task_name: str | None = None
    branch_id: str | None = None
    round_index: int | None = None
    config_path: str | None = None
    train_command: str | None = None
    eval_command: str | None = None
    resumed: bool = False
    metrics_path: str | None = None
    artifact_paths: list[str] = Field(default_factory=list)


class ArtifactStatus(BaseModel):
    metrics_present: bool = False
    scientific_checks_complete: bool = False
    robustness_complete: bool = False
    artifact_valid: bool = False


class ExperimentResult(BaseModel):
    experiment_id: str
    round_index: int
    status: Literal["ok", "failed"]
    metrics: dict[str, Any] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)
    run_dir: str
    scientific_checks: list[ScientificCheckResult] = Field(default_factory=list)
    branch_id: str | None = None
    provenance: ProvenanceRecord | None = None
    artifact_status: ArtifactStatus = Field(default_factory=ArtifactStatus)
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
    next_action_type: Literal["exploit", "explore", "ablate", "validate", "stop"] = "validate"
    actions: list[str] = Field(default_factory=list)


def infer_run_root(task_path: Path) -> Path:
    return task_path.resolve().parent
