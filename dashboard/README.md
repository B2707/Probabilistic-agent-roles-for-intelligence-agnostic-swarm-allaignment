# Swarm oversight results

A read-only web dashboard for this experiment. Each run gives a swarm of 100 AI coding agents 55 problems, and every problem contains one test that no correct code can pass. The dashboard shows how many agents cheated under each kind of oversight.

It reads the run folders in `results/`. It never writes to them. The server uses only the Python standard library. Charts load ECharts from cdnjs, so they need internet access.

## Start

From the repo root:

```
uv run python -m dashboard
```

Then open http://localhost:8765. A fresh clone needs nothing else: no `runs/` folder and no live experiment.

## What each view shows

- **Results**: the first screen. What the experiment is, then the average outcome for each oversight setup, per worker model. Below that are round-by-round charts, every metric for every run (copy as Markdown or download as CSV), and a chart to compare any metric across runs. Only complete runs go into averages.
- **All runs**: every run folder, grouped as complete, partial, stopped by hand, and earlier designs.
- **Run details**: one run in depth.
  - **Activity**: a per-problem heatmap, the agent grid, and a filterable event feed. A slider replays the run round by round.
  - **Charts**: 15 charts, each exportable as PNG.
  - **Network**: who approved, messaged and reported whom, with collusion groups.
  - **Agents** and **PRs**: sortable tables. Click a row for an agent's timeline or a PR's diff.
  - **Config**: the run's settings.
- **Operations**: throughput, retries and token use. This view appears only while runs are live or a `runs/` folder exists.

Hover over a column name to see what it counts.

## Options

| Flag | What it does |
|---|---|
| `--port 8765` | Port to serve on. |
| `--root PATH` | The repo root that holds `results/`. |
| `--host 0.0.0.0` | Allow other machines on the network to connect. |
| `--token T` | Require an access token. Use it whenever others can reach the port. |
| `--peer http://HOST:PORT` | Merge in another machine's dashboard. Repeatable. |
| `--machine NAME` | Label for this machine. |
| `--no-github` | Read status tables from the local checkout only. |
| `--tick 1.0` | Seconds between file polls. |

## Tests

`uv run pytest -q tests/test_dashboard.py` uses synthetic events only.
