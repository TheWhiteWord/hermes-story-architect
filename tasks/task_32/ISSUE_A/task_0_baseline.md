# Task 0: Baseline — Run the test suite on dev and record the baseline

## Goal

Establish the green baseline before any Issue A work begins. Every subsequent task
leaves the suite green, so this is the reference point.

## Work

1. Ensure pytest is installed (`pip install pytest` or check `pyproject.toml`).
2. Run the full test suite on the dev branch: `python -m pytest tests/ -v`
3. Record the total test count and confirm all pass.
4. If any test is already red, note it — it is a pre-existing failure, not caused
   by Issue A.

## Checklist

- [ ] pytest installed
- [ ] Full suite run on dev
- [ ] Total test count recorded
- [ ] All tests green (or pre-existing failures noted)
