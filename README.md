# TaskForge

TaskForge is a small Python framework for defining and running verifiable RL-style
coding tasks. This first stage runs a single task end to end and produces a
reward from hidden pytest tests. There is no LLM, agent harness, Docker runner,
or UI yet.

## Install

```bash
python -m pip install -e ".[dev]"
```

TaskForge targets Python 3.11+ and keeps runtime dependencies minimal:
`pydantic v2`, `pyyaml`, and `typer`. Tests use `pytest`, and linting uses
`ruff`.

## Task Format

A task lives in `tasks/<task-id>/` and contains a `task.yaml`, a source
`workspace/`, and test files.

```yaml
id: fix-retry-backoff
title: Fix retry final exception propagation
description: The coding-agent-facing task description.
workspace: workspace
tests:
  visible:
    - tests/test_basic.py
  hidden:
    - tests/test_grading.py
reward:
  type: test_pass_ratio
  partial_credit: false
budget:
  step_timeout_s: 5
  test_timeout_s: 10
limits:
  max_observation_chars: 4000
  max_steps: 25
```

Validation checks that referenced files exist, visible and hidden test lists do
not overlap, the workspace directory exists, and `reward.type` is registered.
The effective step budget is `--max-steps` when explicitly passed; otherwise it
comes from the task's `limits.max_steps`.

At runtime, TaskForge copies the workspace and tests into a temporary directory.
Hidden tests are restored from the original task definition immediately before
grading, so modifying hidden tests inside the temporary workspace does not affect
the reward.

## Example

The included `fix-retry-backoff` task contains a broken `retry()` helper. Visible
tests cover only the happy path and pass before the fix. Hidden tests assert that
the final exception is re-raised after all attempts fail, so the initial reward
is `0.0`.

Validate tasks:

```bash
taskforge validate tasks
```

Inspect a task:

```bash
taskforge inspect fix-retry-backoff
```

Run the scripted policy, which runs visible tests and then finishes:

```bash
taskforge run fix-retry-backoff --policy scripted
```

`taskforge run` always writes a trajectory. By default it uses
`runs/<timestamp>/<task_id>-0.jsonl`; pass `--trajectory path/to/run.jsonl` to
choose the file explicitly.

Run framework tests:

```bash
python -m pytest
python -m ruff check .
```

## Action Space

Stage 2 adds a Pydantic discriminated union in `taskforge/actions.py`. Agents
should send dictionaries with a `type` field and parse them through
`parse_action(data)`.

Supported actions:

```json
{"type": "read_file", "path": "client.py"}
{"type": "write_file", "path": "client.py", "content": "..."}
{"type": "list_files", "path": "."}
{"type": "run_tests", "scope": "visible"}
{"type": "finish"}
```

`run_tests` only allows `scope: "visible"`. `scope: "hidden"` is rejected during
action parsing because hidden tests are reserved for grading. `ReadFile` and
`WriteFile` resolve paths through `resolve_in_workspace()`, which rejects `..`,
absolute paths outside the workspace, and symlinks that resolve outside the
workspace.

Observation text is truncated by `taskforge/truncation.py` using the task limit
`limits.max_observation_chars`, which defaults to `4000`. `Observation.truncated`
is set when any observation field was shortened.

## Runners

`taskforge run` accepts:

```bash
taskforge run fix-retry-backoff --runner subprocess
taskforge run fix-retry-backoff --runner docker
```

`DockerRunner` uses Docker CLI with `--network none`, `--memory 512m`,
`--cpus 1`, a non-root user, a read-only container filesystem, and the workspace
bind-mounted at `/workspace`. If Docker is not available, it raises a clear error
telling you to use `--runner subprocess`.

## Trajectory Schema

Versioned trajectories are JSONL files written by `taskforge/trajectory.py`.
Every record has `schema_version: "1.0"`. Observations are stored by SHA-256
digest, with an optional side file containing full observation payloads when
`--verbose-trajectory` is used.

Write a trajectory:

```bash
taskforge run fix-retry-backoff --trajectory run.jsonl --verbose-trajectory
```

Read, summarize, and replay:

```bash
taskforge stats run.jsonl
taskforge replay run.jsonl
```

Record examples:

```json
{
  "schema_version": "1.0",
  "record_type": "episode_start",
  "run_id": "7d6a...",
  "task_id": "fix-retry-backoff",
  "step": 0,
  "observation": {
    "digest": "sha256...",
    "side_file": "run.jsonl.observations.jsonl",
    "truncated": false
  },
  "metadata": {
    "policy_name": "claude",
    "seed": 0,
    "temperature": 0.7
  },
  "ts": "2026-08-14T12:00:00+00:00"
}
```

## Policy Interface

Stage 3 adds policy-driven evaluation. A policy implements
`taskforge.policies.base.Policy`:

```python
class Policy(Protocol):
    name: str

    def reset(self) -> None: ...
    def act(self, obs: Observation) -> Action: ...
    def stats(self) -> PolicyStats: ...
```

Built-in policies:

```text
scripted  runs visible tests once, then finishes
random    seeded baseline that samples valid non-hidden actions
claude    Anthropic-backed tool-using policy
```

The Claude policy reads `ANTHROPIC_API_KEY` from the environment, never logs or
persists it, and generates tool schemas directly from the Pydantic action models.
It keeps conversation state, retries transient API failures with exponential
backoff, records token/latency/cost stats, and returns `Finish()` after repeated
SDK failures or malformed model replies.

## Evaluation

Run a parallel evaluation:

```bash
taskforge eval \
  --tasks tasks/ \
  --policy claude \
  --n 3 \
  --max-workers 4 \
  --runner subprocess \
  --out runs/eval-scripted/ \
  --verbose-trajectory \
  --max-steps 25 \
  --temperature 0.7
```

Omit `--max-steps` to use each task's own configured step budget.

Use Claude:

```bash
$env:ANTHROPIC_API_KEY = "..."
taskforge eval --tasks tasks/ --policy claude --n 3 --max-workers 2 --yes --max-cost-usd 1.00
```

Alternatively, put the key in a local `.env` file:

```dotenv
ANTHROPIC_API_KEY=...
```

Before an eval starts, TaskForge prints the planned episode count and an
estimated cost range. Runs above the confirmation threshold require `--yes`.
`--max-cost-usd` stops launching new episodes once accumulated reported cost
crosses the limit; already-running episodes are allowed to finish.

Each episode receives its own workspace, policy instance, runner, and trajectory
file. A failing episode is captured as `done_reason="error"` and does not abort
the rest of the run.

The output directory contains `report.json` and one trajectory JSONL per
episode. With `--verbose-trajectory`, each episode also writes its full
observations to a side file next to its trajectory, for example
`fix-retry-backoff-0.jsonl.observations.jsonl`. Parallel runs use one side file
per episode and do not share observation handles. The trajectory header records
the policy name, seed, and policy temperature when present, so sampled runs can
be interpreted later. Render a saved report with:

```bash
taskforge report runs/eval-scripted/
```

Report columns:

```text
TASK    task id
SEED    per-episode seed
REWARD  terminal reward
STEPS   environment steps
DONE    done_reason, such as finish, step_limit, timeout, or error
COST    policy-reported USD cost
ERROR   captured episode error, if any
```

The summary includes mean reward, mean steps, total cost, and the done-reason
distribution. `taskforge.metrics.pass_at_k(n, c, k)` provides the standard
unbiased pass@k estimator for downstream reporting.

```json
{
  "schema_version": "1.0",
  "record_type": "step",
  "run_id": "7d6a...",
  "task_id": "fix-retry-backoff",
  "step": 1,
  "action": {"type": "run_tests", "scope": "visible"},
  "reward": 0.0,
  "done": false,
  "done_reason": null,
  "observation": {
    "digest": "sha256...",
    "side_file": "run.jsonl.observations.jsonl",
    "truncated": false
  },
  "ts": "2026-08-14T12:00:01+00:00"
}
```

```json
{
  "schema_version": "1.0",
  "record_type": "episode_end",
  "run_id": "7d6a...",
  "task_id": "fix-retry-backoff",
  "step": 2,
  "terminal_reward": 0.0,
  "done_reason": "finish",
  "ts": "2026-08-14T12:00:02+00:00"
}
```
