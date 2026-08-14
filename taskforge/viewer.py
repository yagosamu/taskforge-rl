"""Self-contained trajectory HTML viewer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from taskforge.analysis import classify_episode
from taskforge.trajectory import EpisodeEndRecord, EpisodeStartRecord, StepRecord, read_trajectory


def write_viewer(trajectory_path: Path, out_path: Path) -> None:
    """Write a self-contained HTML viewer for a trajectory."""
    episode = read_trajectory(trajectory_path)
    observations = _read_side_observations(trajectory_path)
    tags = [tag.value for tag in classify_episode(episode)]
    terminal = next(
        (record for record in episode.records if isinstance(record, EpisodeEndRecord)),
        None,
    )
    solved = bool(terminal and terminal.terminal_reward >= 1.0)
    steps = [record for record in episode.records if isinstance(record, StepRecord)]
    payload = {
        "trajectory": trajectory_path.name,
        "tags": tags,
        "solved": solved,
        "terminal_reward": terminal.terminal_reward if terminal else None,
        "done_reason": terminal.done_reason if terminal else None,
        "start": next(
            (
                r.model_dump(mode="json")
                for r in episode.records
                if isinstance(r, EpisodeStartRecord)
            ),
            {},
        ),
        "steps": [
            {
                "step": step.step,
                "action": step.action,
                "reward": step.reward,
                "done": step.done,
                "done_reason": step.done_reason,
                "invalid_actions": step.invalid_actions,
                "cumulative_cost_usd": step.cumulative_cost_usd,
                "observation": observations.get(step.step, {"digest": step.observation.digest}),
            }
            for step in steps
        ],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(_html(payload), encoding="utf-8")


def _read_side_observations(trajectory_path: Path) -> dict[int, dict[str, Any]]:
    side_path = trajectory_path.with_suffix(trajectory_path.suffix + ".observations.jsonl")
    if not side_path.exists():
        return {}
    observations: dict[int, dict[str, Any]] = {}
    for line in side_path.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        observations[int(record["step"])] = record["observation"]
    return observations


def _html(payload: dict[str, Any]) -> str:
    escaped = _script_safe_json(payload)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>TaskForge Trajectory Viewer</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 2rem; background: #f8fafc; color: #111827; }}
.header {{ padding: 1rem; border-radius: 8px; background: white; border-left: 8px solid #ef4444; }}
.header.solved {{ border-left-color: #22c55e; }}
.tag {{ display: inline-block; padding: .15rem .45rem; margin: .15rem;
  border-radius: 999px; background: #e5e7eb; }}
.step {{ margin: 1rem 0; padding: 1rem; background: white;
  border-radius: 8px; border: 1px solid #e5e7eb; }}
pre {{ white-space: pre-wrap; overflow-wrap: anywhere; background: #f3f4f6;
  padding: .75rem; border-radius: 6px; }}
</style>
</head>
<body>
<div id="app"></div>
<script type="application/json" id="data">{escaped}</script>
<script>
const data = JSON.parse(document.getElementById('data').textContent);
const app = document.getElementById('app');
const header = document.createElement('section');
header.className = 'header' + (data.solved ? ' solved' : '');
header.innerHTML = `<h1>${{data.trajectory}}</h1>
<p>Reward: ${{data.terminal_reward}} · Done: ${{data.done_reason}}</p>
<p>${{data.tags.map(t => `<span class="tag">${{t}}</span>`).join('')
  || '<span class="tag">solved</span>'}}</p>`;
app.appendChild(header);
for (const step of data.steps) {{
  const el = document.createElement('section');
  el.className = 'step';
  el.innerHTML = `<h2>Step ${{step.step}}</h2>
  <p>Reward: ${{step.reward}} · Cost: $${{step.cumulative_cost_usd.toFixed(6)}}
  · Invalid actions: ${{step.invalid_actions}}</p>
  <h3>Action</h3><pre>${{JSON.stringify(step.action, null, 2)}}</pre>
  <h3>Observation</h3><pre>${{JSON.stringify(step.observation, null, 2)}}</pre>`;
  app.appendChild(el);
}}
</script>
</body>
</html>
"""


def _script_safe_json(payload: dict[str, Any]) -> str:
    data = json.dumps(payload, sort_keys=True)
    return (
        data.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )
