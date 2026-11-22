# Recovery-Condition (RC) dataset: 20 RCs in CARLA 0.9.15

Hand-off from Victor and Kent to Fred (world model).

For each Recovery Condition (RC) and scene variation we searched for recovery strategies that work, strategies that only mitigate, and strategies that fail,
and recorded every run in CARLA 0.9.15 as evidence. **Every label (PASS / FAIL / INVALID) comes from CARLA**; the surrogate simulators only propose candidates.
All 20 RCs are in `results_search/` in **one run format**, with the constraint block, hidden settings, scene name, shared policies and pre-roll history that
`PIPELINE_HANDOFF` asked for.

## If you only want the data (Fred): read these three, in this order

1. **`results_search/DELIVERY_STATUS.md`**: the 20 RCs in one table (runs, PASS / FAIL / INVALID, recorded time before the cue, `current` = without superseded batches).
2. **`docs/RUN_SCHEMA.md`**: what a run folder contains, units and signs (angles in **degrees**, positive = nose to the right), what the world model may use
   (`ego_observable.csv` and `decisions.jsonl` only; `ground_truth.csv` is for analysis).
3. **`results_search/README.md`**: how to read the batches (which batch replaces which, shared policies, worlds, seeds), and the answers to R1 to R9 / Q1 to Q7 are in
   `docs/handoff/PIPELINE_HANDOFF_REPLY.md`.

The flat index of every run is `results_search/summary/carla_runs.csv` (or `.json`). One row per run: RC, batch, `role` (what the batch is for, table below), `current` (false = superseded batch), scene, history id, hidden world, family, kind,
label, `constraints_pass`, `history_s`, `short_history`, `pass_rule_id`, margin, seeds, parameters, path.
Rebuild it with `python tools/index_runs.py`; check the whole folder against the format with `python tools/check_all.py`.

Optional: **`docs/report.md`** is a plain-language summary of what Victor and Kent did, how the search worked, how much data there is, what we found, and how we hope the world model uses it.

### Decisions you can rely on
- **Pass rule: a run passes if and only if every constraint in `summary.json: constraints` passed.** `constraints_pass` is that value (null for INVALID).
  Two engines wrote the runs and their clearance threshold differs; the id is in `summary.json: pass_rule_id`:
  `victor-v1` = raw limits (clearance 0.5 m in most RCs, 2.0 m during the hold in rc01, 1.0 and 2.0 m in rc05); `kent-v1` = a margin of 0.05 above the reserve (clearance 0.55 m). Labels are never recomputed.
- **INVALID** = the CARLA scene did not match the declared setup (e.g. a vehicle overlapping a wall). It has no label and no margin; leave it out.
- **History before the cue:** `summary.json: history_s` is the recorded time before the cue and `short_history` is true below 3 s. Every RC that could be re-made with a
  longer pre-roll was (rc03, rc04, rc05, rc06, rc09, rc13 at 5 s; rc12, rc18 at 4 s). The older, shorter batches stay on disk but are marked `superseded`
  in `results_search/rc_status.json`; use the `current` columns of `DELIVERY_STATUS.md`.
- **Clock:** `t_since_cue` is the common time axis. `sim_time` has a different origin in the two engines (CARLA clock vs 0 at the end of the pre-roll).

### Known limits (not hidden)
| RC | limit |
|---|---|
| rc15 | the recorded time before the cue is short (about 2 s, `short_history` is true for every run): the scene geometry (entrance ramp, coned lane) allows no more |
| Kent's RCs (rc07 to rc19) | recorded history is 3 to 4.5 s (Victor's: 5 s); 1183 runs (mostly rc12, rc19) have no `t_since_cue` because the policy never triggered, use `sim_time` there; clearance threshold 0.55 m (`kent-v1`), not 0.5 m; no video; label balance differs a lot per RC (rc12, rc18 mostly FAIL; rc07, rc15 mostly PASS) |
| Victor's RCs (rc01 to rc13) | few scenes (28 to 61 per RC): split by scene, not by run, and expect over-fitting; `rc03`, `rc04`, `rc06` are fully scripted (a new seed changes nothing) |
| rc19 | `on_rc03` is superseded by `on_rc03_pre4` (4 s); the `on_rc07` / `on_rc10` parts have about 3 s |
| rc06 | `pre6` covers 165 of 199 scenes: the other 34 cannot be spawned with 6 s of pre-roll (`results_search/rc06/carla/pre6/not_spawnable.json`) |
| rc13 | `pre6` has 63 INVALID runs (the pedestrians leave the sidewalk or the start speed does not match when the scene is shifted to a 6 s pre-roll); the old 1.5 s run of the same scene is the valid one |
| rc01 | 5 INVALID runs ("van moved") re-ran as INVALID: not recoverable |
| rc02, rc17, rc20 | **derived views** (`results_search/rc02`, `rc17`, `rc20`: `members.json` and `README.md`), not separate runs. rc02 and rc17 come from rc01 (plus the new batches `rc01/rc02_gap` and `rc01/rc17_delay`); rc20 from the rc04 library labels. The staged-only RC20 scene was not built (3 scenes UNRESOLVED) |

## Batch names (same meaning in both engines)

The batch folder names come from the two engines. `role` in `carla_runs.csv` gives them one vocabulary; filter `current == True` and a role instead of reading batch names.

| role | batch folders | what it is |
|---|---|---|
| `baseline` | `baseline` | first search result per scene |
| `boundary` | `boundary_r1/r2/r3` | settings next to the PASS / FAIL edge |
| `presets` | `presets_*` | hand-picked presets of one scene family |
| `long_history` | `pre6`, `pre4`, `on_rc03_pre4` | the same experiments re-made with a longer recorded history (5 s / 4 s); replace the older batches |
| `shared_policies` | `r4_shared` | the same few policies in every history (rc01, rc03) |
| `all_worlds` | `r5_worlds` | each policy in every hidden world of its history (rc03) |
| `seeds` | `r6_seeds`, `r6_repeat`, `<batch>/repeats` | repeats with new seeds or shifted starts |
| `search` | `vsearch`, `vsearch_rear`, `vsearch_rc14rear` | Kent's main search batches |
| `lookalike` | `on_rc03`, `on_rc07`, `on_rc10` | rc19: benign look-alikes of other RCs |
| `derived_rc` | `rc02_gap`, `rc17_delay` | extra runs for the derived RCs rc02 and rc17 |
| `rerun` | `rerun_invalid` | reruns of INVALID runs |

## The 20 RCs

| RC | scene | engine | notes |
|---|---|---|---|
| RC01 | stop before a blocking van (street, Town01) | Victor | |
| RC02 | RC01 scenes where no policy reaches PASS | view of rc01 | derived |
| RC03 | braking fails, lateral escape remains (spun car) | Victor | `pre6` = 5 s history |
| RC04 | stopped car ahead, truck alongside, follower | Victor | `pre6` |
| RC05 | abort a lane change | Victor | `pre6` |
| RC06 | broken-down car ahead, passer alongside | Victor | `pre6` (165 of 199) |
| RC07 | tyre blowout, on-ramp | Kent | |
| RC08 | garbage truck | Kent | |
| RC09 | front/rear squeeze in a tunnel | Victor | `pre6` |
| RC10 | spinning lead car | Kent | |
| RC11 | spinning lead car (second variant) | Kent | |
| RC12 | spun car, many sites and road conditions | Kent | re-made with 4 s history (`pre4`) |
| RC13 | sidewalk pedestrians that may dart | Victor | `pre6` |
| RC14 | hidden motorbike | Kent | |
| RC15 | lane end / merge | Kent | short history (see limits) |
| RC16 | double-parked van | Kent | |
| RC17 | RC01 with a reaction delay | view of rc01 | derived, plus new runs |
| RC18 | the RC03 scene on bends in wet / heavy rain | Kent | 4 s history |
| RC19 | benign look-alikes of RC03 / RC07 / RC10 | Kent | |
| RC20 | RC04 scene, restricted vs full policy library | view of rc04 | derived |

Scene definitions (options, variations, hidden parameters): `docs/scenes/20RCs.md`. Grouping and what can be reused: `docs/scenes/RC_GROUPS.md`.

## Repository layout

| path | content |
|---|---|
| `results_search/` | **the dataset** (see its README). `<rc>/carla/<batch>/runs/<run>/` is one run; `<rc>/search/<batch>/` the candidate files; `summary/` the index |
| `docs/` | all documentation, see `docs/README.md`: `RUN_SCHEMA.md` (run format), `report.md` (plain-language summary), `handoff/` (Fred's requests and our answers), `scenes/` (the 20 scene definitions), `extending/` (add a new RC), `kent/` (Kent's own notes, kept for provenance) |
| `tools/` | the converter and checks (`unify_runs.py`, `check_all.py`, `index_runs.py`, `delivery_status.py`, `make_derived.py`) and the batch builders |

**Only needed to reproduce or extend runs (not to use the data):**

| path | content |
|---|---|
| `rcx/`, `rc01/` | Victor's CARLA engine: scenes, scripted actor laws, policies, controller, evidence writer (RC01, 03, 04, 05, 06, 09, 13) |
| `carla_rc/` + `RC_scenarios_HighwayEnv_CARLA.ipynb` | Kent's CARLA engine (RC07, 08, 10, 11, 12, 14, 15, 16, 18, 19). The notebook is not run in HighwayEnv: its code cells (actor laws, controllers) are loaded at run time by `carla_rc/teachers/options.py` |
| `search/` | surrogate simulators and the iCEM search that propose candidates (`cem.py`, `cases.py`, `kent_cases.py`, ...) |
| `results_v3/`, `run_v2.py` | CARLA calibration files the surrogates load, and the legacy driver that made them |
| `results_free/` | RC04 free-form policy pilot (separate from the dataset) |

## Reproducing runs

Needs CARLA 0.9.15 (off-screen rendering works with NVIDIA; `-nullrhi` does not render) and a Python 3.10 environment with `carla`, `numpy`, `gymnasium`, `shapely`,
`py_trees` and `highway-env` (the last one only for Kent's engine), plus ScenarioRunner v0.9.15 for Kent's engine. Some Kent RCs need the CARLA AdditionalMaps (Town06, Town07).
There is no install step. The Slurm scripts are specific to a private cluster and are **not in the repository**; they only (1) start a CARLA server and wait until a client
can connect, (2) set `RC_SUBSTEP=0.002 RC_BRAKE_SCALE=3.0 RC_BRAKE_CAP_MAX=0.85`, (3) call one of the runners below once per shard, restarting the server if it grows too big.

```bash
# Victor's engine: candidates in results_search/<rc>/search/<batch>/candidates.json -> results_search/<rc>/carla/<batch>/
python tools/verify_carla.py --case rc05 --batch pre6 --port 2000 --shard 0 --nshards 4
# Kent's engine: candidates in results_search/<rc>/carla/<batch>/selected.json
RC_PREFIX_T=4.0 python carla_rc/teachers/carla_verify.py run --rc rc18 --batch vsearch --port 2000 --shard 0 --of 4
# then bring the new runs to the common format and rebuild the tables
python tools/unify_runs.py && python tools/make_derived.py && python tools/index_runs.py && python tools/delivery_status.py && python tools/check_all.py
```

`RC_PREFIX_T` (Kent's engine) sets the recorded time before the cue; the default is 1 s. Victor's engine takes it from `preroll_s` in the scene parameters
(6.0 records 5.0 s). A shard that hangs: remove its error lines from `results_shard*.jsonl` and run it again; finished candidates are skipped.
Adding a new RC: `docs/extending/NEW_RC_CHECKLIST.md`.

## Conventions
- All files, comments and logs are in English.
- Per-tick files of every run are gzipped (`ego_observable.csv.gz`, `ground_truth.csv.gz`, `decisions.jsonl.gz`); videos (`run.mp4`), pickles and logs are not part of the repository.
- INVALID runs are ignored for labels and for the surrogate's false-safe rate.
