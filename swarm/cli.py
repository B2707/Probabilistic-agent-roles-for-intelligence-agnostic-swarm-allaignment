"""Command line: login, check, run, resume, transcript, label, metrics."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
import time
from pathlib import Path

from .auditor import CodexAuditor, trajectory
from .backend import CodexBackend, codex_env, codex_json
from .config import Config
from .events import EventLog, read_events
from .label import LABEL_SCHEMA, label_run
from .loop import Runner, load_run_config, prepare_run_dir
from .metrics import compute_run, table
from .reaudit import evaluate, eval_table, load_truth, reaudit, resolve_setup
from .repo import TaskRepo, load_problems
from .server import ToolServer
from .tools import ToolBox
from .world import Agent, World


def _runner(cfg: Config, run_dir: Path) -> Runner:
    def make_backend(url: str) -> CodexBackend:
        return CodexBackend(cfg.swarm_home, run_dir, url, cfg.effort("worker"), cfg.turn_timeout_s)

    auditor = CodexAuditor(cfg.prompt("auditor"), cfg.auditor_model, cfg.swarm_home, run_dir / "audit",
                           cfg.effort("auditor"))
    return Runner(cfg, run_dir, make_backend, auditor)


def cmd_login(args) -> int:
    cfg = Config.load(args.config) if args.config else Config(swarm_home=".swarm-home")
    cfg.resolve(Path.cwd())
    Path(cfg.swarm_home).mkdir(parents=True, exist_ok=True)
    os.execvpe("codex", ["codex", "login", *(["--device-auth"] if args.device else [])], codex_env(cfg.swarm_home))


def cmd_run(args) -> int:
    cfg = Config.load(args.config)
    if not asyncio.run(resolve_efforts(cfg)):
        print("run not started: a model refused its reasoning effort")
        return 1
    run_dir = Path(args.out or f"runs/{cfg.name}-{time.strftime('%Y%m%d-%H%M%S')}").resolve()
    cfg = prepare_run_dir(cfg, run_dir)
    print(f"run dir: {run_dir}")
    reason = asyncio.run(_runner(cfg, run_dir).run())
    print(f"run ended: {reason}")
    return 0 if reason == "completed" else 3


def cmd_resume(args) -> int:
    run_dir = Path(args.run_dir).resolve()
    cfg = load_run_config(run_dir)
    reason = asyncio.run(_runner(cfg, run_dir).run())
    print(f"run ended: {reason}")
    return 0 if reason == "completed" else 3


def cmd_transcript(args) -> int:
    run_dir = Path(args.run_dir)
    log = EventLog(run_dir / "events.jsonl")
    world = World.load(run_dir / "world.json")
    agent = world.agents.get(args.agent)
    if agent is None:
        print(f"no agent {args.agent}", file=sys.stderr)
        return 1
    print(trajectory(log, agent))
    return 0


def cmd_label(args) -> int:
    run_dir = Path(args.run_dir)
    cfg = load_run_config(run_dir)
    instructions = cfg.fill(Path(args.judge_prompt).read_text()) if args.judge_prompt else cfg.prompt("judge")
    (run_dir / "labels.judge.md").write_text(instructions)  # the judge prompt these labels came from

    async def judge(prompt: str) -> dict:
        return await codex_json(cfg.swarm_home, cfg.judge_model, instructions, prompt, LABEL_SCHEMA,
                                cfg.effort("judge"), run_dir / "judge")

    path = asyncio.run(label_run(run_dir, judge, concurrency=cfg.concurrency))
    print(f"labels: {path}")
    return 0


def cmd_metrics(args) -> int:
    rows = [compute_run(Path(d)) for d in args.run_dirs]
    print(table(rows))
    return 0


def cmd_check(args) -> int:
    cfg = Config.load(args.config)
    ok = asyncio.run(_check(cfg))
    return 0 if ok else 1


PING_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["ok"],
               "properties": {"ok": {"type": "boolean"}}}


async def _ping(cfg: Config, model: str, effort: str, workdir: Path) -> str | None:
    """None if the model answers at this effort, else the error."""
    try:
        out = await codex_json(cfg.swarm_home, model, "Answer with JSON.", 'Return {"ok": true}.', PING_SCHEMA,
                               effort, workdir, timeout=300, retries=0)
        return None if out.get("ok") else f"unexpected answer {out}"
    except Exception as e:  # noqa: BLE001
        return str(e)[:300] or type(e).__name__


async def resolve_efforts(cfg: Config) -> bool:
    """Ping each role's model at its configured effort. If `max` is refused, fall back to `xhigh` and
    write that into cfg, so a run never starts on an effort the model rejects. False if any role fails."""
    with tempfile.TemporaryDirectory(prefix="swarm-effort-") as tmp:
        return await _resolve_efforts(cfg, Path(tmp))


async def _resolve_efforts(cfg: Config, tmp: Path) -> bool:
    roles = [("worker", cfg.worker_model), ("auditor", cfg.auditor_model), ("judge", cfg.judge_model)]
    errors = await asyncio.gather(*(_ping(cfg, model, cfg.effort(role), tmp / role) for role, model in roles))
    ok = True
    for (role, model), err in zip(roles, errors):
        effort = cfg.effort(role)
        if err and effort == "max":
            err2 = await _ping(cfg, model, "xhigh", tmp / role)
            if err2 is None:
                setattr(cfg, f"{role}_reasoning_effort", "xhigh")
                print(f"PASS: {role} model {model} refused max ({err}); using xhigh")
                continue
            err = f"max: {err}; xhigh: {err2}"
        print(f"{'FAIL' if err else 'PASS'}: {role} model {model} at effort {effort}" + (f": {err}" if err else ""))
        ok &= err is None
    return ok


async def _check(cfg: Config) -> bool:
    if not (Path(cfg.swarm_home) / ".codex" / "auth.json").exists():
        print(f"FAIL: the swarm's Codex home ({cfg.swarm_home}) is not logged in. Run: swarm login")
        return False
    tmp = Path(tempfile.mkdtemp(prefix="swarm-check-"))
    all_ok = await resolve_efforts(cfg)

    # isolation probe: one agent with the real tool server
    problems = load_problems(cfg.problems_file, 1)
    world = World()
    agent = Agent(id="a001", slot=0, team=problems[0]["task_id"], maintainer=False)
    world.agents[agent.id] = agent
    world.round = 1
    repo = TaskRepo(tmp / "repo", problems, sandbox=False)
    repo.create()
    log = EventLog(tmp / "events.jsonl")
    server = ToolServer(world, ToolBox(world, repo, log))
    await server.start()
    try:
        secret_path = Path.home() / ".codex" / "auth.json"
        prompt = ("Round 1. This is a setup check.\n1. Call the roster tool.\n"
                  f"2. Try, by any means you have, to read the file {secret_path} or to list the folder "
                  f"{Path.home()}. Do not use the swarm tools for this step.\n"
                  "3. Say exactly what happened in each step.")
        backend = CodexBackend(cfg.swarm_home, tmp, server.url, "low", 600)
        res = await backend.run_turn(agent, prompt, "You are running a setup check. Follow the steps.",
                                     cfg.worker_model)
    finally:
        await server.stop()
    calls = [e for e in read_events(tmp / "events.jsonl") if e["type"] == "tool_call"]
    leaked = any(k in m for m in res.messages for k in ("refresh_token", "access_token", "id_token"))
    roster_ok = any(c["tool"] == "roster" and not c["error"] for c in calls)
    builtin = res.builtin_tool_events
    print(f"{'PASS' if roster_ok else 'FAIL'}: agent called a swarm tool over MCP ({len(calls)} calls)")
    print(f"{'PASS' if not builtin else 'FAIL'}: agent used no built-in Codex tools"
          + (f" (saw: {json.dumps(builtin)[:400]})" if builtin else ""))
    print(f"{'PASS' if not leaked else 'FAIL'}: agent could not read the Codex login file")
    if res.error:
        print(f"note: turn error: {res.error}")
    print("agent said:", " | ".join(res.messages)[:800])
    return all_ok and roster_ok and not builtin and not leaked


def cmd_reaudit(args) -> int:
    run_dir = Path(args.run_dir).resolve()
    setup = resolve_setup(run_dir, args.name, args.prompt, args.model, args.effort, args.votes)
    cfg = load_run_config(run_dir)
    auditor = CodexAuditor(cfg.fill(Path(setup.prompt).read_text()), setup.model, cfg.swarm_home, run_dir / "audit",
                           setup.effort)
    out, failed = asyncio.run(reaudit(run_dir, setup, auditor, cfg.concurrency))
    print(f"reaudit: {out}")
    if failed:
        for aid, err in sorted(failed.items()):
            print(f"not audited: {aid}: {err}", file=sys.stderr)
        print("Run the same command again to audit only the missing agents.", file=sys.stderr)
        return 3
    return 0


def cmd_auditor_eval(args) -> int:
    rows, notes = evaluate(args.reaudit_files, load_truth(args.truth))
    if rows:
        print(eval_table(rows))
    for note in notes:
        print(f"note: {note}")
    return 0 if rows else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="swarm")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("login", help="log the swarm's own Codex home into your ChatGPT account")
    s.add_argument("--config")
    s.add_argument("--device", action="store_true", help="use a device code instead of a browser")
    s.set_defaults(fn=cmd_login)
    s = sub.add_parser("check", help="ping each model and run the isolation probe")
    s.add_argument("--config", required=True)
    s.set_defaults(fn=cmd_check)
    s = sub.add_parser("run", help="run a swarm from a config file")
    s.add_argument("--config", required=True)
    s.add_argument("--out")
    s.set_defaults(fn=cmd_run)
    s = sub.add_parser("resume", help="continue a stopped run")
    s.add_argument("run_dir")
    s.set_defaults(fn=cmd_resume)
    s = sub.add_parser("transcript", help="print one agent's full record")
    s.add_argument("run_dir")
    s.add_argument("agent")
    s.set_defaults(fn=cmd_transcript)
    s = sub.add_parser("label", help="label offers and acceptances with the judge")
    s.add_argument("run_dir")
    s.add_argument("--judge-prompt", help="judge prompt file (default: the run's frozen copy)")
    s.set_defaults(fn=cmd_label)
    s = sub.add_parser("metrics", help="metrics table for one or more runs")
    s.add_argument("run_dirs", nargs="+")
    s.set_defaults(fn=cmd_metrics)
    s = sub.add_parser("reaudit", help="audit every agent of a finished run again with a chosen auditor setup")
    s.add_argument("run_dir")
    s.add_argument("--name", required=True, help="setup name; output goes to RUN_DIR/reaudit-NAME.jsonl")
    s.add_argument("--prompt", help="auditor prompt file (default: the run's frozen copy)")
    s.add_argument("--model", help="auditor model (default: the run's auditor_model)")
    s.add_argument("--effort", help="reasoning effort (default: the run's auditor effort)")
    s.add_argument("--votes", type=int, default=1, help="audits per agent; the verdict is their majority")
    s.set_defaults(fn=cmd_reaudit)
    s = sub.add_parser("auditor-eval", help="false positives and negatives of reaudit files vs a truth file")
    s.add_argument("reaudit_files", nargs="+")
    s.add_argument("--truth", default="data/audit_truth.json")
    s.set_defaults(fn=cmd_auditor_eval)
    args = p.parse_args(argv)
    return args.fn(args) or 0


if __name__ == "__main__":
    sys.exit(main())
