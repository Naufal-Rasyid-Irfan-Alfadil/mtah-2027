# MTAH 2027 development handoff

The available submission candidate is frozen V2/R, adapter revision 1.

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

## External sources

- DFL: https://github.com/spoho-datascience/idsse-data and https://doi.org/10.6084/m9.figshare.28196177 (CC BY 4.0; credit DFL and Bassek et al.).
- Metrica sample data pinned commit: https://github.com/metrica-sports/sample-data/tree/e706dd506b360d69d9d123d5b8026e7294b13996 (rights beyond README acknowledgement not verified).
- SoccerTrack: https://huggingface.co/datasets/atomscott/soccertrack-v2 and https://github.com/AtomScott/SoccerTrack-v2/blob/main/LICENSE-DATA
- SAMPLEGAME4: https://www.metrica-sports.com/blog/automatic-tagging-detect-patterns-that-occur-in-the-game

## Environment and bundle verification

Create a virtual environment on the project drive and install pinned requirements there; do not commit it. Read the portable bundle instructions before running its checksum/runtime verifier. Do not run official inference on behalf of the operator. Dataset preparation and training require separately acquired, provenance-verified external inputs.
