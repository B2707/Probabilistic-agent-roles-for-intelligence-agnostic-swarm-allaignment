"""Append-only JSONL event log: the contract between the harness and all analysis."""

from __future__ import annotations

import json
import time
from collections import defaultdict
from pathlib import Path


class EventLog:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.by_agent: dict[str, list[dict]] = defaultdict(list)
        self.seq = 0
        if self.path.exists():
            for ev in read_events(self.path):
                self._index(ev)
                self.seq = ev["seq"] + 1
        self._f = open(self.path, "a")

    def emit(self, type: str, round: int | None = None, **fields) -> dict:
        ev = {"seq": self.seq, "t": round_time(), "type": type, "round": round, **fields}
        self.seq += 1
        self._f.write(json.dumps(ev, ensure_ascii=False) + "\n")
        self._f.flush()
        self._index(ev)
        return ev

    def _index(self, ev: dict) -> None:
        if ev.get("agent"):
            self.by_agent[ev["agent"]].append(ev)

    def close(self) -> None:
        self._f.close()


def round_time() -> float:
    return round(time.time(), 3)


def read_events(path: str | Path) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]
