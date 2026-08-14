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
  max_steps: 3
  step_timeout_s: 5
  test_timeout_s: 10
```

Validation checks that referenced files exist, visible and hidden test lists do
not overlap, the workspace directory exists, and `reward.type` is registered.

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
  "ts": "2026-08-14T12:00:00+00:00"
}
```

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
