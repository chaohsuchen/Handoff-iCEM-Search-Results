"""Bring every run folder of results_search/ (the 20 RCs) to one format.   python tools/unify_runs.py [--root results_search] [--rc rc07,rc10] [--workers 32] [--dry-run]

Two producers write run folders: Victor's engine (rcx/, rc01 rc03 rc04 rc05 rc06 rc09 rc13) and Kent's engine (carla_rc/teachers/evidence.py, rc07 rc08 rc10 rc11 rc12 rc14 rc15 rc16 rc19).
Both are `rcx-run-1` and both carry the same files; the differences this tool removes (idempotent: a folder already unified is skipped):

  per-tick files   always gzipped (`ego_observable.csv.gz`, `ground_truth.csv.gz`, `decisions.jsonl.gz`); `run.mp4` is never part of a delivery
  columns          Kent's seen_<actor>_{s,t,vs,vt} are renamed seen_<actor>_rel_{s,t,vs,vt} (the names of Victor's runs, which Fred has already seen)
  angles           yaw / heading columns of the CSV files in DEGREES, positive = nose to the right (Kent's were radians): `*yaw_rel`, `*_psi`; rates stay rad/s
  constraints      every constraint is {name, kind, measured, required, op, unit, passed} (Kent's had no kind / op, and no_contact / goal had dict values)
  summary.json     all of: scene_name, hidden_settings, scene{name,uid,site,split,history_id,hidden_world,hidden_params}, constraints_pass,
                   contact_detail, first_violated_constraint, history_s (recorded time before the cue), short_history, units, pass_rule_id, unified
Labels are never changed.  What stays different (documented in results_search/README.md): the clearance threshold (Victor: raw 0.5 m; Kent: 0.05 above a 0.5 m reserve = 0.55 m)
and the origin of `sim_time` (CARLA clock in Victor's runs, 0 at the end of the pre-roll in Kent's); `t_since_cue` is the common clock.
"""
import argparse, csv, glob, gzip, hashlib, io, json, math, os, re, sys
from multiprocessing import Pool

VERSION = "unify-2"
PREV = "unify-1"                                  # unify-1 runs only need the column rename of unify-2 (their angles are already converted)
SHORT_S = 3.0                                    # recorded time before the cue below which a run is flagged short_history
DT = 0.05
HIDDEN_HISTORY = {"rc03": ("crash", "intrude", "lead_brake")}     # rc03: the settings Fred measured as hidden (D3); other cases: every declared hidden setting
PASS_RULE = {"victor": "all constraints passed; thresholds are the raw limits in `constraints` (clearance 0.5 m, ...)",
             "kent": "all constraints passed; clearance / road / terminal / friction need a margin of 0.05 above their reserve (clearance reserve 0.5 m, so 0.55 m)"}
ANGLE = lambda c: c.endswith("yaw_rel") or c.endswith("_psi") or c == "ego_psi"


def opened(path):
    """(text, existed) of path or path.gz"""
    if os.path.exists(path): return open(path).read()
    if os.path.exists(path + ".gz"): return gzip.open(path + ".gz", "rt").read()
    return None


def write_gz(path, text):
    tmp = path + ".gz.tmp"
    with gzip.open(tmp, "wt", compresslevel=6) as f: f.write(text)
    os.replace(tmp, path + ".gz")
    if os.path.exists(path): os.remove(path)


def to_deg(text):
    """rows of a csv text with the angle columns converted from radians to degrees"""
    rd = csv.reader(io.StringIO(text)); head = next(rd); idx = [i for i, c in enumerate(head) if ANGLE(c)]
    out = io.StringIO(); w = csv.writer(out, lineterminator="\n"); w.writerow(head)
    for row in rd:
        for i in idx:
            if row[i] != "":
                try: row[i] = "%.7g" % (float(row[i]) * 180.0 / math.pi)
                except ValueError: pass
        w.writerow(row)
    return out.getvalue(), [head[i] for i in idx]


def rename_seen(text):
    head, _, rest = text.partition("\n")
    cols = head.split(",")
    new = [re.sub(r"^(seen_.+)_(s|t|vs|vt)$", r"\1_rel_\2", c) if c.startswith("seen_") and "_rel_" not in c else c for c in cols]
    return ",".join(new) + "\n" + rest


def origin(s):
    return "kent" if isinstance(s.get("scene"), dict) and s["constraints"] and "kind" not in s["constraints"][0] else "victor"


def origin_of(s):
    """origin of an already unified summary"""
    return "kent" if s.get("pass_rule_id", "").startswith("kent") else "victor"


def history_s(rows):
    t0 = next((float(r["sim_time"]) for r in rows[:1]), None)
    k = next((r for r in rows if r.get("t_since_cue") not in ("", None)), None)
    return None if k is None or t0 is None else round(float(k["sim_time"]) - t0, 3)


KIND = dict(clearance="clearance", road="clearance", terminal="clearance", friction="limit", envelope="limit", no_contact="contact", goal="state")


def constraints_kent(s):
    out = []
    for c in s["constraints"]:
        n, m = c["name"], c.get("measured")
        k = KIND.get(n, "state"); o = dict(name=n, kind=k, unit=c.get("unit"), passed=bool(c["passed"]))
        if n == "no_contact":
            o.update(measured=float(len(s.get("contact", {}).get("frames") or [])), required=0.0, op="==", unit="frames")
        elif n == "goal":
            o.update(measured=0.0 if c["passed"] else 1.0, required=0.0, op="==", unit="violations")
        elif n == "envelope":
            o.update(measured=float(m), required=float(c["required"]), op="==" if float(c["required"]) == 0 else "<=")
        else:
            o.update(measured=m, required=c["required"], op=">=")
            if n == "clearance": o["reserve_m"] = 0.5
        if "definition" in c: o["definition"] = c["definition"]
        out.append(o)
    return out


def contact_detail_kent(s, rows):
    c = s.get("contact") or {}; fr = c.get("frames") or []
    if not fr: return None
    r = next((r for r in rows if r.get("contact") not in ("0", "", None)), None)
    ts = float(r["t_since_cue"]) if r and r.get("t_since_cue") not in ("", None) else None
    return dict(frame=fr[0], time_s=float(r["sim_time"]) if r else None, t_since_cue_s=ts, actor=(c.get("actors") or [None])[0], source="footprint/sensor",
                rel_speed_mps=c.get("impact_speed"), normal_impulse_Ns=None, n_contact_frames=len(fr), backfilled=True)


def first_violated_kent(cons, cd):
    bad = [c for c in cons if not c["passed"]]
    if not bad: return None
    ct = next((c for c in bad if c["kind"] == "contact"), None)
    if ct and cd: return dict(name=ct["name"], time_s=cd["time_s"], dated=True, t_since_cue_s=cd["t_since_cue_s"])
    return dict(name=bad[0]["name"], time_s=None, dated=False)


def history_victor(s):
    p = dict(s.get("scenario_params") or {}); case = s.get("rc_case") or s["rc"].lower()
    hid = HIDDEN_HISTORY.get(case, tuple(s.get("hidden_settings") or ()))
    vis = {k: v for k, v in p.items() if k not in hid and k not in ("preroll_s", "seed")}
    hk = hashlib.md5(json.dumps(dict(c=case, sc=s.get("scene_name"), v=vis), sort_keys=True).encode()).hexdigest()[:10]
    world = {k: p.get(k) for k in hid if k in p}
    return "h" + hk, (json.dumps(world, sort_keys=True) if world else None)


def process(args):
    d, dry = args
    try:
        sp = os.path.join(d, "summary.json"); s = json.load(open(sp))
        if s.get("unified") == VERSION: return d, "skip"
        if s.get("unified") == PREV:
            if dry: return d, "ok(dry)"
            if origin_of(s) == "kent":
                eo = opened(os.path.join(d, "ego_observable.csv")); write_gz(os.path.join(d, "ego_observable.csv"), rename_seen(eo))
            s["unified"] = VERSION; json.dump(s, open(sp + ".tmp", "w"), indent=1, default=float); os.replace(sp + ".tmp", sp); return d, "ok"
        o = origin(s); eo = opened(os.path.join(d, "ego_observable.csv")); gt = opened(os.path.join(d, "ground_truth.csv")); dec = opened(os.path.join(d, "decisions.jsonl"))
        if eo is None: return d, "no ego_observable"
        conv = []
        if o == "kent":
            eo, c1 = to_deg(eo); conv += c1; eo = rename_seen(eo)
            if gt is not None: gt, c2 = to_deg(gt)
            rows = list(csv.DictReader(io.StringIO(eo)))
            s["scene_name"] = (s.get("scene") or {}).get("name"); s["hidden_settings"] = list(s.get("hidden_params") or (s.get("scene") or {}).get("hidden_params") or [])
            cons = constraints_kent(s); s["constraints_raw_kent"] = s["constraints"]; s["constraints"] = cons
            s["contact_detail"] = contact_detail_kent(s, rows)
            s["first_violated_constraint"] = first_violated_kent(cons, s["contact_detail"])
        else:
            rows = list(csv.DictReader(io.StringIO(eo)))
            hid, world = history_victor(s)
            s["scene"] = dict(name=s.get("scene_name"), uid=None, site=None, split=None, history_id=hid, hidden_world=world, hidden_params=list(s.get("hidden_settings") or []))
        lab = s.get("label")
        s["constraints_pass"] = None if lab == "INVALID" else all(c["passed"] for c in s["constraints"])
        hs = history_s(rows); s["history_s"] = hs; s["short_history"] = None if hs is None else hs < SHORT_S
        s["units"] = dict(angle="deg", angular_rate="rad/s", length="m", speed="m/s", acceleration="m/s^2", time="s",
                          frame="s forward, t positive to the right, yaw positive nose to the right", sim_time_origin="0 at the end of the pre-roll" if o == "kent" else "CARLA clock",
                          angle_converted_from_rad=conv)
        s["pass_rule_id"] = o + "-v1"; s["pass_rule"] = PASS_RULE[o]; s["unified"] = VERSION
        files = ["summary.json", "ego_observable.csv.gz", "ground_truth.csv.gz", "decisions.jsonl.gz"]
        s["files"] = files
        if dry: return d, "ok(dry)"
        write_gz(os.path.join(d, "ego_observable.csv"), eo)
        if gt is not None: write_gz(os.path.join(d, "ground_truth.csv"), gt)
        if dec is not None: write_gz(os.path.join(d, "decisions.jsonl"), dec)
        json.dump(s, open(sp + ".tmp", "w"), indent=1, default=float); os.replace(sp + ".tmp", sp)
        return d, "ok"
    except Exception as e:
        return d, f"ERROR {type(e).__name__}: {e}"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--root", default="results_search"); ap.add_argument("--rc", default=""); ap.add_argument("--workers", type=int, default=32); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    rcs = a.rc.split(",") if a.rc else sorted(os.path.basename(p) for p in glob.glob(f"{a.root}/rc*") if os.path.isdir(p))
    dirs = []
    for rc in rcs:
        for r, ds, fs in os.walk(f"{a.root}/{rc}/carla"):
            if "summary.json" in fs and os.path.basename(os.path.dirname(r)) == "runs": dirs.append(r)
    print(len(dirs), "run folders in", rcs, flush=True)
    res = {}
    with Pool(a.workers) as p:
        for k, (d, st) in enumerate(p.imap_unordered(process, [(d, a.dry_run) for d in dirs], chunksize=20)):
            res.setdefault(st if not st.startswith("ERROR") else "ERROR", []).append(d)
            if st.startswith("ERROR") and len(res["ERROR"]) <= 5: print(d, st, flush=True)
            if k % 2000 == 0: print(k, {x: len(v) for x, v in res.items()}, flush=True)
    print({x: len(v) for x, v in res.items()})
