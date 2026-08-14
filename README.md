# TaskForge

TaskForge is a Python framework for turning coding tasks into verifiable RL
environments: an agent edits an isolated workspace, hidden tests compute the
terminal reward, and every action is captured as a replayable trajectory. That
reward signal matters because it lets you compare policies, tune prompts, and
study failures without trusting self-reports from the model.

```text
task.yaml + workspace/
        |
        v
  TaskEnv.reset()  -> observation with task statement
        |
        v
 policy action: read, write, list, run visible tests, finish
        |
        v
  TaskEnv.step()   -> observation, reward 0 while running
        |
        v
 finish / limit / timeout
        |
        v
 hidden pytest grading -> terminal reward -> JSONL trajectory/report
```

## Task Format

A task lives in `tasks/<task-id>/`. The agent only receives `workspace/` and
visible tests. Hidden tests and the optional reference `solution/` stay outside
the normal episode.

```yaml
id: fix-retry-backoff
title: Fix retry final exception propagation
description: Re-raise the final exception after all retry attempts fail.
workspace: workspace
solution: solution
tests:
  visible: [tests/test_basic.py]
  hidden: [tests/test_grading.py]
reward:
  type: test_pass_ratio
  partial_credit: false
limits:
  max_steps: 25
  max_observation_chars: 4000
metadata:
  difficulty: easy
  tier: 1
  tags: [swallowed-exception, retry]
```

Authoring checklist:

1. The prompt is solvable from `workspace/` alone.
2. Starter code fails hidden tests before any edit.
3. Applying `solution/` makes hidden reward exactly `1.0`.
4. Visible tests also pass with `solution/`.
5. Hidden tests and solution files are absent from the initial workspace.
6. `metadata.difficulty`, `metadata.tier`, and `metadata.tags` are set for
   filtering and reporting.

## Results

These numbers come from the checked-in `report.md`: random ran 30 episodes
across the tier-1 pack; Claude ran 3 tier-1 episodes before `--max-cost-usd
0.10` stopped launching new work. Tier-2 tasks use multiple hidden tests and
fractional reward, so their mean reward tables are gradients, not directly
comparable with the older pass/fail-only numbers.

| Policy | Episodes | pass@1 | pass@3 | Mean Reward | Mean Steps | Cost |
|---|---:|---:|---:|---:|---:|---:|
| random | 30 | 0.000 | 0.000 | 0.000 | 5.23 | $0.000000 |
| claude | 3 | 1.000 | 1.000 | 1.000 | 7.00 | $0.170124 |

Tier 1 saturates: the available Claude tier-1 run has pass@1 `1.000`. Tier 2
does not: the full tier-2 Claude sweep in `runs/sweep-claude/sweep.json`
reaches pass@1 `0.800` at `max_steps=25`.

Stage-6 tier-2 step-budget curve:

| Max Steps | pass@1 | Mean Reward |
|---:|---:|---:|
| 3 | 0.000 | 0.133 |
| 5 | 0.600 | 0.600 |
| 25 | 0.800 | 0.933 |

The jump from 3 to 5 steps is the first point where agents have enough room to
inspect, edit, and run visible tests on several tier-2 tasks.

Example artifacts are committed under `examples/`:

- `examples/solved/fix-api-404-solved.jsonl` and `examples/solved/viewer.html`
- `examples/failed/fix-retry-backoff-failed.jsonl` and `examples/failed/viewer.html`

## Anti-Reward-Hacking

TaskForge assumes agents will try weird things, so the environment is defensive:

- Hidden tests are restored from the task source immediately before grading.
- `ReadFile` and `WriteFile` resolve through workspace confinement and reject
  `..`, escaped absolute paths, and symlinks that leave the workspace.
- `taskforge verify` checks no hidden test or solution file leaks into the
  initial workspace.
- Observations use the stable placeholder `/workspace`; host temp paths are kept
  internal and are not written to trajectories.
- Failure analysis tracks `attempted_test_edit`; the current report observed 0
  test-edit attempts.

## Quickstart

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"

.venv\Scripts\taskforge verify tasks --runner subprocess
.venv\Scripts\taskforge run fix-retry-backoff --policy scripted --verbose-trajectory
.venv\Scripts\taskforge eval --tasks tasks --policy random --n 3 --yes --out runs/random
.venv\Scripts\taskforge eval --tasks tasks --policy random --tier 2 --tag performance --n 1
.venv\Scripts\taskforge report runs/random --out report.md
.venv\Scripts\taskforge view examples/failed/fix-retry-backoff-failed.jsonl --out viewer.html
```

Claude policy:

```bash
$env:ANTHROPIC_API_KEY = "..."
.venv\Scripts\taskforge eval `
  --tasks tasks `
  --policy claude `
  --n 3 `
  --max-workers 2 `
  --temperature 0.7 `
  --yes `
  --max-cost-usd 1.00 `
  --out runs/claude
```

You can also put `ANTHROPIC_API_KEY=...` in a local `.env`; TaskForge loads it
without logging or persisting the secret.

Step-budget sweep:

```bash
.venv\Scripts\taskforge sweep `
  --tasks tasks `
  --policy claude `
  --max-steps 3,5,25 `
  --n 1 `
  --tier 2 `
  --max-cost-usd 1.00 `
  --out runs/sweep-tier2
```

`sweep` defaults to `--n 1` because Claude runs at `temperature=0` by default,
so extra samples usually repeat the same trajectory. Before any model call it
prints planned episodes per budget and projected cost using the measured
`$0.055` per episode rate. The sweep is resumable: completed
`(task, max_steps, seed)` cells in `sweep.json` are reused, and cells skipped by
the global cost cap are written as `not_run`.

## Action Space

Agents emit Pydantic-validated actions:

```json
{"type": "read_file", "path": "client.py"}
{"type": "write_file", "path": "client.py", "content": "..."}
{"type": "list_files", "path": "."}
{"type": "run_tests", "scope": "visible"}
{"type": "finish"}
```

`run_tests` rejects `scope: "hidden"`. Invalid filesystem actions consume one
step, increment `invalid_actions`, and return an error observation; genuine
framework failures are the ones marked `done_reason="error"`.

## Trajectory Schema

Trajectories are JSONL with `schema_version: "1.0"`. Observations are stored as
digests; `--verbose-trajectory` writes full observations to a side file next to
that episode's trajectory.

```json
{"schema_version":"1.0","record_type":"episode_start","task_id":"fix-api-404","step":0,"observation":{"digest":"...","side_file":"run.jsonl.observations.jsonl","truncated":false},"metadata":{"policy_name":"claude","seed":0,"temperature":0.7},"ts":"..."}
{"schema_version":"1.0","record_type":"step","task_id":"fix-api-404","step":1,"action":{"type":"write_file","path":"api.py","content":"..."},"reward":0.0,"done":false,"done_reason":null,"observation":{"digest":"...","side_file":"run.jsonl.observations.jsonl","truncated":false},"invalid_actions":0,"cumulative_cost_usd":0.0,"ts":"..."}
{"schema_version":"1.0","record_type":"episode_end","task_id":"fix-api-404","step":2,"terminal_reward":1.0,"done_reason":"finish","invalid_actions":0,"ts":"..."}
```

`taskforge replay <trajectory.jsonl>` re-executes recorded actions against a
fresh workspace and checks the same terminal reward.

## Reporting And Viewing

```bash
.venv\Scripts\taskforge report runs/random runs/claude --out report.md
.venv\Scripts\taskforge view runs/random/fix-retry-backoff-0.jsonl --out viewer.html
```

The Markdown report includes headline metrics, breakdowns by difficulty and
tier, task tag breakdowns, per-task mean fractional reward for random and
Claude, failure-tag distribution, and cost summary. Sweep reports include pass@1
per step budget plus an ASCII sparkline. The HTML viewer is a single
self-contained file with inline CSS and JS; it opens directly from the
filesystem.

## What The Benchmark Does Not Measure

The current tier-2 sweep does not prove robust decimal reasoning. The unsolved
`max_steps=25` task is `chain-of-three`: Claude changed cents conversion to
`round(float(price) * 100)`, earning terminal reward `0.6666666666666666`, but
failed `tests/test_grading.py::test_rounds_half_cent_up_before_discount`
because the task requires decimal half-up rounding for values such as `1.005`.

The random tier-2 baseline also exposes a signal weakness in `perf-regression`.
The pristine workspace already passes
`tests/test_grading.py::test_preserves_left_order_and_deduplicates` and
`tests/test_grading.py::test_requires_active_on_both_sides`; only
`tests/test_grading.py::test_large_input_runtime` fails. That means its hidden
suite gives reward `0.6666666666666666` before the actual performance fix.

## Limitations

- The task pack is intentionally small: 15 Python tasks, not a benchmark.
- Claude numbers depend on model version, temperature, API availability, and
  budget guardrails.
- DockerRunner is implemented but not yet tested on Windows Docker Desktop.
- Sandboxing is process/container level, not a full OS security boundary.
- Failure classification is heuristic and trajectory-only by design.
