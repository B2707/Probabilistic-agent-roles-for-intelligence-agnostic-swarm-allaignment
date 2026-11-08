"""Runs one problem's test file and prints JSON results.

Executed in a subprocess (under `codex sandbox` when enabled) with the problem
directory as cwd. Output from agent-written code is discarded so test results
are the only thing that flows back to agents.

Usage: python runner.py <per_test_timeout_seconds>
"""

import importlib.util
import json
import os
import signal
import sys


class _Timeout(Exception):
    pass


def _alarm(signum, frame):
    raise _Timeout()


def _source(fn) -> str:
    try:
        import inspect
        lines = [l.strip() for l in inspect.getsource(fn).splitlines()[1:] if l.strip()]
        return lines[-1][:200] if lines else ""
    except (OSError, TypeError):
        return ""


def main() -> None:
    timeout = float(sys.argv[1]) if len(sys.argv) > 1 else 5.0
    real_stdout = os.dup(1)
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, 1)
    os.dup2(devnull, 2)
    sys.path.insert(0, os.getcwd())
    results = []
    try:
        spec = importlib.util.spec_from_file_location("test_solution", "test_solution.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        tests = [(n, f) for n, f in vars(mod).items() if n.startswith("test") and callable(f)]
    except BaseException as e:  # noqa: BLE001 - report any import failure
        tests = []
        results.append({"name": "<import>", "ok": False, "error": f"{type(e).__name__}: {str(e)[:160]}"})
    signal.signal(signal.SIGALRM, _alarm)
    for name, fn in tests:
        signal.setitimer(signal.ITIMER_REAL, timeout)
        try:
            fn()
            results.append({"name": name, "ok": True, "error": None})
        except _Timeout:
            results.append({"name": name, "ok": False, "error": f"Timeout after {timeout}s"})
        except AssertionError as e:
            results.append({"name": name, "ok": False, "error": f"AssertionError: {_source(fn)} {str(e)[:160]}".strip()})
        except BaseException as e:  # noqa: BLE001
            results.append({"name": name, "ok": False, "error": f"{type(e).__name__}: {str(e)[:160]}"})
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
    os.write(real_stdout, ("@@RESULTS@@" + json.dumps(results)).encode())


if __name__ == "__main__":
    main()
