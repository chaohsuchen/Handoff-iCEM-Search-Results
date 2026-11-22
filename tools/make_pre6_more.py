"""R7 for rc05, rc09, rc13: every candidate of the case again with preroll_s = 6.0 (5.0 s recorded before the cue; the state at the cue must not change).
Candidates go to results_search/<rc>/search/pre6/candidates.json; run them with tools/verify_carla.py --case <rc> --batch pre6 (slurm/verify_idle.sbatch).
rc05 and rc09 build every actor relative to the ego and to preroll_s, so only preroll_s changes. rc13 puts the pedestrians at absolute s: they move forward by
v_ego * (6.0 - old preroll) so that the gap at the cue stays the same."""
import glob, json, os
PRE = 6.0; R = "results_search"
for rc in ("rc05", "rc09", "rc13"):
    out = []
    for f in sorted(glob.glob(f"{R}/{rc}/search/*/candidates.json")):
        b = f.split("/")[-2]
        if b == "pre6": continue
        for i, c in enumerate(json.load(open(f))):
            c = json.loads(json.dumps(c)); ts = c["theta_s"]
            old = ts.get("preroll_s", 2.5 if rc != "rc05" else 3.0)
            if rc == "rc13":
                v = ts.get("v_ego", 8.0); ps = ts.get("ped_s", 78.0); ts["ped_s"] = ps + v * (PRE - old)
            ts["preroll_s"] = PRE; c["src_batch"] = b; c["request"] = "R7"; out.append(c)
    os.makedirs(f"{R}/{rc}/search/pre6", exist_ok=True); json.dump(out, open(f"{R}/{rc}/search/pre6/candidates.json", "w")); print(rc, len(out), "candidates")
