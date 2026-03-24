from __future__ import annotations

from itertools import product
from pathlib import Path
from typing import Any


def flatten_dict(d: dict[str, Any], parent_key: str = "", sep: str = ".") -> dict[str, Any]:
    items: dict[str, Any] = {}
    for key, value in d.items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else key
        if isinstance(value, dict):
            items.update(flatten_dict(value, new_key, sep=sep))
        else:
            items[new_key] = value
    return items


def nest_dict(flat: dict[str, Any], sep: str = ".") -> dict[str, Any]:
    nested: dict[str, Any] = {}
    for key, value in flat.items():
        current = nested
        parts = key.split(sep)
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = value
    return nested


def generate_single_variations(baseline: dict[str, Any], search_space: dict[str, list[Any]]) -> list[dict[str, Any]]:
    variants: list[dict[str, Any]] = []
    for key, values in search_space.items():
        base_value = baseline.get(key)
        for value in values:
            if value == base_value:
                continue
            config = dict(baseline)
            config[key] = value
            variants.append(config)
            break
    return variants


def first_combination(baseline: dict[str, Any], search_space: dict[str, list[Any]], limit: int = 2) -> dict[str, Any] | None:
    candidate_keys = []
    candidate_values = []
    for key, values in search_space.items():
        alt = [v for v in values if v != baseline.get(key)]
        if alt:
            candidate_keys.append(key)
            candidate_values.append(alt[0])
        if len(candidate_keys) == limit:
            break
    if len(candidate_keys) < 2:
        return None
    combo = dict(baseline)
    for key, value in zip(candidate_keys, candidate_values):
        combo[key] = value
    return combo


def round_plan_path(run_root: Path, round_index: int) -> Path:
    return run_root / f"round_{round_index:02d}_plan.yaml"


def round_summary_path(run_root: Path, round_index: int) -> Path:
    return run_root / f"round_{round_index:02d}_summary.md"


def round_suggestions_path(run_root: Path, round_index: int) -> Path:
    return run_root / f"round_{round_index:02d}_suggestions.md"
