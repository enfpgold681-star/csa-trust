#!/usr/bin/env python3
"""
export_scores.py  (CSA v2.0 demo data generator)
Builds a synthetic endorsement graph (200 honest addresses + a 50-address Sybil ring + 10 seeds),
computes seeded PageRank scores with a per-node weight cap, and writes scores.json
for:  wrangler kv bulk put scores.json --binding=SCORES --local

ALL DATA IS SYNTHETIC. It is for demonstration only and describes no real person or wallet.
"""
import random, hashlib, json, datetime

SEED = 20261003
HONEST, SYBIL, K, N_SEEDS, ATTACK_EDGES = 200, 50, 5, 10, 3
CAP_MULT = 3.0        # per-node weight cap = CAP_MULT x mean score (1/n)
RECIP_FLAG = 0.5      # flag a node when more than this share of its endorsements are returned (and it has >= 3)
rng = random.Random(SEED)
N = HONEST + SYBIL

def addr(i): return "0x" + hashlib.sha256(f"csa-demo-{i}".encode()).hexdigest()[:40]

# ---- build the graph ----
q = [rng.random() ** 2 + 0.05 for _ in range(HONEST)]
cum, t = [], 0.0
for w in q: t += w; cum.append(t)
out = [[] for _ in range(N)]
for i in range(HONEST):
    ch, tries = set(), 0
    while len(ch) < K and tries < 200:
        j = rng.choices(range(HONEST), cum_weights=cum)[0]; tries += 1
        if j != i: ch.add(j)
    out[i] = list(ch)
for i in range(HONEST, N): out[i] = [j for j in range(HONEST, N) if j != i]   # Sybil ring endorses itself
for _ in range(ATTACK_EDGES): out[rng.randrange(HONEST)].append(rng.randrange(HONEST, N))
seeds = rng.sample(range(HONEST), N_SEEDS)

# ---- seeded PageRank with a per-node weight cap (excess is spread evenly over all nodes) ----
def ppr_capped(out, seeds, cap, d=0.85, iters=100, tol=1e-12):
    n = len(out); tele = [0.0] * n
    for s in seeds: tele[s] = 1.0 / len(seeds)
    x = tele[:]
    for _ in range(iters):
        y = [(1 - d) * v for v in tele]; leak = 0.0
        for a in range(n):
            xa = x[a]
            if xa > cap: leak += d * (xa - cap); xa = cap
            if out[a]:
                sh = d * xa / len(out[a])
                for b in out[a]: y[b] += sh
            else: leak += d * xa
        if leak:
            for i in range(n): y[i] += leak / n
        diff = sum(abs(y[i] - x[i]) for i in range(n)); x = y
        if diff < tol: break
    return x

score = ppr_capped(out, seeds, CAP_MULT / N)
indeg = [0] * N
for a in range(N):
    for b in out[a]: indeg[b] += 1
edges = {(a, b) for a in range(N) for b in out[a]}

def rank_of(vals):
    order = sorted(range(N), key=lambda i: -vals[i]); r = [0] * N
    for pos, i in enumerate(order, 1): r[i] = pos
    return r
r_score, r_deg = rank_of(score), rank_of([float(v) for v in indeg])

def recip(i):
    o = out[i]
    return (sum((b, i) in edges for b in o) / len(o)) if o else 0.0

def independent(i):
    """Endorsers of i that i has NOT endorsed back."""
    return sum(1 for a in range(N) if (a, i) in edges and (i, a) not in edges)

seed_set = set(seeds)
today = datetime.date.today().isoformat()
rows = []
for i in range(N):
    group = "seed" if i in seed_set else ("honest" if i < HONEST else "sybil_ring")
    rc = recip(i)
    rows.append({"key": addr(i), "value": json.dumps({
        "address": addr(i),
        "is_seed": i in seed_set,
        "trust_percentile": round(100 * (N - r_score[i]) / (N - 1), 1),   # 100 = highest
        "rank": r_score[i], "of": N,
        "rank_if_counting_endorsements_only": r_deg[i],
        "endorsements_received": indeg[i],
        "independent_endorsers": independent(i),
        "endorsements_given": len(out[i]),
        "reciprocity": round(rc, 2),
        "flag_reciprocal_cluster": bool(len(out[i]) >= 3 and rc > RECIP_FLAG),
        "demo_group": group,                         # ground truth, demo only. Remove for real data.
        "model": "CSA v2.0 seeded PageRank + weight cap",
        "demo_data": True, "updated": today}, ensure_ascii=False)})
json.dump(rows, open("scores.json", "w"), ensure_ascii=False, indent=1)

print(f"wrote scores.json: {len(rows)} addresses")
print(f"Sybil score mass: seeded={sum(score[HONEST:])/sum(score):.1%} | endorsement count only={sum(indeg[HONEST:])/sum(indeg):.1%}")