"""Shared by index_runs.py, delivery_status.py and check_all.py: find every run folder of results_search/ and read its summary.json (threaded; the folders are many and small).
run_dirs(root) -> [(rc, batch, run_dir)] where batch is the path between carla/ and runs/ (e.g. 'pre6', 'vsearch/repeats')."""
import glob, json, os
from concurrent.futures import ThreadPoolExecutor


def run_dirs(root="results_search", rcs=None):
    out = []
    for rc in sorted(os.path.basename(p) for p in glob.glob(f"{root}/rc[0-9][0-9]")):
        if rcs and rc not in rcs: continue
        for r, ds, fs in os.walk(f"{root}/{rc}/carla"):
            if "summary.json" in fs and os.path.basename(os.path.dirname(r)) == "runs":
                out.append((rc, os.path.relpath(os.path.dirname(os.path.dirname(r)), f"{root}/{rc}/carla"), r))
    return out


def _read(t):
    rc, b, d = t
    try: return rc, b, d, json.load(open(os.path.join(d, "summary.json")))
    except Exception as e: return rc, b, d, {"_error": repr(e)}


def scan(root="results_search", rcs=None, workers=16):
    with ThreadPoolExecutor(workers) as ex: return list(ex.map(_read, run_dirs(root, rcs), chunksize=64))
