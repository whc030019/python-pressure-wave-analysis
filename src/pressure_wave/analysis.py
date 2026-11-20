"""Validated CSV input and piecewise-linear signal statistics in SI-derived units."""

import csv
import math
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Signal:
    series_id: str
    time_ms: tuple[float, ...]
    pressure_kpa: tuple[float, ...]

    def __post_init__(self):
        if not isinstance(self.series_id, str) or not self.series_id.strip():
            raise ValueError("series_id must not be blank")
        if len(self.time_ms) != len(self.pressure_kpa) or len(self.time_ms) < 3:
            raise ValueError("Each series needs at least three paired samples")
        if not all(math.isfinite(v) for v in (*self.time_ms, *self.pressure_kpa)):
            raise ValueError("Time and pressure must be finite")
        if any(b <= a for a, b in zip(self.time_ms, self.time_ms[1:])):
            raise ValueError("Time must strictly increase within each series")


def read_signals(filename: str | Path) -> list[Signal]:
    """Read UTF-8 CSV; retain input order and reject errors instead of sorting."""
    groups: dict[str, tuple[list[float], list[float]]] = {}
    with Path(filename).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"series_id", "time_ms", "pressure_kpa"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError("Required CSV columns: series_id,time_ms,pressure_kpa")
        if len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("Duplicate CSV column names")
        for row in reader:
            if None in row or any(row.get(key) is None for key in required):
                raise ValueError(f"CSV line {reader.line_num}: malformed row")
            name = row["series_id"]
            if not name.strip():
                raise ValueError(f"CSV line {reader.line_num}: blank series_id")
            try:
                t, p = float(row["time_ms"]), float(row["pressure_kpa"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"CSV line {reader.line_num}: invalid numeric value") from exc
            if not (math.isfinite(t) and math.isfinite(p)):
                raise ValueError(f"CSV line {reader.line_num}: nonfinite value")
            times, pressures = groups.setdefault(name, ([], []))
            times.append(t)
            pressures.append(p)
    if not groups:
        raise ValueError("CSV contains no samples")
    return [Signal(name, tuple(t), tuple(p)) for name, (t, p) in groups.items()]


def _positive_segment(a: float, b: float, dt: float) -> tuple[float, float]:
    """Integral and time strictly above zero for a linear segment."""
    if a <= 0 and b <= 0:
        return 0.0, 0.0
    if a >= 0 and b >= 0:
        return (a + b) * dt / 2, dt
    fraction = (a if a > 0 else b) / abs(b - a)
    duration = dt * fraction
    return max(a, b) * duration / 2, duration


def analyze(signal: Signal, *, baseline_kpa: float = 0.0,
            threshold_kpa: float = 0.5) -> dict:
    """Statistics relative to a user-specified constant baseline.

    Threshold duration sums all intervals above threshold; it is not a
    contiguous pulse width. Areas use actual, possibly irregular time steps.
    """
    if not math.isfinite(baseline_kpa):
        raise ValueError("Baseline must be finite")
    if not math.isfinite(threshold_kpa) or threshold_kpa < 0:
        raise ValueError("Threshold must be finite and nonnegative")
    t = signal.time_ms
    p = tuple(v - baseline_kpa for v in signal.pressure_kpa)
    signed_area = positive_area = duration = 0.0
    for i in range(len(t) - 1):
        dt = t[i + 1] - t[i]
        signed_area += (p[i] + p[i + 1]) * dt / 2
        positive_area += _positive_segment(p[i], p[i + 1], dt)[0]
        duration += _positive_segment(p[i] - threshold_kpa, p[i + 1] - threshold_kpa, dt)[1]
    peak = max(p)
    return {
        "series_id": signal.series_id,
        "sample_count": len(t),
        "observation_duration_ms": t[-1] - t[0],
        "peak_pressure_kpa": peak,
        "peak_time_ms": t[p.index(peak)],
        "min_pressure_kpa": min(p),
        "signed_area_kpa_ms": signed_area,
        "positive_area_kpa_ms": positive_area,
        "time_above_threshold_ms": duration,
        "baseline_kpa": baseline_kpa,
        "threshold_kpa": threshold_kpa,
    }
