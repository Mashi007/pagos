import * as exceljsNs from 'exceljs'

/** Raíz real del módulo (UMD/min suele exponer API en `default`). */
function excelJsRoot(): any {
  const mod: any = exceljsNs
  return mod?.default ?? mod
}

/**




 * Tipos y helpers para exceljs (alternativa segura a xlsx)




 * ExcelJS es una librería moderna y segura para trabajar con archivos Excel




 *




 * ✓ OPTIMIZACIÃ"N: Todos los imports son dinámicos para reducir el bundle inicial




 * Las librerías se cargan solo cuando se necesitan (lazy loading)




 */

// Tipo para el módulo exceljs completo (sin import estático)

// Usamos 'any' para evitar importar el tipo estáticamente y mantener lazy loading

export type ExcelJSModule = {
  Workbook: any // El tipo real se infiere en tiempo de ejecución
}

// Helper para importar exceljs de forma type-safe (LAZY LOADING)

// ✓ CRÍTICO: Este import dinámico asegura que exceljs NO se incluya en el bundle inicial

export async function importExcelJS(): Promise<ExcelJSModule> {
  try {
    // ✓ Proteger la carga dinámica con try-catch para evitar errores NS_ERROR_FAILURE

    const module = excelJsRoot()

    if (!module || !module.Workbook) {
      throw new Error('ExcelJS module loaded but Workbook is not available')
    }

    return {
      Workbook: module.Workbook,
    }
  } catch (error) {
    // ✓ Capturar y manejar errores durante la carga del módulo

    console.error('Error cargando ExcelJS:', error)

    // Re-lanzar el error con un mensaje más descriptivo

    throw new Error(
      `No se pudo cargar ExcelJS: ${error instanceof Error ? error.message : 'Error desconocido'}`
    )
  }
}

/**
 * numFmt de Excel típico de fecha/hora (excluye General/@).
 * Así un entero como 45991 en formato General (p. ej. Nº operación) no se interpreta como serial de fecha.
 */
function excelNumFmtLooksLikeDate(numFmt: unknown): boolean {
  const raw = String(numFmt ?? '').trim()
  if (!raw) return false
  const s = raw.replace(/\[\$[^\]]+\]/gi, '').toLowerCase()
  if (s === 'general' || s === '@') return false
  return (
    /\by{2,4}\b/.test(s) ||
    /\bd{1,4}\b/.test(s) ||
    /\bm{1,5}\b/.test(s) ||
    /\bh{1,2}\b/.test(s) ||
    /\bs{1,2}\b/.test(s)
  )
}

/** Serial de fecha Excel (epoch 1900 con offset -2) → DD/MM/AAAA si el año es plausible. */
function excelSerialToDdMmYyyy(n: number): string | null {
  if (!Number.isFinite(n)) return null
  const k = Math.trunc(n)
  if (k <= 200 || k >= 1e10) return null
  try {
    const d = new Date(1900, 0, 1)
    d.setDate(d.getDate() + k - 2)
    if (Number.isNaN(d.getTime())) return null
    const y = d.getFullYear()
    if (y < 1990 || y > 2040) return null
    return `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}/${y}`
  } catch {
    return null
  }
}

// Helper para leer un archivo Excel y convertirlo a JSON

export async function readExcelToJSON(
  file: File | ArrayBuffer
): Promise<any[][]> {
  try {
    const { Workbook } = await importExcelJS()

    if (!Workbook) {
      throw new Error('Workbook no está disponible en ExcelJS')
    }

    const workbook = new Workbook()

    let buffer: ArrayBuffer

    if (file instanceof File) {
      buffer = await file.arrayBuffer()
    } else {
      buffer = file
    }

    await workbook.xlsx.load(buffer)

    const worksheet = workbook.getWorksheet(1) || workbook.worksheets[0]

    if (!worksheet) {
      throw new Error('El archivo Excel no contiene hojas de cálculo')
    }

    const data: any[][] = []

    worksheet.eachRow((row, rowNumber) => {
      const rowData: any[] = []

      row.eachCell({ includeEmpty: true }, (cell, colNumber) => {
        let val = cell.value

        // Fórmula: usar resultado calculado (fecha/monto serial) como valor atómico
        if (
          val != null &&
          typeof val === 'object' &&
          'result' in (val as object) &&
          (val as { result?: unknown }).result != null &&
          typeof (val as { result?: unknown }).result !== 'object'
        ) {
          val = (val as { result: unknown }).result
        }

        if (
          val != null &&
          typeof val === 'object' &&
          !('richText' in val) &&
          'hyperlink' in (val as object) &&
          (val as { hyperlink?: string }).hyperlink
        ) {
          val = String((val as { hyperlink: string }).hyperlink).trim()
        }

        // Número (en cualquier columna): si parece documento (10+ dígitos) o "número como texto", guardar como string para no perder formato

        if (typeof val === 'number' && !Number.isNaN(val)) {
          if (Math.abs(val) >= 1e10) {
            try {
              const t = (cell as any).text

              const tStr =
                t != null
                  ? String(t)
                      .replace(/[\u200B-\u200D\uFEFF\r\n\t]/g, '')
                      .trim()
                  : ''

              if (tStr && /^\d{10,25}$/.test(tStr)) val = tStr
              else
                val =
                  Math.abs(val) >= 1e15
                    ? BigInt(Math.round(val)).toString()
                    : String(Math.round(val))
            } catch {
              val =
                Math.abs(val) >= 1e15
                  ? BigInt(Math.round(val)).toString()
                  : String(Math.round(val))
            }
          }
        }

        // Serial de fecha en Excel vs "número que parece serial" (p. ej. Nº operación 45991):
        // fuera de columnas A–H no se forzaba `cell.text`; si Excel muestra DD/MM/AAAA, preferir ese texto
        // para que la carga masiva de préstamos no convierta un ID en 30/11/2025.
        if (typeof val === 'number' && !Number.isNaN(val)) {
          const absv = Math.abs(val)
          if (absv > 200 && absv < 1e10) {
            const rawText = (cell as any).text
            const tStr =
              rawText != null
                ? String(rawText)
                    .replace(/[\u200B-\u200D\uFEFF\r\n\t]/g, '')
                    .trim()
                : ''
            if (/\d{1,2}[\/.\-]\d{1,2}[\/.\-]\d{2,4}/.test(tStr)) {
              val = tStr
            } else {
              const nf =
                (cell as any).numFmt ??
                (cell as any).style?.numFmt ??
                (cell as any).model?.numFmt
              if (excelNumFmtLooksLikeDate(nf)) {
                const asDdMm = excelSerialToDdMmYyyy(val)
                if (asDdMm) val = asDdMm
              }
            }
          }
        } else if (
          val != null &&
          typeof val === 'object' &&
          'richText' in val
        ) {
          val =
            (val as any).richText?.map((x: any) => x?.text ?? '').join('') || ''
        }

        const cellHyp = (cell as { hyperlink?: string }).hyperlink
        if (
          typeof cellHyp === 'string' &&
          cellHyp.trim() &&
          /^https?:\/\//i.test(cellHyp.trim())
        ) {
          val = cellHyp.trim()
        }

        // Columnas 1-8: forzar string y limpiar (documento puede estar en cualquier posición típica)

        if (colNumber >= 1 && colNumber <= 8 && val != null) {
          const t = (cell as any).text

          let str =
            typeof val === 'string'
              ? val
              : t != null && String(t).trim()
                ? String(t)
                : String(val)

          if (str)
            val = str.replace(/[\u200B-\u200D\uFEFF\r\n\t]/g, '').trim() || str
        }

        rowData[colNumber - 1] = val
      })

      data.push(rowData)
    })

    return data
  } catch (error) {
    // ✓ Capturar errores durante la lectura del archivo Excel

    console.error('Error leyendo archivo Excel:', error)

    throw new Error(
      `Error procesando archivo Excel: ${error instanceof Error ? error.message : 'Error desconocido'}`
    )
  }
}

// Helper para crear un workbook y descargarlo

export async function createAndDownloadExcel(
  data: Record<string, any>[],

  sheetName: string = 'Datos',

  filename: string
): Promise<void> {
  try {
    const { Workbook } = await importExcelJS()

    if (!Workbook) {
      throw new Error('Workbook no está disponible en ExcelJS')
    }

    const workbook = new Workbook()

    const worksheet = workbook.addWorksheet(sheetName)

    if (data.length === 0) {
      throw new Error('No hay datos para exportar')
    }

    // Agregar encabezados

    const headers = Object.keys(data[0])

    worksheet.addRow(headers)

    // Estilizar encabezados

    const headerRow = worksheet.getRow(1)

    headerRow.font = { bold: true }

    headerRow.fill = {
      type: 'pattern',

      pattern: 'solid',

      fgColor: { argb: 'FFE0E0E0' },
    }

    // Agregar datos

    data.forEach(row => {
      const values = headers.map(header => row[header] ?? '')

      worksheet.addRow(values)
    })

    // Ajustar ancho de columnas automáticamente

    worksheet.columns.forEach((column, index) => {
      if (column) {
        let maxLength = 10

        // Iterar sobre todas las filas para encontrar el ancho máximo

        if (worksheet.eachRow) {
          worksheet.eachRow(row => {
            const cell = row.getCell(index + 1)

            if (cell && cell.value !== null && cell.value !== undefined) {
              const cellValue = cell.value.toString()

              if (cellValue.length > maxLength) {
                maxLength = cellValue.length
              }
            }
          })
        }

        column.width = Math.min(maxLength + 2, 50)
      }
    })

    // Generar buffer y descargar

    const buffer = await workbook.xlsx.writeBuffer()

    const blob = new Blob([buffer], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })

    const url = window.URL.createObjectURL(blob)

    const link = document.createElement('a')

    link.href = url

    link.download = filename

    document.body.appendChild(link)

    link.click()

    document.body.removeChild(link)

    window.URL.revokeObjectURL(url)
  } catch (error) {
    // ✓ Capturar errores durante la creación/descarga del Excel

    console.error('Error creando/descargando Excel:', error)

    throw new Error(
      `Error generando archivo Excel: ${error instanceof Error ? error.message : 'Error desconocido'}`
    )
  }
}

// Helper para crear múltiples hojas en un workbook

export async function createMultiSheetExcel(
  sheets: Array<{ name: string; data: Record<string, any>[] }>,

  filename: string
): Promise<void> {
  try {
    const { Workbook } = await importExcelJS()

    if (!Workbook) {
      throw new Error('Workbook no está disponible en ExcelJS')
    }

    const workbook = new Workbook()

    sheets.forEach(({ name, data }) => {
      if (data.length === 0) return

      const worksheet = workbook.addWorksheet(name)

      const headers = Object.keys(data[0])

      // Agregar encabezados

      worksheet.addRow(headers)

      // Estilizar encabezados

      const headerRow = worksheet.getRow(1)

      headerRow.font = { bold: true }

      headerRow.fill = {
        type: 'pattern',

        pattern: 'solid',

        fgColor: { argb: 'FFE0E0E0' },
      }

      // Agregar datos

      data.forEach(row => {
        const values = headers.map(header => row[header] ?? '')

        worksheet.addRow(values)
      })

      // Ajustar ancho de columnas

      worksheet.columns.forEach((column, index) => {
        if (column) {
          let maxLength = 10

          // Iterar sobre todas las filas para encontrar el ancho máximo

          if (worksheet.eachRow) {
            worksheet.eachRow(row => {
              const cell = row.getCell(index + 1)

              if (cell && cell.value !== null && cell.value !== undefined) {
                const cellValue = cell.value.toString()

                if (cellValue.length > maxLength) {
                  maxLength = cellValue.length
                }
              }
            })
          }

          column.width = Math.min(maxLength + 2, 50)
        }
      })
    })

    // Generar buffer y descargar

    const buffer = await workbook.xlsx.writeBuffer()

    const blob = new Blob([buffer], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })

    const url = window.URL.createObjectURL(blob)

    const link = document.createElement('a')

    link.href = url

    link.download = filename

    document.body.appendChild(link)

    link.click()

    document.body.removeChild(link)

    window.URL.revokeObjectURL(url)
  } catch (error) {
    // ✓ Capturar errores durante la creación/descarga del Excel multi-hoja

    console.error('Error creando/descargando Excel multi-hoja:', error)

    throw new Error(
      `Error generando archivo Excel: ${error instanceof Error ? error.message : 'Error desconocido'}`
    )
  }
}
