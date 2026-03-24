# Contributing

Thanks for your interest in contributing to `scientific-ml-autoresearch`.

## Principles

Please keep contributions aligned with the project goals:

- lightweight by default
- local-first
- easy to read and adapt
- useful for scientific ML workflows
- minimal infrastructure and minimal magic

## Good first contributions

- improve documentation and examples
- add a new toy scientific ML example
- improve summary/report formatting
- add tests for edge cases
- improve planning heuristics without making the system heavy

## Development setup

```bash
pip install -e .
pytest -q
```

## Style

- prefer simple Python over framework-heavy abstractions
- keep CLI behavior predictable
- avoid provider lock-in
- avoid adding infrastructure unless it clearly improves usability

## Pull requests

A good PR should explain:

- what problem it solves
- why the added complexity is worth it
- how it fits the workflow-first philosophy of the repo
