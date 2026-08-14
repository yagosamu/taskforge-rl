# TaskForge Stage 6 Report

## Claude Step-Budget Curve

Source run: `runs/sweep-claude-v2/`.

| Max Steps | Completed | pass@1 | Mean Reward | Curve |
|---:|---:|---:|---:|---|
| 3 | 5/5 | 0.000 | 0.000 | [----------] |
| 5 | 5/5 | 0.600 | 0.600 | [######----] |
| 25 | 5/5 | 0.800 | 0.933 | [########--] |

The transition from 3 to 5 steps is the first point where Claude solves any
tier-2 tasks: pass@1 moves from `0.000` to `0.600`.

## Random Baseline

Source run: `runs/sweep-random-v2/`.

| Max Steps | Completed | pass@1 | Mean Reward | Curve |
|---:|---:|---:|---:|---|
| 3 | 5/5 | 0.000 | 0.000 | [----------] |
| 5 | 5/5 | 0.000 | 0.000 | [----------] |
| 25 | 5/5 | 0.000 | 0.000 | [----------] |

The random baseline now reports `0.000` mean reward at every budget. It
previously read `0.133` because one task granted partial credit on the pristine
workspace; that stale tier-2 sweep is not used in this report.

## Unsolved Task At 25 Steps

Source run: `runs/sweep-claude-v2/`.

At `max_steps=25`, `chain-of-three` was the only unsolved task. Its terminal
reward was `0.6666666666666666`, with done reason `finish`.

Hidden test outcomes after replaying the recorded actions offline:

| Hidden Test | Outcome |
|---|---|
| `tests/test_grading.py::test_rounds_half_cent_up_before_discount` | failed |
| `tests/test_grading.py::test_rounds_each_unit_before_multiplying` | passed |
| `tests/test_grading.py::test_discount_uses_rounded_subtotal` | passed |

The agent fixed `module_a.py` with `round(float(price) * 100)`. That passes the
unit-before-multiplication and rounded-subtotal cases, but it does not implement
decimal half-up rounding for `1.005`, so the half-up hidden test remains red.
