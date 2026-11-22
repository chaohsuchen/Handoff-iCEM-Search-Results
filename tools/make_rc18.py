"""RC18 (requested control exceeds available authority): RC03's spun-car scene on the bend sites in dry, wet and heavy rain, plain (no delay).
Built from rc12's candidates (Kent's RC03 scene with a decision delay) with delay = 0: every distinct (site, policy, scene) is run in all three road conditions, so
the same policy and scene can be compared dry vs wet vs heavy (a lane change that works dry and fails in heavy rain is the case RC18 is about). Town13 sites are left out.
Writes results_search/rc18/carla/vsearch/selected.json; run with slurm/kent_run.sbatch (CMD=run RC=rc18 BATCH=vsearch).   python tools/make_rc18.py"""
import json, os, collections
R = "results_search"; J = lambda x: json.dumps(x, sort_keys=True)
sel = json.load(open(f"{R}/rc12/carla/vsearch/selected.json"))
CURVED = {"C1", "C2", "D1", "D2", "C1b", "C2b", "D2b"}
seen, out = {}, []
for c in sel:
    ts = c["theta_s"]
    if c["site"] not in CURVED or float(ts.get("delay", 0.0)) != 0.0 or c.get("hidden_world"): continue
    base = {k: v for k, v in ts.items() if k not in ("wx", "delay")}
    k = (c["sid"], J(base), c["family"], J(c["theta_p"]), c["kind"])
    seen.setdefault(k, c)
for k, c in sorted(seen.items(), key=lambda x: (x[1]["site"], x[1]["variation_id"], x[1]["family"], x[1]["kind"])):
    for wx in ("dry", "wet", "heavy"):
        e = json.loads(json.dumps(c)); e["theta_s"]["wx"] = wx; e["theta_s"]["delay"] = 0.0
        e["variation_id"] = f"{c['variation_id']}@{wx}"; e["why"] = ["rc18"]; e["surrogate"] = dict(c["surrogate"], verdict="NA", r=0.0)
        e["policy_source"] = dict(c.get("policy_source", {}), note="RC18: policy and scene of rc12 (delay 0), road condition varied")
        e["history_id"] = c["variation_id"] + "@" + wx; e.pop("hidden_world", None); out.append(e)
for i, e in enumerate(out): e["run_id"] = f"{i:03d}_{e['variation_id']}_{e['family'].replace('>', '-')}_{e['kind']}"
os.makedirs(f"{R}/rc18/carla/vsearch", exist_ok=True); json.dump(out, open(f"{R}/rc18/carla/vsearch/selected.json", "w"), indent=1, default=float)
print(len(out), "candidates;", dict(collections.Counter(e["site"] for e in out)), dict(collections.Counter(e["theta_s"]["wx"] for e in out)))
