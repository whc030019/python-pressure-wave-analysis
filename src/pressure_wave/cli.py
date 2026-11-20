"""Command-line entry point."""

import argparse
import csv
import sys
from .analysis import read_signals
from .report import export_report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Analyze teaching pressure-time CSV data")
    parser.add_argument("csv", help="Input CSV file")
    parser.add_argument("--output", default="results", help="Output folder; same-name files are overwritten")
    parser.add_argument("--baseline-kpa", type=float, default=0.0)
    parser.add_argument("--threshold-kpa", type=float, default=0.5)
    args = parser.parse_args(argv)
    try:
        report = export_report(read_signals(args.csv), args.output,
                               baseline_kpa=args.baseline_kpa, threshold_kpa=args.threshold_kpa)
    except (ValueError, OSError, csv.Error) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    print(f"Report: {report.resolve()}")
    return 0
