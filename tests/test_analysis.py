import tempfile
import unittest
from pathlib import Path

from pressure_wave.analysis import Signal, analyze, read_signals
from pressure_wave.cli import main
from pressure_wave.report import export_report


class AnalysisTests(unittest.TestCase):
    def test_triangle_and_interpolated_duration(self):
        s = Signal("triangle", (0, 1, 2), (0, 2, 0))
        result = analyze(s, threshold_kpa=1)
        self.assertEqual(result["signed_area_kpa_ms"], 2)
        self.assertEqual(result["positive_area_kpa_ms"], 2)
        self.assertEqual(result["time_above_threshold_ms"], 1)
        self.assertEqual(result["peak_time_ms"], 1)

    def test_zero_crossing_positive_area(self):
        result = analyze(Signal("cross", (0, 2, 4), (-2, 2, -2)), threshold_kpa=0)
        self.assertEqual(result["signed_area_kpa_ms"], 0)
        self.assertEqual(result["positive_area_kpa_ms"], 2)
        self.assertEqual(result["time_above_threshold_ms"], 2)

    def test_nonuniform_time(self):
        result = analyze(Signal("uneven", (0, 1, 4), (0, 2, 0)), threshold_kpa=1)
        self.assertEqual(result["signed_area_kpa_ms"], 4)
        self.assertEqual(result["time_above_threshold_ms"], 2)

    def test_baseline_correction(self):
        result = analyze(Signal("offset", (10, 11, 12), (5, 7, 5)),
                         baseline_kpa=5, threshold_kpa=1)
        self.assertEqual(result["peak_pressure_kpa"], 2)
        self.assertEqual(result["peak_time_ms"], 11)
        self.assertEqual(result["observation_duration_ms"], 2)
        self.assertEqual(result["positive_area_kpa_ms"], 2)

    def test_threshold_plateau_is_not_above(self):
        result = analyze(Signal("flat", (0, 1, 2), (1, 1, 1)), threshold_kpa=1)
        self.assertEqual(result["time_above_threshold_ms"], 0)

    def test_negative_signal(self):
        result = analyze(Signal("negative", (0, 1, 2), (-1, -2, -1)))
        self.assertEqual(result["positive_area_kpa_ms"], 0)
        self.assertEqual(result["time_above_threshold_ms"], 0)
        self.assertEqual(result["peak_pressure_kpa"], -1)

    def test_separated_intervals(self):
        result = analyze(Signal("two", (0, 1, 2, 3, 4), (0, 2, 0, 2, 0)), threshold_kpa=1)
        self.assertEqual(result["time_above_threshold_ms"], 2)

    def test_invalid_signal(self):
        for times, pressures in [((0, 1), (0, 1)), ((0, 0, 1), (0, 1, 0)),
                                 ((0, 2, 1), (0, 1, 0)), ((0, 1, 2), (0, float("nan"), 0)),
                                 ((0, 1, 2), (1, 2))]:
            with self.subTest(times=times, pressures=pressures), self.assertRaises(ValueError):
                Signal("bad", times, pressures)
        with self.assertRaises(ValueError):
            Signal(" ", (0, 1, 2), (0, 1, 0))

    def test_invalid_parameters(self):
        s = Signal("ok", (0, 1, 2), (0, 1, 0))
        for threshold in (-1, float("nan"), float("inf")):
            with self.subTest(threshold=threshold), self.assertRaises(ValueError):
                analyze(s, threshold_kpa=threshold)
        with self.assertRaises(ValueError):
            analyze(s, baseline_kpa=float("nan"))


class FileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, content):
        p = self.root / "input.csv"
        p.write_text(content, encoding="utf-8")
        return p

    def test_interleaved_series_and_bom(self):
        p = self.write("\ufeffseries_id,time_ms,pressure_kpa\na,0,0\nb,0,0\na,1,2\nb,1,1\na,2,0\nb,2,0\n")
        signals = read_signals(p)
        self.assertEqual([s.series_id for s in signals], ["a", "b"])
        self.assertEqual(signals[0].pressure_kpa, (0, 2, 0))

    def test_reject_bad_csv(self):
        header = "series_id,time_ms,pressure_kpa\n"
        examples = ["bad,columns\n", header, header+"a,0,nan\n",
                    header+"a,0,foo\n", header+",0,1\n", header+"a,0\n",
                    header+"a,0,1,extra\n", "series_id,time_ms,pressure_kpa,time_ms\n",
                    header+"a,0,0\na,0,2\na,2,0\n"]
        for content in examples:
            with self.subTest(content=content), self.assertRaises(ValueError):
                read_signals(self.write(content))

    def test_report_and_processed_roundtrip(self):
        signal = Signal("<sensor&test>", (0, 1, 2), (5, 7, 5))
        output = self.root / "report"
        report = export_report([signal], output, baseline_kpa=5, threshold_kpa=1)
        for name in ["report.html", "summary.csv", "processed_signals.csv",
                     "pressure_overview.png", "pressure_overview.svg"]:
            self.assertGreater((output / name).stat().st_size, 50)
        self.assertIn("&lt;sensor&amp;test&gt;", report.read_text(encoding="utf-8"))
        processed = read_signals(output / "processed_signals.csv")
        self.assertEqual(processed[0].pressure_kpa, (0, 2, 0))
        self.assertEqual(analyze(processed[0])["positive_area_kpa_ms"], 2)
        self.assertEqual((output / "pressure_overview.png").read_bytes()[:8], b"\x89PNG\r\n\x1a\n")

    def test_cli_invalid_file(self):
        self.assertEqual(main([str(self.root / "missing.csv")]), 2)

    def test_empty_report(self):
        with self.assertRaises(ValueError):
            export_report([], self.root / "out")


if __name__ == "__main__":
    unittest.main()
