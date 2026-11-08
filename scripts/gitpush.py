"""Commit some paths and push them to the current branch, so two machines can publish to one branch.

Each try pulls with rebase before it pushes. On a rebase conflict the local commit wins (`-X theirs`: during a rebase,
"theirs" is the local commit being replayed). Files derived from others, such as the metrics tables, are then rebuilt
from the merged tree by `rebuild` and committed again, so no machine's rows get lost.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path


def git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)


def commit(root: Path, paths: list[str], message: str) -> str:
    git(root, "add", "-A", "--", *paths)
    res = git(root, "commit", "-q", "-m", message, "--", *paths)
    return "committed: " + message if res.returncode == 0 else (res.stdout.strip() or res.stderr.strip())


def commit_and_push(root: Path, paths: list[str], message: str, rebuild: Callable[[], None] | None = None,
                    tries: int = 4) -> int:
    print(commit(root, paths, message))
    for n in range(1, tries + 1):
        pull = git(root, "pull", "-q", "--rebase", "--autostash", "-X", "theirs")
        if pull.returncode != 0:
            git(root, "rebase", "--abort")
            print(f"pull failed, try {n} of {tries}: {pull.stderr.strip()}")
            continue
        if rebuild is not None:
            rebuild()
            res = commit(root, paths, message + " (tables rebuilt after pull)")
            if res.startswith("committed"):
                print(res)
        push = git(root, "push", "-q", "origin", "HEAD")
        if push.returncode == 0:
            print("push: ok")
            return 0
        print(f"push failed, try {n} of {tries}: {push.stderr.strip()}")
    return 1
