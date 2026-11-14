"""Small manual counterexamples; never discover/read real datasets or official GT."""

from dataclasses import fields
from contextlib import closing
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import tracemalloc
import unittest
from unittest.mock import patch

from external_baseline.contracts import Observation, map_target
from external_baseline.dfl import coordinate, parse_positions, read_match_info, timestamp_us
from external_baseline.prepare import prepare

META = '''<PutDataRequest><MatchInformation>
<General MatchId="test" HomeTeamId="home" GuestTeamId="away"/>
<Environment PitchX="105" PitchY="68"/><Teams>
<Team TeamId="away" Role="guest"><Players><Player PersonId="a"/></Players></Team>
<Team TeamId="home" Role="home"><Players><Player PersonId="h"/></Players></Team>
</Teams></MatchInformation></PutDataRequest>'''


def frame(n, x="1", y="2", extra="", time=None):
    # Fixed, hand-sized fixtures at frame numbers 10..13.
    stamp = time or f"2022-01-01T00:00:00.{(n-10)*40:03d}+00:00"
    return f'<Frame N="{n}" T="{stamp}" X="{x}" Y="{y}" {extra}/>'


def stream(period, team, person, frames):
    return f'<FrameSet GameSection="{period}" MatchId="test" TeamId="{team}" PersonId="{person}">{frames}</FrameSet>'


def xml(first=None, status="1", possession="1"):
    if first is None:
        first = stream("firstHalf", "BALL", "ball", frame(10, extra=f'BallStatus="{status}" BallPossession="{possession}"'))
    return ('<PutDataRequest><Positions><MetaData MatchId="test"><PitchSize X="105" Y="68"/></MetaData>' + first +
            stream("secondHalf", "BALL", "ball", frame(10, extra='BallStatus="0"')) + '</Positions></PutDataRequest>')


class ExternalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.meta = self.root / "meta.xml"
        self.pos = self.root / "pos.xml"
        self.meta.write_text(META, encoding="utf-8")

    def build(self, content):
        self.pos.write_text(content, encoding="utf-8")
        report = parse_positions(self.pos, read_match_info(self.meta), self.root / "o.sqlite", self.root / "t.sqlite", batch_size=2)
        return report

    def rows(self, database, query):
        with closing(sqlite3.connect(self.root / database)) as db:
            return db.execute(query).fetchall()

    def test_target_policy(self):
        for status, possession, expected in [("0", None, "D"), ("0", "unknown", "D"), ("1", "1", "H"), ("1", "2", "A"), ("1", None, None), (None, "1", None), ("2", "1", None), ("1", "0", None)]:
            with self.subTest(status=status, possession=possession):
                target = map_target(status, possession)
                self.assertEqual(target.label, expected)
                self.assertEqual(target.valid_target, expected is not None)

    def test_team_order_and_units(self):
        info = read_match_info(self.meta)
        self.assertEqual((info.home_id, info.away_id, info.length_m, info.width_m), ("home", "away", 105, 68))
        self.assertEqual(coordinate("52.5"), (52.5, None))
        self.assertEqual(timestamp_us("2022-01-01T01:00:00.040+01:00") - timestamp_us("2022-01-01T00:00:00Z"), 40000)
        with self.assertRaises(ValueError):
            timestamp_us("2022-01-01T00:00:00")

    def test_frame_join_out_of_order_gap_partial_and_missing_record(self):
        first = stream("firstHalf", "home", "h", frame(13, x="nan", y="inf") + frame(10, x="60", y="") + frame(12, x="bad"))
        first += stream("firstHalf", "BALL", "ball", frame(10, extra='BallStatus="1" BallPossession="2"') + frame(13))
        report = self.build(xml(first))
        self.assertEqual(self.rows("o.sqlite", "SELECT source_frame,contiguous_previous FROM timeline WHERE period=1 ORDER BY source_frame"), [(10, 0), (12, 0), (13, 1)])
        self.assertEqual(self.rows("o.sqlite", "SELECT x_m,y_m,x_reason,y_reason FROM observations WHERE entity_id='h' AND source_frame=10"), [(60.0, None, None, "missing")])
        self.assertEqual(self.rows("o.sqlite", "SELECT x_m,y_m,x_reason,y_reason FROM observations WHERE entity_id='h' AND source_frame=13"), [(None, None, "nonfinite", "nonfinite")])
        self.assertEqual(self.rows("t.sqlite", "SELECT source_frame,label,valid_target,invalid_reason FROM targets WHERE period=1 ORDER BY source_frame"), [(10, "A", 1, None), (12, None, 0, "missing_ball_record"), (13, None, 0, "missing_status")])
        self.assertEqual(report["frames_without_ball"], 1)
        self.assertEqual(report["periods"][0]["missing_frame_numbers"], 1)
        self.assertEqual(self.rows("o.sqlite", "SELECT contiguous_previous,split FROM timeline WHERE period=2"), [(0, "validation")])

    def test_identical_duplicate_deduplicates(self):
        f = frame(10, extra='BallStatus="1" BallPossession="1"')
        report = self.build(xml(stream("firstHalf", "BALL", "b", f + f)))
        self.assertEqual(report["identical_observation_duplicates"], 1)
        self.assertEqual(report["identical_target_duplicates"], 1)

    def test_conflicts_fail(self):
        variants = [
            stream("firstHalf", "BALL", "b", frame(10) + frame(10, x="9")),
            stream("firstHalf", "BALL", "b", frame(10, extra='BallStatus="1" BallPossession="1"') + frame(10, extra='BallStatus="1" BallPossession="2"')),
            stream("firstHalf", "home", "a", frame(10)),
            stream("extraTime", "BALL", "b", frame(10)),
            stream("firstHalf", "BALL", "b", frame(10) + frame(11, time="2022-01-01T00:00:00.080Z")),
            stream("firstHalf", "home", "h", frame(10)) + stream("firstHalf", "BALL", "b", frame(10, time="2022-01-01T00:00:01Z")),
        ]
        for i, first in enumerate(variants):
            with self.subTest(case=i), tempfile.TemporaryDirectory(dir=self.root) as folder:
                self.pos.write_text(xml(first), encoding="utf-8")
                with self.assertRaises((ValueError, sqlite3.IntegrityError)):
                    parse_positions(self.pos, read_match_info(self.meta), Path(folder)/"o", Path(folder)/"t")

    def test_no_target_leakage(self):
        self.assertFalse({"label", "ball_status", "ball_possession", "valid_target", "invalid_reason"} & {f.name for f in fields(Observation)})
        outputs = []
        for possession in ("1", "2"):
            folder = self.root / possession
            folder.mkdir()
            self.pos.write_text(xml(possession=possession), encoding="utf-8")
            parse_positions(self.pos, read_match_info(self.meta), folder/"o", folder/"t")
            with closing(sqlite3.connect(folder/"o")) as db:
                outputs.append((db.execute("SELECT * FROM observations ORDER BY period,source_frame,entity_id").fetchall(), db.execute("SELECT * FROM timeline ORDER BY period,source_frame").fetchall(), db.execute("SELECT sql FROM sqlite_master ORDER BY name").fetchall()))
        self.assertEqual(outputs[0], outputs[1])

    def test_manifest_reproducibility_and_no_overwrite(self):
        self.pos.write_text(xml(), encoding="utf-8")
        with patch("external_baseline.prepare.git_metadata", return_value={"commit": "synthetic"}):
            prepare(self.meta, self.pos, self.root/"one")
            prepare(self.meta, self.pos, self.root/"two")
        for name in ("observations.sqlite", "targets.sqlite", "manifest.json"):
            self.assertEqual((self.root/"one"/name).read_bytes(), (self.root/"two"/name).read_bytes())
        with self.assertRaises(FileExistsError):
            prepare(self.meta, self.pos, self.root/"one")

    def test_failure_is_not_ready(self):
        self.pos.write_text(xml().replace('X="105"', 'X="106"'), encoding="utf-8")
        with self.assertRaises(ValueError):
            prepare(self.meta, self.pos, self.root/"failed")
        self.assertFalse((self.root/"failed"/"manifest.json").exists())
        self.assertTrue((self.root/"failed"/"FAILED.json").exists())

    def test_import_and_help_without_dataset_access(self):
        script = '''import sys, runpy
def audit(event, args):
    if event == 'open':
        p = str(args[0]).replace(chr(92), '/').lower()
        if p.endswith(('.xml','.sqlite','.csv','.mp4')) or '/data/' in p or '/evaluation/gt/' in p:
            raise RuntimeError('dataset access forbidden: ' + p)
sys.addaudithook(audit)
import external_baseline.contracts, external_baseline.dfl, external_baseline.prepare
sys.argv = ['prepare', '--help']
runpy.run_module('external_baseline.prepare', run_name='__main__')
'''
        result = subprocess.run([sys.executable, "-B", "-c", script], capture_output=True, text=True, cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--match-info", result.stdout)

    def test_xml_memory_does_not_grow_with_frame_count(self):
        # 10x frames would expose retained XML nodes; SQLite memory is bounded
        # separately by its configured cache and measured via OS RSS on the match.
        peaks = []
        for count in (2000, 20000):
            folder = self.root / str(count)
            folder.mkdir()
            with self.pos.open("w", encoding="utf-8") as handle:
                handle.write('<PutDataRequest><Positions><MetaData MatchId="test"><PitchSize X="105" Y="68"/></MetaData>')
                for period in ("firstHalf", "secondHalf"):
                    handle.write(f'<FrameSet GameSection="{period}" MatchId="test" TeamId="BALL" PersonId="ball">')
                    for n in range(count):
                        seconds, ms = divmod(n * 40, 1000)
                        minutes, sec = divmod(seconds, 60)
                        handle.write(f'<Frame N="{n}" T="2022-01-01T00:{minutes:02d}:{sec:02d}.{ms:03d}Z" X="1" Y="2" BallStatus="0"/>')
                    handle.write('</FrameSet>')
                handle.write('</Positions></PutDataRequest>')
            tracemalloc.start()
            try:
                parse_positions(self.pos, read_match_info(self.meta), folder/"o", folder/"t", batch_size=128)
                peaks.append(tracemalloc.get_traced_memory()[1])
            finally:
                tracemalloc.stop()
        self.assertLess(peaks[1], peaks[0] + 1_000_000, peaks)


if __name__ == "__main__":
    unittest.main()
