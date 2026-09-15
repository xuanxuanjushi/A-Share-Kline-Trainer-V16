"""Verify the final data-bearing release without modifying its clean profile."""
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
import zipfile
from PyInstaller.archive.readers import CArchiveReader

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from stock_simulator import config
from stock_simulator.adjust import GbbqProvider
from stock_simulator.tdx_reader import TdxDayReader

release = Path((ROOT / 'docs/audits/2026-09-06-full-aligned-path.txt').read_text(encoding='utf-8'))
source = Path(json.loads((ROOT / 'config/settings.json').read_text(encoding='utf-8'))['tdx_root'])
manifest = json.loads((release / 'market_data/snapshot.json').read_text(encoding='utf-8'))
for item in manifest['files']:
    assert hashlib.sha256((release / 'market_data' / item['path']).read_bytes()).hexdigest() == item['sha256']
    assert hashlib.sha256((source / item['path']).read_bytes()).hexdigest() == item['sha256']
assert json.loads((release / 'portable_data/settings.json').read_text(encoding='utf-8'))['tdx_root'] == 'market_data'
assert sorted(p.name for p in (release / 'portable_data').iterdir()) == ['settings.json']
executable = release / '大A日K股票模拟训练器.exe'
archive = CArchiveReader(str(executable))
pyz = archive.open_embedded_archive(next(n for n in archive.toc if n.startswith('PYZ')))
for module in ('excel_export', 'config', 'portable_builder', 'app'):
    code = pyz.extract('stock_simulator.' + module)
    assert code == compile((ROOT / f'stock_simulator/{module}.py').read_text(encoding='utf-8-sig'), code.co_filename, 'exec')
assert 'openpyxl' in pyz.toc
print('All market files match original; packaged modules match current source.', flush=True)
with tempfile.TemporaryDirectory(prefix='full-portable-final-') as temporary:
    scratch = Path(temporary)
    moved = scratch / '中文 空格新位置'
    shutil.copytree(release, moved)
    with patch.object(config, 'application_directory', return_value=moved), patch.object(config, 'CONFIG_PATH', moved / 'portable_data/settings.json'):
        settings = config.load_settings()
        assert Path(settings.tdx_root) == moved / 'market_data'
        config.save_settings(settings)
        assert json.loads(config.CONFIG_PATH.read_text(encoding='utf-8'))['tdx_root'] == 'market_data'
    providers = [GbbqProvider(p / 'T0002/hq_cache/gbbq') for p in (source, moved / 'market_data')]
    for provider in providers:
        provider.initialize()
        assert provider.ready, provider.error
    readers = [TdxDayReader(p, adjust_provider=provider) for p, provider in zip((source, moved / 'market_data'), providers)]
    assert readers[0].scan_stock_codes() == readers[1].scan_stock_codes()
    for code in ('sh600000', 'sz000001'):
        assert readers[0].adjustment_variants(code) == readers[1].adjustment_variants(code)
    print('Relocated relative paths, stock list and raw/forward/backward prices verified.', flush=True)
    env = os.environ.copy()
    env['QT_QPA_PLATFORM'] = 'offscreen'
    env['APPDATA'] = str(scratch / 'empty-appdata')
    env['PATH'] = os.environ.get('SystemRoot', 'C:/Windows') + '/System32'
    process = subprocess.Popen([str(moved / executable.name)], cwd=scratch, env=env, creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        time.sleep(8)
        assert process.poll() is None, process.returncode
    finally:
        if process.poll() is None:
            process.terminate()
        process.wait(timeout=15)
    assert not list((scratch / 'empty-appdata').rglob('settings.json'))
output = release.parent / '独立便携版-含日K复权-20260906.zip'
with zipfile.ZipFile(output, 'x', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
    for file in release.rglob('*'):
        if file.is_file():
            archive.write(file, Path(release.name) / file.relative_to(release))
with zipfile.ZipFile(output) as archive:
    assert archive.testzip() is None
report = {'day_files': manifest['day_file_count'], 'verified_files': len(manifest['files']),
          'latest_date': manifest['latest_date'], 'relative_path_after_relocation': True,
          'all_source_hashes_match': True, 'packaged_code_matches_source': True,
          'adjustments_match': True, 'relocated_exe_alive_8s': True,
          'zip_crc_valid': True, 'zip_bytes': output.stat().st_size, 'zip': str(output)}
(ROOT / 'docs/audits/2026-09-06-full-aligned-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=True), flush=True)
