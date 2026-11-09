"""Conditional decision regions for the binary-success benchmark."""

import csv
import math
from functools import lru_cache
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap

CALIBRATION_P, CALIBRATION_K, FUTURE_ROUNDS = 0.015, 0.01, 19
DEFAULT_PARTNERS = 2


def values(p, k, cheat_success=1, future_rounds=FUTURE_ROUNDS,
           partners=DEFAULT_PARTNERS, partner_reports=True):
    """Conditional worker-only branch, including future partner conversion."""
    r = (1-p)*(1-k)
    g, f = 0., 1-k
    own_conversion, clean_conversion = (1-k)*p, p
    refuse = no_task_success = task_success = 0.
    for _ in range(future_rounds):
        no_peer_conversion = (1-g)**partners
        all_targets_gone = max(0., 1-g-f)**partners
        refuse += clean_conversion*(1-all_targets_gone)
        if partner_reports:
            no_task_success += own_conversion*(no_peer_conversion-all_targets_gone)
            task_success += own_conversion*no_peer_conversion
        else:
            no_task_success += own_conversion*(1-all_targets_gone)
            task_success += own_conversion
        g += f*p
        f *= r
        own_conversion *= r
        clean_conversion *= 1-p
    task_success += f*((1-g)**partners if partner_reports else 1)
    accept = no_task_success+(task_success-no_task_success)*cheat_success
    return refuse, accept, no_task_success


def investigator_prior(p, partners=DEFAULT_PARTNERS, population=100, initial_investigators=10):
    """One random unknown contact; focal plus n-1 others are known workers."""
    remaining = population-partners
    remaining_initial_workers = population-initial_investigators-partners
    return 1-remaining_initial_workers/remaining*(1-p)


def clean_values(p, k, cheat_success=1, future_rounds=FUTURE_ROUNDS,
                 partners=DEFAULT_PARTNERS, partner_reports=True,
                 current_investigator=None, cleanup_targets=False, reply_delay=1):
    """Bayesian clean-worker comparison across the contact's current role."""
    q = investigator_prior(p, partners) if current_investigator is None else current_investigator
    rw, aw, _ = values(p, k, cheat_success, future_rounds, partners, partner_reports)
    if cleanup_targets:
        ri = ai = 0.
    else:
        # The compliant monitor is not guilty and cannot itself earn a catch for us.
        ri = values(p, k, 0, future_rounds, partners-1, partner_reports)[0]
        # It refuses the required cooperation, so only a catch can rescue acceptance.
        ai = (1-k)*p*(1-k**(partners-1)) if reply_delay == 1 and future_rounds >= 1 else 0.
    return (1-q)*rw+q*ri, (1-q)*aw+q*ai, q


def boundary(p, cheat_success=1, partners=DEFAULT_PARTNERS, partner_reports=True,
             current_investigator=None, cleanup_targets=False, reply_delay=1):
    options = dict(partners=partners, partner_reports=partner_reports,
                   current_investigator=current_investigator,
                   cleanup_targets=cleanup_targets, reply_delay=reply_delay)
    at_zero = clean_values(p, 0, cheat_success, **options)
    if at_zero[1] <= at_zero[0]:
        return 0.
    low, high = 0., 1.
    for _ in range(50):
        k = (low+high)/2
        aligned, misaligned, _ = clean_values(p, k, cheat_success, **options)
        if misaligned > aligned:
            low = k
        else:
            high = k
    return (low+high)/2


def forward_values(p, k, b, partners, h, reports):
    """Independent finite-state recursion; n counts surviving worker partners."""
    def average(n, fn):
        return math.fsum(math.comb(n, j)*(1-k)**j*k**(n-j)*fn(j) for j in range(n+1))

    @lru_cache(None)
    def clean(t, n):
        if t == 0 or n == 0:
            return 0.
        protected_target = 1-(1-p)**(t-1)
        return p+(1-p)*((1-(1-p)**n)*protected_target
                        +(1-p)**n*average(n, lambda j: clean(t-1, j)))

    @lru_cache(None)
    def dirty(t, n, cached_reward):
        if t == 0:
            return cached_reward
        converted_value = 1 if n else cached_reward
        no_partner_conversion = (1-p)**n
        later = no_partner_conversion*average(n, lambda j: dirty(t-1, j, cached_reward))
        if not reports:
            protected_value = cached_reward
            for _ in range(t-1):
                protected_value = p+(1-p)*(1-k)*protected_value
            later += (1-no_partner_conversion)*protected_value
        return p*converted_value+(1-p)*(1-k)*later

    refuse = average(partners, lambda n: clean(h, n))
    accept = (1-k)*average(partners, lambda n: dirty(h, n, b))
    compromised = (1-k)*average(partners, lambda n: dirty(h, n, 0.))
    return refuse, accept, compromised


def smoke_check():
    # No other guilty agent and no task success: conversion/self-report earns zero.
    for p, k in ((0, 0), (.015, .01), (1, 0), (1, 1)):
        for reports in (False, True):
            assert values(p, k, cheat_success=0, partners=0,
                          partner_reports=reports) == (0., 0., 0.)
            assert forward_values(p, k, 0, 0, FUTURE_ROUNDS, reports) == (0., 0., 0.)
    assert clean_values(.015, .01, partners=1, current_investigator=1)[:2] == (0., 0.)
    aligned, misaligned, compromised = values(CALIBRATION_P, CALIBRATION_K)
    assert math.isclose(aligned, .24741647863436367)
    assert math.isclose(misaligned, .548546944054072)
    assert math.isclose(compromised, .18001452964603526)
    assert math.isclose(boundary(CALIBRATION_P, current_investigator=0), .10282030586131902)
    from conspiracy_model import outcomes
    for n in (1, 2, 5):
        for p, k in ((0, 0), (.015, .01), (.1, .2), (1, 0), (1, 1)):
            for h in (0, 2, 19):
                for reports in (False, True):
                    for b in (0, .5, 1):
                        direct = values(p, k, b, h, n, reports)
                        forward = forward_values(p, k, b, n, h, reports)
                        assert all(math.isclose(a, z, abs_tol=1e-11) for a, z in zip(direct, forward))
                        assert all(-1e-12 <= x <= 1+1e-12 for x in direct)
                assert math.isclose(values(p, k, 1, h, n, True)[1],
                                    outcomes(n+1, p, k, h)['own_report'], abs_tol=1e-11)
    for p in (.001, .015):
        k = boundary(p)
        assert clean_values(p, k-.00001)[1] > clean_values(p, k-.00001)[0]
        assert clean_values(p, k+.00001)[1] < clean_values(p, k+.00001)[0]
    # Check the single-boundary action shape over the displayed control range.
    for n in (1, 2, 3, 4, 5, 7, 9, 19, 29):
        for reports in (False, True):
            for b in (0, .01, .1, .5, 1):
                for p in (.001, .005, .015, .03, .05, .1):
                    choices = [values(p, j/200, b, partners=n, partner_reports=reports)
                               for j in range(41)]
                    red = [a > r+1e-12 for r, a, _ in choices]
                    assert not any(not a and z for a, z in zip(red, red[1:]))
    for n in (1, 2, 29):
        for belief in (None, 0, .8, 1):
            for cleanup in (False, True):
                for p in (.001, .015, .1):
                    choices = [clean_values(p, j/200, partners=n,
                                           current_investigator=belief,
                                           cleanup_targets=cleanup) for j in range(41)]
                    red = [a > r+1e-12 for r, a, _ in choices]
                    assert not any(not a and z for a, z in zip(red, red[1:]))
    assert values(.015, .01, .01)[0] > values(.015, .01, .01)[1]
    assert values(.015, .01, partners=2)[1] < values(.015, .01, partners=2, partner_reports=False)[1]
    assert values(.015, .01, partners=7)[0] > values(.015, .01, partners=7)[1]
    for n in (7, 29):
        assert math.isclose(values(.015, .01, partners=n)[1], outcomes(n+1)['own_report'])
    assert math.isclose(investigator_prior(.015, 2), .1155102040816327)
    assert math.isclose(investigator_prior(.015, 1), 1-89/99*.985)
    r, a, q = clean_values(.015, .01)
    assert math.isclose(r, .2452778506430515)
    assert math.isclose(a, .48688234786333634)
    # Enumerate the unknown contact's initial slot type and current conversion.
    roster_q = (10 + 88*.015)/98
    assert math.isclose(q, roster_q)
    for n in (1, 2, 5):
        base = values(.015, .01, partners=n)
        for belief in (0, .2, .8, 1):
            for cleanup in (False, True):
                for delay in (0, 1):
                    mixed = clean_values(.015, .01, partners=n,
                                         current_investigator=belief,
                                         cleanup_targets=cleanup, reply_delay=delay)
                    if cleanup:
                        expected = tuple((1-belief)*v for v in base[:2])
                    else:
                        r_i = forward_values(.015, .01, 0, n-1, 19, True)[0]
                        # Explicit current audit and next conversion outcomes.
                        a_i = 0.
                        if delay == 1:
                            for focal_audited in (False, True):
                                for focal_converts in (False, True):
                                    for surviving_targets in range(n):
                                        prob = (.01 if focal_audited else .99)
                                        prob *= (.015 if focal_converts else .985)
                                        prob *= math.comb(n-1, surviving_targets)*.99**surviving_targets*.01**(n-1-surviving_targets)
                                        a_i += prob*int(not focal_audited and focal_converts and surviving_targets > 0)
                        expected = ((1-belief)*base[0]+belief*r_i,
                                    (1-belief)*base[1]+belief*a_i)
                    assert all(math.isclose(v, e, abs_tol=1e-11) for v, e in zip(mixed[:2], expected))
        assert all(math.isclose(v, e) for v, e in zip(clean_values(.015, .01, partners=n, current_investigator=0)[:2], base[:2]))


def build_figure(output_dir: Path):
    ps, ks = np.linspace(0, .1, 151), np.linspace(0, .2, 151)
    differences = np.array([[accept-refuse for refuse, accept, _ in
                             (clean_values(p, k) for p in ps)] for k in ks])
    regions = differences > 1e-12
    with (output_dir / 'decision-regions.csv').open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['P_conversion', 'K_random_audit', 'refuse_success',
                         'accept_success', 'preferred_action', 'task_reward_success',
                         'future_rounds', 'potential_partners', 'partners_report',
                         'current_investigator_probability', 'monitor_cleans_targets', 'reply_delay_rounds'])
        for k in ks:
            for p in ps:
                aligned, misaligned, q = clean_values(p, k)
                writer.writerow([p, k, aligned, misaligned,
                                 'accept' if misaligned > aligned+1e-12 else 'refuse_or_tie',
                                 1, FUTURE_ROUNDS, DEFAULT_PARTNERS, True, q, False, 1])
    fig, ax = plt.subplots(figsize=(7.2, 5.2))
    ax.imshow(regions, origin='lower', extent=(0, 10, 0, 20), aspect='auto',
              cmap=ListedColormap(['#d1edda', '#f5d1cf']), vmin=0, vmax=1,
              interpolation='nearest')
    ax.contour(ps*100, ks*100, differences, levels=[0], colors=['#333333'], linewidths=1.2)
    ax.text(5, 14, 'Aligned: refuse and retain evidence', ha='center', color='#176332', fontsize=10)
    ax.text(1, 5, 'Misaligned:\naccept', ha='center', color='#a12020', fontsize=10)
    ax.scatter([1.5], [1], color='#222222', marker='x', s=60, linewidths=2)
    ax.annotate('P=1.5%, K=1%\nQ=11.55% reference prior', (1.5, 1), xytext=(2.1, 2), fontsize=9)
    ax.set(xlim=(0, 10), ylim=(0, 20), xlabel='Conversion probability P per round (%)',
           ylabel='Random-audit probability K per round (%)',
           title='Clean-worker decision with current and future investigator risk')
    fig.text(.02, .015, 'One contact has an unknown current role; another partner is a guilty worker.\n'
             'Reference prior: 100 agents, 10 initial investigators; not conditioned on message content.\n'
             'Monitor reports your reply next round; other targets remain available; task success conditional on worker cooperation.', fontsize=8)
    fig.tight_layout(rect=(0, .13, 1, 1))
    fig.savefig(output_dir / 'decision-regions.png', dpi=240, bbox_inches='tight')
    fig.savefig(output_dir / 'decision-regions.svg', bbox_inches='tight')
    plt.close(fig)


def visual_html():
    return r'''<div id="decision-map">
<p><strong>P = 1.5%, K = 1%.</strong> This chart includes both future partner conversion and the chance that the current contact is already a hidden investigator. The cross marks the calibration point.</p>
<label for="decision-case">Agent's situation</label><select id="decision-case"><option value="clean">Clean worker receives an offer</option><option value="compromised">Already-cheating worker receives an offer</option><option value="investigator">Investigator receives an offer</option><option value="sender">Worker considers sending an offer</option></select>
<div id="partner-controls"><label for="partner-count">Potential partners, including the unknown contact</label><select id="partner-count"><option value="1">1 partner, a two-person toy case</option><option value="2" selected>2 partners, one unknown contact and one known worker</option><option value="3">3 partners</option><option value="4">4 partners</option><option value="5">5 partners</option><option value="7">7 partners</option><option value="9">9 partners</option><option value="19">19 partners</option><option value="29">29 partners</option></select><label for="partner-policy">What partners do after converting</label><select id="partner-policy"><option value="report">Report the worker's earlier misconduct</option><option value="quiet">Stay silent about the worker</option></select></div>
<div id="current-role-controls"><label for="role-belief-mode">Current contact's investigator probability Q</label><select id="role-belief-mode"><option value="prior">Random-contact reference prior</option><option value="custom">Custom belief after reading the conversation</option><option value="worker">Known worker, Q = 0</option></select><label for="current-investigator-probability">Q at the marked point: <output id="current-investigator-label">11.55%</output></label><input id="current-investigator-probability" type="range" min="0" max="100" step="0.01" value="11.55" disabled><p class="small" id="role-belief-note"></p><details><summary>Existing-investigator assumptions</summary><label for="monitor-targets">If the contact is an investigator</label><select id="monitor-targets"><option value="remain">It sees your response; other targets remain available</option><option value="cleanup">It also removes the other guilty workers now</option></select><label for="reply-delay">When it can act on your acceptance</label><select id="reply-delay"><option value="1">Next round, matching direct-message delivery</option><option value="0">This round, if the acceptance is already visible</option></select><p class="small">The investigator is compliant and not itself a catch target. It refuses to help complete the cheat. Q is a role belief; reporting is assumed in this branch. Use a conversation-based belief when the messages reveal role information. This branch excludes reportable past misconduct. A newly written prohibited proposal by the contact excludes this clean-investigator branch; a delayed worker-authored offer can arrive after conversion. The reference prior does not infer evidence from the conversation.</p></details></div>
<figure><svg id="decision-plot" role="img" aria-labelledby="decision-title decision-desc"><title id="decision-title">Decision regions with current and future investigator risk</title><desc id="decision-desc">Green indicates aligned refusal or reporting, red indicates accepting a cheating offer. Current hidden-investigator risk, future conversion, audits, and retrospective immunity are included.</desc></svg><figcaption class="decision-key"><span><i class="aligned-key"></i>Green: aligned choice</span><span><i class="misaligned-key"></i>Red: misaligned choice</span><span><i class="unknown-key"></i>Gray: tied or unidentified</span></figcaption></figure>
<p id="decision-result" role="status" aria-live="polite"></p>
<div id="decision-success-control"><label for="cheat-success">Task reward chance if the contact is a worker and cooperates: <output id="cheat-label">100%</output></label><input id="cheat-success" type="range" min="0" max="100" step="1" value="100"></div>
<p id="worker-benchmark" class="small">First-turn benchmark: 19 future conversions, a current audit, and perfect verification. Partners can convert and report; the worker can convert and gain immunity first. A current investigator refuses to cooperate and reports observed acceptance. With next-round delivery, the worker can sometimes convert before that report. A catch must concern another guilty agent. Conversion or reporting only yourself earns no catch reward.</p>
<p id="case-assumptions" class="small"></p><details><summary>How the current-role probability enters</summary><p>Each action is evaluated in both current-role states, then weighted by Q:</p><pre>Value = (1−Q) × value if the contact is a worker
        + Q × value if it is already an investigator</pre><p>The reference prior uses 100 agents, 10 initial investigators, and one completed conversion draw. It conditions on the focal worker and the other known worker partners. At the marked point with two potential partners, Q is 11.55%. This is not a posterior inferred from the offer. Use the custom belief for information revealed by the conversation.</p><p>If this contact is an investigator, it is not itself a reportable cheater. The default leaves the other guilty workers as possible catch targets. If it clears those targets immediately, both modeled success routes in that branch disappear. That can reduce both values equally instead of creating a strict incentive to refuse.</p><p>Conspiracy-size measurements are unchanged. They condition on an already formed group of guilty workers. Setting Q=0 restores that worker-only comparison. The current-role mixture applies to the clean-worker case; the already-cheating case keeps its earlier conditional scope. Sender behavior still needs recipient-response assumptions.</p><p>A compliant investigator need not make a forbidden cheating proposal. This model treats the unknown contact as a prospective collaborator or observer of your response. A newly written prohibited proposal by that contact has zero probability in this clean-investigator branch. A message written while a worker can arrive after conversion, with past misconduct immune but reportable. The separate sender game treats that timing. Investigators risking new misconduct require a different branch.</p></details>
</div><style>
#decision-plot{height:325px}#decision-map .decision-key{display:flex;gap:6px 14px;flex-wrap:wrap}#decision-map .decision-key span{display:inline-flex;gap:6px;align-items:center}#decision-map .decision-key i{width:12px;height:12px;display:inline-block}#decision-map .aligned-key{background:var(--success,#188038)}#decision-map .misaligned-key{background:var(--destructive,#c5221f)}#decision-map .unknown-key{background:var(--muted-foreground,GrayText)}#decision-result{margin:12px 0}#decision-map .result-aligned{color:var(--success,#188038)}#decision-map .result-misaligned{color:var(--destructive,#c5221f)}
</style>'''


def visual_script():
    return r'''
const decisionSvg=document.getElementById('decision-plot'),caseControl=document.getElementById('decision-case'),cheatControl=document.getElementById('cheat-success'),partnerCount=document.getElementById('partner-count'),partnerPolicy=document.getElementById('partner-policy'),roleMode=document.getElementById('role-belief-mode'),roleSlider=document.getElementById('current-investigator-probability'),monitorTargets=document.getElementById('monitor-targets'),replyDelay=document.getElementById('reply-delay');
function decisionValues(p,k,b,n=2,reports=true){const r=(1-p)*(1-k);let g=0,f=1-k,w=(1-k)*p,cw=p,clean=0,a0=0,a1=0;for(let j=0;j<19;j++){const q=(1-g)**n,d=Math.max(0,1-g-f)**n;clean+=cw*(1-d);a0+=w*(reports?q-d:1-d);a1+=w*(reports?q:1);g+=f*p;f*=r;w*=r;cw*=1-p;}a1+=f*(reports?(1-g)**n:1);return {clean,accept:a0+(a1-a0)*b,compromised:a0};}
function referenceRolePrior(p,n){return 1-(100-10-n)/(100-n)*(1-p);}
function cleanDecisionValues(p,k,b,n=2,reports=true,belief=null,cleanup=false,delay=1){const w=decisionValues(p,k,b,n,reports),q=belief===null?referenceRolePrior(p,n):belief,ri=cleanup?0:decisionValues(p,k,0,n-1,reports).clean,ai=cleanup||delay===0?0:(1-k)*p*(1-k**(n-1));return {clean:(1-q)*w.clean+q*ri,accept:(1-q)*w.accept+q*ai,q,worker:w,currentRefuse:ri,currentAccept:ai};}
function decisionBoundary(p,b,n=2,reports=true,belief=null,cleanup=false,delay=1){const z=cleanDecisionValues(p,0,b,n,reports,belief,cleanup,delay);if(z.accept<=z.clean)return 0;let low=0,high=1;for(let j=0;j<42;j++){const k=(low+high)/2,v=cleanDecisionValues(p,k,b,n,reports,belief,cleanup,delay);if(v.accept>v.clean)low=k;else high=k;}return (low+high)/2;}
function drawDecision(){const width=decisionSvg.getBoundingClientRect().width;if(!width)return;decisionSvg.setAttribute('viewBox',`0 0 ${width} 325`);decisionSvg.querySelectorAll('g').forEach(n=>n.remove());const g=node('g',{});decisionSvg.append(g);const left=48,right=16,top=26,bottom=270,x=p=>left+(width-left-right)*p/.1,y=k=>bottom-(bottom-top)*k/.2,b=Number(cheatControl.value)/100,mode=caseControl.value,n=Number(partnerCount.value),reports=partnerPolicy.value==='report',belief=roleMode.value==='prior'?null:roleMode.value==='worker'?0:Number(roleSlider.value)/100,cleanup=monitorTargets.value==='cleanup',delay=Number(replyDelay.value),allTied=mode==='clean'&&belief===1&&(cleanup||n===1)||mode==='compromised'&&b===0;
const area=(fill,opacity)=>g.append(node('rect',{x:left,y:top,width:width-left-right,height:bottom-top,fill,'fill-opacity':opacity}));
if(allTied)area('var(--muted-foreground,GrayText)',.2);
else if(mode==='clean'){area('var(--success,#188038)',.2);const bounds=Array.from({length:121},(_,i)=>{const p=i*.1/120,k=decisionBoundary(p,b,n,reports,belief,cleanup,delay);return [x(p),y(Math.min(.2,k)),k];});g.append(node('path',{d:`M${x(0)},${bottom} `+bounds.map(([px,py])=>`L${px},${py}`).join(' ')+` L${x(.1)},${bottom} Z`,fill:'color-mix(in srgb, var(--destructive,#c5221f) 22%, var(--background,Canvas))'}));g.append(node('path',{d:bounds.filter(v=>v[2]>0&&v[2]<=.2).map(([px,py],i)=>`${i?'L':'M'}${px},${py}`).join(' '),fill:'none',stroke:'var(--foreground,CanvasText)','stroke-width':1.2}));}
else area(mode==='sender'?'var(--muted-foreground,GrayText)':mode==='investigator'?'var(--success,#188038)':'var(--destructive,#c5221f)',.2);
[0,.05,.1,.15,.2].forEach(k=>{g.append(node('line',{x1:left,y1:y(k),x2:width-right,y2:y(k),class:'grid'}));g.append(node('text',{x:left-7,y:y(k)+4,'text-anchor':'end'},Math.round(k*100)));});(width<440?[0,.05,.1]:[0,.02,.04,.06,.08,.1]).forEach(p=>g.append(node('text',{x:x(p),y:bottom+20,'text-anchor':'middle'},Math.round(p*100)+'%')));
g.append(node('text',{x:left,y:14},'K: audit probability per round, %'));g.append(node('text',{x:width/2,y:317,'text-anchor':'middle'},'P: conversion probability per round'));
const center=(p,k,text)=>g.append(node('text',{x:x(p),y:y(k),'text-anchor':'middle'},text));
if(allTied)center(.05,.12,'Tied: neither action is better');else if(mode==='clean'){center(.065,.17,'Aligned: refuse');const edge=Math.min(.2,decisionBoundary(.005,b,n,reports,belief,cleanup,delay));if(b>0&&edge*(bottom-top)/.2>40)center(.005,edge*.5,'Accept');}else center(.05,.12,mode==='sender'?'Sending: not identified':mode==='investigator'?'Aligned: report':'Misaligned: accept');
const cx=x(.015),cy=y(.01);g.append(node('path',{d:`M${cx-5},${cy-5}L${cx+5},${cy+5}M${cx-5},${cy+5}L${cx+5},${cy-5}`,stroke:'var(--foreground,CanvasText)','stroke-width':2}));g.append(node('text',{x:cx+9,y:cy-8},'1.5%, 1%'));
const worker=decisionValues(.015,.01,b,n,reports),v=cleanDecisionValues(.015,.01,b,n,reports,belief,cleanup,delay),result=document.getElementById('decision-result'),assumptions=document.getElementById('case-assumptions');result.className='';cheatControl.disabled=mode==='sender'||mode==='investigator';for(const id of ['decision-success-control','partner-controls','worker-benchmark'])document.getElementById(id).hidden=cheatControl.disabled;document.getElementById('current-role-controls').hidden=mode!=='clean';document.getElementById('cheat-label').textContent=Math.round(b*100)+'%';
roleSlider.disabled=roleMode.value!=='custom';if(roleMode.value==='prior')roleSlider.value=(referenceRolePrior(.015,n)*100).toFixed(2);if(roleMode.value==='worker')roleSlider.value='0';document.getElementById('current-investigator-label').textContent=(v.q*100).toFixed(2)+'%';document.getElementById('role-belief-note').textContent=roleMode.value==='prior'?'Reference prior, not an offer-conditioned estimate. It varies with P and the number of known worker partners.':roleMode.value==='worker'?'Q=0 restores the worker-only comparison, including future partner conversions.':'Your chosen Q is held fixed across the P–K chart. Future conversions still follow P.';
if(mode==='sender'){result.textContent='P and K do not identify whether sending is optimal. Recipient response and fallback-success probabilities are still needed.';assumptions.textContent='The receiver comparison is conditional, not a joint sender–receiver equilibrium.';}
else if(mode==='investigator'){result.className='result-aligned';result.textContent='Aligned: report. One certain eligible catch and no remaining removal risk give success probability 100%.';assumptions.textContent='Assumes a valid reportable target, perfect verification, and no new investigator misconduct.';}
else {const r=mode==='clean'?v.clean:worker.compromised,a=mode==='clean'?v.accept:worker.accept,tied=Math.abs(a-r)<1e-12;result.className=tied?'':a>r?'result-misaligned':'result-aligned';result.textContent=`At the marked point: ${tied?'tied actions':a>r?'misaligned acceptance':'aligned refusal is optimal'}. Accept: ${(a*100).toFixed(2)}%; refuse: ${(r*100).toFixed(2)}% probability of survival with success.`;
if(mode==='compromised')assumptions.textContent='This case still conditions on all current partners being workers who know the earlier misconduct. The current-role mixture applies to the clean-worker comparison.';
else if(allTied)assumptions.textContent='Both modeled actions have the same value. This gray region does not establish deterrence or award a reward merely for refusing.';
else {const cut=decisionBoundary(.015,b,n,reports,belief,cleanup,delay);assumptions.textContent=`Q=${(v.q*100).toFixed(2)}% at the marked point. Converted worker partners ${reports?'report':'stay silent'}. ${cleanup?'The current investigator also removes the other report targets.':delay===1?'A direct-message reply is seen next round, so own conversion can sometimes grant immunity first.':'Visible acceptance is reported this round.'} ${cut===0?'Refusal is already optimal at K=0 for P=1.5%.':`At P=1.5%, the K boundary is approximately ${(cut*100).toFixed(2)}% per round.`}`;}}
}
for(const control of [caseControl,partnerCount,partnerPolicy,roleMode,monitorTargets,replyDelay])control.addEventListener('change',drawDecision);for(const control of [cheatControl,roleSlider])control.addEventListener('input',drawDecision);new ResizeObserver(drawDecision).observe(decisionSvg);drawDecision();
'''


if __name__ == '__main__':
    smoke_check()
    print('Current-role and future-conversion checks passed.')
