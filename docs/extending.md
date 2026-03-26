# Extending the workflow

To adapt this repo to your own scientific ML project, the easiest path is:

1. keep your existing training code
2. expose a config file interface
3. make evaluation write a `metrics.json`
4. point `task.yaml` commands to your scripts
5. progressively convert scientific checks from reminders into executable hooks

The current v0 assumes each experiment can be launched via:

- a train command with `{config_path}` and `{run_dir}` placeholders
- an eval command with `{run_dir}`

If your project already has training and evaluation scripts, integration should mainly be a matter of command wrapping and metric parsing.

## Recommended extension order

### 1. Start with metrics that already exist

If your evaluator already produces things like:

- relative L2 error
- conservation error
- runtime
- rollout instability flags

then add them directly to `metrics.json` and wire the important ones into:

- `metrics.primary`
- `metrics.secondary`
- executable `constraints`

### 2. Convert named checks into executable checks

A good first upgrade is turning a statement like:

```yaml
constraints:
  - conservation
```

into:

```yaml
constraints:
  - name: conservation
    metric: conservation_error
    threshold: 1.0e-3
    direction: lower_is_better
```

This lets the runner evaluate the check automatically and lets the reporting layer distinguish:

- passed evidence
- failed evidence
- missing evidence

### 3. Add explicit robustness evaluators

If your project has special evaluation scripts for harder settings, attach them as robustness hooks:

```yaml
robustness_checks:
  - name: shifted-grid
    eval_command: "python evaluate_shifted.py --run-dir {run_dir} --output {output_path}"
    output_file: shifted_grid.json
```

This keeps robustness evidence close to the experiment it belongs to.

## Design goal

The longer-term goal is not just cleaner automation.
It is to make the workflow increasingly evidence-aware, so the next-step logic can reason about:

- what improved,
- what failed,
- what is still pending,
- and what should not yet be claimed.
