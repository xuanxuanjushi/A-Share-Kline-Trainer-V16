# 对齐修复与无行情便携版

- `stock_simulator/excel_export.py`：总览B列的文字、日期、金额、比例、计数统一左对齐，数值类型和格式保留。
- `stock_simulator/portable_builder.py`：新增可选的无行情打包方式，独立数据包原有默认行为保留；无行情包不读取通达信，不复制个人记录，设置中的数据源为空。
- 新增 `tests/test_light_portable.py`。修改前备份在 `backups/20260906-211905-aligned-light-portable/`。

交付文件：`releases/便携版-无行情-Excel对齐修复-20260906.zip`，88,080,778 字节（约84 MiB）。
解压后双击运行.bat或EXE；使用个股行情时自行选择通达信目录。保留原有上证指数和测试K线，不附带通达信个股日K、权息资料、个人成绩或续作记录。

验证：88项测试通过；导出总览结果列对齐校验通过；打包EXE中的Excel导出模块代码与当前源码一致；openpyxl已包含；包内无.day及gbbq文件，portable_data仅有空数据源的默认设置；中文含空格新目录、移除Python PATH后启动8秒正常，未向AppData写设置；ZIP CRC通过。

未在另一台实体电脑测试，也未在桌面Excel/WPS里人工复验本次对齐。未覆盖或修改用户现有Excel文件与旧便携版。
