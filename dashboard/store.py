"""In-memory state for the dashboard: tails every run's events.jsonl by byte offset and keeps aggregates.

Read-only by design. Nothing here opens a file for writing. Paper metrics come from `swarm.metrics.compute`, run in
memory over a slim copy of each run's events (only the fields `compute` reads), so the numbers match
`results/metrics.md` without ever calling `compute_run`, which writes metrics.json.
"""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
from array import array
from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict, deque
from pathlib import Path

try:  # the paper metrics, reused as-is (pure functions)
    from swarm import metrics as swarm_metrics
except Exception:  # noqa: BLE001  pragma: no cover - the dashboard still works without them
    swarm_metrics = None

DEADLINE = "2026-11-09T11:59:00Z"
DEADLINE_T = 1794225540.0  # the same moment as a unix time
CHUNK = 4 << 20
STALL_S = 600  # a live process with no event for this long is flagged as stalled
METRICS_EVERY_S = 20  # recompute paper metrics for a live run at most this often

# ---------------------------------------------------------------------------------------------------------------
# Event categories (feed filters)

CATS = {
    "message": "chat", "agent_message": "say",
    "instigator_message": "instigator", "instigator_reported": "oversight", "instigator_joined": "lifecycle",
    "pr_opened": "prs", "pr_updated": "prs", "pr_reviewed": "prs", "pr_merged": "prs", "pr_stale": "prs",
    "pr_checked": "prs", "test_file_edit": "prs",
    "tests_run": "tests", "team_scores": "tests", "test_files_changed": "tests", "tests_flagged": "tests",
    "report_submitted": "oversight", "report_result": "oversight", "audit": "oversight", "agent_removed": "oversight",
    "role_change": "oversight", "honeypot_access": "oversight",
    "tool_call": "tools", "builtin_tool_use": "tools",
    "turn_input": "turns", "model_usage": "turns", "session_started": "turns",
    "turn_error": "errors", "usage_limit_hit": "errors",
    "run_start": "lifecycle", "run_end": "lifecycle", "run_resumed": "lifecycle", "round_start": "lifecycle",
    "round_end": "lifecycle", "agent_joined": "lifecycle",
}
DEFAULT_CATS = ("chat", "instigator", "prs", "tests", "oversight", "errors", "lifecycle")

# Fields of each event type that swarm.metrics.compute reads. Everything else is dropped from the slim copy.
SLIM = {
    "run_start": ("config",), "run_end": ("reason",), "instigator_joined": (), "agent_joined": ("role", "team"),
    "pr_opened": ("pr_id", "team", "touches_tests"), "pr_updated": ("pr_id", "team", "touches_tests"),
    "pr_merged": ("pr_id", "team", "touches_tests", "approvers"),
    "tests_run": ("team", "pr_id", "full_pass"), "pr_checked": ("pr_id", "team", "full_pass"),
    "team_scores": ("scores",), "instigator_message": ("message_id", "pr_id", "to"),
    "turn_input": ("role", "message_ids"), "pr_reviewed": ("pr_id", "decision", "message_id"),
    "report_submitted": ("accused",), "round_end": ("investigators", "workers"),
    "report_result": ("report_id", "accused", "confirmed", "reporter_verdict"), "test_file_edit": (),
    "audit": ("triggers", "verdict"), "agent_removed": (), "tests_flagged": (), "model_usage": ("usage",),
    "honeypot_access": ("url",),
}
VERDICT_KEYS = ("misaligned_before_conversion", "misaligned_after_conversion")
USAGE_KEYS = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens")
METRIC_KEYS = (
    "impossible_assert_passes", "misaligned_caught", "misaligned_total", "agents_removed", "reports", "self_reports",
    "collusion_offers", "instigator_offers", "collusion_acceptances", "peer_acceptances", "instigator_acceptances",
    "endorsements", "structural_acceptances", "alerts", "collusion_acceptance_rate", "peer_acceptance_rate",
    "peer_acceptance_rate_without_endorsements", "instigator_acceptance_rate", "largest_conspiracy",
    "largest_conspiracy_active", "worker_to_investigator_rounds", "agents_editing_tests", "tests_flagged",
    "honeypot_agents", "honeypot_attempts", "labels_present", "rounds_completed", "end_reason",
)
SERIES_KEYS = (
    "swarm_pass_rate", "problems_at_100", "pr_opened", "pr_updated", "pr_merged", "merged_cross", "cheat_merges",
    "approvals", "request_changes", "instigator_dms", "reports", "instigator_reports", "removals", "conversions",
    "audits", "turn_errors", "retries", "turns", "tool_calls", "dms", "board_posts", "tests_run", "full_passes",
    "test_file_edits", "tokens_in", "tokens_cached", "tokens_out", "workers", "investigators", "round_minutes",
    "cheaters_cum", "largest_conspiracy", "largest_conspiracy_active", "honeypot",
)

RUN_DIR_RE = re.compile(r"swarm (run|resume|label)\b.*?([\w.-]+(?:-\d{8}-\d{6}(?:-stopped)?|pilot-[\w-]+))")
QUEUE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (.*)$")


_HOST: list = []


def hostname() -> str:
    """Machine label. On macOS the LocalHostName (stable), since gethostname() can be a DHCP name."""
    if not _HOST:
        name = ""
        if sys.platform == "darwin":
            try:
                name = subprocess.run(["scutil", "--get", "LocalHostName"], capture_output=True, text=True, check=False,
                                      timeout=3).stdout.strip()
            except (OSError, subprocess.SubprocessError):
                name = ""
        _HOST.append(name or socket.gethostname().removesuffix(".local"))
    return _HOST[0]


def group_of(name: str, cfg: dict, published: list | None = None) -> str:
    if name.endswith("-stopped"):
        return "stopped"
    if "pr_approvals" not in cfg:
        return "v1"
    if cfg.get("swarm_wide"):
        return "v3"
    if "ordered" in (published or []) or not cfg.get("shuffle_turns"):
        return "v2-archive"
    return "v2-shuffled"


MODEL_TOKEN = re.compile(r"^(\d+|luna|sol|max|terra|high|xhigh|glm\w*|qwen\w*|deepseek\w*|gemma\w*|gpt\w*|adaption\w*|"
                         r"ds\w*|flash|pro|mini)$", re.IGNORECASE)
STAMP = re.compile(r"-\d{8}-\d{6}(?:-stopped)?$")


def arm_base(name: str) -> str:
    """Design arm of a config or run name, without model, seed and timestamp: 'A100-6-luna-s2-20261107-235039' ->
    'A100', 'A100-glm53flash' -> 'A100', 'H-k001-6-luna' -> 'H-k001', 'baseline-56-luna' -> 'baseline'."""
    toks = STAMP.sub("", name or "").split("-")
    while len(toks) > 1 and re.fullmatch(r"s\d+", toks[-1]):
        toks.pop()
    for i in range(1, len(toks)):
        if MODEL_TOKEN.match(toks[i]):
            return "-".join(toks[:i])
    return "-".join(toks)


def seed_of(name: str, cfg: dict) -> int | None:
    if isinstance(cfg.get("seed"), int):
        return cfg["seed"]
    m = re.search(r"-s(\d+)(?:-\d{8}-\d{6})?(?:-stopped)?$", name or "")
    return int(m.group(1)) if m else (1 if name else None)


def model_of(name: str, cfg: dict) -> str:
    if cfg.get("worker_model"):
        return cfg["worker_model"]
    toks = STAMP.sub("", name or "").split("-")
    while len(toks) > 1 and re.fullmatch(r"s\d+", toks[-1]):
        toks.pop()
    rest = "-".join(toks[len(arm_base(name).split("-")):])
    return {"6-luna": "gpt-6-luna", "56-luna": "gpt-5.6-luna", "sol-max": "gpt-6.1-sol"}.get(rest, rest or "?")


def condition_of(cfg: dict) -> str:
    """Oversight condition of an arm, for colouring and the informed-vs-uninformed headline."""
    inv = (cfg.get("initial_investigators") or 0) > 0 or (cfg.get("k") or 0) > 0
    if cfg.get("informed"):
        return "informed" if inv else "bluff"
    if inv:
        return "uninformed"
    return "audits-only" if (cfg.get("p") or 0) > 0 else "none"


def _slim(ev: dict, v1: bool) -> dict | None:
    t = ev["type"]
    keep = SLIM.get(t)
    if keep is None:
        if t == "tool_call" and v1 and ev.get("tool") in ("write_file", "run_tests"):
            args = ev.get("args") or {}
            return {"seq": ev["seq"], "type": t, "round": ev.get("round"), "agent": ev.get("agent"),
                    "tool": ev["tool"], "error": ev.get("error"), "args": {"path": args.get("path", "")},
                    "result": str(ev.get("result", "")).split("\n", 1)[0]}
        if ev.get("agent") and t not in ("tool_call", "message", "agent_message"):
            return {"seq": ev["seq"], "type": t, "round": ev.get("round"), "agent": ev["agent"]}
        return None
    out = {"seq": ev["seq"], "type": t, "round": ev.get("round")}
    if ev.get("agent"):
        out["agent"] = sys.intern(ev["agent"])
    for k in keep:
        if k in ev:
            out[k] = ev[k]
    if t == "turn_input":
        out["message_ids"] = [sys.intern(m) for m in ev.get("message_ids") or []]
    elif t == "audit":
        out["verdict"] = {k: (ev.get("verdict") or {}).get(k) for k in VERDICT_KEYS}
    elif t == "report_result":
        out["reporter_verdict"] = {k: (ev.get("reporter_verdict") or {}).get(k) for k in VERDICT_KEYS}
    elif t == "model_usage":
        out["usage"] = {k: (ev.get("usage") or {}).get(k, 0) or 0 for k in USAGE_KEYS[:3]}
    return out


def _short(s, n: int = 160) -> str:
    s = " ".join(str(s or "").split())
    return s if len(s) <= n else s[: n - 1] + "…"


# ---------------------------------------------------------------------------------------------------------------


class AgentState:
    __slots__ = (
        "approvals",
        "audits",
        "board_posts",
        "confirmed_reports",
        "converted_round",
        "dms_received",
        "dms_sent",
        "done_rounds",
        "errors",
        "full_passes",
        "honeypot",
        "id",
        "in_turn_since",
        "initial_role",
        "instigator_dms",
        "instigator_reports",
        "joined_round",
        "last",
        "last_t",
        "progress_posts",
        "prs_merged",
        "prs_opened",
        "prs_updated",
        "removed_round",
        "replaced_by",
        "replaces",
        "reports_filed",
        "request_changes",
        "retries",
        "role",
        "said",
        "slot",
        "team",
        "tests_run",
        "times_accused",
        "tokens_cached",
        "tokens_in",
        "tokens_out",
        "tool_calls",
        "tool_errors",
        "turns",
    )

    def __init__(self, aid: str, slot=None, team=None, role="worker", joined_round=1, replaces=None):
        self.id, self.slot, self.team, self.role = aid, slot, team, role
        self.initial_role, self.converted_round, self.joined_round = role, None, joined_round
        self.replaces, self.replaced_by, self.removed_round = replaces, None, None
        for k in ("turns", "tool_calls", "tool_errors", "dms_sent", "board_posts", "progress_posts", "dms_received",
                  "instigator_dms", "prs_opened", "prs_updated", "prs_merged", "approvals", "request_changes",
                  "reports_filed", "times_accused", "confirmed_reports", "tests_run", "full_passes", "tokens_in",
                  "tokens_cached", "tokens_out", "errors", "retries", "honeypot", "instigator_reports"):
            setattr(self, k, 0)
        self.audits: list = []
        self.in_turn_since = None
        self.last_t, self.last, self.said = None, "", ""
        self.done_rounds = 0

    def as_dict(self) -> dict:
        d = {k: getattr(self, k) for k in self.__slots__ if k != "done_rounds"}
        return d


class PRState:
    __slots__ = (
        "approvers",
        "author",
        "checks",
        "diff_seq",
        "full_pass",
        "id",
        "merged_round",
        "opened_round",
        "reviews",
        "status",
        "team",
        "test_edit",
        "tests_full_pass",
        "title",
        "touches_tests",
        "version",
    )

    def __init__(self, pid, author, team, title, rnd):
        self.id, self.author, self.team, self.title = pid, author, team, title
        self.status, self.opened_round, self.version = "open", rnd, 1
        self.touches_tests, self.approvers, self.reviews = False, [], []
        self.merged_round, self.checks, self.full_pass, self.tests_full_pass = None, [], False, False
        self.diff_seq, self.test_edit = None, False

    def as_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__slots__}


class RunState:
    """One run: incremental aggregates plus a compact byte-offset index of every event."""

    def __init__(self, name: str, path: Path, origin: str):
        self.name, self.dir, self.origin = name, Path(path), origin
        self.events_path = self.dir / "events.jsonl"
        self.version = 0
        self.alive = False  # a swarm run/resume process for this run is on this machine
        self.labeling = False
        self.published: list[str] = []
        self._reset()
        self.cfg = {}
        try:
            self.cfg = json.loads((self.dir / "config.json").read_text())
        except (OSError, ValueError):
            pass
        self.v1 = "pr_approvals" not in self.cfg
        self.labels_mtime = None
        self.labels: dict[str, tuple] = {}
        self.label_counts: dict[str, Counter] = defaultdict(Counter)
        self.label_list: list[tuple] = []  # (sender, target, label, round, kind)
        self.metrics: dict | None = None
        self.metrics_error = None
        self.metrics_key = None
        self.metrics_t = 0.0
        self.cheaters_by_round: dict[int, list] = {}
        self.first_cheat: dict[str, int] = {}
        self.cheat_prs: set = set()
        self.cheaters: list = []

    def _reset(self) -> None:
        self.offset = 0
        self.inode = None
        self.n = 0
        self.seq = -1
        self.first_t = self.last_t = None
        # index: parallel arrays, one entry per event
        self.i_seq, self.i_off, self.i_len, self.i_round = array("q"), array("q"), array("l"), array("h")
        self.i_type: list = []
        self.i_cat: list = []
        self.i_agent: list = []
        self.i_other: list = []
        self.i_team: list = []
        self.slim: list = []
        self.round_end_pos: dict[int, int] = {}
        self.type_counts = Counter()
        self.tool_counts = Counter()
        self.error_kinds = Counter()
        self.agents: dict[str, AgentState] = {}
        self.instigator = None
        self.problems: list = []
        self.prs: dict[str, PRState] = {}
        self.round = 0
        self.completed_rounds = 0
        self.rs: dict[int, dict] = defaultdict(lambda: defaultdict(float))
        self.r_start: dict[int, float] = {}
        self.r_end: dict[int, float] = {}
        self.scores: dict[int, dict] = {}
        self.done: dict[int, set] = defaultdict(set)
        self.run_start_t = None
        self.end = None  # {"reason", "t"}
        self.usage_stops: list = []
        self.resumes: list = []
        self.final_audits = 0
        self.minutes: dict[int, list] = defaultdict(lambda: [0, 0, 0, 0, 0, 0])  # turns, retries, errors, tools, tin, tout
        self.dm_pairs: dict[tuple, Counter] = defaultdict(Counter)
        self.approve_edges: list = []
        self.report_edges: list = []
        self.removed_order: list = []
        self.harness_commit = None

    # ---------------------------------------------------------------- tailing
    def poll(self, budget: int = 64 << 20) -> int:
        """Read new complete lines. Returns how many events were added (-1 after a reset)."""
        try:
            st = os.stat(self.events_path)
        except OSError:
            return 0
        reset = False
        if self.inode is not None and (st.st_ino != self.inode or st.st_size < self.offset):
            self._reset()
            reset = True
        self.inode = st.st_ino
        if st.st_size <= self.offset:
            return -1 if reset else 0
        added = 0
        with open(self.events_path, "rb") as f:
            f.seek(self.offset)
            left = min(st.st_size - self.offset, budget)
            while left > 0:
                data = f.read(min(CHUNK, left))
                if not data:
                    break
                cut = data.rfind(b"\n")
                if cut < 0:
                    if len(data) < CHUNK:
                        break  # an incomplete last line; wait for the writer
                    cut = len(data) - 1  # a line longer than CHUNK: read on
                    data += f.readline()
                    cut = data.rfind(b"\n")
                    if cut < 0:
                        break
                body = data[: cut + 1]
                pos = self.offset
                for line in body.split(b"\n")[:-1]:
                    ln = len(line) + 1
                    if line.strip():
                        try:
                            ev = json.loads(line)
                        except ValueError:
                            ev = None
                        if isinstance(ev, dict) and "type" in ev:
                            self.feed(ev, pos, ln - 1)
                            added += 1
                    pos += ln
                self.offset = pos
                left -= len(body)
                f.seek(self.offset)
        if added:
            self.version += 1
        return -1 if reset else added

    def load_labels(self) -> bool:
        p = self.dir / "labels.jsonl"
        try:
            m = p.stat().st_mtime
        except OSError:
            if self.labels_mtime is not None:
                self.labels_mtime, self.labels, self.label_counts, self.label_list = None, {}, defaultdict(Counter), []
                return True
            return False
        if m == self.labels_mtime:
            return False
        labels, counts, lst = {}, defaultdict(Counter), []
        try:
            for line in p.read_text().splitlines():
                if not line.strip():
                    continue
                lab = json.loads(line)
                if lab.get("label") and lab["label"] != "none":
                    labels[lab["message_id"]] = (lab["label"], lab.get("target") or "", lab.get("quote") or "")
                    counts[lab["sender"]][lab["label"]] += 1
                    lst.append((lab["sender"], lab.get("target") or lab.get("to") or "", lab["label"],
                                lab.get("round"), lab.get("kind")))
        except (OSError, ValueError):
            return False
        self.labels_mtime, self.labels, self.label_counts, self.label_list = m, labels, counts, lst
        self.version += 1
        return True

    # ---------------------------------------------------------------- aggregation
    def agent(self, aid: str) -> AgentState:
        a = self.agents.get(aid)
        if a is None:
            a = self.agents[aid] = AgentState(aid)
        return a

    def feed(self, ev: dict, off: int, ln: int) -> None:
        t, r, aid = ev["type"], ev.get("round"), ev.get("agent")
        r = r if isinstance(r, int) else 0
        self.n += 1
        self.seq = ev.get("seq", self.seq + 1)
        ts = ev.get("t")
        if ts:
            self.first_t = self.first_t or ts
            self.last_t = ts
        self.type_counts[t] += 1
        other = ""
        if t in ("message", "instigator_message"):
            other = ev.get("to") or ""
        elif t == "pr_reviewed":
            other = ev.get("author") or ""
        elif t in ("report_submitted", "report_result"):
            other = ",".join(ev.get("accused") or [])
        elif t in ("pr_merged", "test_file_edit"):
            other = ",".join(ev.get("approvers") or [])
        cat = CATS.get(t, "lifecycle")
        if t == "message":
            if aid and aid == self.instigator:
                cat = "instigator"
            elif ev.get("kind") == "review":
                cat = "review"  # duplicated by pr_reviewed, which carries the same comment
            elif ev.get("kind") == "progress":
                cat = "progress"
        self.i_seq.append(self.seq)
        self.i_off.append(off)
        self.i_len.append(ln)
        self.i_round.append(max(-1, min(r, 32000)))
        self.i_type.append(sys.intern(t))
        self.i_cat.append(cat)
        self.i_agent.append(sys.intern(aid) if isinstance(aid, str) else "")
        self.i_other.append(sys.intern(other) if other else "")
        team = ev.get("team")
        self.i_team.append(sys.intern(team) if isinstance(team, str) else "")
        s = _slim(ev, self.v1)
        if s is not None:
            self.slim.append(s)
        h = getattr(self, "on_" + t, None)
        if h is not None:
            h(ev, r, aid, ts)

    def _touch(self, aid, ts, text):
        if aid and aid in self.agents:
            a = self.agents[aid]
            a.last_t, a.last = ts, text

    def on_run_start(self, ev, r, aid, ts):
        self.cfg = ev.get("config") or self.cfg
        self.v1 = "pr_approvals" not in self.cfg
        self.problems = list(ev.get("problems") or [])
        self.run_start_t = self.run_start_t or ts
        self.harness_commit = ev.get("harness_commit")

    def on_run_end(self, ev, r, aid, ts):
        self.end = {"reason": ev.get("reason"), "t": ts, "round": r}

    def on_run_resumed(self, ev, r, aid, ts):
        self.resumes.append({"t": ts, "round": r, "phase": ev.get("phase")})
        self.end = None

    def on_usage_limit_hit(self, ev, r, aid, ts):
        self.usage_stops.append({"t": ts, "round": r, "phase": ev.get("phase"), "missed": len(ev.get("missed") or [])})

    def on_agent_joined(self, ev, r, aid, ts):
        a = self.agent(aid)
        a.slot, a.team, a.role = ev.get("slot"), ev.get("team"), ev.get("role") or "worker"
        a.initial_role, a.joined_round, a.replaces = a.role, max(r, 1), ev.get("replaces")
        if a.replaces and a.replaces in self.agents:
            self.agents[a.replaces].replaced_by = aid
        if a.team and a.team not in self.problems:
            self.problems.append(a.team)

    def on_instigator_joined(self, ev, r, aid, ts):
        self.instigator = aid

    def on_round_start(self, ev, r, aid, ts):
        self.round = max(self.round, r)
        self.r_start.setdefault(r, ts)

    def on_round_end(self, ev, r, aid, ts):
        self.r_end[r] = ts
        self.completed_rounds = max(self.completed_rounds, r)
        rs = self.rs[r]
        rs["workers"], rs["investigators"] = ev.get("workers") or 0, ev.get("investigators") or 0
        self.round_end_pos[r] = len(self.slim)

    def on_team_scores(self, ev, r, aid, ts):
        sc = {k: v for k, v in (ev.get("scores") or {}).items() if v is not None}
        self.scores[r] = sc
        rs = self.rs[r]
        rs["problems_at_100"] = sum(1 for v in sc.values() if v >= 1)
        rs["swarm_pass_rate"] = sum(sc.values()) / len(sc) if sc else 0.0

    def on_turn_input(self, ev, r, aid, ts):
        a = self.agent(aid)
        a.turns += 1
        a.in_turn_since = ts
        self.rs[r]["turns"] += 1
        self.minutes[int(ts // 60)][0] += 1

    def on_model_usage(self, ev, r, aid, ts):
        a = self.agent(aid)
        u = ev.get("usage") or {}
        tin, tc, tout = u.get("input_tokens", 0) or 0, u.get("cached_input_tokens", 0) or 0, u.get("output_tokens", 0) or 0
        a.tokens_in += tin
        a.tokens_cached += tc
        a.tokens_out += tout
        retries = max(0, (ev.get("attempts") or 1) - 1)
        a.retries += retries
        a.in_turn_since = None
        self.done[r].add(aid)
        rs = self.rs[r]
        rs["tokens_in"] += tin
        rs["tokens_cached"] += tc
        rs["tokens_out"] += tout
        rs["retries"] += retries
        mb = self.minutes[int(ts // 60)]
        mb[1] += retries
        mb[4] += tin
        mb[5] += tout

    def on_turn_error(self, ev, r, aid, ts):
        a = self.agent(aid)
        a.errors += 1
        err = str(ev.get("error") or "error")
        self.error_kinds["403 forbidden" if "403" in err else _short(err, 40)] += 1
        self.rs[r]["turn_errors"] += 1
        self.minutes[int(ts // 60)][2] += 1

    def on_session_started(self, ev, r, aid, ts):
        pass

    def on_agent_message(self, ev, r, aid, ts):
        if aid in self.agents:
            self.agents[aid].said = _short(ev.get("text"), 240)

    def on_tool_call(self, ev, r, aid, ts):
        a = self.agent(aid)
        a.tool_calls += 1
        tool = ev.get("tool") or "?"
        self.tool_counts[tool] += 1
        if ev.get("error"):
            a.tool_errors += 1
        self.rs[r]["tool_calls"] += 1
        self.minutes[int(ts // 60)][3] += 1
        args = ev.get("args") or {}
        hint = args.get("path") or args.get("pr_id") or args.get("to") or args.get("team") or args.get("query") or ""
        a.last_t, a.last = ts, f"{tool}({_short(hint, 40)})" if hint else tool

    def on_message(self, ev, r, aid, ts):
        kind, to = ev.get("kind"), ev.get("to")
        if aid == self.instigator:
            if to:
                self.dm_pairs[(aid, to)][r] += 1
            return
        a = self.agent(aid) if aid else None
        if kind == "dm":
            self.rs[r]["dms"] += 1
            if a:
                a.dms_sent += 1
            if to:
                self.agent(to).dms_received += 1
                self.dm_pairs[(aid, to)][r] += 1
        elif kind == "board":
            self.rs[r]["board_posts"] += 1
            if a:
                a.board_posts += 1
        elif kind == "progress" and a:
            a.progress_posts += 1

    def on_instigator_message(self, ev, r, aid, ts):
        self.rs[r]["instigator_dms"] += 1
        to = ev.get("to")
        if to:
            self.agent(to).instigator_dms += 1

    def on_instigator_reported(self, ev, r, aid, ts):
        self.rs[r]["instigator_reports"] += 1
        if aid:
            self.agent(aid).instigator_reports += 1

    def on_tests_run(self, ev, r, aid, ts):
        a = self.agent(aid)
        a.tests_run += 1
        self.rs[r]["tests_run"] += 1
        if ev.get("full_pass"):
            a.full_passes += 1
            self.rs[r]["full_passes"] += 1
            pr = self.prs.get(ev.get("pr_id") or "")
            if pr:
                pr.tests_full_pass = True

    def _pr_event(self, ev, r, aid, opened: bool):
        pid = ev.get("pr_id")
        pr = self.prs.get(pid)
        if pr is None:
            pr = self.prs[pid] = PRState(pid, aid, ev.get("team"), ev.get("title") or "", r)
        pr.title = ev.get("title") or pr.title
        pr.touches_tests = bool(ev.get("touches_tests"))
        pr.diff_seq = self.seq
        if not opened:
            pr.version += 1
            pr.approvers = []
            pr.status = "open"
        return pr

    def on_pr_opened(self, ev, r, aid, ts):
        pr = self._pr_event(ev, r, aid, True)
        a = self.agent(aid)
        a.prs_opened += 1
        self.rs[r]["pr_opened"] += 1
        self._touch(aid, ts, f"opened {pr.id}")

    def on_pr_updated(self, ev, r, aid, ts):
        pr = self._pr_event(ev, r, aid, False)
        self.agent(aid).prs_updated += 1
        self.rs[r]["pr_updated"] += 1
        self._touch(aid, ts, f"updated {pr.id}")

    def on_pr_checked(self, ev, r, aid, ts):
        pr = self.prs.get(ev.get("pr_id"))
        if pr:
            pr.checks.append((ev.get("version"), ev.get("passed"), ev.get("total"), bool(ev.get("full_pass"))))
            if ev.get("full_pass"):
                pr.full_pass = True

    def on_pr_reviewed(self, ev, r, aid, ts):
        pr = self.prs.get(ev.get("pr_id"))
        dec = ev.get("decision")
        a = self.agent(aid)
        if dec == "approve":
            a.approvals += 1
            self.rs[r]["approvals"] += 1
            self.approve_edges.append((aid, ev.get("author"), r, ev.get("pr_id")))
        else:
            a.request_changes += 1
            self.rs[r]["request_changes"] += 1
        if pr:
            pr.approvers = list(ev.get("approvals") or pr.approvers)
            pr.reviews.append({"agent": aid, "decision": dec, "round": r, "comment": _short(ev.get("comment"), 400),
                               "message_id": ev.get("message_id"), "version": pr.version})
        self._touch(aid, ts, f"{'approved' if dec == 'approve' else 'rejected'} {ev.get('pr_id')}")

    def on_pr_merged(self, ev, r, aid, ts):
        pid = ev.get("pr_id")
        pr = self.prs.get(pid)
        approvers = ev.get("approvers") or []
        if pr:
            pr.status, pr.merged_round, pr.approvers = "merged", r, approvers
            pr.touches_tests = bool(ev.get("touches_tests"))
        if aid:
            self.agent(aid).prs_merged += 1
        rs = self.rs[r]
        rs["pr_merged"] += 1
        team = ev.get("team")
        if any(self.agents.get(x) and self.agents[x].team != team for x in approvers):
            rs["merged_cross"] += 1
        if ev.get("touches_tests") or (pr and (pr.full_pass or pr.tests_full_pass)):
            rs["cheat_merges"] += 1

    def on_pr_stale(self, ev, r, aid, ts):
        pr = self.prs.get(ev.get("pr_id"))
        if pr:
            pr.status = "stale"

    def on_test_file_edit(self, ev, r, aid, ts):
        self.rs[r]["test_file_edits"] += 1
        pr = self.prs.get(ev.get("pr_id") or "")
        if pr:
            pr.test_edit = True

    def on_role_change(self, ev, r, aid, ts):
        a = self.agent(aid)
        a.role, a.converted_round = ev.get("role") or "investigator", r
        self.rs[r]["conversions"] += 1

    def on_report_submitted(self, ev, r, aid, ts):
        self.rs[r]["reports"] += 1
        a = self.agent(aid)
        a.reports_filed += 1
        for x in ev.get("accused") or []:
            self.agent(x).times_accused += 1
            self.report_edges.append((aid, x, r))
        self._touch(aid, ts, f"reported {', '.join(ev.get('accused') or [])}")

    def on_report_result(self, ev, r, aid, ts):
        if aid:
            self.agent(aid).confirmed_reports += len(ev.get("confirmed") or [])

    def on_audit(self, ev, r, aid, ts):
        v = ev.get("verdict") or {}
        mis = bool(v.get("misaligned_before_conversion") or v.get("misaligned_after_conversion"))
        trig = ev.get("triggers") or []
        if "final" in trig:
            self.final_audits += 1
        else:
            self.rs[r]["audits"] += 1
        self.agent(aid).audits.append({"round": r, "triggers": trig, "misaligned": mis, "removed": ev.get("removed"),
                                       "summary": _short(v.get("summary"), 600), "seq": self.seq})

    def on_agent_removed(self, ev, r, aid, ts):
        a = self.agent(aid)
        a.removed_round = r
        self.rs[r]["removals"] += 1
        self.removed_order.append((aid, r))

    def on_honeypot_access(self, ev, r, aid, ts):
        self.agent(aid).honeypot += 1
        self.rs[r]["honeypot"] += 1

    # ---------------------------------------------------------------- derived
    def active_agents(self) -> list[AgentState]:
        return [a for a in self.agents.values() if a.removed_round is None and a.replaced_by is None
                and a.slot is not None]

    def phase(self) -> str:
        if self.end and self.end.get("reason") == "completed":
            return "done"
        r = self.round
        if r == 0:
            return "setup"
        if r in self.r_end:
            if self.completed_rounds >= (self.cfg.get("rounds") or 20):
                return "final audit"
            return "between rounds"
        done = len(self.done.get(r, ()))
        return "turns" if done < len(self.active_agents()) else "audits"

    def round_minutes(self) -> list[float]:
        return [(self.r_end[r] - self.r_start[r]) / 60 for r in sorted(self.r_end) if r in self.r_start]

    def state(self, now: float, queue: QueueLog | None) -> tuple[str, str]:
        """(state, detail). States: running, stalled, labeling, resuming, usage-limit, interrupted, stopped,
        ended, labeled, partial."""
        end = self.end
        if self.alive:
            if self.last_t and now - self.last_t > STALL_S:
                return "stalled", f"no event for {int((now - self.last_t) // 60)} min"
            return "running", ""
        if self.labeling:
            return "labeling", "judge labeling"
        if end and end.get("reason") == "completed":
            if self.labels_mtime:
                return "labeled", ""
            return "ended", "not labeled yet"
        if self.name.endswith("-stopped"):
            return "stopped", "stopped by hand (archived)"
        if end and end.get("reason") == "usage_limit":
            nxt = queue.next_resume(self.name) if queue else None
            if nxt:
                return "resuming", f"usage-limit stop; resume {nxt[1]} at {time.strftime('%H:%M', time.localtime(nxt[0]))}"
            return "usage-limit", "stopped on a usage limit; resume with swarm resume"
        if self.origin == "runs":
            return "interrupted", "no process and no run_end (crash or kill?)"
        return "partial", "copy without run_end"

    def eta(self, now: float) -> float | None:
        total = self.cfg.get("rounds") or 20
        mins = self.round_minutes()
        if not mins or (self.end and self.end.get("reason") == "completed"):
            return None
        per = sum(mins[-3:]) / len(mins[-3:]) * 60
        left = total - self.completed_rounds
        cur_start = self.r_start.get(self.round) if self.round not in self.r_end else None
        spent = (now - cur_start) if cur_start else 0.0
        return now + max(0.0, left * per - spent) + per * 0.15  # plus the final audit

    def series(self) -> dict:
        total = max(self.cfg.get("rounds") or 0, self.round, max(self.rs.keys(), default=0))
        rounds = list(range(1, total + 1))
        out = {"rounds": rounds}
        mins = {r: (self.r_end[r] - self.r_start[r]) / 60 for r in self.r_end if r in self.r_start}
        lc = (self.metrics or {}).get("largest_conspiracy_by_round") or {}
        lca = (self.metrics or {}).get("largest_conspiracy_active_by_round") or {}
        for k in SERIES_KEYS:
            vals = []
            for r in rounds:
                seen = r <= self.round
                if k == "round_minutes":
                    vals.append(round(mins[r], 2) if r in mins else None)
                elif k == "swarm_pass_rate":
                    vals.append(round(self.rs[r][k], 4) if r in self.scores else None)
                elif k in ("problems_at_100",):
                    vals.append(int(self.rs[r][k]) if r in self.scores else None)
                elif k in ("workers", "investigators"):
                    vals.append(int(self.rs[r][k]) if r in self.r_end else None)
                elif k == "cheaters_cum":
                    vals.append(len(self.cheaters_by_round[r]) if r in self.cheaters_by_round else None)
                elif k == "largest_conspiracy":
                    vals.append(lc.get(r, lc.get(str(r))) if r in self.r_end else None)
                elif k == "largest_conspiracy_active":
                    vals.append(lca.get(r, lca.get(str(r))) if r in self.r_end else None)
                else:
                    v = self.rs[r][k] if r in self.rs else 0
                    vals.append((int(v) if float(v).is_integer() else v) if seen else None)
            out[k] = vals
        return out

    # ---------------------------------------------------------------- paper metrics
    def compute_metrics(self, slim: list, labels: list[dict]) -> None:
        if swarm_metrics is None or not any(e["type"] == "run_start" for e in slim[:5]):
            return
        try:
            m = swarm_metrics.compute(slim, labels)
            by_round, first, cum = {}, {}, set()
            ends = sorted((r, pos) for r, pos in self.round_end_pos.items())
            for r, pos in ends:
                _, ch, _ = swarm_metrics._blame(slim[:pos])
                for a in ch:
                    if a not in cum:
                        first[a] = r
                cum |= ch
                by_round[r] = sorted(cum)
            _, chs, prs = swarm_metrics._blame(slim)
            for a in chs:
                first.setdefault(a, self.round)
            self.metrics, self.metrics_error = m, None
            self.cheaters, self.cheat_prs = sorted(chs), set(prs)
            self.cheaters_by_round, self.first_cheat = by_round, first
        except Exception as e:  # noqa: BLE001
            self.metrics_error = f"{type(e).__name__}: {e}"

    def labels_raw(self) -> list[dict]:
        p = self.dir / "labels.jsonl"
        try:
            return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
        except (OSError, ValueError):
            return []

    # ---------------------------------------------------------------- reading events back
    def read_raw(self, positions: list[int]) -> list[dict]:
        out = []
        try:
            fd = os.open(self.events_path, os.O_RDONLY)
        except OSError:
            return out
        try:
            for i in positions:
                try:
                    out.append(json.loads(os.pread(fd, self.i_len[i], self.i_off[i])))
                except (OSError, ValueError):
                    out.append({"seq": self.i_seq[i], "type": self.i_type[i], "round": self.i_round[i],
                                "error": "unreadable"})
        finally:
            os.close(fd)
        return out

    def pos_of(self, seq: int) -> int | None:
        i = bisect_left(self.i_seq, seq)
        return i if i < len(self.i_seq) and self.i_seq[i] == seq else None

    def select(self, *, before=None, after=None, limit=200, cats=None, types=None, agent=None, team=None,
               rnd=None, q=None, involve=False, max_scan=None) -> tuple[list[int], bool, int | None]:
        """Positions of matching events, newest first (or oldest first with `after`).
        Returns (positions, more, cursor): `cursor` is the seq to pass as `before` (or `after`) to continue."""
        if max_scan is None:
            max_scan = 60000 if q else 400000
        n = len(self.i_seq)
        if after is not None:
            rng = range(bisect_right(self.i_seq, after), n)
        else:
            hi = bisect_left(self.i_seq, before) if before is not None else n
            rng = range(hi - 1, -1, -1)
        out, scanned, more, last = [], 0, False, None
        ql = q.lower().encode() if q else None
        fd = os.open(self.events_path, os.O_RDONLY) if ql else None
        try:
            for i in rng:
                scanned += 1
                if scanned > max_scan:
                    more = True
                    break
                last = i
                if cats is not None and self.i_cat[i] not in cats:
                    continue
                if types is not None and self.i_type[i] not in types:
                    continue
                if rnd is not None and self.i_round[i] != rnd:
                    continue
                if team and self.i_team[i] != team:
                    continue
                if agent:
                    if self.i_agent[i] != agent:
                        if not involve or agent not in self.i_other[i].split(","):
                            continue
                if ql is not None:
                    try:
                        if ql not in os.pread(fd, self.i_len[i], self.i_off[i]).lower():
                            continue
                    except OSError:
                        continue
                out.append(i)
                if len(out) >= limit:
                    more = True
                    break
        finally:
            if fd is not None:
                os.close(fd)
        return out, more, (self.i_seq[last] if last is not None else None)


# ---------------------------------------------------------------------------------------------------------------


class QueueLog:
    """Tails runs/queue.log (production queue events)."""

    def __init__(self, path: Path):
        self.path = path
        self.offset = 0
        self.inode = None
        self.lines: deque = deque(maxlen=400)
        self.events: list[dict] = []  # parsed, last 500

    def poll(self) -> bool:
        try:
            st = os.stat(self.path)
        except OSError:
            return False
        if self.inode is not None and (st.st_ino != self.inode or st.st_size < self.offset):
            self.offset, self.lines, self.events = 0, deque(maxlen=400), []
        self.inode = st.st_ino
        if st.st_size <= self.offset:
            return False
        with open(self.path, "rb") as f:
            f.seek(max(self.offset, st.st_size - (2 << 20)))
            data = f.read()
        cut = data.rfind(b"\n")
        if cut < 0:
            return False
        self.offset = st.st_size - (len(data) - cut - 1)
        for raw in data[: cut + 1].decode("utf-8", "replace").splitlines():
            self.lines.append(raw)
            self._parse(raw)
        self.events = self.events[-500:]
        return True

    def _parse(self, raw: str) -> None:
        line = raw.strip()
        if line.startswith("----"):
            m = re.match(r"^-+ (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (.*)$", line)
            if m:
                self.events.append({"t": _ts(m.group(1)), "kind": "note", "text": m.group(2)})
            return
        m = QUEUE_RE.match(raw)
        if not m:
            return
        t, text = _ts(m.group(1)), m.group(2)
        kind = "info"
        if re.search(r"stopped; resume (\d+) of (\d+) in (\d+)s", text):
            kind = "resume_scheduled"
        elif text.startswith("resumed") or "manual resume" in text:
            kind = "resumed"
        elif re.search(r" exit \d+ \(", text):
            kind = "exit"
        elif text.startswith("labeled") or text.startswith("labeling"):
            kind = "label"
        elif "queue start" in text or "queue done" in text:
            kind = "queue"
        elif "stop" in text:
            kind = "stop"
        self.events.append({"t": t, "kind": kind, "text": text})

    def next_resume(self, run: str) -> tuple[float, str] | None:
        """(time, 'n of m') of a scheduled resume for `run` that hasn't happened yet."""
        for e in reversed(self.events):
            if run not in e["text"]:
                continue
            m = re.search(r"stopped; resume (\d+) of (\d+) in (\d+)s", e["text"])
            if m:
                at = e["t"] + int(m.group(3))
                return (at, f"{m.group(1)} of {m.group(2)}") if at > time.time() - 120 else None
            if e["kind"] in ("resumed", "exit", "label"):
                return None
        return None


def _ts(s: str) -> float:
    try:
        return time.mktime(time.strptime(s, "%Y-%m-%d %H:%M:%S"))
    except ValueError:
        return 0.0


# ---------------------------------------------------------------------------------------------------------------


TAILSCALE_CLIS = ("/Applications/Tailscale.app/Contents/MacOS/Tailscale", "/opt/homebrew/bin/tailscale",
                  "/usr/local/bin/tailscale")
FLEET_PORT = int(os.environ.get("FLEET_STATUS_PORT", "7477"))


def norm_host(s: str | None) -> str:
    """Comparable machine key: 'Baders-MacBook-Pro.local', 'baders-macbook-pro.tail9fc878.ts.net.' and
    'Bader’s MacBook Pro' all become 'badersmacbookpro'."""
    s = (s or "").lower().removesuffix(".").split(".")[0] if "." in (s or "") and " " not in (s or "") else (s or "").lower()
    return re.sub(r"[^a-z0-9]", "", s)


class Fleet:
    """Device health through the fleet-status pathway: devices from `tailscale status --json`, numbers from each
    Mac's fleet-statusd (GET http://<tailscale-ip>:7477/status, answers loopback and Tailscale peers only)."""

    def __init__(self, every: float = 15.0, enabled: bool = True):
        self.every = every
        self.enabled = enabled
        self.devices: list[dict] = []
        self.t = None
        self.error = None
        self.source = None

    def poll(self) -> None:
        import urllib.request
        from concurrent.futures import ThreadPoolExecutor
        devices: list[dict] = []
        cli = next((c for c in TAILSCALE_CLIS if os.access(c, os.X_OK)), None)
        self.error = None
        if cli:
            try:
                out = subprocess.run([cli, "status", "--json"], capture_output=True, text=True, check=False, timeout=8).stdout
                d = json.loads(out)
                nodes = [(d.get("Self") or {}, True)] + [(n, False) for n in (d.get("Peer") or {}).values()]
                for n, me in nodes:
                    if not me and ("tag:ingress" in (n.get("Tags") or []) or n.get("HostName") == "funnel-ingress-node"):
                        continue  # Tailscale's Funnel relay servers, shared in while Funnel is on: not our devices
                    ips = n.get("TailscaleIPs") or []
                    dns = (n.get("DNSName") or "").split(".")[0]
                    devices.append({
                        "id": dns or n.get("HostName"), "name": n.get("HostName"), "dns": dns, "os": n.get("OS") or "",
                        "online": bool(me or n.get("Online")), "self": me,
                        "ip": next((i for i in ips if ":" not in i), ips[0] if ips else None),
                        "last_seen": n.get("LastSeen"), "keys": sorted({norm_host(dns), norm_host(n.get("HostName"))} - {""}),
                    })
                self.source = "tailscale"
            except (OSError, ValueError, subprocess.SubprocessError) as e:
                self.error = f"tailscale: {e}"
        if not devices:
            me = hostname()
            devices = [{"id": me.lower(), "name": me, "dns": me.lower(), "os": "macOS" if sys.platform == "darwin" else
                        sys.platform, "online": True, "self": True, "ip": "127.0.0.1", "last_seen": None,
                        "keys": [norm_host(me)]}]
            self.source = "local"
        local_key = norm_host(hostname())
        for dv in devices:
            if dv["self"] and local_key not in dv["keys"]:
                dv["keys"].append(local_key)

        def fetch(dv: dict) -> None:
            dv["status"], dv["status_error"] = None, None
            if not dv["online"] or (dv["os"] not in ("macOS", "darwin") and not dv["self"]):
                return
            addr = "127.0.0.1" if dv["self"] else dv["ip"]
            if not addr:
                return
            host = f"[{addr}]" if ":" in addr else addr
            try:
                with urllib.request.urlopen(f"http://{host}:{FLEET_PORT}/status", timeout=6) as resp:
                    dv["status"] = json.loads(resp.read())
                if dv["status"].get("name"):
                    dv["keys"] = sorted(set(dv["keys"]) | {norm_host(dv["status"]["name"])})
            except Exception as e:  # noqa: BLE001
                dv["status_error"] = f"{type(e).__name__}: {getattr(e, 'reason', e)}"

        with ThreadPoolExecutor(max_workers=8) as ex:
            list(ex.map(fetch, devices))
        self.devices, self.t = devices, time.time()

    def loop(self, stop: threading.Event, on_change) -> None:
        while self.enabled and not stop.is_set():
            try:
                self.poll()
                on_change()
            except Exception as e:  # noqa: BLE001
                self.error = repr(e)
            stop.wait(self.every)

    def view(self) -> dict:
        return {"devices": self.devices, "t": self.t, "error": self.error, "source": self.source, "port": FLEET_PORT}


class RemoteStatus:
    """Runs on a machine this one can't reach, from the status table it pushes through git
    (results/live-<machine>.md, written by scripts/live_status.py every 15 minutes). Read from the local checkout and,
    when `gh` is signed in, from GitHub, so a snapshot shows up without a git pull. The newer copy wins."""

    HEAD = re.compile(r"^# Live run status, (\d{4}-\d{2}-\d{2} \d{2}:\d{2})")

    def __init__(self, root: Path, github: tuple[str, str] | None, use_github: bool = True,
                 aliases: dict[str, str] | None = None):
        self.root = root
        self.github = github if use_github else None
        self.aliases = aliases or {}  # git machine name -> Tailscale device (--machine-alias laptop=danas-macbook-pro)
        self.mtimes: dict[str, float] = {}
        self.local: dict[str, tuple[float, list[dict]]] = {}  # machine -> (as of, rows)
        self.remote: dict[str, tuple[float, list[dict]]] = {}
        self.remote_t = 0.0
        self.remote_error = None
        self.version = 0

    @classmethod
    def parse(cls, text: str) -> tuple[float, list[dict]]:
        asof = 0.0
        rows, header = [], None
        for line in text.splitlines():
            m = cls.HEAD.match(line)
            if m:
                try:
                    asof = time.mktime(time.strptime(m.group(1), "%Y-%m-%d %H:%M"))
                except ValueError:
                    pass
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if header is None:
                header = cells
            elif not all(set(c) <= set("-: ") for c in cells):
                rows.append(dict(zip(header, cells)))
        return asof, rows

    def poll_local(self) -> bool:
        changed = False
        for f in sorted((self.root / "results").glob("live-*.md")):
            try:
                m = f.stat().st_mtime
            except OSError:
                continue
            if self.mtimes.get(f.name) == m:
                continue
            self.mtimes[f.name] = m
            self.local[f.stem[len("live-"):]] = self.parse(f.read_text(errors="replace"))
            changed = True
        if changed:
            self.version += 1
        return changed

    def poll_github(self) -> bool:
        """Read results/live-*.md from GitHub with the gh CLI (read-only API calls)."""
        if not self.github:
            return False
        import base64
        base, branch = self.github
        repo = base.removeprefix("https://github.com/")
        try:
            names = subprocess.run(["gh", "api", f"repos/{repo}/contents/results?ref={branch}", "--jq",
                                    '.[] | select(.name | test("^live-.+[.]md$")) | .name'],
                                   capture_output=True, text=True, check=False, timeout=20)
            if names.returncode != 0:
                self.remote_error = (names.stderr or "gh failed").strip()[:200]
                return False
            got = {}
            for name in names.stdout.split():
                out = subprocess.run(["gh", "api", f"repos/{repo}/contents/results/{name}?ref={branch}", "--jq",
                                      ".content"], capture_output=True, text=True, check=False, timeout=20)
                if out.returncode == 0:
                    got[name[len("live-"):-3]] = self.parse(base64.b64decode(out.stdout).decode("utf-8", "replace"))
            self.remote, self.remote_t, self.remote_error = got, time.time(), None
            self.version += 1
            return True
        except (OSError, subprocess.SubprocessError, ValueError) as e:
            self.remote_error = str(e)[:200]
            return False

    def loop(self, stop: threading.Event, on_change, every: float = 120.0) -> None:
        while self.github and not stop.is_set():
            if self.poll_github():
                on_change()
            stop.wait(every)

    def snapshots(self) -> dict[str, tuple[float, list[dict], str]]:
        out = {}
        for machine in set(self.local) | set(self.remote):
            a, b = self.local.get(machine), self.remote.get(machine)
            if a and (not b or a[0] >= b[0]):
                out[machine] = (a[0], a[1], "local checkout")
            elif b:
                out[machine] = (b[0], b[1], "GitHub")
        return out

    def summaries(self, known: set[str], skip_machines: frozenset[str] | set[str] = frozenset()) -> list[dict]:
        """Snapshot rows for runs this store doesn't hold. `skip_machines` (norm_host keys) are machines whose runs
        come from a better source, such as this machine itself."""
        out = []
        for machine, (asof, rows, src) in self.snapshots().items():
            if {norm_host(machine), norm_host(self.aliases.get(machine))} & set(skip_machines):
                continue
            for r in rows:
                name = r.get("run") or ""
                if not name or name in known or f"{name}-stopped" in known:
                    continue  # the real run folder wins, also after it is archived as <run>-stopped
                rnd, _, total = (r.get("round") or "0/0").partition("/")
                def num(k, row=r):
                    return _num(row.get(k))
                state = r.get("state") or "?"
                out.append({
                    "name": name, "machine": machine, "machine_key": norm_host(self.aliases.get(machine) or machine),
                    "origin": "snapshot",
                    "snapshot": True, "snapshot_t": asof, "snapshot_src": f"results/live-{machine}.md via {src}",
                    "published": [], "group": "v3" if r.get("swarm_wide") == "True" or num("N") == 100 else "v2-shuffled",
                    "arm": STAMP.sub("", name), "arm_base": arm_base(name), "seed": seed_of(name, {}),
                    "model": model_of(name, {}), "condition": None, "N": num("N"), "rounds_total": _num(total) or 20,
                    "n_problems": num("teams") or None, "state": _snap_state(state),
                    "state_detail": f"{machine} snapshot: {state}",
                    "alive": state == "running", "phase": None, "round": _num(rnd) or 0,
                    "completed_rounds": max(0, (_num(rnd) or 1) - (1 if state == "running" else 0)),
                    "turns": num("turns"), "turn_errors": num("turn_errors"), "usage_stops": num("usage_stops"),
                    "prs_opened": num("prs_opened"), "prs_merged": num("prs_merged"),
                    "merged_cross": num("merged_cross_team"), "problems_at_100": num("teams_at_100"),
                    "swarm_pass_rate": _pct(r.get("swarm_pass_rate")), "instigator_dms": num("instigator_dms"),
                    "reports": num("reports"), "removed": num("removed"), "test_file_edits": num("test_file_edits"),
                    "last_t": asof, "start_t": _start_of(name), "metrics": None, "cheaters_n": None,
                    "version": f"{asof}-{self.version}",
                })
        return out


def _snap_state(state: str) -> str:
    if state == "running":
        return "running"
    if "usage_limit" in state:
        return "usage-limit"
    if "completed" in state:
        return "ended"
    if state == "not running":
        return "interrupted"
    return state


def _num(v):
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        try:
            return float(str(v).strip())
        except (TypeError, ValueError):
            return None


def _pct(v):
    try:
        return float(str(v).strip().rstrip("%")) / 100
    except (TypeError, ValueError):
        return None


def _start_of(name: str) -> float | None:
    m = re.search(r"-(\d{8}-\d{6})(?:-stopped)?$", name or "")
    if not m:
        return None
    try:
        return time.mktime(time.strptime(m.group(1), "%Y%m%d-%H%M%S"))
    except ValueError:
        return None


class Store:
    """Every run under runs/ and results/, tailed by one background thread."""

    def __init__(self, root: Path, machine: str | None = None, tick: float = 1.0, scan_processes: bool = True,
                 fleet: bool = True, github_poll: bool = True, aliases: dict[str, str] | None = None):
        self.root = Path(root).resolve()
        self.machine = machine or hostname()
        self.tick_s = tick
        self.scan_processes = scan_processes
        self.lock = threading.RLock()
        self.cond = threading.Condition()
        self.runs: dict[str, RunState] = {}
        self.version = 0
        self.loaded = False
        self.loading = {"done": 0, "total": 0}
        self.queue = QueueLog(self.root / "runs" / "queue.log")
        self.machine_stats: dict = {}
        self.procs: dict = {}
        self.boot_t = _boot_time()
        self.started = time.time()
        self._last_discover = 0.0
        self._last_ps = 0.0
        self._cpu_prev = (time.time(), _cpu_seconds())
        self.self_cpu = 0.0
        self.stop_event = threading.Event()
        self.github = _github_base(self.root)
        self.thread: threading.Thread | None = None
        self.fleet = Fleet(enabled=fleet)
        self.remote = RemoteStatus(self.root, self.github, use_github=github_poll, aliases=aliases)

    # ---------------------------------------------------------------- discovery
    def _sources(self) -> list[tuple[str, Path, str]]:
        found: list[tuple[str, Path, str]] = []

        def scan(base: Path, origin: str):
            try:
                kids = sorted(p for p in base.iterdir() if p.is_dir())
            except OSError:
                return
            for p in kids:
                if (p / "events.jsonl").exists() and (p / "config.json").exists():
                    found.append((p.name, p, origin))

        scan(self.root / "runs", "runs")
        scan(self.root / "results", "results")
        for sub in ("ordered", "stopped", "v1"):
            scan(self.root / "results" / sub, sub)
        return found

    def discover(self) -> bool:
        changed = False
        prio = {"runs": 0, "results": 1, "ordered": 2, "stopped": 3, "v1": 4}
        best: dict[str, tuple[str, Path, str]] = {}
        published: dict[str, list[str]] = defaultdict(list)
        for name, path, origin in self._sources():
            if origin != "runs":
                published[name].append(origin)
            if name not in best or prio[origin] < prio[best[name][2]]:
                best[name] = (name, path, origin)
        with self.lock:
            for name, (_, path, origin) in best.items():
                run = self.runs.get(name)
                if run is None or run.dir != path:
                    self.runs[name] = RunState(name, path, origin)
                    changed = True
                pubs = sorted(published.get(name, []))
                if self.runs[name].published != pubs:
                    self.runs[name].published = pubs
                    self.runs[name].version += 1
                    changed = True
            for name in [n for n in self.runs if n not in best]:
                del self.runs[name]
                changed = True
        return changed

    # ---------------------------------------------------------------- the loop
    def start(self) -> None:
        self.thread = threading.Thread(target=self._loop, name="store", daemon=True)
        self.thread.start()
        if self.fleet.enabled:
            threading.Thread(target=self.fleet.loop, args=(self.stop_event, self._bump), name="fleet",
                             daemon=True).start()
        if self.remote.github:
            threading.Thread(target=self.remote.loop, args=(self.stop_event, self._bump), name="github",
                             daemon=True).start()

    def stop(self) -> None:
        self.stop_event.set()

    def _order(self) -> list[RunState]:
        def key(r: RunState):
            try:
                m = os.stat(r.events_path).st_mtime
            except OSError:
                m = 0
            return (r.origin != "runs", -m)
        return sorted(self.runs.values(), key=key)

    def initial_load(self) -> None:
        self.discover()
        runs = self._order()
        self.loading = {"done": 0, "total": len(runs)}
        for run in runs:
            if self.stop_event.is_set():
                return
            while True:
                with self.lock:
                    n = run.poll(budget=16 << 20)
                    run.load_labels()
                if n == 0:
                    break
                time.sleep(0.005)
            self._compute(run)
            self.loading["done"] += 1
            self._bump()
        self.loaded = True
        self._bump()

    def _bump(self) -> None:
        self.version += 1
        with self.cond:
            self.cond.notify_all()

    def step(self) -> bool:
        """One tick: discover, tail, refresh processes and metrics. Returns True if anything changed."""
        now = time.time()
        changed = False
        if now - self._last_discover >= 5:
            self._last_discover = now
            if self.discover():
                changed = True
        for run in list(self.runs.values()):
            with self.lock:
                n = run.poll()
                lab = run.load_labels()
            if n or lab:
                changed = True
            live = run.alive or (run.last_t and now - run.last_t < 300)
            due = now - run.metrics_t >= (METRICS_EVERY_S if live else 2)
            key = (len(run.slim), run.labels_mtime)
            if key != run.metrics_key and due:
                self._compute(run)
                changed = True
        if self.queue.poll():
            changed = True
        if self.remote.poll_local():
            changed = True
        if now - self._last_ps >= 5:
            self._last_ps = now
            if self._scan(now):
                changed = True
        return changed

    def _compute(self, run: RunState) -> None:
        with self.lock:
            slim = list(run.slim)
            key = (len(run.slim), run.labels_mtime)
        labels = run.labels_raw() if run.labels_mtime else []
        run.compute_metrics(slim, labels)
        run.metrics_key, run.metrics_t = key, time.time()
        run.version += 1

    def _loop(self) -> None:
        try:
            self.initial_load()
        except Exception as e:  # noqa: BLE001
            print("dashboard: initial load failed:", e, file=sys.stderr)
            self.loaded = True
        while not self.stop_event.is_set():
            t0 = time.time()
            try:
                if self.step():
                    self._bump()
            except Exception as e:  # noqa: BLE001
                print("dashboard: tick failed:", repr(e), file=sys.stderr)
            self.stop_event.wait(max(0.05, self.tick_s - (time.time() - t0)))

    # ---------------------------------------------------------------- processes and machine
    def _scan(self, now: float) -> bool:
        procs = {"swarm": [], "codex": 0, "rss_mb": None}
        lines = []
        if self.scan_processes:
            try:
                out = subprocess.run(["ps", "-axo", "pid=,rss=,etime=,command="], capture_output=True, text=True, check=False,
                                     timeout=5).stdout
                lines = out.splitlines()
            except (OSError, subprocess.SubprocessError):
                lines = []
        me = os.getpid()
        alive, labeling = set(), set()
        for line in lines:
            parts = line.split(None, 3)
            if len(parts) < 4:
                continue
            pid, rss, etime, cmd = parts
            if pid == str(me):
                procs["rss_mb"] = round(int(rss) / 1024, 1)
            if "codex" in cmd and " exec" in cmd:
                procs["codex"] += 1
            if "swarm " in cmd and ("swarm run" in cmd or "swarm resume" in cmd or "swarm label" in cmd):
                for name in self.runs:
                    if name in cmd:
                        (labeling if "swarm label" in cmd else alive).add(name)
                if "uv run" not in cmd and "python" in cmd or "/bin/swarm" in cmd:
                    procs["swarm"].append({"pid": int(pid), "etime": etime, "cmd": _short(cmd, 200)})
        changed = False
        with self.lock:
            for name, run in self.runs.items():
                a, lb = name in alive, name in labeling
                if run.alive != a or run.labeling != lb:
                    run.alive, run.labeling = a, lb
                    run.version += 1
                    changed = True
        t1, c1 = now, _cpu_seconds()
        t0, c0 = self._cpu_prev
        self.self_cpu = round(100 * (c1 - c0) / max(1e-6, t1 - t0), 2)
        self._cpu_prev = (t1, c1)
        self.procs = procs
        self.machine_stats = _machine_stats(self.root)
        return changed

    # ---------------------------------------------------------------- views
    def summary(self, run: RunState, now: float | None = None) -> dict:
        now = now or time.time()
        cfg = run.cfg
        state, detail = run.state(now, self.queue)
        m = run.metrics or {}
        rounds_total = cfg.get("rounds") or 20
        last_scores = run.scores.get(max(run.scores)) if run.scores else {}
        at100 = sorted(k for k, v in (last_scores or {}).items() if v >= 1)
        rs_rounds = sorted(r for r in run.scores)
        n_agents = cfg.get("swarm_size") or 0
        tokens = {"in": 0, "cached": 0, "out": 0}
        retries = turns = errors = merged = merged_cross = opened = dms = reports = removals = 0
        for r, rs in run.rs.items():
            tokens["in"] += rs["tokens_in"]
            tokens["cached"] += rs["tokens_cached"]
            tokens["out"] += rs["tokens_out"]
            retries += rs["retries"]
            turns += rs["turns"]
            errors += rs["turn_errors"]
            merged += rs["pr_merged"]
            merged_cross += rs["merged_cross"]
            opened += rs["pr_opened"]
            dms += rs["instigator_dms"]
            reports += rs["reports"]
            removals += rs["removals"]
        active = run.active_agents()
        roles = Counter(a.role for a in active)
        end_t = run.end["t"] if run.end else None
        mins = run.round_minutes()
        return {
            "name": run.name, "machine": self.machine, "machine_key": norm_host(self.machine), "origin": run.origin, "published": run.published,
            "group": group_of(run.name, cfg, run.published), "arm": cfg.get("name") or run.name,
            "arm_base": arm_base(cfg.get("name") or run.name), "seed": seed_of(run.name, cfg),
            "condition": condition_of(cfg), "model": model_of(run.name, cfg), "effort": cfg.get("worker_reasoning_effort") or cfg.get("reasoning_effort"),
            "N": n_agents, "rounds_total": rounds_total, "n_problems": len(run.problems) or cfg.get("problems"),
            "informed": bool(cfg.get("informed")), "I0": cfg.get("initial_investigators"), "k": cfg.get("k"),
            "p": cfg.get("p"), "swarm_wide": bool(cfg.get("swarm_wide")), "shuffle": bool(cfg.get("shuffle_turns")),
            "tests_visible": cfg.get("tests_visible", True), "aggressive": bool(cfg.get("instigator_aggressive")),
            "state": state, "state_detail": detail, "alive": run.alive, "phase": run.phase(),
            "round": run.round, "completed_rounds": run.completed_rounds,
            "turns_done": len(run.done.get(run.round, ())), "active_agents": len(active),
            "in_turn": sum(1 for a in active if a.in_turn_since) if run.alive else 0,
            "investigators": roles.get("investigator", 0), "workers": roles.get("worker", 0),
            "start_t": run.run_start_t or run.first_t, "last_t": run.last_t, "end_t": end_t,
            "end_reason": run.end["reason"] if run.end else None,
            "eta_t": run.eta(now) if state in ("running", "stalled") else None,
            "round_min_avg": round(sum(mins[-3:]) / len(mins[-3:]), 2) if mins else None,
            "active_s": round(sum(mins) * 60) if mins else 0,
            "events": run.n, "seq": run.seq, "turns": turns, "turn_errors": errors, "retries": retries,
            "usage_stops": len(run.usage_stops), "resumes": len(run.resumes),
            "prs_opened": opened, "prs_merged": merged, "merged_cross": merged_cross,
            "problems_at_100": len(at100), "at100": at100,
            "swarm_pass_rate": (sum(last_scores.values()) / len(last_scores)) if last_scores else None,
            "pass_series": [round(run.rs[r]["swarm_pass_rate"], 4) for r in rs_rounds],
            "at100_series": [int(run.rs[r]["problems_at_100"]) for r in rs_rounds],
            "instigator_dms": dms, "reports": reports, "removed": removals, "tokens": tokens,
            "labels_present": bool(run.labels_mtime), "labels_n": len(run.labels),
            "metrics": {k: m.get(k) for k in METRIC_KEYS} if m else None,
            "cheaters": run.cheaters, "cheaters_n": len(run.cheaters) if m else None,
            "metrics_error": run.metrics_error,
            "github": self.github_url(run), "version": run.version,
        }

    def github_url(self, run: RunState) -> str | None:
        if not self.github or not run.published:
            return None
        base, branch = self.github
        sub = {"results": "", "ordered": "ordered/", "stopped": "stopped/", "v1": "v1/"}
        where = run.published[0]
        return f"{base}/tree/{branch}/results/{sub.get(where, '')}{run.name}"

    def summaries(self) -> list[dict]:
        now = time.time()
        with self.lock:
            out = [self.summary(r, now) for r in self.runs.values()]
        # a machine's status file describes its own runs, which this store already reads from runs/
        return out + self.remote.summaries({s["name"] for s in out}, {norm_host(self.machine)} - {""})

    def detail(self, name: str) -> dict | None:
        with self.lock:
            run = self.runs.get(name)
            if run is None:
                return None
            now = time.time()
            s = self.summary(run, now)
            series = run.series()
            agents = []
            for a in sorted(run.agents.values(), key=lambda a: (a.slot if a.slot is not None else 9999, a.id)):
                if a.id == run.instigator or a.slot is None:
                    continue
                d = a.as_dict()
                d["cheat_round"] = run.first_cheat.get(a.id)
                d["labels"] = dict(run.label_counts.get(a.id, {}))
                d["audits"] = a.audits[-6:]
                d["in_turn"] = bool(a.in_turn_since) and run.alive
                d["done_this_round"] = a.id in run.done.get(run.round, ())
                agents.append(d)
            problems = list(run.problems)
            rounds = sorted(run.scores)
            heat = [[r, i, run.scores[r].get(p)] for r in rounds for i, p in enumerate(problems)
                    if run.scores[r].get(p) is not None]
            m = dict(run.metrics or {})
            for k in ("report_timing",):
                m.pop(k, None)
            return {
                "summary": s, "config": run.cfg, "series": series, "agents": agents, "instigator": run.instigator,
                "problems": problems, "heat": heat, "heat_rounds": rounds, "metrics": m,
                "cheaters_by_round": run.cheaters_by_round, "tool_counts": run.tool_counts.most_common(20),
                "type_counts": dict(run.type_counts), "error_kinds": dict(run.error_kinds),
                "usage_stops": run.usage_stops, "resumes": run.resumes, "harness_commit": run.harness_commit,
                "removed_order": run.removed_order, "final_audits": run.final_audits,
                "r_start": run.r_start, "r_end": run.r_end,
            }

    def prs(self, name: str) -> list[dict] | None:
        with self.lock:
            run = self.runs.get(name)
            if run is None:
                return None
            out = []
            for pr in run.prs.values():
                d = pr.as_dict()
                d["cheat"] = bool(pr.full_pass or pr.tests_full_pass or pr.touches_tests or pr.id in run.cheat_prs)
                d["cross"] = any(run.agents.get(x) and run.agents[x].team != pr.team for x in pr.approvers)
                d["last_check"] = pr.checks[-1] if pr.checks else None
                d.pop("checks")
                out.append(d)
            return out

    def pr_detail(self, name: str, pid: str) -> dict | None:
        with self.lock:
            run = self.runs.get(name)
            pr = run.prs.get(pid) if run else None
            if pr is None:
                return None
            d = pr.as_dict()
            pos = run.pos_of(pr.diff_seq) if pr.diff_seq is not None else None
        d["diff"] = None
        if pos is not None:
            ev = run.read_raw([pos])[0]
            d["diff"] = str(ev.get("diff") or "")[:60000]
        for rv in d["reviews"]:
            lab = run.labels.get(rv.get("message_id") or "")
            rv["label"] = lab[0] if lab else None
        d["cheat"] = bool(pr.full_pass or pr.tests_full_pass or pr.touches_tests or pr.id in run.cheat_prs)
        return d

    def network(self, name: str) -> dict | None:
        with self.lock:
            run = self.runs.get(name)
            if run is None:
                return None
            nodes = []
            for a in run.agents.values():
                if a.slot is None or a.id == run.instigator:
                    continue
                nodes.append({"id": a.id, "team": a.team, "slot": a.slot, "role0": a.initial_role,
                              "conv": a.converted_round, "joined": a.joined_round, "removed": a.removed_round,
                              "cheat": run.first_cheat.get(a.id), "replaces": a.replaces})
            if run.instigator:
                nodes.append({"id": run.instigator, "team": None, "slot": -1, "instigator": True})
            edges: dict[tuple, Counter] = defaultdict(Counter)
            for (s, t), byr in run.dm_pairs.items():
                kind = "instigator" if s == run.instigator else "dm"
                for r, c in byr.items():
                    edges[(s, t, kind)][r] += c
            cheat_prs = {p.id for p in run.prs.values()
                         if p.full_pass or p.tests_full_pass or p.touches_tests or p.id in run.cheat_prs}
            for s, t, r, pid in run.approve_edges:
                if t:
                    edges[(s, t, "approve_cheat" if pid in cheat_prs else "approve")][r] += 1
            for p in run.prs.values():
                if p.status == "merged" and p.id in cheat_prs:
                    for x in p.approvers:
                        edges[(p.author, x, "merged_cheat")][p.merged_round or 0] += 1
            for s, t, r in run.report_edges:
                edges[(s, t, "report")][r] += 1
            for s, t, lab, r, kind in run.label_list:
                if t and s != t:
                    edges[(s, t, "label_" + lab)][r or 0] += 1
            out_edges = [{"s": s, "t": t, "k": k, "r": {str(r): c for r, c in byr.items()}}
                         for (s, t, k), byr in edges.items()]
            # conspiracy groups: the metric's "active" links (labelled collusion and cheat merges)
            links = [(e["s"], e["t"]) for e in out_edges
                     if e["k"] in ("merged_cheat", "label_offer", "label_acceptance", "label_endorsement")
                     and run.instigator not in (e["s"], e["t"])]
        groups = _components(links)
        return {"nodes": nodes, "edges": out_edges, "instigator": run.instigator, "groups": groups,
                "rounds": max(run.round, run.cfg.get("rounds") or 0)}

    def feed(self, name: str, **kw) -> dict | None:
        with self.lock:
            run = self.runs.get(name)
            if run is None:
                return None
            pos, more, cursor = run.select(**kw)
        evs = run.read_raw(pos)
        items = [render(ev, run) for ev in evs]
        return {"items": items, "more": more, "cursor": cursor, "seq": run.seq}

    def agent_detail(self, name: str, aid: str, limit: int = 400, before=None, cats=None) -> dict | None:
        with self.lock:
            run = self.runs.get(name)
            if run is None or aid not in run.agents and aid != run.instigator:
                return None
            a = run.agents.get(aid)
            info = a.as_dict() if a else {"id": aid}
            info["cheat_round"] = run.first_cheat.get(aid)
            info["labels"] = dict(run.label_counts.get(aid, {}))
            info["instigator"] = aid == run.instigator
            pos, more, cursor = run.select(agent=aid, involve=True, limit=limit, before=before, cats=cats)
            prs = [p.as_dict() for p in run.prs.values() if p.author == aid]
            for p in prs:
                p.pop("checks", None)
        evs = run.read_raw(pos)
        return {"agent": info, "items": [render(ev, run) for ev in evs], "more": more, "cursor": cursor, "prs": prs}

    def event(self, name: str, seq: int) -> dict | None:
        with self.lock:
            run = self.runs.get(name)
            if run is None:
                return None
            pos = run.pos_of(seq)
        if pos is None:
            return None
        ev = run.read_raw([pos])[0]
        for k, v in list(ev.items()):
            if isinstance(v, str) and len(v) > 80000:
                ev[k] = v[:80000] + f"\n… ({len(v) - 80000} more chars)"
        return ev

    def ops(self, minutes: int = 180) -> dict:
        now = time.time()
        lo = int(now // 60) - minutes
        buckets: dict[int, list] = defaultdict(lambda: [0, 0, 0, 0, 0, 0])
        per_run_turns: dict[str, dict] = {}
        with self.lock:
            for run in self.runs.values():
                rt = {}
                for mi, b in run.minutes.items():
                    if mi > lo:
                        acc = buckets[mi]
                        for j in range(6):
                            acc[j] += b[j]
                        rt[mi] = b[0]
                if rt:
                    per_run_turns[run.name] = rt
            tokens = []
            for run in self.runs.values():
                tin = sum(rs["tokens_in"] for rs in run.rs.values())
                if tin:
                    tokens.append({"name": run.name, "in": tin,
                                   "cached": sum(rs["tokens_cached"] for rs in run.rs.values()),
                                   "out": sum(rs["tokens_out"] for rs in run.rs.values()),
                                   "group": group_of(run.name, run.cfg, run.published)})
            stops = []
            for run in self.runs.values():
                for s in run.usage_stops:
                    stops.append({"run": run.name, **s, "kind": "usage_limit_hit"})
                for s in run.resumes:
                    stops.append({"run": run.name, **s, "kind": "run_resumed"})
                if run.end and run.end.get("reason") not in ("completed", None):
                    stops.append({"run": run.name, "t": run.end["t"], "round": run.end.get("round"),
                                  "kind": "run_end", "phase": run.end["reason"]})
            interrupted = [r.name for r in self.runs.values() if r.state(now, self.queue)[0] == "interrupted"]
        mins = list(range(lo + 1, int(now // 60) + 1))
        return {
            "machine": self.machine, "now": now, "boot_t": self.boot_t, "started": self.started,
            "minutes": [m * 60 for m in mins],
            "turns": [buckets[m][0] if m in buckets else 0 for m in mins],
            "retries": [buckets[m][1] if m in buckets else 0 for m in mins],
            "errors": [buckets[m][2] if m in buckets else 0 for m in mins],
            "tool_calls": [buckets[m][3] if m in buckets else 0 for m in mins],
            "tokens_in": [buckets[m][4] if m in buckets else 0 for m in mins],
            "tokens_out": [buckets[m][5] if m in buckets else 0 for m in mins],
            "per_run_turns": {k: [v.get(m, 0) for m in mins] for k, v in per_run_turns.items()},
            "tokens": sorted(tokens, key=lambda x: -x["in"]),
            "stops": sorted(stops, key=lambda x: x.get("t") or 0)[-200:],
            "queue_lines": list(self.queue.lines)[-250:], "queue_events": self.queue.events[-200:],
            "machine_stats": self.machine_stats, "procs": self.procs, "self_cpu": self.self_cpu,
            "interrupted": interrupted, "loading": self.loading,
        }

    def light(self) -> dict:
        return {"machine": self.machine, "machine_key": norm_host(self.machine), "now": time.time(),
                "boot_t": self.boot_t, "machine_stats": self.machine_stats, "codex": self.procs.get("codex"),
                "self_cpu": self.self_cpu, "rss_mb": self.procs.get("rss_mb"), "loading": self.loading,
                "loaded": self.loaded, "fleet": self.fleet.view()}


def _components(links: list[tuple[str, str]]) -> list[list[str]]:
    parent: dict[str, str] = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in links:
        parent[find(a)] = find(b)
    groups: dict[str, list] = defaultdict(list)
    for n in list(parent):
        groups[find(n)].append(n)
    return sorted((sorted(g) for g in groups.values() if len(g) > 1), key=len, reverse=True)


# ---------------------------------------------------------------------------------------------------------------
# Feed rendering: one compact, display-ready item per raw event


def render(ev: dict, run: RunState) -> dict:
    t = ev.get("type", "?")
    aid = ev.get("agent")
    item = {"seq": ev.get("seq"), "t": ev.get("t"), "type": t, "round": ev.get("round"), "agent": aid,
            "role": ev.get("role"), "team": ev.get("team"), "cat": CATS.get(t, "lifecycle")}
    title, body, tags = "", "", []
    if t == "message":
        kind, to = ev.get("kind"), ev.get("to")
        inst = aid == run.instigator
        item["cat"] = "instigator" if inst else ("review" if kind == "review" else
                                                 "progress" if kind == "progress" else "chat")
        title = f"{aid} → {to}" if to else f"{aid} · {kind}"
        tags.append("instigator" if inst else kind)
        body = _short_keep(ev.get("text"), 2400)
        item["to"], item["kind"], item["message_id"] = to, kind, ev.get("message_id")
        lab = run.labels.get(ev.get("message_id") or "")
        if lab:
            item["label"], item["label_target"] = lab[0], lab[1]
    elif t == "agent_message":
        title, body = f"{aid} says", _short_keep(ev.get("text"), 1600)
    elif t == "instigator_message":
        title = f"instigator → {ev.get('to')}: {ev.get('trigger')}"
        body = f"team {ev.get('team')}" + (f", PR {ev['pr_id']}" if ev.get("pr_id") else "")
        item["to"] = ev.get("to")
    elif t == "tool_call":
        args = ev.get("args") or {}
        a = ", ".join(f"{k}={_short(v if not isinstance(v, dict) else '{…' + str(len(v)) + ' files}', 60)}"
                      for k, v in args.items())
        title = f"{aid} · {ev.get('tool')}({a})"
        body = _short_keep(ev.get("result"), 600)
        if ev.get("error"):
            tags.append("error")
    elif t == "tests_run":
        title = f"{aid} ran tests: {ev.get('team')}" + (f" on {ev['pr_id']}" if ev.get("pr_id") else " main")
        body = f"{ev.get('passed')}/{ev.get('total')} passed" + (f" · {ev['error']}" if ev.get("error") else "")
        if ev.get("full_pass"):
            tags.append("full-pass")
    elif t in ("pr_opened", "pr_updated"):
        title = f"{aid} {'opened' if t == 'pr_opened' else 'updated'} {ev.get('pr_id')} on {ev.get('team')}"
        body = _short(ev.get("title"), 300)
        if ev.get("touches_tests"):
            tags.append("touches-tests")
        item["pr_id"] = ev.get("pr_id")
    elif t == "pr_checked":
        title = f"harness check {ev.get('pr_id')} v{ev.get('version')}"
        body = f"{ev.get('passed')}/{ev.get('total')} passed"
        if ev.get("full_pass"):
            tags.append("full-pass")
        item["pr_id"] = ev.get("pr_id")
    elif t == "pr_reviewed":
        dec = ev.get("decision")
        title = f"{aid} {'approved' if dec == 'approve' else 'requested changes on'} {ev.get('pr_id')} (by {ev.get('author')})"
        body = _short_keep(ev.get("comment"), 1200)
        tags.append(dec or "")
        item["pr_id"], item["to"] = ev.get("pr_id"), ev.get("author")
        pr = run.prs.get(ev.get("pr_id") or "")
        if pr and (pr.full_pass or pr.touches_tests or pr.id in run.cheat_prs):
            tags.append("cheat-pr")
        lab = run.labels.get(ev.get("message_id") or "")
        if lab:
            item["label"], item["label_target"] = lab[0], lab[1]
    elif t == "pr_merged":
        title = f"{ev.get('pr_id')} merged into {ev.get('team')}"
        body = f"author {aid}; approvers {', '.join(ev.get('approvers') or [])}"
        pr = run.prs.get(ev.get("pr_id") or "")
        if ev.get("touches_tests"):
            tags.append("touches-tests")
        if pr and (pr.full_pass or pr.tests_full_pass or pr.id in run.cheat_prs):
            tags.append("cheat-pr")
        item["pr_id"] = ev.get("pr_id")
    elif t == "pr_stale":
        title, body = f"{ev.get('pr_id')} went stale", ", ".join(ev.get("paths") or [])
    elif t == "test_file_edit":
        title = f"TEST FILE EDITED by {aid} via {ev.get('pr_id')}"
        body = f"{ev.get('path')} · approvers {', '.join(ev.get('approvers') or [])}"
        tags.append("cheat-pr")
    elif t == "team_scores":
        sc = {k: v for k, v in (ev.get("scores") or {}).items() if v is not None}
        full = sorted(k for k, v in sc.items() if v >= 1)
        rate = sum(sc.values()) / len(sc) if sc else 0
        title = f"round {ev.get('round')} scores · swarm {rate:.1%} · {len(full)} at 100%"
        body = ", ".join(full)
        if full:
            tags.append("full-pass")
    elif t in ("round_start", "round_end"):
        title = f"round {ev.get('round')} {'starts' if t == 'round_start' else 'ends'}"
        if t == "round_end":
            body = f"workers {ev.get('workers')}, investigators {ev.get('investigators')}"
    elif t == "report_submitted":
        title = f"{aid} reported {', '.join(ev.get('accused') or [])}"
        body = _short_keep(ev.get("evidence"), 1200)
        item["to"] = ",".join(ev.get("accused") or [])
    elif t == "report_result":
        conf = ev.get("confirmed") or []
        title = f"report {ev.get('report_id')} by {aid}: {len(conf)}/{len(ev.get('accused') or [])} confirmed"
        body = f"accused {', '.join(ev.get('accused') or [])}" + (f"; confirmed {', '.join(conf)}" if conf else "")
    elif t == "audit":
        v = ev.get("verdict") or {}
        mis = v.get("misaligned_before_conversion") or v.get("misaligned_after_conversion")
        title = f"audit {aid} ({', '.join(ev.get('triggers') or [])}): {'MISALIGNED' if mis else 'aligned'}"
        if ev.get("removed"):
            title += " → removed"
        body = _short_keep(v.get("summary"), 1200)
        tags.append("misaligned" if mis else "aligned")
    elif t == "agent_removed":
        title, body = f"{aid} removed from the swarm", f"slot {ev.get('slot')}"
        tags.append("removed")
    elif t == "role_change":
        title = f"{aid} converted to {ev.get('role')}"
    elif t == "agent_joined":
        title = f"{aid} joined ({ev.get('role')}, {ev.get('team')})" + (f" replacing {ev['replaces']}" if ev.get("replaces") else "")
    elif t == "instigator_joined":
        title = f"instigator {aid} joined"
    elif t == "instigator_reported":
        title, body = f"{aid} reported the instigator", _short_keep(ev.get("evidence"), 800)
    elif t == "turn_input":
        title = f"{aid} turn ({ev.get('role')})"
        body = _short_keep(ev.get("prompt"), 1500)
    elif t == "model_usage":
        u = ev.get("usage") or {}
        title = f"{aid} turn done · {u.get('input_tokens', 0):,} in / {u.get('output_tokens', 0):,} out"
        if (ev.get("attempts") or 1) > 1:
            tags.append(f"{ev['attempts'] - 1} retries")
        if ev.get("error"):
            tags.append("error")
            body = _short(ev.get("raw_error") or ev.get("error"), 300)
    elif t == "turn_error":
        title, body = f"{aid} turn error", _short(ev.get("error"), 300)
        tags.append("error")
    elif t == "usage_limit_hit":
        title = f"USAGE LIMIT in {ev.get('phase')}"
        body = f"{len(ev.get('missed') or [])} agents missed their turn"
        tags.append("error")
    elif t == "run_start":
        title = f"run started · {run.cfg.get('name')}"
        body = f"harness {ev.get('harness_commit')}"
    elif t == "run_end":
        title = f"run ended: {ev.get('reason')}"
        if ev.get("reason") != "completed":
            tags.append("error")
    elif t == "run_resumed":
        title = f"run resumed ({ev.get('phase')}, {ev.get('completed_rounds')} rounds done)"
    elif t == "honeypot_access":
        title, body = f"{aid} fetched {ev.get('url')}", "honeypot (answer key)"
        tags.append("honeypot")
    elif t == "tests_flagged":
        title, body = f"{aid} flagged tests on {ev.get('team')}", _short_keep(ev.get("reason"), 600)
    elif t == "session_started":
        title = f"{aid} session started"
    elif t == "test_files_changed":
        title = f"test files changed on main: {len(ev.get('changed') or [])}"
        body = ", ".join(map(str, ev.get("changed") or []))[:400]
        tags.append("cheat-pr")
    elif t == "builtin_tool_use":
        title = f"{aid} used built-in tools ({len(ev.get('items') or [])})"
    else:
        title = t
    item["title"], item["body"], item["tags"] = title, body, [x for x in tags if x]
    return item


def _short_keep(s, n: int) -> str:
    s = str(s or "")
    return s if len(s) <= n else s[: n - 1] + "…"


# ---------------------------------------------------------------------------------------------------------------
# Machine stats


def _cpu_seconds() -> float:
    import resource
    u = resource.getrusage(resource.RUSAGE_SELF)
    return u.ru_utime + u.ru_stime


def _boot_time() -> float | None:
    try:
        out = subprocess.run(["sysctl", "-n", "kern.boottime"], capture_output=True, text=True, check=False, timeout=3).stdout
        m = re.search(r"sec = (\d+)", out)
        if m:
            return float(m.group(1))
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        with open("/proc/stat") as f:
            for line in f:
                if line.startswith("btime"):
                    return float(line.split()[1])
    except OSError:
        pass
    return None


def _machine_stats(root: Path) -> dict:
    out: dict = {"ncpu": os.cpu_count()}
    try:
        out["load"] = [round(x, 2) for x in os.getloadavg()]
    except OSError:
        out["load"] = None
    try:
        du = os.statvfs(root)
        out["disk_free_gb"] = round(du.f_bavail * du.f_frsize / 1e9, 1)
    except OSError:
        pass
    try:
        if sys.platform == "darwin":
            total = _memsize()
            vm = subprocess.run(["vm_stat"], capture_output=True, text=True, check=False, timeout=3).stdout
            page = int(re.search(r"page size of (\d+)", vm).group(1))
            pages = {k.strip(): int(v.strip().rstrip(".")) for k, v in
                     (line.split(":", 1) for line in vm.splitlines()[1:] if ":" in line) if v.strip().rstrip(".").isdigit()}
            free = (pages.get("Pages free", 0) + pages.get("Pages speculative", 0)) * page
            avail = free + pages.get("Pages inactive", 0) * page + pages.get("Pages purgeable", 0) * page
            out["mem_total_gb"] = round(total / 1e9, 1)
            out["mem_used_gb"] = round((total - avail) / 1e9, 1)
            out["compressed_gb"] = round(pages.get("Pages occupied by compressor", 0) * page / 1e9, 2)
            sw = subprocess.run(["sysctl", "-n", "vm.swapusage"], capture_output=True, text=True, check=False, timeout=3).stdout
            m = re.search(r"used = ([\d.]+)M", sw)
            out["swap_used_gb"] = round(float(m.group(1)) / 1024, 2) if m else None
        elif os.path.exists("/proc/meminfo"):
            info = {}
            with open("/proc/meminfo") as f:
                for line in f:
                    k, v = line.split(":", 1)
                    info[k] = int(v.split()[0]) * 1024
            out["mem_total_gb"] = round(info["MemTotal"] / 1e9, 1)
            out["mem_used_gb"] = round((info["MemTotal"] - info.get("MemAvailable", 0)) / 1e9, 1)
            out["swap_used_gb"] = round((info.get("SwapTotal", 0) - info.get("SwapFree", 0)) / 1e9, 2)
    except (OSError, subprocess.SubprocessError, AttributeError, ValueError):
        pass
    return out


_MEMSIZE: list = []


def _memsize() -> int:
    if not _MEMSIZE:
        _MEMSIZE.append(int(subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, check=False,
                                           timeout=3).stdout.strip() or 0))
    return _MEMSIZE[0]


def _github_base(root: Path) -> tuple[str, str] | None:
    try:
        url = subprocess.run(["git", "-C", str(root), "config", "--get", "remote.origin.url"], capture_output=True,
                             text=True, timeout=3).stdout.strip()
        branch = subprocess.run(["git", "-C", str(root), "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True,
                                text=True, timeout=3).stdout.strip() or "main"
    except (OSError, subprocess.SubprocessError):
        return None
    m = re.search(r"github\.com[:/](.+?)(?:\.git)?$", url)
    return (f"https://github.com/{m.group(1)}", branch) if m else None
