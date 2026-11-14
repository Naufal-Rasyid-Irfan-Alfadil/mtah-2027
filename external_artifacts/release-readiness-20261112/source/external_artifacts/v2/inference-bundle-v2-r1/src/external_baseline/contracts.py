"""Versioned contracts: planar metres, UTC microseconds, original frame numbers.

None denotes missing, never zero. Continuity always requires the same period,
adjacent source frames and a 40 ms timestamp interval. IDs are join keys, not
model features. Targets and their validity must never be passed to features.
"""

from dataclasses import dataclass
from typing import Optional

CONTRACT_VERSION = 1
PERIODS = {"firstHalf": 1, "secondHalf": 2}
SPLITS = {1: "train", 2: "validation"}
FPS = 25
STEP_US = 40_000


@dataclass(frozen=True)
class FrameKey:
    match_id: str
    period: int
    source_frame: int


@dataclass(frozen=True)
class Observation:
    """One present entity record; missing records have no row.

    x_m/y_m are independent nullable metre coordinates. Reasons distinguish
    absent attributes, malformed text and nonfinite values. Finite outside
    values are retained. Entity identity never implies identity in another feed.
    """

    key: FrameKey
    entity_id: str
    team: str
    timestamp_us: int
    x_m: Optional[float]
    y_m: Optional[float]
    x_reason: Optional[str]
    y_reason: Optional[str]


@dataclass(frozen=True)
class Target:
    label: Optional[str]
    valid_target: bool
    invalid_reason: Optional[str]


def map_target(status: Optional[str], possession: Optional[str]) -> Target:
    """Map external DFL codes, without filling gaps or carrying team forward.

    Inactive is D independently of possession. Active needs an explicit team.
    Unknown/missing status is invalid; invalid labels remain None, not X or D.
    """
    if status == "0":
        return Target("D", True, None)
    if status == "1":
        if possession in ("1", "2"):
            return Target({"1": "H", "2": "A"}[possession], True, None)
        return Target(None, False, "ambiguous_possession")
    return Target(None, False, "missing_status" if status is None else "unknown_status")
