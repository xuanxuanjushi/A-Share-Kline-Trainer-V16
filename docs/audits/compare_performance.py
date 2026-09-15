"""Compare the saved baseline and current source in separate processes."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[2]
output = root / 'backups/20260906-performance'
if not (output / 'app.py').is_file():
    raise SystemExit('Historical baseline was cleaned. Use: python docs/audits/benchmark_performance.py')
with tempfile.TemporaryDirectory(prefix='stock-baseline-') as directory:
    baseline = Path(directory)
    shutil.copytree(root/'stock_simulator', baseline/'stock_simulator', ignore=shutil.ignore_patterns('__pycache__'))
    for name in ('app.py','tdx_reader.py','kline_widget.py'):
        shutil.copy2(output/name, baseline/'stock_simulator'/name)
    scripts = baseline/'docs/audits'
    scripts.mkdir(parents=True)
    shutil.copy2(root/'docs/audits/benchmark_performance.py', scripts/'benchmark_performance.py')
    for label, script in (('baseline-controlled',scripts/'benchmark_performance.py'),
                          ('optimized-controlled',root/'docs/audits/benchmark_performance.py')):
        result = subprocess.run([sys.executable,str(script)],cwd=root,capture_output=True,
                                env={**os.environ,'PYTHONIOENCODING':'utf-8'})
        (output/f'{label}.txt').write_bytes(result.stdout+result.stderr)
        if result.returncode:
            raise RuntimeError(f'{label} failed: {result.returncode}')
        for line in result.stdout.decode('utf-8').splitlines():
            if line.startswith(('imports_ms','startup_empty','render_10000')):
                print(label,line)
