"""Tests for Claude policy behavior using a fake SDK client."""

from __future__ import annotations

import os
from types import SimpleNamespace
from typing import Any

from taskforge.actions import Finish, ReadFile
from taskforge.env import Observation
from taskforge.policies.claude import ClaudePolicy, _load_dotenv, tool_schemas


class FakeMessages:
    """Fake Anthropic messages endpoint."""

    def __init__(self, responses: list[Any] | None = None, error: Exception | None = None) -> None:
        """Create a fake messages endpoint."""
        self.responses = responses or []
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        """Return the next fake response or raise the configured error."""
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.responses.pop(0)


class FakeClient:
    """Fake Anthropic client."""

    def __init__(self, messages: FakeMessages) -> None:
        """Create a fake client."""
        self.messages = messages


class RateLimitError(Exception):
    """Fake transient rate limit error."""


def _obs() -> Observation:
    return Observation(
        task_id="fix-retry-backoff",
        task_statement="Fix retry final exception propagation\n\nFix the retry helper.",
        workspace="/workspace",
        step=0,
        remaining_steps=3,
        last_output="",
    )


def _response(content: list[Any]) -> Any:
    return SimpleNamespace(
        content=content,
        usage=SimpleNamespace(input_tokens=10, output_tokens=5),
    )


def test_claude_tool_schemas_are_generated_from_action_models() -> None:
    """Claude tools use Pydantic action model JSON schemas."""
    schemas = tool_schemas()
    read_file = next(schema for schema in schemas if schema["name"] == "read_file")

    assert read_file["input_schema"] == ReadFile.model_json_schema()


def test_claude_malformed_reply_triggers_corrective_path() -> None:
    """A response without tool_use gets a corrective user turn before retrying."""
    messages = FakeMessages(
        [
            _response([{"type": "text", "text": "I will explain instead."}]),
            _response(
                [
                    {
                        "type": "tool_use",
                        "id": "toolu_1",
                        "name": "finish",
                        "input": {"type": "finish"},
                    }
                ]
            ),
        ]
    )
    policy = ClaudePolicy(client=FakeClient(messages), max_retries=2)

    action = policy.act(_obs())

    assert isinstance(action, Finish)
    assert any(
        message["content"] == "Please respond with exactly one TaskForge tool call."
        for message in policy.messages
    )
    assert messages.calls[0]["tools"] == tool_schemas()


def test_claude_repeated_failures_return_finish() -> None:
    """Repeated transient failures end cleanly with Finish."""
    policy = ClaudePolicy(
        client=FakeClient(FakeMessages(error=RateLimitError("slow down"))),
        max_retries=2,
    )

    action = policy.act(_obs())

    assert isinstance(action, Finish)


def test_claude_loads_api_key_from_dotenv(tmp_path, monkeypatch) -> None:
    """The Claude policy can load ANTHROPIC_API_KEY from a local .env file."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    (tmp_path / ".env").write_text('ANTHROPIC_API_KEY="test-key"\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    _load_dotenv()

    assert os.environ["ANTHROPIC_API_KEY"] == "test-key"
