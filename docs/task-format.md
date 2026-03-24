# Task format

A task is a YAML file that defines:

- workspace location
- train/eval commands
- tracked metrics
- search space
- baseline configuration
- round budget

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
```
