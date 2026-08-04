"""Reproducible P0 pilot and benchmark execution."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import resource
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .evaluator import evaluate
from .generator import baseline_candidates


def _revision() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], text=True, check=True,
                          capture_output=True).stdout.strip()


def _percentile(values: list[int], p: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * p
    lower = int(position)
    fraction = position - lower
    return ordered[lower] if fraction == 0 else ordered[lower] + fraction * (ordered[lower + 1] - ordered[lower])


def run_pilot(output_root: Path, *, per_digit: int = 40) -> dict:
    """Run the registered six-stratum P0 experiment and atomically write artifacts."""
    experiment_id = "e000-p0-pilot"
    result_dir, report_dir = output_root / "results" / experiment_id, output_root / "reports" / experiment_id
    raw_dir = result_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    digits = [500, 600, 700, 800, 900, 1000]
    records: list[dict] = []
    start_wall, start_cpu = time.perf_counter_ns(), time.process_time_ns()
    for digit_count in digits:
        for ordinal, candidate in enumerate(baseline_candidates(per_digit, digit_count)):
            wall, cpu = time.perf_counter_ns(), time.process_time_ns()
            result = evaluate(candidate)
            wall, cpu = time.perf_counter_ns() - wall, time.process_time_ns() - cpu
            record = result.to_record(
                experiment_id=experiment_id, record_id=f"d{digit_count}-{ordinal:05d}",
                wall_time_ns=wall, cpu_time_ns=cpu, strategy="S0-hash-counter",
                strategy_version=1, strategy_parameters={"seed": "p0-baseline-v1", "ordinal": ordinal},
                evaluator_version=__version__, software_revision=_revision(), limits={},
            )
            records.append(record)
    elapsed = time.perf_counter_ns() - start_wall
    cpu_elapsed = time.process_time_ns() - start_cpu
    raw_path = raw_dir / "part-00000.jsonl"
    raw_bytes = "".join(json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n" for r in records).encode()
    raw_path.write_bytes(raw_bytes)
    checksum = hashlib.sha256(raw_bytes).hexdigest()
    times = [r["wall_time_ns"] for r in records]
    steps = [r["total_steps_executed"] for r in records]
    by_digits = {}
    for digit_count in digits:
        group = [r for r in records if r["decimal_digits"] == digit_count]
        group_time = sum(r["wall_time_ns"] for r in group)
        by_digits[str(digit_count)] = {
            "trajectories": len(group), "mean_wall_time_ms": statistics.fmean(r["wall_time_ns"] for r in group) / 1e6,
            "trajectories_per_second": len(group) * 1e9 / group_time,
            "mean_steps": statistics.fmean(r["total_steps_executed"] for r in group),
        }
    rate = len(records) * 1e9 / elapsed
    benchmark = {
        "schema_version": 1, "trajectories": len(records), "wall_time_seconds": elapsed / 1e9,
        "cpu_time_seconds": cpu_elapsed / 1e9, "trajectories_per_second": rate,
        "average_evaluation_time_ms": statistics.fmean(times) / 1e6,
        "peak_process_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "throughput_by_decimal_digits": by_digits,
        "estimated_runtime_seconds": {str(n): n / rate for n in (1000, 10000, 100000)},
    }
    summary = {
        "schema_version": 1, "experiment_id": experiment_id, "count": len(records),
        "outcomes": {name: sum(r["outcome"] == name for r in records) for name in ("reached_one", "repeated_state", "interrupted")},
        "steps": {"mean": statistics.fmean(steps), "median": statistics.median(steps),
                  "p90_linear_interpolation": _percentile(steps, .9), "maximum": max(steps)},
        "maximum_excursion_digits": max(len(r["maximum_integer"]) - r["decimal_digits"] for r in records),
        "best_record_id": max(records, key=lambda r: r["total_steps_executed"])["record_id"],
        "raw_sha256": checksum,
    }
    metadata = {
        "schema_version": 1, "experiment_id": experiment_id,
        "generated_utc": datetime.now(timezone.utc).isoformat(), "command": f"python -m bigcollatz pilot --per-digit {per_digit}",
        "seed": "p0-baseline-v1", "digit_strata": digits, "per_digit": per_digit,
        "software_revision": _revision(), "python": sys.version, "implementation": platform.python_implementation(),
        "platform": platform.platform(), "machine": platform.machine(), "logical_cpus": os.cpu_count(),
        "hostname_sha256": hashlib.sha256(platform.node().encode()).hexdigest(),
        "raw_file": str(raw_path.relative_to(output_root)), "raw_sha256": checksum,
    }
    for name, value in (("benchmark.json", benchmark), ("summary.json", summary)):
        (report_dir / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    (result_dir / "metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    return {"benchmark": benchmark, "summary": summary, "metadata": metadata}
