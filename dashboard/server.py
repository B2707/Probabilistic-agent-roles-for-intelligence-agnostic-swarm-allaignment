"""Swarm ops dashboard: a read-only web console for the experiment's runs, with live updates over SSE.

Usage, from the repo root:
  uv run python -m dashboard [--host 127.0.0.1] [--port 8765] [--root .] [--peer http://HOST:PORT]... [--token T]

Standard library only. The server never writes under runs/, results/, configs/ or git.
"""

from __future__ import annotations

import argparse
import gzip
import hmac
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

if __package__ in (None, ""):  # run as a file: uv run python dashboard/server.py
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from dashboard.store import DEADLINE, DEADLINE_T, Store, hostname
else:
    from .store import DEADLINE, DEADLINE_T, Store, hostname

STATIC = Path(__file__).resolve().parent / "static"
STATIC_FILES = {"index.html": "text/html; charset=utf-8", "app.js": "text/javascript; charset=utf-8",
                "style.css": "text/css; charset=utf-8", "favicon.svg": "image/svg+xml"}
MAX_STREAMS = 48
COOKIE = "swarm_dash"


class Peer:
    """Another machine's dashboard. Its run summaries are kept current over its own SSE stream."""

    def __init__(self, url: str, on_change):
        parsed = urllib.parse.urlsplit(url)
        q = urllib.parse.parse_qs(parsed.query)
        self.token = (q.get("token") or [None])[0]
        self.url = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", ""))
        self.on_change = on_change
        self.machine = None
        self.runs: dict[str, dict] = {}
        self.light: dict = {}
        self.ok = False
        self.error = None
        self.last_ok = None
        self.latency_ms = None
        self.stop = threading.Event()

    def headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def get(self, path: str, timeout: float = 10) -> bytes:
        req = urllib.request.Request(self.url + path, headers={**self.headers(), "Accept-Encoding": "gzip"})
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            if resp.headers.get("Content-Encoding") == "gzip":
                body = gzip.decompress(body)
        self.latency_ms = round((time.time() - t0) * 1000)
        return body

    def get_json(self, path: str, timeout: float = 10):
        return json.loads(self.get(path, timeout))

    def start(self) -> None:
        threading.Thread(target=self._loop, name=f"peer {self.url}", daemon=True).start()

    def _loop(self) -> None:
        while not self.stop.is_set():
            try:
                st = self.get_json("/api/state?local=1")
                self.machine = st.get("machine")
                self.runs = {s["name"]: s for s in st.get("runs") or []}
                self.light = st.get("light") or {}
                self.ok, self.error, self.last_ok = True, None, time.time()
                self.on_change()
                req = urllib.request.Request(self.url + "/api/stream?local=1", headers=self.headers())
                with urllib.request.urlopen(req, timeout=45) as resp:
                    event, data = None, []
                    for raw in resp:
                        if self.stop.is_set():
                            return
                        line = raw.decode("utf-8", "replace").rstrip("\r\n")
                        if line.startswith("event:"):
                            event = line[6:].strip()
                        elif line.startswith("data:"):
                            data.append(line[5:].lstrip())
                        elif line == "":
                            if event and data:
                                self._dispatch(event, "\n".join(data))
                            event, data = None, []
                        self.last_ok = time.time()
            except Exception as e:  # noqa: BLE001
                self.ok, self.error = False, f"{type(e).__name__}: {e}"
                self.on_change()
                self.stop.wait(3)

    def _dispatch(self, event: str, data: str) -> None:
        try:
            payload = json.loads(data)
        except ValueError:
            return
        if event == "summary":
            for s in payload:
                self.runs[s["name"]] = s
            self.on_change()
        elif event == "light":
            self.light = payload.get("local") or payload
        elif event == "hello":
            self.machine = payload.get("machine") or self.machine

    def status(self) -> dict:
        return {"url": self.url, "machine": self.machine, "ok": self.ok, "error": self.error, "last_ok": self.last_ok,
                "latency_ms": self.latency_ms, "runs": len(self.runs), "light": self.light}


class App:
    def __init__(self, store: Store, peers: list[str], token: str | None):
        self.store = store
        self.token = token
        self.peer_version = 0
        self.peers = [Peer(u, self._peer_changed) for u in peers]
        self.streams = threading.BoundedSemaphore(MAX_STREAMS)

    def _peer_changed(self) -> None:
        self.peer_version += 1
        with self.store.cond:
            self.store.cond.notify_all()

    def start(self) -> None:
        self.store.start()
        for p in self.peers:
            p.start()

    # merged view: local runs plus peers' runs; for a name on both, the copy with more events wins
    def merged(self, local_only: bool = False) -> list[dict]:
        out = {s["name"]: s for s in self.store.summaries()}
        if not local_only:
            for i, p in enumerate(self.peers):
                for name, s in list(p.runs.items()):
                    cur = out.get(name)
                    if cur is None or (s.get("events") or 0) > (cur.get("events") or 0):
                        out[name] = {**s, "peer": i, "machine": s.get("machine") or p.machine}
        return sorted(out.values(), key=lambda s: (s.get("start_t") or 0), reverse=True)

    def fleet(self, local_only: bool = False) -> dict:
        """Devices from this machine's fleet pathway, merged with each peer's (a device seen twice keeps the copy
        that has live numbers, then the newer one)."""
        local = self.store.fleet.view()
        views = [{"machine": self.store.machine, **local}]
        if not local_only:
            for p in self.peers:
                try:
                    views.append({"machine": p.machine, **p.get_json("/api/fleet?local=1", timeout=8)})
                except Exception as e:  # noqa: BLE001
                    views.append({"machine": p.machine or p.url, "devices": [], "error": str(e)})
        merged: dict[str, dict] = {}
        for v in views:
            for d in v.get("devices") or []:
                d = {**d, "via": v.get("machine")}
                cur = merged.get(d.get("id"))
                better = cur is None or (d.get("status") and not cur.get("status")) or (
                    bool(d.get("status")) == bool(cur.get("status"))
                    and ((d.get("status") or {}).get("time") or 0) > ((cur.get("status") or {}).get("time") or 0))
                if better:
                    merged[d.get("id")] = d
        return {"devices": sorted(merged.values(), key=lambda d: (not d.get("online"), not d.get("self"), d.get("id") or "")),
                "sources": [{k: v.get(k) for k in ("machine", "t", "error", "source", "port")} for v in views]}

    def owner(self, name: str) -> Peer | None:
        """The peer that serves `name`, or None when it is local (or unknown)."""
        local = self.store.runs.get(name)
        best, best_n = None, (local.n if local else -1)
        for p in self.peers:
            s = p.runs.get(name)
            if s and (s.get("events") or 0) > best_n:
                best, best_n = p, s.get("events") or 0
        return best

    def state(self, local_only: bool) -> dict:
        return {"machine": self.store.machine, "now": time.time(), "deadline": DEADLINE, "deadline_t": DEADLINE_T,
                "runs": self.merged(local_only), "loaded": self.store.loaded, "loading": self.store.loading,
                "light": self.store.light(), "peers": [] if local_only else [p.status() for p in self.peers],
                "version": self.store.version}


class Handler(BaseHTTPRequestHandler):
    server_version = "SwarmDash/1"
    protocol_version = "HTTP/1.1"
    app: App

    def log_message(self, fmt, *args):  # quiet
        if os.environ.get("DASHBOARD_LOG"):
            super().log_message(fmt, *args)

    # ---------------------------------------------------------------- plumbing
    def _send(self, code: int, body: bytes, ctype: str = "application/json", extra: dict | None = None) -> None:
        gz = len(body) > 2048 and "gzip" in (self.headers.get("Accept-Encoding") or "")
        if gz:
            body = gzip.compress(body, compresslevel=5)
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        if gz:
            self.send_header("Content-Encoding", "gzip")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code: int = 200, extra: dict | None = None) -> None:
        self._send(code, json.dumps(obj, separators=(",", ":"), default=_default).encode(), extra=extra)

    def _authorized(self, q: dict) -> tuple[bool, dict]:
        token = self.app.token
        if not token:
            return True, {}
        given = (q.get("token") or [None])[0]
        if given and hmac.compare_digest(given, token):
            return True, {"Set-Cookie": f"{COOKIE}={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=2592000"}
        auth = self.headers.get("Authorization") or ""
        if auth.startswith("Bearer ") and hmac.compare_digest(auth[7:].strip(), token):
            return True, {}
        c = cookies.SimpleCookie(self.headers.get("Cookie") or "")
        if COOKIE in c and hmac.compare_digest(c[COOKIE].value, token):
            return True, {}
        return False, {}

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        url = urllib.parse.urlsplit(self.path)
        q = urllib.parse.parse_qs(url.query)
        path = url.path
        ok, extra = self._authorized(q)
        if not ok:
            if path.startswith("/api/"):
                return self._json({"error": "unauthorized"}, 401)
            return self._send(401, LOGIN_PAGE.encode(), "text/html; charset=utf-8")
        try:
            if path in ("/", "/index.html"):
                return self._static("index.html", extra)
            if path.startswith("/static/"):
                return self._static(path[len("/static/"):], extra)
            if path == "/favicon.ico":
                return self._static("favicon.svg", extra)
            if path == "/api/health":
                return self._json({"ok": True, "machine": self.app.store.machine, "loaded": self.app.store.loaded})
            if path == "/api/state":
                return self._json(self.app.state(_flag(q, "local")), extra=extra)
            if path == "/api/ops":
                return self._ops(q)
            if path == "/api/fleet":
                return self._json(self.app.fleet(_flag(q, "local")))
            if path == "/api/series":
                return self._series(q)
            if path == "/api/stream":
                return self._stream(q)
            if path.startswith("/api/run/"):
                return self._run(path[len("/api/run/"):], q, url.query)
            return self._json({"error": "not found"}, 404)
        except (BrokenPipeError, ConnectionResetError):
            return None
        except Exception as e:  # noqa: BLE001
            try:
                return self._json({"error": f"{type(e).__name__}: {e}"}, 500)
            except OSError:
                return None

    def _static(self, name: str, extra: dict) -> None:
        if name not in STATIC_FILES:
            return self._json({"error": "not found"}, 404)
        body = (STATIC / name).read_bytes()
        return self._send(200, body, STATIC_FILES[name], extra)

    # ---------------------------------------------------------------- run endpoints
    def _run(self, rest: str, q: dict, raw_query: str) -> None:
        parts = [urllib.parse.unquote(p) for p in rest.split("/")]
        name = parts[0]
        peer = self.app.owner(name)
        if peer is not None:
            try:
                body = peer.get("/api/run/" + "/".join(urllib.parse.quote(p) for p in parts)
                                + (f"?{raw_query}" if raw_query else ""), timeout=20)
                return self._send(200, body)
            except urllib.error.HTTPError as e:
                return self._send(e.code, e.read() or b"{}")
            except Exception as e:  # noqa: BLE001
                return self._json({"error": f"peer {peer.machine}: {e}"}, 502)
        st = self.app.store
        if name not in st.runs:
            return self._json({"error": f"unknown run {name}"}, 404)
        sub = parts[1] if len(parts) > 1 else ""
        if sub == "":
            return self._json(st.detail(name))
        if sub == "prs":
            return self._json(st.prs(name))
        if sub == "pr" and len(parts) > 2:
            d = st.pr_detail(name, parts[2])
            return self._json(d) if d else self._json({"error": "no such PR"}, 404)
        if sub == "network":
            return self._json(st.network(name))
        if sub == "feed":
            return self._json(st.feed(name, **_feed_args(q)))
        if sub == "agent" and len(parts) > 2:
            cats = _list(q, "cats")
            d = st.agent_detail(name, parts[2], limit=_int(q, "limit", 400, 1, 3000), before=_int(q, "before"),
                                cats=set(cats) if cats else None)
            return self._json(d) if d else self._json({"error": "no such agent"}, 404)
        if sub == "event" and len(parts) > 2:
            ev = st.event(name, int(parts[2]))
            return self._json(ev) if ev else self._json({"error": "no such event"}, 404)
        return self._json({"error": "not found"}, 404)

    def _series(self, q: dict) -> None:
        names = _list(q, "names")
        st = self.app.store
        out = {}
        by_peer: dict[int, list[str]] = {}
        for n in names:
            peer = self.app.owner(n)
            if peer is not None:
                by_peer.setdefault(self.app.peers.index(peer), []).append(n)
                continue
            with st.lock:
                run = st.runs.get(n)
                if run:
                    out[n] = run.series()
        for i, lst in by_peer.items():
            try:
                out.update(self.app.peers[i].get_json("/api/series?names=" + ",".join(map(urllib.parse.quote, lst))))
            except Exception:  # noqa: BLE001
                pass
        return self._json(out)

    def _ops(self, q: dict) -> None:
        minutes = _int(q, "minutes", 180, 10, 24 * 60)
        local = self.app.store.ops(minutes)
        if _flag(q, "local"):
            return self._json(local)
        machines = [local]
        for p in self.app.peers:
            try:
                machines.append(p.get_json(f"/api/ops?local=1&minutes={minutes}", timeout=8))
            except Exception as e:  # noqa: BLE001
                machines.append({"machine": p.machine or p.url, "error": str(e)})
        return self._json({"machines": machines, "peers": [p.status() for p in self.app.peers]})

    # ---------------------------------------------------------------- SSE
    def _stream(self, q: dict) -> None:
        if not self.app.streams.acquire(blocking=False):
            return self._json({"error": "too many streams"}, 503)
        try:
            self._stream_loop(q)
        finally:
            self.app.streams.release()

    def _sse(self, event: str, data) -> None:
        payload = json.dumps(data, separators=(",", ":"), default=_default)
        self.wfile.write(f"event: {event}\ndata: {payload}\n\n".encode())
        self.wfile.flush()

    def _stream_loop(self, q: dict) -> None:
        app, st = self.app, self.app.store
        local_only = _flag(q, "local")
        run = (q.get("run") or [None])[0]
        after = _int(q, "after")
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache, no-transform")
        self.send_header("X-Accel-Buffering", "no")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        self.close_connection = True
        # padding defeats proxies that buffer the first bytes of a response
        self.wfile.write(b": " + b" " * 2048 + b"\n\n")
        self._sse("hello", {"machine": st.machine, "now": time.time(), "run": run})
        sent: dict[str, tuple] = {}
        last_light = last_ping = last_peer_poll = 0.0
        seen_v = (-1, -1)
        peer = app.owner(run) if run and not local_only else None
        while True:
            now = time.time()
            v = (st.version, app.peer_version)
            if v != seen_v:
                seen_v = v
                changed = [s for s in app.merged(local_only)
                           if sent.get(s["name"]) != (s.get("machine"), s.get("version"), s.get("state"))]
                if changed:
                    for s in changed:
                        sent[s["name"]] = (s.get("machine"), s.get("version"), s.get("state"))
                    self._sse("summary", changed)
                if run and peer is None and after is not None:
                    res = st.feed(run, after=after, limit=500, cats=None)
                    if res and res["items"]:
                        after = res["items"][-1]["seq"]
                        self._sse("events", {"run": run, "items": res["items"], "seq": res["seq"]})
            if run and peer is not None and after is not None and now - last_peer_poll >= 1.0:
                last_peer_poll = now
                try:
                    res = peer.get_json(f"/api/run/{urllib.parse.quote(run)}/feed?after={after}&limit=500&cats=all",
                                        timeout=5)
                    if res.get("items"):
                        after = res["items"][-1]["seq"]
                        self._sse("events", {"run": run, "items": res["items"], "seq": res.get("seq")})
                except Exception:  # noqa: BLE001
                    pass
            if now - last_light >= 5:
                last_light = now
                self._sse("light", {"local": st.light(), "peers": [] if local_only else
                                    [p.status() for p in app.peers]})
            if now - last_ping >= 15:
                last_ping = now
                self.wfile.write(b": ping\n\n")
                self.wfile.flush()
            with st.cond:
                st.cond.wait(timeout=1.0 if peer is not None else 5.0)


# ---------------------------------------------------------------------------------------------------------------


def _default(o):
    if isinstance(o, (set, frozenset)):
        return sorted(o)
    if isinstance(o, tuple):
        return list(o)
    return str(o)


def _flag(q: dict, k: str) -> bool:
    return (q.get(k) or ["0"])[0] not in ("0", "", "false")


def _int(q: dict, k: str, default=None, lo=None, hi=None):
    try:
        v = int((q.get(k) or [None])[0])
    except (TypeError, ValueError):
        return default
    if lo is not None:
        v = max(lo, v)
    if hi is not None:
        v = min(hi, v)
    return v


def _list(q: dict, k: str) -> list[str]:
    raw = (q.get(k) or [""])[0]
    return [x for x in raw.split(",") if x]


def _feed_args(q: dict) -> dict:
    cats = _list(q, "cats")
    types = _list(q, "types")
    return {
        "before": _int(q, "before"), "after": _int(q, "after"), "limit": _int(q, "limit", 200, 1, 2000),
        "cats": None if not cats or cats == ["all"] else set(cats), "types": set(types) if types else None,
        "agent": (q.get("agent") or [None])[0] or None, "team": (q.get("team") or [None])[0] or None,
        "rnd": _int(q, "round"), "q": ((q.get("q") or [""])[0] or None), "involve": True,
    }


LOGIN_PAGE = """<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Swarm Ops: sign in</title>
<style>body{font:15px -apple-system,system-ui,sans-serif;background:#0d1117;color:#e6edf3;display:grid;place-items:center;
height:100vh;margin:0}form{background:#161b22;border:1px solid #30363d;padding:28px;border-radius:10px;width:320px}
input{width:100%;box-sizing:border-box;padding:9px;margin:12px 0;background:#0d1117;color:#e6edf3;border:1px solid #30363d;
border-radius:6px}button{padding:9px 14px;background:#2f81f7;color:#fff;border:0;border-radius:6px;cursor:pointer}</style>
<form method=get action="/"><b>Swarm Ops</b><div style="color:#8b949e;margin-top:6px">This dashboard needs an access token.</div>
<input name=token type=password placeholder="access token" autofocus><button>Open dashboard</button></form>"""


def make_server(root: Path, host: str = "127.0.0.1", port: int = 8765, peers: list[str] | None = None,
                token: str | None = None, machine: str | None = None, tick: float = 1.0,
                scan_processes: bool = True, fleet: bool = True, github_poll: bool = True,
                ) -> tuple[ThreadingHTTPServer, App]:
    store = Store(root, machine=machine, tick=tick, scan_processes=scan_processes, fleet=fleet,
                  github_poll=github_poll)
    app = App(store, peers or [], token)
    handler = type("BoundHandler", (Handler,), {"app": app})
    srv = ThreadingHTTPServer((host, port), handler)
    srv.daemon_threads = True
    return srv, app


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m dashboard", description=__doc__.split("\n")[0])
    ap.add_argument("--host", default="127.0.0.1", help="bind address (0.0.0.0 for LAN viewing)")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--root", default=".", help="repo root holding runs/ and results/")
    ap.add_argument("--peer", action="append", default=[],
                    help="another machine's dashboard to merge, e.g. http://laptop:8765 (add ?token=T if it has one)")
    ap.add_argument("--token", default=os.environ.get("DASHBOARD_TOKEN"),
                    help="require this access token (or set DASHBOARD_TOKEN); use it when the port is public")
    ap.add_argument("--machine", default=None, help="machine label (default: this hostname)")
    ap.add_argument("--tick", type=float, default=1.0, help="seconds between file polls")
    ap.add_argument("--no-fleet", action="store_true", help="skip device health (tailscale + fleet-statusd :7477)")
    ap.add_argument("--no-github", action="store_true",
                    help="don't read results/live-*.md snapshots from GitHub with gh (local checkout only)")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()
    if not (root / "runs").is_dir() and not (root / "results").is_dir():
        print(f"no runs/ or results/ under {root}", file=sys.stderr)
        return 2
    srv, app = make_server(root, args.host, args.port, args.peer, args.token, args.machine or hostname(), args.tick,
                           fleet=not args.no_fleet, github_poll=not args.no_github)
    app.start()
    shown = "localhost" if args.host in ("127.0.0.1", "0.0.0.0") else args.host
    print(f"Swarm Ops dashboard for {root} on http://{shown}:{args.port}/"
          + (f"?token={args.token}" if args.token else "") + f"  (machine {app.store.machine}, {len(app.peers)} peers)",
          flush=True)
    try:
        srv.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        app.store.stop()
        srv.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
