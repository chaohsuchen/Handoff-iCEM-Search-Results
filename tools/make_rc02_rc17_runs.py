"""More rc01 runs for the two RCs that are views of rc01 (tools/make_derived.py): rc02 (gap too short to stop: negative cases) and rc17 (observation delay).
The three shared rc01 policies (Fred's R4 set) in every scene of a grid: rc01/rc02_gap (v_ego x gap) and rc01/rc17_delay (gap x delay_s, delay 0 included so each delayed scene has its no-delay pair).
Writes results_search/rc01/search/{rc02_gap,rc17_delay}/candidates.json.   python tools/make_rc02_rc17_runs.py"""
import json, os
R = "results_search"
SHARED = [("brake", dict(a0=0.0, t1=99.0, d0=0.318002504425445, a1=5.978474320278684)),
          ("surge_brake", dict(t1=99.0, a0=0.3, d0=0.2, a1=7.2)),
          ("two_stage", dict(a0=0.0, d0=0.365863820875553, a1=5.97911846818319, t1=1.3180948562768222, a2=5.492681724246033))]
def cands(scenes, req):
    out = []
    for name, ts in scenes:
        for fam, tp in SHARED:
            out.append(dict(scenario=name, theta_s=ts, family=fam, kind="shared", theta_p=tp, request=req, search=dict(note="coverage: " + req),
                            surrogate=dict(verdict="NA", cls="NA", min_front=0.0, min_rear=0.0)))
    return out
def write(b, c):
    os.makedirs(f"{R}/rc01/search/{b}", exist_ok=True); json.dump(c, open(f"{R}/rc01/search/{b}/candidates.json", "w")); print(b, len(c))
write("rc02_gap", cands([(f"v{v}_g{g}", dict(v_ego=v, gap=float(g))) for v in (9.5, 8.1) for g in (5, 6, 7, 8, 9)], "RC02"))
write("rc17_delay", cands([(f"g{g}_d{d}", dict(v_ego=8.1, gap=float(g), delay_s=d)) for g in (14, 16, 18) for d in (0.0, 0.15, 0.3, 0.45, 0.6, 0.75, 0.9)], "RC17"))
