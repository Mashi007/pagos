# -*- coding: utf-8 -*-
"""One-off patch for ExcelUploaderPagosUI - run from repo root."""

from pathlib import Path

path = Path(
    r"c:/Users/PORTATIL/Documents/BIBLIOTECA/GitHub/pagos/frontend/src/components/pagos/ExcelUploaderPagosUI.tsx"
)
text = path.read_text(encoding="utf-8")

old = """import {
  useExcelUploadPagos,
  type ExcelUploaderPagosProps,
} from '../../hooks/useExcelUploadPagos'"""

new = """import {
  useExcelUploadPagos,
  type ExcelUploaderPagosProps,
} from '../../hooks/useExcelUploadPagos'

import { useMemo } from 'react'"""

if "import { useMemo } from 'react'" in text:
    print("useMemo import already present")
else:
    if old not in text:
        raise SystemExit("import block not found")
    text = text.replace(old, new, 1)

needle = """  const invalidCount = excelData.filter(r => r._hasErrors).length

  return ("""

insert = """  const invalidCount = excelData.filter(r => r._hasErrors).length

  const tablaRowsVisibles = useMemo(
    () =>
      excelData.filter(
        r =>
          !savedRows.has(r._rowIndex) &&
          !enviadosRevisar.has(r._rowIndex)
      ),
    [excelData, savedRows, enviadosRevisar]
  )

  return ("""

if "tablaRowsVisibles" not in text:
    if needle not in text:
        raise SystemExit("validCount block not found")
    text = text.replace(needle, insert, 1)

old_rows = """rows={excelData.filter(
                  r =>
                    !savedRows.has(r._rowIndex) &&
                    !enviadosRevisar.has(r._rowIndex)
                )}"""

if old_rows in text:
    text = text.replace(old_rows, "rows={tablaRowsVisibles}", 1)

path.write_text(text, encoding="utf-8", newline="\n")
print("OK ExcelUploaderPagosUI.tsx")
