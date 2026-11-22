# What Victor and Kent did: a short report (optional reading)

You do not need this file to use the data (see `README.md` for that). It is a plain-language summary of **what was done, how, how much, what we found, and what we hope the world model does with it.**
Numbers are counted from `results_search/summary/carla_runs.json` (24 715 run folders) and `results_search/DELIVERY_STATUS.md`; "current" means without the batches a later batch replaces.

---

## 1. The idea in five lines

- A **Recovery Condition (RC)** is a hazard story, for example "the car ahead spins and braking alone will not stop us in time, but a swerve might" (RC03).
- For each RC there are several **scene variations** (speeds, gaps, road, weather, hidden facts such as how hard the lead car brakes) and several **recovery policies** (brake, steer left or right, stage a brake then a swerve, wait and overtake, ...).
- We ran many (scene, policy) pairs in **CARLA 0.9.15** and recorded each run as a folder of per-tick files plus a label **PASS / FAIL / INVALID**.
- PASS means every safety constraint held (no contact, enough clearance, acceleration within limits, ego settled). FAIL means one did not. INVALID means the scene itself was not set up as declared (leave it out).
- The goal: a **world model** that, given what the ego car has seen up to the cue and a policy, predicts what happens next, so that a planner can tell good recoveries from bad ones without running CARLA each time.

## 2. Who built what

| | Victor | Kent |
|---|---|---|
| RCs | rc01, 03, 04, 05, 06, 09, 13 | rc07, 08, 10, 11, 12, 14, 15, 16, 18, 19 |
| Engine (code) | `rcx/`, `rc01/`; runner `tools/verify_carla.py` | `carla_rc/`; runner `carla_rc/teachers/carla_verify.py` (needs ScenarioRunner) |
| Scenes | few, hand-built, one town each (Town01, Town03, Town04) | many sites and towns, loaded from variation files (`uid`, `site`, `split`) |
| Style | scripted actors, deep history (5 s recorded; rc01 9.3 s) | broad coverage, many policies per scene, history 3 to 4.5 s |
| Pass rule id | `victor-v1` (raw limits, clearance mostly 0.5 m) | `kent-v1` (clearance 0.55 m) |
| Video | yes (`run.mp4`, not delivered) | no camera |

Derived RCs (no runs of their own): **rc02** (rc01 scenes where no policy works), **rc17** (rc01 with a reaction delay), **rc20** (rc04 with a restricted policy library).

## 3. How much data

Total: **24 715 run folders** (PASS 11 266, FAIL 13 341, INVALID 108). Without superseded batches (the usable set): about **21 500 labelled runs** (PASS or FAIL).

| RC | scene | current runs | PASS / FAIL | variations* | recorded pre-cue |
|---|---|---|---|---|---|
| rc01 | stop before a blocking van | 368 | 246 / 122 | 61 | 9.3 s |
| rc03 | braking fails, swerve remains | 386 | 133 / 253 | 39 | 5.0 s |
| rc04 | stopped car, truck alongside | 185 | 60 / 125 | 43 | 5.0 s |
| rc05 | abort a lane change | 136 | 63 / 73 | 28 | 5.0 s |
| rc06 | broken-down car, passer alongside | 165 | 96 / 69 | 40 | 5.0 s |
| rc07 | tyre blowout on a ramp | 2352 | 1818 / 534 | 160 | 3.05 s |
| rc08 | garbage truck | 1736 | 981 / 755 | 120 | 3.05 s |
| rc09 | squeeze in a tunnel | 162 | 89 / 73 | 29 | 5.0 s |
| rc10 | spinning lead car | 3176 | 1278 / 1898 | 218 | 3.05 s |
| rc11 | spinning lead car, variant | 2974 | 1019 / 1955 | 202 | 3.05 s |
| rc12 | spun car, many sites and road conditions | 1748 | 274 / 1474 | 168 | 4.45 s |
| rc13 | pedestrians who may dart | 180 | 111 / 69 | 45 | 5.0 s |
| rc14 | hidden motorbike | 3265 | 1611 / 1654 | 184 | 3.95 s |
| rc15 | lane end / merge | 2451 | 1609 / 842 | 120 | 1.95 s (short) |
| rc16 | double-parked van | 539 | 403 / 136 | 40 | 5.05 s |
| rc18 | spun car on bends, wet / heavy rain | 216 | 29 / 187 | 21 | 4.45 s |
| rc19 | benign look-alikes of rc03 / 07 / 10 | 1435 | 525 / 910 | 140 | 3.05 s (rc03 part 4.45 s) |

\* A *variation* is one scene: Kent's `uid`; for Victor's RCs, the pair (history id, hidden world). The two are comparable, not identical definitions.
INVALID runs are not counted in the table. About **2 300 runs were newly made in the last round** (rc12 and rc19 re-made at 4 s of history).

**Reading the table:** Kent's RCs have many scenes and many runs, Victor's have few scenes but long histories. A scene appears with many policies, so the number of *independent* situations is much smaller than the number of runs.

## 4. How we searched (the pipeline)

1. **Define the RC** in `docs/scenes/20RCs.md`: the story, the options the ego has, the variations (with ranges) and what is hidden at the cue.
2. **Surrogate simulator** (`search/*_sim.py`, `plant.py`, `families.py`): a fast, simplified simulation of the same scene. It is *only* a proposal engine.
3. **Search** (`search/cem.py`, an iCEM search; `search/cases.py`, `kent_cases.py`): for each scene it looks for policy parameters that are expected to recover, and for settings near the pass / fail edge.
4. **Candidates**: each candidate has a `kind`:
   - `best` (the search's chosen policy; 9 183 current runs),
   - `boundary` (settings next to the PASS / FAIL edge; 5 609),
   - `shared` (a small fixed policy set run in every scene, so scenes can be compared; 6 135),
   - `ref` (reference policies; 653).
5. **CARLA verification**: every candidate is replayed in CARLA with the real physics; **the label always comes from CARLA**, never from the surrogate.
6. **Batches** (`baseline`, `boundary_r*`, `presets_*`, `r4_shared`, `r5_worlds`, `r6_seeds`, `pre6` / `pre4`, `vsearch*`): each round of this loop is one batch. Later batches may replace earlier ones (`superseded` in `results_search/rc_status.json`).
7. **Unify and check** (`tools/unify_runs.py`, `check_all.py`, `index_runs.py`, `delivery_status.py`): both engines are brought to one run format, indexed, and checked.

Policy families seen in the data (current runs, top ones): brake, left, right, brake_free, merge_back, keep, stop_end, memory_left, merge_front, watch_merge, staged / two_stage / surge_brake / reachable_set / pre_slow (Victor), lane_change.

## 5. What we found

1. **CARLA disagrees with the surrogate often enough to matter.** Counting runs where the surrogate gave a plain PASS or FAIL verdict (not "uncertain" or per-world):
   - Victor's RCs: surrogate said PASS 703 times, CARLA said FAIL in 104 (**about 15 % false-safe**); surrogate said FAIL 799 times, CARLA said PASS in 153 (about 19 %).
   - Kent's RCs: PASS predicted 1 734 times, 113 were FAIL in CARLA (**about 6.5 %**); FAIL predicted 2 958 times, 32 were PASS (about 1 %).
   This is why every label is re-measured in CARLA, and why a learned world model that replaces the surrogate is worth building.
2. **Some RCs are fully scripted** (rc03, rc04, rc06 draw no random numbers). Re-running with a new seed changes nothing, so "more seeds near the boundary" is meaningless there; the real variety is in the scene and the hidden settings.
3. **The same policy can pass in one hidden world and fail in another.** That is the point of the shared policy runs (`r4_shared`, `r5_worlds`): the history looks identical, the hidden part differs, and the outcome differs.
4. **Reaction delay matters** (rc17): for delays up to about 0.6 s most runs still pass; at 0.9 s and above almost all fail (counts per delay are in `results_search/rc17/`).
5. **Longer history was possible for most RCs, not all.** 5 s (Victor) and 4 s (rc12, rc18, rc19) were re-made. rc13 and rc06 lose some scenes when shifted to a longer pre-roll (63 INVALID, 34 unspawnable); rc15's geometry only allows about 2 s.
6. **Infrastructure findings** (useful if you re-run): off-screen rendering needs an NVIDIA GPU; large towns (Town13) do not load in time on the smaller GPU nodes; the CARLA server must be restarted every so often during long batches.

## 6. Limits you should know about

- **History length differs** between RCs (about 2 s to 9 s). Every run says its own length in `summary.json: history_s`; `short_history` is true below 3 s (all of rc15).
- **Two pass thresholds** (Victor: raw limits, mostly 0.5 m; Kent: 0.55 m clearance). Use `pass_rule_id`, or recompute from the `constraints` block.
- **Class imbalance:** rc12, rc18, rc19 are mostly FAIL; rc07, rc15, rc16 mostly PASS.
- **Victor's RCs have few scenes** (28 to 61 each): easy to overfit. Split by scene, not by run.
- **1 183 runs have no cue clock** (the policy never triggered); use `sim_time` for those.
- **No video** for Kent's RCs; videos are not part of the delivery for anyone.
- **Not done:** the extra coverage requests `refine_boundary`, `vary_alone`, `search_harder_settings` (they need new scenes or a new search); rc20's staged-only scene (3 scenes unresolved). Reasons: `docs/handoff/PIPELINE_HANDOFF_REPLY.md`.

## 7. What we hope the world model does with the data

**Inputs** (only these): `ego_observable.csv` and `decisions.jsonl`: what the ego state and its sensors saw before and after the cue, and the policy's actions. **Never** `ground_truth.csv`, `hidden_settings` or any `surrogate` field as input (they are for analysis).

**Suggested uses, in order of ambition:**
1. **Outcome prediction.** Given the history up to the cue and a policy, predict PASS / FAIL and the margin (how close to the limit). Train and test split by **scene**, not by run.
2. **Rollout prediction.** Predict the next ego and actor states under a policy, and check the predicted trajectory against the same constraints as CARLA (clearance, acceleration, settle).
3. **Uncertainty over hidden facts.** The history does not reveal the hidden settings (e.g. how the lead car brakes). A good model should give a spread of outcomes, and be *cautious* where the hidden world could flip PASS to FAIL. The shared-policy batches are the test for that.
4. **Surrogate replacement.** Use the model as the fast proposal engine in place of the iCEM surrogate, then confirm in CARLA. Success measure: a lower false-safe rate than the figures in section 5.
5. **Transfer.** Train on some RCs and test on a held-out RC (rc19's benign look-alikes are a natural negative test: scenes that look like a hazard but are fine).

**Practical tips for training:** use only `current` batches; drop INVALID; weight or resample the minority class per RC; pad or cut history to a common length or mask it; keep `pass_rule_id` as a feature or compare labels by recomputing from `constraints`.

**What we would like back from the world-model side:** which RCs are the hardest to predict, where it is most over-confident, and which scenes or policies you want more of. The cheapest extra data is more *scenes* for Victor's RCs; more runs of the same scene add little.

---

*Where to go next:* `README.md` (overview and layout) → `results_search/DELIVERY_STATUS.md` (counts) → `docs/RUN_SCHEMA.md` (files and units) → `docs/handoff/PIPELINE_HANDOFF_REPLY.md` (answers to the R and Q list) → `docs/scenes/20RCs.md` (scene definitions).
