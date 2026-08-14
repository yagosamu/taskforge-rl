# TaskForge Evaluation Report

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
