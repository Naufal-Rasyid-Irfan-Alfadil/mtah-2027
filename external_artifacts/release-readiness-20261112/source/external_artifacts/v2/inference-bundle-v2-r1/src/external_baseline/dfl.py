"""Streaming DFL reader. No official loaders, model imports or implicit paths.

XML is consumed frame by frame and removed from its parent. SQLite handles
joins/sorting on disk; memory is bounded by one batch and metadata, not match
length. Coordinates follow the DFL metre/centred convention (see docs).
"""

from collections import Counter
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sqlite3
import xml.etree.ElementTree as ET

from .contracts import CONTRACT_VERSION, FPS, PERIODS, SPLITS, STEP_US, map_target


@dataclass(frozen=True)
class MatchInfo:
    match_id: str
    home_id: str
    away_id: str
    length_m: float
    width_m: float
    players: dict


def coordinate(raw):
    """Return (metres, reason); no rescaling or clipping of finite DFL values."""
    if raw is None or not raw.strip():
        return None, "missing"
    try:
        value = float(raw)
    except ValueError:
        return None, "malformed"
    return (value, None) if math.isfinite(value) else (None, "nonfinite")


def timestamp_us(raw):
    """Parse timezone-aware ISO timestamp into exact UTC microseconds; fail if absent."""
    if not raw:
        raise ValueError("missing timestamp")
    value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if value.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    delta = value.astimezone(timezone.utc) - datetime(1970, 1, 1, tzinfo=timezone.utc)
    return (delta.days * 86400 + delta.seconds) * 1_000_000 + delta.microseconds


def read_match_info(path):
    """Read explicit external metadata path; return IDs, roster and pitch in metres.

    No result, names, kickoff or lineup attributes become observations. Team
    order is irrelevant; contradictory role/ID or roster assignments fail.
    """
    root = ET.parse(path).getroot()
    general = root.find("./MatchInformation/General")
    env = root.find("./MatchInformation/Environment")
    if general is None or env is None:
        raise ValueError("missing match metadata")
    home = general.get("HomeTeamId")
    away = general.get("AwayTeamId") or general.get("GuestTeamId")
    if general.get("AwayTeamId") and general.get("GuestTeamId") != general.get("AwayTeamId") and general.get("GuestTeamId"):
        raise ValueError("contradictory away IDs")
    if not home or not away or home == away or not general.get("MatchId"):
        raise ValueError("invalid match/team IDs")
    length, width = coordinate(env.get("PitchX"))[0], coordinate(env.get("PitchY"))[0]
    if length is None or width is None or min(length, width) <= 0:
        raise ValueError("invalid pitch dimensions")
    players = {}
    found = set()
    for team in root.findall("./MatchInformation/Teams/Team"):
        tid = team.get("TeamId")
        if tid not in (home, away):
            continue
        expected = "home" if tid == home else "guest"
        if team.get("Role") not in (expected, "away" if tid == away else "home"):
            raise ValueError("team role conflicts with metadata")
        found.add(tid)
        for player in team.findall("./Players/Player"):
            pid = player.get("PersonId")
            if not pid or (pid in players and players[pid] != tid):
                raise ValueError("conflicting player identity")
            players[pid] = tid
    if found != {home, away} or not players:
        raise ValueError("missing team roster")
    return MatchInfo(general.get("MatchId"), home, away, length, width, players)


def _table(db, table, columns, key):
    """Create a table and reject conflicting duplicates using NULL-safe equality."""
    db.execute(f"CREATE TABLE {table} ({columns}, PRIMARY KEY ({','.join(key)})) WITHOUT ROWID")
    names = [row[1] for row in db.execute(f"PRAGMA table_info({table})")]
    same_key = " AND ".join(f"old.{n} IS NEW.{n}" for n in key)
    different = " OR ".join(f"old.{n} IS NOT NEW.{n}" for n in names if n not in key)
    db.execute(f"""CREATE TRIGGER conflict_{table} BEFORE INSERT ON {table}
        WHEN EXISTS(SELECT 1 FROM {table} old WHERE {same_key} AND ({different}))
        BEGIN SELECT RAISE(ABORT, 'conflicting duplicate in {table}'); END""")


def parse_positions(path, info, observations_path, targets_path, batch_size=4096):
    """Prepare two databases from one explicit external positions XML.

    Input coordinates are centred metres; timestamps must agree with 25 Hz for
    every record of each stream, including out-of-order records and gaps. Join
    keys include match/period/N; no rows are synthesized across missing frames.
    Missing coordinates become SQL NULL with reasons. Raw targets live only in
    targets_path. Conflicts raise, leaving no ready manifest (caller owns it).
    """
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    stats = Counter()
    with Path(path).open("rb") as xml_file, closing(sqlite3.connect(observations_path)) as obs, closing(sqlite3.connect(targets_path)) as tgt:
        for db in (obs, tgt):
            db.execute("PRAGMA cache_size=-8192")
            db.execute("PRAGMA temp_store=FILE")
        key = ("match_id", "period", "source_frame")
        _table(obs, "frames", "match_id TEXT, period INTEGER, source_frame INTEGER, timestamp_us INTEGER", key)
        _table(obs, "observations", "match_id TEXT, period INTEGER, source_frame INTEGER, entity_id TEXT, team TEXT, x_m REAL, y_m REAL, x_reason TEXT, y_reason TEXT", (*key, "entity_id"))
        _table(tgt, "targets", "match_id TEXT, period INTEGER, source_frame INTEGER, ball_status TEXT, ball_possession TEXT, label TEXT, valid_target INTEGER, invalid_reason TEXT", key)
        frame_batch, obs_batch, target_batch = [], [], []

        def flush():
            for db, table, rows, counter in ((obs, "frames", frame_batch, "repeated_frame_keys"), (obs, "observations", obs_batch, "identical_observation_duplicates"), (tgt, "targets", target_batch, "identical_target_duplicates")):
                if rows:
                    before = db.total_changes
                    db.executemany(f"INSERT OR IGNORE INTO {table} VALUES ({','.join('?' for _ in rows[0])})", rows)
                    stats[counter] += len(rows) - (db.total_changes - before)
                    rows.clear()
            obs.commit()
            tgt.commit()

        stack = []
        stream = None
        pitch_seen = False
        match_seen = False
        for event, elem in ET.iterparse(xml_file, events=("start", "end")):
            if event == "start":
                stack.append(elem)
                if elem.tag == "MetaData":
                    if elem.get("MatchId") != info.match_id:
                        raise ValueError("positions metadata match mismatch")
                    match_seen = True
                if elem.tag == "FrameSet":
                    if stream is not None:
                        raise ValueError("nested FrameSet")
                    if elem.get("MatchId") != info.match_id:
                        raise ValueError("FrameSet match mismatch")
                    period = PERIODS.get(elem.get("GameSection"))
                    if period is None:
                        raise ValueError("unsupported GameSection")
                    tid, pid = elem.get("TeamId"), elem.get("PersonId")
                    if tid == "BALL":
                        team, entity = "BALL", "BALL"
                    elif tid in (info.home_id, info.away_id):
                        if info.players.get(pid) != tid:
                            raise ValueError("tracking player/team inconsistent with roster")
                        team, entity = ("H" if tid == info.home_id else "A"), pid
                    elif tid and tid.lower() == "referee":
                        team, entity = "SKIP", pid
                    else:
                        raise ValueError("unknown tracking team")
                    stream = (period, team, entity)
                    anchor = previous = None
                    stats["streams"] += 1
                continue
            if elem.tag == "PitchSize":
                if (coordinate(elem.get("X"))[0], coordinate(elem.get("Y"))[0]) != (info.length_m, info.width_m):
                    raise ValueError("positions pitch dimensions disagree")
                pitch_seen = True
            elif elem.tag == "Frame":
                if stream is None:
                    raise ValueError("Frame outside FrameSet")
                period, team, entity = stream
                n = int(elem.attrib["N"])
                if n < 0:
                    raise ValueError("negative source frame")
                t = timestamp_us(elem.get("T"))
                if anchor is None:
                    anchor = (n, t)
                elif t - anchor[1] != (n - anchor[0]) * STEP_US:
                    raise ValueError("timestamp/frame cadence differs from 25 Hz")
                if previous is not None and n <= previous:
                    stats["nonincreasing_stream_records"] += 1
                previous = n
                if team != "SKIP":
                    k = (info.match_id, period, n)
                    x, xr = coordinate(elem.get("X"))
                    y, yr = coordinate(elem.get("Y"))
                    frame_batch.append((*k, t))
                    obs_batch.append((*k, entity, team, x, y, xr, yr))
                    if team == "BALL":
                        status, possession = elem.get("BallStatus"), elem.get("BallPossession")
                        target = map_target(status, possession)
                        target_batch.append((*k, status, possession, target.label, int(target.valid_target), target.invalid_reason))
                    stats["input_observation_records"] += 1
                    if len(obs_batch) >= batch_size:
                        flush()
                else:
                    stats["ignored_referee_records"] += 1
            elif elem.tag == "FrameSet":
                if anchor is None:
                    raise ValueError("empty FrameSet")
                stream = None
            # Removing children, not just clear(), prevents empty-node accumulation.
            stack.pop()
            if stack:
                stack[-1].remove(elem)
            elem.clear()
        flush()
        if not pitch_seen or not match_seen:
            raise ValueError("missing positions metadata/pitch")
        periods = [r[0] for r in obs.execute("SELECT DISTINCT period FROM frames ORDER BY period")]
        if periods != [1, 2]:
            raise ValueError("both halves required for the declared split")
        for period in periods:
            ball_count = obs.execute("SELECT COUNT(*) FROM observations WHERE period=? AND team='BALL'", (period,)).fetchone()[0]
            if not ball_count:
                raise ValueError("missing ball stream in half")
        # No target attributes or target-derived masks are present in this database.
        obs.executescript(f"""
            CREATE VIEW timeline AS
            SELECT *, CASE WHEN source_frame=LAG(source_frame) OVER w + 1
                AND timestamp_us=LAG(timestamp_us) OVER w + {STEP_US}
                THEN 1 ELSE 0 END AS contiguous_previous,
                CASE period WHEN 1 THEN 'train' WHEN 2 THEN 'validation' END AS split
            FROM frames WINDOW w AS (PARTITION BY match_id, period ORDER BY source_frame);
            CREATE TABLE metadata (json TEXT NOT NULL);
        """)
        metadata = dict(contract_version=CONTRACT_VERSION, match_id=info.match_id,
                        home_id=info.home_id, away_id=info.away_id, length_m=info.length_m,
                        width_m=info.width_m, coordinate_unit="m", origin="pitch_center", fps=FPS)
        obs.execute("INSERT INTO metadata VALUES (?)", (json.dumps(metadata, sort_keys=True),))
        report = dict(stats)
        report["periods"] = []
        for period in periods:
            count, start, end = obs.execute("SELECT COUNT(*), MIN(source_frame), MAX(source_frame) FROM frames WHERE period=?", (period,)).fetchone()
            breaks = obs.execute("SELECT COUNT(*) FROM timeline WHERE period=? AND contiguous_previous=0", (period,)).fetchone()[0]
            report["periods"].append(dict(period=period, split=SPLITS[period], frames=count,
                                           first_frame=start, last_frame=end, missing_frame_numbers=end-start+1-count,
                                           contiguous_runs=breaks))
        report["coordinate_quality"] = [dict(team=r[0], records=r[1], missing_x=r[2], missing_y=r[3], outside=r[4], min_x=r[5], max_x=r[6], min_y=r[7], max_y=r[8]) for r in obs.execute("""SELECT team, COUNT(*), SUM(x_m IS NULL), SUM(y_m IS NULL),
            SUM(COALESCE(ABS(x_m)>?,0) OR COALESCE(ABS(y_m)>?,0)), MIN(x_m), MAX(x_m), MIN(y_m), MAX(y_m)
            FROM observations GROUP BY team""", (info.length_m/2, info.width_m/2))]
        report["coordinate_reasons"] = [list(r) for r in obs.execute("SELECT x_reason,y_reason,COUNT(*) FROM observations GROUP BY x_reason,y_reason")]
        report["entity_missing_frame_numbers"] = obs.execute("""SELECT COALESCE(SUM(source_frame-previous-1),0)
            FROM (SELECT source_frame,LAG(source_frame) OVER
                (PARTITION BY match_id,period,entity_id ORDER BY source_frame) AS previous
                FROM observations) WHERE previous IS NOT NULL""").fetchone()[0]
        report["frames_without_ball"] = obs.execute("SELECT COUNT(*) FROM frames f WHERE NOT EXISTS (SELECT 1 FROM observations o WHERE o.match_id=f.match_id AND o.period=f.period AND o.source_frame=f.source_frame AND o.entity_id='BALL')").fetchone()[0]
        # Unavailable targets are explicit rows, without changing the observation timeline.
        tgt.executemany("INSERT INTO targets VALUES (?,?,?,NULL,NULL,NULL,0,'missing_ball_record')",
                        obs.execute("SELECT match_id,period,source_frame FROM frames f WHERE NOT EXISTS (SELECT 1 FROM observations o WHERE o.match_id=f.match_id AND o.period=f.period AND o.source_frame=f.source_frame AND o.entity_id='BALL')"))
        report["missing_ball_targets"] = report["frames_without_ball"]
        report["target_counts"] = [dict(period=r[0], label=r[1], valid_target=r[2], invalid_reason=r[3], count=r[4]) for r in tgt.execute("SELECT period,label,valid_target,invalid_reason,COUNT(*) FROM targets GROUP BY period,label,valid_target,invalid_reason")]
        obs.commit()
        tgt.commit()
        return report
