/**
 * Tipos y helpers para exceljs (alternativa segura a xlsx)
 * ExcelJS es una librería moderna y segura para trabajar con archivos Excel
 *
 * ✅ OPTIMIZACIÓN: Todos los imports son dinámicos para reducir el bundle inicial
 * Las librerías se cargan solo cuando se necesitan (lazy loading)
 */

// Tipo para el módulo exceljs completo (sin import estático)
// Usamos 'any' para evitar importar el tipo estáticamente y mantener lazy loading
export type ExcelJSModule = {
  Workbook: any // El tipo real se infiere en tiempo de ejecución
}

// Helper para importar exceljs de forma type-safe (LAZY LOADING)
// ✅ CRÍTICO: Este import dinámico asegura que exceljs NO se incluya en el bundle inicial
export async function importExcelJS(): Promise<ExcelJSModule> {
  try {
    // ✅ Proteger la carga dinámica con try-catch para evitar errores NS_ERROR_FAILURE
    const module = await import('exceljs')
    if (!module || !module.Workbook) {
      throw new Error('ExcelJS module loaded but Workbook is not available')
    }
    return {
      Workbook: module.Workbook
    }
  } catch (error) {
    // ✅ Capturar y manejar errores durante la carga del módulo
    console.error('Error cargando ExcelJS:', error)
    // Re-lanzar el error con un mensaje más descriptivo
    throw new Error(`No se pudo cargar ExcelJS: ${error instanceof Error ? error.message : 'Error desconocido'}`)
  }
}

// Helper para leer un archivo Excel y convertirlo a JSON
export async function readExcelToJSON(file: File | ArrayBuffer): Promise<any[][]> {
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
        rowData[colNumber - 1] = cell.value
      })
      data.push(rowData)
    })

    return data
  } catch (error) {
    // ✅ Capturar errores durante la lectura del archivo Excel
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
      fgColor: { argb: 'FFE0E0E0' }
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
    // ✅ Capturar errores durante la creación/descarga del Excel
    console.error('Error creando/descargando Excel:', error)
    throw new Error(`Error generando archivo Excel: ${error instanceof Error ? error.message : 'Error desconocido'}`)
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
          // Iterar sobre todas las filas para encontrar el ancho máximo
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
    // ✅ Capturar errores durante la creación/descarga del Excel multi-hoja
    console.error('Error creando/descargando Excel multi-hoja:', error)
    throw new Error(`Error generando archivo Excel: ${error instanceof Error ? error.message : 'Error desconocido'}`)
  }
}

