"""Exercise the real startup and TDX import without mouse or keyboard input."""
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.pop('QT_QPA_PLATFORM', None)
from stock_simulator import config
from PySide6.QtCore import Qt, QTimer, QThreadPool
from PySide6.QtWidgets import QApplication

with tempfile.TemporaryDirectory(prefix='startup-tdx-verification-') as temporary:
    config.CONFIG_PATH = Path(temporary) / 'settings.json'
    config.ensure_packaged_user_files(is_packaged=True)
    from stock_simulator.app import MainWindow
    from stock_simulator.tdx_reader import resolve_tdx_location
    application = QApplication([])
    stages = []
    success = [False]
    with patch('stock_simulator.app.fetch_shanghai_index_bars', side_effect=AssertionError('unexpected online index')) as online_index, \
         patch('stock_simulator.app.fetch_public_market_stats', side_effect=AssertionError('unexpected online statistics')) as online_stats:
        window = MainWindow()
        window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        window.show()

        def capture(stage):
            stages.append({'stage': stage, 'date': window.engine.current_bar.date if window.engine else None,
                           'label': window.index_market_labels['上涨/下跌家数'].text(),
                           'source': window.tdx_path.text()})

        def import_local():
            capture('startup without TDX; no input')
            assert window.engine.current_bar.date == '2026-08-21'
            assert '暂未更新' not in stages[-1]['label']
            window._apply_tdx_location(resolve_tdx_location('D:/TDX'))
            capture('TDX import requested; no navigation')

        def observe():
            if (window.engine and window.engine.current_bar.date == '2026-09-04'
                    and '2442 / 2918' in window.index_market_labels['上涨/下跌家数'].text()):
                capture('TDX completed automatically; still no navigation')
                success[0] = True
                application.quit()

        QTimer.singleShot(1500, import_local)
        timer = QTimer()
        timer.timeout.connect(observe)
        timer.start(100)
        QTimer.singleShot(90000, application.quit)
        application.exec()
        timer.stop()
        window._migration_restore_pending_restart = True
        window.close()
        QThreadPool.globalInstance().waitForDone()
        report = {'stages': stages, 'online_index_calls': online_index.call_count,
                  'online_stats_calls': online_stats.call_count, 'success': success[0]}
        (ROOT / 'docs/audits/2026-09-06-startup-then-tdx.json').write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        assert success[0], report
        assert online_index.call_count == online_stats.call_count == 0, report
        print('Real startup cache -> real TDX import -> updated labels: passed with no navigation or online requests.')
