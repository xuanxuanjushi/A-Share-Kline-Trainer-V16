import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import zipfile
from PyInstaller.archive.readers import CArchiveReader

ROOT = Path(__file__).resolve().parents[2]
release = Path((ROOT / 'docs/audits/2026-09-06-light-release-path.txt').read_text(encoding='utf-8'))
assert (release / 'portable_mode.flag').is_file()
assert not (release / 'market_data').exists()
assert not list(release.rglob('*.day'))
assert not list(release.rglob('gbbq*'))
assert sorted(p.name for p in (release / 'portable_data').iterdir()) == ['settings.json']
assert json.loads((release / 'portable_data/settings.json').read_text(encoding='utf-8'))['tdx_root'] == ''
executable = release / '大A日K股票模拟训练器.exe'
archive = CArchiveReader(str(executable))
pyz = archive.open_embedded_archive(next(name for name in archive.toc if name.startswith('PYZ')))
assert 'openpyxl' in pyz.toc and 'openpyxl.chart.label' in pyz.toc
code = pyz.extract('stock_simulator.excel_export')
assert code == compile((ROOT / 'stock_simulator/excel_export.py').read_text(encoding='utf-8-sig'), code.co_filename, 'exec')
print('Package has current Excel exporter and dependencies; no TDX data or user records.', flush=True)
with tempfile.TemporaryDirectory(prefix='light-portable-check-') as temporary:
    scratch = Path(temporary)
    copied = scratch / '中文 空格便携版'
    shutil.copytree(release, copied)
    env = os.environ.copy()
    env['QT_QPA_PLATFORM'] = 'offscreen'
    env['APPDATA'] = str(scratch / 'appdata')
    env['PATH'] = os.environ.get('SystemRoot', 'C:/Windows') + '/System32'
    process = subprocess.Popen([str(copied / executable.name)], cwd=scratch, env=env,
                               creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        time.sleep(8)
        assert process.poll() is None, process.returncode
    finally:
        if process.poll() is None:
            process.terminate()
        process.wait(timeout=15)
    assert not list((scratch / 'appdata').rglob('settings.json'))
output = release.parent / '便携版-无行情-Excel对齐修复-20260906.zip'
with zipfile.ZipFile(output, 'x', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
    for path in release.rglob('*'):
        if path.is_file():
            archive.write(path, Path(release.name) / path.relative_to(release))
with zipfile.ZipFile(output) as archive:
    assert archive.testzip() is None
report = {'aligned_exporter_matches_source': True, 'openpyxl_bundled': True,
          'no_tdx_data': True, 'empty_profile': True, 'relocated_startup_8s': True,
          'zip_crc_valid': True, 'zip_bytes': output.stat().st_size, 'zip': str(output)}
(ROOT / 'docs/audits/2026-09-06-light-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=True), flush=True)
