"""Add scene_name, hidden_settings and the constraint block (rcx/constraints.py) to the summary.json of every existing run, from the recorded
ego_observable.csv + ground_truth.csv + summary.json (no CARLA needed). New runs get the same fields from rcx/common.py:run_engine.
Check: constraints_pass must agree with the CARLA label (PASS <=> all constraints passed) for every run; disagreements are listed and NOT written.
python tools/backfill_constraints.py [--dry-run] [--root results_search]"""
import argparse, csv, glob, json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rcx import constraints

ap = argparse.ArgumentParser(); ap.add_argument("--root", default="results_search"); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--skip-batches", default="", help="comma list of batch names to leave alone (batches still being written)")
a = ap.parse_args()


def val(x):
    if x in ("True", "False"): return x == "True"
    try: return float(x)
    except ValueError: return x


def load_rows(d):
    ego = {int(r["frame"]): r for r in csv.DictReader(open(os.path.join(d, "ego_observable.csv")))}
    out = []
    for g in csv.DictReader(open(os.path.join(d, "ground_truth.csv"))):
        r = dict(ego[int(g["frame"])]); r.update(g); out.append({k: val(v) for k, v in r.items()})
    return out


def contact_detail_from_rows(rows):
    """R9 for runs recorded before contact_detail existed: time, actor and relative speed from the recorded rows. No collision impulse (None)."""
    i = next((k for k, r in enumerate(rows) if r.get("contact") == 1 or r.get("contact") == "1"), None)
    if i is None: return None
    r0, r1 = rows[max(0, i - 1)], rows[i]; who = str(r1.get("contact_actor", "")).replace(" (footprint overlap)", "")
    rel = None
    if f"actor_{who}_vs" in r0 and isinstance(r0[f"actor_{who}_vs"], float):
        y = math.radians(r0["ego_yaw_rel"]); rel = math.hypot(r0["speed"] * math.cos(y) - r0[f"actor_{who}_vs"], r0["speed"] * math.sin(y) - r0[f"actor_{who}_vt"])
    tc = r1["t_since_cue"]
    return dict(frame=int(r1["frame"]), time_s=float(r1["sim_time"]), t_since_cue_s=(float(tc) if isinstance(tc, float) else None), actor=who,
                source=("footprint" if "footprint" in str(r1.get("contact_actor", "")) else "sensor"), rel_speed_mps=rel, normal_impulse_Ns=None,
                n_contact_frames=int(sum(1 for r in rows if r.get("contact") in (1, "1"))), backfilled=True)


n = bad = 0; skipped = {}
for f in sorted(glob.glob(os.path.join(a.root, "*", "carla", "*", "runs", "*", "summary.json"))):
    d = os.path.dirname(f)
    if d.split(os.sep)[-3] in a.skip_batches.split(","): continue
    s = json.load(open(f)); case = s["rc_case"]
    rows = load_rows(d) if s["label"] not in ("INVALID", "UNRESOLVED") else []
    if rows and "contact_detail" not in s: s["contact_detail"] = contact_detail_from_rows(rows)
    ann = constraints.annotate(case, s, rows)
    n += 1
    ok = ann["constraints_pass"] is None or ann["constraints_pass"] == (s["label"] == "PASS")
    if not ok:
        bad += 1; failed = [c["name"] for c in ann["constraints"] if not c["passed"]]
        print(f"MISMATCH {d}: label {s['label']} constraints_pass {ann['constraints_pass']} failed={failed} | {s['reason'][:100]}"); continue
    if not a.dry_run: s.update(ann); json.dump(s, open(f, "w"), indent=2, default=float)
print(f"{n} runs, {bad} mismatches" + (" (dry run, nothing written)" if a.dry_run else ""))
