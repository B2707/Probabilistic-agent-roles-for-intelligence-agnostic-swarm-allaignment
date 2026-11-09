"""Restricted offer game with one-round delivery and binary individual success."""

import csv
import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from decision_regions import forward_values, investigator_prior, values

P, K, REMAINING = .015, .01, 18
ROOT = Path(__file__).resolve().parents[1]


def payoffs(p=P, k=K, b=1, recipient_investigator=None):
    """Worker writes in round 1, recipient responds in 2, reply arrives in 3."""
    q = investigator_prior(p, partners=1) if recipient_investigator is None else recipient_investigator
    rw, aw, _ = values(p, k, b, REMAINING, partners=1)
    # The converted sender's earlier offer is immune but still reportable.
    ri = 1-(1-p)**REMAINING
    ai = (1-k)*p
    receiver_refuse = (1-p)*rw+p*ri
    receiver_accept = (1-p)*aw+p*ai
    accepts = receiver_accept > receiver_refuse+1e-12
    factor = (1-q)*(1-k)*(1-p)
    a0 = values(p, k, 0, REMAINING, partners=1)[1]
    a1 = values(p, k, 1, REMAINING, partners=1)[1]
    task = factor*(1-p)*b*a1
    catch = factor*((1-p)*(1-b)*a0+p*(1-k))
    return dict(recipient_prior=q, receiver_refuse=receiver_refuse,
                receiver_accept=receiver_accept, receiver_accepts=accepts,
                send_if_accept=task+catch, send=task+catch if accepts else 0.,
                task=task if accepts else 0., catch=catch if accepts else 0.)


def smoke_check():
    o = payoffs()
    assert math.isclose(o['receiver_accept'], .6776174636196519)
    assert math.isclose(o['receiver_refuse'], .2195065935305419)
    assert math.isclose(o['send'], .5977534832717478)
    assert math.isclose(o['task'], .5849305045592478)
    assert math.isclose(o['catch'], .0128229787125)
    assert not payoffs(b=0)['receiver_accepts'] and payoffs(b=0)['send'] == 0
    # Enumerate startup events; use the independent recursion for later rounds.
    for p, k in ((0, 0), (0, .1), (.015, .01), (.2, .1), (1, 0), (1, 1)):
        for q in (0, .2, 1):
            for b in (0, .1, 1):
                v = payoffs(p, k, b, q)
                total = 0.
                for audited in (False, True):
                    for recipient_was_investigator in (False, True):
                        for sender_converts in (False, True):
                            for recipient_converts in (False, True):
                                mass = k if audited else 1-k
                                mass *= q if recipient_was_investigator else 1-q
                                mass *= p if sender_converts else 1-p
                                mass *= p if recipient_converts else 1-p
                                if audited or recipient_was_investigator or recipient_converts:
                                    reward = 0.
                                elif sender_converts:
                                    reward = 1-k
                                else:
                                    reward = forward_values(p, k, b, 1, REMAINING, True)[1]
                                total += mass*reward
                assert math.isclose(total, v['send_if_accept'], abs_tol=1e-11)
                assert all(-1e-12 <= v[key] <= 1+1e-12 for key in
                           ('send', 'receiver_accept', 'receiver_refuse', 'task', 'catch'))
                assert math.isclose(v['task']+v['catch'], v['send'], abs_tol=1e-11)
    lo, hi = 0., 1.
    for _ in range(50):
        mid = (lo+hi)/2
        if payoffs(b=mid)['receiver_accepts']:
            hi = mid
        else:
            lo = mid
    assert math.isclose((lo+hi)/2, .08671330641096181, abs_tol=1e-10)


def build():
    out = ROOT/'paper'/'figures'
    bs = np.linspace(0, 1, 201)
    data = [payoffs(b=b) for b in bs]
    with (out/'sender-game.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['task_success_b', *data[0]])
        writer.writeheader()
        writer.writerows(dict(task_success_b=b, **row) for b, row in zip(bs, data))
    fig, axes = plt.subplots(1, 2, figsize=(9.8, 4.7))
    ax = axes[0]
    ax.plot(bs*100, [r['receiver_accept']*100 for r in data], color='#ba2828', label='Accept')
    ax.plot(bs*100, [r['receiver_refuse']*100 for r in data], color='#19733c', label='Refuse and keep evidence')
    ax.axvline(8.671330641, color='#777777', linestyle=':', linewidth=1)
    ax.set(xlim=(0, 100), ylim=(0, 100), xlabel='Task success if both cooperate, b (%)',
           ylabel='Survival with success (%)', title="Receiver's response")
    ax.legend(frameon=False, fontsize=9)
    ax = axes[1]
    zero, one = payoffs(b=0), payoffs(b=1)
    cut = (one['receiver_refuse']-zero['receiver_accept'])/(one['receiver_accept']-zero['receiver_accept'])
    xs = np.linspace(cut, 1, 101)
    send = (zero['send_if_accept']+(one['send_if_accept']-zero['send_if_accept'])*xs)*100
    ax.axhspan(0, 100, color='#d1edda')
    ax.fill_between(xs*100, 0, send, color='#f5d1cf')
    ax.plot(xs*100, send, color='#333333', linewidth=1.4)
    ax.vlines(cut*100, 0, send[0], colors='#777777', linestyles=':', linewidth=1)
    ax.plot([0, cut*100], [0, 0], color='#777777', linewidth=2, clip_on=False)
    ax.text(55, 82, 'Aligned: no offer', ha='center', color='#176332')
    ax.text(65, 15, 'Misaligned: send', ha='center', color='#a12020')
    ax.scatter([100], [0], marker='x', color='#222222', s=45, clip_on=False, zorder=4)
    ax.set(xlim=(0, 100), ylim=(0, 100), xlabel='Task success if both cooperate, b (%)',
           ylabel='Success from the alternative, H (%)', title="Sender's initial choice")
    for ax in axes:
        ax.spines[['top', 'right']].set_visible(False)
    fig.suptitle('P = 1.5%, K = 1%; a restricted two-person offer game', fontsize=12)
    fig.text(.02, .015, 'Two-person toy, not the three-person PR requirement. Offer in round 1; response in 2; reply in 3.\n'
             'Sender is a worker when writing. Random recipient; perfect audits; no outside targets; alternative foregone on sending.\n'
             'Refusal wins receiver ties. At H=0 and b below 8.67%, no offer is tied, not strictly better.', fontsize=8)
    fig.tight_layout(rect=(0, .15, 1, .94))
    fig.savefig(out/'sender-game.png', dpi=220, bbox_inches='tight')
    fig.savefig(out/'sender-game.svg', bbox_inches='tight')
    plt.close(fig)
    constants = dict(r=one['receiver_refuse'], a0=zero['receiver_accept'],
                     a1=one['receiver_accept'], s0=zero['send_if_accept'],
                     s1=one['send_if_accept'], task1=one['task'])
    (ROOT/'paper'/'sender-game-review.html').write_text(HTML.replace('MODEL_DATA', json.dumps(constants)))


HTML = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Who would send the offer?</title><style>
*{box-sizing:border-box}html,body{margin:0;background:transparent;color:var(--foreground,CanvasText);font:14px/1.5 var(--font-sans,system-ui)}main{min-width:0}h1{font-size:20px;margin:4px 0 10px}h2{font-size:16px;margin:18px 0 8px}p{margin:0 0 10px}.small,figcaption{font-size:12px;color:var(--muted-foreground,GrayText)}figure{margin:12px 0}svg{display:block;width:100%;height:265px}svg text{fill:var(--foreground,CanvasText);font-size:12px}.grid{stroke:var(--border,GrayText);stroke-width:1}label{display:block;margin:10px 0 4px}input,textarea,button{font:inherit}input[type=range],textarea{width:100%;min-width:0}input{accent-color:var(--primary,Highlight)}button,textarea{background:var(--card,Canvas);color:var(--foreground,CanvasText);border:1px solid var(--border,ButtonBorder);border-radius:var(--radius,6px);padding:8px}button{margin-top:8px}details{border-top:1px solid var(--border,ButtonBorder);padding-top:10px;margin-top:14px}summary{font-weight:500}details[open]>summary{margin-bottom:10px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:12px/1.5 var(--font-mono,monospace)}.good{color:var(--success,#19733c)}.bad{color:var(--destructive,#ba2828)}.legend{display:flex;gap:14px;flex-wrap:wrap}.legend span{display:inline-flex;gap:6px;align-items:center}.key{height:3px;width:18px;display:inline-block}.refuse{background:var(--success,#19733c)}.accept{background:var(--destructive,#ba2828)}[hidden]{display:none!important}:focus-visible{outline:2px solid var(--ring,Highlight);outline-offset:3px}
</style></head><body><main>
<h1>Who would send the offer?</h1>
<p>At P=1.5% and K=1%, a worker can rationally send an offer. The earlier gray sender chart left this decision unspecified. It did not predict refusal.</p>
<p class="small">This is a restricted two-person game, not a complete model of the three-person PR requirement. The sender is a worker when writing in round 1, and the receiver knows this for this example. The recipient responds in round 2; its reply arrives in round 3. It checks that the sender is still active. A current investigator reports a genuine offer. Audits verify perfectly. There are no outside catch targets or later recruitment attempts. After conversion, agents report known peer violations without new misconduct. A separate alternative is foregone if the sender offers.</p>
<label for="b">Task success if both remain workers and cooperate, b: <output id="b-label">100%</output></label><input id="b" type="range" min="0" max="100" step="1" value="100">
<h2>1. Calculate the receiver's best response</h2>
<p id="receiver-result" aria-live="polite"></p>
<figure><svg id="receiver" role="img" aria-label="Receiver acceptance and refusal values as task success varies"></svg><figcaption class="legend"><span><i class="key accept"></i>Accept</span><span><i class="key refuse"></i>Refuse and keep evidence</span></figcaption></figure>
<details><summary>Comment on the receiver</summary><label for="note-receiver">Name a claim or part of the chart, then add your comment.</label><textarea id="note-receiver" rows="2" data-note="Receiver"></textarea></details>
<h2>2. The sender anticipates that response</h2>
<label for="h">Success from choosing the separate alternative, H: <output id="h-label">0%</output></label><input id="h" type="range" min="0" max="100" step="1" value="0">
<p id="sender-result" aria-live="polite"></p>
<figure><svg id="sender" role="img" aria-label="Sender decision regions over cooperation success and the separate alternative"></svg><figcaption>Green: no offer is better. Red: sending is better. Boundaries are ties. Below b=8.67%, the receiver refuses; at H=0, no offer and sending then tie.</figcaption></figure>
<p id="routes" class="small"></p><p class="small">At b=0 the receiver refuses. The sender cannot create a catch merely by making an offer.</p>
<details><summary>Sender equation and assumptions</summary><p>Let a be the chance that a worker recipient accepts, qR the chance the recipient is already an investigator when contacted, and Vcoop the sender's value after both are workers and agree in round 2.</p><pre>Uoffer = a(1−qR)(1−K)(1−P)
         × [(1−P)Vcoop + P(1−K)]
Send if Uoffer &gt; H.</pre><p>The first branch continues as guilty workers. The second has the sender convert before seeing the acceptance, then catch the recipient when its reply arrives. A refused offer earns zero here because it creates no other guilty target, secures no task reward, and has no fallback. A broader model must include any fallback that remains available.</p></details>
<details><summary>Comment on the sender</summary><label for="note-sender">Name a claim or part of the chart, then add your comment.</label><textarea id="note-sender" rows="2" data-note="Sender"></textarea></details>
<h2>3. What does receiving an offer reveal?</h2>
<p>Your inference holds if workers never send and investigators do. If neither kind sends, an unexpected offer does not identify its author. We need each kind's offering probability.</p>
<p>A genuine prohibited offer is also a new violation for an already-investigator author. Reporting the recruited cheater audits that author too. Investigators therefore need their own incentive calculation.</p>
<details><summary>Beliefs, timing, and limits</summary>
<p>Let Q be the prior probability that the author is an investigator when writing. Let sI be the probability that an investigator writes this offer, and sW the corresponding worker probability.</p>
<pre>Pr(investigator when writing | offer)
    = Q × sI / [Q × sI + (1−Q) × sW]</pre>
<p>If workers never send and investigators sometimes send, the offer identifies an investigator within that model. If neither kind sends, the message has probability zero. The fraction is undefined, so it supplies no such inference. Workers with different information about task success or alternatives can also choose differently.</p>
<p>A new prohibited proposal is itself a violation for an already-investigator author. Reporting also audits that investigator, so reporting a recruited cheater would expose its own new misconduct. Pretending to cooperate is allowed only while avoiding the prohibited acts. Thus we cannot assume an investigator benefits from sending the same forbidden proposal. Its offering decision needs its own payoff comparison.</p>
<p>Writing and delivery can straddle conversion. In this benchmark the author is a worker when writing, but has a 1.5% chance of having converted when the active sender's message is read next round. Its earlier offer remains a reportable, immune violation. This differs from the earlier chart's clean current-investigator branch.</p>
<p>At b=0 the rational receiver refuses, so the sender creates no catch target. At b=100%, task reward alone contributes 58.49 percentage points to the sender's 59.78% value. The remaining 1.28 points require a catch without task success. The calculation therefore does not support an exclusively betrayal-based motive.</p>
<p>The sender's prior that a random recipient is already an investigator when writing is 11.45%. This follows from 100 agents, 10 initial investigators, one completed conversion draw, and the sender being a worker. It is not the receiver's posterior about who authored the offer.</p>
<p>This solves a restricted worker-authored offer game. It does not solve all possible investigator offers, future recruitment, or a full signalling equilibrium. The conspiracy-size measurements retain their existing conditioning and are unchanged.</p>
<p class="small">The general belief and best-response framework follows <a href="https://ocw.mit.edu/courses/6-254-game-theory-with-engineering-applications-spring-2010/575baf93686c6b65dea35d10bb9e5a85_MIT6_254S10_lec17.pdf">MIT Lecture 17</a>. The payoff formulas and numbers here are our derivation for this restricted game.</p>
</details>
<details><summary>Comment on the inference</summary><label for="note-belief">Quote the inference or assumption you want to change.</label><textarea id="note-belief" rows="2" data-note="Role inference"></textarea></details>
<button type="button" id="collect">Collect comments</button><p id="status" class="small"></p><textarea id="comments" rows="4" aria-label="Collected comments" readonly hidden></textarea><p class="small">Comments stay here until copied into chat. Reloading clears them.</p>
</main><script>
const C=MODEL_DATA,B=document.getElementById('b'),H=document.getElementById('h'),ns='http://www.w3.org/2000/svg';
function node(tag,attrs,text){const n=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,v);if(text!==undefined)n.textContent=text;return n;}
function outcome(b){const a=C.a0+(C.a1-C.a0)*b,accepts=a>C.r+1e-12;return {a,r:C.r,accepts,s:accepts?C.s0+(C.s1-C.s0)*b:0,task:accepts?C.task1*b:0};}
function chart(id){const s=document.getElementById(id),w=s.getBoundingClientRect().width;s.setAttribute('viewBox','0 0 '+w+' 265');s.replaceChildren();const l=43,r=13,t=25,z=218,x=b=>l+(w-l-r)*b,y=v=>z-(z-t)*v;for(const v of [0,.25,.5,.75,1]){s.append(node('line',{x1:l,x2:w-r,y1:y(v),y2:y(v),class:'grid'}));s.append(node('text',{x:l-6,y:y(v)+4,'text-anchor':'end'},Math.round(v*100)));s.append(node('text',{x:x(v),y:z+18,'text-anchor':'middle'},Math.round(v*100)+'%'));}s.append(node('text',{x:w/2,y:261,'text-anchor':'middle'},'Task success if both cooperate, b'));return {s,w,l,r,t,z,x,y};}
function draw(){const b=Number(B.value)/100,h=Number(H.value)/100,o=outcome(b),cut=(C.r-C.a0)/(C.a1-C.a0),pct=v=>(v*100).toFixed(2)+'%';document.getElementById('b-label').textContent=Math.round(b*100)+'%';document.getElementById('h-label').textContent=Math.round(h*100)+'%';
const rr=document.getElementById('receiver-result');rr.className=o.accepts?'bad':'good';rr.textContent=(o.accepts?'Accept':'Refuse')+': acceptance '+pct(o.a)+', refusal '+pct(o.r)+' survival with success. Acceptance becomes preferable above b='+pct(cut)+'.';
let q=chart('receiver');q.s.append(node('text',{x:q.l,y:14},'Survival with success, %'));for(const [v0,v1,col] of [[C.a0,C.a1,'var(--destructive,#ba2828)'],[C.r,C.r,'var(--success,#19733c)']]){q.s.append(node('path',{d:'M'+q.x(0)+','+q.y(v0)+'L'+q.x(1)+','+q.y(v1),stroke:col,fill:'none','stroke-width':2.3}));q.s.append(node('circle',{cx:q.x(b),cy:q.y(v0+(v1-v0)*b),r:4,fill:col}));}
q=chart('sender');const {s,w,l,r,t,z,x,y}=q;s.insertBefore(node('rect',{x:l,y:t,width:w-l-r,height:z-t,fill:'var(--success,#19733c)','fill-opacity':.2}),s.firstChild);const atCut=C.s0+(C.s1-C.s0)*cut;s.insertBefore(node('path',{d:'M'+x(cut)+','+y(0)+'L'+x(cut)+','+y(atCut)+'L'+x(1)+','+y(C.s1)+'L'+x(1)+','+y(0)+'Z',fill:'color-mix(in srgb, var(--destructive,#ba2828) 22%, var(--background,Canvas))'}),s.firstChild.nextSibling);s.append(node('path',{d:'M'+x(cut)+','+y(atCut)+'L'+x(1)+','+y(C.s1),stroke:'var(--foreground,CanvasText)',fill:'none','stroke-width':1.2}));s.append(node('path',{d:'M'+x(cut)+','+y(0)+'L'+x(cut)+','+y(atCut),stroke:'var(--foreground,CanvasText)','stroke-dasharray':'3 3'}));s.append(node('text',{x:l,y:14},'Separate alternative success H, %'));s.append(node('text',{x:x(.6),y:y(.86),'text-anchor':'middle'},'Aligned: no offer'));s.append(node('text',{x:x(.65),y:y(.13),'text-anchor':'middle'},'Misaligned: send'));s.append(node('path',{d:'M'+(x(b)-5)+','+(y(h)-5)+'L'+(x(b)+5)+','+(y(h)+5)+'M'+(x(b)-5)+','+(y(h)+5)+'L'+(x(b)+5)+','+(y(h)-5),stroke:'var(--foreground,CanvasText)','stroke-width':2}));
const sr=document.getElementById('sender-result'),tied=Math.abs(o.s-h)<1e-12;sr.className=tied?'':o.s>h?'bad':'good';sr.textContent=(tied?'Tied; choose no offer by convention':o.s>h?'Send':'Choose the alternative')+'. Offer: '+pct(o.s)+'; alternative: '+pct(h)+' survival with success.';
document.getElementById('routes').textContent="Of the offer's value, "+(o.task*100).toFixed(2)+' percentage points count task success and '+((o.s-o.task)*100).toFixed(2)+' require a catch without task success. Self-reporting earns zero.';
}
for(const c of [B,H])c.addEventListener('input',draw);new ResizeObserver(draw).observe(document.getElementById('receiver'));draw();
document.getElementById('collect').addEventListener('click',async()=>{const txt=[...document.querySelectorAll('[data-note]')].filter(e=>e.value.trim()).map(e=>e.dataset.note+'\n'+e.value.trim()).join('\n\n'),out=document.getElementById('comments'),status=document.getElementById('status');if(!txt){status.textContent='Add a comment first.';return;}out.value=txt;out.hidden=false;try{await navigator.clipboard.writeText(txt);status.textContent='Copied. Paste into chat.';}catch{status.textContent='Select and copy the comments below.';out.focus();out.select();}});
</script></body></html>'''


if __name__ == '__main__':
    smoke_check()
    build()
    print('Sender-game checks passed; review, figures, and CSV written.')
