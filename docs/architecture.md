# Architecture

V0 is intentionally simple.

Core modules:

- `planner.py`: generate a small round plan from the task spec and prior history
- `runner.py`: execute train/eval commands and collect metrics
- `summarizer.py`: convert experiment results into a markdown round summary
- `suggester.py`: produce lightweight next-step recommendations
- `loop.py`: connect the full round-based workflow

The default loop is:

1. load `task.yaml`
2. generate `round_XX_plan.yaml`
3. execute experiments
4. write `history.json`
5. generate `round_XX_summary.md`
6. generate `round_XX_suggestions.md`
