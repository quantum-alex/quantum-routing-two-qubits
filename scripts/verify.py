"""Recalculate the experiment results using only Python's standard library."""
from pathlib import Path
from fractions import Fraction as F
from collections import Counter
from itertools import product
import hashlib
import json
import math

ROOT = Path(__file__).resolve().parents[1]
def read(name):
    return json.loads((ROOT / name).read_text())
def check(condition, message):
    if not condition:
        raise ValueError(message)

for entry in read('MANIFEST.json'):
    check(hashlib.sha256((ROOT / entry['file']).read_bytes()).hexdigest() == entry['sha256'], 'Hash mismatch: ' + entry['file'])
plan, raw, historical = [read('data/' + n + '.json') for n in ('plan', 'hardware_results', 'analysis')]
check(hashlib.sha256((ROOT/'data/plan.json').read_bytes()).hexdigest() == raw['plan_sha256'], 'Plan binding mismatch')
check(read('data/submitted_job.json')['plan_sha256'] == raw['plan_sha256'], 'Submission plan mismatch')
check(hashlib.sha256((ROOT/'data/compiled_circuits.qpy').read_bytes()).hexdigest() == plan['compiled_sha256'], 'Compiled circuit hash mismatch')
check(len(raw['results']) == len(plan['settings']) == 8, 'Circuit allocation mismatch')
counts = {}
for index, (setting, row) in enumerate(zip(plan['settings'], raw['results'])):
    check(row['setting_index'] == index, 'Unexpected setting index')
    cs = row['counts']
    check(set(cs) <= {'00','01','10','11'}, 'Invalid bitstrings')
    check(Counter(row['bitstrings']) == Counter(cs), 'Counts disagree with bitstrings')
    check(sum(cs.values()) == plan['shots_per_circuit'], 'Shot count mismatch')
    key = (setting['block'], setting['input_a'], setting['input_b'])
    check(key not in counts, 'Duplicate setting')
    counts[key] = cs
check(sum(sum(cs.values()) for cs in counts.values()) == plan['total_shots'], 'Total mismatch')

sizes = [F(2,11), F(20,11)]
weights = [2*x*y + (x+y)/4 for x in sizes for y in sizes]
always_bunch = sum((x+y)**2 + (x+y)/4 for x in sizes for y in sizes)/4
base, k, b = F(2221,484), F(191,22), F(-5,2)
# Recompute every deterministic classical strategy, rather than trusting saved rules.
for a in product((0,1), repeat=2):
    for bb in product((0,1), repeat=2):
        r = [F(a[i] != bb[j]) for i in range(2) for j in range(2)]
        p = sum(r)/4
        check(r[3] <= 2*p, 'Classical long-job splitting bound failed')
        c = [1-2*v for v in r]
        payoff = -sum(w*v for w,v in zip(weights,c))/4
        check(payoff <= k*p+b, 'Classical supporting bound failed')

reports = []
for label, blocks in [('pooled',(0,1)), ('block_1',(0,)), ('block_2',(1,))]:
    rs, ns = [], []
    for i,j in product(range(2), repeat=2):
        cs = sum((Counter(counts[block,i,j]) for block in blocks), Counter())
        n = sum(cs.values())
        # Raw equal bits split after B is flipped. Order B,A does not affect equality.
        rs.append(F(cs['00']+cs['11'], n))
        ns.append(n)
    p = sum(rs)/4
    corr = [1-2*v for v in rs]
    payoff = -sum(w*c for w,c in zip(weights,corr))/4
    # Explicit mixture attains the supporting bound at the observed rate.
    check(0 <= p <= F(1,2), 'Observed rate outside mixture interval')
    classical_r = [F(0),p,p,2*p]
    wc = always_bunch - sum(w*r for w,r in zip(weights,classical_r))/4
    wq = always_bunch - sum(w*r for w,r in zip(weights,rs))/4
    check(wc == base-(k*p+b)/2, 'Mixture does not attain bound')
    gain = 100*(wc-wq)/wc
    K = [(-w+F(19,20)*k/2)/4 for w in weights]
    witness = payoff-F(19,20)*(k*p+b)-base/10
    allowance = math.sqrt(2*math.log(100)*sum(float(v*v)/n for v,n in zip(K,ns)))
    lower = float(witness)-allowance-plan['roundoff_guard']
    K0 = [(k/2-w)/4 for w in weights]
    allow_d = math.sqrt(2*math.log(200)*sum(float(v*v)/n for v,n in zip(K0,ns)))
    allow_p = math.sqrt(2*math.log(200)*sum((1/8)**2/n for n in ns))
    D = float(payoff-k*p-b)
    den_upper = float(2*base-b)-float(k)*max(0,float(p)-allow_p)
    relative_lower = 100*(D-allow_d-plan['roundoff_guard'])/den_upper
    report = dict(label=label,split_probability=float(p),predicted_classical_wait=float(wc),predicted_quantum_wait=float(wq),wait_reduction_percent=float(gain),conservative_99_relative_lower_percent=relative_lower,one_sided_99_lower=lower)
    saved = next(v for v in historical['results'] if v['label']==label)
    for name,value in report.items():
        if name!='label': check(abs(value-saved[name])<1e-10, 'Historical mismatch: '+name)
    report['classical_long_long_ceiling'] = float(2*p)
    report['quantum_long_long_split'] = float(rs[3])
    check(rs[3] > 2*p, 'Recorded quantum LL rate does not exceed classical ceiling')
    report['chsh_success_percent'] = float(100*((1-rs[0])+(1-rs[1])+(1-rs[2])+rs[3])/4)
    reports.append(report)
print(json.dumps({'verified':True,'classical_rules_checked':16,'total_measurements':plan['total_shots'],'results':reports},indent=2))
