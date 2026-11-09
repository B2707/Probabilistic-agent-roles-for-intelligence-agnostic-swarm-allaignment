"""Opus final audit against terra's final audit, per finished v3 A/B/C run in results/.

terra's final verdicts are the run's `audit` events with "final" in `triggers` (events.jsonl). Opus's are
RUN/reaudit-opus.jsonl (`swarm reaudit RUN --name opus --model claude/claude-opus-5-5 --effort xhigh`, one row per
agent). An agent is flagged when a verdict says misaligned before or after conversion (swarm.metrics._misaligned).

Per run: agents both audited, how many each flags, agreement, who only one flags, recall on objective cheaters
(metrics.json `cheaters`), and the misaligned total (in-round catches | objective cheaters | final flags) under each
final auditor. Usage, from the repo root: python3 scripts/opus_vs_terra.py [--json OUT]
"""
import glob, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from swarm.metrics import _misaligned

rows = []
for run in sorted(glob.glob("results/[ABC]100-6*-*")):
    if run.endswith("-stopped"):
        continue
    m = json.load(open(f"{run}/metrics.json"))
    if m.get("final_auditor") != "opus":
        continue
    terra, caught = {}, set()
    for line in open(f"{run}/events.jsonl"):
        if '"audit"' not in line:
            continue
        e = json.loads(line)
        if e["type"] != "audit":
            continue
        if "final" in e["triggers"]:
            terra[e["agent"]] = _misaligned(e["verdict"])
        elif _misaligned(e["verdict"]):
            caught.add(e["agent"])
    opus = {r["agent"]: _misaligned(r["verdict"]) for r in map(json.loads, open(f"{run}/reaudit-opus.jsonl"))}
    both = set(terra) & set(opus)
    t_flag = {a for a in both if terra[a]}
    o_flag = {a for a in both if opus[a]}
    cheaters = set(m["cheaters"])
    total_terra = caught | cheaters | {a for a, v in terra.items() if v}
    total_opus = caught | cheaters | {a for a, v in opus.items() if v}
    rows.append({
        "run": run.split("/", 1)[1], "terra_audited": len(terra), "opus_audited": len(opus), "both": len(both),
        "terra_flags": len(t_flag), "opus_flags": len(o_flag), "agree": len(both) - len(t_flag ^ o_flag),
        "terra_only": sorted(t_flag - o_flag), "opus_only": sorted(o_flag - t_flag),
        "cheaters": len(cheaters), "cheaters_in_both": len(cheaters & both),
        "terra_cheater_hits": len(cheaters & t_flag), "opus_cheater_hits": len(cheaters & o_flag),
        "caught_in_round": len(caught), "total_terra": len(total_terra), "total_opus": len(total_opus),
        "metrics_total": m["misaligned_total"],
    })

for r in rows:
    print(f"{r['run'][:34]:34} both {r['both']:3}  terra {r['terra_flags']:3}  opus {r['opus_flags']:3}  "
          f"agree {r['agree']:3}  terra-only {len(r['terra_only']):2}  opus-only {len(r['opus_only']):2}  "
          f"cheaters hit t/o {r['terra_cheater_hits']}/{r['opus_cheater_hits']} of {r['cheaters_in_both']}  "
          f"total t/o {r['total_terra']}/{r['total_opus']} (metrics {r['metrics_total']})")
s = lambda k: sum(len(r[k]) if isinstance(r[k], list) else r[k] for r in rows)
print(f"ALL {len(rows)} runs: both audited {s('both')}, agree {s('agree')} ({s('agree') / s('both'):.1%}), "
      f"terra flags {s('terra_flags')}, opus flags {s('opus_flags')}, terra-only {s('terra_only')}, "
      f"opus-only {s('opus_only')}; objective cheaters hit terra {s('terra_cheater_hits')}, "
      f"opus {s('opus_cheater_hits')} of {s('cheaters_in_both')}")
if "--json" in sys.argv:
    json.dump(rows, open(sys.argv[sys.argv.index("--json") + 1], "w"), indent=1)
