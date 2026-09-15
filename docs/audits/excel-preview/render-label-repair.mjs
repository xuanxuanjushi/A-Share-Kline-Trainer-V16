import fs from 'node:fs/promises';
import { FileBlob, SpreadsheetFile } from '@oai/artifact-tool';
const path = 'C:/Users/Administrator/Desktop/交易统计-连续复利模式-20230928-20260906-210809-图表修正版.xlsx';
const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(path));
const preview = await workbook.render({sheetName:'统计概览', autoCrop:'all', scale:1, format:'png'});
await fs.writeFile(new URL('./labels-fixed.png', import.meta.url), new Uint8Array(await preview.arrayBuffer()));
