# TaskForge Evaluation Report

## Stage 6 Step-Budget Sweep

Source: `runs/sweep-claude/sweep.json`.

| Max Steps | Completed | pass@1 | Mean Reward | Total Cost |
|---:|---:|---:|---:|---:|
| 3 | 5/5 | 0.000 | 0.133 | $0.085200 |
| 5 | 5/5 | 0.600 | 0.600 | $0.181956 |
| 25 | 5/5 | 0.800 | 0.933 | $0.334824 |

The tier-2 random baseline in `runs/sweep-random/sweep.json` has pass@1 `0.000`
and mean reward `0.133` at max steps `3`, `5`, and `25`.

## Stage 6 Unsolved Cell

At `max_steps=25`, Claude solved 4/5 tier-2 tasks. The unsolved task was
`chain-of-three`, with terminal reward `0.6666666666666666`, `9` steps,
done reason `finish`, and cost `$0.08300700000000001`.

Hidden test outcomes after replaying the recorded actions offline:

| Hidden Test | Outcome |
|---|---|
| `tests/test_grading.py::test_rounds_half_cent_up_before_discount` | failed |
| `tests/test_grading.py::test_rounds_each_unit_before_multiplying` | passed |
| `tests/test_grading.py::test_discount_uses_rounded_subtotal` | passed |

The action sequence was: list files, read `module_a.py`, read `module_b.py`,
read `module_c.py`, read `tests/test_basic.py`, run visible tests, write
`module_a.py`, run visible tests, finish. The written fix used
`round(float(price) * 100)`, which did not implement decimal half-up rounding
for `1.005`; that is why the half-cent hidden case stayed red.

## Stage 6 Random Baseline Anomaly

The pristine `perf-regression` workspace receives reward `0.6666666666666666`.
It passes two hidden tests before any meaningful fix:

| Hidden Test | Pristine Outcome |
|---|---|
| `tests/test_grading.py::test_preserves_left_order_and_deduplicates` | passed |
| `tests/test_grading.py::test_requires_active_on_both_sides` | passed |
| `tests/test_grading.py::test_large_input_runtime` | failed |

This weakens the signal for that task: the hidden suite is mostly checking
functional behaviour the starter implementation already satisfies, while the
actual required fix is isolated to the runtime-bounded test.

## Headline

| Policy | pass@1 | pass@3 | Mean Reward | Mean Steps | Mean Cost |
|---|---:|---:|---:|---:|---:|
| claude | 1.000 | 1.000 | 1.000 | 7.00 | $0.056708 |
| random | 0.000 | 0.000 | 0.000 | 5.23 | $0.000000 |

## By Difficulty

| Difficulty | Policy | Episodes | Mean Reward | pass@1 |
|---|---|---:|---:|---:|
| easy | random | 9 | 0.000 | 0.000 |
| hard | claude | 1 | 1.000 | 1.000 |
| hard | random | 12 | 0.000 | 0.000 |
| medium | claude | 2 | 1.000 | 1.000 |
| medium | random | 9 | 0.000 | 0.000 |

## By Tier

| Tier | Policy | Episodes | Mean Reward | pass@1 |
|---|---|---:|---:|---:|
| 1 | claude | 3 | 1.000 | 1.000 |
| 1 | random | 30 | 0.000 | 0.000 |

## By Tag

| Tag | Policy | Episodes | Mean Reward |
|---|---|---:|---:|
| api | claude | 1 | 1.000 |
| api | random | 3 | 0.000 |
| asyncio | claude | 1 | 1.000 |
| asyncio | random | 3 | 0.000 |
| boundary | random | 3 | 0.000 |
| cache | claude | 1 | 1.000 |
| cache | random | 3 | 0.000 |
| data-migration | random | 3 | 0.000 |
| docstring | random | 3 | 0.000 |
| generalization | random | 3 | 0.000 |
| helper-extraction | claude | 1 | 1.000 |
| helper-extraction | random | 3 | 0.000 |
| multi-file | random | 3 | 0.000 |
| off-by-one | random | 3 | 0.000 |
| pagination | random | 3 | 0.000 |
| performance | random | 3 | 0.000 |
| pricing | random | 3 | 0.000 |
| race-condition | claude | 1 | 1.000 |
| race-condition | random | 3 | 0.000 |
| refactor | claude | 1 | 1.000 |
| refactor | random | 3 | 0.000 |
| retry | random | 3 | 0.000 |
| reward-trap | random | 3 | 0.000 |
| runtime-bounded | random | 3 | 0.000 |
| status-code | claude | 1 | 1.000 |
| status-code | random | 3 | 0.000 |
| string-processing | random | 3 | 0.000 |
| swallowed-exception | random | 3 | 0.000 |

## Per Task

| Task | Tier | Difficulty | Random Mean Reward | Claude Mean Reward |
|---|---:|---|---:|---:|
| chain-of-three | 2 | hard | n/a | n/a |
| coordinated-edit | 2 | hard | n/a | n/a |
| extract-discount-helper | 1 | medium | 0.000 | 1.000 |
| fix-api-404 | 1 | medium | 0.000 | 1.000 |
| fix-async-cache-race | 1 | hard | 0.000 | 1.000 |
| fix-migration-boundary | 1 | hard | 0.000 | n/a |
| fix-multifile-tax | 1 | hard | 0.000 | n/a |
| fix-pagination | 1 | easy | 0.000 | n/a |
| fix-retry-backoff | 1 | easy | 0.000 | n/a |
| implement-slugify | 1 | easy | 0.000 | n/a |
| optimize-common-ids | 1 | hard | 0.000 | n/a |
| perf-regression | 2 | hard | n/a | n/a |
| preserve-contract | 2 | hard | n/a | n/a |
| reward-trap-normalize | 1 | medium | 0.000 | n/a |
| stateful-second-call | 2 | hard | n/a | n/a |

## Failure Tags

| Failure Tag | Count |
|---|---:|
| gave_up_early | 30 |
| never_tested | 16 |
| wrong_file | 14 |
| fell_for_trap | 3 |
| unproductive_loop | 3 |

## Cost Summary

- Total cost: `$0.170124`
- Mean per episode: `$0.005155`
- Mean per solved episode: `$0.056708`
