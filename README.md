# scientific-ml-autoresearch

**A minimal autonomous research workflow for scientific machine learning.**

Scientific ML research often follows a repetitive loop:

- tweak an idea
- create a few experiment configs
- run training and evaluation
- compare results
- summarize what happened
- decide what to try next

This project automates that loop with as little infrastructure as possible.

It is designed for researchers who already have working training scripts and want a lightweight workflow to iterate faster, keep better experiment records, and reduce manual overhead.

## Why this project?

Scientific ML experiments are often harder to manage than standard ML benchmarks because they involve:

- multiple baselines and ablations
- PDE- or physics-specific constraints
- custom metrics
- noisy experiment bookkeeping
- repeated small next-step decisions after each round

Most of this work is not intellectually deep, but it still consumes time.

This repo focuses on a simple goal:

> make iterative research workflows easier to run, summarize, and continue.

## What this project does

`scientific-ml-autoresearch` provides a lightweight loop:

1. **plan** the next round of experiments
2. **run** those experiments
3. **summarize** results into a readable report
4. **suggest** what to try next
5. **repeat**

The design is intentionally minimal:

- local-first
- file-based
- CLI-driven
- easy to adapt to existing training scripts
- no heavy orchestration required

## What this project is not

This repo is **not**:

- a fully autonomous scientist
- a general multi-agent platform
- a replacement for scientific judgment
- a full MLOps system
- tied to a single LLM provider or benchmark

The goal is not to discover science automatically.

The goal is to provide a practical, open-source workflow that helps scientific ML researchers iterate more cleanly and more consistently.

## Installation

```bash
git clone https://github.com/yourname/scientific-ml-autoresearch.git
cd scientific-ml-autoresearch
pip install -e .
```

## Quick start

```bash
autoresearch init --example advection --output runs/advection_demo
autoresearch plan --task runs/advection_demo/task.yaml
autoresearch run --task runs/advection_demo/task.yaml
autoresearch summarize --run runs/advection_demo
autoresearch suggest --run runs/advection_demo
autoresearch loop --task runs/advection_demo/task.yaml --rounds 2
```

You can also start from the second example:

```bash
autoresearch init --example burgers --output runs/burgers_demo
```

## Detailed usage guide

### 1. Initialize a run directory

```bash
autoresearch init --example advection --output runs/advection_demo
```

This creates a self-contained run directory with:

- `task.yaml`
- example scripts
- `history.json`

Use `advection` or `burgers` as the starting example, then edit `task.yaml` to match your own project.

### 2. Inspect the task file

A task file defines:

- `commands.train` and `commands.eval`
- tracked metrics
- search space
- planner baseline
- budget
- optional `seeds`
- optional `evaluation_regimes`
- optional `constraints`
- optional `robustness_checks`

Minimal example:

```yaml
name: advection_minimal
workspace: .
commands:
  train: "python train.py --config {config_path} --output-dir {run_dir}"
  eval: "python evaluate.py --run-dir {run_dir}"
metrics:
  primary: [rel_l2]
  secondary: [conservation_error, runtime_seconds]
search_space:
  model.width: [32, 64]
planner:
  baseline:
    model.width: 32
budget:
  max_runs_per_round: 4
  max_rounds: 3
seeds: [0, 1]
evaluation_regimes:
  - name: default-grid
  - name: harder-grid
constraints:
  - conservation
robustness_checks:
  - name: shifted-grid
```

### 3. Use constraints and robustness hooks

These fields are lightweight but important if you want the workflow to look more like scientific ML rather than generic config search.

#### `constraints`
Use this list for domain properties you expect the method to respect, for example:

- conservation
- positivity
- stable long-time behavior
- symmetry preservation
- shock-capturing quality

The current system does not yet automatically compute these checks, but it does:

- surface them in summaries
- include them in suggestions
- encourage you to validate them before overclaiming progress

#### `robustness_checks`
Use this list for explicit validation hooks, for example:

- shifted-grid
- noisy-observation
- sharper-regime
- lr-perturbation
- parameter-transfer

The current system uses them as structured reminders in reports and suggestions.

### 4. Preview the next round

```bash
autoresearch plan --task runs/advection_demo/task.yaml --preview
```

This shows the next round without writing files.

Useful when you want to inspect whether the planner is in:

- `explore`
- `exploit`
- `ablate`
- `validate`

mode before actually saving or running anything.

### 5. Save a round plan

```bash
autoresearch plan --task runs/advection_demo/task.yaml
```

This writes a file like:

- `round_01_plan.yaml`
- `round_02_plan.yaml`

The first experiment in each round is the anchor, and its tag encodes the round mode, for example:

- `carryover-explore`
- `carryover-exploit`
- `carryover-ablate`
- `carryover-validate`

### 6. Dry-run before execution

```bash
autoresearch run --task runs/advection_demo/task.yaml --dry-run
```

This prints the exact experiment configs that would run.

### 7. Execute experiments

```bash
autoresearch run --task runs/advection_demo/task.yaml
```

By default the runner:

- writes one config per experiment
- executes the training command
- executes the evaluation command
- collects metrics into per-experiment directories

### 8. Summarize results

```bash
autoresearch summarize --run runs/advection_demo
```

The generated summary includes:

- round mode
- ranking
- delta vs baseline
- delta vs round anchor
- best run in this round
- best-so-far across all completed rounds
- named constraints
- named robustness hooks

### 9. Generate next-step suggestions

```bash
autoresearch suggest --run runs/advection_demo
```

Suggestions include:

- rationale from the current round
- `next_action_type`
- actionable next experiments
- reminders about constraints and robustness hooks

Current action types are:

- `explore`
- `exploit`
- `ablate`
- `validate`
- `stop`

### 10. Check current status

```bash
autoresearch status --run runs/advection_demo
```

This shows:

- rounds completed
- seeds and evaluation regimes
- best-so-far run and config
- per-round best trend
- latest summary path
- latest suggestion path
- latest round mode

### 11. Run a multi-round loop

```bash
autoresearch loop --task runs/advection_demo/task.yaml --rounds 3
```

During the loop, the tool now prints:

- current round mode
- planned experiments
- round completion summary
- current best result
- next recommended action type

The loop also supports a lightweight stopping heuristic:

- if the suggestion after a round becomes `stop`, the loop ends early

## Helpful CLI options

```bash
# Preview the next round plan without writing files
autoresearch plan --task runs/advection_demo/task.yaml --preview

# Show which experiments would run without executing them
autoresearch run --task runs/advection_demo/task.yaml --dry-run

# Show current progress, best run so far, and report locations
autoresearch status --run runs/advection_demo
```

## Typical workflow

```text
task.yaml
   ↓
plan
   ↓
round_01_plan.yaml
   ↓
run
   ↓
metrics + logs + artifacts
   ↓
summarize
   ↓
round_01_summary.md
   ↓
suggest
   ↓
round_01_suggestions.md
```

## Example summary output

```md
## Best Run
`exp_003` achieved the best `rel_l2` value in this round: `0.0464`.
Compared with baseline, the improvement on `rel_l2` is `0.016800`.
Compared with the round anchor, the improvement on `rel_l2` is `0.004000`.

## Scientific checks
- Review whether the best run appears consistent with these named constraints: conservation, stable long-time behavior.
- Pending robustness hooks for this task: shifted-grid, noisy-observation.
```

## Current features

- simple file-based task spec
- heuristic round planning with explicit exploit / explore / ablate / validate modes
- lightweight history-aware carryover of the best previous configuration
- round 2+ generation that adapts between refinement, ablation, exploration, and validation
- local execution of train/eval commands
- markdown round summaries with round mode, config changes, ranking, baseline deltas, anchor deltas, constraints, and robustness hooks
- suggestion logic that reasons about anchor gains, top-run gaps, stopping cases, constraints, and robustness hooks
- reproducible run directories
- plan preview, run dry-run, and status inspection support
- more informative loop progress logs with early stopping on `stop`
- two toy scientific ML-style examples: advection and Burgers

## Project layout

```text
scientific-ml-autoresearch/
├─ examples/
├─ src/autoresearch/
├─ docs/
├─ runs/
└─ tests/
```

## Philosophy

This repo tries to sit in a narrow but useful space:

- more structured than ad-hoc scripts
- much lighter than a full orchestration platform
- more research-aware than generic experiment tracking

If it helps researchers spend less time on repetitive workflow glue and more time on actual scientific reasoning, it is doing its job.

## Next improvements

Near-term improvements are still focused on practical workflow quality:

- stronger historical stopping rules
- richer summary/report views
- more realistic scientific ML adapters
- optional model-backed suggestion mode
- explicit claim-strength reporting for scientific conclusions

## License

MIT
