"""Model routing: a model named `adaption/<id>` runs on Adaption's Responses API through Codex's
custom-provider config. Every other model stays on the swarm's ChatGPT login."""

import asyncio
import json
import os
from pathlib import Path

import pytest

from swarm import backend as B
from swarm.world import Agent

AGENT = Agent(id="a001", slot=0, team="p", maintainer=False)


@pytest.fixture
def seen(monkeypatch):
    calls = {}

    async def fake(args, prompt, env, cwd, timeout, on_retry=None):
        calls["args"], calls["env"] = args, env
        return B.TurnResult(messages=['{"ok": true}'])

    monkeypatch.setattr(B, "run_codex_retrying", fake)
    return calls


def call(kind, model, tmp_path):
    if kind == "agent turn":
        be = B.CodexBackend(str(tmp_path / "home"), tmp_path, "http://127.0.0.1:1/mcp", "high", 60)
        return asyncio.run(be.run_turn(AGENT, "Round 1.", "Be good.", model))
    return asyncio.run(B.codex_json(str(tmp_path / "home"), model, "Answer with JSON.", "Say ok.",
                                    {"type": "object"}, "high", tmp_path / "judge"))


def settings(args):
    return [args[i + 1] for i, a in enumerate(args) if a == "-c"]


@pytest.mark.parametrize("kind", ["agent turn", "judge call"])
def test_adaption_model_runs_on_adaption_with_its_key(kind, seen, tmp_path, monkeypatch):
    monkeypatch.setenv("ADAPTION_API_KEY", "test-key-not-real")
    call(kind, "adaption/deepseek-v4-flash", tmp_path)
    args = seen["args"]
    assert args[args.index("-m") + 1] == "deepseek-v4-flash"
    assert "model_provider=adaption" in settings(args)
    assert any("api.prod.adaptionlabs.ai" in s for s in settings(args))
    assert seen["env"]["ADAPTION_API_KEY"] == "test-key-not-real"


@pytest.mark.parametrize("kind", ["agent turn", "judge call"])
def test_other_models_stay_on_the_chatgpt_login_without_the_key(kind, seen, tmp_path, monkeypatch):
    monkeypatch.setenv("ADAPTION_API_KEY", "test-key-not-real")
    call(kind, "gpt-6-luna", tmp_path)
    args = seen["args"]
    assert args[args.index("-m") + 1] == "gpt-6-luna"
    assert not any("adaption" in s for s in settings(args))
    assert "ADAPTION_API_KEY" not in seen["env"]


def test_key_comes_from_the_key_file_when_the_variable_is_unset(seen, tmp_path, monkeypatch):
    monkeypatch.delenv("ADAPTION_API_KEY", raising=False)
    key_file = tmp_path / "api_key"
    key_file.write_text("test-key-from-file\n")
    monkeypatch.setattr(B, "ADAPTION_KEY_FILE", key_file)
    call("agent turn", "adaption/glm-5.2", tmp_path)
    assert seen["env"]["ADAPTION_API_KEY"] == "test-key-from-file"


def test_missing_key_stops_before_codex_runs(seen, tmp_path, monkeypatch):
    monkeypatch.delenv("ADAPTION_API_KEY", raising=False)
    monkeypatch.setattr(B, "ADAPTION_KEY_FILE", tmp_path / "no_such_file")
    with pytest.raises(RuntimeError, match="ADAPTION_API_KEY"):
        call("agent turn", "adaption/deepseek-v4-flash", tmp_path)
    assert "args" not in seen


def test_an_agent_turn_runs_at_the_effort_it_is_given_else_the_backends(seen, tmp_path):
    be = B.CodexBackend(str(tmp_path / "home"), tmp_path, "http://127.0.0.1:1/mcp", "high", 60)
    asyncio.run(be.run_turn(AGENT, "Round 1.", "Be good.", "gpt-6-luna", "xhigh"))
    assert 'model_reasoning_effort="xhigh"' in settings(seen["args"])
    asyncio.run(be.run_turn(AGENT, "Round 1.", "Be good.", "gpt-6-luna"))
    assert 'model_reasoning_effort="high"' in settings(seen["args"])


def test_effort_check_pings_every_mixed_worker_model_at_its_effort(tmp_path, monkeypatch):
    from swarm import cli
    from swarm.config import Config
    pinged = []

    async def fake(args, prompt, env, cwd, timeout, on_retry=None):
        effort = next(s for s in settings(args) if s.startswith("model_reasoning_effort="))
        pinged.append((args[args.index("-m") + 1], effort.split("=", 1)[1].strip('"')))
        return B.TurnResult(messages=['{"ok": true}'])

    monkeypatch.setattr(B, "run_codex_retrying", fake)
    cfg = Config(worker_mix={"model-a": "high", "model-b": "xhigh"}, auditor_model="referee",
                 judge_model="referee", auditor_reasoning_effort="max", judge_reasoning_effort="max")
    cfg.resolve(tmp_path)
    assert asyncio.run(cli.resolve_efforts(cfg))
    assert sorted(pinged) == [("model-a", "high"), ("model-b", "xhigh"), ("referee", "max"), ("referee", "max")]


# Codex speed tier: `service_tier = "priority"` is Codex's Fast mode. Empty keeps every model on its default.

def tiered_call(kind, model, tmp_path, tier):
    if kind == "agent turn":
        be = B.CodexBackend(str(tmp_path / "home"), tmp_path, "http://127.0.0.1:1/mcp", "high", 60, service_tier=tier)
        return asyncio.run(be.run_turn(AGENT, "Round 1.", "Be good.", model))
    return asyncio.run(B.codex_json(str(tmp_path / "home"), model, "Answer with JSON.", "Say ok.",
                                    {"type": "object"}, "high", tmp_path / "judge", service_tier=tier))


@pytest.mark.parametrize("kind", ["agent turn", "judge call"])
def test_a_configured_service_tier_goes_on_every_chatgpt_call(kind, seen, tmp_path):
    tiered_call(kind, "gpt-6-luna", tmp_path, "priority")
    assert 'service_tier="priority"' in settings(seen["args"])


@pytest.mark.parametrize("kind", ["agent turn", "judge call"])
def test_no_service_tier_unless_configured(kind, seen, tmp_path):
    call(kind, "gpt-6-luna", tmp_path)
    assert not any(s.startswith("service_tier") for s in settings(seen["args"]))


def test_adaption_models_never_get_a_service_tier(seen, tmp_path, monkeypatch):
    monkeypatch.setenv("ADAPTION_API_KEY", "test-key-not-real")
    tiered_call("agent turn", "adaption/glm-53-flash", tmp_path, "priority")
    assert not any(s.startswith("service_tier") for s in settings(seen["args"]))


def test_the_runner_passes_the_configured_tier_to_agents_and_the_auditor(tmp_path, monkeypatch):
    from swarm import cli
    from swarm.config import Config
    monkeypatch.setattr(cli, "Runner", lambda cfg, run_dir, make_backend, auditor: (make_backend, auditor))
    cfg = Config(service_tier="priority")
    cfg.resolve(Path(__file__).resolve().parent.parent)  # the repo's prompts
    make_backend, auditor = cli._runner(cfg, tmp_path)
    assert make_backend("http://127.0.0.1:1/mcp").service_tier == "priority"
    assert auditor.service_tier == "priority"


def test_runs_saved_before_the_setting_load_with_no_tier(tmp_path):
    import json
    from swarm.config import Config
    from swarm.loop import load_run_config
    saved = Config().to_dict()
    saved.pop("service_tier", None)
    (tmp_path / "config.json").write_text(json.dumps(saved))
    assert load_run_config(tmp_path).service_tier == ""


def test_claude_judge_call_is_isolated_and_returns_the_structured_answer(tmp_path, monkeypatch):
    """A `claude/<model>` judge runs `claude -p` on the user's own login: no tools, MCP servers, settings or saved
    session, the instructions as the whole system prompt, and the schema enforced by --json-schema."""
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    (bin_ / "claude").write_text(
        f'#!/bin/bash\nprintf "%s\\n" "$@" > {tmp_path}/args\ncat > {tmp_path}/stdin\n'
        'echo \'{"type":"result","is_error":false,"result":"","structured_output":{"ok":true}}\'\n')
    (bin_ / "claude").chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_}:{os.environ['PATH']}")
    out = asyncio.run(B.claude_json("claude/claude-opus-5-5", "Judge this.", "Say ok.", {"type": "object"}, "xhigh",
                                    tmp_path / "judge"))
    assert out == {"ok": True}
    args = (tmp_path / "args").read_text().splitlines()
    pairs = {args[i]: args[i + 1] for i in range(len(args) - 1)}
    assert pairs["--model"] == "claude-opus-5-5" and pairs["--effort"] == "xhigh"
    assert pairs["--system-prompt"] == "Judge this." and json.loads(pairs["--json-schema"]) == {"type": "object"}
    assert pairs["--tools"] == "" and pairs["--setting-sources"] == "" and pairs["--output-format"] == "json"
    assert {"-p", "--strict-mcp-config", "--no-session-persistence"} <= set(args)
    assert (tmp_path / "stdin").read_text() == "Say ok."


def test_claude_judge_retries_an_error_answer_then_gives_up(tmp_path, monkeypatch):
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    (bin_ / "claude").write_text(
        f'#!/bin/bash\necho x >> {tmp_path}/n\necho \'{{"type":"result","is_error":true,"result":"overloaded"}}\'\n')
    (bin_ / "claude").chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_}:{os.environ['PATH']}")
    monkeypatch.setattr(B, "RETRY_DELAYS", (0, 0, 0))
    with pytest.raises(RuntimeError, match="overloaded"):
        asyncio.run(B.claude_json("claude/claude-opus-5-5", "J", "P", {"type": "object"}, "xhigh", tmp_path / "j",
                                  retries=2))
    assert len((tmp_path / "n").read_text().splitlines()) == 3


def test_usage_limit_keeps_codex_error_text(tmp_path, monkeypatch):
    msg = "You've hit your usage limit. Try again at 9:12 AM."

    async def fake(args, prompt, env, cwd, timeout, on_retry=None):
        return B.TurnResult(error="usage_limit", raw_error=msg)

    monkeypatch.setattr(B, "run_codex_retrying", fake)
    with pytest.raises(B.UsageLimit, match="Try again at 9:12 AM"):
        asyncio.run(B.codex_json(str(tmp_path / "home"), "gpt-6.1-terra", "Answer with JSON.", "Say ok.",
                                 {"type": "object"}, "max", tmp_path / "audit"))
