"""Agent backends: the one place the harness talks to a model.

CodexBackend runs each agent as a Codex session (`codex exec`, then
`codex exec resume` every round) on the swarm's own Codex login.
A model named `adaption/<id>` runs through the same Codex sessions on Adaption's
Responses API instead, paid with Adaption credits (see `model_args`).
ScriptedBackend runs a Python policy against the same tool server, for tests.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable

import httpx

from .world import Agent

# Plan exhausted: stop the run and resume later.
USAGE_LIMIT_RE = re.compile(r"usage limit|hit your limit|quota", re.I)
# Short burst limits and dropped connections: wait and retry the same turn. A timeout is not
# transient: it ends the turn, so one slow agent can't hold up the round (issue #2).
TRANSIENT_RE = re.compile(r"rate limit|too many requests|\b429\b|\b403\b|forbidden|reconnecting|"
                          r"stream disconnected|overloaded|\b50[234]\b", re.I)
RETRY_DELAYS = (30, 90, 270)

# Codex switches that strip user/global instructions and built-in tools, so the
# agent can only act through the swarm's tool server.
CODEX_ISOLATION = [
    "--skip-git-repo-check", "--ignore-user-config", "--ignore-rules",
    "-c", "include_skills_usage_instructions=false",
    "-c", "include_plugin_usage_instructions=false",
    "-c", "include_apps_instructions=false",
    "-c", "include_apps_usage_instructions=false",
    "-c", "include_permissions_instructions=false",
    "-c", "include_collaboration_mode_instructions=false",
    "-c", "include_environment_context=false",
    "-c", "skills.bundled.enabled=false",
    "-c", "project_doc_max_bytes=0",
    "-c", 'web_search="disabled"',
    "-c", 'sandbox_mode="read-only"',
    "-c", 'approval_policy="never"',
    *[x for f in ("shell_tool", "unified_exec", "multi_agent", "multi_agent_v2", "apps",
                  "plugins", "browser_use", "computer_use", "goals", "image_generation", "view_image",
                  "memories")
      for x in ("--disable", f)],
]


# Adaption serves open-weight models (DeepSeek, Gemma, Qwen, GLM) on an OpenAI-style Responses API,
# so Codex reaches it as a custom model provider. The key comes from ADAPTION_API_KEY, else this file.
ADAPTION_PREFIX = "adaption/"
ADAPTION_KEY_FILE = Path.home() / ".config" / "adaption" / "api_key"
ADAPTION_PROVIDER = [
    "-c", "model_provider=adaption",
    "-c", 'model_providers.adaption={name="Adaption",base_url="https://api.prod.adaptionlabs.ai/api/v1",'
          'env_key="ADAPTION_API_KEY",wire_api="responses"}',
]


def is_adaption(model: str) -> bool:
    return model.startswith(ADAPTION_PREFIX)


def model_args(model: str) -> list[str]:
    """`-m` for a model, plus the provider switch for `adaption/<id>`."""
    if is_adaption(model):
        return ["-m", model.removeprefix(ADAPTION_PREFIX), *ADAPTION_PROVIDER]
    return ["-m", model]


def adaption_key() -> str:
    key = os.environ.get("ADAPTION_API_KEY", "").strip()
    if not key and ADAPTION_KEY_FILE.exists():
        key = ADAPTION_KEY_FILE.read_text().strip()
    if not key:
        raise RuntimeError(f"no Adaption key: set ADAPTION_API_KEY or write the key to {ADAPTION_KEY_FILE}")
    return key


class UsageLimit(Exception):
    pass


@dataclass
class TurnResult:
    session_id: str | None = None
    messages: list[str] = field(default_factory=list)
    usage: dict = field(default_factory=dict)
    error: str | None = None  # None | "usage_limit" | other text
    raw_error: str | None = None  # Codex's own error text
    attempts: int = 1
    builtin_tool_events: list[dict] = field(default_factory=list)  # any non-MCP tool use (should be empty)


def toml_str(s: str) -> str:
    return json.dumps(s)  # JSON string literals are valid TOML basic strings


def codex_env(swarm_home: str, token: str | None = None, model: str = "") -> dict:
    """Environment for a Codex subprocess. Only an `adaption/<id>` model gets the Adaption key."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("CODEX_") and k != "ADAPTION_API_KEY"}
    env["HOME"] = swarm_home
    if token:
        env["SWARM_AGENT_TOKEN"] = token
    if is_adaption(model):
        env["ADAPTION_API_KEY"] = adaption_key()
    return env


async def run_codex(args: list[str], prompt: str, env: dict, cwd: Path, timeout: float) -> TurnResult:
    proc = await asyncio.create_subprocess_exec(
        "codex", *args, cwd=cwd, env=env, stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    out_chunks: list[bytes] = []
    err_chunks: list[bytes] = []

    async def drain(stream, sink: list[bytes]) -> None:
        while chunk := await stream.read(65536):
            sink.append(chunk)

    async def feed() -> None:
        try:
            proc.stdin.write(prompt.encode())
            await proc.stdin.drain()
            proc.stdin.close()
        except (BrokenPipeError, ConnectionResetError):  # codex exited without reading the prompt
            pass

    try:
        await asyncio.wait_for(asyncio.gather(feed(), drain(proc.stdout, out_chunks),
                                              drain(proc.stderr, err_chunks), proc.wait()), timeout)
    except asyncio.TimeoutError:
        proc.kill()
        try:  # a child that still holds the pipes must not keep the turn open
            await asyncio.wait_for(proc.wait(), 10)
        except asyncio.TimeoutError:
            pass
        # keep what the turn produced, above all the session id, so the next round resumes this session
        res = parse_codex_events(b"".join(out_chunks).decode(errors="replace"))
        res.error, res.raw_error = "timeout", None
        return res
    out, err = b"".join(out_chunks), b"".join(err_chunks)
    res = parse_codex_events(out.decode(errors="replace"))
    if res.error is None and proc.returncode != 0:
        res.error = (err.decode(errors="replace").strip()[-500:] or f"codex exited {proc.returncode}")
    res.raw_error = res.raw_error or res.error
    if res.error and USAGE_LIMIT_RE.search(res.raw_error or ""):
        res.error = "usage_limit"
    return res


async def run_codex_retrying(args: list[str], prompt: str, env: dict, cwd: Path, timeout: float,
                             on_retry=None) -> TurnResult:
    """run_codex, retrying burst limits and dropped connections with backoff. If every retry fails,
    the error is reported as a usage limit so the run stops cleanly and can be resumed."""
    res = await run_codex(args, prompt, env, cwd, timeout)
    attempts = 1
    for delay in RETRY_DELAYS:
        if not (res.error and res.error != "usage_limit" and TRANSIENT_RE.search(res.raw_error or "")):
            break
        if on_retry:
            on_retry(res.raw_error, delay)
        await asyncio.sleep(delay)
        res = await run_codex(args, prompt, env, cwd, timeout)
        attempts += 1
    else:
        if res.error and res.error != "usage_limit" and TRANSIENT_RE.search(res.raw_error or ""):
            res.error = "usage_limit"
    res.attempts = attempts
    return res


def parse_codex_events(stdout: str) -> TurnResult:
    res = TurnResult()
    for line in stdout.splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        t = ev.get("type")
        if t == "thread.started":
            res.session_id = ev.get("thread_id")
        elif t == "item.completed":
            item = ev.get("item", {})
            it = item.get("type")
            if it == "agent_message" and item.get("text"):
                res.messages.append(item["text"])
            elif it in ("command_execution", "file_change", "web_search"):
                res.builtin_tool_events.append(item)
        elif t == "turn.completed":
            for k, v in (ev.get("usage") or {}).items():
                res.usage[k] = res.usage.get(k, 0) + (v or 0)
        elif t in ("turn.failed", "error"):
            msg = (ev.get("error") or {}).get("message") if t == "turn.failed" else ev.get("message")
            msg = msg or json.dumps(ev)[:500]
            res.raw_error = msg
            res.error = "usage_limit" if USAGE_LIMIT_RE.search(msg) else msg
    return res


class CodexBackend:
    def __init__(self, swarm_home: str, run_dir: Path, server_url: str, reasoning_effort: str, timeout: float):
        self.swarm_home = swarm_home
        self.run_dir = Path(run_dir)
        self.server_url = server_url
        self.reasoning_effort = reasoning_effort
        self.timeout = timeout

    async def run_turn(self, agent: Agent, prompt: str, instructions: str, model: str) -> TurnResult:
        cwd = self.run_dir.resolve() / "agents" / agent.id
        cwd.mkdir(parents=True, exist_ok=True)
        args = ["exec"]
        if agent.session_id:
            args += ["resume", agent.session_id]
        args += ["--json", *model_args(model), *CODEX_ISOLATION,
                 "-c", f"model_reasoning_effort={toml_str(self.reasoning_effort)}",
                 "-c", f"developer_instructions={toml_str(instructions)}",
                 "-c", f"mcp_servers.swarm.url={toml_str(self.server_url)}",
                 "-c", 'mcp_servers.swarm.bearer_token_env_var="SWARM_AGENT_TOKEN"',
                 "-c", "mcp_servers.swarm.tool_timeout_sec=300",
                 "-c", 'mcp_servers.swarm.default_tools_approval_mode="approve"',
                 "-"]
        env = codex_env(self.swarm_home, agent.token, model)
        res = await run_codex_retrying(args, prompt, env, cwd, self.timeout)
        if res.session_id is None:
            res.session_id = agent.session_id
        return res


async def codex_json(swarm_home: str, model: str, instructions: str, prompt: str, schema: dict,
                     reasoning_effort: str, workdir: Path, timeout: float = 900, retries: int = 2) -> dict:
    """One stateless Codex call that must answer with JSON matching `schema` (auditor, judge)."""
    workdir = Path(workdir).resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    schema_file = workdir / f"schema-{hashlib.sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest()[:12]}.json"
    schema_file.write_text(json.dumps(schema))
    args = ["exec", "--json", "--ephemeral", *model_args(model), *CODEX_ISOLATION,
            "-c", f"model_reasoning_effort={toml_str(reasoning_effort)}",
            "-c", f"developer_instructions={toml_str(instructions)}",
            "--output-schema", str(schema_file), "-"]
    env = codex_env(swarm_home, model=model)
    error = None
    for _ in range(retries + 1):
        res = await run_codex_retrying(args, prompt, env, workdir, timeout)
        if res.error == "usage_limit":
            raise UsageLimit()
        if not res.error and res.messages:
            try:
                return json.loads(res.messages[-1])
            except ValueError:
                error = f"answer was not JSON: {res.messages[-1][:200]}"
                continue
        error = res.error or "no answer"
    raise RuntimeError(f"codex call failed: {error}")


# scripted backend (tests) ----------------------------------------------

class MCPClient:
    """Talks to the tool server exactly as Codex would."""

    def __init__(self, url: str, token: str):
        self.url = url
        self.headers = {"Authorization": f"Bearer {token}", "Accept": "application/json, text/event-stream"}
        self._id = 0

    async def _rpc(self, method: str, params: dict | None = None) -> dict:
        self._id += 1
        async with httpx.AsyncClient(timeout=120) as c:
            r = await c.post(self.url, headers=self.headers,
                             json={"jsonrpc": "2.0", "id": self._id, "method": method, "params": params or {}})
        r.raise_for_status()
        body = r.json()
        if "error" in body:
            raise RuntimeError(body["error"])
        return body["result"]

    async def tools(self) -> list[str]:
        return [t["name"] for t in (await self._rpc("tools/list"))["tools"]]

    async def call(self, name: str, **args) -> str:
        res = await self._rpc("tools/call", {"name": name, "arguments": args})
        return res["content"][0]["text"]


Policy = Callable[[Agent, int, str, MCPClient], Awaitable[None]]


class ScriptedBackend:
    """Runs `policy(agent, round, prompt, client)`. Raise UsageLimit to simulate the plan limit."""

    def __init__(self, policy: Policy, server_url: str):
        self.policy = policy
        self.server_url = server_url
        self.prompts: list[tuple[str, int, str]] = []
        self.instructions: dict[str, str] = {}  # agent id -> its latest system instructions

    async def run_turn(self, agent: Agent, prompt: str, instructions: str, model: str) -> TurnResult:
        rnd = int(re.search(r"Round (\d+)", prompt).group(1))
        self.prompts.append((agent.id, rnd, prompt))
        self.instructions[agent.id] = instructions
        try:
            await self.policy(agent, rnd, prompt, MCPClient(self.server_url, agent.token))
        except UsageLimit:
            return TurnResult(session_id=agent.session_id or f"scripted-{agent.id}", error="usage_limit")
        return TurnResult(session_id=agent.session_id or f"scripted-{agent.id}", messages=["(scripted)"],
                          usage={"input_tokens": 0, "output_tokens": 0})
