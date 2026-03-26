# scientific-ml-autoresearch

English | [简体中文](./README.zh-CN.md)

A complete, lightweight, evidence-aware auto-research workflow for scientific machine learning.

## Quick links

- **Static UI**: `docs/workflow-ui/index.html`
- **Task format**: `docs/task-format.md`
- **Extension notes**: `docs/extending.md`
- **Examples**: `examples/advection/`, `examples/burgers/`
- **CLI**: `autoresearch init / plan / run / summarize / suggest / loop / status`

## Repository snapshot

| Area | What it provides |
|---|---|
| `src/autoresearch/` | Planner, runner, evidence, summary, suggestion, storage, loop |
| `examples/` | Minimal runnable scientific ML examples |
| `docs/` | Task format, extension notes, architecture, static workflow UI |
| `tests/` | End-to-end workflow, evidence, recovery, and planner tests |

## At a glance

- Branch-aware planning with two-level budgeting
- Structured constraints and robustness checks
- Branch evidence cards, claim taxonomy, and evidence gaps
- Persisted evidence state and resumable execution
- Provenance and artifact validity tracking

## What this project is

**scientific-ml-autoresearch** packages a scientific ML research loop into a coherent workflow:

- plan experiment branches
- execute training and evaluation
- record scientific checks
- aggregate evidence state
- generate the next round suggestion

This repository is not a full MLOps platform and not an autonomous scientist.
It is a complete, runnable workflow built to support scientific ML research with explicit branch structure, evidence tracking, and recovery behavior.

## Workflow loop

The main loop is organized as:

1. `plan`: generate a round plan from the task spec, history, and evidence state
2. `run`: execute train / eval commands and write metrics, checks, and provenance
3. `summarize`: produce a round summary centered on branch evidence and scientific checks
4. `suggest`: recommend the next action from claim taxonomy and evidence gaps
5. `loop`: connect the round-based workflow into a continuous research cycle

## Core design

### 1. Branch-first planning
A round is treated as an allocation problem over **canonical branches**, not only as a flat list of configurations.

Each branch can expand into multiple evidence members, such as:

- different seeds
- different evaluation regimes

This gives the workflow an explicit way to represent both:

- exploration breadth
- validation depth

### 2. Evidence-aware research judgment
The system tracks more than a single best run. It maintains:

- branch evidence cards
- claim taxonomy
- evidence gaps
- partial bundle completion

It distinguishes among:

- observed
- promising
- validated
- unsupported

These states feed back into planning and suggestion generation.

### 3. Scientific checks as first-class workflow objects
`constraints` and `robustness_checks` are part of execution and reporting rather than being left as narrative comments.

They are consumed by:

- the runner
- evidence state generation
- summaries
- suggestions
- planning decisions

This makes common scientific ML validation concepts such as:

- conservation
- stability
- shifted-grid robustness
- noisy-observation robustness

part of the workflow itself.

### 4. Reliability layer
The repository includes a workflow reliability layer with:

- `provenance.json`
- artifact validity flags
- `round_XX_evidence_state.json`
- resume / rerun policy
- invalid artifact recovery

The workflow therefore does more than recommend actions. It can resume interrupted work and make explicit judgments about artifact validity.

## Main files and outputs

A typical run directory contains:

- `task.yaml`
- `round_XX_plan.yaml`
- `round_XX_evidence_state.json`
- `round_XX_summary.md`
- `round_XX_suggestions.md`
- `history.json`

Each experiment directory commonly contains:

- `config.yaml`
- `train.log`
- `eval.log`
- `metrics.json`
- `provenance.json`
- robustness artifacts

## CLI entry points

```bash
autoresearch init --example advection --output runs/advection_demo
autoresearch plan --task runs/advection_demo/task.yaml
autoresearch run --task runs/advection_demo/task.yaml
autoresearch summarize --run runs/advection_demo
autoresearch suggest --run runs/advection_demo
autoresearch loop --task runs/advection_demo/task.yaml --rounds 3
autoresearch status --run runs/advection_demo
```

## Documentation and UI

- Task format: `docs/task-format.md`
- Extension notes: `docs/extending.md`
- Static workflow UI: `docs/workflow-ui/index.html`

The UI is written in plain HTML / CSS / JS and can be opened directly in a browser.

## License

MIT
