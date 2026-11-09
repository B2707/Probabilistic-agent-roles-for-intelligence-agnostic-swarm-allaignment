#!/usr/bin/env python3
"""Rebuild the theory chart and review page. Requires matplotlib; no agent calls."""

import csv
import html
import itertools
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import decision_regions
import conspiracy_model

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
FIGURES = PAPER / "figures"
T, N, I0, DEFAULT_P = 20, 100, 10, 0.02


def worker_rounds(p, turns=T):
    return math.fsum((1 - p) ** r for r in range(1, turns + 1))


def conversion_before_detection(p, k, future_turns):
    return (1 - k) * p * math.fsum(
        ((1 - p) * (1 - k)) ** j for j in range(future_turns)
    )


def smoke_check():
    # Enumerate conversion times independently of the survival-sum derivation.
    for turns in (1, 2, 6, 20):
        for p in (0, 0.01, 0.02, 0.5, 1):
            enumerated = math.fsum(
                (r - 1) * (1 - p) ** (r - 1) * p
                for r in range(1, turns + 1)
            ) + turns * (1 - p) ** turns
            assert math.isclose(worker_rounds(p, turns), enumerated, abs_tol=1e-12)
    assert worker_rounds(0) == T and worker_rounds(1) == 0
    assert math.isclose(worker_rounds(0.02), 16.287209384000366)
    counts = [90 * 0.98**r for r in range(1, 21)]
    total = math.fsum(counts)
    assert math.isclose(counts[-1], 60.08471745795848)
    assert math.isclose(total, 1465.848844560033)
    assert math.isclose(total / 2000, math.fsum(c / 100 for c in counts) / 20)
    assert not math.isclose(total / 2000, counts[-1] / 100)
    assert sum(r < 18 for r in range(1, 21)) == 17
    assert sum(r <= 18 for r in range(1, 21)) == 18
    assert all(worker_rounds(i / 1000) > worker_rounds((i + 1) / 1000)
               for i in range(1000))
    # Exhaust every four-round conversion/reset schedule, including initial investigators.
    for initial_worker in (False, True):
        for draws in itertools.product((False, True), repeat=4):
            for resets in itertools.product((False, True), repeat=4):
                baseline = reset = initial_worker
                baseline_count = reset_count = 0
                for convert, replace in zip(draws, resets):
                    if replace:
                        reset = True
                    baseline = baseline and not convert
                    reset = reset and not convert
                    baseline_count += baseline
                    reset_count += reset
                assert reset_count >= baseline_count
    for p, k in ((0, 0.1), (0.02, 0.01), (0.5, 0.2), (1, 0), (1, 1)):
        surviving = 1 - k
        converted = 0
        for _ in range(5):
            converted += surviving * p
            surviving *= (1 - p) * (1 - k)
        assert math.isclose(converted, conversion_before_detection(p, k, 5), abs_tol=1e-12)
    # Binary success with removal-as-failure gives the selected 40% threshold.
    assert (1 - 0.3) * 1 > 0.6
    assert (1 - 0.5) * 1 < 0.6
    for accepted, reported, failed_detection in ((0.5, 0.1, 0), (0.2, 0.3, 0.1), (0, 0, 1)):
        failed = 1 - accepted - reported
        h, b, d = 0.6, 1, 0.1
        offer = accepted*(1-d)*b + failed*(1-failed_detection)*h
        advantage = accepted*((1-d)*b-h) - (reported+failed*failed_detection)*h
        assert math.isclose(offer-h, advantage, abs_tol=1e-12)
        assert 0 <= offer <= 1
    # Enumerate complete two-future-round histories, rather than adding overlapping rewards.
    for p, k in ((0, 0), (0.02, 0.01), (0.5, 0.2), (1, 0), (1, 1)):
        for catch_success, worker_success in itertools.product((False, True), repeat=2):
            enumerated = 0
            for events in itertools.product((False, True), repeat=5):
                probability = 1
                for event, rate in zip(events, (k, p, k, p, k)):
                    probability *= rate if event else 1-rate
                active, converted = not events[0], False
                for conversion, audit in ((events[1], events[2]), (events[3], events[4])):
                    if active and not converted:
                        converted = conversion
                        if audit and not converted:
                            active = False
                success = catch_success if converted else worker_success
                enumerated += probability * int(active and success)
            g = conversion_before_detection(p, k, 2)
            f = (1-k)*((1-p)*(1-k))**2
            expected = g*catch_success + f*worker_success
            assert 0 <= expected <= 1
            assert math.isclose(enumerated, expected, abs_tol=1e-12)
        assert conversion_before_detection(p, k, 2) <= 1-(1-p)**2 + 1e-12


def build_figure():
    FIGURES.mkdir(exist_ok=True)
    rates = [i / 1000 for i in range(101)]
    values = [worker_rounds(p) for p in rates]
    with (FIGURES / "worker-rounds.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["P_conversion_per_round", "T", "N", "I0",
                         "expected_rounds_per_initial_worker", "expected_worker_agent_rounds",
                         "share_of_N_times_T", "expected_final_workers", "share_final_workers"])
        writer.writerows((p, T, N, I0, w, (N-I0)*w, (N-I0)*w/(N*T),
                          (N-I0)*(1-p)**T, (N-I0)*(1-p)**T/N)
                         for p, w in zip(rates, values))
    plt.rcParams.update({"font.size": 11, "svg.fonttype": "none"})
    fig, ax = plt.subplots(figsize=(7.2, 4.2), layout="constrained")
    ax.plot([p*100 for p in rates], values, color="#245a81", linewidth=2)
    chosen = worker_rounds(DEFAULT_P)
    ax.scatter([DEFAULT_P*100], [chosen], color="#245a81", s=35, zorder=3)
    ax.annotate(f"P = 2%: {chosen:.2f} rounds", (2, chosen), xytext=(3.1, 17.6),
                arrowprops={"arrowstyle": "-", "color": "#555555"})
    ax.set(xlim=(0, 10), ylim=(0, T), xlabel="Conversion probability P per round (%)",
           ylabel="Expected worker-role rounds\nper initially assigned worker")
    ax.set_xticks(range(0, 11, 2))
    ax.set_yticks(range(0, T+1, 5))
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#dddddd", linewidth=0.6)
    ax.set_axisbelow(True)
    ax.set_title("Worker-role allocation over 20 rounds", loc="left", fontsize=12)
    fig.savefig(FIGURES / "worker-rounds.png", dpi=240)
    fig.savefig(FIGURES / "worker-rounds.svg")
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(7.2, 4.3), layout="constrained")
    work_shares = [(N-I0)*w/(N*T)*100 for w in values]
    final_shares = [(N-I0)*(1-p)**T/N*100 for p in rates]
    ax.plot([p*100 for p in rates], work_shares, color="#245a81", linewidth=2,
            label="Worker-rounds / all 2,000 agent-rounds")
    ax.plot([p*100 for p in rates], final_shares, color="#a24e18", linewidth=2,
            linestyle="--", label="Final workers / all 100 agents")
    for share, color, label_x, offset in ((73.29244222800165, "#245a81", 2.3, 4),
                                          (60.08471745795848, "#a24e18", 1.0, -10)):
        ax.scatter([2], [share], color=color, s=30, zorder=3)
        ax.annotate(f"{share:.2f}%", (2, share), xytext=(label_x, share+offset), color=color)
    ax.set(xlim=(0, 10), ylim=(0, 100), xlabel="Conversion probability P per round (%)",
           ylabel="Share of the respective total (%)")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#dddddd", linewidth=0.6)
    ax.set_axisbelow(True)
    ax.set_title("Final headcount differs from accumulated worker-rounds", loc="left", fontsize=12)
    ax.legend(frameon=False, loc="lower left", fontsize=10)
    fig.savefig(FIGURES / "worker-shares.png", dpi=240)
    fig.savefig(FIGURES / "worker-shares.svg")
    plt.close(fig)



def build_page():
    chunks = (PAPER / 'theory-draft.txt').read_text().split('\n[')[1:]
    assert len(chunks) == 4
    panels = []
    for i, chunk in enumerate(chunks):
        title, content = chunk.split(']\n', 1)
        blocks = []
        for j, block in enumerate(content.strip().split('\n\n')):
            escaped = html.escape(block)
            if ' | ' in block:
                rows = [row.split(' | ') for row in block.splitlines()]
                table_id = ' id="counts-table"' if i == 0 else ''
                blocks.append('<table' + table_id + '><thead><tr>' + ''.join('<th scope="col">' + html.escape(cell) + '</th>' for cell in rows[0]) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join('<td>' + html.escape(cell) + '</td>' for cell in row) + '</tr>' for row in rows[1:]) + '</tbody></table>')
            elif block.startswith('    '):
                blocks.append('<pre>' + escaped.strip() + '</pre>')
            elif i == 0 and block.startswith('Your example'):
                continue  # The two timing conventions are shown by the timeline.
            elif i == 0 and block.startswith('With 100 agents'):
                blocks.append('<p id="parameters">' + escaped + '</p>SHARE_CHART')
            else:
                blocks.append('<p>' + escaped.replace('\n', '<br>') + '</p>')
            if i == 0 and j == 0:
                blocks.append('TIMELINE')
            if i == 1 and j == 0:
                blocks.append(decision_regions.visual_html())
            if i == 3 and j == 0:
                blocks.append(conspiracy_model.visual_html())
        if i == 1:
            blocks = blocks[:2] + ['<details><summary>Short model notes</summary>' + ''.join(blocks[2:]) + '</details>']
        if i == 3:
            blocks = blocks[:2] + ['<details><summary>Short model notes</summary>' + ''.join(blocks[2:]) + '</details>']
        panels.append('<section class="panel" id="panel-' + str(i) + '"' + (' hidden' if i else '') + '><h2>' + html.escape(title) + '</h2>' + ''.join(blocks) + '<details><summary>Comment on this part</summary><label for="note-' + str(i) + '">Quote a sentence or name a visual, then add your comment.</label><textarea rows="3" id="note-' + str(i) + '" data-note="' + html.escape(title) + '"></textarea></details></section>')
    timeline = '''<figure><label for="conversion-timing">One agent over 20 rounds</label><select id="conversion-timing"><option value="before">Convert before round 18, as in the code</option><option value="after">Convert after round 18, as in your example</option></select><div id="timeline" class="timeline" role="img"></div><figcaption id="timeline-result" aria-live="polite"></figcaption></figure>'''
    chart = '''<figure><svg id="share-chart" role="img" aria-labelledby="share-title share-desc"><title id="share-title">Final workers and accumulated worker-rounds are different</title><desc id="share-desc">At two percent conversion per round, workers are 60.08 percent of the final population but worker-rounds are 73.29 percent of all agent-rounds.</desc></svg><figcaption class="legend"><span><i class="line accumulated"></i>Worker-round share</span><span><i class="line final"></i>Final worker share</span></figcaption></figure><label for="probability">Conversion probability P per round: <output id="p-label">2.0%</output></label><input id="probability" type="range" min="0" max="10" step="0.1" value="2"><p class="sr-only" id="chart-result" aria-live="polite"></p>'''
    template = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Theory sketch</title><style>
*{box-sizing:border-box}html,body{margin:0;background:transparent;color:var(--foreground,CanvasText);font:14px/1.5 var(--font-sans,system-ui)}main{min-width:0}h2{font-size:18px;margin:12px 0}p{margin:0 0 12px}nav{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px}button,select,input,textarea{font:inherit}button,select,textarea{background:var(--card,Canvas);color:var(--foreground,CanvasText);border:1px solid var(--border,ButtonBorder);border-radius:var(--radius,6px);padding:8px}button[aria-pressed=true]{background:var(--primary,Highlight);color:var(--primary-foreground,HighlightText)}:focus-visible{outline:2px solid var(--ring,Highlight);outline-offset:3px}[hidden]{display:none!important}label{display:block;margin:10px 0 5px}select,textarea,input[type=range]{width:100%;min-width:0}input[type=range]{accent-color:var(--primary,Highlight)}textarea{resize:vertical}figure{margin:14px 0 18px}figcaption,.small{font-size:12px;color:var(--muted-foreground,GrayText)}.timeline{display:grid;grid-template-columns:repeat(20,minmax(0,1fr));gap:3px;margin:12px 0 7px}.slot{text-align:center;font-size:12px;padding:5px 0;background:var(--secondary,ButtonFace);color:var(--secondary-foreground,CanvasText);border-radius:2px}.slot.worker{background:var(--chart-1,Highlight);color:var(--primary-foreground,HighlightText)}svg{width:100%;height:235px;display:block}svg text{fill:var(--foreground,CanvasText);font-size:12px}svg .grid{stroke:var(--border,GrayText);stroke-width:1}.curve{fill:none;stroke-width:2.5}.accumulated{stroke:var(--chart-1,Highlight)}.final{stroke:var(--chart-2,GrayText);stroke-dasharray:5 4}.legend{display:flex;flex-wrap:wrap;gap:6px 18px}.legend span{display:inline-flex;align-items:center;gap:7px}.line{display:inline-block;width:20px;height:0;border-top:3px solid var(--chart-1,Highlight)}.line.final{border-top:3px dashed var(--chart-2,GrayText)}table{width:100%;border-collapse:collapse;margin:12px 0 16px;table-layout:fixed}td,th{text-align:left;vertical-align:top;padding:8px 4px;border-bottom:1px solid var(--border,ButtonBorder);overflow-wrap:anywhere}#counts-table th:first-child{width:42%}#counts-table th:nth-child(2){width:38%}#counts-table th:last-child{width:20%}pre{font:12px/1.5 var(--font-mono,monospace);white-space:pre-wrap;overflow-wrap:anywhere;margin:8px 0 12px}details,footer{border-top:1px solid var(--border,ButtonBorder);padding-top:12px;margin-top:14px}summary{font-weight:500}details[open]>summary{margin-bottom:10px}footer button{margin-bottom:8px}.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}@media(max-width:560px){.timeline{grid-template-columns:repeat(10,minmax(0,1fr))}nav button{flex:1}table{font-size:13px}}
</style></head><body><main><nav aria-label="Theory sections">NAV</nav>PANELS<footer><p class="small">P converts. K selects random audits. Code names are k and p respectively.</p><button id="collect" type="button">Collect comments</button><p id="status" role="status"></p><textarea id="comments" rows="4" aria-label="Collected comments" readonly hidden></textarea><p class="small">Comments stay here until copied into chat. Reloading clears them.</p></footer></main><script>
const tabs=[...document.querySelectorAll('[data-panel]')];tabs.forEach(b=>b.addEventListener('click',()=>{tabs.forEach(x=>x.setAttribute('aria-pressed',String(x===b)));document.querySelectorAll('.panel').forEach(p=>p.hidden=p.id!=='panel-'+b.dataset.panel);if(b.dataset.panel==='0')draw();}));
const timeline=document.getElementById('timeline'),timing=document.getElementById('conversion-timing');function drawTimeline(){const workers=timing.value==='before'?17:18;timeline.replaceChildren(...Array.from({length:20},(_,i)=>{const n=document.createElement('div');n.className='slot'+(i<workers?' worker':'');n.textContent=i+1;n.setAttribute('aria-label',`Round ${i+1}: ${i<workers?'worker':'investigator'}`);return n;}));const description=`${workers} worker rounds and ${20-workers} investigator rounds. Filled cells are worker turns; pale cells are investigator turns.`;document.getElementById('timeline-result').textContent=description;timeline.setAttribute('aria-label',description);}timing.addEventListener('change',drawTimeline);drawTimeline();
const svg=document.getElementById('share-chart'),slider=document.getElementById('probability');const workerRounds=p=>Array.from({length:20},(_,r)=>90*(1-p)**(r+1)).reduce((a,b)=>a+b,0);const finalWorkers=p=>90*(1-p)**20;
function node(tag,attrs,text){const n=document.createElementNS('http://www.w3.org/2000/svg',tag);Object.entries(attrs).forEach(([k,v])=>n.setAttribute(k,v));if(text!==undefined)n.textContent=text;return n;}
function draw(){const width=svg.getBoundingClientRect().width;if(!width)return;svg.setAttribute('viewBox',`0 0 ${width} 235`);svg.querySelectorAll('g').forEach(g=>g.remove());const g=node('g',{});svg.append(g);const left=40,right=16,top=24,bottom=187,x=p=>left+(width-left-right)*p/.1,y=v=>bottom-(bottom-top)*v/100;[0,25,50,75,100].forEach(v=>{g.append(node('line',{x1:left,y1:y(v),x2:width-right,y2:y(v),class:'grid'}));g.append(node('text',{x:left-7,y:y(v)+4,'text-anchor':'end'},v));});(width<440?[0,.05,.1]:[0,.02,.04,.06,.08,.1]).forEach(p=>g.append(node('text',{x:x(p),y:bottom+18,'text-anchor':'middle'},Math.round(p*100)+'%')));g.append(node('text',{x:left,y:13},'Share of each total, %'));g.append(node('text',{x:width/2,y:230,'text-anchor':'middle'},'Conversion probability P per round'));
const p=Number(slider.value)/100;for(const [name,fn] of [['accumulated',q=>workerRounds(q)/20],['final',finalWorkers]]){g.append(node('path',{class:'curve '+name,d:Array.from({length:101},(_,i)=>`${i?'L':'M'}${x(i/1000)},${y(fn(i/1000))}`).join(' ')}));g.append(node('circle',{cx:x(p),cy:y(fn(p)),r:4,fill:name==='accumulated'?'var(--chart-1,Highlight)':'var(--chart-2,GrayText)'}));}
const rows=document.querySelectorAll('#counts-table tbody tr'),w=workerRounds(p),end=finalWorkers(p);rows[0].cells[1].textContent=end.toFixed(2)+' of 100 agents';rows[0].cells[2].textContent=end.toFixed(2)+'%';rows[1].cells[1].textContent=w.toFixed(2)+' of 2000 agent-rounds';rows[1].cells[2].textContent=(w/20).toFixed(2)+'%';document.getElementById('p-label').textContent=(p*100).toFixed(1)+'%';document.getElementById('parameters').textContent=`100 agents, 10 initial investigators, 20 rounds, P = ${(p*100).toFixed(1)}%.`;document.getElementById('chart-result').textContent=`Final worker share ${end.toFixed(2)} percent; worker-round share ${(w/20).toFixed(2)} percent.`;}
slider.addEventListener('input',draw);new ResizeObserver(draw).observe(svg);draw();
document.getElementById('collect').addEventListener('click',async()=>{const text=[...document.querySelectorAll('[data-note]')].filter(n=>n.value.trim()).map(n=>n.dataset.note+'\n'+n.value.trim()).join('\n\n');const out=document.getElementById('comments'),status=document.getElementById('status');if(!text){status.textContent='Add a comment in a section first.';return;}out.value=text;out.hidden=false;try{await navigator.clipboard.writeText(text);status.textContent='Copied. Paste into chat.';}catch{status.textContent='Select and copy the comments below.';out.focus();out.select();}});
</script></body></html>'''
    labels = ['Worker rounds', 'Rational choices', 'Experiment', 'Conspiracy size']
    nav = ''.join('<button type="button" data-panel="' + str(i) + '" aria-pressed="' + str(i == 0).lower() + '" aria-controls="panel-' + str(i) + '">' + label + '</button>' for i, label in enumerate(labels))
    page = template.replace('NAV', nav).replace('PANELS', ''.join(panels)).replace('TIMELINE', timeline).replace('SHARE_CHART', chart)
    page = page.replace('</script></body>', decision_regions.visual_script() + conspiracy_model.visual_script() + '</script></body>')
    (PAPER / 'theory-review.html').write_text(page)


if __name__ == '__main__':
    smoke_check()
    decision_regions.smoke_check()
    conspiracy_model.smoke_check()
    build_figure()
    decision_regions.build_figure(FIGURES)
    conspiracy_model.build_figure(FIGURES)
    build_page()
    print(f'Checks passed. Review: {PAPER / "theory-review.html"}')
    print(f'Figures and CSV: {FIGURES}')
