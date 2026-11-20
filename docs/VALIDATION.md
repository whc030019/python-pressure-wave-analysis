# 验证记录

本项目在 Windows、CPython 3.14.6、Matplotlib 3.11.2 环境中实际运行。

执行 `python -m unittest discover -s tests -v`，14 项测试全部通过。测试检查已知解析结果、非均匀采样、跨零区间、阈值交点、异常数据、HTML 转义和导出文件往返读取。

执行 `python -m pressure_wave data/sample_signals.csv --output results`，成功处理三组教学数据，共 723 个采样点，生成 PNG、SVG、统计 CSV、处理后 CSV 与 HTML 报告。

README 中的预览图和本目录的 `sample_report.html` 来自此次实际运行，不是界面设计稿。Python 3.10 是代码的最低目标版本；本次没有进行多版本兼容性测试。

教学数据不用于验证任何实际压力波源模型。自动化测试验证数据处理算法及文件流程，不代表实际测量系统的精度认证。
