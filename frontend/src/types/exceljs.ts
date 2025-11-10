/**
 * Tipos y helpers para exceljs (alternativa segura a xlsx)
 * ExcelJS es una librería moderna y segura para trabajar con archivos Excel
 */

import ExcelJS from 'exceljs'

// Tipo para el módulo exceljs completo
export interface ExcelJSModule {
  Workbook: typeof ExcelJS.Workbook
}

// Helper para importar exceljs de forma type-safe
export async function importExcelJS(): Promise<ExcelJSModule> {
  const module = await import('exceljs')
  return {
    Workbook: module.Workbook
  }
}

// Helper para leer un archivo Excel y convertirlo a JSON
export async function readExcelToJSON(file: File | ArrayBuffer): Promise<any[][]> {
  const { Workbook } = await importExcelJS()
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
}

// Helper para crear un workbook y descargarlo
export async function createAndDownloadExcel(
  data: Record<string, any>[],
  sheetName: string = 'Datos',
  filename: string
): Promise<void> {
  const { Workbook } = await importExcelJS()
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
}

// Helper para crear múltiples hojas en un workbook
export async function createMultiSheetExcel(
  sheets: Array<{ name: string; data: Record<string, any>[] }>,
  filename: string
): Promise<void> {
  const { Workbook } = await importExcelJS()
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
}

