# MTAH 2027 development handoff

The available submission candidate is frozen V2/R, adapter revision 1.

## Git handoff update, 14 November 2026

Audited V3 artifacts and the restored V2 release-readiness tree are now included
for Git handoff. Read external_artifacts/README.md and the checksum inventory
external_artifacts/handoff-inventory-20261114.json (498 listed files). New
artifact attributes preserve exact bytes across checkout. This includes Q01-Q06
review clips; the review remains 0/6. Research gates and V2 candidate status are
unchanged. Raw datasets, runtime and official inputs/GT/results stay local.
See section 33 of KONTEKS_PERCAKAPAN.md for exclusions and author configuration.

## Local readiness update — 12 November 2026, 19:59 WIB

Read `docs/kesiapan_pengumpulan_20261112.md` for the current operator commands,
machine audit, source register and remaining gates. Windows checkout converted
43 bundle files to CRLF; do not run that original working-tree bundle. An exact
136-file handoff was restored from checksum-matching HEAD blobs to
`external_artifacts/release-readiness-20261112/source/`, without modifying old
artifacts or manifests. A project-drive venv now matches every runtime pin.

`validation-final/report.json` under that readiness directory records 26 passing
synthetic tests, frozen-R synthetic checks, and 49 verified ZIP members plus a
successful relocated-bundle verification. Use its ZIP and the documented venv.
DFL dataset fallback remains pending external acquisition; official inference,
compatibility with actual official inputs, and predictive quality are untested.
No detector/fusion or new possession candidate was implemented.

## Start here

- `KONTEKS_PERCAKAPAN.md`: Indonesian conversation context, latest decisions, restrictions and V3 status.
- `penjelasan_file.md`: project file explanations.
- `docs/perbandingan_v1_v2_eksternal.md`: external A/R comparison and limitations.
- `docs/audit_adapter_half_bounds.md`: timeline and period adapter audit.
- `external_artifacts/v2/inference-bundle-v2-r1/README.md`: portable V2 bundle.
- `HANDOFF_MANIFEST.json`: checksums for included project files.

The original project history is not included. This is a separate source snapshot.
Official match inputs, GT, per-frame outputs, notebook outputs, downloaded datasets, caches and virtual environments are excluded. Only manifest-listed V2 bundle files and named aggregate external reports are included under external_artifacts.

## V3 status on 12 November 2026

V3 has not been implemented or trained. Preserve V2 and its checksums.
Do not create production modules for a modality before data feasibility passes.
DFL J03WOH/J03WPY are training; J03WQQ is reused development; J03WMX is additional assessment with unverified legacy history, not an established untouched test.

SoccerTrack v2 v1.2 is a potential geometry source (CC BY 4.0), but the file host is gated, published schema/timebase descriptions need reconciliation, and its reconstructed/interpolated ball track is not independent GT for out/restart. Metrica SAMPLEGAME4 access, export rights, version and independent targets remain unverified. No visual pretrained weights have been selected.

Component accuracy does not establish end-to-end possession improvement. Evaluate video/tagging possession benefit only where paired external modalities and independent targets exist. Use DFL to verify unchanged V2 fallback when modalities are absent. Freeze protocols and relevant gates before scoring; do not select using official match scores.

The execution machine is a different GPU-equipped machine according to the operator; GPU model/VRAM, RAM, disk and runtime have not been verified. The audit laptop specifications are not the execution budget. No throughput estimate has been established.

No agent access to official match video, tracking, homography, Smart Tagging, GT or per-frame derivatives. No official-video fitting/calibration, prediction comparison, or uploads to AI services. Operator-only official inference after pipeline freeze.

Internal submission target: 15 November 2026; this is not a claim about the organizer deadline. Keep V2 available if V3 is not validated in time.

## Latest external geometry reference status, 13 November 2026

Read sections 26-32 of KONTEKS_PERCAKAPAN.md before older V3 status above.
SoccerTrack 117093 now has 54 operator pixel annotations across three raw
frames from one camera, complete self-reported overlay exposure provenance,
passing annotation preflight, and qualitative crop review. Independent blinding
and absolute geometric accuracy are not established. No model scoring or fitting
was performed on these references.

The reference snapshot is external_artifacts/v3/117093-reference-freeze-20261113/;
all 73 member checksums were verified. Its manifest and adjacent verification
report bind the snapshot. Quantify annotation uncertainty and freeze numerical
gates before component scoring. Independent synchronized possession targets
remain unavailable. No V3 production candidate is selected; preserve V2/R r1.

Section 27 records preparation of an 18-crop repeat-measurement package at
external_artifacts/v3/117093-repeatability-task-20261113/. Source snapshot hashes
and pixel-exact crops are verified. The repeat CSV now contains 18/18 operator
measurements. The operator confirmed neither prior-coordinate nor model-overlay
exposure during the repeat session; evidence is self-report, not independently
verified blinding. Section 29 records the completed paired analysis: absolute
median/p95/max displacement 1/2.15/3 px, 18 valid pairs, one camera. Eleven input/
statistical checks passed. Results and nine checksum-verified snapshot members:
external_artifacts/v3/117093-repeatability-analysis-20261113/.
See docs/protokol_pengukuran_ulang_117093.md. The descriptive displacement is
not absolute accuracy or a production tolerance. A justified downstream error
budget and independent synchronized possession targets remain unavailable.
No candidate geometry scoring or fitting was performed. Preserve V2/R r1.

Latest execution update: section 30 and docs/kelanjutan_v3_possession_117093.md.
Five pinned publisher source/license files passed Git blob verification. The
Frame source declares ballStatus. Actual XML now confirms dense HOME/AWAY/
BALLOUT/NEUTRAL statuses; semantics and independent origin remain unverified.
Earlier unauthenticated small dataset requests returned HTTP 401.
All three explicitly requested raw 117093 files (217,000,782 bytes total) are
now present with matching sizes. Both small non-LFS payload Git blobs passed;
the XML also matches the operator-transcribed publisher LFS SHA256.
See section 32 and payload-report.json in the readiness directory.
URLs and expected sizes/blob hashes are in
docs/soccertrack_v1_2_117093_possession_inputs.json.
The checksum-first streaming research auditor is ready; 13 synthetic checks
passed. Findings/report: external_artifacts/v3/117093-possession-readiness-20261113/.
No production module, training or inference was performed. Do not ask for more
field-line annotations. Clock consensus: raw minus released time is 1040 ms
in half 1 (1086 anchor pairs) and 2700007 ms in half 2 (1080). This is shared
provider evidence, not independent visual proof. Seven clock checks pass.
The next dependency is target semantics/independence. Six 12-second external
review clips Q01-Q06 are ready at v3/117093-possession-review-pilot-20261113/;
the review CSV is empty (0/6), target at 6.00 s. No provider labels are rendered.
Ask for live/dead/uncertain and visual kit colour, not forced Home/Away. Clips
are silent; unclear cases stay uncertain. See docs/audit_target_possession_117093.md.
V2 remains the candidate.

## External sources

- DFL: https://github.com/spoho-datascience/idsse-data and https://doi.org/10.6084/m9.figshare.28196177 (CC BY 4.0; credit DFL and Bassek et al.).
- Metrica sample data pinned commit: https://github.com/metrica-sports/sample-data/tree/e706dd506b360d69d9d123d5b8026e7294b13996 (rights beyond README acknowledgement not verified).
- SoccerTrack: https://huggingface.co/datasets/atomscott/soccertrack-v2 and https://github.com/AtomScott/SoccerTrack-v2/blob/main/LICENSE-DATA
- SAMPLEGAME4: https://www.metrica-sports.com/blog/automatic-tagging-detect-patterns-that-occur-in-the-game

## Environment and bundle verification

Create a virtual environment on the project drive and install pinned requirements there; do not commit it. Read the portable bundle instructions before running its checksum/runtime verifier. Do not run official inference on behalf of the operator. Dataset preparation and training require separately acquired, provenance-verified external inputs.
