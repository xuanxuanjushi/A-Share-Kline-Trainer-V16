"""Blank settings + bundled August cache must first display local latest data."""
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.pop('QT_QPA_PLATFORM', None)
from stock_simulator import config
from PySide6.QtCore import Qt, QTimer, QThreadPool
from PySide6.QtWidgets import QApplication

with tempfile.TemporaryDirectory(prefix='latest-startup-verification-') as temporary:
    config.CONFIG_PATH = Path(temporary) / 'settings.json'
    config.ensure_packaged_user_files(is_packaged=True)
    from stock_simulator.app import MainWindow
    application = QApplication([])
    started = time.perf_counter()
    first_displays = []
    original_activate = MainWindow._activate_browse_engine

    def record_display(window, bars, *args, **kwargs):
        first_displays.append({'date': bars[-1].date, 'seconds': time.perf_counter() - started})
        return original_activate(window, bars, *args, **kwargs)

    complete = [False]
    with patch.object(MainWindow, '_activate_browse_engine', record_display), \
         patch('stock_simulator.app.fetch_shanghai_index_bars', side_effect=AssertionError('unexpected network')) as network:
        window = MainWindow()
        window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        window.show()

        def observe():
            if window.engine and '2442 / 2918' in window.index_market_labels['上涨/下跌家数'].text():
                complete[0] = True
                application.quit()

        timer = QTimer()
        timer.timeout.connect(observe)
        timer.start(100)
        QTimer.singleShot(90000, application.quit)
        application.exec()
        timer.stop()
        report = {'first_displays': first_displays, 'source': window.tdx_path.text(),
                  'label': window.index_market_labels['上涨/下跌家数'].text(),
                  'completed': complete[0], 'network_calls': network.call_count}
        window._migration_restore_pending_restart = True
        window.close()
        QThreadPool.globalInstance().waitForDone()
        (ROOT / 'docs/audits/2026-09-06-latest-startup-real.json').write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        assert complete[0] and first_displays[0]['date'] == '2026-09-04', report
        assert all(item['date'] == '2026-09-04' for item in first_displays), report
        assert network.call_count == 0, report
        assert json.loads(config.CONFIG_PATH.read_text(encoding='utf-8'))['tdx_root'] == window.tdx_path.text()
        print('Fresh startup automatically located TDX; first chart was September 4; statistics updated without navigation.')
