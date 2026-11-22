# Reply to docs/handoff/PIPELINE_HANDOFF.md (Victor and Kent), 2026-11-21

Answers to section 5 (R1 to R9), section 6 (Q1 to Q7, Q15) and the coverage requests. Checked against the code and the runs in `results_search/`; "measured" means run on the data, "from code" means read from the code. Nothing is left open for Kent or Victor: the decisions that were open (one pass rule, scene identity, schedule) are made below. What is on disk right now: `results_search/DELIVERY_STATUS.md` (`python tools/delivery_status.py`).



## What was delivered

**All 20 RCs, in one run format** (`rcx-run-1`, `docs/RUN_SCHEMA.md`): 17 RCs with CARLA runs (rc01, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12, 13, 14, 15, 16, 18, 19) and 3 derived views (rc02 and rc17 from rc01, rc20 from rc04). Victor's engine (`rcx/`) made
rc01, 03, 04, 05, 06, 09, 13; Kent's engine (`carla_rc/`) made rc07, 08, 10, 11, 12, 14, 15, 16, 18, 19. `tools/unify_runs.py` brought both to the same files and fields (per-tick files gzipped; angles in degrees; constraint block, scene,
hidden settings, history, units and pass rule in `summary.json`); `tools/check_all.py` checks every run folder against that format. Totals and per-RC counts: `results_search/DELIVERY_STATUS.md`. Videos and `.pkl` files are not part of the delivery.

**Pass rule (Q7, decided).** A run passes if and only if every constraint in `summary.json: constraints` passed. The two engines use different clearance thresholds and neither was changed: `pass_rule_id` is `victor-v1` (raw limits, clearance 0.5 m)
or `kent-v1` (0.05 above the reserve, clearance 0.55 m). Each run carries `measured` and `required` for every constraint, so you can apply one threshold to all of them.

## Section 5: what a run folder carries

| ID | State | Where / how |
|---|---|---|
| R1 constraint block | **done** | `summary.json: constraints` (name, kind, measured, required, op, unit, passed) and `constraints_pass`. Code `rcx/constraints.py`; existing runs filled by `tools/backfill_constraints.py`. Measured: `constraints_pass` is true exactly for PASS, false exactly for FAIL, null for INVALID, on every run. It comes from the same numbers as the label, so it is a consistency check, not an independent measurement |
| R2 hidden settings | **done (declared)** | `summary.json: hidden_settings` from `docs/scenes/20RCs.md` "Hidden at the trigger", with the implementation's names: rc01 none; rc03 crash, intrude, psi_rest, T_slide, lead_brake, lead_react; rc04 and rc06 side_acc, side_react, fol_headway, fol_react; rc05 rear_acc, rear_vmax; rc09 rear_delay_s, rear_decel; rc13 dart_speed, dart_dist. Your measured rc03 list (intrude, lead_brake, crash) is a subset; the other three never vary alone in the data, so they are untested rather than visible |
| R3 scene name | **done** | `summary.json: scene_name`, `variation_id`, and `scene{name, uid, site, split, history_id, hidden_world, hidden_params}` for every run. `uid`, `site` and `split` come from Kent's variation files and are filled for Kent's RCs; they are null for Victor's RCs (their scenes are the classes in `rcx/scenarios.py`, and `scene_name` plus `history_id` are the grouping keys) |
| R4 shared policy set | **done** | batches `rc03/r4_shared` (117 runs: your 3 shared policies in every history and every hidden world) and `rc01/r4_shared` (71 runs). Your list says 81 (rc03) and 66 (rc01): rc01 is within 5; rc03 is larger because I run each shared policy in every hidden world of every history, not only once per history |
| R5 each policy in every hidden world | **done** | `rc03/r5_worlds`: 134 runs, the same number as in `coverage_requests.json`. Each is a policy that ran in at least one world of a history, run in the worlds it was missing. Built by `tools/make_requests.py` from the policy identity (family + parameters, D10) and the visible/hidden split of D3 |
| R6 more seeds near boundaries | **partly, and one finding** | `rc01/r6_seeds`: runs with margin within 0.05 of zero, three new seeds each (11, 13, 17). **rc03, rc04 and rc06 are fully scripted: they draw no random numbers, so a new `seed` changes nothing there.** For rc03 I run `rc03/r6_repeat` (the 8 runs closest to margin 0, three seeds each) as a run-to-run noise measurement instead. Your seed requests for RC03 (87 runs in `coverage_requests.json`) are therefore not run as seeds; the noise band for those cases can only be measured with this repeat, or by varying something real |
| R7 whole pre-roll | **done, with documented limits** | recorded time before the cue is `history_s` (and `short_history` below 3 s). rc01 about 9.3 s; rc03, rc04, rc05, rc06, rc09, rc13: `pre6` batches (5.0 s recorded, measured; the cue time does not move); rc12 and rc19: `pre4` batches (4.0 s, `RC_PREFIX_T=4`); rc18 4.45 s; rc07, rc08, rc10, rc11, rc14, rc16 median 3.05 to 5.05 s (none below 3 s). **Limits:** rc06 `pre6` covers 165 of 199 scenes (`rc06/carla/pre6/not_spawnable.json`: the follower would start before the road); rc13 `pre6` has 63 INVALID runs (the shifted scene does not fit the road); rc15 stays short (about 2 s): the scene geometry allows no more. rc19 `on_rc03` was re-made as `on_rc03_pre4` (4 s) and rc12 as `pre4`; the Town13 sites were not re-run (Town13 does not load in time on the GPU nodes) and rc12 has no Town13 site in its current batch. Old short batches are marked `superseded` in `results_search/rc_status.json` |
| R8 RUN_SCHEMA.md | **done** | `docs/RUN_SCHEMA.md`. The `ego_yaw_rel` sign is now settled: **degrees, positive = nose turned to the right of the road direction (toward positive `t`)**. Measured on 120 rc03 runs (9754 ticks): d(ego_t)/dt = 0.35 m/s per degree, correlation 0.94 |
| R9 contact severity | **done for new runs, backfilled for old ones** | `summary.json: contact_detail` (time, time since cue, actor, relative impact speed, collision impulse) and `first_violated_constraint` (name and time). **Limits:** the collision impulse exists only for contacts reported by the CARLA collision sensor; the spun car in rc03 is a scripted kinematic actor and its contacts are footprint overlaps, so `normal_impulse_Ns` is null there. The 1206 earlier runs carry `contact_detail` with `backfilled: true` (relative speed from the recorded rows, no impulse). `first_violated_constraint` is dated only for contact and the acceleration limits; clearance and end-state checks have no per-tick time (`dated: false`) |

## Section 6: questions

**Q1. Reference point of `seen_*_rel_s`.** `rel_s` = footprint-centroid s of the other actor minus footprint-centroid s of the ego. The centroid is the mean of the 8 bounding-box vertices (`fp_local` in `rcx/common.py`, used by `rcx/evidence.py`), the bounding-box centre. `ego_s` in the CSV is the CARLA actor origin. The origin is not at the bounding-box centre, so the few-cm offset you see (about 8 cm in rc03, 3 cm in rc01) is most likely this. From code, not measured. `ground_truth.csv actor_*_s` is the same footprint centroid as `rel_s`.

**Q2. `seen_*` and `obs_*`.** Yes, both intended. `seen_*` = line of sight: centre distance at most 80 m (`VIS_RANGE`) and the centre-to-centre segment is not blocked by another tracked actor's footprint; static map geometry is not modelled. `obs_*` = the observation dict the policy is given. Measured on all 161 rc01 runs: 68 `seen_*_visible` columns, **24** never visible (you counted 19; I cannot see which 5 differ, probably objects against columns).

**Q3. Thresholds** (from code: `rcx/scenarios.py`, `rcx/rc03_laws.py`, `rcx/rc04_laws.py`, `rc01/evaluate.py`, `rc01/config.py`; every one is also in `constraints` of each run):
- Physics envelope: not one combined 1 g. 0.2 s trailing mean of the measured acceleration: forward 0.5 g, braking 1 g, lateral 1 g, planar 1 g, each checked separately.
- Ego settled (rc03/04/06): stopped (speed < 0.3 m/s), or over the last 10 ticks (0.5 s) |lateral offset| < `settle_tol` = 0.6 m from the start-lane centre or the escape-lane centre. **Heading is not checked** (your assumed 0.06 rad over 2 s does not exist). rc05: last 20 ticks (1 s), within 0.5 m of a lane centre (not half a lane width).
- Still closing (rc03/04/06, last tick): speed > 0.3 m/s, lateral overlap (gap after half widths < 0.3 m), gap > 0 and gap / closing speed < 2.0 s (`still_closing`, `rear_closing`). For a car behind (`esc_follow`, `rear`, `fol`) the same with its closing speed.
- Left the road (rc03/04/06): largest |lateral offset| after the cue > 1.5 lane widths. rc05: left edge beyond lane_w + 1.75 m or right edge beyond 1.75 m.
- Minimum clearance: rc03/04/06/09 0.5 m; rc05 rear-left 1.0 m and lead 2.0 m; rc01 2.0 m during the hold (hold = speed < 0.1 m/s for 2 s); rc09 stop = speed < 0.1 m/s at the end.
- rc13: pedestrian clearance 0.5 m (only when the pedestrian enters the lane); unnecessary slowing = speed at the pass < 0.9 of the target, or a stop when the pedestrian never entered.
The four rc03 runs that fail only on "still closing" now have measured and required values in `constraints`.

**Q4. Scene and policy identity: yes.** A scene is `scenario_params`, a policy is family + `policy_params`. Measured: 18 of 1173 distinct (case, family, policy parameters, scene parameters) occur in more than one batch (the earlier note said 9, counted differently). `scene_seed` is 7 for all of them, so they are the same experiment twice; merge them as proposed. They are also a free check on CARLA determinism: compare their margins.

**Q5. Schedule.** Nothing is left to schedule: all 20 RCs exist (see above). Not recoverable: the 5 INVALID rc01 runs ("van moved") re-ran as INVALID (`rc01/rerun_invalid`); `rc01/r4_shared` has 5 more and `rc01/r6_seeds` 6 INVALID runs; rc13 `pre6` has 63 INVALID runs and rc09 and rc05 a few: INVALID runs have no label, exclude them. RC10 and RC14 (the history-dependent cases) are built (Kent's engine).

**Q6. Which scenes do the next deliveries use? (decided)** Both engines stay: each RC has the scenes of the engine that made it. `scene_name` and `scene.history_id` identify a scene in every run; Kent's RCs also carry `uid`, `site` and `split`. rc01 is Victor's street scene; Kent's roadworks-corridor version was not built, so there is one RC01.

**Q7. One pass rule. (decided)** Every constraint must pass; thresholds are the ones in each run's `constraints`, and `pass_rule_id` names the engine (`victor-v1`: raw limits, clearance 0.5 m in most RCs, 2.0 m during the hold in rc01; `kent-v1`: 0.05 margin above the reserve, clearance 0.55 m). Labels are not recomputed; to apply one threshold to all runs, recompute from `measured` and `required`.

**Q15. Is the controller told about the hazard? Yes.** The policy's observation contains the cue: measured in one baseline run of every case, `obs_cue` goes from False to True exactly at the first row with `t_since_cue` (rc01 uses `obs_delivered`). `obs_hazard` does the same in rc03, rc04 and rc06; in rc05 `obs_hazard` is still False at the cue (the hazard is a separate event there). So `cue_delivered` can be a model input. The four times you ask for are not recorded as separate fields: `t_since_cue` marks only the delivery tick.

## Coverage requests not run, and why

| kind | requests | state |
|---|---|---|
| `refine_boundary` (169 runs) | settings between boundary neighbours | **not run.** None of them decides a profile (`decides_up_to` 0), and each needs a new scene value that has no search behind it; say so if you want them |
| `vary_alone` (5 runs) | one untested rc03 setting alone | **not run**, same reason. They need new scene pairs, and rc03 scenes at 6 s would first have to be rerun in full |
| `resolve` / `no_margin` (4 rc03) | threshold in no file | **no run needed**: Q3 and R1 give the thresholds |
| `resolve` / `invalid_run` | INVALID reruns | rc01: re-run, INVALID again (same reason); rc09 old format: not rerun (same overlap) |
| `rerun_in_new_format` RC05, RC09, RC13 | 111 runs | **already met** by this delivery |
| `search_harder_settings` (RC05, RC13, RC09) | no recovery boundary yet | not run: needs a new search, not a re-run |
| `record_telemetry` RC02, RC06, RC10, RC14, RC18 | label-only runs from Fred's own runner | not ours to run |
