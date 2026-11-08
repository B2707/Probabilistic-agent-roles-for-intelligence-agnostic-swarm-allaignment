# Swarm Ops dashboard

A live, read-only web console for the swarm runs. It tails every `events.jsonl` under `runs/` and `results/` and pushes new events to the browser with Server-Sent Events, usually within half a second. The server uses only the Python standard library. Charts come from ECharts 5.5.0 on cdnjs.

## Start

From the repo root:

```
uv run python -m dashboard                      # http://localhost:8765
uv run python -m dashboard --host 0.0.0.0       # LAN viewing
uv run python -m dashboard --token "$TOKEN"     # require a token (use this whenever the port is reachable by others)
```

| Flag | What it does |
|---|---|
| `--port 8765` | Port to serve on. |
| `--root PATH` | The repo root that holds `runs/` and `results/`. |
| `--peer http://HOST:PORT` | Merges another machine's dashboard. Repeatable. Add `?token=T` if that dashboard has a token. Each peer's runs are labelled with its machine name. |
| `--machine NAME` | Machine label. Defaults to the macOS LocalHostName. |
| `--machine-alias GIT_NAME=DEVICE` | Says that the machine pushing `results/live-GIT_NAME.md` is the Tailscale device `DEVICE` (its DNS name, such as `danas-macbook-pro`). Its snapshot runs then show on that device's Fleet card and get its CPU line in the overview, instead of under "Machines seen through git". Repeatable. |
| `--no-fleet` | Skips device health, which comes from Tailscale and the fleet-statusd server on port 7477. |
| `--no-github` | Reads `results/live-*.md` from the local checkout only, not from GitHub through `gh`. |
| `--tick 1.0` | Seconds between file polls. |

## What it reads

The dashboard never writes. It reads these sources:

- `runs/<run>/` and `results/<run>/` (also `results/ordered/`, `results/stopped/` and `results/v1/`): config, events and judge labels.
- `results/live-<machine>.md`: the status table another machine pushes through git. It shows the laptop's seed-2 runs before they publish.
- `runs/queue.log`, `ps`, and the machine's load and memory.
- `tailscale status --json` and `http://<device>:7477/status`: device battery, CPU and memory, the same path the fleet menu bar app uses.

Paper metrics come from `swarm.metrics.compute`, run in memory. They match `results/metrics.md`, and the dashboard never writes `metrics.json`.

## Views

The dashboard has five views:

- **Overview**: every run grouped as v3, stopped, v2 archive, and v1, with v3 split by worker model. Each row shows state (running, resuming, usage-limit, interrupted, labelled), progress, ETA, cheats on main, cheaters, removals, retries, and device health.
- **Results**: the v3 arms side by side, with seeds 1 and 2 paired per arm. It has round-by-round charts, a metric table you can copy as Markdown or download as CSV, an overlay of any metric across any runs, and the v2 archive as a secondary section.
- **Run**: each run has these tabs:
  - **Live**: tiles, a replay slider, a per-problem heatmap, an agent grid, and a filterable live feed.
  - **Charts**: 15 charts, each exportable as PNG.
  - **Network**: approvals, DMs, instigator pushes, reports and judge labels, with conspiracy groups and replay.
  - **Agents**: a sortable table of every agent.
  - **PRs**: every PR, with diff, reviews and judge labels.
  - **Config**: the run's configuration.

  Click any agent ID or PR ID to open its timeline or diff.
- **Fleet**: every Tailscale device, with battery, CPU, memory pressure and uptime, plus which runs it hosts. Machines that report only through git appear too.
- **Ops**: throughput and 403 retries per minute, turns by run, tokens by run, usage-limit stops and resumes, and the tail of `runs/queue.log`.

## Tests

`uv run pytest -q tests/test_dashboard.py` uses synthetic events only.

## Sharing it (Tailscale Funnel)

Funnel is enabled on the tailnet. The public address is https://baders-macbook-pro.tail9fc878.ts.net/. It only works while the dashboard runs, and it always requires the token.

```
# start detached in its own session, with the token from ~/.config/swarm-dash/token (kept out of the process list);
# the laptop pushes results/live-laptop.md and is the Tailscale device danas-macbook-pro
DASHBOARD_TOKEN="$(cat ~/.config/swarm-dash/token)" nohup python3 scripts/detach.py uv run python -m dashboard --port 8765 \
  --machine-alias laptop=danas-macbook-pro > ~/.config/swarm-dash/dashboard.log 2>&1 < /dev/null &
/Applications/Tailscale.app/Contents/MacOS/Tailscale funnel --bg 8765      # expose it
/Applications/Tailscale.app/Contents/MacOS/Tailscale funnel --https=443 off # stop exposing it
pkill -f "python -m dashboard --port 8765"                                  # stop the dashboard
```

To share a link, append `?token=<token>`. The first visit with the token sets a cookie, so later visits don't need it. To revoke access, replace the token file and restart the dashboard.
