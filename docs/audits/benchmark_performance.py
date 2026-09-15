"""Isolated startup and full-widget paint benchmark; no network or user writes."""
from __future__ import annotations
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import cProfile
import io
import json
import pstats
import statistics
import tempfile
import time
from datetime import date, timedelta
from unittest.mock import patch

def main():
    started = time.perf_counter()
    from stock_simulator import config
    with tempfile.TemporaryDirectory(prefix='stock-performance-') as directory:
        config.CONFIG_PATH = Path(directory)/'settings.json'
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QPixmap
        from stock_simulator.app import MainWindow
        from stock_simulator.kline_widget import KLineWidget
        from stock_simulator.models import DailyBar
        print('imports_ms', round((time.perf_counter()-started)*1000, 2))
        application=QApplication.instance() or QApplication([])
        times=[]
        windows=[]
        profiler=cProfile.Profile()
        for _ in range(5):
            with patch.object(MainWindow, '_load_startup_market'), patch.object(MainWindow, '_start_adjust_initialize'):
                started=time.perf_counter()
                profiler.enable()
                window=MainWindow()
                windows.append(window)
                profiler.disable()
                window.show()
                application.processEvents()
                times.append((time.perf_counter()-started)*1000)
                window._migration_restore_pending_restart=True
                window.close()
                # Keep widgets alive until process exit: old versions have
                # pending layout timers. Remove filters to avoid accumulating
                # work from previous windows in the next startup sample.
                application.removeEventFilter(window)
                application.processEvents()
        print('startup_empty_config_ms', json.dumps(times))
        stream=io.StringIO()
        pstats.Stats(profiler,stream=stream).sort_stats('cumulative').print_stats(18)
        print(stream.getvalue())
        widget=KLineWidget(None)
        widget.resize(1100,750)
        bars=[DailyBar('sh600000',(date(1990,1,1)+timedelta(days=i)).isoformat(),10,12,9,10+i%17/10,1000,100) for i in range(10000)]
        widget.set_data(bars,bars[-120:],[],9999,0,120,True)
        target=QPixmap(widget.size())
        for mode in ('none','boll','gma'):
            widget.main_overlay_mode=mode
            times=[]
            for _ in range(12):
                started=time.perf_counter()
                widget.render(target)
                times.append((time.perf_counter()-started)*1000)
            print('render_10000_ms',mode,'first',round(times[0],3),'median_warm',round(statistics.median(times[2:]),3),'max_warm',round(max(times[2:]),3))
        widget.close()

if __name__=='__main__':
    main()
