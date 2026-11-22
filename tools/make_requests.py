"""Build the candidate files for the CARLA runs Fred asked for in coverage_requests.json (R4, R5, R6, R7, invalid reruns).
Candidates go to results_search/<rc>/search/<batch>/candidates.json and are executed with tools/verify_carla.py --case <rc> --batch <batch>
(slurm/verify_idle.sbatch).  Nothing here needs CARLA.  python tools/make_requests.py [--dry-run]

Batches
  rc03/pre6         R7   every rc03 candidate again with preroll_s = 6.0 (5 s recorded before the cue; the cue time is unchanged)
  rc03/r5_worlds    R5   each rc03 policy in every hidden world (crash, intrude, lead_brake) of the histories it already ran in, at preroll 6
  rc03/r4_shared    R4   Fred's shared policy set in every history and hidden world, at preroll 6
  rc01/r4_shared    R4   same for rc01 (rc01 has no hidden settings: one run per history)
  rc01/r6_seeds     R6   rc01 runs with |margin| < BAND2 again with three new scene seeds
  rc03/r6_repeat    R6   the 8 rc03 runs closest to margin 0 again, three scene seeds (rc03 uses no random numbers: this measures run-to-run noise)
  rc01/rerun_invalid     the rc01 runs that were INVALID ("van moved")
A history = the scenes that differ only in hidden settings (D3/D4 of PIPELINE_HANDOFF); a world = one value of the hidden settings.
Policy identity = family + searched parameters (D10).  A candidate that already ran in that scene is never requested again.
"""
import argparse, collections, glob, json, os, sys

ap = argparse.ArgumentParser(); ap.add_argument("--root", default="results_search"); ap.add_argument("--dry-run", action="store_true")
a = ap.parse_args()
HIDDEN = dict(rc03=("crash", "intrude", "lead_brake"), rc01=())          # measured by Fred (D3); rc01 has none
PREROLL = 6.0
SEEDS = (11, 13, 17)
BAND2 = 0.05                                                              # twice the declared noise band 0.03 would be 0.06; 0.05 keeps the list short
J = lambda x: json.dumps(x, sort_keys=True)

# Fred's shared policy set (coverage_requests.json, kind share_policies)
SHARED = dict(
    rc01=[("brake", dict(a0=0.0, t1=99.0, d0=0.318002504425445, a1=5.978474320278684)),
          ("surge_brake", dict(t1=99.0, a0=0.3, d0=0.2, a1=7.2)),
          ("two_stage", dict(a0=0.0, d0=0.365863820875553, a1=5.97911846818319, t1=1.3180948562768222, a2=5.492681724246033))],
    rc03=[("brake", dict(t_react=0.18228891639390465, a_brake=5.4354037300202656, shift=0.1334083419513106)),
          ("keep", {}),
          ("lane_change", dict(t_react=0.4008841505784707, t_lc=2.2014856067469966, a_lc=1.1903724080231033, a_post=1.94784283733585))])


def load(case, batches=None):
    out = []
    for f in sorted(glob.glob(f"{a.root}/{case}/search/*/candidates.json")):
        b = f.split("/")[-2]
        if batches is not None and b not in batches: continue
        for i, c in enumerate(json.load(open(f))): out.append((b, i, c))
    return out


def margin(cons):
    """Smallest constraint margin, clearances and limits over 5 m / 5 m/s2 (Fred's provisional D6/D7 scale), yes/no checks +-1, clipped to [-1, 1]."""
    m = 1.0
    for c in cons:
        if c["kind"] in ("clearance", "limit"):
            d = (c["measured"] - c["required"]) if c["op"] == ">=" else (c["required"] - c["measured"])
            m = min(m, d / 5.0)
        elif not c["passed"]: m = min(m, -0.1 if c["kind"] == "contact" else -1.0)
    return max(-1.0, m)


def runs(case):
    """existing run folders -> (candidate index, summary) per batch"""
    for f in sorted(glob.glob(f"{a.root}/{case}/carla/*/runs/*/summary.json")):
        p = f.split("/"); yield p[3], int(p[5].split("_")[0]), json.load(open(f))


def write(case, batch, cands):
    d = f"{a.root}/{case}/search/{batch}"
    print(f"{case}/{batch}: {len(cands)} candidates")
    if a.dry_run or not cands: return
    os.makedirs(d, exist_ok=True); json.dump(cands, open(f"{d}/candidates.json", "w"))


def new(donor, theta_s, theta_p, scenario, request, **extra):
    c = json.loads(json.dumps(donor)); c.update(theta_s=theta_s, theta_p=theta_p, scenario=scenario, request=request, search=dict(note="coverage request " + request))
    c.update(extra); return c


def split(case, ts):
    h = HIDDEN[case]; vis = {k: v for k, v in ts.items() if k not in h and k != "preroll_s" and k != "seed"}
    return J(vis), tuple(ts.get(k) for k in h)


def plan(case, base, request, shared_only):
    """base = candidates already run (with their final theta_s).  Returns new candidates."""
    hist = collections.defaultdict(dict)                    # history -> world -> representative candidate (scene)
    ran = set(); by_pol = collections.defaultdict(set)      # (policy) -> histories it ran in
    for b, i, c in base:
        hk, w = split(case, c["theta_s"]); hist[hk].setdefault(w, c)
        pk = (c["family"], J(c["theta_p"])); ran.add((hk, w, pk)); by_pol[pk].add(hk)
    donors = {}
    for _, _, c in base: donors.setdefault(c["family"], c)
    out = []
    pols = [((f, J(tp)), tp) for f, tp in SHARED[case]] if shared_only else None
    if shared_only:
        targets = [(pk, tp, set(hist)) for pk, tp in pols]
    else:                                                    # every policy in the histories it already ran in; shared policies are asked by R4
        sk = {(f, J(tp)) for f, tp in SHARED[case]}
        targets = [(pk, json.loads(pk[1]), hs) for pk, hs in by_pol.items() if pk not in sk]
    for pk, tp, hs in sorted(targets, key=lambda x: str(x[0])):
        for hk in sorted(hs):
            for w, sc in sorted(hist[hk].items(), key=str):
                if (hk, w, pk) in ran: continue
                donor = donors.get(pk[0]) or base[0][2]
                out.append(new(donor, sc["theta_s"], tp, sc["scenario"], request, family=pk[0], kind=donor["kind"]))
    return out


def with_preroll(cands):
    c2 = []
    for b, i, c in cands:
        c = json.loads(json.dumps(c)); c["theta_s"]["preroll_s"] = PREROLL; c["src_batch"] = b; c2.append((b, i, c))
    return c2


# ---------------- rc03: R7 base, R5, R4, R6 ----------------
c03 = load("rc03", batches={"baseline", "boundary_r3", "presets_22mps"})
pre6 = [(b, i, dict(c, theta_s=dict(c["theta_s"], preroll_s=PREROLL), src_batch=b)) for b, i, c in c03]
write("rc03", "pre6", [c for _, _, c in pre6])
r4 = plan("rc03", pre6, "R4", shared_only=True)
for c in r4: c["theta_s"]["preroll_s"] = PREROLL
write("rc03", "r4_shared", r4)
have = pre6 + [("r4_shared", i, c) for i, c in enumerate(r4)]
r5 = plan("rc03", have, "R5", shared_only=False)
for c in r5: c["theta_s"]["preroll_s"] = PREROLL
write("rc03", "r5_worlds", r5)

# ---------------- rc01: R4, R6, invalid ----------------
c01 = load("rc01")
r4b = plan("rc01", c01, "R4", shared_only=True); write("rc01", "r4_shared", r4b)
bad, near = [], []
for b, i, s in runs("rc01"):
    donor = json.load(open(f"{a.root}/rc01/search/{b}/candidates.json"))[i]
    if s["label"] == "INVALID": bad.append(donor)
    elif s.get("constraints") and abs(margin(s["constraints"])) < BAND2: near.append(donor)
write("rc01", "rerun_invalid", bad)
write("rc01", "r6_seeds", [new(d, dict(d["theta_s"], seed=sd), d["theta_p"], d["scenario"], "R6", kind=d["kind"], family=d["family"]) for d in near for sd in SEEDS])
n03 = []                                                  # the 8 valid rc03 runs closest to margin 0 (few are within the band: rc03 margins are mostly -0.1 or large)
for b, i, s in runs("rc03"):
    donor = json.load(open(f"{a.root}/rc03/search/{b}/candidates.json"))[i]
    if s.get("constraints") and s["label"] != "INVALID": n03.append((abs(margin(s["constraints"])), donor))
n03 = [d for _, d in sorted(n03, key=lambda x: x[0])[:8]]
write("rc03", "r6_repeat", [new(d, dict(d["theta_s"], preroll_s=PREROLL, seed=sd), d["theta_p"], d["scenario"], "R6", kind=d["kind"], family=d["family"]) for d in n03 for sd in SEEDS])
