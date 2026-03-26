from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from .schemas import History, RoundPlan, TaskSpec


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def dump_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def load_task(path: Path) -> TaskSpec:
    return TaskSpec.model_validate(load_yaml(path))


def save_plan(path: Path, plan: RoundPlan) -> None:
    dump_yaml(path, plan.model_dump())


def load_plan(path: Path) -> RoundPlan:
    return RoundPlan.model_validate(load_yaml(path))


def history_path(run_root: Path) -> Path:
    return run_root / "history.json"


def evidence_state_path(run_root: Path, round_index: int) -> Path:
    return run_root / f"round_{round_index:02d}_evidence_state.json"


def save_evidence_state(run_root: Path, round_index: int, payload: dict[str, Any]) -> Path:
    path = evidence_state_path(run_root, round_index)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def load_evidence_state(run_root: Path, round_index: int) -> dict[str, Any] | None:
    path = evidence_state_path(run_root, round_index)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_latest_evidence_state(run_root: Path) -> dict[str, Any] | None:
    paths = sorted(run_root.glob("round_*_evidence_state.json"))
    if not paths:
        return None
    return json.loads(paths[-1].read_text(encoding="utf-8"))


def load_history(run_root: Path, task_name: str | None = None) -> History:
    path = history_path(run_root)
    if not path.exists():
        return History(task_name=task_name or run_root.name)
    return History.model_validate(json.loads(path.read_text(encoding="utf-8")))


def save_history(run_root: Path, history: History) -> None:
    path = history_path(run_root)
    path.write_text(history.model_dump_json(indent=2), encoding="utf-8")
