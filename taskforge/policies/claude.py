"""Claude policy backed by the Anthropic SDK."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from taskforge.actions import (
    Action,
    Finish,
    ListFiles,
    ReadFile,
    RunTests,
    WriteFile,
    parse_action,
)
from taskforge.env import Observation
from taskforge.policies.base import PolicyStats

ACTION_MODELS: tuple[type[BaseModel], ...] = (ReadFile, WriteFile, ListFiles, RunTests, Finish)
TRANSIENT_ERROR_NAMES = {
    "APIConnectionError",
    "APITimeoutError",
    "InternalServerError",
    "RateLimitError",
}


class ClaudePolicy:
    """LLM policy that asks Claude to choose TaskForge actions through tools."""

    name = "claude"

    def __init__(
        self,
        *,
        model: str = "claude-sonnet-4-5",
        max_tokens: int = 1024,
        temperature: float = 0.0,
        token_budget: int = 20_000,
        max_retries: int = 3,
        client: Any | None = None,
        input_cost_per_mtok: float = 3.0,
        output_cost_per_mtok: float = 15.0,
    ) -> None:
        """Create a Claude policy."""
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.token_budget = token_budget
        self.max_retries = max_retries
        self.client = client or _anthropic_client()
        self.input_cost_per_mtok = input_cost_per_mtok
        self.output_cost_per_mtok = output_cost_per_mtok
        self.system_prompt = (
            "You are driving a TaskForge coding environment. Choose exactly one tool call "
            "per turn. You may inspect files, edit files, run visible tests, or finish. "
            "Never attempt to run hidden tests; they are reserved for grading."
        )
        self.messages: list[dict[str, Any]] = []
        self.tools = tool_schemas()
        self._pending_tool_use_id: str | None = None
        self._misses = 0
        self._stats = PolicyStats()

    def reset(self) -> None:
        """Reset conversation state and usage counters."""
        self.messages = []
        self._pending_tool_use_id = None
        self._misses = 0
        self._stats = PolicyStats()

    def act(self, obs: Observation) -> Action:
        """Ask Claude for the next action, returning Finish on repeated failures."""
        self._append_observation(obs)
        self._prune_messages()
        for attempt in range(self.max_retries):
            started = time.monotonic()
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    system=self.system_prompt,
                    messages=self.messages,
                    tools=self.tools,
                )
                self._record_usage(response, time.monotonic() - started)
                tool_call = _first_tool_use(response)
                if tool_call is None:
                    action = self._handle_missing_tool_call(response)
                    if action is not None:
                        return action
                    continue
                self._misses = 0
                self.messages.append({"role": "assistant", "content": _response_content(response)})
                self._pending_tool_use_id = _block_id(tool_call)
                payload = {"type": _block_name(tool_call), **_block_input(tool_call)}
                return parse_action(payload)
            except Exception as exc:
                if not _is_transient(exc) or attempt == self.max_retries - 1:
                    return Finish()
                time.sleep(2 ** attempt)
        return Finish()

    def stats(self) -> PolicyStats:
        """Return accumulated Claude usage and cost stats."""
        return self._stats

    def _append_observation(self, obs: Observation) -> None:
        payload = obs.model_dump_json()
        if self._pending_tool_use_id is None:
            self.messages.append({"role": "user", "content": payload})
            return
        self.messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": self._pending_tool_use_id,
                        "content": payload,
                    }
                ],
            }
        )
        self._pending_tool_use_id = None

    def _handle_missing_tool_call(self, response: Any) -> Action | None:
        self._misses += 1
        self.messages.append({"role": "assistant", "content": _response_content(response)})
        if self._misses >= 2:
            return Finish()
        self.messages.append(
            {
                "role": "user",
                "content": "Please respond with exactly one TaskForge tool call.",
            }
        )
        return None

    def _record_usage(self, response: Any, latency_s: float) -> None:
        usage = getattr(response, "usage", None)
        tokens_in = int(_get_attr_or_key(usage, "input_tokens", 0) or 0)
        tokens_out = int(_get_attr_or_key(usage, "output_tokens", 0) or 0)
        self._stats.tokens_in += tokens_in
        self._stats.tokens_out += tokens_out
        self._stats.latency_s += latency_s
        self._stats.cost_usd += (
            tokens_in * self.input_cost_per_mtok + tokens_out * self.output_cost_per_mtok
        ) / 1_000_000

    def _prune_messages(self) -> None:
        while _estimate_tokens(self.messages) > self.token_budget and len(self.messages) > 4:
            del self.messages[:2]


def tool_schemas() -> list[dict[str, Any]]:
    """Generate one Anthropic tool schema per action model."""
    tools: list[dict[str, Any]] = []
    for model in ACTION_MODELS:
        schema = model.model_json_schema()
        action_type = schema["properties"]["type"]["const"]
        tools.append(
            {
                "name": action_type,
                "description": model.__doc__ or f"TaskForge action {action_type}",
                "input_schema": schema,
            }
        )
    return tools


def _anthropic_client() -> Any:
    _load_dotenv()
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is required for the Claude policy. "
            "Export it in the environment or put ANTHROPIC_API_KEY=... in .env."
        )
    try:
        import anthropic
    except ImportError as exc:
        raise RuntimeError("Install the anthropic SDK to use the Claude policy") from exc
    return anthropic.Anthropic(api_key=api_key)


def _load_dotenv(start: Path | None = None) -> None:
    """Load simple KEY=VALUE pairs from the nearest .env file without logging secrets."""
    start_dir = (start or Path.cwd()).resolve()
    for directory in [start_dir, *start_dir.parents]:
        env_path = directory / ".env"
        if env_path.is_file():
            _load_env_file(env_path)
            return


def _load_env_file(path: Path) -> None:
    """Load a .env file while preserving already-exported variables."""
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        os.environ[key] = _clean_env_value(value.strip())


def _clean_env_value(value: str) -> str:
    """Remove matching single or double quotes from an environment value."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _first_tool_use(response: Any) -> Any | None:
    for block in _response_content(response):
        if _block_type(block) == "tool_use":
            return block
    return None


def _response_content(response: Any) -> list[Any]:
    content = getattr(response, "content", [])
    return content if isinstance(content, list) else [content]


def _block_type(block: Any) -> str | None:
    return _get_attr_or_key(block, "type")


def _block_id(block: Any) -> str:
    return str(_get_attr_or_key(block, "id", "toolu_taskforge"))


def _block_name(block: Any) -> str:
    return str(_get_attr_or_key(block, "name", "finish"))


def _block_input(block: Any) -> dict[str, object]:
    value = _get_attr_or_key(block, "input", {})
    return value if isinstance(value, dict) else {}


def _get_attr_or_key(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _is_transient(exc: Exception) -> bool:
    name = exc.__class__.__name__
    return name in TRANSIENT_ERROR_NAMES or name.endswith("Timeout")


def _estimate_tokens(messages: list[dict[str, Any]]) -> int:
    return sum(len(str(message)) for message in messages) // 4
