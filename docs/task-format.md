# Task format

A task is a YAML file that defines:

- workspace location
- train/eval commands
- tracked metrics
- search space
- baseline configuration
- round budget
- scientific constraints
- robustness evaluation hooks

Minimal example:

```yaml
name: advection_minimal
workspace: .
commands:
  train: "python train.py --config {config_path} --output-dir {run_dir}"
  eval: "python evaluate.py --run-dir {run_dir}"
metrics:
  primary: [rel_l2]
search_space:
  model.width: [32, 64]
planner:
  baseline:
    model.width: 32
budget:
  max_runs_per_round: 4
  max_rounds: 3
reporting:
  sort_by: rel_l2
  lower_is_better: true
constraints:
  - name: conservation
    metric: conservation_error
    threshold: 0.001
    direction: lower_is_better
robustness_checks:
  - name: shifted-grid
    eval_command: "python evaluate_shifted.py --run-dir {run_dir} --output {output_path}"
    output_file: shifted_grid.json
    metrics: [rel_l2_shifted, conservation_error_shifted]
```

## Constraint forms

Legacy string-only constraints are still accepted:

```yaml
constraints:
  - conservation
  - stable long-time behavior
```

These act as named reminders only.

Executable constraints use a structured form:

```yaml
constraints:
  - name: conservation
    metric: conservation_error
    threshold: 1.0e-3
    direction: lower_is_better
```

When `metric` and `threshold` are present, the runner evaluates the constraint automatically from `metrics.json`.

## Robustness check forms

Reminder-only robustness checks:

```yaml
robustness_checks:
  - name: shifted-grid
    description: Validate on a shifted mesh.
```

Executable robustness checks:

```yaml
robustness_checks:
  - name: shifted-grid
    eval_command: "python evaluate_shifted.py --run-dir {run_dir} --output {output_path}"
    output_file: robustness_shifted_grid.json
    metrics: [rel_l2_shifted, conservation_error_shifted]
```

The robustness command may use these placeholders:

- `{config_path}`
- `{run_dir}`
- `{check_name}`
- `{output_path}`

The output file is expected to be JSON, for example:

```json
{
  "status": "passed",
  "details": "Shifted-grid error stayed within the allowed tolerance.",
  "metrics": {
    "rel_l2_shifted": 0.061,
    "conservation_error_shifted": 0.0004
  }
}
```

Supported statuses are:

- `passed`
- `failed`
- `pending`
- `missing`
- `error`

## Evidence bundles

When `seeds` or `evaluation_regimes` are present, the planner now expands a canonical candidate configuration into multiple concrete experiments.

For example, with:

```yaml
seeds: [0, 1]
evaluation_regimes:
  - name: default
  - name: harder
```

one planned candidate may expand into up to four concrete runs:

- same config + seed 0 + regime default
- same config + seed 0 + regime harder
- same config + seed 1 + regime default
- same config + seed 1 + regime harder

This is a lightweight way to make branch-level evidence more systematic.

The budget layer now supports both:

```yaml
budget:
  max_runs_per_round: 8
  max_branches_per_round: 3
  max_evidence_runs_per_branch: 2
```

Interpretation:

- `max_branches_per_round`: how many distinct canonical branches to consider in one round
- `max_evidence_runs_per_branch`: how many seed/regime bundle members to allocate per branch
- `max_runs_per_round`: hard ceiling on total concrete runs after expansion

If the expanded bundle would exceed the hard total run budget, the planner truncates concrete members.

## Design note

The point of these fields is not just richer bookkeeping.
It is to make the workflow increasingly evidence-aware:

- the runner records scientific checks,
- the summary reports them,
- and the suggestion logic can avoid overclaiming when evidence is incomplete.
