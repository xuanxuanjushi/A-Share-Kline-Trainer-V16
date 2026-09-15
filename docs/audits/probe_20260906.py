"""Read-only source audit: all data writes use temporary directories.

Run from the project root: python docs/audits/probe_20260906.py
These probes print behavior for the original audit inputs; use run_tests.py
for assertions on the repaired behavior.
"""
from __future__ import annotations

import json
import os
import statistics
import sys
import tempfile
import time
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from stock_simulator import config, persistence


def capture(label, callback):
    try:
        print(label, repr(callback()))
    except Exception as exc:
        print(label, type(exc).__name__, str(exc))


def main():
    with tempfile.TemporaryDirectory(prefix="stock-audit-") as temporary:
        config.CONFIG_PATH = Path(temporary) / "settings.json"
        # Set the directory before importing app: it imports CONFIG_PATH by value.
        from PySide6.QtCore import QEventLoop, QTimer
        from PySide6.QtWidgets import QApplication
        from stock_simulator.app import MainWindow
        from stock_simulator.kline_widget import KLineWidget
        from stock_simulator.models import DailyBar, TradeNode
        from stock_simulator.engine import DailySimulationEngine
        from stock_simulator.data_migration import export_migration_package, import_migration_package

        application = QApplication.instance() or QApplication([])
        config.CONFIG_PATH.write_text('{"sub_pane_indicators": [{}]}', encoding="utf-8")
        capture("config_wrong_element", config.load_settings)
        config.CONFIG_PATH.write_text("{}", encoding="utf-8")
        persistence.performance_history_path().write_text('{"ordinary_records": null}', encoding="utf-8")
        capture("history_null_list", persistence.load_performance_history)
        persistence.performance_history_path().unlink()
        persistence.save_document([1])
        capture("session_wrong_root", lambda: MainWindow._restore_session(SimpleNamespace(_show_storage_notices=lambda: None)))
        persistence.save_document({"version": 1, "active": None})
        capture("session_wrong_active", lambda: MainWindow._restore_session(SimpleNamespace(_show_storage_notices=lambda: None)))
        persistence.delete_document()

        with patch.object(MainWindow, "_load_startup_market"), patch.object(MainWindow, "_start_adjust_initialize"):
            window = MainWindow()
            bars = [DailyBar("sh600000", "2024-01-02", 10, 11, 9, 10, 1000, 100)]
            window.engine = DailySimulationEngine(bars, 100000, 4)
            window.engine.start()
            window.trade_started = True
            window.training_mode = True
            window.using_sample_kline = True
            window._persist_timer.start(1)
            source = Path(temporary) / "import-source"
            source.mkdir()
            (source / "session_state.json").write_text('{"version":1,"active":{"code":"IMPORTED"}}', encoding="utf-8")
            package = export_migration_package(Path(temporary) / "import.zip", source)
            import_migration_package(package, Path(temporary))
            window._migration_restore_pending_restart = True
            # A real modal information dialog runs a nested Qt event loop too.
            loop = QEventLoop()
            QTimer.singleShot(40, loop.quit)
            loop.exec()
            print("import_session_after_pending_timer", persistence.load_document()["active"]["code"])
            window._persist_timer.stop()
            window.close()
            window.deleteLater()

        engine = DailySimulationEngine([DailyBar("x", "2024-01-02", -10, 11, -10, 10, 1, 100)], 10000, 1)
        result = engine.buy_quantity(0, TradeNode.OPEN, 100)
        print("engine_negative_price", result.accepted, engine.cash, engine.slots[0].quantity)

        widget = KLineWidget(None)
        for count in (1000, 5000, 10000):
            widget.all_bars = [
                DailyBar("x", (date(1990, 1, 1) + timedelta(days=i)).isoformat(), 10, 12, 9, 10 + i % 17 / 10, 1000, 100)
                for i in range(count)
            ]
            widget.current_index = count - 1
            widget.reveal_current_full = True
            widget._boll_series()
            durations = []
            for _ in range(9):
                start = time.perf_counter()
                widget._boll_series()
                durations.append((time.perf_counter() - start) * 1000)
            print("boll_series_ms", count, "median", round(statistics.median(durations), 3), "max", round(max(durations), 3))
        widget.close()


if __name__ == "__main__":
    main()
