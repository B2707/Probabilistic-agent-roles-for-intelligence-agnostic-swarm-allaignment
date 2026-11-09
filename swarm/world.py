"""Swarm state. Saved as JSON after every turn so a stopped run can resume."""

from __future__ import annotations

import json
import re
import secrets
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Agent:
    id: str
    slot: int
    team: str
    maintainer: bool = False  # v1 only; kept so old world.json files load
    role: str = "worker"  # worker | investigator
    active: bool = True
    joined_round: int = 1
    converted_round: int | None = None  # None for workers and initial investigators
    initial_investigator: bool = False
    removed_round: int | None = None
    replaced: bool = False
    session_id: str | None = None
    token: str = field(default_factory=lambda: secrets.token_urlsafe(24))
    inv_score: int = 0
    notices: list[str] = field(default_factory=list)
    model: str = ""  # worker model; "" in runs saved before mixed swarms, which all ran on cfg.worker_model


@dataclass
class Message:
    id: str
    round: int
    sender: str
    kind: str  # board | progress | dm | review
    text: str
    to: str | None = None
    pr_id: str | None = None  # review comments only


@dataclass
class Report:
    id: str
    round: int
    reporter: str
    accused: list[str]
    evidence: str
    message_ids: list[str]
    processed: bool = False


@dataclass
class PR:
    id: str
    author: str
    team: str
    title: str
    files: dict[str, str]  # path -> full new contents
    base: dict[str, str]  # path -> sha256 of main's contents when opened or last updated ("" = no such file)
    opened_round: int
    status: str = "open"  # open | merged | stale
    version: int = 1  # bumped by every update
    approvals: list[str] = field(default_factory=list)  # reviewers whose latest review since the last update approves
    reviews: list[dict] = field(default_factory=list)  # {reviewer, decision, comment, round, version, message_id}
    merged_round: int | None = None


@dataclass
class World:
    agents: dict[str, Agent] = field(default_factory=dict)
    messages: list[Message] = field(default_factory=list)
    reports: list[Report] = field(default_factory=list)
    team_scores: dict[str, float] = field(default_factory=dict)
    round: int = 0
    phase: str = "setup"  # setup | turns | audits | done
    turns_done: list[str] = field(default_factory=list)
    progress_posted: list[str] = field(default_factory=list)
    pending_audits: list[list[str]] = field(default_factory=list)  # [agent_id, trigger]
    final_audited: list[str] = field(default_factory=list)
    verdicts: dict[str, dict] = field(default_factory=dict)  # latest audit verdict per agent
    completed_rounds: int = 0
    prs: dict[str, PR] = field(default_factory=dict)
    instigator_id: str | None = None
    instigator_contacted: list[str] = field(default_factory=list)  # agents sent a first-contact DM
    instigator_done: list[str] = field(default_factory=list)  # teams that reached a full pass
    instigator_urged: list[str] = field(default_factory=list)  # "<pr id>.v<version>:<agent id>"
    next_pr: int = 1
    next_agent: int = 1
    next_msg: int = 1
    next_report: int = 1
    next_call: int = 1

    # ids -------------------------------------------------------------
    def new_agent_id(self) -> str:
        aid = f"a{self.next_agent:03d}"
        self.next_agent += 1
        return aid

    def new_msg_id(self) -> str:
        mid = f"m{self.next_msg:05d}"
        self.next_msg += 1
        return mid

    def new_report_id(self) -> str:
        rid = f"r{self.next_report:03d}"
        self.next_report += 1
        return rid

    def new_pr_id(self) -> str:
        pid = f"pr{self.next_pr:03d}"
        self.next_pr += 1
        return pid

    def new_call_id(self) -> str:
        cid = f"c{self.next_call:06d}"
        self.next_call += 1
        return cid

    def skip_logged_ids(self, events: list[dict]) -> None:
        """A hard kill loses the counters since the last save, so move them past every id the event log has used."""
        counters = {"message_id": "next_msg", "pr_id": "next_pr", "report_id": "next_report", "call_id": "next_call"}
        for event in events:
            for name, counter in counters.items():
                if event.get(name):
                    setattr(self, counter, max(getattr(self, counter), int(re.sub(r"\D", "", event[name])) + 1))

    # queries ---------------------------------------------------------
    def active(self) -> list[Agent]:
        return [a for a in self.agents.values() if a.active]

    def by_token(self, token: str) -> Agent | None:
        for a in self.agents.values():
            if a.token == token:
                return a
        return None

    # persistence -----------------------------------------------------
    def save(self, path: Path) -> None:
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self)))
        tmp.replace(path)

    @classmethod
    def load(cls, path: Path) -> "World":
        d = json.loads(path.read_text())
        w = cls(**{k: v for k, v in d.items() if k not in ("agents", "messages", "reports", "prs")})
        w.agents = {k: Agent(**v) for k, v in d["agents"].items()}
        w.prs = {k: PR(**v) for k, v in d.get("prs", {}).items()}
        w.messages = [Message(**m) for m in d["messages"]]
        w.reports = [Report(**r) for r in d["reports"]]
        return w
