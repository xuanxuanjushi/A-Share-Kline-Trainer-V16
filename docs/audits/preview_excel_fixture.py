"""Exercise the real application exporter using clearly marked synthetic observations."""
import math
from datetime import date, timedelta
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
from test_excel_entrypoint import report_window, MainWindow, EquityPoint, TradeNode

points = []
day = date(2018, 6, 6)
for i in range(2000):
    while day.weekday() >= 5:
        day += timedelta(days=1)
    points.append(EquityPoint(day.isoformat(), TradeNode.CLOSE, round(100000 + i * 40 + 18000 * math.sin(i / 110), 2)))
    day += timedelta(days=1)
directory = ROOT / 'docs/audits/excel-preview'
window = report_window(directory, points)
result = MainWindow._export_performance_report(window, 'Excel')
assert result, window._update_status.call_args
target = directory / '交易统计-验证.xlsx'
result.replace(target)
print('Synthetic 2000-day report generated via the real application export entrypoint.')
