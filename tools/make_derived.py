"""RC02, RC17 and RC20 are defined on scenes that another RC already runs (docs/scenes/20RCs.md), so they are views over existing run folders, not new simulations:
  rc02  the RC01 van scene at a gap too short to stop: scenes in which no evaluated policy passes (negative cases)
  rc17  the RC01 scene with the ego's observation delayed by delay_s (the variant docs/scenes/20RCs.md calls built): the same policy and scene at different delays
  rc20  the RC04 scene under search coverage: the label of a scene under the restricted library (brake, lane_change) and under the full library (+ staged)
Writes results_search/<rc>/members.json (+ README.md).  python tools/make_derived.py  (needs results_search/summary/carla_runs.json: tools/index_runs.py)"""
import collections, json, os
R = "results_search"; rows = json.load(open(f"{R}/summary/carla_runs.json")); J = lambda x: json.dumps(x, sort_keys=True)
def put(rc, body, readme):
    os.makedirs(f"{R}/{rc}", exist_ok=True); json.dump(body, open(f"{R}/{rc}/members.json", "w"), indent=1); open(f"{R}/{rc}/README.md", "w").write(readme)
    print(rc, {k: (len(v) if isinstance(v, list) else v) for k, v in body.items() if k not in ("definition", "rule", "note")})
ref = lambda r: dict(run_id=r["run_id"], batch=f"rc01/{r['batch']}" if r["case"] == "rc01" else f"{r['case']}/{r['batch']}", dir=r["evidence_dir"], label=r["label"], family=r["family"], kind=r["kind"])

# ---------------- rc02 / rc17 from rc01
r1 = [r for r in rows if r["case"] == "rc01" and r["label"] != "INVALID"]
scene = lambda r: J({k: v for k, v in r["scenario_params"].items() if k not in ("seed", "preroll_s")})
bysc = collections.defaultdict(list)
for r in r1: bysc[scene(r)].append(r)
neg = []
for k, v in bysc.items():
    p = json.loads(k)
    if not p.get("delay_s") and not any(x["label"] == "PASS" for x in v) and len(v) >= 3:
        neg.append(dict(scene=p, n_policies=len(v), runs=[ref(x) for x in v]))
put("rc02", dict(definition="RC02: the RC01 scene with the trigger gap below the stopping distance; nothing works (negative case). docs/scenes/20RCs.md: generated from RC01's gap range, not a separate scene.",
                 rule="scenes of rc01 with delay_s = 0 and at least 3 evaluated policies in which no policy passes", scenes=neg),
    "# RC02 (view over rc01)\n\nRC02 is the RC01 van scene at a gap too short to stop in. It has no scene of its own (`docs/scenes/20RCs.md`), so this folder only lists the rc01 run folders that are RC02 cases: "
    "`members.json` -> `scenes[]` = the scene parameters, and for each the evaluated policies with their run folders (`dir`) and labels. Every one of them FAILs (negative cases, `UNRESOLVED` does not occur). "
    "All format rules of the run folders are those of rc01.\n")
pairs = []
for k, v in bysc.items():
    p = json.loads(k)
    if p.get("delay_s"):                                              # compare with the same scene and policy at another delay
        base = {kk: vv for kk, vv in p.items() if kk != "delay_s"}
        pairs.append((J(base), p["delay_s"], v))
fam = collections.defaultdict(dict)                                   # (scene without delay, policy) -> {delay: label}
for r in r1:
    p = {kk: vv for kk, vv in r["scenario_params"].items() if kk not in ("seed", "preroll_s", "delay_s")}
    fam[(J(p), r["family"], J(r["policy_params"]))][r["scenario_params"].get("delay_s") or 0.0] = r
con = []
for (sc, f, pp), d in fam.items():
    if len(d) >= 2 and len({x["label"] for x in d.values()}) > 1:
        con.append(dict(scene=json.loads(sc), family=f, policy_params=json.loads(pp), by_delay_s={str(k): ref(v) for k, v in sorted(d.items())}))
dl = collections.defaultdict(collections.Counter)
for r in r1: dl[r["scenario_params"].get("delay_s") or 0.0][r["label"]] += 1
put("rc17", dict(definition="RC17 (built variant): the RC01 scene with the ego's observation delayed by delay_s (docs/scenes/20RCs.md, RC01 and RC17). The planned RC16 + lag version is not built.",
                 rule="rc01 runs, grouped by delay_s; a contrast = the same scene and policy that passes at a short delay and fails at a longer one",
                 delays={str(k): dict(v) for k, v in sorted(dl.items())}, contrasts=con),
    "# RC17 (view over rc01)\n\nThe RC17 variant that is built in this project is RC01 with `delay_s` (the delay of the observation that reaches the controller). `members.json`: `delays` = labels per delay_s over all rc01 runs; "
    "`contrasts[]` = the same scene and policy at different delays whose label differs (the contrast RC17 asks for), each with the run folder of every delay. "
    "The md's planned RC17 (RC16 + a lag on the car's sensing and actuation) is **not** built.\n")

# ---------------- rc20 from rc04
r4 = [r for r in rows if r["case"] == "rc04" and r["label"] != "INVALID"]
RESTRICTED, FULL = ("brake", "lane_change"), ("brake", "lane_change", "staged")
hist = collections.defaultdict(lambda: collections.defaultdict(list))
for r in r4: hist[(r["history_id"], r["hidden_world"])][r["family"]].append(r)
out = []; cnt = collections.Counter()
for (h, w), fams in sorted(hist.items(), key=str):
    ok = lambda fs: any(x["label"] == "PASS" for f in fs for x in fams.get(f, []))
    missing_r = [f for f in RESTRICTED if f not in fams]; missing_f = [f for f in FULL if f not in fams]
    lab_r = "recoverable" if ok(RESTRICTED) else ("UNRESOLVED" if missing_r else "unrecoverable within the library")
    lab_f = "recoverable" if ok(FULL) else ("UNRESOLVED" if missing_f else "unrecoverable within the library")
    cnt[(lab_r, lab_f)] += 1
    out.append(dict(history_id=h, hidden_world=w, scene=r4[0]["scene"], evaluated_families=sorted(fams), restricted_library=lab_r, full_library=lab_f,
                    found_by_staged_only=bool(lab_f == "recoverable" and lab_r != "recoverable"), library_version="rc04 families brake, lane_change, staged (rcx/rc04_laws.py)",
                    runs=[ref(x) for f in sorted(fams) for x in fams[f]]))
put("rc20", dict(definition="RC20: the RC04 scene, label under the restricted library (immediate lane change, straight braking) vs the full library (+ staged); a missing family is UNRESOLVED, never failure.",
                 rule="a (scene, hidden world) is recoverable under a library when one of its policies passes in CARLA; if no policy passes but a family of the library was never evaluated it is UNRESOLVED",
                 counts={f"{a} | {b}": v for (a, b), v in cnt.items()}, scenes=out),
    "# RC20 (view over rc04)\n\nRC20 asks how the label depends on search coverage on the RC04 scene (brake, then change behind the truck). `members.json` -> `scenes[]`: one entry per (scene history, hidden world) with its label under the "
    "restricted library (`brake`, `lane_change`) and under the full library (+ `staged`), the evaluated families and the rc04 run folders behind it. `found_by_staged_only` = the staged plan makes the scene recoverable "
    "where the restricted library does not: the case RC20 is about. A scene in which a family was never evaluated is `UNRESOLVED` (missing evaluations are never failure). `counts` summarises.\n")
