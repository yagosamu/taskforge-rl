"""Tests for report generation and trajectory viewer."""

from __future__ import annotations

import json
import re
from pathlib import Path

from taskforge.metrics import EpisodeResult, EvalReport
from taskforge.reporting import generate_report_markdown
from taskforge.trajectory import (
    EpisodeEndRecord,
    EpisodeStartRecord,
    StepRecord,
    TrajectoryObservation,
)
from taskforge.viewer import write_viewer


def test_report_generation_is_deterministic(tmp_path: Path) -> None:
    """Markdown reports are stable for fixed inputs."""
    report_path = tmp_path / "report.json"
    report = EvalReport(
        policy_name="random",
        n_samples=1,
        max_workers=1,
        results=[
            EpisodeResult(
                task_id="fix-retry-backoff",
                policy_name="random",
                seed=0,
                reward=0.0,
                steps=2,
                done_reason="finish",
                trajectory_path=None,
            )
        ],
        mean_reward=0.0,
        mean_steps=2.0,
        mean_cost_usd=0.0,
        total_cost_usd=0.0,
        done_reasons={"finish": 1},
    )
    report_path.write_text(report.model_dump_json(), encoding="utf-8")

    first = generate_report_markdown([report_path])
    second = generate_report_markdown([report_path])

    assert first == second
    assert "| random |" in first
    assert "## Cost Summary" in first


def test_viewer_generates_self_contained_html(tmp_path: Path) -> None:
    """The viewer writes a single HTML file with inline data and no CDN."""
    trajectory = tmp_path / "episode.jsonl"
    _write_minimal_trajectory(trajectory)
    out = tmp_path / "viewer.html"

    write_viewer(trajectory, out)

    html = out.read_text(encoding="utf-8")
    assert "<!doctype html>" in html
    assert "https://" not in html
    assert "type=\"application/json\"" in html
    assert "TaskForge Trajectory Viewer" in html
    match = re.search(
        r'<script type="application/json" id="data">(.*?)</script>',
        html,
        re.DOTALL,
    )
    assert match is not None
    payload = json.loads(match.group(1))
    assert payload["trajectory"] == "episode.jsonl"
    assert payload["steps"][0]["cumulative_cost_usd"] == 0.0
    assert "Cost:" in html


def _write_minimal_trajectory(path: Path) -> None:
    obs = TrajectoryObservation(digest="digest", truncated=False)
    records = [
        EpisodeStartRecord(
            run_id="run",
            task_id="fix-retry-backoff",
            step=0,
            observation=obs,
            ts="0",
        ),
        StepRecord(
            run_id="run",
            task_id="fix-retry-backoff",
            step=1,
            action={"type": "finish"},
            reward=0.0,
            done=True,
            done_reason="finish",
            observation=obs,
            ts="1",
        ),
        EpisodeEndRecord(
            run_id="run",
            task_id="fix-retry-backoff",
            step=1,
            terminal_reward=0.0,
            done_reason="finish",
            ts="end",
        ),
    ]
    path.write_text("\n".join(record.model_dump_json() for record in records), encoding="utf-8")
