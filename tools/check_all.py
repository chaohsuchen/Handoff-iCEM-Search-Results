"""Check that every run folder of the 20 RCs follows the one format (docs/RUN_SCHEMA.md).  python tools/check_all.py [--rc rc07,rc10] [--header-sample 1.0]
Prints violations by kind with a few examples, and exits 1 if there are any.  Labels are not judged here, only the format and the internal consistency."""
import argparse, collections, csv, gzip, json, os, random, sys
sys.path.insert(0, os.path.dirname(__file__)); from runs_scan import scan
ap = argparse.ArgumentParser(); ap.add_argument("--root", default="results_search"); ap.add_argument("--rc", default=""); ap.add_argument("--header-sample", type=float, default=0.1, help="share of runs whose csv / jsonl headers are read")
a = ap.parse_args()
KEYS = {"schema", "run_id", "rc", "label", "reason", "end_reason", "scenario_params", "policy_params", "family", "candidate_kind", "variation_id", "metrics", "contact", "files", "scene_seed",
        "scene_name", "hidden_settings", "scene", "constraints", "constraints_pass", "contact_detail", "first_violated_constraint", "history_s", "short_history", "units", "pass_rule_id", "unified"}
SCENE = {"name", "uid", "site", "split", "history_id", "hidden_world", "hidden_params"}
CON = {"name", "kind", "measured", "required", "op", "unit", "passed"}
EGO = {"frame", "sim_time", "t_since_cue", "phase", "ego_s", "ego_t", "ego_yaw_rel", "speed", "a_req", "throttle", "brake", "steer", "contact"}
GT = {"frame", "sim_time", "contact_actor"}
DEC = {"frame", "t_since_cue", "observation", "policy_output"}
bad = collections.defaultdict(list); random.seed(0); n = 0; notrig = []
for rc, b, d, s in scan(a.root, set(a.rc.split(",")) if a.rc else None):
    n += 1; t = f"{rc}/{b}/{os.path.basename(d)}"
    if "_error" in s: bad["summary unreadable"].append(t); continue
    m = KEYS - set(s)
    if m: bad[f"summary missing {sorted(m)}"].append(t); continue
    if s["schema"] != "rcx-run-1": bad["schema != rcx-run-1"].append(t)
    if s["label"] not in ("PASS", "FAIL", "INVALID"): bad[f"label {s['label']}"].append(t)
    if SCENE - set(s["scene"]): bad["scene block incomplete"].append(t)
    if any(CON - set(c) for c in (s["constraints"] or [])): bad["constraint without kind/op/unit/..."].append(t)
    if s["label"] != "INVALID":
        if s["constraints_pass"] != (s["label"] == "PASS"): bad["label and constraints_pass disagree"].append(t)
    if s["units"].get("angle") != "deg": bad["angle unit not deg"].append(t)
    if s["history_s"] is None and s["label"] != "INVALID": notrig.append(rc)         # the policy never fired its trigger: no cue clock in this run (not a format error)
    for f in ("ego_observable.csv.gz", "ground_truth.csv.gz", "decisions.jsonl.gz"):
        if not os.path.exists(f"{d}/{f}"): bad[f"missing {f}"].append(t)
    for f in os.listdir(d):
        if f in ("ego_observable.csv", "ground_truth.csv", "decisions.jsonl"): bad["plain per-tick file left next to .gz"].append(t)
    if random.random() < a.header_sample:
        try:
            for f, need in (("ego_observable.csv.gz", EGO), ("ground_truth.csv.gz", GT)):
                mm = need - set(next(csv.reader(gzip.open(f"{d}/{f}", "rt")))); mm and bad[f"{f} missing {sorted(mm)}"].append(t)
            mm = DEC - set(json.loads(gzip.open(f"{d}/decisions.jsonl.gz", "rt").readline())); mm and bad[f"decisions missing {sorted(mm)}"].append(t)
        except Exception as e: bad[f"per-tick file unreadable: {type(e).__name__}"].append(t)
print(n, "run folders checked;", len(notrig), "runs without a cue clock (policy never triggered):", dict(collections.Counter(notrig)))
for k, v in sorted(bad.items(), key=lambda x: -len(x[1])): print(f"  {len(v):6d}  {k}   e.g. {v[0]}")
print("FORMAT OK" if not bad else f"{sum(len(v) for v in bad.values())} violations"); sys.exit(1 if bad else 0)
