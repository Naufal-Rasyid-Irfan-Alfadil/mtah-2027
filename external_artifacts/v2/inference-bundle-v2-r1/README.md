# V2 adapter revision 1

Frozen classifier, features, router thresholds and decoder unchanged. This revision adds an explicit public organizer period source; provider is still the default.

Verify: `python -B verify_bundle.py --runtime`.

Operator-only inference: `python -B run_tactical.py --bundle . --metadata PATH_XML --tracking PATH_TXT --output NEW_PATH --period-source organizer-public --game BAR-ATH --operator-local`.

Organizer source is the included public games.py function half_video_blocks, with published video indices converted to inclusive raw ATD IDs by +1. It is not a zero-based guess about provider fields. Both halves remain separate for feature state and decoder calls. Rows outside the published per-half scope are X. The recording length/FPS must match the selected public game. No GT label or mask file, video, homography or Smart Tagging is opened.

External model-selection provenance is inherited; the changed adapter is separately attested in provenance/adapter. Agent validation uses synthetic/public metadata only; actual official input compatibility and predictive quality remain unverified.
