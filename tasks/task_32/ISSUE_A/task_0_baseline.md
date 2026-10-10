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

- [x] pytest installed
- [x] Full suite run on dev
- [x] Total test count recorded
- [x] All tests green (or pre-existing failures noted)

## Baseline Record

| Field | Value |
|---|---|
| Date | 2026-10-10 |
| Branch | feature/issue-redesign |
| Working tree | clean |
| Python | 3.14.7 |
| pytest | 9.1.1 |
| Tests collected | 1067 |
| Tests passed | 1067 |
| Tests failed | 0 |
| Duration | 75.30s |
| Pre-existing failures | None |

## Final Brief

Baseline established. The full test suite on `feature/issue-redesign` is green:
**1067 tests, 1067 passed, 0 failed** in 75.30s. pytest 9.1.1 was installed via
`pip install -e ".[dev]"`. No pre-existing failures. This is the reference point
for all subsequent Issue A tasks.
