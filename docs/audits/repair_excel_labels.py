"""Repair chart-label defaults in a separate copy, preserving all workbook data."""
from pathlib import Path
import hashlib
import json
import zipfile
from xml.etree import ElementTree as ET

C = 'http://schemas.openxmlformats.org/drawingml/2006/chart'
A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
ET.register_namespace('', C)
ET.register_namespace('a', A)
ns = {'c': C}
source = Path('C:/Users/Administrator/Desktop/交易统计-连续复利模式-20230928-20260906-210809.xlsx')
destination = source.with_name(source.stem + '-图表修正版.xlsx')
before = hashlib.sha256(source.read_bytes()).hexdigest()
flags = ('showLegendKey', 'showVal', 'showCatName', 'showSerName', 'showPercent', 'showBubbleSize', 'showLeaderLines')
changed = {}
with zipfile.ZipFile(source) as original, zipfile.ZipFile(destination, 'x', zipfile.ZIP_DEFLATED) as result:
    for entry in original.infolist():
        data = original.read(entry.filename)
        if entry.filename.startswith('xl/charts/chart') and entry.filename.endswith('.xml'):
            root = ET.fromstring(data)
            modified = False
            for series in root.findall('.//c:ser', ns):
                group = series.find('c:dLbls', ns)
                if group is None:
                    continue
                count = int(series.find('c:val/c:numRef/c:numCache/c:ptCount', ns).get('val'))
                selected = {int(label.find('c:idx', ns).get('val')): label
                            for label in group.findall('c:dLbl', ns) if label.find('c:tx', ns) is not None}
                group.clear()
                for index in range(count):
                    label = selected.get(index)
                    if label is None:
                        label = ET.Element(f'{{{C}}}dLbl')
                        ET.SubElement(label, f'{{{C}}}idx', val=str(index))
                    for child in list(label):
                        if child.tag in {f'{{{C}}}{tag}' for tag in (*flags, 'delete')}:
                            label.remove(child)
                    label.insert(1, ET.Element(f'{{{C}}}delete', val='0' if index in selected else '1'))
                    for flag in flags:
                        ET.SubElement(label, f'{{{C}}}{flag}', val='0')
                    group.append(label)
                for flag in flags:
                    ET.SubElement(group, f'{{{C}}}{flag}', val='0')
                changed[entry.filename] = {'points': count, 'visible_custom_labels': len(selected)}
                modified = True
            if modified:
                data = ET.tostring(root, encoding='utf-8', xml_declaration=True)
        result.writestr(entry, data)
assert before == hashlib.sha256(source.read_bytes()).hexdigest()
with zipfile.ZipFile(source) as original, zipfile.ZipFile(destination) as repaired:
    assert repaired.testzip() is None
    assert original.namelist() == repaired.namelist()
    for name in original.namelist():
        if name not in changed:
            assert original.read(name) == repaired.read(name), name
report = {'source_unchanged': True, 'all_nonchart_parts_identical': True, 'changes': changed,
          'output': str(destination)}
Path(__file__).with_name('2026-09-06-excel-label-repair.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=True))
