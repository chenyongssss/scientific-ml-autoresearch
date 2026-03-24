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

## Observations
- The round anchor is `exp_001` with changes: model.width=64.
- The current best run is `exp_003` with changes: model.width=64, model.depth=3.
- No failed runs were observed in this round.
```

## Current v0 features

- simple file-based task spec
- heuristic round planning
- lightweight history-aware carryover of the best previous configuration
- round 2+ ablation and local exploration around the current best run
- local execution of train/eval commands
- markdown round summaries with config changes, ranking, baseline deltas, and anchor deltas
- suggestion logic that reasons about anchor gains and top-run gaps
- reproducible run directories
- plan preview, run dry-run, and status inspection support
- more informative loop progress logs
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

## Roadmap

### v0
- local-first CLI workflow
- file-based task specs
- minimal planning, running, summarizing, and suggestion loop
- toy examples for adaptation

### v1
- stronger history-aware planning
- richer summary tables and config diff views
- optional LLM-backed suggestion mode
- more scientific ML examples
- lightweight robustness and ablation helpers

## License

MIT
