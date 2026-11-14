"""Manual geometry/temporal counterexamples; no external or official match reads."""

from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from external_baseline.contracts import FrameKey
from external_baseline.features import (EntityPosition as E, FEATURE_NAMES,
                                        FrameFeatureExtractor, extract_features,
                                        iter_feature_frames)
from external_baseline.prepare import sha256


def key(n, period=1, match="synthetic"):
    return FrameKey(match, period, n)


def fixture(folder):
    """Hand-built observation-only DB, including empty and partial frames."""
    path = folder/"observations.sqlite"
    with closing(sqlite3.connect(path)) as db:
        db.executescript('''
            CREATE TABLE frames(match_id TEXT,period INTEGER,source_frame INTEGER,timestamp_us INTEGER,
                PRIMARY KEY(match_id,period,source_frame));
            CREATE TABLE observations(match_id TEXT,period INTEGER,source_frame INTEGER,entity_id TEXT,
                team TEXT,x_m REAL,y_m REAL,x_reason TEXT,y_reason TEXT,
                PRIMARY KEY(match_id,period,source_frame,entity_id));
            CREATE TABLE metadata(json TEXT);
        ''')
        # Insert in reverse order: source frame/time are authoritative.
        db.executemany("INSERT INTO frames VALUES ('synthetic',?,?,?)", [(2, 10, 900000), (1, 14, 160000), (1, 12, 80000), (1, 11, 40000), (1, 10, 0)])
        db.executemany("INSERT INTO observations VALUES ('synthetic',?,?,?,?,?,?,?,?)", [
            (1, 10, "BALL", "BALL", 0, 0, None, None),
            (1, 10, "h", "H", 3, 4, None, None),
            (1, 10, "partial", "H", None, 0, "missing", None),
            (1, 11, "BALL", "BALL", 0.12, 0.16, None, None),
            (1, 14, "BALL", "BALL", 5, 5, None, None),
            (2, 10, "BALL", "BALL", 0, 0, None, None)])
        db.execute("INSERT INTO metadata VALUES (?)", (json.dumps({"contract_version": 1, "coordinate_unit": "m", "origin": "pitch_center", "fps": 25, "match_id": "synthetic", "length_m": 105, "width_m": 68}),))
        db.commit()
    (folder/"manifest.json").write_text(json.dumps({"status": "ready", "contract_version": 1, "provenance": {"source": "synthetic"}}), encoding="utf-8")
    return path


class FeatureTests(unittest.TestCase):
    def test_manual_geometry_and_counts(self):
        result = FrameFeatureExtractor(105, 68).extract(key(10), 0, [
            E("BALL", "BALL", 0, 0), E("h1", "H", 3, 4),
            E("h2", "H", -6, -8), E("partial", "H", 0, None), E("a", "A", 0, -12)])
        self.assertEqual(tuple(result), FEATURE_NAMES)
        self.assertEqual(len(result), 16)
        self.assertEqual((result["nearest_home_m"], result["nearest_away_m"]), (5, 12))
        self.assertEqual((result["home_records"], result["home_xy_observed"], result["away_records"]), (3, 2, 1))
        self.assertEqual((result["ball_longitudinal_margin_m"], result["ball_lateral_margin_m"], result["ball_inside_pitch"]), (52.5, 34, 1))
        self.assertIsNone(result["ball_speed_mps"])

    def test_backward_speed_metres_per_second(self):
        extractor = FrameFeatureExtractor(105, 68)
        extractor.extract(key(10), 0, [E("BALL", "BALL", 0, 0)])
        result = extractor.extract(key(11), 40000, [E("BALL", "BALL", 0.12, 0.16)])
        self.assertAlmostEqual(result["ball_speed_mps"], 5.0)

    def test_continuity_guards(self):
        for new_key, stamp in ((key(12), 80000), (key(11), 80000), (key(11, 2), 40000), (key(11, match="another"), 40000)):
            with self.subTest(key=new_key, stamp=stamp):
                extractor = FrameFeatureExtractor(105, 68)
                extractor.extract(key(10), 0, [E("BALL", "BALL", 0, 0)])
                result = extractor.extract(new_key, stamp, [E("BALL", "BALL", 1, 1)])
                self.assertIsNone(result["ball_speed_mps"])

    def test_absent_partial_nonfinite_reset_speed_and_nearest(self):
        for middle in ([], [E("BALL", "BALL", 1, None)], [E("BALL", "BALL", float("nan"), float("inf"))]):
            with self.subTest(middle=middle):
                extractor = FrameFeatureExtractor(105, 68)
                extractor.extract(key(10), 0, [E("BALL", "BALL", 0, 0)])
                result = extractor.extract(key(11), 40000, middle + [E("h", "H", 0, 0)])
                self.assertEqual(result["ball_record_present"], int(bool(middle)))
                self.assertEqual(result["ball_xy_observed"], 0)
                self.assertIsNone(result["nearest_home_m"])
                self.assertIsNone(result["ball_speed_mps"])
                self.assertIsNone(result["ball_inside_pitch"])
                after = extractor.extract(key(12), 80000, [E("BALL", "BALL", 1, 1)])
                self.assertIsNone(after["ball_speed_mps"])

    def test_outside_is_not_clipped_and_partial_axes_survive(self):
        extractor = FrameFeatureExtractor(105, 68)
        result = extractor.extract(key(10), 0, [E("BALL", "BALL", 55.5, 38), E("h", "H", 52.5, 34)])
        self.assertEqual((result["ball_x_m"], result["ball_y_m"], result["nearest_home_m"]), (55.5, 38, 5))
        self.assertEqual((result["ball_longitudinal_margin_m"], result["ball_lateral_margin_m"], result["ball_inside_pitch"]), (-3, -4, 0))
        partial = extractor.extract(key(11), 40000, [E("BALL", "BALL", 52.5, None)])
        self.assertEqual((partial["ball_x_observed"], partial["ball_y_observed"], partial["ball_longitudinal_margin_m"]), (1, 0, 0))
        self.assertIsNone(partial["ball_lateral_margin_m"])

    def test_no_complete_players_means_missing_distance_not_zero(self):
        result = FrameFeatureExtractor(105, 68).extract(key(10), 0, [E("BALL", "BALL", 0, 0), E("h", "H", None, 0)])
        self.assertEqual(result["home_records"], 1)
        self.assertEqual(result["home_xy_observed"], 0)
        self.assertEqual(result["away_records"], 0)
        self.assertIsNone(result["nearest_home_m"])
        self.assertIsNone(result["nearest_away_m"])

    def test_player_id_and_order_cannot_create_ball_speed(self):
        a, b = FrameFeatureExtractor(105, 68), FrameFeatureExtractor(105, 68)
        for n in (10, 11):
            ball = E("BALL", "BALL", (n-10)*0.04, 0)
            self.assertEqual(a.extract(key(n), (n-10)*40000, [ball, E("stable", "H", 3, 4)]),
                             b.extract(key(n), (n-10)*40000, [E(f"anonymous-{n}", "H", 3, 4), ball]))

    def test_duplicate_entities_and_multiple_balls_fail(self):
        for entities in ([E("h", "H", 0, 0)]*2, [E("b1", "BALL", 0, 0), E("b2", "BALL", 0, 0)]):
            with self.assertRaises(ValueError):
                FrameFeatureExtractor(105, 68).extract(key(10), 0, entities)

    def test_streaming_join_preserves_empty_frames_gaps_and_halves(self):
        with tempfile.TemporaryDirectory() as folder:
            path = fixture(Path(folder))
            with closing(sqlite3.connect(path)) as db:
                rows = list(iter_feature_frames(db))
            self.assertEqual([(k.period, k.source_frame) for k, _, _ in rows], [(1,10), (1,11), (1,12), (1,14), (2,10)])
            self.assertAlmostEqual(rows[1][2]["ball_speed_mps"], 5)
            self.assertEqual(rows[2][2]["ball_record_present"], 0)
            self.assertIsNone(rows[3][2]["ball_speed_mps"])
            self.assertIsNone(rows[4][2]["ball_speed_mps"])

    def test_output_report_reproducibility_and_no_target_access(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = fixture(root)
            # Not a valid target DB: any attempt to attach it would fail.
            (root/"targets.sqlite").write_text("DO NOT OPEN", encoding="utf-8")
            before = sha256(source)
            with patch("external_baseline.features.git_metadata", return_value={"commit": "synthetic"}):
                report = extract_features(source, root/"one")
                (root/"targets.sqlite").write_text("different labels must have no influence", encoding="utf-8")
                extract_features(source, root/"two")
            for file in ("features.sqlite", "manifest.json"):
                self.assertEqual((root/"one"/file).read_bytes(), (root/"two"/file).read_bytes())
            self.assertEqual(sha256(source), before)
            self.assertEqual(report["periods"][0]["frames"], 4)
            self.assertEqual(report["periods"][0]["features"]["ball_speed_mps"]["defined"], 1)
            self.assertEqual(report["periods"][0]["features"]["ball_speed_mps"]["coverage"], 0.25)
            with closing(sqlite3.connect(root/"one"/"features.sqlite")) as db:
                columns = [r[1] for r in db.execute("PRAGMA table_info(features)")]
                self.assertEqual(columns[5:], list(FEATURE_NAMES))
                self.assertFalse({"label", "ball_status", "ball_possession", "valid_target", "invalid_reason"} & set(columns))
            with self.assertRaises(FileExistsError):
                extract_features(source, root/"one")

    def test_unit_and_schema_mismatch_fail_without_ready_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = fixture(root)
            with closing(sqlite3.connect(source)) as db:
                db.execute("CREATE TABLE targets(label TEXT)")
                db.commit()
            with self.assertRaises(ValueError):
                extract_features(source, root/"failed")
            self.assertTrue((root/"failed"/"FAILED.json").exists())
            self.assertFalse((root/"failed"/"manifest.json").exists())
            with closing(sqlite3.connect(source)) as db:
                db.execute("DROP TABLE targets")
                meta = json.loads(db.execute("SELECT json FROM metadata").fetchone()[0])
                meta["coordinate_unit"] = "cm"
                db.execute("UPDATE metadata SET json=?", (json.dumps(meta),))
                db.commit()
                with self.assertRaises(ValueError):
                    list(iter_feature_frames(db))

    def test_import_help_and_run_guarded_against_target_or_official_access(self):
        with tempfile.TemporaryDirectory() as folder:
            source = fixture(Path(folder))
            script = '''import sys,runpy
def audit(event,args):
    if event in ('open','sqlite3.connect'):
        p=str(args[0]).replace(chr(92),'/').lower()
        if any(s in p for s in ('targets.sqlite','/evaluation/gt/','/evaluation/results/')) or p.endswith(('.xml','.csv','.mp4','.txt')):
            raise RuntimeError('forbidden data access: '+p)
sys.addaudithook(audit)
from external_baseline.features import extract_features
assert not any(m in sys.modules for m in ('sklearn','torch','numpy','pandas'))
if sys.argv[1]=='help':
    sys.argv=['features','--help']
    runpy.run_module('external_baseline.features',run_name='__main__')
else:
    extract_features(sys.argv[1],sys.argv[2])
'''
            for arguments in (("help",), (str(source), str(Path(folder)/"guarded"))):
                result = subprocess.run([sys.executable,"-B","-c",script,*arguments], capture_output=True,text=True,cwd=Path(__file__).resolve().parents[1])
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
