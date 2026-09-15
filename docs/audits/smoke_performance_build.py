"""Start the packaged application with isolated AppData and no online startup."""
import os
from pathlib import Path
import subprocess
import tempfile
import time

root=Path(__file__).resolve().parents[2]
exe=root/'releases/performance-20260906/大A日K股票模拟训练器/大A日K股票模拟训练器.exe'
with tempfile.TemporaryDirectory(prefix='stock-exe-smoke-') as directory:
    with open(Path(directory)/'stderr.txt','wb') as errors:
        process=subprocess.Popen([str(exe)],env={**os.environ,'APPDATA':directory,'QT_QPA_PLATFORM':'offscreen'},
                                 stdout=errors,stderr=errors,creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            time.sleep(3)
            if process.poll() is not None:
                raise RuntimeError(f'Application exited early: {process.returncode}')
            settings=list(Path(directory).rglob('settings.json'))
            assert settings, 'Packaged initialization did not create isolated settings'
            print('Packaged smoke: process alive after 3s; isolated settings initialized; offscreen startup.')
        finally:
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=10)
