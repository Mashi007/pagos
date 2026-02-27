import * as exceljsModule from 'exceljs'

/**
 * Tipos y helpers para exceljs (alternativa segura a xlsx)
 * ExcelJS es una librerÃ­a moderna y segura para trabajar con archivos Excel
 *
 * âœ… OPTIMIZACIÃ“N: Todos los imports son dinÃ¡micos para reducir el bundle inicial
 * Las librerÃ­as se cargan solo cuando se necesitan (lazy loading)
 */

// Tipo para el mÃ³dulo exceljs completo (sin import estÃ¡tico)
// Usamos 'any' para evitar importar el tipo estÃ¡ticamente y mantener lazy loading
export type ExcelJSModule = {
  Workbook: any // El tipo real se infiere en tiempo de ejecuciÃ³n
}

// Helper para importar exceljs de forma type-safe (LAZY LOADING)
// âœ… CRÃTICO: Este import dinÃ¡mico asegura que exceljs NO se incluya en el bundle inicial
export async function importExcelJS(): Promise<ExcelJSModule> {
  try {
    // âœ… Proteger la carga dinÃ¡mica con try-catch para evitar errores NS_ERROR_FAILURE
    const module = exceljsModule
    if (!module || !module.Workbook) {
      throw new Error('ExcelJS module loaded but Workbook is not available')
    }
    return {
      Workbook: module.Workbook
    }
  } catch (error) {
    // âœ… Capturar y manejar errores durante la carga del mÃ³dulo
    console.error('Error cargando ExcelJS:', error)
    // Re-lanzar el error con un mensaje mÃ¡s descriptivo
    throw new Error(`No se pudo cargar ExcelJS: ${error instanceof Error ? error.message : 'Error desconocido'}`)
  }
}

// Helper para leer un archivo Excel y convertirlo a JSON
export async function readExcelToJSON(file: File | ArrayBuffer): Promise<any[][]> {
  try {
    const { Workbook } = await importExcelJS()
    if (!Workbook) {
      throw new Error('Workbook no estÃ¡ disponible en ExcelJS')
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
      throw new Error('El archivo Excel no contiene hojas de cÃ¡lculo')
    }

    const data: any[][] = []
    worksheet.eachRow((row, rowNumber) => {
      const rowData: any[] = []
      row.eachCell({ includeEmpty: true }, (cell, colNumber) => {
        let val = cell.value
        // Número largo (12–16 dígitos, ej. 740087443317051 o 3740087403067198): preferir cell.text ("número como texto") para no perder dígitos
        if (typeof val === 'number' && !Number.isNaN(val) && Math.abs(val) >= 1e11) {
          try {
            const t = (cell as any).text
            const tStr = t != null ? String(t).trim() : ''
            if (tStr !== '' && /^\d{12,20}$/.test(tStr)) val = tStr
            else val = Math.abs(val) >= 1e15 ? BigInt(Math.round(val)).toString() : Math.round(val).toString()
          } catch {
            val = Math.abs(val) >= 1e15 ? BigInt(Math.round(val)).toString() : Math.round(val).toString()
          }
        } else if (val != null && typeof val === 'object' && 'richText' in val) {
          // Cualquier celda con richText (ej. Nº documento con formato): extraer texto para no guardar [object Object]
          val = (val as any).richText?.map((x: any) => x?.text ?? '').join('') || ''
        } else if (colNumber === 3 || colNumber === 4 || colNumber === 5) {
          // Columnas típicas de Monto/Documento/Préstamo: forzar string para zelle/, BS./VZLA.REF, etc.
          try {
            const t = (cell as any).text
            if (t != null && String(t).trim()) val = String(t).trim()
            else if (typeof val === 'string' && val.trim()) val = val.trim()
            else if (typeof val === 'number' && !Number.isNaN(val)) val = String(Math.round(val))
          } catch {
            val = val != null ? String(val) : val
          }
        }
        rowData[colNumber - 1] = val
      })
      data.push(rowData)
    })

    return data
  } catch (error) {
    // âœ… Capturar errores durante la lectura del archivo Excel
    console.error('Error leyendo archivo Excel:', error)
    throw new Error(`Error procesando archivo Excel: ${error instanceof Error ? error.message : 'Error desconocido'}`)
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
      throw new Error('Workbook no estÃ¡ disponible en ExcelJS')
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
      fgColor: { argb: 'FFE0E0E0' }
    }

    // Agregar datos
    data.forEach(row => {
      const values = headers.map(header => row[header] ?? '')
      worksheet.addRow(values)
    })

    // Ajustar ancho de columnas automÃ¡ticamente
    worksheet.columns.forEach((column, index) => {
      if (column) {
        let maxLength = 10
        // Iterar sobre todas las filas para encontrar el ancho mÃ¡ximo
        if (worksheet.eachRow) {
          worksheet.eachRow((row) => {
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
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
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
    // âœ… Capturar errores durante la creaciÃ³n/descarga del Excel
    console.error('Error creando/descargando Excel:', error)
    throw new Error(`Error generando archivo Excel: ${error instanceof Error ? error.message : 'Error desconocido'}`)
  }
}

// Helper para crear mÃºltiples hojas en un workbook
export async function createMultiSheetExcel(
  sheets: Array<{ name: string; data: Record<string, any>[] }>,
  filename: string
): Promise<void> {
  try {
    const { Workbook } = await importExcelJS()
    if (!Workbook) {
      throw new Error('Workbook no estÃ¡ disponible en ExcelJS')
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
        fgColor: { argb: 'FFE0E0E0' }
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
          // Iterar sobre todas las filas para encontrar el ancho mÃ¡ximo
          if (worksheet.eachRow) {
            worksheet.eachRow((row) => {
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
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
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
    // âœ… Capturar errores durante la creaciÃ³n/descarga del Excel multi-hoja
    console.error('Error creando/descargando Excel multi-hoja:', error)
    throw new Error(`Error generando archivo Excel: ${error instanceof Error ? error.message : 'Error desconocido'}`)
  }
}

