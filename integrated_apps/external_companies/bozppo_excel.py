# -*- coding: utf-8 -*-

from html import escape
from zipfile import ZIP_DEFLATED, ZipFile


def write_xlsx(path, sheet_name, headers, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    values = [headers, *rows]
    sheet_xml = _worksheet_xml(values)
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types_xml())
        archive.writestr("_rels/.rels", _root_rels_xml())
        archive.writestr("xl/workbook.xml", _workbook_xml(sheet_name))
        archive.writestr("xl/_rels/workbook.xml.rels", _workbook_rels_xml())
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)


def _worksheet_xml(values):
    max_columns = max((len(row) for row in values), default=1)
    max_rows = max(len(values), 1)
    dimension = f"A1:{_column_name(max_columns)}{max_rows}"
    rows_xml = []
    for row_index, row in enumerate(values, start=1):
        cells = []
        for column_index, value in enumerate(row, start=1):
            reference = f"{_column_name(column_index)}{row_index}"
            text = escape("" if value is None else str(value), quote=False)
            cells.append(f'<c r="{reference}" t="inlineStr"><is><t>{text}</t></is></c>')
        rows_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')

    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <dimension ref="{dimension}"/>
  <sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>
  <sheetData>
    {''.join(rows_xml)}
  </sheetData>
  <autoFilter ref="{dimension}"/>
</worksheet>"""


def _content_types_xml():
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>"""


def _root_rels_xml():
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""


def _workbook_xml(sheet_name):
    safe_sheet_name = escape(sheet_name[:31])
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="{safe_sheet_name}" sheetId="1" r:id="rId1"/></sheets>
</workbook>"""


def _workbook_rels_xml():
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>"""


def _column_name(index):
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name
