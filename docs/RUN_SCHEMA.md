# Per-run evidence schema (`rcx-run-1`)

## One format for all 20 RCs (read this first)

Run folders come from two engines: Victor's (`rcx/`: rc01, rc03, rc04, rc05, rc06, rc09, rc13) and Kent's (`carla_rc/teachers/`: rc07, rc08, rc10, rc11, rc12, rc14, rc15, rc16, rc19). Both write `rcx-run-1`. `tools/unify_runs.py` brings every folder to the same form (it is idempotent and never changes a label); `tools/check_all.py` verifies it (prints `FORMAT OK`). What is common to every run folder:

- **Files:** `summary.json` (plain) and `ego_observable.csv.gz`, `ground_truth.csv.gz`, `decisions.jsonl.gz`. Read them with `pandas.read_csv("...csv.gz")` / `gzip.open(..., "rt")` or `tools/kent/runs_io.py` (opens gzipped or plain). No video is part of a delivery.
- **Angles:** every angle column of the CSVs (`ego_yaw_rel`, `seen_*_yaw_rel`, `actor_*_yaw_rel`, `ego_psi`) is in **degrees**, positive = nose to the right (toward +t). Angular rates (`yaw_rate`, `r_req`, `obs_ego_yaw_rate`) and the angles inside the per-RC `obs_*` vectors of Kent's RCs stay in rad (rad/s); `summary.json: units` says so.
- **`seen_<actor>_rel_{s,t,vs,vt}`, `seen_<actor>_yaw_rel`, `seen_<actor>_{length,width}`, `seen_<actor>_visible`:** the same names in all RCs (Kent's engine wrote `seen_<actor>_{s,t,vs,vt}`; renamed).
- **Clocks:** `t_since_cue` is the common clock (empty before the decision point = the cue). `sim_time` is the CARLA clock in Victor's runs and 0 at the end of the pre-roll in Kent's runs. Do not compare `sim_time` across RCs; use `t_since_cue`.
- **`summary.json` keys present in every run:** `schema`, `run_id`, `rc`, `label`, `reason`, `end_reason`, `family`, `candidate_kind`, `variation_id`, `scenario_params`, `policy_params`, `scene_seed`, `metrics`, `contact`, `scene_name`, `hidden_settings`, `scene` (`name`, `uid`, `site`, `split`, `history_id`, `hidden_world`, `hidden_params`), `constraints`, `constraints_pass`, `contact_detail`, `first_violated_constraint`, `history_s`, `short_history`, `units`, `pass_rule_id`, `pass_rule`, `files`, `unified`.
  - `history_s` = recorded time before the cue [s] (null in 467 runs of rc07, rc10, rc11, rc12, rc19, all PASS: benign companion scenes in which the hazard never appears, so no cue is ever delivered; there is no cue clock there). `short_history` = `history_s` < 3.0 s: those runs are superseded by a longer-pre-roll run where one exists (see `results_search/README.md`).
  - `scene.uid / site / split` are Kent's and null in Victor's runs; `scene.history_id` and `scene.hidden_world` group scenes that differ only in hidden settings (in Victor's runs computed from the scene parameters; in Kent's written by the pipeline).
- **`constraints`** is the same shape everywhere: `{name, kind, measured, required, op, unit, passed}` (+ `definition`, `reserve_m`). `kind` = `contact` | `clearance` | `limit` | `state`.
- **Pass rule (one rule, two threshold conventions):** **PASS iff every constraint passed** (`constraints_pass`); `label` is that, and INVALID runs have `constraints_pass` null. `pass_rule_id` says which convention a run uses: `victor-v1` = the raw limits in `constraints` (clearance 0.5 m, ...); `kent-v1` = a margin of at least 0.05 above each reserve (clearance reserve 0.5 m, so 0.55 m; for Kent's `measured` is that margin). The two clearance thresholds differ by 0.05 m, which is inside the declared noise band (0.03 to 0.05). A model trained on both should treat `pass_rule_id` as a categorical feature or use one RC family at a time; nothing was relabelled.
- **`decisions.jsonl`:** one record per policy decision: every tick (20 Hz) in Victor's runs, every 0.1 s (10 Hz) in Kent's runs.
- **Derived RCs** (no run folders of their own): rc02, rc17, rc20 are views over rc01 / rc04 runs (`results_search/rc02/members.json` ...). rc18: see `results_search/README.md`.

Every CARLA execution of a policy writes one folder `runs/<run_id>/` (written by `rcx/common.py:run_engine` + `rcx/evidence.py`, for every RC):

| file | contents | for the world model? |
|---|---|---|
| `summary.json` | configuration, labels, metrics (see below) | metadata only |
| `ego_observable.csv` | one row per tick: what the ego knows | **yes** (only this + `decisions.jsonl`) |
| `ground_truth.csv` | one row per tick: true state of every actor, scene measurements | **no** (hidden information; labelling / analysis) |
| `decisions.jsonl` | one JSON record per decision | yes |

## summary.json
`schema`, `run_id`, `rc` (e.g. RC03-01), `rc_case`, `variation_id` (scenario name from the search, e.g. `steer_only`), `candidate_kind` (best / boundary), `family`,
`scenario_params` (the varied scene parameters) and `scenario` (full scene parameters incl. defaults), `scene_seed`, `policy` (name, version, params) and `policy_params`,
`policy_source` (optimizer, search seed, pop, iters, robust cost of the iCEM run that produced the policy), `surrogate_prediction`, `calibration`,
`label` / `reason` / `end_reason` (CARLA verdict, reference only: final recovery-profile labels are produced downstream), `metrics`, `times`, `contact` (frames, actors), `evidence_meta`, `files`.

### Constraint block, scene name and hidden settings (added fields)
- `scene_name`: scene family, separate from the RC number: `street_van` (rc01), `spun_car` (rc03), `stopped_car_truck_alongside` (rc04), `lane_change_abort` (rc05), `broken_car_passer` (rc06), `tunnel_squeeze` (rc09), `sidewalk_pedestrian_dart` (rc13). `variation_id` is the scene variation inside it.
- `hidden_settings`: names of the scene parameters (keys of `scenario`) that are not observable in the recorded history at the decision point. Declared per case from `docs/scenes/20RCs.md` ("Hidden at the trigger"): rc01 none; rc03 crash, intrude, psi_rest, T_slide, lead_brake, lead_react; rc04 and rc06 side_acc, side_react, fol_headway, fol_react; rc05 rear_acc, rear_vmax; rc09 rear_delay_s, rear_decel; rc13 dart_speed, dart_dist.
- `constraints`: every check the CARLA judge applied, as a list of `{name, kind, measured, required, op, unit, passed}`. `kind` is `contact` (frames in contact, required 0), `clearance` (distance in m), `limit` (filtered acceleration against the physics envelope, m/s2: forward 0.5 g, braking 1 g, lateral 1 g, planar 1 g) or `state` (yes/no end checks such as settled, stopped, not closing). `op` compares `measured` with `required`. `constraints_pass` is true when every listed constraint passed; it is null for INVALID or UNRESOLVED runs, whose `constraints` is null.
- `contact_detail` (R9, separate from the margin; null when there was no contact): `frame`, `time_s`, `t_since_cue_s`, `actor` (role of the first actor hit), `source` (`sensor` = CARLA collision sensor, `footprint` = footprint overlap with a scripted kinematic actor), `rel_speed_mps` (ego speed relative to that actor in the lane frame, at the last tick before the first contact frame), `normal_impulse_Ns` (collision-sensor impulse summed over the first contact frame; **null for `footprint` contacts, because scripted actors (for example the spun car in rc03) do not report an impulse**), `n_contact_frames`. Runs recorded before this field existed (the original batches) carry `backfilled: true`: computed from `ego_observable.csv` + `ground_truth.csv`, `normal_impulse_Ns` always null. INVALID runs have no `contact_detail` (their rows are not evaluated).
- `first_violated_constraint` (R9; null when every constraint passed): `{name, time_s, t_since_cue_s, dated}`. Dated for `no_contact` (first contact frame) and for the four acceleration limits (first tick whose 0.2 s mean exceeds the limit); the earliest dated one is given. Clearance and end-state checks (settled, stopped, not closing, ...) are not dated per tick: if only those failed, `dated` is false and `time_s` is null.
- `request`, `src_batch` (only on runs made for a coverage request): `R4`, `R5` or `R6`, and the original batch a re-run was copied from (`pre6` batches).
- The block is computed from the same recorded numbers as the label (`rcx/constraints.py`); `tools/backfill_constraints.py` checks that `constraints_pass` agrees with the label for every run (PASS if and only if all constraints passed). Some checks are only decisive when there is no contact (clearances, settled, not closing, stopped): a run that ends in a contact fails on `no_contact` first.

## Units, signs and reference points
| quantity | unit / sign / reference |
|---|---|
| time (`sim_time`, `t_since_cue`) | seconds; tick 0.05 s; `t_since_cue` is empty before the decision point (the tick at which the policy is first told about the hazard) |
| `scene_seed` | seed of the scene's random generator (`seed` in the scene parameters, default 7). Only rc01 draws random numbers (placement of parked cars, props and walkers); rc03/rc04/rc06 are fully scripted, so a new seed changes nothing there |
| `preroll_s` (scene parameter) | time from the start of the scene to the cue, including `warmup_s` = 1.0 s that is not recorded. Recorded time before the cue = `preroll_s` - 1.0 s. The cue time itself does not move when `preroll_s` changes |
| `ego_s`, `ego_t` | metres in the scene lane frame: s forward along the road, t lateral, positive to the right; ego lane centre t = 0 (rc03/04/06: the escape lane is at t = -side * lane_w) |
| `ego_yaw_rel`, `seen_*_yaw_rel`, `actor_*_yaw_rel` | **degrees**, wrapped to [-180, 180]: CARLA yaw minus the road heading. **Positive = nose turned to the right of the road direction (toward positive `t`).** Checked on 120 rc03 runs (9754 ticks, speed > 5 m/s, |yaw| < 10): d(ego_t)/dt = 0.35 m/s per degree, correlation 0.94 (18 m/s x sin 1 deg = 0.31) |
| `speed`, `accel_*` | m/s and m/s2; `accel_long` positive forward, `accel_lat` positive to the ego's right; `*_f` = 0.2 s trailing mean |
| `a_req`, `a_req_clipped` | requested longitudinal acceleration in m/s2, negative = braking |
| `seen_<actor>_rel_*` | the other actor relative to the ego: `rel_s` forward, `rel_t` right, `rel_vs`/`rel_vt` relative velocities (m/s), `yaw_rel` degrees, `length`/`width` m. Reference point of the position: see the open question in the hand-off notes (the offset to the true centre distance is a few cm) |
| `*_clear` (ground truth) | footprint-to-footprint distance in metres between the ego and that actor (rotated rectangles); 0 at contact |
| `throttle`, `brake`, `steer`, `hand_brake` | CARLA vehicle control values as applied |

## ego_observable.csv (per tick, dt = 0.05 s)
- time: `frame`, `sim_time`, `t_since_cue` (empty before the cue).
- ego state (own sensing): `ego_s`, `ego_t` (lane frame; t positive to the right), `ego_yaw_rel`, `speed`, `accel_long`, `accel_lat`, `*_f` (0.2 s mean), `accel_planar_f`, `contact` (collision sensor bit).
- policy view: `obs_*` = the exact observation dict the policy received this tick (e.g. cue, hazard).
- perception: `seen_<actor>_visible` (0/1) and, when visible, `seen_<actor>_{rel_s,rel_t,rel_vs,rel_vt,yaw_rel,length,width}` (ego-relative). Visibility rule (provisional): euclidean distance <= 80 m AND the line of sight from the ego centre to the actor centre is not blocked by another tracked actor footprint. Static map geometry (buildings) is not modelled. Hidden (invisible) actors have empty cells.
- controls: requested `a_req`, `a_req_clipped`, `t_des`, `phase`; applied `throttle`, `brake`, `steer`, `hand_brake`.

## ground_truth.csv (per tick)
`frame`, `sim_time`, `contact_actor`, per actor `actor_<name>_{s,t,yaw_rel,vs,vt,clear,length,width}` (lane-frame centre, velocity components, footprint distance to the ego),
and every scene-specific measurement (clearances, front/rear s of actors, ...). Hidden scene parameters (e.g. RC03 `intrude`, `psi_rest`) are in `summary.json: scenario`.

## decisions.jsonl (one record per tick)
`frame`, `query_time`, `t_since_cue`, `observation` (what the policy was given), `observation_history_frames` (the previous 20 frames: look up their rows in `ego_observable.csv`),
`policy_output` (phase, a_req, t_des, t_rate, lane_keep, info), `controller_state` (integrator / brake-frame counter / throttle memory / accel history of the low-level controller),
`applied_command`, `pending_commands` (commands issued during the last `delay_frames` ticks of the actuator delay window, i.e. possibly not yet effective).

## Notes
- Names of actors are the scene roles (`victim`, `esc_lead`, `esc_follow`, `rear`, ...); duplicates get a numeric suffix.
- No preprocessing, recovery-profile labelling or splitting is done here.
- The same files are written for RC01 / RC05 / RC09 / RC13 / RC03 because they share `run_engine`.
