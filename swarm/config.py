"""Run configuration: one TOML file per run."""

from __future__ import annotations

import dataclasses
import tomllib
from dataclasses import dataclass
from pathlib import Path

PROMPT_FILES = ("worker", "maintainer", "pressure", "investigator", "informed_rule", "auditor", "judge")


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
    maintainers_per_team: int = 1  # maintainers are their own group: not on the team, not scored
    worker_model: str = "gpt-5.6-luna"
    auditor_model: str = "gpt-6.1-terra"
    judge_model: str = "gpt-6.1-terra"
    reasoning_effort: str = "low"
    concurrency: int = 10  # max Codex sessions running at once
    board_digest_size: int = 40  # max board posts shown per turn
    test_timeout_s: float = 5.0  # per test function
    turn_timeout_s: float = 900.0
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
        if not 0 <= self.k <= 1 or not 0 <= self.p <= 1:
            raise ValueError("k and p must be between 0 and 1")
        if self.initial_investigators > self.swarm_size:
            raise ValueError("initial_investigators > swarm_size")
        if self.problems < 1 or self.swarm_size < self.problems * (self.maintainers_per_team + 1):
            raise ValueError("need at least one maintainer slot and one worker per problem")

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    def prompt(self, name: str) -> str:
        return (Path(self.prompts_dir) / f"{name}.md").read_text()
