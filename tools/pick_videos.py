"""Pick representative runs for videos: per RC of Victor's engine (rc01, 03, 04, 05, 06, 09, 13; Kent's engine records no video) one PASS and one FAIL.
  python tools/pick_videos.py            -> results_search/videos/plan.json  (+ a table on stdout)

The runs are taken from the `current` batches only (not the superseded ones, see results_search/rc_status.json), valid labels only (no INVALID),
and are the middle element (by run folder name) of the runs of kind `best` (or, if there are none, of every kind): typical runs, not extremes.
The videos are re-rendered by running the same candidate again (tools/render_videos.sh) because the delivery does not keep the videos of the 22000 runs.
"""
import collections, json, os

R = "results_search"
idx = json.load(open(f"{R}/summary/carla_runs.json"))
meta = json.load(open(f"{R}/rc_status.json"))
ENGINE = {rc: "victor" for rc in ("rc01", "rc03", "rc04", "rc05", "rc06", "rc09", "rc13")}
plan, by = [], collections.defaultdict(list)
for r in idx:
    sup = set(meta.get(r["case"], {}).get("superseded", []))
    if r["batch"].split("/")[0] in sup or r["label"] not in ("PASS", "FAIL") or "pilot" in r["batch"] or "smoke" in r["batch"] or "/" in r["batch"]: continue    # repeats (shifted starts) cannot be re-rendered by id
    by[(r["case"], r["label"])].append(r)
for (rc, lab), v in sorted(by.items()):
    best = [r for r in v if r["kind"] == "best"] or v
    best.sort(key=lambda r: (r["batch"], r["run_id"]))
    r = best[len(best) // 2]
    if ENGINE.get(rc) != "victor": continue     # only Victor's engine records video; Kent's runs have no camera
    plan.append(dict(rc=rc, label=lab, batch=r["batch"], run_id=r["run_id"], engine=ENGINE.get(rc, "kent"), history_s=r["history_s"], evidence_dir=r["evidence_dir"],
                     video=f"{rc}_{lab}_{r['run_id']}.mp4".replace("@", "-")))
os.makedirs(f"{R}/videos", exist_ok=True)
json.dump(plan, open(f"{R}/videos/plan.json", "w"), indent=1)
for p in plan: print(p["rc"], p["label"], p["batch"], p["run_id"], p["history_s"])
print(len(plan), "videos planned")
