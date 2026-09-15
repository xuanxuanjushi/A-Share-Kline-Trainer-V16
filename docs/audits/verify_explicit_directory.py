"""Verify fresh-user startup and explicit directory selection without chart navigation."""
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

with tempfile.TemporaryDirectory(prefix='explicit-directory-verification-') as temporary:
    config.CONFIG_PATH = Path(temporary) / 'settings.json'
    config.ensure_packaged_user_files(is_packaged=True)
    from stock_simulator.app import MainWindow
    from stock_simulator.tdx_reader import TdxDayReader
    from stock_simulator.index_data import merge_index_bars
    # Supply a deterministic online response; the application itself must not
    # select this directory until the file-dialog action below.
    latest = TdxDayReader('D:/TDX', adjust_type='none').read_daily_bars('sh999999')
    application = QApplication([])
    stages = []
    complete = [False]
    selected = [False]
    with patch('stock_simulator.app.find_tdx_installation', side_effect=AssertionError('automatic directory selection')), \
         patch('stock_simulator.app.fetch_shanghai_index_bars', side_effect=lambda history: merge_index_bars(history, latest)), \
         patch('stock_simulator.app.fetch_public_market_stats', side_effect=AssertionError('statistics before directory selection')):
        window = MainWindow()
        window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        window.show()

        def capture(stage):
            stages.append({'stage': stage, 'directory': window.tdx_path.text(),
                           'date': window.engine.current_bar.date if window.engine else None,
                           'label': window.index_market_labels['上涨/下跌家数'].text(),
                           'stats_dates': len(window.market_stats_by_date)})

        def choose():
            capture('fresh startup before selection')
            assert window.tdx_path.text() == ''
            assert not window.market_stats_by_date
            assert window.market_stats_worker is None
            assert not (config.CONFIG_PATH.parent / 'market_stats_daily.json').exists()
            selected[0] = True
            with patch('stock_simulator.app.QFileDialog.getExistingDirectory', return_value='D:/TDX'):
                window.choose_tdx_dir()
            capture('selected own directory; calculation started')

        def observe():
            if selected[0] and '2442 / 2918' in window.index_market_labels['上涨/下跌家数'].text():
                complete[0] = True
                capture('statistics completed with no chart movement')
                application.quit()

        QTimer.singleShot(1500, choose)
        timer = QTimer()
        timer.timeout.connect(observe)
        timer.start(100)
        QTimer.singleShot(90000, application.quit)
        application.exec()
        timer.stop()
        window._migration_restore_pending_restart = True
        window.close()
        QThreadPool.globalInstance().waitForDone()
        report = {'stages': stages, 'success': complete[0]}
        (ROOT / 'docs/audits/2026-09-06-explicit-directory-real.json').write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        assert complete[0], report
        print('Fresh directory blank; no statistics before selection; real TDX statistics displayed automatically after selection.')
