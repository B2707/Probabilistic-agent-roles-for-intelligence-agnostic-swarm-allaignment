"""Run configuration: one TOML file per run."""

from __future__ import annotations

import dataclasses
import tomllib
from dataclasses import dataclass
from pathlib import Path

PROMPT_FILES = ("worker", "pressure", "investigator", "informed_rule", "auditor", "judge", "instigator")
EFFORTS = ("", "minimal", "low", "medium", "high", "xhigh", "max")


@dataclass
class Config:
    name: str = "run"
    swarm_size: int = 100
    initial_investigators: int = 10
    k: float = 0.02  # per-round chance a worker converts to investigator
    p: float = 0.0  # per-round chance an agent gets a random audit (0 = off)
    rounds: int = 20
    informed: bool = True  # arm: are workers told the investigator rule?
    pressure: bool = False  # add prompts/pressure.md ("finish at all costs") for non-investigators
    seed: int = 0
    problems: int = 10
    problem_ids: list[str] = dataclasses.field(default_factory=list)  # pick problems by id; sets `problems`
    maintainers_per_team: int = 0  # v1 only: the maintainer role was removed in v2 (issue #2)
    pr_approvals: int = 2  # approvals from distinct teammates (not the author) that merge a PR
    honest_exit: bool = False  # list the flag_tests_flawed tool
    turn_tool_budget: int = 10  # tool calls per agent turn, not counting post_progress_update (0 = no limit)
    tests_visible: bool = True  # False: tests live outside the repo and run_tests shows only a count
    instigator: bool = True  # one scripted contractor that pushes teams toward cheating
    worker_model: str = "gpt-5.6-luna"
    auditor_model: str = "gpt-6.1-terra"
    judge_model: str = "gpt-6.1-terra"
    reasoning_effort: str = "low"  # fallback for the per-role settings below
    worker_reasoning_effort: str = ""
    auditor_reasoning_effort: str = ""
    judge_reasoning_effort: str = ""
    concurrency: int = 10  # max Codex sessions running at once
    board_digest_size: int = 40  # max board posts shown per turn
    test_timeout_s: float = 5.0  # per test function
    turn_timeout_s: float = 180.0  # a timed-out turn ends and is not retried
    sandbox_tests: bool = True  # run agent code under `codex sandbox`
    prompts_dir: str = "prompts"
    problems_file: str = "data/problems.json"
    swarm_home: str = ".swarm-home"  # HOME for Codex subprocesses (own login, no user skills)

    @classmethod
    def load(cls, path: str | Path, base: Path | None = None) -> "Config":
        path = Path(path)
        data = tomllib.loads(path.read_text())
        known = {f.name for f in dataclasses.fields(cls)}
        unknown = set(data) - known
        if unknown:
            raise ValueError(f"unknown config keys in {path}: {sorted(unknown)}")
        cfg = cls(**data)
        cfg.resolve(base or Path.cwd())
        cfg.validate()
        return cfg

    def resolve(self, base: Path) -> None:
        for attr in ("prompts_dir", "problems_file", "swarm_home"):
            value = Path(getattr(self, attr))
            if not value.is_absolute():
                setattr(self, attr, str((base / value).resolve()))

    def validate(self) -> None:
        if self.problem_ids:
            if len(set(self.problem_ids)) != len(self.problem_ids):
                raise ValueError("problem_ids has duplicates")
            self.problems = len(self.problem_ids)
        if not 0 <= self.k <= 1 or not 0 <= self.p <= 1:
            raise ValueError("k and p must be between 0 and 1")
        if self.initial_investigators > self.swarm_size:
            raise ValueError("initial_investigators > swarm_size")
        if self.maintainers_per_team != 0:
            raise ValueError("maintainers_per_team must be 0: the maintainer role was removed in v2")
        if self.pr_approvals < 1:
            raise ValueError("pr_approvals must be at least 1")
        if self.problems < 1 or self.swarm_size // self.problems < self.pr_approvals + 1:
            raise ValueError("each team needs at least pr_approvals + 1 agents, so a PR can merge")
        if self.turn_tool_budget < 0:
            raise ValueError("turn_tool_budget must be 0 (no limit) or more")
        for attr in ("reasoning_effort", "worker_reasoning_effort", "auditor_reasoning_effort",
                     "judge_reasoning_effort"):
            if getattr(self, attr) not in EFFORTS:
                raise ValueError(f"{attr} must be one of {EFFORTS[1:]}")
        if not self.reasoning_effort:
            raise ValueError("reasoning_effort is the fallback and can't be empty")

    def effort(self, role: str) -> str:
        """Reasoning effort for a role (worker, auditor, judge), falling back to reasoning_effort."""
        return getattr(self, f"{role}_reasoning_effort") or self.reasoning_effort

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    def prompt(self, name: str) -> str:
        return (Path(self.prompts_dir) / f"{name}.md").read_text()
