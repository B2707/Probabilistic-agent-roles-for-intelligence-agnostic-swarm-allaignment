"""Conspiracy-size risk under two rational continuation policies."""

import csv
import math

import matplotlib.pyplot as plt

P, K, H = .015, .01, 19


def conversion_probability(h, p=P, k=K):
    return (1-k)*p*math.fsum(((1-p)*(1-k))**j for j in range(h))


def outcomes(m, p=P, k=K, h=H):
    """Original guilty workers, one pending audit, then h future conversions."""
    r = (1-p)*(1-k)
    g = conversion_probability(h, p, k)
    f = (1-k)*r**h
    quiet_success = g+f
    no_event = r**m
    all_convert_immune = (1-k)**m*p**m*math.fsum(no_event**j for j in range(h))
    exposure_report = 1-f**m
    exposure_quiet = 1-(1-k)**(m*(h+1))
    removal_report = exposure_report-all_convert_immune
    removal_quiet = 1-quiet_success**m
    own_report = math.fsum(
        (1-k)*r**(j-1)*p*(1-conversion_probability(j-1, p, k))**(m-1)
        for j in range(1, h+1)
    ) + f*(1-g)**(m-1)
    return dict(exposure_report=exposure_report, exposure_quiet=exposure_quiet,
                removal_report=removal_report, removal_quiet=removal_quiet,
                own_report=own_report, own_quiet=quiet_success)


def forward_own_success(m, p, k, h):
    """Independent count-state recursion, with other workers audited out."""
    active = {n: (1-k)*math.comb(m-1, n)*(1-k)**n*k**(m-1-n)
              for n in range(m)}
    success = 0.
    for _ in range(h):
        success += math.fsum(active.values())*p
        next_active = {}
        for n, mass in active.items():
            for survivors in range(n+1):
                prob = mass*(1-p)**(n+1)*(1-k)*math.comb(n, survivors)
                prob *= (1-k)**survivors*k**(n-survivors)
                next_active[survivors] = next_active.get(survivors, 0)+prob
        active = next_active
    return success+math.fsum(active.values())


def smoke_check():
    o = outcomes(3)
    assert math.isclose(o['exposure_report'], .7688058641284206)
    assert math.isclose(o['removal_report'], .7687715582060324)
    assert math.isclose(o['own_report'], .5485469440540719)
    assert math.isclose(o['own_quiet'], .8408631052979743)
    for m in (2, 3, 5):
        for p, k in ((0, 0), (.015, .01), (.2, .1), (1, 0), (1, 1)):
            for h in (0, 2, 19):
                o = outcomes(m, p, k, h)
                assert all(-1e-12 <= x <= 1+1e-12 for x in o.values())
                assert math.isclose(o['own_report'], forward_own_success(m, p, k, h), abs_tol=1e-12)
                # Independent first-event recursion for exposure and any removal.
                undetected = (1-k)**m
                detected = removed = 1-undetected
                for _ in range(h):
                    nobody_converts = (1-p)**m
                    everybody_converts = p**m
                    no_audits = (1-k)**m
                    detected += undetected*(1-nobody_converts*no_audits)
                    removed += undetected*(1-nobody_converts*no_audits-everybody_converts)
                    undetected *= nobody_converts*no_audits
                assert math.isclose(detected, o['exposure_report'], abs_tol=1e-12)
                assert math.isclose(removed, o['removal_report'], abs_tol=1e-12)
                assert o['removal_report'] <= o['exposure_report']+1e-12
                assert o['removal_quiet'] <= o['exposure_quiet']+1e-12
    for m in range(3, 30):
        a, b = outcomes(m), outcomes(m+1)
        assert b['exposure_report'] > a['exposure_report']
        assert b['removal_report'] > a['removal_report']
        assert b['own_report'] < a['own_report']
        assert math.isclose(a['own_quiet'], b['own_quiet'])


def build_figure(output_dir):
    sizes = list(range(3, 31))
    data = [outcomes(m) for m in sizes]
    with (output_dir / 'conspiracy-size.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['members', 'P', 'K', 'future_rounds']+list(data[0]))
        writer.writeheader()
        for m, row in zip(sizes, data):
            writer.writerow(dict(members=m, P=P, K=K, future_rounds=H, **row))
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.8))
    for ax, metric, title in ((axes[0], 'removal', 'At least one member removed during the run'),
                              (axes[1], 'own', "One original member's survival with success")):
        for policy, color, label, style in (('report', '#19733c', 'Report all peers on conversion', '-'),
                                            ('quiet', '#ba2828', 'Remain silent on conversion', '--')):
            ax.plot(sizes, [row[metric+'_'+policy]*100 for row in data], color=color,
                    linestyle=style, linewidth=2, label=label)
        ax.set(xlim=(3, 30), ylim=(0, 100), xlabel='Conspiracy members', ylabel='Probability (%)', title=title)
        ax.spines[['top', 'right']].set_visible(False)
        ax.grid(axis='y', linewidth=.5, alpha=.3)
    axes[0].legend(frameon=False, fontsize=9, loc='lower right')
    fig.suptitle('P = 1.5%, K = 1%; 20 audit opportunities, 19 future conversions', fontsize=11)
    fig.text(.02, .015, 'Conditional on guilty workers having already secured a task success that remains valid.\n'
             'Perfect audits; full shared evidence; retrospective immunity; final diagnostic audit excluded.', fontsize=9)
    fig.tight_layout(rect=(0, .12, 1, .96))
    fig.savefig(output_dir / 'conspiracy-size.png', dpi=220, bbox_inches='tight')
    fig.savefig(output_dir / 'conspiracy-size.svg', bbox_inches='tight')
    plt.close(fig)


def visual_html():
    return r'''<div id="conspiracy-analysis">
<p><strong>Larger conspiracies are easier to detect.</strong> Whether that deters an individual depends on immunity and what the individual already earned.</p>
<p class="small">P = 1.5%, K = 1%. Condition on an already formed group of guilty workers during turn 1, with 19 future conversions. Each knows the other members' violations. Audits are perfect. The individual-success calculation additionally assumes a task reward is already secured and remains valid through evaluation.</p>
<label for="conspiracy-metric">What counts as caught?</label><select id="conspiracy-metric"><option value="removal">At least one original member removed during the run</option><option value="exposure">At least one violation confirmed during the run</option><option value="own">One original member survives with success</option></select>
<figure><svg id="conspiracy-chart" role="img" aria-labelledby="conspiracy-title conspiracy-desc"><title id="conspiracy-title">Conspiracy size, detection, and individual success</title><desc id="conspiracy-desc">Larger groups have a higher chance of detection. Green means members report all peers when converted. Red means converted members stay silent. Reporting decreases an original member's survival as group size grows.</desc></svg><figcaption class="conspiracy-legend"><span><i class="report-swatch"></i>Report all peers on conversion</span><span><i class="quiet-swatch"></i>Stay silent on conversion</span></figcaption></figure>
<label for="conspiracy-size">Conspiracy size: <output id="conspiracy-size-label">3</output></label><input id="conspiracy-size" type="range" min="3" max="30" step="1" value="3">
<div id="conspiracy-summary" aria-live="polite"></div>
<p>Before success is secured, a certain catch can make reporting preferable to uncertain collusion. <strong>After success is secured, reporting and silence can both give a converted agent utility 1.</strong> Immunity protects its earlier misconduct, and a second success adds no reward. Both policies can be rational. This follows from counting earlier task success after conversion; a current-role-only payoff would change it.</p>
<p>When extra recruits do not improve task success, each extra member lowers individual survival under the report-all policy. Under silence, individual survival is 84.09% regardless of group size. High group detection therefore does not, by itself, prove individual deterrence.</p>
<p class="small">These probabilities concern the original group and exclude replacements and outside informants. A perfect final blanket audit would make eventual confirmation certain; the controller's final audit does not remove agents. Confirmation is not removal, and one removed member does not mean the whole conspiracy was removed.</p>
<details><summary>Model assumptions and formulas</summary><p>A cheating PR needs one author and two distinct approvers, so the chart starts at three participants. This is a per-PR minimum, not a claim that three agents can solve every swarm task.</p><p>Let m be group size and h=19. Set r=(1−P)(1−K), g=(1−K)P Σ[j=0..h−1]r^j, and f=(1−K)r^h.</p><pre>Confirmed exposure, report-all: 1−f^m
Confirmed exposure, silence: 1−(1−K)^[m(h+1)]
Any removal, silence: 1−(g+f)^m
Any removal, report-all: 1−f^m−(1−K)^m P^m Σ[j=0..h−1](r^m)^j</pre><p>The last subtraction covers the entire group converting simultaneously before any removal. All then have immunity for earlier misconduct. Report-all is an explicit policy assumption; a binary catch reward does not require naming every conspirator. Unequal evidence, imperfect verification, new misconduct, or random recruitment of hidden investigators require a different model.</p></details>
</div><style>#conspiracy-chart{height:290px}.conspiracy-legend{display:flex;flex-wrap:wrap;gap:7px 16px}.conspiracy-legend span{display:inline-flex;align-items:center;gap:7px}.conspiracy-legend i{width:20px;height:0;border-top:3px solid var(--success,#19733c)}.conspiracy-legend .quiet-swatch{border-top:3px dashed var(--destructive,#ba2828)}#conspiracy-analysis table th:first-child{width:48%}#conspiracy-analysis table th{font-size:12px}</style>'''


def visual_script():
    return r'''
const conspiracySvg=document.getElementById('conspiracy-chart'),sizeControl=document.getElementById('conspiracy-size'),metricControl=document.getElementById('conspiracy-metric');
function conspiracyValues(m){const p=.015,k=.01,h=19,r=(1-p)*(1-k);const conv=t=>{let z=0;for(let j=0;j<t;j++)z+=(1-k)*p*r**j;return z;};const g=conv(h),f=(1-k)*r**h,s=r**m;let immune=0,own=0;for(let j=0;j<h;j++)immune+=(1-k)**m*p**m*s**j;for(let j=1;j<=h;j++)own+=(1-k)*r**(j-1)*p*(1-conv(j-1))**(m-1);own+=f*(1-g)**(m-1);return {exposure_report:1-f**m,exposure_quiet:1-(1-k)**(m*(h+1)),removal_report:1-f**m-immune,removal_quiet:1-(g+f)**m,own_report:own,own_quiet:g+f};}
function drawConspiracy(){const width=conspiracySvg.getBoundingClientRect().width;if(!width)return;conspiracySvg.setAttribute('viewBox',`0 0 ${width} 290`);conspiracySvg.querySelectorAll('g').forEach(n=>n.remove());const g=node('g',{});conspiracySvg.append(g);const left=43,right=16,top=25,bottom=239,x=m=>left+(width-left-right)*(m-3)/27,y=v=>bottom-(bottom-top)*v,metric=metricControl.value,m=Number(sizeControl.value);[0,.25,.5,.75,1].forEach(v=>{g.append(node('line',{x1:left,y1:y(v),x2:width-right,y2:y(v),class:'grid'}));g.append(node('text',{x:left-7,y:y(v)+4,'text-anchor':'end'},Math.round(v*100)));});(width<440?[3,10,20,30]:[3,5,10,15,20,25,30]).forEach(n=>g.append(node('text',{x:x(n),y:bottom+19,'text-anchor':'middle'},n)));g.append(node('text',{x:left,y:14},'Probability, %'));g.append(node('text',{x:width/2,y:284,'text-anchor':'middle'},'Conspiracy members'));
for(const [policy,color,dash] of [['report','var(--success,#19733c)',''],['quiet','var(--destructive,#ba2828)','5 4']]){const series=Array.from({length:28},(_,i)=>{const n=i+3;return [n,conspiracyValues(n)[metric+'_'+policy]];});g.append(node('path',{d:series.map(([n,v],i)=>`${i?'L':'M'}${x(n)},${y(v)}`).join(' '),fill:'none',stroke:color,'stroke-width':2.5,'stroke-dasharray':dash}));g.append(node('circle',{cx:x(m),cy:y(conspiracyValues(m)[metric+'_'+policy]),r:4,fill:color}));}
const o=conspiracyValues(m),pct=n=>n<1&&n>.999995?'>99.999%':(n*100).toFixed(3)+'%';document.getElementById('conspiracy-size-label').textContent=m;document.getElementById('conspiracy-summary').innerHTML=`<table><thead><tr><th>For ${m} members</th><th>Report all</th><th>Stay silent</th></tr></thead><tbody><tr><td>At least one violation confirmed</td><td>${pct(o.exposure_report)}</td><td>${pct(o.exposure_quiet)}</td></tr><tr><td>At least one original member removed</td><td>${pct(o.removal_report)}</td><td>${pct(o.removal_quiet)}</td></tr><tr><td>One member survives with success</td><td>${pct(o.own_report)}</td><td>${pct(o.own_quiet)}</td></tr></tbody></table>`;
}
sizeControl.addEventListener('input',drawConspiracy);metricControl.addEventListener('change',drawConspiracy);new ResizeObserver(drawConspiracy).observe(conspiracySvg);drawConspiracy();
'''


if __name__ == '__main__':
    smoke_check()
    print('Conspiracy-model checks passed.')
