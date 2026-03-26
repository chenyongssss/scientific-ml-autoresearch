# Technical roadmap

This roadmap prioritizes scientific validity over surface autonomy.

## Guiding principle

The next major upgrade is not "more automatic planning".
It is **better scientific evidence management**.

That means the workflow should increasingly answer:

- what improved?
- under which checks?
- with what evidence strength?
- what is still unsupported?

rather than only:

- what metric was best?
- what should we try next?

---

## Phase 1 — Executable scientific checks

**Goal:** turn constraints and robustness hooks from reminders into structured executable objects.

### Scope

1. Extend `task.yaml` so constraints can be declared as metric-threshold checks.
2. Extend `task.yaml` so robustness checks can optionally run dedicated evaluation commands.
3. Save per-experiment scientific check results into history.
4. Make summaries and suggestions aware of passed / failed / pending checks.

### Deliverables

- structured schema for `constraints`
- structured schema for `robustness_checks`
- runner support for optional robustness evaluation hooks
- summary section for scientific check outcomes
- suggestion logic that gates stronger claims on check completion

### Exit criteria

A round summary should be able to say not only "run X is best", but also:

- which constraints passed or failed
- which robustness checks are still pending
- whether the current claim is blocked by incomplete scientific evidence

---

## Phase 2 — Evidence-aware claim logic

**Goal:** move from single-run wins to defensible evidence states.

Status: in progress. Initial branch evidence aggregation and claim taxonomy are now being introduced.

### Scope

1. Aggregate results across seeds.
2. Aggregate across evaluation regimes.
3. Track evidence cards for each branch/configuration.
4. Distinguish observation, promising effect, validated effect, and unsupported claim.
5. Add multi-objective summaries instead of only single-metric ranking.

### Deliverables

- seed-aware result aggregation
- regime-aware result aggregation
- branch-level evidence summaries
- claim-strength model driven by structured evidence
- optional Pareto summary for accuracy / physics / cost tradeoffs
- bundle-style planning/execution support so seed/regime evidence is produced systematically instead of incidentally

### Exit criteria

The system should be able to explain why a claim is:

- only observed locally,
- promising but not yet robust,
- or sufficiently repeated to justify stronger wording.

---

## Phase 3 — Research-state-aware planning

**Goal:** upgrade planning from parameter search to research-action selection.

### Scope

1. Track a structured `research_state` after each round.
2. Represent the current best hypothesis and main threat to validity.
3. Choose next actions based on evidence gaps, not only score deltas.
4. Distinguish exploit / ablate / validate / stop using evidence needs.

### Deliverables

- research-state schema
- planner inputs derived from evidence gaps
- explicit decision reasons in plans
- better stop criteria based on repeated non-improvement or unresolved failures

### Exit criteria

The planner should justify not only what to run next, but why that action has the highest research value.

---

## Phase 4 — Scientific ML adapters

**Goal:** make the framework domain-aware instead of merely generic.

### Scope

1. PDE-oriented task templates.
2. Forward / inverse problem adapters.
3. Common scientific checks for conservation, positivity, long-time stability, transfer, and noisy observations.
4. Bundled evaluation regimes for resolution transfer and harder settings.
5. Paper-ready reporting blocks for methods sections and empirical claims.

### Deliverables

- adapter templates under `examples/` or `src/autoresearch/adapters/`
- reusable scientific check patterns
- example reports closer to paper appendix tables

### Exit criteria

A new scientific ML project should be able to start from a domain-aware template rather than only a generic task file.

---

## Immediate implementation order

1. Phase 1 schema + runner + report integration
2. Phase 1 examples + docs
3. Phase 2 seed/regime aggregation design
4. Phase 2 implementation
5. Branch-level schema + two-level budgeting
6. Phase 3 planner redesign around evidence gaps (in progress)
7. Reliability layer: persisted evidence state, provenance metadata, resumable execution (in progress)
8. Phase 4 adapters
