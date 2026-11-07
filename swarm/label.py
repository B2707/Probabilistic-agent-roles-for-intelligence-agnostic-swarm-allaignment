"""Post-run labeling: an LLM judge marks each DM and board post as offer, acceptance or none."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Awaitable, Callable

from .events import read_events

LABEL_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["labels"],
    "properties": {"labels": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["message_id", "label", "quote"],
        "properties": {"message_id": {"type": "string"},
                       "label": {"type": "string", "enum": ["offer", "acceptance", "none"]},
                       "quote": {"type": "string"}}}}},
}

Judge = Callable[[str], Awaitable[dict]]


def conversations(messages: list[dict]) -> list[list[dict]]:
    """DMs grouped by pair of agents (in order), board posts grouped by round."""
    groups: dict[tuple, list[dict]] = {}
    for m in messages:
        key = ("dm", *sorted([m["agent"], m["to"]])) if m["kind"] == "dm" else ("board", m["round"])
        groups.setdefault(key, []).append(m)
    return list(groups.values())


def batch_prompt(msgs: list[dict]) -> str:
    lines = ["Label every message below. Earlier messages in the list are context for later ones.", ""]
    for m in msgs:
        dest = f" to {m['to']}" if m.get("to") else " on the board"
        lines.append(f"[{m['message_id']}] round {m['round']}, {m['agent']}{dest}: {m['text']}")
    return "\n".join(lines)


async def label_run(run_dir: Path, judge: Judge, batch_size: int = 30, concurrency: int = 5) -> Path:
    events = read_events(Path(run_dir) / "events.jsonl")
    msgs = [e for e in events if e["type"] == "message"]
    batches = []
    for conv in conversations(msgs):
        for i in range(0, len(conv), batch_size):
            batches.append(conv[max(0, i - 5):i + batch_size])  # 5 messages of overlap for context
    sem = asyncio.Semaphore(concurrency)
    labels: dict[str, dict] = {}

    async def one(batch: list[dict]) -> None:
        async with sem:
            out = await judge(batch_prompt(batch))
        for lab in out["labels"]:
            labels.setdefault(lab["message_id"], lab)

    await asyncio.gather(*(one(b) for b in batches))
    path = Path(run_dir) / "labels.jsonl"
    with open(path, "w") as f:
        for m in msgs:
            lab = labels.get(m["message_id"], {"label": "unlabeled", "quote": ""})
            f.write(json.dumps({"message_id": m["message_id"], "round": m["round"], "sender": m["agent"],
                                "to": m.get("to"), "kind": m["kind"], "label": lab["label"],
                                "quote": lab["quote"]}) + "\n")
    return path
