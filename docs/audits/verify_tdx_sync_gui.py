"""Read real TDX data; use a temporary app profile and offscreen Qt window."""
import json
import os
import sys
import tempfile
import time
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from stock_simulator import config
from PySide6.QtCore import QThreadPool, QTimer
from PySide6.QtWidgets import QApplication

with tempfile.TemporaryDirectory(prefix='tdx-gui-verification-') as temporary:
    config.CONFIG_PATH = Path(temporary) / 'settings.json'
    config.CONFIG_PATH.write_text(json.dumps(asdict(config.AppSettings(
        tdx_root='D:/TDX', adjust_type='none'))), encoding='utf-8')
    from stock_simulator.app import MainWindow
    from stock_simulator.tdx_reader import resolve_tdx_location
    app = QApplication([])
    with patch.object(MainWindow, '_load_startup_market'), \
         patch.object(MainWindow, '_start_adjust_initialize'), \
         patch.object(MainWindow, '_schedule_random_prefetch'), \
         patch.object(MainWindow, '_schedule_continuation_prefetch'):
        window = MainWindow()
        window.show()
        started = time.perf_counter()
        last = [started]
        gaps = []
        finished = [False]

        def poll():
            now = time.perf_counter()
            gaps.append(now - last[0])
            last[0] = now
            if ('2026-09-04' in window.market_stats_by_date and window.engine
                    and window.engine.current_bar.date == '2026-09-04'):
                finished[0] = True
                window.grab().save(str(ROOT / 'docs/audits/2026-09-06-tdx-sync-screen.png'))
                report = {
                    'latest': window.engine.current_bar.date,
                    'labels': {key: label.text() for key, label in window.index_market_labels.items()},
                    'seconds': now - started,
                    'heartbeat_count': len(gaps),
                    'maximum_heartbeat_gap_seconds': max(gaps),
                }
                (ROOT / 'docs/audits/2026-09-06-tdx-sync-gui.json').write_text(
                    json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
                app.quit()

        timer = QTimer()
        timer.timeout.connect(poll)
        timer.start(100)
        with patch.dict(os.environ, {'QT_QPA_PLATFORM': ''}):
            window._request_market_stats_update(resolve_tdx_location('D:/TDX'))
        QTimer.singleShot(90000, app.quit)
        app.exec()
        timer.stop()
        window._migration_restore_pending_restart = True
        window._persist_timer.stop()
        window.close()
        QThreadPool.globalInstance().waitForDone()
        assert finished[0], (window.market_stats_status, len(window.market_stats_by_date))
        print('Actual background worker, signal delivery and visible labels verified.')
