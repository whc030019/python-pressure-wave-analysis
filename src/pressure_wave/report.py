"""Headless plots and a self-contained HTML report."""

import csv
import html
import io
from pathlib import Path

from .analysis import Signal, analyze


def export_report(signals: list[Signal], folder: str | Path, *,
                  baseline_kpa: float = 0.0, threshold_kpa: float = 0.5) -> Path:
    if not signals:
        raise ValueError("At least one signal is required")
    summaries = [analyze(s, baseline_kpa=baseline_kpa, threshold_kpa=threshold_kpa)
                 for s in signals]
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    target = Path(folder)
    target.mkdir(parents=True, exist_ok=True)
    fig, (ax, bar) = plt.subplots(2, 1, figsize=(11, 8), layout="constrained",
                                  gridspec_kw={"height_ratios": [3, 1.5]})
    try:
        for signal in signals:
            ax.plot(signal.time_ms, [p-baseline_kpa for p in signal.pressure_kpa],
                    label=signal.series_id, linewidth=1.8)
        ax.axhline(threshold_kpa, color="#6b7280", linestyle="--", label="Analysis threshold")
        ax.axhline(0, color="#9ca3af", linewidth=0.8)
        ax.set(xlabel="Time (ms)", ylabel="Pressure relative to baseline (kPa)",
               title="Pressure-time signals | educational data analysis")
        ax.grid(alpha=0.2)
        ax.legend()
        bar.bar([str(i + 1) for i in range(len(summaries))],
                [s["peak_pressure_kpa"] for s in summaries], color="#2563eb")
        bar.set(xlabel="Series index (see summary)", ylabel="Peak pressure (kPa)",
                title="Sampled peak pressure")
        bar.grid(axis="y", alpha=0.2)
        fig.savefig(target / "pressure_overview.png", dpi=160)
        fig.savefig(target / "pressure_overview.svg")
        buffer = io.StringIO()
        fig.savefig(buffer, format="svg")
        svg = buffer.getvalue()
        svg = svg[svg.index("<svg"):]
    finally:
        plt.close(fig)
    with (target / "summary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)
    with (target / "processed_signals.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["series_id", "time_ms", "pressure_kpa"])
        for signal in signals:
            writer.writerows((signal.series_id, t, p-baseline_kpa)
                             for t, p in zip(signal.time_ms, signal.pressure_kpa))
    columns = list(summaries[0])
    def cell(value):
        return html.escape(f"{value:.6g}" if isinstance(value, float) else str(value))
    head = "".join(f"<th>{html.escape(c)}</th>" for c in columns)
    body = "".join("<tr>"+"".join(f"<td>{cell(s[c])}</td>" for c in columns)+"</tr>"
                   for s in summaries)
    document = f"""<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>压力波数据分析报告</title><style>
body{{font:16px/1.7 system-ui,sans-serif;color:#172b45;background:#f5f7fb;margin:0}}
main{{max-width:1120px;margin:32px auto;padding:24px;background:white;border-radius:12px}}
svg{{width:100%;height:auto}}.table{{overflow:auto}}table{{border-collapse:collapse;font-size:13px}}
th,td{{border:1px solid #dce3ec;padding:9px;text-align:left}}th{{background:#edf3fb}}
</style><main><h1>压力波数据分析报告</h1>
<p>本报告分析输入的压力—时间数据，不推断信号来源或传播规律。随附样本为教学合成信号。</p>
<p>基线：{baseline_kpa:g} kPa；分析阈值：{threshold_kpa:g} kPa。
阈值用于信号统计，不代表任何安全或损伤标准。</p>
{svg}<h2>统计结果</h2><p>时间单位 ms，压力单位 kPa，面积单位 kPa·ms。
峰值取采样点最大值；持续时间累计所有高于阈值的区间，交点按线性插值计算。</p>
<div class="table"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>
<p>processed_signals.csv 已扣除基线。重新分析此文件时应使用 baseline=0。</p></main></html>"""
    (target / "report.html").write_text(document, encoding="utf-8")
    return target / "report.html"
