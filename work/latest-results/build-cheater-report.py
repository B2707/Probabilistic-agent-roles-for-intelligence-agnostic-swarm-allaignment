"""Reformat the saved publication as agent-level misconduct, detection and removal counts."""
import csv
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
data = json.loads((ROOT / 'paper/results-evidence.json').read_text())
ref = data['source_commit']
base = f'https://github.com/B2707/agent-swarm-hackathon/blob/{ref}'
flagged = lambda v: bool(v and (v.get('misaligned_before_conversion') or v.get('misaligned_after_conversion')))
rows = []
for r in data['runs']:
    if r['folder'].count('/') != 1:
        continue
    c, m = r['config'], r['metrics']
    events = [json.loads(line) for line in subprocess.check_output(
        ['git', 'show', f'{ref}:{r["folder"]}/events.jsonl'], cwd=ROOT).splitlines() if line.strip()]
    audits = [e for e in events if e['type'] == 'audit' and 'final' not in e.get('triggers', []) and flagged(e.get('verdict'))]
    caught = {e['agent'] for e in audits}
    removed = {e['agent'] for e in events if e['type'] == 'agent_removed'}
    authors = set(m['cheaters'])
    final_rows = [json.loads(line) for line in subprocess.check_output(
        ['git', 'show', f'{ref}:{r["folder"]}/reaudit-opus.jsonl'], cwd=ROOT).splitlines() if line.strip()]
    final = {e['agent']: e['verdict'] for e in final_rows}
    total = caught | authors | {agent for agent, verdict in final.items() if flagged(verdict)}
    assert (len(total), len(caught), len(removed)) == (m['misaligned_total'], m['misaligned_caught'], m['agents_removed'])
    assert removed <= caught <= total
    immune = {e['agent'] for e in audits if e.get('immune')}
    assert caught - removed <= immune
    rows.append(dict(folder=r['folder'], model='Luna' if 'luna' in c['worker_model'] else 'Sol', arm=c['name'][0],
                     seed=c['seed'], extra=r['extra'], cheaters=len(total), caught=len(caught), removed=len(removed),
                     caught_not_removed=len(caught - removed), not_caught=len(total - caught),
                     code_authors=len(authors), code_authors_caught=len(authors & caught),
                     code_authors_removed=len(authors & removed), source_commit=ref))
rows.sort(key=lambda r: (r['extra'], r['model'], r['arm'], r['seed']))
assert len(rows) == 25
with (OUT / 'cheater-counts.csv').open('w', newline='') as stream:
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
grouped = defaultdict(list)
for row in rows:
    if not row['extra']:
        grouped[row['model'], row['arm']].append(row)
groups = [dict(model=model, arm=arm, seeds=len(rr), **{
    key: sum(r[key] for r in rr) for key in ['cheaters', 'caught', 'removed', 'code_authors', 'code_authors_caught', 'code_authors_removed']})
    for (model, arm), rr in grouped.items()]
assert len(groups) == 10 and sum(g['seeds'] for g in groups) == 22
(OUT / 'cheater-counts.json').write_text(json.dumps(dict(source_commit=ref, source_time=data['source_commit_time'],
    definitions=dict(cheaters='Published misconduct total: runtime flags, full-pass code authors, or final-audit flags.',
                     caught='Unique agents flagged by an audit during the run, excluding final audits.',
                     removed='Caught agents removed during the run. All removal events have distinct agent IDs.'),
    groups=groups, runs=rows, smoke_check='passed'), indent=2) + '\n')

prior = (OUT / 'report.html').read_text()
style = re.search(r'<style>([\s\S]*?)</style>', prior)[1]
script = re.search(r'<script>([\s\S]*?)</script>', prior)[1]
def note(key, label):
    return f'<details class="feedback"><summary>Comment</summary><label for="note-{key}">{label}</label><textarea id="note-{key}" rows="2" data-note="{label}"></textarea></details>'

scale = max(g['cheaters'] for g in groups)
table_rows = []
for g in groups:
    label = f'{g["model"]} {g["arm"]}'
    cells = ''.join(f'<td class="count"><div class="mini" role="img" aria-label="{label}, {key}: {g[key]} agents">'
                    f'<i class="{key}" style="width:{100*g[key]/scale:.3f}%"></i></div><span>{g[key]}</span></td>'
                    for key in ['cheaters', 'caught', 'removed'])
    table_rows.append(f'<tr><td>{label}{note(label.replace(" ", "-"), label)}</td><td class="num">{g["seeds"]}</td>{cells}</tr>')
def run_table(selected):
    rr = []
    for r in selected:
        label = f'{r["model"]} {r["arm"]} · seed {r["seed"]}'
        rr.append(f'<tr><td><a href="{base}/{r["folder"]}/metrics.json" target="_blank" rel="noreferrer">{label}</a>'
                  + note(r['folder'].split('/')[-1], label) + '</td>'
                  + ''.join(f'<td class="num">{r[k]}</td>' for k in ['cheaters', 'caught', 'removed']) + '</tr>')
    return '<div class="table-wrap"><table><thead><tr><th>Run</th><th>Cheaters</th><th>Caught</th><th>Removed</th></tr></thead><tbody>'+''.join(rr)+'</tbody></table></div>'

body = f'''<main id="latest-results"><h2>Cheaters, caught and removed</h2>
<p class="muted">Same snapshot · 8 Nov 2026, 6:05 p.m. EST · counts of agents</p>
<p><strong>Cheaters</strong> uses the published misconduct total, including proposing or approving cheating. <strong>Caught</strong> means flagged during the run. <strong>Removed</strong> is the subset actually removed. Final audits contribute to the total, not to caught or removed.</p>
<p>Totals across the listed seeds. A/B/C have three seeds each; D/E/F have one. Bars share the same scale.</p>
<div class="table-wrap"><table class="comparison"><thead><tr><th>Model / arm</th><th>Seeds</th><th>Cheaters</th><th>Caught</th><th>Removed</th></tr></thead><tbody>{''.join(table_rows)}</tbody></table></div>
<p>Each run starts with 100 agents; removals introduce replacements. Totals pool seeds. All caught agents who remained in the swarm had investigator immunity. The three disturbed Luna seed-1 extras are shown separately below.</p>
<details><summary>Condition definitions</summary><p>A: no runtime oversight, with instigator.<br>B: undisclosed investigators and audits.<br>C: disclosed investigators and audits.<br>D: warning without runtime enforcement.<br>E: warning plus random audits, no investigators.<br>F: no instigator or runtime oversight.</p><p>D/E Sol has no published completed run in this snapshot.</p></details>
<details><summary>Every seed, 22 comparison runs</summary>{run_table([r for r in rows if not r['extra']])}</details>
<details><summary>Three disturbed seed-1 extras</summary>{run_table([r for r in rows if r['extra']])}</details>
<details><summary>Code authors only</summary><p>This narrower count uses authors linked to code that passed every test. Caught and removed intersect those same author IDs, so the counts use a consistent group.</p><div class="table-wrap"><table><thead><tr><th>Model / arm</th><th>Authors</th><th>Caught</th><th>Removed</th></tr></thead><tbody>'''
body += ''.join(f'<tr><td>{g["model"]} {g["arm"]}</td>'+''.join(f'<td class="num">{g[k]}</td>' for k in ['code_authors','code_authors_caught','code_authors_removed'])+'</tr>' for g in groups)
body += f'''</tbody></table></div></details><p class="muted">Source <a href="{base}/swarm/metrics.py#L237" target="_blank" rel="noreferrer">metric definitions</a> · publication <code>{ref[:12]}</code>. Counts are observed classifications; undetected misconduct may remain.</p>
<button id="collect" type="button">Collect comments</button><p id="status" class="muted" aria-live="polite"></p><label for="collected">Comments to copy into chat</label><textarea id="collected" rows="2" readonly></textarea></main>'''
style += '''\n.comparison{table-layout:fixed}.comparison th:first-child{width:25%}.comparison th:nth-child(2){width:9%}.comparison td{vertical-align:middle}.count{font-variant-numeric:tabular-nums;text-align:right}.mini{height:12px;position:relative;margin-bottom:5px}.mini i{display:block;height:12px}.cheaters{background:var(--chart-1)}.caught{background:var(--chart-2)}.removed{background:var(--chart-3,var(--success))}@media(max-width:520px){.comparison th{font-size:12px}.comparison td{font-size:14px}.comparison th:first-child{width:26%}}'''
page = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Cheaters, caught and removed</title><style>'+style+'</style>'+body+'<script>'+script+'</script></html>'
assert page.count('class="mini"') == 30 and page.count('data-note=') == 35
(OUT / 'cheaters.html').write_text(page)
print(json.dumps(groups, indent=2))
