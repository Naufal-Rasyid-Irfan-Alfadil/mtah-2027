# External DFL preparation, contract v1

## Adapter audit revision (V2 r1)

The previous claim that half-scope information was unavailable was premature.
Public `DATA.md` and `games.py:half_video_blocks()` supply the per-half video
scope. Adapter r1 supports this explicit source with `--period-source
organizer-public --game BAR-ATH`; it converts both inclusive endpoints by +1
to raw ATD IDs and keeps feature/decoder halves separate. No official dataset
or GT file was inspected. The old bundle remains intact and the revised model,
feature/router sources and decoder hashes are unchanged. Full audit and
operator commands: [audit_adapter_half_bounds.md](audit_adapter_half_bounds.md).

## Current refinement release: R / V2 (2026-11-07)

The fixed observation router passed J03WQQ development guards and the
predeclared additional J03WMX assessment. Bundle:
`external_artifacts/v2/inference-bundle-v2/` (portable ZIP alongside it).
J03WMX legacy-project usage is unknown; no untouched-test claim is made.
All 101 synthetic tests passed. Serialized R replay matched labels for all 14
development half/scenario combinations. Standalone synthetic inference, both
routing branches, archive hashes and relocated runtime verification passed.
Official inference was not run. Results, limitations and operator commands:
[hasil_refinement_v2.md](hasil_refinement_v2.md). The section below records the
original A/B/C experiment; C alone remains rejected.

## V2 bounded decoder/context experiment

### Observed local development result (2026-11-06)

Completed run: `external_artifacts/v2/run1/`, status `ready`. Dependencies were
installed into the separate v2 runtime with the exact bundle package pins;
Python is Windows 3.11.6. A reproduced the documented J03WQQ clean scores.
One C model fit used 1,979,175 samples; model reload probabilities were exact.

| Candidate | Clean Spell F1 | Macro F1 | D F1 | Transition F1 @12 / @25 |
| --- | ---: | ---: | ---: | ---: |
| A | 0.446316 | 0.863894 | 0.960087 | 0.415254 / 0.501695 |
| Best B by clean Spell F1 (alpha=.5, beta=1) | 0.422869 | 0.862752 | 0.961962 | 0.398367 / 0.489796 |
| C | 0.507111 | 0.879104 | 0.961132 | 0.444050 / 0.547069 |

**Decision: retain A.** Every B failed the predefined gates. C improved clean
Spell F1 by .060795 but failed the burst-ball-missing D-F1 and player-drop
Transition-F1@12 regression guards. Do not relax these guards or expand the grid
after seeing the results. No v2 candidate was promoted, so no replacement bundle
was created; original v1 remains intact. No historical test or official asset
was scored. This is reused external development evidence, not an independent
generalization result. Full per-class precision/recall, transition latency,
fragmentation, half scores and perturbation scores are in `metrics.json`;
`selection.json` lists every rejection reason. The original protocol records
the experiment's source hashes; packaging helper portability was subsequently
corrected to write forward-slash manifest paths for Windows/Linux relocation.
Final regression: 95 tests passed, including the 18-feature synthetic bundle
roundtrip/tamper check (`external_artifacts/v2/regression-complete.log`). All
experiment output hashes and the original v1 bundle were reverified. C's two
guard violations were D F1 .943398 -> .929799 under burst missing and Transition
F1@12 .385044 -> .372197 under player drop. The complete dependency installation
and experiments stayed on external/synthetic inputs; no official asset was read.

Implementation entrypoint: `python -B -m external_baseline.v2 --output external_artifacts/v2/NEW_RUN`.
Use `external_artifacts/v2/runtime/Scripts/python.exe` on this Windows checkout;
its dependencies are pinned by `requirements-multimatch-training.txt`. No official
asset path is accepted or discovered. The driver explicitly verifies the three
documented DFL matches, baseline bundle and prepared database hashes against the
bundle's frozen expanded lineage. Historical absolute paths are never opened.

A uses the frozen expanded 14-feature classifier and decoder. Five B candidates
reuse exactly the same H/A/D posterior arrays: prior correction alpha in
{0,.5,1}, transition weight beta in {.5,1}, excluding A=(1,1). Initial prior and
training transitions remain fixed. These are discriminative path scores, not
claims of generative likelihoods. V1 decoding remains the default API behavior.

C has a fixed diagnosis gate: at least one decoded error on a valid frame with
incomplete ball observation in clean, ball-drop, burst or partial-ball validation.
This gate is evaluated before its single fit; no feature search follows a failure.
It appends four causal context features: complete-ball fraction in the trailing
25 frames, seconds since last complete ball, and median available nearest-home
and nearest-away distance over that window. Before any complete ball, age is
NaN; an empty distance window is NaN. Windows include the present frame and reset
on match/half/frame/time discontinuity. No player identity continuity is assumed.
The classifier input is (N,18), float64/NaN; posterior order is H/A/D. Training
uses both halves of J03WOH/J03WPY, unchanged HGB/augmentation seed 2028. Decoder
parameters stay identical to A. All seven observation perturbations are applied
before feature extraction, evaluation seed 2027, paired across candidates.

J03WQQ is reused development validation, not untouched test. No J03WOY/J03WR9
scores participate in selection. Spell gain must be at least .01 overall;
Macro F1, D F1 and Transition F1 at 12/25 frames may regress at most .01.
Each clean half's Spell F1 and every stress scenario's overall Spell/Macro/D/
Transition F1 have the same .01 regression guard. Exact ties prefer Macro F1,
then B over C, then B closest to A. Failure retains A; no additional sweep or
combined B+C is performed. No independent generalization claim follows.

Outputs include protocol/source/input hashes, keyed per-half/scenario NPZ
observations/posteriors/hard labels, full official metric dictionaries plus run
duration/fragmentation diagnostics, training audit, selection rejection reasons
and a ready manifest (or FAILED.json). Arrays are never reused without matching
keys, timestamps and feature replay. New output paths cannot overwrite v1.
If a candidate passes, `inference_bundle.build_v2(experiment, NEW_BUNDLE)` verifies
the experiment before packaging a versioned model/decoder/feature contract.
The agent only tests inference with synthetic fixtures; official inference is
operator-local and requires declared metadata half boundaries. The v1 packaged
full-recording option is not carried into the v2 adapter.

Risk-focused tests are in `tests/test_v2.py`: causal missing/reset behavior,
anonymous-slot invariance, brute-force path-score optimality, unchanged v1
decoding, class-column permutation/ties, destruction of true short H/A/D runs by
smoothing, and conservative selection/stress rejection. Existing regression
tests cover target isolation, frame keys, bundle tampering and CSV contracts.

This stage prepares observations and supervised targets only. It does not fit a
model, extract model features, decode predictions or run official inference.
Use Python 3.11 with standard-library SQLite support. Tested runtime versions and
source/input hashes are recorded in each manifest. No dependency installation is
needed. Repository NumPy/pandas requirements and optional kloppy/notebook tools
are not imported here. Future scikit-learn/NumPy/pandas versions remain unselected.

## Development boundary and provenance

The organizer email clarification supplied by the user takes precedence over
older repository guidance. No official video, ATD, homography, Smart Tagging,
public/private GT, predictions or per-frame diagnostics may be opened by the
agent. No training, tuning, threshold/candidate selection, self-supervised fitting,
pseudo-label training or calibration uses the official match. The user runs
official inference locally after the external pipeline is frozen. Never check
predictions against official video or upload official data to AI services.

The user explicitly confirmed that the current `data/` directory contains only
external DFL data. Only the two explicitly named J03WOH XML inputs were processed;
the code never searches that directory or falls back to official loaders. Future
invocations must likewise supply known external inputs, not assume every file in
`data/` remains external. Fixtures are synthetic and use no match labels.

Base commit: `f8f2629ff1e0985f81d7e59d8413678514ee1530`, initially clean. No old
project code, model, threshold, augmentation or decoder was copied. The HGB idea
is user-proposed, not selected by new measurements. A fresh clone alone cannot
prove decisions are independent of earlier experiments. Manifest provenance
records this limitation honestly; it does not assert a full provenance audit.

## Attribution and sources

Data supplied with authorization of **Deutsche Fußball Liga (DFL)**.

Bassek, M., Rein, R., Weber, H. & Memmert, D. (2025). *An integrated dataset of
spatiotemporal and event data in elite soccer*. Scientific Data **12**, 195.
https://doi.org/10.1038/s41597-025-04505-y

- Dataset: https://doi.org/10.6084/m9.figshare.28196177
- Author license/attribution statement: https://github.com/spoho-datascience/idsse-data
- CC-BY 4.0: https://creativecommons.org/licenses/by/4.0/
- DFL schema reference: https://floodlight.readthedocs.io/en/latest/_modules/floodlight/io/dfl.html
- Coordinate convention: https://floodlight.readthedocs.io/en/latest/_modules/floodlight/core/pitch.html

The author repository states CC-BY 4.0 and requests DFL credit plus publication
citation. Give attribution, link the license and identify modifications when
sharing derived data. This preparation changes representation, normalizes
missing coordinates, joins frames, maps labels and assigns a half-based split;
it does not correct tracking by hand. DFL licensing is separate from the MTAH
repository's MIT code license. No upstream code was copied.

## Commands (PowerShell, repository root)

```powershell
python -B -m unittest discover -s tests -v
python -B -m external_baseline.prepare --help
python -B -m external_baseline.prepare --match-info data/DFL_02_01_matchinformation_DFL-COM-000002_DFL-MAT-J03WOH.xml --positions data/DFL_04_03_positions_raw_observed_DFL-COM-000002_DFL-MAT-J03WOH.xml --output external_artifacts/J03WOH-v1
```

The output directory must not already exist. Reproduction uses a new output
directory, not deletion or overwrite. `external_artifacts/` and source XML data
are ignored by Git. No official evaluation runner is invoked: its default GT is
public official GT and its default assumptions are unsuitable here.

## Contracts and temporal semantics

`contracts.py` defines immutable FrameKey, Observation and Target types. SQLite
stores normalized tables rather than repeating a timestamp in every entity row.
All tables have explicit primary keys; SQL retrieval must use `ORDER BY`.

| Artifact/table | Contents |
| --- | --- |
| `observations.sqlite` / `frames` | Match ID, period, original source frame N, UTC timestamp in integer microseconds |
| `observations` | Frame key plus entity ID, team H/A/BALL, nullable x_m/y_m and per-axis missing reasons |
| `timeline` view | Frames ordered within match/period, continuity flag, deterministic split |
| `metadata` | Contract version, home/away IDs, pitch metres, origin, fixed FPS |
| `targets.sqlite` / `targets` | Frame key, raw BallStatus/BallPossession, nullable H/A/D label, valid_target, invalid_reason |
| `manifest.json` | Ready status, input/source SHA-256, Git state, runtime, policies and attribution |
| `validation_report.json` | Counts, gaps, missing/outside ranges, duplicates, labels, runtime and peak resident memory |

One prepared pair contains one match. Join keys are `(match_id, period,
source_frame)`; observations add `entity_id`. Never join by array index or nearest
timestamp. Home/away come from explicit metadata IDs and roster membership,
including the actual `GuestTeamId` spelling. Team order is irrelevant. Referee
records are counted and excluded; unknown teams/players fail validation.

`firstHalf` maps to 1 (train), `secondHalf` to 2 (validation). Other periods are
unsupported and rejected. Both halves and a ball stream in each are required.
This is **inter-half validation**, not inter-match validation. No fitted
preprocessing exists in this stage. Later fitting, including decoder priors,
must use only train. IDs, split and timestamps are bookkeeping, not automatically
model features.

The timeline is the union of tracked player and ball frame keys. `N` is never
renumbered; no 199,319-row constraint applies to DFL. Frames entirely absent from
all streams are represented as gaps, not synthetic observations. Halftime is a
period boundary, not an interpolated run. `contiguous_previous=1` requires same
period, N difference 1, timestamp difference 40,000 microseconds. Downstream
per-entity derivatives additionally require that entity present with valid
coordinates in both frames. Do not filter to valid targets and treat resulting
array neighbours as contiguous.

Coordinates follow DFL's centred metre convention: pitch boundaries are
±length/2 and ±width/2. No scaling, direction flipping, clipping or zero filling
is applied. This stage intentionally excludes provider S/D/A/M, ball Z and all
target attributes from observations. Future speed is planar displacement divided
by seconds, using only valid contiguous observations, not anonymous slot changes.

An absent entity record has **no observation row**. A present record with a
missing axis has SQL NULL plus `missing`, `malformed` or `nonfinite` reason.
Partial coordinates remain distinguishable; finite outside coordinates remain
unchanged. Future distance calculations require both valid axes and otherwise
return missing, not zero. Roster membership does not imply that a substitute is
on the pitch; do not fill every roster member into every frame.

Targets: status 0 → D regardless of possession; status 1 plus possession 1 → H,
2 → A. Active without a recognized possession, missing/unknown status, or absent
ball record → NULL label, valid_target=0, explicit reason. No forward filling.
X is not a supervised class. Neither target values nor validity/missing reasons
are exposed in the observation database. A target-only change must leave all
observation rows/schema unchanged, as tested.

The reader checks match/pitch consistency, roster/team identity, integer frame
IDs, timezone-aware timestamps, all within-stream 25 Hz intervals and exact
cross-stream timestamp agreement per frame. Out-of-order records are counted and
sorted by key; identical normalized duplicates are deduplicated; conflicting
duplicates fail, including conflicting raw target codes. Ignored noncontract
attributes do not participate in duplicate identity. Unknown XML namespace/schema
variants are unsupported rather than silently interpreted as a different format.

SQLite batches and XML parent removal bound memory independently of match length.
Database/report size still grows with input size. SQLite cache is limited to
8 MiB per connection and temporary sorting uses disk. OS peak RSS covers the
process lifetime, including interpreter and SQLite; compare fresh processes.

Only a successfully completed directory with `manifest.status=ready` is usable.
Failure retains partial artifacts and FAILED.json, without a ready manifest.
Source edits, input hash changes during preparation or conflicting records cannot
be silently attested as a complete result. Logical tables and stable manifest
fields reproduce; timing/memory and absolute input paths can differ across runs.

## Tests and deferred work

Synthetic tests use manually specified expected labels, metre coordinates and
frame joins. They cover inactive/ambiguous targets, reversed team order,
timezone conversion, partial/nonfinite/outside values, lost records versus lost
coordinates, unordered/conflicting duplicates, gap/period boundaries, target
leakage, reproducibility, no-overwrite and failed output readiness. Import/help
is run under an audit hook that rejects dataset access. No official GT is loaded.

Next stages: compact features available from both external and later official
inputs; HGB training; raw predictions; Spell F1 first, Macro F1/per-class and
transitions as diagnostics; optional single temporal comparator; robustness on
external data; additional untouched external match test; configuration freeze.
F1 is not accuracy. External evaluation must preserve timeline gaps and separate
periods. The eventual official CSV is `frame,label`, 199,319 rows, frames
0..199318; official inference remains a later local user action.

## Stage 2: observation features v1

The implemented feature stage reads only an explicit `observations.sqlite` in
SQLite read-only/query-only mode, plus its ready preparation manifest. It never
opens `targets.sqlite`, XML, the preparation validation report, official loaders
or evaluation files. No training, fitting, scaling, imputation or decoder runs.
The core `FrameFeatureExtractor` accepts a frame of planar observations, so it
does not depend on DFL labels or player identity continuity. A future official
adapter must establish the same metre/time/team convention before using it.

Run from the repository root, with a new output directory:

```powershell
python -B -m unittest discover -s tests -v
python -B -m external_baseline.features `
  --observations "external_artifacts/J03WOH-run2/observations.sqlite" `
  --output "external_artifacts/J03WOH-features-v1"
Get-Content "external_artifacts/J03WOH-features-v1/feature_report.json"
```

The 16 numeric features are fixed in the ordered `FEATURE_NAMES` allowlist:

| Names | Meaning and missing policy |
| --- | --- |
| `ball_record_present` | 1 for a ball record, including invalid/partial coordinates; otherwise 0 |
| `ball_x_observed`, `ball_y_observed`, `ball_xy_observed` | Finite axis/complete-pair availability, encoded 0/1 |
| `ball_x_m`, `ball_y_m` | Original centred metre coordinates, independently nullable; outside retained |
| `ball_speed_mps` | Backward 2D ball displacement / 0.04 s; NULL unless both frames have complete ball coordinates, same match/period, N difference 1 and timestamp difference 40 ms |
| `home_records`, `away_records` | Number of present team records, including partial/missing coordinates; empty team is 0 |
| `home_xy_observed`, `away_xy_observed` | Number of team records with both finite coordinates |
| `nearest_home_m`, `nearest_away_m` | Minimum Euclidean distance from a complete ball to complete players of that team; NULL if either side unavailable |
| `ball_longitudinal_margin_m` | length/2 − abs(ball_x), independently nullable |
| `ball_lateral_margin_m` | width/2 − abs(ball_y), independently nullable |
| `ball_inside_pitch` | 1 inside/on boundaries, 0 outside, NULL for incomplete ball coordinates |

Margins are signed distances to the corresponding boundary pair, not clipped
distances to a pitch polygon. No missing value becomes a zero distance. A real
zero distance remains valid. No player velocity is calculated from anonymous
slots. Record counts do not assume 11 players or count absent roster members.
Changing IDs/order without changing the frame geometry cannot alter features.

The feature set deliberately starts with basic geometry and one backward
difference. No near-ball radius, temporal smoothing window, restart rule,
augmentation or fitted transform has been selected. Short window summaries and
their coverage are deferred; the current report supplies availability coverage
for each feature, separately by half. This choice comes from the agreed minimal
feature stage, not official-match scores or old project parameters.

Output files:

- `features.sqlite`: one row per original frame in table `features`, plus
  `feature_metadata` containing the ordered numeric allowlist and units.
- `feature_report.json`: frame counts and defined/missing counts, coverage, min,
  max and defined-value mean per feature/half; elapsed time and OS peak RSS.
- `manifest.json`: ready status, observation/parent-manifest hashes, source
  hashes, feature version/units, policy, runtime and inherited attribution.

Columns `match_id`, `period`, `source_frame`, `timestamp_us` and `split` are
bookkeeping, **not model inputs**. Later training must select `FEATURE_NAMES`
explicitly and join targets by all three frame keys, applying valid_target
without compacting the timeline for temporal evaluation. Stage 2 does not read
target masks, target quality fields or labels.

Prepared input databases remain unchanged. Existing output directories are
rejected. Failure after output creation produces FAILED.json without a ready
manifest; consumers must require ready status. Input/source changes during the
run also fail. All feature values must be finite or NULL. Geometry overflow is
an error rather than an infinite model input. Unsupported units, FPS or a
combined observation/target database are rejected.

Additional tests use hand-computed 3–4–5 distances and 0.2 m / 0.04 s speed;
outside/partial/nonfinite coordinates; empty teams/frames; missing, gap, match
and half boundaries; changing player IDs; duplicate entities/balls; sorting and
full timeline retention; unsupported schema/units; reproducibility/no-overwrite;
and audit-hook rejection of target/official data access during import/help/run.
The synthetic target-file contents can change or be invalid without changing
the feature output. No scientific score is claimed at this stage.

## Stage 3: one fixed HGB, raw external evaluation

```powershell
python -B -m unittest discover -s tests -v
python -B -m external_baseline.training `
  --features "external_artifacts/J03WOH-features-run2/features.sqlite" `
  --targets "external_artifacts/J03WOH-run2/targets.sqlite" `
  --output "external_artifacts/J03WOH-hgb-v1"
Get-Content "external_artifacts/J03WOH-hgb-v1/metrics.json"
```

Use a new output directory on every run. The installed training dependencies
were verified; exact versions are in `requirements-external-training.txt` and
each training manifest. No installation runs automatically. Preparation/features
continue to work without these dependencies. Import and `--help` do not import
NumPy/sklearn or open data. Runtime model/metric imports occur only on execution.

Training uses only the 16 `FEATURE_NAMES` columns, in that order. SQL NULL is
converted to float64 NaN, retained natively by HGB. There is no fitted scaler,
imputer, feature selection, augmentation, weighting, probability calibration,
decoder or threshold. Target joins use the full match/period/source-frame key;
missing or extra keys and inconsistent valid masks are errors, not silent inner
joins. Invalid labels are excluded from fitting but retained at original frame
positions in prediction/evaluation outputs.

One configuration is fixed **before validation scores are inspected**, using
sklearn 1.7.2 defaults (learning rate 0.1, 100 iterations, 31 leaf nodes,
min_samples_leaf 20 and L2 0), with these explicit controls:

- `early_stopping=False`, `validation_fraction=None`: no hidden random frame
  validation split and no selection of iteration count on half 2.
- `random_state=0`: reproducible binning seed; numeric
  `categorical_features=None` prevents automatic category inference.
- `threadpool_limits(limits=1)` for fitting/prediction: one thread, without
  assuming the user's available CPU count.

See the verified version's documentation:
https://scikit-learn.org/1.7/modules/generated/sklearn.ensemble.HistGradientBoostingClassifier.html

All valid half-1 labels fit the one estimator. Half-2 targets are loaded after
fitting and raw prediction; they never enter `fit`. Raw hard labels use the
estimator's native class-order argmax, including tie handling. Probabilities are
written with explicitly mapped `p_H`, `p_A`, `p_D` columns, not assumed sklearn
class order. Training metrics are in-sample diagnostics, not generalization
estimates. Half-2 metrics are inter-half development validation only. Another
untouched external match is still required for inter-match testing.

The evaluator imports only `evaluation/possession_metrics.py` functions and
never calls the default evaluation runner or any GT/CSV reader. It retains
missing source frame numbers as unscored X positions in a per-half evaluation
lattice. Invalid targets and period/time discontinuities break valid runs.
Transition matching is performed independently within each valid contiguous run,
then TP/FP/FN are pooled; transitions either side of a short unknown gap cannot
match each other. No transition is invented at a run boundary. Spell matching
uses the repository's IoUs 0.3/0.4/0.5/0.6/0.7 and mean F1. Macro F1 and per-class
metrics use H/A/D; transition tolerances are 12/25 frames at 25 Hz. Bootstrap is
disabled for this first baseline. F1 is not an accuracy percentage. Evaluation
lattice length can exceed the observed row count; real source keys are retained
in predictions.sqlite. Report both `observed_frames` and `n_graded`.

Outputs, all external-only and ignored by Git:

- `config.json`: fixed feature allowlist and full model parameters, written
  before fit. No CLI parameter sweep is provided.
- `model.joblib`: fitted estimator, feature order and config; load only this
  project's trusted local artifacts. It is not an official inference runner.
- `predictions.sqlite`: every observed train/validation frame, original keys,
  timestamp, split, raw label, H/A/D probabilities. This is not a tactical CSV.
- `metrics.json`: train/validation Spell F1, Macro F1, per-class metrics,
  confusion, transitions, spell counts/durations, mask counts, iterations,
  elapsed time and OS peak RSS.
- `manifest.json`: ready status, input/source/output hashes, exact dependency
  versions, config and inherited DFL attribution/provenance.

Feature artifact hash and target preparation lineage are checked before training;
all actual inputs are hashed and rechecked after training. Current source and
metric-library hashes are captured separately; old preparation source hashes
remain historical provenance rather than being overwritten by later code.
Failed runs have no ready manifest and retain FAILED.json after output creation.
Models/configurations are not declared frozen for official inference at this
stage. No full-match refit, tuning, candidate selection or decoder is performed.

Training tests cover keyed/masked joins and NaN retention, three-class support,
disabled early stopping, deterministic fit with ignored invalid labels,
serialization and unchanged model/predictions after altering **synthetic**
validation labels, manual confusion/spell examples, gaps/invalid/half boundaries,
cross-gap transition matching, lineage errors, and import/help without data or
training dependency access.

## Stage 4: aggregate raw-baseline diagnosis

```powershell
python -B -m external_baseline.diagnostics `
  --features "external_artifacts/J03WOH-features-run2/features.sqlite" `
  --targets "external_artifacts/J03WOH-run2/targets.sqlite" `
  --predictions "external_artifacts/J03WOH-hgb-v1/predictions.sqlite" `
  --output "external_artifacts/J03WOH-diagnostics-v1"
```

Requires a new output directory. Reads only the three explicit external SQLite
artifacts and their ready manifests, in read-only mode. It verifies feature and
prediction hashes, preparation lineage, the baseline's original input hashes,
and exact frame/timestamp/split joins. It does not deserialize a model, fit,
calibrate, decode, change features or modify predictions. Imports/help do not
load datasets or training dependencies. NumPy is used only on execution.

`diagnostic_report.json` reports, separately for train and validation:

- H/A/D confusion and an exhaustive valid-frame outcome decomposition:
  correct, H/A swap, alive misclassified D, and D misclassified H/A.
- Maximum probability, top-two probability margin and entropy by outcome.
  Confidence is descriptive; no calibration or abstention threshold is selected.
- Ball x/y, speed and home-minus-away nearest distance distributions by target;
  alive-frame error/support counts by negative/zero/positive/missing ball x.
  The only sign boundary is the pitch centre, not a tuned cut point.
- Association between the nearer team and target/prediction, on complete alive
  frames, with equal-distance ties explicitly counted. This is a geometry
  diagnostic, not a new nearest-player candidate or possession rule.
- Target and predicted H/A/D run durations, transition counts, exact one-frame
  runs, predicted H/A switches and D changes inside constant true possession,
  and contiguous error-run lengths. H/A runs are possessions; D runs are not.

Quantiles describe available values; missing counts remain explicit. Run
statistics use the same valid target mask for truth and predictions and break
on gaps, periods, timestamps or unknown targets. Comparisons do not compact the
timeline or invent transitions across unknown time. Target-conditioned summaries
are diagnostics only and must never be added to observation features.

`manifest.json` captures input/source/report hashes and inherited attribution;
FAILED.json marks failures after directory creation. Existing outputs are never
overwritten. All input files are rehashed after diagnosis. Tests use synthetic
labels only and check manual error/confidence counts, run fragmentation, missing
geometry, temporal boundaries, reproducibility, input immutability, provenance
rejection and safe import/help. Diagnosis cannot establish causality: a half-wise
position shift can motivate a later external-only ablation but does not prove
that absolute coordinates caused an error.

No decoder, duration cutoff, smoothing radius/window or new model configuration
is chosen here. A later single temporal comparator must estimate its priors and
transitions from training only, reset on observation gaps/half boundaries, and
be evaluated against this unchanged raw baseline on external data.

Observed J03WOH diagnosis (`J03WOH-diagnostics-v1`, external development data):
validation has 10,475 H/A swaps among 34,101 alive frames, 95 alive→D errors,
1,761 D→alive errors and 1,933 predicted H/A switches inside constant true
possession. There are 2,070 predicted versus 174 target possession spells; 512
predicted H/A spells last exactly one frame. Median ball x for target H changes
from +4.315 m in training to −13.63 m in validation; target A changes from
−8.74 m to +7.21 m. These are descriptive associations, not proof that absolute
coordinates caused the errors.

The resulting recommendation, not implemented in this diagnostic stage, is one
external-only ablation dropping `ball_x_m` and `ball_y_m` (14 remaining numeric
features), keeping the original HGB parameters and half split fixed. This tests
sensitivity to signed location while preserving distances, unsigned boundary
margins and availability. Its provenance is the external inter-half diagnostic,
not an untouched test or official-match experiment. It must retain the original
16-feature baseline and artifacts for comparison. Decoder choice remains deferred
until this geometry question is assessed; no model or threshold was changed by
the diagnosis itself.

## Stage 5: one 14-feature ablation

```powershell
python -B -m external_baseline.training `
  --features "external_artifacts/J03WOH-features-run2/features.sqlite" `
  --targets "external_artifacts/J03WOH-run2/targets.sqlite" `
  --feature-set no-signed-position `
  --reference "external_artifacts/J03WOH-hgb-v1" `
  --output "external_artifacts/J03WOH-hgb-no-signed-position-v1"
Get-Content "external_artifacts/J03WOH-hgb-no-signed-position-v1/comparison.json"
```

Use a new output directory. The unchanged 16-column source database is reused;
there is no need to regenerate observations or features. `project_features`
applies a fixed ordered projection removing only `ball_x_m`/`ball_y_m`. Missing
values and frame rows remain unchanged. The model sees 14 numeric columns;
`feature_names` in its serialized artifact and config contains exactly those
14 names. Downstream prediction must project to that saved order. Diagnostics
continue to consume the full 16-feature observation database for analysis.

Default training remains `--feature-set all16`. The sole alternative is
`no-signed-position`, requiring an explicit original 16-feature reference. There
is no arbitrary feature selector, parameter search or automatic model promotion.
The reference's feature/target input hashes, raw predictions, config, model and
manifest are checked. Model parameters, split, seed, thread policy and runtime
dependency versions must match. Baseline artifacts are never retrained or
overwritten. All actual input/reference files are rehashed after the run.

The new model fits valid half-1 targets with identical HGB parameters and no
early stopping. Half-2 prediction precedes target loading as before. No decoder,
weighting, scaling, calibration or full-match refit is added. Predictions and
metrics have the same original frame-key contract as the baseline.

`comparison.json` recomputes the reference scores from its unchanged predictions
and the exact same external target timeline, rather than trusting an edited
metrics file. It reports training and validation Spell F1, Macro F1, per-class
F1, transition F1, spell counts, H/A swaps and H/A switches inside constant true
possession, plus signed deltas (ablation minus baseline). A lower error/spell
count is not automatically better; compare against the target count and Spell
F1. Reference files and the comparison hash are included in the new manifest.

This is a single development ablation motivated by already-seen external
inter-half diagnostics. Its validation is therefore reused for development, not
an untouched inter-match test. A score difference alone is not proof of causal
dependence on signed coordinates. Original baseline/model parameters are not
silently replaced or declared ready for official inference.

Additional tests verify the exact 14-column projection and NaN retention,
invariance under reflection of the complete synthetic player/ball geometry,
serialized feature order/model width, unchanged HGB parameters, keyed predictions,
unchanged source/reference artifacts, recomputed comparison scores/deltas,
no-overwrite, matching reference requirements and gap-aware switch counting.

Observed J03WOH ablation (`J03WOH-hgb-no-signed-position-v1`): validation Macro
F1 changes from 0.772198 to 0.815931 and H/A swaps from 10,475 to 8,341. Spell F1
changes only from 0.040820 to 0.041270, while predicted spells increase from
2,070 to 2,220 against 174 target spells. H/A switches inside constant true
possession increase from 1,933 to 2,085. Thus the frame-label improvement does
not resolve temporal fragmentation. No statistical-significance claim, automatic
baseline replacement or official inference freeze follows from this single
reused inter-half comparison. All 42 tests pass; artifact/input/source hashes,
original frame keys and identical validation predictions after model reload
were verified. Original 16-feature model/prediction files remain unchanged.

## Stage 6: one Markov/Viterbi temporal comparator

```powershell
python -B -m unittest discover -s tests -v
python -B -m external_baseline.temporal `
  --features "external_artifacts/J03WOH-features-run2/features.sqlite" `
  --targets "external_artifacts/J03WOH-run2/targets.sqlite" `
  --predictions "external_artifacts/J03WOH-hgb-no-signed-position-v1/predictions.sqlite" `
  --output "external_artifacts/J03WOH-markov-v1"
Get-Content "external_artifacts/J03WOH-markov-v1/comparison.json"
```

Use a new output directory. The raw 14-feature classifier and its probabilities
are fixed; no model is loaded or retrained. This is one predeclared comparator,
without parameter sweep, validation calibration, EM, pseudo-label training,
duration minimum, restart rules or automatic candidate promotion. The choice of
14-feature source follows the explicit prior external ablation, so development
validation has already been reused and is not a held-out test.

States and posterior column order are H/A/D. Valid **half-1 target labels only**
estimate frame-occupancy counts `n[c]` and adjacent-label counts `n[i,j]`. Gaps,
unknown training labels and period boundaries cannot contribute transitions.
With fixed Laplace pseudocount 1:

```
prior[c] = initial[c] = (n[c] + 1) / (sum(n) + 3)
transition[i,j] = (n[i,j] + 1) / (sum_j n[i,j] + 3)
emission[t,c] = log(raw_posterior[t,c]) - log(prior[c])
score(path) = log(initial[path[0]]) + sum_t emission[t,path[t]]
              + sum_{t>0} log(transition[path[t-1],path[t]])
```

Using occupancy for the initial distribution avoids estimating kickoff-specific
probabilities from a single run start. Prior correction treats classifier
posteriors as relative likelihood scores instead of adding the class prior
twice. This is an adaptation of the standard hybrid classifier/HMM construction;
see the University of Edinburgh's primary teaching material:
https://www.inf.ed.ac.uk/teaching/courses/asr/2022-23/asr11-hybrid_hmm_nn.pdf
Fixed add-one smoothing is documented, not selected on match results:
https://scikit-learn.org/1.7/modules/naive_bayes.html#multinomial-naive-bayes

The posterior-likelihood interpretation and first-order temporal independence
are modelling assumptions; HGB scores are not asserted calibrated or independent
across frames. Both emission and transition weights are exactly one. The model
has geometric implicit state durations through self-transition probabilities,
not an explicit football duration model. No numeric probability floor is tuned:
exact zero posterior has score −infinity. Smoothed priors/transitions are strictly
positive. Ties follow fixed H/A/D state order. Common score offsets stabilize the
dynamic program without changing the optimum.

Viterbi uses future probabilities within an observation-contiguous run, so this
is **offline decoding**, not online inference. Inference boundaries come only
from original match/period keys, adjacent N and 40 ms timestamps. A missing ball
coordinate does not itself break a present frame. Crucially, target labels and
valid-target masks are **not passed to decoding**. Unknown validation targets
therefore cannot provide oracle reset locations. Valid target masks are used
afterwards for scoring, where unknown time breaks evaluation runs as before.
Half-2 targets are loaded only after its labels have been decoded.

Outputs:

- `decoder_parameters.json`: training counts, prior and transition matrix with
  explicit class order; sufficient to reproduce decoding without the targets.
- `config.json`: fixed method, fit period, smoothing, weights and reset policy,
  written before validation target loading.
- `predictions.sqlite`: original frame keys/time/split and decoded hard label.
  It contains no fake decoded probabilities; raw probabilities remain in the
  unchanged classifier artifact. This file is not a tactical submission CSV.
- `metrics.json` and `comparison.json`: raw14 versus decoded14, with Spell F1,
  Macro F1, per-class/transition metrics, spell counts, H/A errors and internal
  H/A switches. Raw scores are recomputed on exactly the same target timeline.
- `manifest.json`: source/input/output hashes, runtime, inherited attribution,
  method assumptions and selection provenance; failures retain FAILED.json
  without ready status. All SQLite inputs are read-only and rehashed afterwards.

The decoder adds no dependency. Its numerical core uses NumPy; the existing
metric library imports NumPy/pandas when evaluation runs. Import/help performs
no dataset I/O or heavy dependency import. Synthetic tests cover exact smoothed
counts, unknown/gap boundaries in fitting, brute-force path optimality, zeros,
ties, state order, independent inference across gaps/halves/time discontinuities,
invalid probabilities/duplicate keys, parameter reload reproducibility, changed
validation labels/masks leaving decoded results unchanged, input immutability,
lineage/hash/timeline rejection, failed readiness and safe import/help.

Observed J03WOH comparator (`J03WOH-markov-v1`): validation Spell F1 rises from
0.041270 (raw14) to 0.297358 (decoded14), Macro F1 from 0.815931 to 0.846650,
and predicted possession spells fall from 2,220 to 356 against 174 target spells.
H/A swaps fall from 8,341 to 6,725 and H/A switches inside constant true
possession from 2,085 to 295. The tradeoff is D→alive errors increasing from
1,504 to 1,658; D-class F1 changes from 0.976235 to 0.974535. These are reused
external inter-half development results, not inter-match evidence or an official
score. No second decoder or parameter change was tried after seeing them.

Parameters use exactly 69,424 valid training frames and 69,423 adjacent training
transitions, with H/A/D occupancy counts 20,714/17,130/31,580. All 50 tests pass;
hashes, all 137,214 original output frame keys, SQLite integrity and identical
train/validation decoding from reloaded parameter JSON were verified. Raw model,
probability and feature artifacts remain unchanged. Next comes external-only
robustness work and an untouched additional-match test before any official
pipeline freeze; no official inference adapter has been added here.

## Stage 7: frozen external observation stress tests

```powershell
python -B -m unittest discover -s tests -v
python -B -m external_baseline.robustness `
  --observations "external_artifacts/J03WOH-run2/observations.sqlite" `
  --features "external_artifacts/J03WOH-features-run2/features.sqlite" `
  --targets "external_artifacts/J03WOH-run2/targets.sqlite" `
  --classifier "external_artifacts/J03WOH-hgb-no-signed-position-v1" `
  --decoder "external_artifacts/J03WOH-markov-v1" `
  --output "external_artifacts/J03WOH-robustness-v1"
Get-Content "external_artifacts/J03WOH-robustness-v1/robustness_report.json"
```

This freezes the existing classifier/decoder **parameters**, not the final
official pipeline. No fitting, transition estimation, calibration, new model,
threshold selection or scenario sweep is performed. Only the already-used
external validation half is stressed. Data/model/parameter/manifest files are
read-only and rehashed afterwards. The model is this project's own hash-verified
local joblib artifact; no old project model is loaded. Dependency versions must
match the recorded classifier environment.

The protocol is written before inference and was declared before inspecting
stress results. All stochastic scenarios use separate NumPy generators with
seed 2027, stable frame/entity order and no target inputs. Scenarios are fixed
engineering probes, not estimates matched to official tracking or distributions.

| Scenario | Observation transformation |
| --- | --- |
| `clean` | Identity replay, with exact feature/raw-probability/decoded-label agreement required |
| `ball_drop_iid20` | Drop the ball record with probability 0.2 independently per frame |
| `ball_drop_burst2s` | Drop ball records for offsets 0..49 of each 500-frame cycle (2 s every 20 s) |
| `ball_x_missing_iid20` | Set only ball x missing with probability 0.2; record and y remain |
| `player_drop_iid20` | Drop each H/A player record independently with probability 0.2; ball remains |
| `position_jitter_025m` | Add independent zero-mean Gaussian noise, sigma 0.25 m, to every finite entity axis; missing axes remain missing and outside coordinates are not clipped |
| `frame_gap1s_every60s` | Remove offsets 0..24 of each 1,500-frame cycle (1 s every 60 s) from observation inference |

Offsets use original N minus the validation half's first N, not compacted row
indices. Fixed blocks start at the half's first frame and were not positioned
using labels/events. Random ball masks are drawn independently of coordinate
values/visibility. The full-drop and partial-axis scenarios use the same random
frame selection, allowing a controlled distinction. Player/noise generators
consume their own per-entity draws; they cannot change other scenarios' masks.
Independent frame-wise jitter intentionally perturbs derived speed as well as
geometry; it is not a claim about realistic tracking-noise autocorrelation.

Perturbations operate on immutable observation records **before recomputing**
all 16 features. Missingness flags, distances, counts, margins and ball speed are
therefore consistent. The frozen model still projects to its 14 saved inputs.
Missing/partial ball data invalidates consecutive speed calculations. Dropped
whole frames are not passed to the extractor or Viterbi; original key/time gaps
reset speed and decoding. Missing ball coordinates on a present frame do not
invent a frame gap. Viterbi never receives target labels or valid masks.

Features and predictions for every scenario are computed before target labels
are loaded. The clean scenario must exactly reproduce saved validation features,
raw hard labels/H/A/D probabilities and decoded labels. A replay mismatch fails
the run rather than silently mixing pipeline versions.

Evaluation retains the **full original target timeline** for every scenario.
Removed frames have raw and decoded `X`, and NULL probabilities, rather than
being silently excluded or assigned D. Target validity is unchanged. This counts
abstentions as per-frame misses. For temporal metrics, the repository scorer's
existing within-GT-valid-run abstention filling applies **only during scoring**;
it never fills saved predictions or supplies GT boundaries to inference. Thus
temporal scores alone can understate coverage loss; inspect retained fraction,
`n_graded` and `n_abstain_on_graded` alongside F1. The evaluator's default H/A/D
contract remains strict; X scoring requires explicit `allow_abstain=True`.

Outputs in a new directory:

- `protocol.json`: the fixed scenarios/seed and no-fitting/full-timeline policy.
- `predictions.sqlite`: seven scenarios × all validation frame keys, retained
  flag, raw/decoded labels and raw probabilities; no features/targets modified.
- `robustness_report.json`: full raw/decoded metrics, compact summaries, decoded
  deltas from clean, retained coverage, audit counts and per-feature finite/missing
  counts on retained frames, elapsed time and OS peak RSS. `selected_frames` is
  the frame-level ball/gap mask count; player-drop/jitter use record/axis counts.
- `manifest.json`: ready status, source/input/output hashes, runtime and inherited
  DFL provenance. Failed runs retain FAILED.json without a ready manifest.

The source observations are read once, holding one frame of entity objects plus
the seven per-frame feature matrices. No augmented training dataset or disk copy
of raw observations is produced. This adds no new dependency beyond the existing
training environment. Import/help does not read data or import model libraries.

Synthetic tests check missing-record versus partial-axis versus removed-frame
semantics, original-frame burst placement, deterministic/geometry-independent
masks, player-only removal, missing/outside jitter behaviour, speed resets,
abstention confusion/temporal scoring, exact clean replay, repeated-output
determinism, no input mutation, no model/transition fitting, coverage accounting,
hash/readiness failures and safe import/help. These are stress diagnostics on
reused external development data, not an untouched match test or a prediction of
official competition performance. No pass/fail score threshold has been chosen.

Observed J03WOH stress run (`J03WOH-robustness-v1`, decoded metrics):

| Scenario | Spell F1 | Macro F1 |
| --- | ---: | ---: |
| Clean | 0.297358 | 0.846650 |
| Ball drop IID 20% | 0.020720 | 0.614011 |
| Ball drop 2 s every 20 s | 0.227258 | 0.785844 |
| Ball x missing IID 20% | 0.020654 | 0.613795 |
| Player drop IID 20% | 0.156808 | 0.833793 |
| Independent position jitter sigma 0.25 m | 0.203232 | 0.353691 |
| Frame gap 1 s every 60 s | 0.288000 | 0.839053 |

The random ball/partial-axis cases share exactly 13,547 selected frames. Ball
bursts remove 6,800 ball records; jitter modifies 3,118,340 finite axes. The gap
scenario removes 1,150 observation frames, all saved as X and counted as graded
abstentions, while all 67,790 target-valid frames remain scored in every scenario.
Jitter gives D-class F1 0; this independent frame-wise noise also changes derived
speed and should not be interpreted as a calibrated model of real tracking noise.
The results expose missing/noise sensitivity and do not support recommending an
official pipeline freeze. No model or scenario was adjusted after these results.

All 58 tests pass. Exact clean replay, source/input/output hashes, SQLite integrity
and all 474,530 scenario/frame keys were verified. Original features, classifier,
decoder parameters and targets remain unchanged. The next development question
is how to handle missing/noisy observations using external training only; an
untouched additional external-match test remains required before generalization
claims. These stress results are not an additional-match test.

## Stage 8: one augmentation experiment on external training only

```powershell
python -B -m external_baseline.augmented `
  --observations "external_artifacts/J03WOH-run2/observations.sqlite" `
  --features "external_artifacts/J03WOH-features-run2/features.sqlite" `
  --targets "external_artifacts/J03WOH-run2/targets.sqlite" `
  --classifier "external_artifacts/J03WOH-hgb-no-signed-position-v1" `
  --decoder "external_artifacts/J03WOH-markov-v1" `
  --reference-stress "external_artifacts/J03WOH-robustness-v1" `
  --output "external_artifacts/J03WOH-augmented-v1"
Get-Content "external_artifacts/J03WOH-augmented-v1/comparison.json"
```

Use a new output directory. This is exactly one new model, motivated by the
previously observed external missing/noise failures. There is no sweep or
automatic model selection. The recipe is written before fitting:

- Replay **half 1 only**, in seven separate observation views: clean plus all
  six perturbations from the existing stress protocol. Training seed is **2028**;
  validation stress retains seed **2027**. Burst schedules remain anchored to
  each half's original first frame; the similar validation corruption protocol
  is intentionally known development data, not a novel distribution.
- Recompute features from each modified observation stream. Missing stays
  missing, outside coordinates are retained, and speed cannot cross dropped
  frames or view/half boundaries. Only the same 14 model inputs are projected.
- Join each retained training frame to its **unchanged external DFL target**.
  Unknown targets are excluded; no previous-team/D filling, pseudo labels or
  synthetic human annotations are created. Repeated frame IDs denote augmented
  views, not fake matches or independent evaluation groups.
- Give each retained valid sample equal weight, including the clean view. No
  balancing, scaler, imputer, sample-weight fitting or label-aware corruption
  is introduced. Frame-gap removal means the last view has fewer samples;
  resulting clean versus pooled class counts are explicitly audited.
- Fit HGB once with the identical 100-iteration configuration, seed 0,
  early_stopping=False, feature order and one-thread policy. No validation
  targets/features enter fitting or binning.
- Copy the original decoder parameter JSON **byte for byte**, without calling
  transition/prior estimation. It retains original unaugmented training-count
  priors, not counts multiplied by the augmentation views. Its posterior/prior
  interpretation remains approximate: pooled classifier training class
  proportions can differ slightly after gap removal; no validation calibration
  is introduced to compensate.

All clean train/validation predictions preserve original frame keys, and
validation targets are loaded only after its raw probabilities and decoded
labels exist. Clean in-sample train scores do not describe performance on
independent data. The new model is then frozen and passed through the exact
same validation stress runner as the original model. Scenario audit counts,
retained coverage, feature missing counts and evaluated target/spell counts
must match the old stress report; otherwise comparison fails.

Outputs in the new experiment directory:

- `protocol.json`, `training_audit.json`: recipe, seed/weights, source frame
  counts, valid rows/class counts by view and pooled fitted sample count.
- `classifier/`: one new model, clean keyed raw predictions, config, metrics
  and manifest using the existing 14-feature artifact contract.
- `decoder/`: copied parameter JSON, clean keyed decoded predictions, metrics,
  config and manifest explicitly identifying frozen parameter provenance.
- `stress/`: the unchanged seven-scenario stress protocol, perturbed validation
  predictions and full robustness report for this newly frozen model.
- `comparison.json`: original versus augmented clean train/validation metrics
  and all seven decoded stress comparisons, including per-class F1 and signed
  deltas. Original baseline scores are recomputed from its unchanged probabilities
  with the same decoder; stress reference scores come from the hash-verified
  original report.
- Root `manifest.json`: ready only when training **and** stress/comparison finish,
  with input/source/all nested output hashes, dependencies, runtime and provenance.
  Root FAILED.json signals incomplete experiments; child ready artifacts alone
  do not establish completion of the full experiment.

Original observations, features, targets, classifiers, decoder parameters and
stress results are read-only and rehashed. No official data is read and no
additional dependency is introduced. Training feature arrays are released after
fit before validation stress matrices are generated. No augmented raw XML or
large observation database copy is written. Existing output directories are
rejected. Import/help reads no dataset and loads no model libraries.

Synthetic tests check exact retained/valid copy counts and class support, NaN
retention, deterministic view generation, rejection of validation fitting, clean
feature replay, exactly one classifier fit, no decoder fitting, byte-identical
decoder reuse, unchanged parents, validation-target loading after inference,
identical stress masks/coverage, repeated prediction reproducibility, output
hashes/readiness, failure handling and safe import/help.

This experiment uses knowledge of the earlier external validation stress
results. Improvement on the matched stress cases cannot establish robustness on
unseen matches or realistic official tracking. No new model is automatically
promoted or frozen for official inference; an untouched additional external
match remains needed before generalization claims.

Observed J03WOH experiment (`J03WOH-augmented-v1`), decoded Spell F1:

| Validation scenario | Original | Augmented |
| --- | ---: | ---: |
| Clean | 0.297358 | 0.287943 |
| Ball drop IID 20% | 0.020720 | 0.244550 |
| Ball drop 2 s every 20 s | 0.227258 | 0.290359 |
| Ball x missing IID 20% | 0.020654 | 0.212448 |
| Player drop IID 20% | 0.156808 | 0.117269 |
| Position jitter sigma 0.25 m | 0.203232 | 0.279070 |
| Frame gap 1 s every 60 s | 0.288000 | 0.290071 |

Clean Macro F1 drops from 0.846650 to 0.786861; jitter Macro F1 improves from
0.353691 to 0.729220 and jitter D-class F1 from 0 to 0.802755. This is a tradeoff:
the recipe addresses the matched missing-ball/noise probes but does not improve
all scenarios or clean performance. No automatic baseline replacement follows.

The single new HGB fit used 484,793 augmented samples from 69,424 unique half-1
frames, with pooled H/A/D counts 144,643/119,545/220,605. These copies are not
independent matches. Decoder bytes are identical to the original. All 61 tests
pass; input/source/output hashes, SQLite integrity, original clean prediction
keys, full stress coverage and identical clean validation raw/decoded results
after model/parameter reload were verified. Original pipeline/data files remain
unchanged. The experiment took 85.051 seconds with measured process peak RSS
546.47 MiB in this run, not a hardware requirement or cross-machine guarantee.

The next recommended assessment is both candidates on an untouched additional
external match, with these artifacts/configurations fixed before inspecting its
labels/results. That match must not become another tuning set if its scores are
reported as test evidence. No additional match was downloaded in this stage and
no official input or inference pipeline was introduced.

## Stage 9: frozen external-match assessment

At the start of this stage, local inspection found only J03WOH. Figshare article 28196177 version
1 lists J03WOY in the same competition. It is the first remaining match ID in
lexical order for competition DFL-COM-000002, chosen without inspecting tracking,
labels or performance. The public catalog was checked at
https://api.figshare.com/v2/articles/28196177 (CC-BY 4.0). Required files:

| File | Figshare file ID | Bytes | Published MD5 |
| --- | ---: | ---: | --- |
| `DFL_02_01_matchinformation_DFL-COM-000002_DFL-MAT-J03WOY.xml` | 51643481 | 11,952 | `7b021e577fca917a63111d55cc29ae5b` |
| `DFL_04_03_positions_raw_observed_DFL-COM-000002_DFL-MAT-J03WOY.xml` | 51643523 | 362,567,859 | `4e1063e0a0ae499920cf68ac1aa3ab4e` |

The holdout CLI does not download those files automatically. Dataset absence in
this repository cannot establish that the user has never used the match in an
earlier project. The user explicitly confirmed that no DFL match other than
J03WOH had been used, including in the old project. The confirmed snapshot
`external_artifacts/J03WOY-holdout-frozen-v1/` was then created before download or
new-match processing. The earlier unconfirmed draft remains non-evaluable and
was not used. Only after confirmation/snapshotting were the two listed XMLs
downloaded to `data/external_dfl/J03WOY/`, checked against their published byte
sizes/MD5, and recorded in download_manifest.json. No real scores were generated
while history was pending.

After explicit confirmation that the match is unused, create a **new** snapshot
before preparing or scoring its data (the flag is a statement of history, not a
replacement for checking it):

```powershell
python -B -m external_baseline.holdout freeze `
  --original-classifier "external_artifacts/J03WOH-hgb-no-signed-position-v1" `
  --original-decoder "external_artifacts/J03WOH-markov-v1" `
  --augmented-classifier "external_artifacts/J03WOH-augmented-v1/classifier" `
  --augmented-decoder "external_artifacts/J03WOH-augmented-v1/decoder" `
  --test-match DFL-MAT-J03WOY --confirm-unused `
  --output "external_artifacts/J03WOY-holdout-frozen-v1"
```

Both candidate model files and decoder parameter files are copied into that
snapshot, with hashes, frozen source/metric code, feature order, versions, training provenance and fixed
primary candidate **augmented**. Primary is declared from the earlier external
robustness objective before seeing new-match targets/scores; original is the
predeclared comparator. No automatic winner or official pipeline freeze follows
from a score comparison. Both candidates must have the same 14 inputs, HGB
parameters and identical decoder JSON. J03WOH is rejected as test. Snapshots and
results never overwrite existing directories, and import/help never loads data.

Once the two external XML paths are verified, use the existing `prepare` and
`features` commands on them, with fresh output folders such as
`external_artifacts/J03WOY-prepared-v1` and `J03WOY-features-v1`. Do not train or
augment this match. The parser's legacy split strings still say half 1=train and
half 2=validation as bookkeeping; the dedicated evaluator overrides their role:
**both halves are test**, and output prediction rows use `split=test`.

```powershell
python -B -m external_baseline.holdout evaluate `
  --protocol "external_artifacts/J03WOY-holdout-frozen-v1/protocol.json" `
  --features "external_artifacts/J03WOY-features-v1/features.sqlite" `
  --targets "external_artifacts/J03WOY-prepared-v1/targets.sqlite" `
  --output "external_artifacts/J03WOY-holdout-results-v1"
```

Evaluation verifies snapshot/data hashes, exact declared match identity, feature
units/allowlist and source lineage. It predicts/decodes **both candidates and
both halves before loading any test labels or valid masks**. No classifier fit,
new preprocessing, prior estimation or calibration is supported. Original frame
numbers, gaps, unknown targets and half boundaries retain the existing contracts.
`metrics.json` reports each candidate's raw/decoded metrics per half and overall;
overall Macro/Spell F1 are computed on the combined bounded timeline, not averaged
half scores. `predictions.sqlite` holds both fixed candidates, raw probabilities
and decoded labels for all observed frames. A ready manifest records all hashes
and that test evidence has been consumed for reporting these fixed candidates.

Repeating the identical protocol/data can verify reproduction. If this match is
then used for candidate selection, thresholds or retraining, relabel it as
development and obtain another untouched match for final performance claims.
Neither scores nor direction/threshold/model choices may use the official match.

Synthetic tests cover immutable candidate copies and primary declaration,
unconfirmed-history/development-match rejection, both halves tagged test, labels
loaded after all inference, no classifier/decoder fitting, valid-mask and temporal
boundaries, identical repeated predictions, wrong-match/hash/failure handling and
safe import/help. No synthetic score is reported as new-match evidence.

Observed J03WOY assessment (`J03WOY-holdout-results-v1`), both halves decoded:

| Fixed candidate | Spell F1 | Macro F1 | Predicted possession spells |
| --- | ---: | ---: | ---: |
| Original raw14 + original decoder | 0.311512 | 0.841001 | 873 |
| Augmented raw14 + identical decoder (predeclared primary) | 0.322801 | 0.791735 | 772 |

There are 142,536 observed/valid target frames (69,111 + 73,425) and 456 target
possession spells. Augmentation has a small higher observed Spell F1 and fewer
excess spells, but lower Macro F1. No statistical-significance or consistent
generalization superiority is claimed from this one external match. Primary was
not changed after seeing these results; neither model nor decoder was refitted.

The full regression suite passed 65 tests; the four holdout tests were rerun
after adding the frozen source-code mismatch guard and passed. Snapshot/data/
source/output hashes, SQLite integrity, all 285,072 candidate/frame prediction
keys and `split=test` role for both halves were verified. Reloading snapshot
models/parameters reproduced all raw labels, probabilities and decoded labels
exactly for both candidates/both halves. Evaluation took 14.764 seconds with
measured peak RSS 385.45 MiB in this run. These are runtime observations, not
hardware requirements. All source inputs and frozen candidates remain unchanged.

J03WOY is now consumed as external assessment evidence for these preregistered
candidates. Do not silently reuse it for tuning/selection while continuing to
describe it as untouched test. No official data was opened or official inference
performed. The next step is reproducible packaging of the predeclared primary
and its configuration, with this result and its limitations retained.

## Development expansion: acquisition and validation only

The user subsequently requested this first step of a new development experiment:
download and validate J03WPY and J03WQQ, without feature extraction, fitting or
inference. Source is Figshare article 28196177, with the existing DFL/publication
attribution and CC-BY 4.0 terms. Exact catalog names, byte sizes and MD5 are
verified before a downloaded `.partial` file is renamed to `.xml`. Existing
download directories are not overwritten. `download_manifest.json` records
source version/license, published checksums, role and download time.

| New match | Match-information file ID / bytes | Raw-observed positions file ID / bytes | Planned whole-match role |
| --- | --- | --- | --- |
| J03WPY | 51643487 / 11,922 | 51643526 / 371,688,499 | Training, both halves |
| J03WQQ | 51643484 / 11,932 | 51643529 / 356,219,423 | Development validation, both halves |

Files are stored only under `data/external_dfl/J03WPY/` and `J03WQQ/`. The existing
streaming preparation CLI validates match/team IDs, rosters, pitch dimensions,
25 Hz frame/timestamp consistency, duplicate conflicts, gaps, coordinates and
target availability, then writes separate observations/targets plus a manifest
and aggregate report. Preparation is data parsing/validation, not model inference.

Future partitioning is J03WOH + J03WPY for training and J03WQQ for inter-match
development validation, using both halves of each. The parser's legacy per-half
`train`/`validation` strings are bookkeeping and must not override these new
whole-match roles. J03WOY retains its consumed assessment status for the earlier
frozen candidates; those scores are not test evidence for a future retrained
model. J03WR9 is reserved for a later untouched assessment and is not downloaded
or processed in this acquisition step. No historical model or split is changed.

The next step after acquisition/validation is feature extraction on these two
new external matches. No training, decoder fitting or prediction is authorized
by the acquisition step alone.

Acquisition/validation completed for this step:

| Match | Half 1 frames | Half 2 frames | Total frames | Planned role, both halves |
| --- | ---: | ---: | ---: | --- |
| J03WPY | 69,131 | 77,080 | 146,211 | Development training |
| J03WQQ | 69,204 | 73,141 | 142,345 | Development validation |

All four raw files match the published byte sizes and MD5; parser SHA-256 hashes
were independently rechecked. Both prepared observation/target databases passed
SQLite quick_check and exact frame-key alignment, with no missing frame numbers
on either per-half timeline. Every target in these two matches is valid H/A/D.
Finite outside coordinates remain preserved under the existing contract.

Prepared artifacts are `external_artifacts/J03WPY-prepared-v1/` and
`external_artifacts/J03WQQ-prepared-v1/`. Aggregate integrity results, input/output
hashes, target counts and the explicit future whole-match partition plan are in
`external_artifacts/development-data-v1/manifest.json` (`status=ready`). Raw files
and all prepared data/reports are ignored by Git. This step changed documentation
and added external data artifacts only; it did not change parser/model code,
extract features, train, fit a decoder or run inference. No new score is claimed.

## Development expansion: existing observation features

Feature extraction completed on Linux using the unchanged v1 extractor for
J03WPY and J03WQQ. Before extraction, the copied observation databases and
preparation manifests matched the SHA-256 values in the historical
`development-data-v1/manifest.json`. Historical Windows paths/manifests were
preserved; the orchestration mapped only their explicit external-artifact
suffixes to the current repository. This verifies transfer consistency, not a
new independent upstream provenance audit.

The local isolated environment is `.venv/` (Python 3.10.12, SQLite 3.37.2).
No additional libraries were downloaded or installed. Its `pip.conf` disables
the download cache and requires an active virtual environment. Temporary files
were directed to `external_artifacts/local-runtime/tmp/`, on the project drive,
instead of the home filesystem. Use these environment settings for later runs:

```bash
export TMPDIR="$PWD/external_artifacts/local-runtime/tmp"
export SQLITE_TMPDIR="$TMPDIR"
export PIP_CACHE_DIR="$PWD/external_artifacts/local-runtime/pip-cache"
export PIP_NO_CACHE_DIR=1
.venv/bin/python -B -m unittest discover -s tests -p 'test_observation_features.py' -v
```

All 12 feature tests passed, including synthetic geometry, missing/partial
observations, gap/half resets, target isolation, safe import/help, reproducibility
and no-overwrite checks. No training or full regression suite was run here.

Extraction used the existing `external_baseline.features` CLI implementation:

```bash
.venv/bin/python -B -m external_baseline.features --observations external_artifacts/J03WPY-prepared-v1/observations.sqlite --output external_artifacts/J03WPY-features-v1
.venv/bin/python -B -m external_baseline.features --observations external_artifacts/J03WQQ-prepared-v1/observations.sqlite --output external_artifacts/J03WQQ-features-v1
```

These output directories now exist; reproduction must use new output names.
The local orchestration script
`external_artifacts/run_development_features_v1.py` additionally applied an audit
hook rejecting targets, raw data, official GT/results and model-library imports,
and performed the output checks below. It requires the original output names to
be absent and does not overwrite artifacts. Both extraction and verification
read only observation databases/manifests, not target databases.

| Match | Half 1 frames | Half 2 frames | Total feature rows | Planned role, both halves |
| --- | ---: | ---: | ---: | --- |
| J03WPY | 69,131 | 77,080 | 146,211 | Development training |
| J03WQQ | 69,204 | 73,141 | 142,345 | Development validation |

Each output contains all 16 features in their original order and units; the
future classifier still projects to the existing 14-feature allowlist. Exact
match/period/source-frame keys and microsecond timestamps agree with the input
timeline. Both output databases passed SQLite quick_check, all feature values
are finite or NULL, and input observation/manifest hashes stayed unchanged.
Complete ball coordinates are available on every frame of these two matches;
ball speed is NULL only on each half's first frame and defined on all remaining
frames. Outside coordinates remain unmodified. Feature output hashes match
their ready manifests.

The ready aggregate verification and per-half coverage are recorded in
`external_artifacts/development-features-v1/manifest.json`; each feature directory
also contains `features.sqlite`, `feature_report.json` and `manifest.json`.
Artifacts, the local runner and the venv remain Git-ignored. DFL attribution and
the publication/license references are inherited from the preparation manifests.

Stored half-based split strings remain historical bookkeeping: future training
uses both halves of J03WOH and J03WPY; J03WQQ is development validation for both
halves. This step did not fit a classifier/decoder, tune parameters, run
predictions, read official match data or produce a new scientific score. The
existing half-specific training/augmentation entrypoints still need an explicit
whole-match extension before the proposed training experiment can run.

## Development expansion: one whole-match training comparison

`external_baseline.multimatch` adds an independent entrypoint for the agreed
experiment without changing the historical half-specific entrypoints. Its
explicit directory-pair interface selects whole matches: both halves of J03WOH
and J03WPY are training, and both halves of J03WQQ are development validation.
The legacy per-half split strings remain unchanged and do not assign experiment
roles. Repeated/overlapping match identities are rejected; input hashes, feature
units/order, preparation lineage and the old baseline's augmentation/configuration
and dependency versions are checked before fitting.

The 14 features, HGB parameters, seven augmentation views and seed 2028 are
unchanged. Each original half restarts separate scenario RNGs with seed 2028,
resets temporal state and retains original source frame numbers. Samples are
ordered by sorted match, half, scenario and original frame; each retained valid
sample has equal weight. The raw 16-feature artifacts are unchanged. No tuning,
class weighting, imputation, new features or early stopping is introduced.

The disk-backed training pool contains 1,979,175 samples from 283,425 clean
training frames (J03WOH: 69,424 + 67,790; J03WPY: 69,131 + 77,080). The classifier
fits once for 100 iterations with one thread. Clean training counts, without
augmentation duplication, determine the decoder: H/A/D occupancy counts are
90,318 / 63,087 / 130,020, with 283,421 within-half transitions across four runs.
Counts are pooled before adding the same fixed Laplace pseudocount once.
Viterbi weights, prior correction and continuity rules are unchanged. The old
augmented model and its byte-unchanged decoder form the declared comparator.

The installed training environment is separate from the feature-only `.venv`:
`external_artifacts/local-runtime/training-venv/`, using Python 3.11.17. The six
historical training dependency versions match exactly; transitive dependencies
are pinned in `requirements-multimatch-training.txt`. `pip check` passed. Cache
was disabled and installation temporary files were placed on the project drive;
no user-site installation or home download cache was used. The venv's local
`pip.conf` keeps caching disabled and requires a virtual environment.

Reproduction from the repository root, after creating a Python 3.11 venv and
installing `requirements-multimatch-training.txt` into it, uses the earlier
TMPDIR/SQLITE_TMPDIR/PIP settings plus:

```bash
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
external_artifacts/local-runtime/training-venv/bin/python -B -m unittest discover -s tests -v
external_artifacts/local-runtime/training-venv/bin/python -B -m external_baseline.multimatch \
  --train external_artifacts/J03WOH-run2 external_artifacts/J03WOH-features-run2 \
  --train external_artifacts/J03WPY-prepared-v1 external_artifacts/J03WPY-features-v1 \
  --validation external_artifacts/J03WQQ-prepared-v1 external_artifacts/J03WQQ-features-v1 \
  --reference-classifier external_artifacts/J03WOH-augmented-v1/classifier \
  --reference-decoder external_artifacts/J03WOH-augmented-v1/decoder \
  --output external_artifacts/development-multimatch-v1
```

The output directory now exists; reproduction requires a fresh output name.
This run additionally used the local ignored wrapper
`external_artifacts/local-runtime/run_external_multimatch.py`, which rejects raw
data/video and official GT/result file access via a Python audit hook. The
standard module command above uses the same implementation and explicit inputs.
No official match data, J03WOY data or J03WR9 data was read in this experiment.

All 70 synthetic regression tests passed, including five new whole-match tests.
They check exact legacy half-1 augmentation equivalence, half-2 fitting samples,
count pooling before smoothing, match-role separation, input mutation rejection,
one fit and training-only decoder counts, and safe import/help. Validation labels
and valid masks are loaded only after both candidates predict/decode both halves.
A validation-only label/mask change leaves the synthetic training pool, serialized
model, decoder parameters and predictions byte-identical. Failure never publishes
a ready manifest; existing outputs are never overwritten. The test log is
`external_artifacts/local-runtime/multimatch-tests.log`.

Observed J03WQQ results, 142,345 graded frames and 401 target possession spells:

| Candidate | Raw Spell F1 | Raw Macro F1 | Decoded Spell F1 | Decoded Macro F1 | Decoded spells |
| --- | ---: | ---: | ---: | ---: | ---: |
| Old augmented J03WOH half-1 model + old decoder | 0.047144 | 0.804542 | 0.325389 | 0.822043 | 757 |
| Expanded whole-match training + refitted decoder | 0.070730 | 0.819479 | 0.446316 | 0.863894 | 549 |

Decoded Spell F1 improves on both halves: 0.346714 to 0.494118 in half 1 and
0.305210 to 0.401629 in half 2. Overall metrics are recomputed over the combined
gap-aware timeline, not averaged half scores. F1 is not an accuracy percentage.
This is one development-match comparison, not untouched test evidence or a
statistical-significance claim. In addition to J03WPY, the experiment incorporates
formerly-validation J03WOH half 2 and refits both classifier and decoder; the
observed gain does not isolate the causal effect of adding one match alone.
No candidate is automatically promoted and no official pipeline is frozen.

The ready output includes `protocol.json`, `training_audit.json`, the binary
training pool, `model.joblib`, `decoder_parameters.json`, `predictions.sqlite`,
`metrics.json`, `comparison.json` and a manifest with all input/source/output
hashes and inherited DFL/publication attribution. The new layout is a dedicated
whole-match experiment artifact, not a drop-in legacy half-based manifest.
Independent verification rechecked every recorded hash, the old model/decoder
lineage, SQLite integrity, all 284,690 candidate/frame rows, validation roles and
probability sums. Reloading the new model reproduced half-1 validation labels
and probabilities exactly. Measured training/evaluation runtime was 355.675 s
and process peak RSS 470,953,984 bytes; these are observations for this run.
The full dependency freeze is also retained under local-runtime. J03WOY remains
consumed assessment evidence for the historical candidates; J03WR9 remains
reserved and unprocessed. Any later assessment/freeze is separate work.

## Expanded pipeline: frozen J03WR9 assessment

The user explicitly confirmed that J03WR9 had never been used for training,
tuning, evaluation or method selection in this or the old project. That history
statement, not absence of local files, authorizes its role as an untouched
external test for the two declared candidates. Before downloading test XMLs,
`external_baseline.freeze_expanded` created
`external_artifacts/J03WR9-expanded-frozen-v1/`. Its 25 copied files and source
hashes were independently verified against the snapshot manifest.

The snapshot retains both models and their respective decoders, all current
external pipeline/metric source, feature units/order, pinned requirements and
runtime versions, plus historical training provenance. Training/development and
consumed assessment match IDs are rejected as new test IDs. Pending snapshots
cannot evaluate; this snapshot records the explicit confirmed-unused history.
It is a holdout-v1-compatible protocol: the legacy evaluator's `augmented` key
means the new **expanded** primary, while `original` means the **old_augmented**
comparator. Display names in protocol.json make this mapping explicit. The
decoders intentionally differ, preserving each candidate's already-fixed pair.

```bash
external_artifacts/local-runtime/training-venv/bin/python -B -m external_baseline.freeze_expanded \
  --expanded external_artifacts/development-multimatch-v1 \
  --reference-classifier external_artifacts/J03WOH-augmented-v1/classifier \
  --reference-decoder external_artifacts/J03WOH-augmented-v1/decoder \
  --test-match DFL-MAT-J03WR9 --confirm-unused \
  --output external_artifacts/J03WR9-expanded-frozen-v1
```

All 74 synthetic regression tests passed (including four new snapshot tests).
The new tests cover copy/hash identity, primary declaration and separate
decoders, used-match rejection, pending-history gating before dataset access,
safe import/help, exact repeated predictions with the existing evaluator,
tamper rejection, no fitting, and test targets loaded only after both candidates
predict/decode both halves. The log is
`external_artifacts/local-runtime/expanded-holdout-tests.log`.

Figshare article 28196177 version 1 was checked through its public API. It lists
CC-BY 4.0 and these predeclared files, downloaded only after freezing:

| Asset | Figshare file ID | Bytes | Published MD5 |
| --- | ---: | ---: | --- |
| J03WR9 match information | 51643490 | 11,823 | `5e2d580d3d8ed97e32959de90d04992b` |
| J03WR9 positions raw observed | 51643532 | 372,934,140 | `e060bb7d7a5a3bfbd15bbf9bc631024d` |

Source: https://api.figshare.com/v2/articles/28196177. The verified files and
download manifest are under `data/external_dfl/J03WR9/`; the manifest records
SHA-256, DFL/publication attribution, license and the frozen protocol hash.
The slow transfer was completed using verified HTTP byte ranges. Assembly
preserved byte order and matched the published full-file size and MD5 before
any parser run. Downloads, venv and temporary files stayed on the project drive.

The existing parser, feature extractor and holdout evaluator are used unchanged,
with explicit J03WR9 input paths and fresh output directories. Preparation is
`J03WR9-expanded-prepared-v1`, features are `J03WR9-expanded-features-v1`, and
evaluation output is `J03WR9-expanded-results-v1`, all under external_artifacts.
The evaluation command is:

```bash
external_artifacts/local-runtime/training-venv/bin/python -B -m external_baseline.holdout evaluate \
  --protocol external_artifacts/J03WR9-expanded-frozen-v1/protocol.json \
  --features external_artifacts/J03WR9-expanded-features-v1/features.sqlite \
  --targets external_artifacts/J03WR9-expanded-prepared-v1/targets.sqlite \
  --output external_artifacts/J03WR9-expanded-results-v1
```

Both halves are test, irrespective of stored legacy half split strings. All
candidate/half predictions precede target loading; no training, decoder fitting,
calibration, threshold/candidate selection or automatic promotion is supported.
Repeated source/data/output paths never overwrite an existing result directory.
No official match inputs or GT are involved.

Observed J03WR9 assessment is complete: 146,810 observed/valid frames
(68,354 + 78,456), no missing frame numbers or absent ball records, a 105 x 68 m
pitch, and 370 target possession spells. All feature keys and microsecond
timestamps match the original observation timeline. SQLite quick_check passed
for observations, targets, features and predictions. Every output prediction row
uses `split=test`; there are 293,620 candidate/frame rows with valid probability
sums. Snapshot copies and all recorded source/input/output hashes were rechecked.
Independent verification is recorded in
`external_artifacts/local-runtime/J03WR9-verification.json`.

| Fixed candidate | Raw Spell F1 | Raw Macro F1 | Decoded Spell F1 | Decoded Macro F1 | Decoded spells |
| --- | ---: | ---: | ---: | ---: | ---: |
| Old augmented J03WOH half-1 model + old decoder (`original`) | 0.043152 | 0.818262 | 0.318868 | 0.849971 | 690 |
| Expanded model + expanded decoder (`augmented`, predeclared primary) | 0.074125 | 0.840805 | 0.423374 | 0.868860 | 537 |

Decoded Spell F1 improves on both halves: 0.332394 to 0.449275 on half 1 and
0.306927 to 0.401623 on half 2. Decoded class F1 also increases: A from 0.756887
to 0.775489, D from 0.951026 to 0.960369, H from 0.841999 to 0.870724. Overall
scores are recomputed across the combined bounded timeline, not half-score
averages. F1 is not an accuracy percentage. This is evidence on one additional
external match for these already-frozen pairs, not a significance claim or an
official-match score. The training expansion also includes formerly-validation
J03WOH half 2 and refits the decoder, so it does not isolate adding J03WPY alone.

Evaluation took 51.014 s with measured process peak RSS 421,638,144 bytes. Neither
model nor decoder was fitted or changed during the assessment. Predictions,
per-half/overall metrics (including transitions), and the ready result manifest
are in `external_artifacts/J03WR9-expanded-results-v1/`. The local orchestration
script `external_artifacts/local-runtime/run_j03wr9_assessment.py` verified raw
SHA-256 values and the snapshot before running the existing CLIs, and verified
the frozen copies and all evaluation hashes again afterwards. Its preparation,
feature and evaluation logs are under local-runtime.

**J03WR9 is now consumed assessment evidence for these candidates.** Do not
silently treat the historical `reserved_test` field in the immutable development
protocol as its current availability. The commands above document the original
pre-test snapshot; they do not authorize declaring this match unused again.
Repeating the identical frozen protocol/data can check reproduction. Using
these results for further tuning or candidate selection changes this match's
role to development and requires another untouched match for final claims.
The predeclared primary was retained, with no automatic promotion or official
inference freeze. Packaging and an official-input adapter remain separate work;
the user will run official inference locally.

## Public Metrica sample CSV inference

The requested external repository is https://github.com/metrica-sports/sample-data,
pinned here to commit `e706dd506b360d69d9d123d5b8026e7294b13996`.
Analysis confirmed two CSV-format games and a third EPTS-format game. This
implementation supports the paired Home/Away tracking CSVs for Games 1 and 2;
Game 3 requires a separate reader and is not supported by this CSV adapter.
The upstream README documents normalized top-left-origin coordinates and
105 x 68 m dimensions. All rows of both CSV games were checked for a 25-Hz
frame/time grid and agreement of the duplicated ball coordinates.

These CSV samples do not include dense H/A/D possession targets. The inspected
event CSV schema describes event intervals, not a complete frame-label target
timeline; it is not converted or forward-filled into supposed possession GT.
Events are not downloaded or passed to inference. This is a frozen-model
integration/inference check, not another untouched, scored possession test.
No score, model selection or generalization superiority is claimed here.

The pinned tree has no standalone LICENSE file. Its README invites community
experimentation and asks for source acknowledgement for public use; do not
silently label these data MIT or CC-BY. Attribute **Metrica Sports sample data**
and link the upstream repository when sharing related work. Raw files and
derived artifacts remain ignored by Git, separately from repository source.

Acquisition downloaded only README and the four tracking CSVs to
`data/external_metrica_sample/e706dd506b360d69d9d123d5b8026e7294b13996/`.
Each file's byte count and Git blob SHA-1 matched the pinned GitHub tree, and
SHA-256 plus source URLs are recorded in download_manifest.json. All downloads
and existing-venv execution stayed on the project drive; no libraries were added.

`external_baseline.metrica_sample` provides the adapter and inference CLI:

- Parse the three-row team/jersey/name header, including the upstream Game-2
  alias `Player 26`. Canonical jersey identities are namespaced by team. Home
  and Away must agree with their explicit source headers; neither is guessed.
- Merge streams by original `(period, frame)` keys, preserving the union and
  gaps. Same-key relative timestamps and duplicated ball axes must agree exactly.
  Reject duplicates, unordered rows, malformed headers and non-25-Hz timelines,
  including incompatible time anchors across non-overlapping team rows.
- Convert `x_m=(x-.5)*105`, `y_m=(.5-y)*68`. Keep finite outside positions and
  partial coordinates; blank/nonfinite axes remain missing. Fully missing player
  pairs are unobserved roster slots, not assumed active players. A CSV ball
  pair remains an explicit record even when both axes are missing.
- Run the unchanged 16-feature extractor, project to the frozen 14-feature
  allowlist, then predict and decode with the frozen expanded primary from
  `J03WR9-expanded-frozen-v1`. No refitting, threshold changes, imputation or
  calibration is performed. Period/gap boundaries retain their temporal meaning.

Sample times are match-relative integer microseconds, **not UTC**. Feature and
prediction databases use `time_us` to make that distinction explicit. Their
original source frames are preserved; they are not 0-based tactical submission
indices and are not padded/truncated to 199,319 rows. The sample output should
not be passed to the competition submission validator.

Using the existing training venv and the local TMPDIR/SQLITE_TMPDIR and single
thread settings from the earlier stages, reproduce one game with a new output:

```bash
external_artifacts/local-runtime/training-venv/bin/python -B -m external_baseline.metrica_sample \
  --home data/external_metrica_sample/e706dd506b360d69d9d123d5b8026e7294b13996/data/Sample_Game_1/Sample_Game_1_RawTrackingData_Home_Team.csv \
  --away data/external_metrica_sample/e706dd506b360d69d9d123d5b8026e7294b13996/data/Sample_Game_1/Sample_Game_1_RawTrackingData_Away_Team.csv \
  --snapshot external_artifacts/J03WR9-expanded-frozen-v1 \
  --match-id Metrica-Sample-Game-1 --output external_artifacts/metrica-sample-game1-reproduction
```

For Game 2 change both source names/directories, match ID and output name to
Game 2. Import/help perform no dataset I/O and import no model libraries. The
adapter checks snapshot copies, frozen core source and dependency versions
before deserializing the trusted local model; inputs/source must stay unchanged
throughout the run. Existing outputs are rejected and failures never publish a
ready manifest.

Each successful directory contains `features.sqlite`, `predictions.sqlite`,
`predictions.csv`, `report.json` and `manifest.json`. CSV columns are
`period,source_frame,time_s,raw_label,label,p_H,p_A,p_D`; `label` is the decoded
prediction, while probabilities remain the classifier's raw H/A/D probabilities.
The report summarizes input coverage, raw/decoded label counts and predicted
spell counts, with `evaluation_status=not_scored_no_dense_possession_GT`.

All 80 synthetic regression tests passed, including six new sample-adapter
tests covering hand-calculated metre distances/speeds, outside/missing/partial
coordinates, union joins, conflicting ball/time values, FPS/order/header errors,
the Game-2 name alias, half/gap resets, no fitting/scoring, safe import/help,
snapshot tampering, no-overwrite/failure readiness and exact repeated outputs.
Changing an unusable synthetic event file cannot change predictions. The log is
`external_artifacts/local-runtime/metrica-sample-regression-tests.log`.

Final successful runs are `external_artifacts/metrica-sample-game1-v2/` and
`metrica-sample-game2-v2/`. The first Game-2 attempt correctly failed on its
previously unsupported spaced player name; that partial v1 output remains
non-ready. Header compatibility was added without changing model/core feature
code. Game-1 v1/v2 feature database, prediction database and CSV are byte-identical.

| Sample | Half 1 frames | Half 2 frames | Total | Fully missing ball pairs | Decoded H / A / D frames | Predicted possession spells |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| Game 1 | 71,268 | 73,738 | 145,006 | 56,755 | 86,346 / 49,643 / 9,017 | 610 |
| Game 2 | 67,941 | 73,215 | 141,156 | 57,884 | 91,850 / 45,614 / 3,692 | 542 |

These counts describe predictions, not correct/incorrect frames. Raw H/A/D
counts are 49,869 / 35,334 / 59,803 for Game 1 and 48,709 / 33,425 / 59,022 for
Game 2; the report retains both views so decoder effects are visible. Without
possession GT neither set of counts establishes quality. Observed run times
were 23.787 s and 22.837 s, with process peak RSS about 209 MB each; these are
measurements, not hardware requirements.

Independent checks verified feature/prediction timeline equality, CSV/database
keys/labels/probabilities, exact CSV row counts, SQLite integrity, finite normalized
probabilities and all recorded input/source/output hashes. Verification is in
`external_artifacts/local-runtime/metrica-sample-verification.json`, and the
combined acquisition/inference summary is
`external_artifacts/metrica-sample-inference-v2.json`. Frozen models/decoders and
all official-match data remain unchanged; no official data was accessed.

## Sample diagnosis, sparse event context, and portable tactical adapter

The user authorized all three steps: review the sample timelines, add limited
external event context, then package the unchanged primary and prepare a local
tactical ATD adapter. No model/decoder parameters were changed. The agent did
not open or run any actual official input, output, GT, video or Smart Tagging.

### Decoder diagnosis and external event references

The two event CSVs, event-definition PDF and public Sample-Game-3 metadata were
downloaded from the same pinned Metrica commit. Byte counts and Git blob SHA-1
were verified, with SHA-256 and attribution under the source directory's
`diagnostic_references/download_manifest.json`. They are external references,
not official competition data. The upstream definitions describe BALL OUT as
the last touch before the ball goes out, SET PIECE as a restart, and note that
RECOVERY can also restart play without a set piece. Accordingly no event is
expanded into a dense possession target or treated as proof of the whistle time.

`external_baseline.sample_review` reads the ready sample inference databases in
SQLite read-only/query-only mode. It checks exact feature/prediction alignment,
then writes the label-change matrix, ball-coverage breakdown, longest changed
runs, contextual event anchors/spans and a self-contained interactive HTML
timeline. It never calls a model, fits anything, modifies predictions or computes
accuracy/F1. Run-length encoding cannot bridge frame/time gaps or half boundaries.

```bash
external_artifacts/local-runtime/training-venv/bin/python -B -m external_baseline.sample_review \
  --run external_artifacts/metrica-sample-game1-v2 \
  --events data/external_metrica_sample/e706dd506b360d69d9d123d5b8026e7294b13996/diagnostic_references/Sample_Game_1_RawEventsData.csv \
  --output external_artifacts/metrica-game1-review-reproduction
```

Use the corresponding Game-2 paths and a fresh output name for Game 2.
Successful outputs are `metrica-game1-review-v1/` and `metrica-game2-review-v1/`
under external_artifacts, each with `timeline.html`, `summary.json`,
`event_references.json` and a ready hash manifest. The timeline supports half,
time-window, next/previous and event-jump controls for raw/decoded labels,
ball visibility and D-to-alive changes. BALL OUT end-frame and SET PIECE
start-frame markers are explicitly contextual references, not dense GT.

| Sample | Raw D | Decoded D | D -> H/A changes | Changes while ball missing | Ball-out -> next set-piece references |
| --- | ---: | ---: | ---: | ---: | ---: |
| Game 1 | 59,803 | 9,017 | 50,841 | 50,088 | 49 |
| Game 2 | 59,022 | 3,692 | 55,338 | 54,653 | 48 |

All event anchors matched exact source keys. Each game has 39 reference spans
with no intervening recorded events. Their observed interior counts/raw-D/
decoded-D are 16,518 / 16,518 / 6,451 in Game 1 and 13,640 / 13,640 / 3,131 in
Game 2. These are review counts, not a target mask or performance score; spans
can overlap and absent event records do not prove absent play. The report lists
intervening event types for every span, including possible RECOVERY restarts.

The missing-ball classifier vector is constant in these samples, approximately
H/A/D = 0.322095 / 0.222604 / 0.455301. Clean training priors are
0.318666 / 0.222589 / 0.458744. Thus the decoder's fixed posterior/prior ratios
are about 1.010760 / 1.000066 / 0.992494. Including the fixed self-transition
term, the steady self-path log contributions are approximately
0.006075 / -0.006454 / -0.009051 per frame. This explains a tendency toward H
over long unobserved runs even though raw argmax is D; boundary costs and future
observations also matter. It does not establish which label is correct.
The longest changed missing-context runs can exceed two minutes, so missing-data
domain behavior is a material limitation despite the earlier DFL test result.
No prior, emission weight, threshold or model was adjusted after this diagnosis.
Mechanism calculations are retained in
`external_artifacts/local-runtime/metrica-decoder-mechanism-v2.json`.

### Portable primary bundle and local-only ATD adapter

`external_baseline.inference_bundle` copies the primary's exact model/decoder,
source, feature contract, pinned dependencies, license and training/assessment
provenance. It reads no match data or predictions. Known packaged files and
runtime versions are verified before model deserialization; inputs/models and
source are immutable during construction. The ZIP includes no data or venv.

```bash
external_artifacts/local-runtime/training-venv/bin/python -B -m external_baseline.inference_bundle build \
  --snapshot external_artifacts/J03WR9-expanded-frozen-v1 \
  --output external_artifacts/inference-bundle-reproduction
```

The final directory is `external_artifacts/inference-bundle-v1/`, with a portable
archive at `external_artifacts/inference-bundle-v1.zip` and release verification
in `inference-bundle-v1-release.json`. The model SHA-256 remains
`d1f4fdd7e9d7ea1a18b42e505dd9bef741379ff4bf81a039530f69afcc6a6f10`;
decoder SHA-256 remains
`2aa5b5f1c777fe9c2c71b7bdb894082b22b967dae5b67664be9b5c7871bafa74`.

`external_baseline.atd_inference` requires explicit input paths and a local
operator CLI flag. It parses normalized 25-Hz FIFA metadata, declared pitch
dimensions, local/visiting IDs (or documented FIFA team order), inclusive
1-based half bounds and per-frame-range DataFormatSpecifications. PlayerChannel
references determine raw slot identity/team/x-y ordering; roster order is not
assumed. Public Sample-Game-3 metadata parsed successfully: 35 roster players,
22 initial slots and 11 changing format specifications. Its full tracking data
was not downloaded or inferred; only public metadata and a first-line syntax
check informed compatibility. Actual official metadata remains uninspected.

All raw ATD IDs must be exactly 1..199319 for the default tactical contract.
The adapter maps them to video/submission frames 0..199318, derives centred metre
features and backward ball speed, and decodes halves independently. No player
velocity is derived from anonymous slots. Missing axes stay missing, finite
outside values stay outside, malformed/conflicting schemas fail rather than
guessing, and no GT offset/calibration or frame filling occurs. Only metadata
half scopes are inferred; outside them the CSV label is X. Missing ball alone
does not force a D or X label. Empty/standalone-NaN ball fields mean absent
records; explicit NaN pairs retain a present-but-unobserved record.

**The following command is for the user to execute locally, never an agent
invocation on actual official assets:**

```bash
external_artifacts/local-runtime/training-venv/bin/python -B external_artifacts/inference-bundle-v1/run_tactical.py \
  --bundle external_artifacts/inference-bundle-v1 \
  --metadata /YOUR/LOCAL/tactical_atd.xml \
  --tracking /YOUR/LOCAL/tactical_atd.txt \
  --output local_official_artifacts/run1 --operator-local
```

The existing project venv can run this; no additional libraries were installed.
For a new venv follow the bundled README, keeping pip cache disabled and temp
files on the project drive. `local_official_artifacts/` is now Git-ignored;
its actual contents must not be opened by agents. Output includes decoded and
raw `frame,label` CSVs, scoped feature/probability databases, a format-only report
and ready hashes. Existing outputs are rejected. Unsupported/missing metadata
is a local compatibility error, not permission to inspect or tune on the official
match. Official correctness and competition score have not been validated.

### Verification

All 89 synthetic regression tests passed. New cases cover exact decoder-change
counts, gap-safe timelines, event end=0 placeholders, conflicting reference gaps,
import/help without data/model I/O, explicit channel/team mapping, layout
changes, missing/outside coordinates, units/FPS/period conflicts, raw ID errors,
no-fit/no-GT execution, failure readiness and no-overwrite. A complete synthetic
199,319-row CSV passed the pure official format validator without loading GT;
only submission indices 1,2,5,6 were scoped under that fixture's metadata.
Repeated CSV/database outputs were byte-identical. No real official input was
used in any of these tests. The log is
`external_artifacts/local-runtime/diagnosis-bundle-regression-tests.log`.

Both generated HTML files passed JavaScript syntax, DOM/control and canvas
drawing smoke checks using Node, including half changes and event jumps. The
actual ZIP was extracted to another temporary location and verified outside
the project cwd. The actual frozen primary then ran through that relocated CLI
on an eight-row synthetic ATD fixture; submission, raw submission, features and
predictions matched the original-location outputs byte-for-byte. Bundle/source/
model hashes and exact runtime versions passed verification. These checks prove
packaging and adapter mechanics, not possession quality on official data.
