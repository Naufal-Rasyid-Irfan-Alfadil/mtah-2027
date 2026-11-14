"""Explicit external-only CLI. Import and --help never open datasets."""

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import platform
import sqlite3
import subprocess
import time

from .contracts import CONTRACT_VERSION
from .dfl import parse_positions, read_match_info

REPO = Path(__file__).resolve().parents[1]


def peak_memory_bytes():
    """Return OS process peak resident memory bytes, or None if unavailable.

    Includes interpreter/SQLite, not just Python allocations. It is a process
    lifetime peak, so use a fresh CLI process when comparing input sizes.
    """
    if platform.system() == "Windows":
        import ctypes
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        if psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            return counters.PeakWorkingSetSize
        return None
    try:
        import resource
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return peak if platform.system() == "Darwin" else peak * 1024
    except ImportError:
        return None


def sha256(path):
    """Hash one explicit file using bounded 1 MiB reads; returns hexadecimal SHA-256."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_metadata():
    """Read Git metadata only; unavailable Git is recorded, never guessed."""
    try:
        def run(*args):
            return subprocess.check_output(["git", *args], cwd=REPO, text=True).strip()
        return {"commit": run("rev-parse", "HEAD"), "status": run("status", "--porcelain=v1")}
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "status": "unavailable"}


def prepare(match_info, positions, output):
    """Build external artifacts in a new directory; never overwrite existing output.

    Requires explicit, distinct XML files. Only manifest.status=ready marks
    completion. Failures retain FAILED.json and partial databases for diagnosis;
    consumers must reject directories without a ready manifest. No fitting or
    inference is performed. Logical rows are reproducible; timings may differ.
    """
    paths = [Path(p).resolve(strict=True) for p in (match_info, positions)]
    if paths[0] == paths[1] or any(not p.is_file() or p.suffix.lower() != ".xml" for p in paths):
        raise ValueError("two distinct external XML files required")
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    try:
        source_hashes = {str(p.relative_to(REPO)): sha256(p) for p in sorted((REPO / "external_baseline").glob("*.py"))}
        inputs = [{"path": str(p), "bytes": p.stat().st_size, "sha256": sha256(p)} for p in paths]
        info = read_match_info(paths[0])
        report = parse_positions(paths[1], info, output / "observations.sqlite", output / "targets.sqlite")
        # Detect input edits during preparation rather than attesting a stale hash.
        if any(sha256(p) != item["sha256"] for p, item in zip(paths, inputs)):
            raise ValueError("input changed during preparation")
        report["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        report["process_peak_resident_bytes"] = peak_memory_bytes()
        if any(sha256(REPO / name) != digest for name, digest in source_hashes.items()):
            raise ValueError("source changed during preparation")
        manifest = {
            "status": "ready", "contract_version": CONTRACT_VERSION,
            "inputs": inputs, "git": git_metadata(), "source_sha256": source_hashes,
            "python": platform.python_version(), "sqlite": sqlite3.sqlite_version,
            "config": {"fps": 25, "coordinate_unit": "m", "origin": "pitch_center", "batch_size": 4096,
                       "split": {"1": "train", "2": "validation"}, "target_policy": "inactive_D_active_explicit_team_else_invalid"},
            "match": {k: v for k, v in asdict(info).items() if k != "players"},
            "provenance": {
                "authorization": "User confirmed data directory contains external DFL only.",
                "source": "https://doi.org/10.6084/m9.figshare.28196177",
                "license": "https://creativecommons.org/licenses/by/4.0/",
                "attribution": "Deutsche Fussball Liga (DFL); Bassek, Rein, Weber and Memmert (2025), Scientific Data 12:195, doi:10.1038/s41597-025-04505-y",
                "changes": "Streaming parse, planar observation extraction, missing normalization, frame-key joins, target mapping and half split.",
                "decisions": "User-approved plan; no old project code/parameters copied. Fresh clone alone does not establish independence from earlier experiments.",
                "model": "HGB proposed by user; not implemented or selected experimentally.",
                "official_data": "No official data, GT or prediction files used. Organizer clarification supplied by user takes precedence over repository docs.",
            },
        }
        for name, value in (("validation_report.json", report), ("manifest.json", manifest)):
            (output / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return report
    except Exception as error:
        (output / "FAILED.json").write_text(json.dumps({"status": "failed", "error": str(error)}, indent=2) + "\n", encoding="utf-8")
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--match-info", required=True, type=Path)
    parser.add_argument("--positions", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = prepare(args.match_info, args.positions, args.output)
    print(json.dumps({"output": str(args.output), "periods": report["periods"]}, indent=2))


if __name__ == "__main__":
    main()
