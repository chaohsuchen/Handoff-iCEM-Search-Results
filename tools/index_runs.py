"""Flat index of every CARLA run of every RC: one row per run folder -> results_search/summary/carla_runs.json (+ carla_runs.csv).
Built from the run folders' summary.json (the label is CARLA's verdict). Run after tools/unify_runs.py.   python tools/index_runs.py"""
import csv, json, os, collections, sys
sys.path.insert(0, os.path.dirname(__file__)); from runs_scan import scan
R = "results_search"; rows = []
STATUS = json.load(open(f"{R}/rc_status.json"))
# one vocabulary for the two engines' batch names (see README: "Batch names")
ROLE = [("baseline", "baseline"), ("boundary", "boundary"), ("presets", "presets"), ("pre6", "long_history"), ("pre4", "long_history"), ("r4_shared", "shared_policies"),
        ("r5_worlds", "all_worlds"), ("r6_", "seeds"), ("on_rc", "lookalike"), ("vsearch", "search"), ("rc02_gap", "derived_rc"), ("rc17_delay", "derived_rc"), ("rerun_invalid", "rerun")]
def role(batch):
    if "/repeats" in batch or batch.endswith("repeats"): return "seeds"
    if batch.split("/")[0].endswith("_pre4"): return "long_history"
    return next((r for k, r in ROLE if batch.startswith(k)), "other")
for rc, batch, d, s in scan(R):
    if "_error" in s: continue
    sc = s.get("scene") or {}; m = s.get("metrics") or {}
    rows.append(dict(case=rc, batch=batch, role=role(batch), current=batch.split("/")[0] not in STATUS.get(rc, {}).get("superseded", []), run_id=s.get("run_id") or os.path.basename(d), scene=sc.get("name") or s.get("scene_name"), uid=sc.get("uid"), site=sc.get("site"), split=sc.get("split"),
                     history_id=sc.get("history_id"), hidden_world=sc.get("hidden_world"), family=s.get("family"), kind=s.get("candidate_kind"),
                     label=s.get("label"), reason=s.get("reason"), constraints_pass=s.get("constraints_pass"), history_s=s.get("history_s"), short_history=s.get("short_history"),
                     pass_rule_id=s.get("pass_rule_id"), margin_r=m.get("r"), scene_seed=json.dumps(s.get("scene_seed")), scenario_params=s.get("scenario_params"), policy_params=s.get("policy_params"),
                     surrogate=s.get("surrogate_prediction"), contact=(s.get("contact") or {}).get("actors"), evidence_dir=d))
os.makedirs(f"{R}/summary", exist_ok=True)
json.dump(rows, open(f"{R}/summary/carla_runs.json", "w"), default=str)
flat = [k for k in rows[0] if k not in ("scenario_params", "policy_params", "surrogate", "contact")]
with open(f"{R}/summary/carla_runs.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=flat, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
c = collections.Counter((r["case"], r["batch"]) for r in rows)
for k, v in sorted(c.items()): print(k, v)
print(len(rows), "rows ->", f"{R}/summary/carla_runs.json, carla_runs.csv")
