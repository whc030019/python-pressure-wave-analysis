"""Generate generic smooth sensor-like pulses; not an explosion model."""

import csv
import math
from pathlib import Path


def generate(filename: Path) -> None:
    filename.parent.mkdir(parents=True, exist_ok=True)
    with filename.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["series_id", "time_ms", "pressure_kpa"])
        for name, amplitude, center, width in [
            ("smooth_A", 2.0, 35.0, 9.0),
            ("smooth_B", 2.8, 48.0, 13.0),
            ("smooth_C", 1.6, 60.0, 7.0),
        ]:
            for i in range(241):
                t = i * 0.5
                p = amplitude * math.exp(-0.5*((t-center)/width)**2)
                p += 0.035 * math.sin(2*math.pi*t/15)
                writer.writerow([name, f"{t:.6f}", f"{p:.9f}"])


if __name__ == "__main__":
    generate(Path(__file__).resolve().parents[1] / "data" / "sample_signals.csv")
