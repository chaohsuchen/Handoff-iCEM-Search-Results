# Pipeline hand-off: what the dataset does, what each run must carry, and open items

Date: 2026-11-17, updated the same day after dataset version 2 was built. From: Fred (dataset). For: Kent (scenarios), Victor (policy search and CARLA runs), Yige (world model).

This page is the working agreement between the four stages. It says who does what, the words we use, the decisions
already made, what a run folder must contain, and the few things I cannot decide alone.

**How to respond.** Write under the `Answer:` line of an item and push to the branch `team-questions`, or comment on
its pull request with the item ID (for example `R3`). If you disagree with a decision in section 4, name its ID (for
example `D5`). Nothing here blocks me: every open item has a default that I use until you answer.

## 1. The pipeline

| Stage | Owner | Hands over |
| --- | --- | --- |
| Scenario generation | Kent | scene definitions and their variations, for all 20 RCs |
| Policy search and CARLA execution | Victor | one run folder per executed policy, with full per-tick telemetry |
| Dataset | Fred | validated runs, signed margins, recovery profiles, observation/action sequences, grouped splits, a coverage and quality report |
| World model | Yige | the model |

I work only from Victor's run folders. Anything from Kent that I need (scene IDs, splits, which settings are hidden)
has to travel inside those folders.

**What the model does** (Yige, 2026-11-15). It takes the observation history (ego motion, other actors' relative
positions and velocities, visibility, timestamps, past controls) plus the applied ego actions. It predicts how the
observed world evolves. Given a candidate-policy descriptor as well, it predicts that policy's signed recovery margin
from the current history. The margins of several policies from one history form a recovery profile. Hidden simulator
state and scene settings are for reference and audit, never model inputs.

## 2. Words

| Word | Meaning |
| --- | --- |
| Scene | one setting of every scene parameter (Victor's `variation_id`) |
| Run | one policy executed once in one scene |
| Decision point | the tick at which the policy is first told about the hazard |
| History | everything the ego observed and did before the decision point |
| Hidden setting | a scene parameter that does not change the history (for example how far a car will intrude later) |
| Hidden world | one value set of the hidden settings. Scenes that differ only in hidden settings are worlds of one history |
| Margin | one signed number per run: zero or more means every constraint was met with its required reserve |
| Recovery profile | per history, each tested policy with its worst margin over the hidden worlds and a status: supported, refuted or unresolved |

The reference for every rule is `docs/spec/Recoverability_Definitions_and_CARLA_Cases.pdf` ("the PDF").

## 3. What the dataset delivers

Version 2 is built: `data/wm_dataset_v2/`. Its card is `docs/dataset/WM_DATASET.md` (how to load it, what every
field means, what is missing). Its coverage and quality report is `docs/dataset/WM_COVERAGE_REPORT.md`, and the full
list of requests for more runs is `docs/dataset/coverage_requests.json`. The design is
`docs/superpowers/specs/2026-11-15-wm-dataset-v2-design.md`. Version 1 (`data/wm_dataset_v1/`, run and scene labels
only) is kept as it was.

| Yige's request | Where it is in version 2 | State |
| --- | --- | --- |
| Data validation | per run: `validity`, the list of failed `checks`, margins recomputed from `ground_truth.csv` | done for RC01 and RC03 |
| History alignment | per history: observations, applied actions, pending commands and tick length compared up to the decision point; `alignment` in each profile | done for RC01 and RC03 |
| Recovery profiles, with hidden worlds | `profiles.jsonl` | done for every case; hidden worlds for RC03 |
| Feature preprocessing | `sequences/*.npz` (observations, visibility, actions), `policy_descriptor`, `margin_signed` | done for RC01 and RC03 |
| Grouped splits | `split` (one history together), `split_strict` (one base scenario together) | done; see D9 |
| Coverage analysis | `docs/dataset/WM_COVERAGE_REPORT.md`: boundaries, histories with no contrast, missing runs, requests for more evidence | done |
| Quality report | same document, with figures; `feature_spec.json` | done |

**What I received on 2026-11-17** (format `rcx-run-1`):

| | RC01 | RC03 |
| --- | --- | --- |
| Scene | a van blocks a street between parked cars (Town01) | a car is hit and spins into the ego lane (Town04) |
| Scenes / runs | 35 / 161 | 43 / 111 |
| PASS / FAIL / INVALID | 106 / 50 / 5 | 52 / 59 / 0 |
| Policies per scene | 2 to 6 | 1 to 6 |
| Recorded before the cue | about 9 s | 0.5 s |
| Scene seeds / repeats | one (7) / none | one (7) / none |

All 272 runs load. My recomputed margin agrees in sign with the label on every valid run. That shows the records are
consistent with each other; it is not an independent check of the labels.

## 4. Decisions

Each one follows from the PDF or from Yige's brief. Tell me if one is wrong.

| ID | Decision | Source |
| --- | --- | --- |
| D1 | Model inputs come only from `ego_observable.csv`: ego motion, the `seen_*` actors with their visibility flags, and applied controls. `ground_truth.csv`, `obs_*`, `phase`, requested controls and `decisions.jsonl` are reference only. | Yige; PDF section 1 |
| D2 | The decision point is the tick at which the policy is first told (the cue plus the delivery delay). | PDF section 1: an observation delivered late is not available earlier |
| D3 | A setting is hidden when scenes that differ only in it could not be told apart in the recorded history, within the tolerances. I measure this from the runs. RC03: `intrude`, `lead_brake` and `crash` are hidden (difference under 1 cm); `d0` and `esc_gap` are visible; the other RC03 settings never vary alone, so they are untested and treated as visible. RC01: `gap`, `v_ego` and `delay_s` are all visible. The RC03 evidence is thin: the recorded history is 0.5 s, `intrude` rests on 36 scene pairs, `lead_brake` on 2 and `crash` on 1. | PDF sections 1 and 2.4; matches Kent's "hidden at the trigger" list for RC03 |
| D4 | Scenes that differ only in hidden settings form one history with several hidden worlds. | Yige ("compatible hidden-world cases"); PDF section 1 |
| D5 | Profile status. **Refuted:** in at least one world the policy's margin is below −0.03. **Supported:** every world of its history has a valid run and the smallest margin is at least +0.03. **Unresolved:** anything else (a world not run, an invalid run, repeats that disagree, a margin within 0.03 of zero). Unresolved is never a failure. | PDF sections 2.1 to 3; Yige |
| D6 | The pass rule of a run is the one recorded in that run's own `summary.json` (`scenario` thresholds). The margin is the smallest constraint margin, clipped to [−1, 1]; a clearance gives `(measured − required) / 5 m`. For Victor's runs this formula is mine, marked `proposed`, until R1 is in place. | PDF section 1 (the contract travels with the label) and 2.1 |
| D7 | A failed yes/no end check (did not hold the stop, did not settle) is a separate flag (`terminal_ok`), and the margin is −1. A missed clearance keeps its measured margin. A run that ends at a contact also keeps its measured margin: the contact sets the clearance to 0, so every crash of a case has the same margin (−0.4 in RC01, −0.1 in RC03). See Q14. | PDF section 2.1: no invented distances |
| D8 | Matched histories must agree in observations, applied actions, pending commands and tick length up to the decision point. Each profile reports the largest difference found. | Yige ("timing and pending commands") |
| D9 | Two splits. `split` keeps one history together; neighbouring settings of one sweep can still fall in different splits. `split_strict` keeps a whole base scenario together, which today means a whole case: RC01 is all train and RC03 all test, with no validation set. Until more cases arrive, `split` is the practical one. Splits belong to one build: a later build with more data can move a group, so train and evaluate on the same build. | Yige; PDF section 10.3 |
| D10 | A policy is identified by its family and its searched parameters. The same policy run in several scenes is one profile entry. | needed for D5 |
| D11 | Observation sequences exist only for runs in the new format. Old-format runs (RC05, RC09, RC13) and my own earlier runs keep labels, margins and descriptors, and the coverage report lists them as waiting to be rerun or replaced in the new format. | Yige (label-only runs need an observable history) |
| D12 | A new-format run of a case replaces the old-format runs of that case. INVALID runs are kept, flagged, and never counted as failures. | Victor's README; PDF section 3 |

## 5. What each run folder needs to carry

This is what lets the same code handle all 20 RCs. "Have" means `rcx-run-1` already does it.

| ID | Item | State | Who |
| --- | --- | --- | --- |
| — | Label, reason, end reason | have | |
| — | Every scene value and threshold (`scenario`) | have | |
| — | Policy family, searched parameters, fixed parameters | have | |
| — | Observed values in their own file, apart from the true state | have | |
| — | Visibility flag per actor and tick | have | |
| — | Decision records with pending commands and controller state | have | |
| R1 | **One block listing every constraint the run was judged on:** name, measured value, required value, pass/fail. | missing | Victor |
| R2 | **The hidden settings of the scene**, as a list of parameter names. | missing | Kent → Victor |
| R3 | **A scene name separate from the RC number** (for example `street_van`, `spun_car`), plus Kent's `uid`, `site` and `split` when the run starts from one of Kent's variations. | missing | Kent → Victor |
| R4 | **A shared set of policies run on every scene**, next to the searched ones. | missing | Victor |
| R5 | **Each candidate policy run in every hidden world of its history.** | partly (`ref` runs only) | Victor |
| R6 | **More than one scene seed** for scenes near a pass/fail boundary. | missing | Victor |
| R7 | **The whole pre-roll recorded** before the cue. | RC03 has 0.5 s | Victor |
| R8 | **`docs/RUN_SCHEMA.md`** in the delivery (units, signs, reference points). | missing | Victor |

Why each one matters:

- **R1.** Without it I write the pass rules again per case by reading label texts, which does not scale to 20 RCs and
  can drift from the evaluator. With it, margins come straight from the evaluator's own numbers. It also settles
  thresholds I could not find (see Q3).
- **R2.** D3 measures hidden settings from the data, which needs scene pairs that differ in one setting only. A
  declared list is exact and works from the first run. I will use the list and report the measurement next to it.
- **R3.** Kent files RC01, RC02 and RC09 by what happened in the run, on one shared scene. If the RC number is my
  only grouping, holding out "a whole case" separates recoverable scenes from unrecoverable ones. With a scene name I
  group by scene.
- **R4.** Each scene now has its own few policies, mostly the best ones the search found. So the model rarely sees the
  same policy in two scenes and rarely sees a policy fail, and the coverage analysis has little contrast to report.
  Kent's kit already has fixed settings per family; running those on every scene would be enough.
- **R5.** The search tunes a policy for one scene, including its hidden settings. A pass then shows that this one
  world can be solved in hindsight, not that the policy recovers from that history (PDF section 2.4). Under D5 such a
  policy stays unresolved until it has been run in the other hidden worlds. The coverage report will list the exact
  missing runs.
- **R6.** With one seed and no repeats, a pass close to zero cannot be told from luck, and I cannot measure the noise
  band that D5 uses (PDF section 9.4).
- **R7.** The model reads the history. Half a second is very little to read.

**What to run, concretely.** The coverage report turns R4 to R7 into run lists for the two cases delivered so far:
68 requests, 742 CARLA runs. By kind: each policy in the hidden worlds it missed (R5) 134 runs, all in two RC03
histories; repeats with new seeds near boundaries (R6) 138; a shared set of policies in every history (R4) 147;
settings between far-apart boundary neighbours 169; the full pre-roll in RC03 (R7) 111; reruns of invalid or
undecided runs 38; scene pairs that vary one untested setting alone 5. Each request names the scene, the policy with
its parameters and the run to copy it from. See `docs/dataset/WM_COVERAGE_REPORT.md`, section 11.

## 6. Open items

### For Victor

**Q1. Which point does `seen_*_rel_s` measure from?**
In RC03 the observed longitudinal position differs from `ground_truth.csv` in every run: before the decision point by
8.2 cm (median; largest 8.7 cm), over the whole run by 6.6 cm (median). Larger values, up to 70.6 cm, occur only after
the decision point, in 5 runs that end at a contact. In RC01 the difference is 3 cm.
*Default:* I use the values as they are and flag the runs.
Answer:

**Q2. `seen_*` and `obs_*`.**
I read `seen_*` as plain line of sight and `obs_*` as what the policy is told. In RC01 the van is `seen` from the
start, about 70 m away, while the policy is told only at the gap threshold. The RC01 pedestrians, delivery people and
props (19 of 68 objects) are never visible in any run. Are both intended?
*Default:* yes to both.
Answer:

**Q3. Thresholds not stated in the files.** Please confirm or correct:
- "physics envelope": 1 g combined, as in Kent's kit?
- "ego settled": within 0.6 m of a lane centre and 0.06 rad of heading over the last 2 s?
- "still closing from esc_follow": what is tested, and with which threshold?
- "ego left the road" in RC03: which limit?
- From the earlier zip: RC09 stop speed 0.1 m/s; RC05 "returned to lane" within half a lane width.

*Default:* these checks are not scored. Four RC03 runs that fail only on "still closing" have no margin. R1 would
close this item.
Answer:

**Q4. Scene and policy identity.**
I put two scenes with identical settings in different batches into one history and one hidden world (for example
`baseline/g8_v9.5` and `presets_r2/fast_hard`), and I treat two candidates with identical searched parameters as one
policy (D10). Correct?
*Default:* yes.
Answer:

**Q5. Schedule.**
When do the other RCs come in this format? Will the 5 invalid RC01 runs ("van moved") be rerun? Please send without
videos (0.5 GB instead of 4 GB).
Answer:

### For Kent and Victor

**Q6. Which scenes do the next deliveries use?**
RC01 in the 2026-11-17 delivery is a van in a street; Kent's RC01 is the roadworks corridor. RC03 is the same scene
idea in both, with Victor's own scene list. Will Victor's runs start from Kent's variation files from now on?
*Default:* I take whatever is delivered and name it by R3 when that exists.
Answer:

**Q7. One pass rule between you.**
Kent's kit passes a run at 0.05 m of clearance. Victor's evaluator requires 2.0 m during the hold (RC01) and 0.5 m
(RC03). Under D6 I follow whatever each run records, so this does not block me, but the two stages should agree.
Answer:

### For Yige

**Q8. Which target do you train on?**
Each run has `margin_signed`, the margin in its own world. Each history and policy has `margin_robust`, the worst
over its hidden worlds, with a status. Where a history has hidden worlds, the same input has several run-level
margins.
*Default:* both are provided, and the card's loading example uses `margin_robust` with its status as the recovery
target and the run sequences for dynamics.
Answer:

**Q9. Actor slots.**
`actors` is [T, K, 7] with K per case (68 for RC01, 4 for RC03), and each slot is one named actor (`victim`,
`esc_lead`, ...). A slot index therefore tells the model an actor's role before the hazard (PDF section 8.2). I can
instead deliver a fixed number of role-free slots ordered by position (nearest first, per lane).
*Default:* named slots, flagged `reveals_role` in `feature_spec.json`. Say the word and I add the role-free arrays.
Answer:

**Q10. Margin scale.**
D6 and D7: one number in [−1, 1], clearances divided by 5 m, a failed end check at −1 with its own flag, 0.03 as the
unresolved band. Change any of these?
*Default:* as stated.
Answer:

**Q11. The cue as an input.**
Should "the policy has now been told about the hazard" be a model input, or only what was visible?
*Default:* not an input; it only marks the end of the history.
Answer:

**Q12. Policy descriptor.**
15 fixed slots with a mask (intervention time, braking levels and durations, lateral target, lane-change time,
triggers, target speed, four family-specific slots, a braking-unit flag), plus a one-hot of the policy family.
*Default:* as stated.
Answer:

**Q14. Crash margins are flat.**
A crash sets the clearance to 0, so every crash in a case has the same margin: −0.4 in RC01 and −0.1 in RC03 (43 of
the 44 refuted RC03 policies sit at −0.1). The margin says "crashed", not how hard. Do you want a graded value for
crashes, for example the impact speed? That needs one more recorded quantity from Victor (it could go into R1).
*Default:* as it is.
Answer:

**Q13. Shortest history and date.**
What is the shortest history the model needs (see R7), and when do you need the dataset?
Answer:

## 7. Summary

| ID | For | What | Needed for |
| --- | --- | --- | --- |
| R1 | Victor | constraint block per run | margins for all 20 RCs |
| R2 | Kent → Victor | hidden settings per scene | profiles |
| R3 | Kent → Victor | scene name, `uid`, `site`, `split` | splits, tracing |
| R4 | Victor | shared policies on every scene | profiles, coverage |
| R5 | Victor | each policy in every hidden world | "supported" entries |
| R6 | Victor | more seeds near boundaries | noise band |
| R7 | Victor | full pre-roll | history length |
| R8 | Victor | `RUN_SCHEMA.md` | units and signs |
| Q1 to Q5 | Victor | confirmations and schedule | |
| Q6, Q7 | Kent, Victor | scene source, one pass rule | |
| Q8 to Q14 | Yige | target, slots, scale, cue, descriptor, date, crash margins | |
