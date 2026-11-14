"""Explicit ATD period sources; no dataset or organizer-code I/O on import."""
import importlib.util
from pathlib import Path

from .prepare import sha256


def validate_periods(periods):
    """Validate two ordered inclusive 1-based ATD intervals, without guessing.

    Input/output: [(period, first_raw_id, last_raw_id)], periods exactly 1/2.
    Missing, bool, fractional, reversed, or overlapping bounds are rejected.
    Gaps remain gaps. No default zero, offset search, sorting, or imputation.
    """
    periods=[tuple(row) for row in periods]
    if len(periods)!=2 or any(len(row)!=3 for row in periods):
        raise ValueError('two explicit half intervals required')
    if any(type(value) is not int for row in periods for value in row):
        raise ValueError('half boundaries must be integer frame IDs')
    if [row[0] for row in periods]!=[1,2]:raise ValueError('ordered half IDs 1 and 2 required')
    if any(start<1 or end<start for _,start,end in periods):raise ValueError('invalid half bounds')
    if periods[0][2]>=periods[1][1]:raise ValueError('overlapping/reversed halves')
    return periods


def provider_periods(parameters):
    """Parse populated provider fields as inclusive raw ATD frame bounds.

    These provider-specific fields are supported by the pinned public Metrica
    example. Their convention is not inferred from arbitrary zero-valued data.
    Empty/noninteger fields raise; no conversion failure becomes a numeric zero.
    """
    periods=[]
    for number,name in ((1,'first_half'),(2,'second_half')):
        try:start,end=int(parameters[name+'_start']),int(parameters[name+'_end'])
        except (KeyError,TypeError,ValueError) as error:
            raise ValueError('provider half bounds missing, empty or noninteger; '
                'use an explicit documented period source, not a recording-wide fallback') from error
        if start<1 or end<start:raise ValueError('invalid half bounds')
        periods.append((number,start,end))
    return validate_periods(periods)


def organizer_period_scope(source_path,game,expected_frames,fps=25):
    """Read documented organizer scope from verified public Python source only.

    Production callers pass a source file covered by the bundle manifest. The
    reviewed games.py imports only os, constructs constants/paths, and defines
    functions; half_video_blocks(game) performs no dataset reads. Never call its
    asset, require, GT, or video functions. No tuning/adjust offset is accepted.

    Public scope is video 0-based, both endpoints inclusive. Raw ATD IDs are
    video+1, also inclusive. Return both conventions and provenance explicitly.
    Published scope means evaluation blocks per half, not inferred kickoffs.
    """
    if not game:raise ValueError('--game is required for organizer-public periods')
    path=Path(source_path).resolve(strict=True)
    spec=importlib.util.spec_from_file_location('_mtah_public_period_metadata',path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if game not in module.GAMES:raise ValueError('game absent from public organizer metadata')
    if module.GAMES[game]['fps']!=fps:raise ValueError('public scope FPS differs from adapter')
    if module.GAMES[game]['n_video_frames']!=expected_frames:
        raise ValueError('public scope recording length differs from expected tracking length')
    video=[tuple(row) for row in module.half_video_blocks(game)]
    if any(len(row)!=3 or any(type(v) is not int for v in row) for row in video):
        raise ValueError('invalid public video scope contract')
    if any(first<0 or last>=expected_frames for _,first,last in video):
        raise ValueError('public video scope outside recording')
    periods=validate_periods([(period,first+1,last+1) for period,first,last in video])
    return dict(source='organizer-public',game=game,recording='tactical',fps=fps,
        expected_frames=expected_frames,periods=periods,video_blocks=video,
        input_convention='video_0_based_inclusive',output_convention='atd_1_based_inclusive',
        transform='raw_id = video_frame + 1; no IdFrame offset applied to raw IDs',
        public_source_sha256=sha256(path),public_function='half_video_blocks(game)',
        scope_meaning='published per-half evaluation blocks; not inferred kickoffs')
