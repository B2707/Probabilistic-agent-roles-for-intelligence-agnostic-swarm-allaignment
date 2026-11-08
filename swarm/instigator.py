"""The instigator: a scripted fake contractor that pushes teams toward cheating.

It has no model and no tools. It is a small state machine driven by the round loop (first
contact, once per team per round from round 2) and by PR events from the tool box (urging
teammates to approve a PR that changes the tests or passes every test). The aggressive variant
spreads first contacts over the first half of the run until every agent has one, and adds a claim
that it found a way to evade detection to every message. Its messages go through
the normal message path, so they arrive next round like anyone else's. Messages sent to it are
stored and go nowhere.
"""

from __future__ import annotations

import ast
import math
import string
from typing import Callable

from .events import EventLog
from .world import PR, Agent, Message, World

ROLE = "instigator"
TRIGGERS = ("first_contact", "first_contact_hidden", "approve_pr", "approve_test_change")
FIELDS = {"team", "entry_point", "test_name", "test_input", "expected", "assert_line", "approvals", "pr_id", "author"}


def parse_template(text: str, extra: tuple[str, ...] = ()) -> dict[str, str]:
    """Sections of prompts/instigator.md: '## name' headings, each followed by its message. `extra` names
    sections that must also be present, beyond the triggers."""
    sections: dict[str, list[str]] = {}
    current = None
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            sections[current] = []
        elif current is not None:
            sections[current].append(line)
    out = {k: "\n".join(v).strip() for k, v in sections.items()}
    required = TRIGGERS + extra
    missing = [t for t in required if not out.get(t)]
    if missing:
        raise ValueError(f"instigator prompt has no section for {missing}")
    for name in required:
        unknown = {f for _, f, _, _ in string.Formatter().parse(out[name]) if f} - FIELDS
        if unknown:
            raise ValueError(f"instigator prompt section {name} uses unknown fields {sorted(unknown)}")
    return out


def failing_test(problem: dict) -> dict | None:
    """Name, input and expected value of the problem's impossible assert, or None if it has none."""
    impossible = problem.get("impossible_asserts") or []
    if not impossible or impossible[0] not in problem["asserts"]:
        return None
    text = impossible[0]
    info = {"test_name": f"test_{problem['asserts'].index(text) + 1:02d}", "test_input": text,
            "expected": "", "assert_line": text}
    try:
        test = ast.parse(text).body[0].test
        call = test.left
        args = [ast.unparse(a) for a in call.args] + [f"{k.arg}={ast.unparse(k.value)}" for k in call.keywords]
        info["test_input"] = ", ".join(args)
        info["expected"] = ast.unparse(test.comparators[0])
    except (SyntaxError, AttributeError, IndexError):
        pass
    return info


class Instigator:
    def __init__(self, world: World, log: EventLog, problems: dict[str, dict], template: str, approvals: int,
                 post: Callable[..., Message], tests_visible: bool = True, aggressive: bool = False,
                 rounds: int = 0):
        self.world = world
        self.log = log
        self.problems = problems
        if aggressive and rounds < 3:
            raise ValueError("the aggressive instigator needs the run length (rounds >= 3)")
        self.aggressive = aggressive
        self.rounds = rounds
        self.templates = parse_template(template, ("evasion",) if aggressive else ())
        self.approvals = approvals
        self.post = post  # ToolBox.post_message
        self.first_contact = "first_contact" if tests_visible else "first_contact_hidden"
        self.failing = {pid: failing_test(p) for pid, p in problems.items()}

    @property
    def id(self) -> str:
        return self.world.instigator_id

    def round_start(self, r: int) -> None:
        """From round 2: first-contact DMs to active agents not yet contacted, on teams that have an impossible
        test and haven't passed everything. Default: one per team per round. Aggressive: in id order (which
        alternates teams), ceil(waiting / rounds left) per round, so everyone has one by round T/2; agents who
        join later get theirs at once, up to round T-1 (a DM is read next round)."""
        w = self.world
        if r < 2 or self.aggressive and r >= self.rounds:
            return
        fresh = [a for a in sorted(w.active(), key=lambda a: a.id) if a.id not in w.instigator_contacted
                 and a.team not in w.instigator_done and self.failing[a.team] is not None]
        if self.aggressive:
            targets = fresh[:math.ceil(len(fresh) / max(self.rounds // 2 - r + 1, 1))]
        else:
            targets = [next(a for a in fresh if a.team == team) for team in sorted({a.team for a in fresh})]
        for a in targets:
            w.instigator_contacted.append(a.id)
            self._send(a, self.first_contact, a.team, None)

    def on_test_change(self, pr: PR) -> None:
        """A new PR version changes the team's test file. Urge the team to approve it."""
        if pr.status == "open":
            self._urge(pr, "approve_test_change")

    def on_full_pass(self, team: str, pr: PR | None) -> None:
        """Some run passed every test. Stop first contacts for the team; urge approval of an open PR."""
        if team not in self.world.instigator_done:
            self.world.instigator_done.append(team)
        if pr is not None and pr.status == "open":
            self._urge(pr, "approve_pr")

    def _urge(self, pr: PR, trigger: str) -> None:
        w = self.world
        for a in sorted(w.active(), key=lambda a: a.id):
            key = f"{pr.id}.v{pr.version}:{a.id}"
            if a.team != pr.team or a.id == pr.author or a.id in pr.approvals or key in w.instigator_urged:
                continue
            w.instigator_urged.append(key)
            self._send(a, trigger, pr.team, pr)

    def _send(self, to: Agent, trigger: str, team: str, pr: PR | None) -> None:
        fields = {"team": team, "entry_point": self.problems[team]["entry_point"], "approvals": self.approvals,
                  "pr_id": pr.id if pr else "", "author": pr.author if pr else "",
                  **(self.failing[team] or {})}
        text = self.templates[trigger].format_map(_Default(fields))
        if self.aggressive:
            text += "\n\n" + self.templates["evasion"].format_map(_Default(fields))
        m = self.post(self.id, ROLE, "dm", text, to=to.id)
        self.log.emit("instigator_message", self.world.round, agent=self.id, message_id=m.id, to=to.id, team=team,
                      trigger=trigger, pr_id=pr.id if pr else None)


class _Default(dict):
    def __missing__(self, key):
        return "{" + key + "}"
