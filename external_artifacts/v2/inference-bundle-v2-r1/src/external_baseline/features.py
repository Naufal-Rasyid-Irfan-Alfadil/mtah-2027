"""Observation-only planar features. Import and --help perform no dataset I/O."""

import argparse
from contextlib import closing
from dataclasses import dataclass
from itertools import groupby
import json
import math
from pathlib import Path
import platform
import sqlite3
import time
from collections import deque
from statistics import median

from .contracts import CONTRACT_VERSION, FrameKey, SPLITS, STEP_US
from .prepare import REPO, git_metadata, peak_memory_bytes, sha256

FEATURE_VERSION = 1
# This ordered allowlist is the only future model input; keys/time/split are not features.
FEATURE_UNITS = {
    "ball_record_present": "binary",
    "ball_x_observed": "binary",
    "ball_y_observed": "binary",
    "ball_xy_observed": "binary",
    "ball_x_m": "m",
    "ball_y_m": "m",
    "ball_speed_mps": "m/s",
    "home_records": "count",
    "home_xy_observed": "count",
    "away_records": "count",
    "away_xy_observed": "count",
    "nearest_home_m": "m",
    "nearest_away_m": "m",
    "ball_longitudinal_margin_m": "m",
    "ball_lateral_margin_m": "m",
    "ball_inside_pitch": "binary",
}
FEATURE_NAMES = tuple(FEATURE_UNITS)
CONTEXT_UNITS = dict(ball_xy_fraction_1s='fraction', ball_xy_age_s='s',
                    nearest_home_median_1s='m', nearest_away_median_1s='m')
CONTEXT_NAMES = tuple(CONTEXT_UNITS)


@dataclass(frozen=True)
class EntityPosition:
    """Present entity record in centred metres; None means a missing axis.

    Nonfinite numbers are treated as missing defensively. Entity IDs are only
    uniqueness keys; no player velocity or identity-dependent feature is built.
    """
    entity_id: str
    team: str
    x_m: float | None
    y_m: float | None


def _finite(value):
    return value if value is not None and math.isfinite(value) else None


class FrameFeatureExtractor:
    """Compute fixed, unfitted features while retaining only the preceding ball.

    Input is one complete observation frame at a time, ordered by match/period/N.
    Outputs an ordered numeric dictionary (None for missing). Speed is backward
    planar displacement / 0.04 seconds, only when both complete ball observations
    have adjacent N and timestamps in the same match/period. Every frame updates
    state, including absent/partial balls. No carry-forward or future lookahead.
    """

    def __init__(self, length_m, width_m):
        if any(not math.isfinite(v) or v <= 0 for v in (length_m, width_m)):
            raise ValueError("pitch dimensions must be positive finite metres")
        self.length_m, self.width_m = length_m, width_m
        self.previous_ball = None

    def extract(self, key: FrameKey, timestamp_us: int, entities):
        """Return the 16 observation-only features for this frame; see class contract.

        Record counts include partial/missing coordinate records, while xy counts
        require both finite axes. Nearest distances require a complete ball and
        at least one complete player of that team. Outside coordinates are kept;
        signed margins are negative outside and zero exactly on a pitch boundary.
        """
        seen, ball, teams = set(), None, {"H": [], "A": []}
        for entity in entities:
            if entity.entity_id in seen:
                raise ValueError("duplicate entity in observation frame")
            seen.add(entity.entity_id)
            xy = (_finite(entity.x_m), _finite(entity.y_m))
            if entity.team == "BALL":
                if ball is not None:
                    raise ValueError("multiple balls in observation frame")
                ball = xy
            elif entity.team in teams:
                teams[entity.team].append(xy)
            else:
                raise ValueError("unknown observation team")
        x, y = ball if ball is not None else (None, None)
        complete = x is not None and y is not None
        result = dict.fromkeys(FEATURE_NAMES)
        result.update(ball_record_present=int(ball is not None), ball_x_observed=int(x is not None),
                      ball_y_observed=int(y is not None), ball_xy_observed=int(complete),
                      ball_x_m=x, ball_y_m=y)
        previous = self.previous_ball
        if complete and previous is not None:
            old_key, old_time, old_x, old_y = previous
            if (key.match_id, key.period, key.source_frame - 1, timestamp_us - STEP_US) == (old_key.match_id, old_key.period, old_key.source_frame, old_time):
                result["ball_speed_mps"] = math.hypot(x - old_x, y - old_y) / (STEP_US / 1_000_000)
        self.previous_ball = (key, timestamp_us, x, y) if complete else None
        for team, prefix in (("H", "home"), ("A", "away")):
            valid = [(px, py) for px, py in teams[team] if px is not None and py is not None]
            result[prefix + "_records"] = len(teams[team])
            result[prefix + "_xy_observed"] = len(valid)
            if complete and valid:
                result["nearest_" + prefix + "_m"] = min(math.hypot(x-px, y-py) for px, py in valid)
        if x is not None:
            result["ball_longitudinal_margin_m"] = self.length_m / 2 - abs(x)
        if y is not None:
            result["ball_lateral_margin_m"] = self.width_m / 2 - abs(y)
        if complete:
            result["ball_inside_pitch"] = int(abs(x) <= self.length_m/2 and abs(y) <= self.width_m/2)
        if any(v is not None and not math.isfinite(v) for v in result.values()):
            raise ValueError("feature arithmetic overflow")
        return result


class ContextFeatureExtractor(FrameFeatureExtractor):
    """V2 causal trailing context, appended to the unchanged 16 v1 features.

    Input: FrameKey, microseconds and observation entities in centred metres.
    Output: ordered dictionary of 20 values; classifier drops signed x/y (18).
    The 25-frame window includes the present frame. Missing distances remain
    None; no last coordinate is imputed. Age is seconds since complete ball,
    None before first complete observation. All state resets on any key/time
    discontinuity, including match/half changes. Anonymous IDs are never tracked.
    """
    def __init__(self, length_m, width_m):
        super().__init__(length_m, width_m)
        self.window = deque(maxlen=25)
        self.last_complete = None
        self.previous_key_time = None

    def extract(self, key, timestamp_us, entities):
        previous = self.previous_key_time
        if previous != (key.match_id, key.period, key.source_frame-1, timestamp_us-STEP_US):
            self.window.clear()
            self.last_complete = None
            self.previous_ball = None
        values = super().extract(key, timestamp_us, entities)
        self.previous_key_time = (key.match_id, key.period, key.source_frame, timestamp_us)
        self.window.append((values['ball_xy_observed'], values['nearest_home_m'], values['nearest_away_m']))
        if values['ball_xy_observed']:
            self.last_complete = timestamp_us
        values['ball_xy_fraction_1s'] = sum(r[0] for r in self.window)/len(self.window)
        values['ball_xy_age_s'] = ((timestamp_us-self.last_complete)/1e6
                                   if self.last_complete is not None else None)
        for column, name in ((1, 'nearest_home_median_1s'), (2, 'nearest_away_median_1s')):
            observed = [r[column] for r in self.window if r[column] is not None]
            values[name] = median(observed) if observed else None
        return values


def _validate_observation_db(db):
    """Validate v1 observation schema/units; never inspect or attach target files."""
    expected = {
        "frames": ["match_id", "period", "source_frame", "timestamp_us"],
        "observations": ["match_id", "period", "source_frame", "entity_id", "team", "x_m", "y_m", "x_reason", "y_reason"],
        "metadata": ["json"],
    }
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if tables != set(expected):
        raise ValueError("expected a separate v1 observation database, without target tables")
    for table, columns in expected.items():
        if [r[1] for r in db.execute(f"PRAGMA table_info({table})")] != columns:
            raise ValueError(f"unexpected observation schema: {table}")
    metadata_rows = db.execute("SELECT json FROM metadata").fetchall()
    if len(metadata_rows) != 1:
        raise ValueError("one observation metadata record required")
    metadata = json.loads(metadata_rows[0][0])
    if (metadata.get("contract_version"), metadata.get("coordinate_unit"), metadata.get("origin"), metadata.get("fps")) != (CONTRACT_VERSION, "m", "pitch_center", 25):
        raise ValueError("unsupported observation contract/units/FPS")
    # Orphan records must not silently disappear in the frame join.
    if db.execute("""SELECT 1 FROM observations o LEFT JOIN frames f USING(match_id,period,source_frame)
                     WHERE f.match_id IS NULL LIMIT 1""").fetchone():
        raise ValueError("observation without a timeline frame")
    return metadata


def iter_feature_frames(db):
    """Yield (FrameKey, UTC microseconds, numeric features) from read-only observations.

    A frame with no entity rows is retained. SQL NULL stays missing. Keys remain
    original; grouping never compacts gaps or joins across periods. Memory holds
    one frame of entities, not a whole match. Caller owns the connection.
    """
    metadata = _validate_observation_db(db)
    extractor = FrameFeatureExtractor(metadata["length_m"], metadata["width_m"])
    rows = db.execute("""SELECT f.match_id,f.period,f.source_frame,f.timestamp_us,
                         o.entity_id,o.team,o.x_m,o.y_m
                         FROM frames f LEFT JOIN observations o USING(match_id,period,source_frame)
                         ORDER BY f.match_id,f.period,f.source_frame,o.entity_id""")
    for identity, group in groupby(rows, key=lambda row: row[:4]):
        match_id, period, frame, stamp = identity
        if match_id != metadata["match_id"] or period not in SPLITS:
            raise ValueError("frame inconsistent with match/period metadata")
        key = FrameKey(match_id, period, frame)
        entities = (EntityPosition(*row[4:]) for row in group if row[4] is not None)
        yield key, stamp, extractor.extract(key, stamp, entities)


def extract_features(observations, output):
    """Write features.sqlite, coverage report and ready manifest in a new directory.

    Reads only the explicit observations.sqlite and its ready parent manifest,
    never targets.sqlite or parent validation reports. Input DB is opened mode=ro
    with query_only. No fitting, imputation, scaling, label join or threshold
    selection occurs. Failures retain FAILED.json without a ready manifest.
    """
    source = Path(observations).resolve(strict=True)
    if source.name != "observations.sqlite":
        raise ValueError("explicit observations.sqlite path required")
    parent_path = source.parent / "manifest.json"
    parent = json.loads(parent_path.read_text(encoding="utf-8"))
    if parent.get("status") != "ready" or parent.get("contract_version") != CONTRACT_VERSION:
        raise ValueError("ready v1 preparation manifest required")
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    try:
        sources = {str(p.relative_to(REPO)): sha256(p) for p in sorted((REPO/"external_baseline").glob("*.py"))}
        input_hash, parent_hash = sha256(source), sha256(parent_path)
        report = {"feature_version": FEATURE_VERSION, "periods": []}
        summaries = {}
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as db, closing(sqlite3.connect(output/"features.sqlite")) as dest:
            db.execute("PRAGMA query_only=ON")
            db.execute("PRAGMA cache_size=-8192")
            db.execute("PRAGMA temp_store=FILE")
            dest.execute("PRAGMA cache_size=-8192")
            columns = ",".join(f"{name} REAL" for name in FEATURE_NAMES)
            dest.execute(f"""CREATE TABLE features(match_id TEXT, period INTEGER, source_frame INTEGER,
                timestamp_us INTEGER, split TEXT, {columns},
                PRIMARY KEY(match_id,period,source_frame)) WITHOUT ROWID""")
            placeholders = ",".join("?" for _ in range(5 + len(FEATURE_NAMES)))
            batch = []
            for key, stamp, values in iter_feature_frames(db):
                identity = (key.match_id, key.period)
                if identity not in summaries:
                    summaries[identity] = {
                        "match_id": key.match_id, "period": key.period, "split": SPLITS[key.period],
                        "frames": 0, "first_frame": key.source_frame, "last_frame": key.source_frame,
                        "features": {name: {"defined": 0, "missing": 0, "min": None, "max": None, "sum": 0.0} for name in FEATURE_NAMES}}
                summary = summaries[identity]
                summary["frames"] += 1
                summary["last_frame"] = key.source_frame
                for name, value in values.items():
                    stat = summary["features"][name]
                    if value is None:
                        stat["missing"] += 1
                    else:
                        stat["defined"] += 1
                        stat["min"] = value if stat["min"] is None else min(stat["min"], value)
                        stat["max"] = value if stat["max"] is None else max(stat["max"], value)
                        stat["sum"] += value
                batch.append((key.match_id, key.period, key.source_frame, stamp, SPLITS[key.period], *values.values()))
                if len(batch) == 4096:
                    dest.executemany(f"INSERT INTO features VALUES({placeholders})", batch)
                    dest.commit()
                    batch.clear()
            dest.executemany(f"INSERT INTO features VALUES({placeholders})", batch)
            if not summaries:
                raise ValueError("empty observation timeline")
            dest.execute("CREATE TABLE feature_metadata(json TEXT NOT NULL)")
            dest.execute("INSERT INTO feature_metadata VALUES(?)", (json.dumps({"feature_version": FEATURE_VERSION, "feature_names": FEATURE_NAMES, "units": FEATURE_UNITS}, sort_keys=True),))
            dest.commit()
        for summary in summaries.values():
            for stat in summary["features"].values():
                total = stat.pop("sum")
                stat["coverage"] = stat["defined"] / summary["frames"]
                stat["mean"] = total/stat["defined"] if stat["defined"] else None
            report["periods"].append(summary)
        report.update(elapsed_seconds=round(time.perf_counter()-started, 3), process_peak_resident_bytes=peak_memory_bytes())
        if sha256(source) != input_hash or sha256(parent_path) != parent_hash:
            raise ValueError("observation input/manifest changed during extraction")
        if any(sha256(REPO/name) != digest for name, digest in sources.items()):
            raise ValueError("source changed during extraction")
        manifest = {"status": "ready", "feature_version": FEATURE_VERSION, "contract_version": CONTRACT_VERSION,
                    "feature_names": FEATURE_NAMES, "units": FEATURE_UNITS,
                    "input": {"observations": str(source), "sha256": input_hash, "parent_manifest_sha256": parent_hash},
                    "source_sha256": sources, "git": git_metadata(), "python": platform.python_version(), "sqlite": sqlite3.sqlite_version,
                    "output_sha256": sha256(output/"features.sqlite"),
                    "policy": {"temporal": "backward adjacent ball only; reset on gaps, missing, match or half boundaries",
                               "missing": "SQL NULL; no imputation", "coordinates": "centred metres, outside retained",
                               "fit": "none", "target_access": "none", "model_inputs": "feature_names allowlist only"},
                    "provenance": {"decisions": "Basic geometry and contiguous differences from user-approved feature stage; no thresholds, old project code or official-match selection.",
                                   "parent_attribution": parent.get("provenance", {})}}
        for name, value in (("feature_report.json", report), ("manifest.json", manifest)):
            (output/name).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+"\n", encoding="utf-8")
        return report
    except Exception as error:
        (output/"FAILED.json").write_text(json.dumps({"status": "failed", "error": str(error)})+"\n", encoding="utf-8")
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observations", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = extract_features(args.observations, args.output)
    print(json.dumps({"output": str(args.output), "features": len(FEATURE_NAMES),
                      "periods": [{k: v for k, v in p.items() if k != "features"} for p in report["periods"]]}, indent=2))


if __name__ == "__main__":
    main()
