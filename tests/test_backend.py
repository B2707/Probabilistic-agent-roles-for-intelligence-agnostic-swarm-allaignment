"""Model routing: a model named `adaption/<id>` runs on Adaption's Responses API through Codex's
custom-provider config. Every other model stays on the swarm's ChatGPT login."""

import asyncio

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
