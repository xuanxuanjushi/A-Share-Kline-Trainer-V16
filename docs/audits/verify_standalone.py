"""Verify copied data, source switching, and a relocated packaged runtime."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from stock_simulator import config
from stock_simulator.adjust import GbbqProvider
from stock_simulator.tdx_reader import TdxDayReader
from stock_simulator.stock_info import StockInfoReader


def main():
    release = Path((ROOT / 'docs/audits/2026-09-06-standalone-release-path.txt').read_text(encoding='utf-8'))
    source = Path(json.loads((ROOT / 'config/settings.json').read_text(encoding='utf-8'))['tdx_root'])
    manifest = json.loads((release / 'market_data/snapshot.json').read_text(encoding='utf-8'))
    report = {'day_files': manifest['day_file_count'], 'latest_date': manifest['latest_date']}
    for item in manifest['files']:
        copied = release / 'market_data' / item['path']
        original = source / item['path']
        assert hashlib.sha256(copied.read_bytes()).hexdigest() == item['sha256']
        assert hashlib.sha256(original.read_bytes()).hexdigest() == item['sha256']
    report['verified_files'] = len(manifest['files'])
    print('All market files match original hashes.', flush=True)
    with tempfile.TemporaryDirectory(prefix='standalone-verification-') as temporary:
        scratch = Path(temporary)
        config.CONFIG_PATH = scratch / 'profile/settings.json'
        # Both providers decode the original rights file without relying on author caches.
        providers = [GbbqProvider(root / 'T0002/hq_cache/gbbq', scratch / f'gbbq-{i}.json')
                     for i, root in enumerate((source, release / 'market_data'))]
        for provider in providers:
            provider.initialize()
            assert provider.ready, provider.error
        readers = [TdxDayReader(root, adjust_provider=provider)
                   for root, provider in zip((source, release / 'market_data'), providers)]
        assert readers[0].scan_stock_codes() == readers[1].scan_stock_codes()
        report['stock_count'] = len(readers[1].scan_stock_codes())
        checked = []
        for code in ('sh600000', 'sh600519', 'sz000001', 'sz300750'):
            left, right = (reader.adjustment_variants(code) for reader in readers)
            assert left == right
            assert StockInfoReader(source).get(code) == StockInfoReader(release / 'market_data').get(code)
            checked.append({'code': code, 'bars': len(right['none']),
                            'adjusted_differs_from_raw': right['qfq'] != right['none']})
        report['adjustment_checks'] = checked
        print('Raw, forward/backward adjustment and stock information match.', flush=True)

        from PySide6.QtCore import QThreadPool
        from PySide6.QtWidgets import QApplication
        from stock_simulator.app import MainWindow
        application = QApplication.instance() or QApplication([])
        with patch.object(config, 'application_directory', return_value=release), \
             patch('stock_simulator.app._is_offscreen', return_value=False), \
             patch.object(MainWindow, '_request_shanghai_index_update'), \
             patch('stock_simulator.app.load_document', return_value=None):
            config.save_settings(config.AppSettings(tdx_root='market_data'))
            window = MainWindow()
            window.show()
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                application.processEvents()
                if window.engine is not None and window.adjust_provider.ready:
                    break
                time.sleep(.05)
            assert window.engine is not None
            assert window.adjust_provider.ready
            assert window.reader.scan_stock_codes() == readers[1].scan_stock_codes()
            assert '内置历史数据' in window.windowTitle()
            with patch('stock_simulator.app.QFileDialog.getExistingDirectory', return_value=str(source)):
                window.choose_tdx_dir()
            assert window.reader.tdx_root.resolve() == source.resolve()
            window.use_bundled_market()
            assert window.reader.tdx_root.resolve() == (release / 'market_data').resolve()
            assert json.loads(config.CONFIG_PATH.read_text(encoding='utf-8'))['tdx_root'] == 'market_data'
            window.grab().save(str(ROOT / 'docs/audits/2026-09-06-standalone-window.png'))
            report['gui_source_roundtrip'] = True
            window._migration_restore_pending_restart = True
            window.close()
            QThreadPool.globalInstance().waitForDone()
            application.processEvents()
        print('GUI started offline and switched external -> bundled.', flush=True)

        copied = scratch / 'copy'
        moved = scratch / '中文 搬迁后的便携版'
        assert copied.resolve().is_relative_to(scratch.resolve())
        assert moved.resolve().is_relative_to(scratch.resolve())
        shutil.copytree(release, copied)
        copied.rename(moved)
        env = os.environ.copy()
        env['APPDATA'] = str(scratch / 'empty-appdata')
        # The EXE gets neither a Python installation on PATH nor a TDX path in settings.
        env['PATH'] = os.environ.get('SystemRoot', 'C:/Windows') + '/System32'
        process = subprocess.Popen([str(moved / '大A日K股票模拟训练器.exe')], cwd=scratch,
                                   env=env, creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            time.sleep(8)
            assert process.poll() is None, f'EXE exited with {process.returncode}'
            report['relocated_exe_alive_8s_without_python_path'] = True
        finally:
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=15)
        assert not (scratch / 'empty-appdata' / config.CONFIG_DIR_NAME / 'settings.json').exists()
        report['appdata_untouched'] = True
    report['release_bytes'] = sum(p.stat().st_size for p in release.rglob('*') if p.is_file())
    (ROOT / 'docs/audits/2026-09-06-standalone-verification.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True), flush=True)


if __name__ == '__main__':
    main()
